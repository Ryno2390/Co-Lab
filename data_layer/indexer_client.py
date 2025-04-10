import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import httpx # Import httpx

from ..config import settings # Import settings

# --- Placeholder Models for Query/Result ---
# (Models DocumentInfo, IndexerQuery, IndexerResult remain the same)
class DocumentInfo(BaseModel):
    """Represents information about an indexed document."""
    cid: str = Field(..., description="IPFS Content Identifier")
    score: Optional[float] = Field(None, description="Relevance score from the search")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Stored metadata associated with the CID")
    snippet: Optional[str] = Field(None, description="A relevant snippet from the document content (optional)")

class IndexerQuery(BaseModel):
    """Represents a query to the Indexer."""
    query_text: Optional[str] = Field(None, description="Natural language query for semantic search")
    query_vector: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    keywords: Optional[List[str]] = Field(None, description="Keywords for keyword search")
    metadata_filter: Optional[Dict[str, Any]] = Field(None, description="Filter based on document metadata (e.g., {'tags': 'finance'})")
    top_k: int = Field(default=5, description="Number of results to return")
    # Add other potential fields like date range filters, etc.

class IndexerResult(BaseModel):
    """Represents the result from an Indexer query."""
    query: IndexerQuery
    results: List[DocumentInfo] = Field(default_factory=list)
    status: str = Field(default="success")
    error_message: Optional[str] = None


# --- Client Function ---

# Get Indexer API URL from settings
# TODO: Add INDEXER_API_URL to config/settings.py and .env file
INDEXER_API_URL = getattr(settings, "INDEXER_API_URL", "http://localhost:8010") + "/query" # Example URL + endpoint

DEFAULT_TIMEOUT = 30.0

async def query_indexer(query: IndexerQuery) -> IndexerResult:
    """
    Queries the Indexer API via HTTP to find relevant document CIDs.

    Args:
        query: An IndexerQuery object specifying the search criteria.

    Returns:
        An IndexerResult object containing the found documents.
    """
    print(f"Querying Indexer API at {INDEXER_API_URL}:")
    if query.query_text: print(f"  Text: '{query.query_text[:50]}...'")
    if query.keywords: print(f"  Keywords: {query.keywords}")
    if query.metadata_filter: print(f"  Filter: {query.metadata_filter}")
    print(f"  Top K: {query.top_k}")

    try:
        async with httpx.AsyncClient() as client:
            # TODO: Add internal API Key authentication header from settings if needed
            # headers = {"X-API-Key": settings.INTERNAL_API_KEY}
            headers = {} # Placeholder
            # Use model_dump() for Pydantic v2+ to serialize the query model
            response = await client.post(
                INDEXER_API_URL,
                json=query.model_dump(exclude_none=True), # Send non-None fields
                timeout=DEFAULT_TIMEOUT,
                headers=headers
            )
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            result_data = response.json()
            # Assuming the API returns data compatible with IndexerResult structure
            # It might just return the list of results, requiring construction here
            # Example: Assuming API returns {"results": [...], "status": "success"}
            if "results" in result_data and isinstance(result_data["results"], list):
                 validated_result = IndexerResult(
                     query=query, # Echo the original query
                     results=[DocumentInfo.model_validate(doc) for doc in result_data["results"]],
                     status=result_data.get("status", "success")
                 )
                 print(f"  Received {len(validated_result.results)} results from Indexer.")
                 return validated_result
            else:
                 raise ValueError("Invalid response structure from Indexer API")

    except httpx.HTTPStatusError as e:
        error_message = f"HTTP error querying Indexer: {e.response.status_code} - {e.response.text}"
        print(error_message)
        return IndexerResult(query=query, status="error", error_message=error_message)
    except httpx.RequestError as e:
        error_message = f"Network error querying Indexer: {e}"
        print(error_message)
        return IndexerResult(query=query, status="error", error_message=error_message)
    except Exception as e:
        error_message = f"Unexpected error querying Indexer: {e}"
        print(error_message)
        return IndexerResult(query=query, status="error", error_message=error_message)