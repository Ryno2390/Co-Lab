import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from typing import Optional

# Import the FastAPI app object from the service we want to test
# Use imports relative to the project root 'Co-Lab'
try:
    # Assuming tests are run from the directory containing 'Co-Lab'
    from services.summarization_ai.main import app
    from services.summarization_ai.api import SummarizationResponse
except ImportError:
    # Fallback if structure is different or imports fail during test discovery
    print("Warning: Could not import SummarizationAI app/models for testing.")
    app = None # type: ignore
    SummarizationResponse = None # type: ignore


# Create a TestClient instance using the service's app
if app:
    client = TestClient(app)
else:
    pytest.skip("Skipping summarization service tests: could not import app", allow_module_level=True)


# Mark tests as asyncio if the endpoint functions themselves are async
pytestmark = pytest.mark.asyncio


# --- Test Cases ---

def test_health_check():
    """Tests the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

async def test_invoke_summarization_success_with_text(mocker: MockerFixture):
    """Tests successful summarization when text is provided directly."""
    # Arrange
    mock_summary = "This is the generated summary."
    # Mock the 'logic' module *where it is imported* in the 'api' module.
    mock_logic = mocker.patch('Co-Lab.services.summarization_ai.api.logic')
    # Configure the specific function on the mock module object
    mock_logic.generate_summary.return_value = mock_summary

    request_data = {
        "instruction": "Please summarize this long text...",
    }

    # Act
    response = client.post("/invoke", json=request_data)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["content"] == mock_summary
    assert response_data["error"] is None
    # Check that the mocked logic function was called correctly
    mock_logic.generate_summary.assert_awaited_once_with(
        instruction=request_data["instruction"],
        cid=None,
        max_length=None
    )

async def test_invoke_summarization_success_with_cid(mocker: MockerFixture):
    """Tests successful summarization when a CID is provided."""
    # Arrange
    mock_summary = "Summary based on CID content."
    mock_logic = mocker.patch('Co-Lab.services.summarization_ai.api.logic')
    mock_logic.generate_summary.return_value = mock_summary

    request_data = {
        "instruction": "Summarize the document at this CID.",
        "cid": "bafybe..." # Example CID
    }

    # Act
    response = client.post("/invoke", json=request_data)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["content"] == mock_summary
    assert response_data["error"] is None
    mock_logic.generate_summary.assert_awaited_once_with(
        instruction=request_data["instruction"],
        cid=request_data["cid"],
        max_length=None
    )

async def test_invoke_summarization_logic_error(mocker: MockerFixture):
    """Tests the case where the summarization logic raises an exception."""
    # Arrange
    error_message = "LLM API call failed"
    mock_logic = mocker.patch('Co-Lab.services.summarization_ai.api.logic')
    mock_logic.generate_summary.side_effect = Exception(error_message)

    request_data = {"instruction": "Summarize this."}

    # Act
    response = client.post("/invoke", json=request_data)

    # Assert
    assert response.status_code == 200 # API handles error gracefully
    response_data = response.json()
    assert response_data["content"] is None
    assert error_message in response_data["error"]
    mock_logic.generate_summary.assert_awaited_once()

async def test_invoke_summarization_logic_returns_none(mocker: MockerFixture):
    """Tests the case where the summarization logic returns None without error."""
    # Arrange
    mock_logic = mocker.patch('Co-Lab.services.summarization_ai.api.logic')
    mock_logic.generate_summary.return_value = None

    request_data = {"instruction": "Summarize this."}

    # Act
    response = client.post("/invoke", json=request_data)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["content"] is None
    assert "failed internally (no content returned)" in response_data["error"]
    mock_logic.generate_summary.assert_awaited_once()

# TODO: Add tests for input validation if not fully covered by Pydantic/FastAPI