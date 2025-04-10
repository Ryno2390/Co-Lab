import pytest
from pytest_mock import MockerFixture
from typing import List, Tuple, Optional, Dict, Any
import asyncio

# Modules to test
# Use imports relative to project root 'Co-Lab'
try:
    from services.indexer_service import logic
    # Import models from shared data_layer
    from data_layer.indexer_client import IndexerQuery, IndexerResult, DocumentInfo
except ImportError:
     pytest.skip("Skipping indexer logic tests: could not import modules", allow_module_level=True)

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

# --- Test Fixtures ---

@pytest.fixture
def sample_query_text() -> IndexerQuery:
    return IndexerQuery(query_text="find documents about python", top_k=5)

@pytest.fixture
def sample_query_keywords() -> IndexerQuery:
    return IndexerQuery(keywords=["python", "fastapi"], top_k=3)

@pytest.fixture
def sample_query_vector() -> IndexerQuery:
    # Assuming 1536 dims based on previous settings
    return IndexerQuery(query_vector=[0.1]*1536, top_k=4)

@pytest.fixture
def sample_query_hybrid() -> IndexerQuery:
    return IndexerQuery(query_text="hybrid search query", keywords=["hybrid"], top_k=5)

@pytest.fixture
def mock_pinecone_results() -> Tuple[str, List[DocumentInfo]]:
    docs = [
        DocumentInfo(cid="pine_cid_1", score=0.9, metadata={"type": "pine"}),
        DocumentInfo(cid="common_cid_1", score=0.8, metadata={"type": "pine"}),
        DocumentInfo(cid="pine_cid_2", score=0.7, metadata={"type": "pine"}),
    ]
    return "pinecone", docs

@pytest.fixture
def mock_es_results() -> Tuple[str, List[DocumentInfo]]:
    docs = [
        DocumentInfo(cid="es_cid_1", score=20.5, metadata={"type": "es"}), # ES scores aren't normalized like cosine
        DocumentInfo(cid="common_cid_1", score=15.0, metadata={"type": "es"}),
        DocumentInfo(cid="es_cid_2", score=10.1, metadata={"type": "es"}),
    ]
    return "elasticsearch", docs

# --- Test Cases ---

async def test_perform_search_vector_only(
    mocker: MockerFixture,
    sample_query_vector: IndexerQuery,
    mock_pinecone_results: Tuple[str, List[DocumentInfo]]
):
    """Tests search when only a vector query is feasible."""
    # Arrange
    # Mock helpers called by perform_search
    mock_gen_embed = mocker.patch('Co-Lab.services.indexer_service.logic.generate_embedding')
    mock_query_pine = mocker.patch('Co-Lab.services.indexer_service.logic.query_pinecone', return_value=mock_pinecone_results)
    mock_query_es = mocker.patch('Co-Lab.services.indexer_service.logic.query_elasticsearch') # Should not be called

    # Act
    result = await logic.perform_search(sample_query_vector)

    # Assert
    mock_gen_embed.assert_not_called() # Vector was provided
    mock_query_pine.assert_awaited_once()
    mock_query_es.assert_not_called()
    assert result.status == "success"
    assert len(result.results) == len(mock_pinecone_results[1])
    assert result.results[0].cid == "pine_cid_1" # Check basic ordering by score (RRF score here)

async def test_perform_search_keyword_only(
    mocker: MockerFixture,
    sample_query_keywords: IndexerQuery,
    mock_es_results: Tuple[str, List[DocumentInfo]]
):
    """Tests search when only a keyword query is feasible."""
    # Arrange
    mock_gen_embed = mocker.patch('Co-Lab.services.indexer_service.logic.generate_embedding')
    mock_query_pine = mocker.patch('Co-Lab.services.indexer_service.logic.query_pinecone') # Should not be called
    mock_query_es = mocker.patch('Co-Lab.services.indexer_service.logic.query_elasticsearch', return_value=mock_es_results)

    # Act
    result = await logic.perform_search(sample_query_keywords)

    # Assert
    mock_gen_embed.assert_not_called()
    mock_query_pine.assert_not_called()
    mock_query_es.assert_awaited_once()
    assert result.status == "success"
    assert len(result.results) == len(mock_es_results[1])
    assert result.results[0].cid == "es_cid_1" # Check basic ordering by score (RRF score here)


async def test_perform_search_hybrid_rrf(
    mocker: MockerFixture,
    sample_query_hybrid: IndexerQuery,
    mock_pinecone_results: Tuple[str, List[DocumentInfo]],
    mock_es_results: Tuple[str, List[DocumentInfo]]
):
    """Tests hybrid search and RRF combination."""
    # Arrange
    mock_vector = [0.2] * 1536
    mock_gen_embed = mocker.patch('Co-Lab.services.indexer_service.logic.generate_embedding', return_value=mock_vector)
    mock_query_pine = mocker.patch('Co-Lab.services.indexer_service.logic.query_pinecone', return_value=mock_pinecone_results)
    mock_query_es = mocker.patch('Co-Lab.services.indexer_service.logic.query_elasticsearch', return_value=mock_es_results)

    # Act
    result = await logic.perform_search(sample_query_hybrid)

    # Assert
    mock_gen_embed.assert_awaited_once_with(sample_query_hybrid.query_text)
    mock_query_pine.assert_awaited_once()
    mock_query_es.assert_awaited_once()
    assert result.status == "success"
    # Expected order based on RRF (k=60):
    # common_cid_1: 1/(60+2) + 1/(60+2) = 2/62 ~ 0.0322
    # pine_cid_1:   1/(60+1) = 1/61 ~ 0.0164
    # es_cid_1:     1/(60+1) = 1/61 ~ 0.0164
    # pine_cid_2:   1/(60+3) = 1/63 ~ 0.0159
    # es_cid_2:     1/(60+3) = 1/63 ~ 0.0159
    # Expected order: common_cid_1, pine_cid_1, es_cid_1, pine_cid_2, es_cid_2
    assert len(result.results) == 5 # top_k=5
    assert result.results[0].cid == "common_cid_1"
    # Check the next two have the same score (tie-breaking depends on sort stability)
    assert result.results[1].score == result.results[2].score
    assert {result.results[1].cid, result.results[2].cid} == {"pine_cid_1", "es_cid_1"}
    assert result.results[3].score == result.results[4].score
    assert {result.results[3].cid, result.results[4].cid} == {"pine_cid_2", "es_cid_2"}


async def test_perform_search_no_query(mocker: MockerFixture):
    """Tests search when no valid query parameters are provided."""
     # Arrange
    empty_query = IndexerQuery(top_k=5) # No text, keywords, or vector
    mock_gen_embed = mocker.patch('Co-Lab.services.indexer_service.logic.generate_embedding')
    mock_query_pine = mocker.patch('Co-Lab.services.indexer_service.logic.query_pinecone')
    mock_query_es = mocker.patch('Co-Lab.services.indexer_service.logic.query_elasticsearch')

    # Act
    result = await logic.perform_search(empty_query)

    # Assert
    mock_gen_embed.assert_not_called()
    mock_query_pine.assert_not_called()
    mock_query_es.assert_not_called()
    assert result.status == "error"
    assert "No valid query parameters" in result.error_message

# TODO: Add tests for error handling within query_pinecone/query_elasticsearch
# TODO: Add tests for embedding generation failure