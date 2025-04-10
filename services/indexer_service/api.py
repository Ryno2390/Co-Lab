from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List # Added List

# Import the background processing function
from . import processing
# Import the search logic function
from . import logic
# Import models from the main data_layer. Assumes monorepo structure.
try:
    from ...data_layer.indexer_client import IndexerQuery, IndexerResult, DocumentInfo
except ImportError:
    # Fallback basic models if import fails (e.g., if run standalone)
    print("Warning: Could not import models from data_layer. Using basic definitions.")
    class DocumentInfo(BaseModel): cid: str; score: Optional[float] = None; metadata: Optional[Dict[str, Any]] = None; snippet: Optional[str] = None
    class IndexerQuery(BaseModel): query_text: Optional[str] = None; query_vector: Optional[List[float]] = None; keywords: Optional[List[str]] = None; metadata_filter: Optional[Dict[str, Any]] = None; top_k: int = 5
    class IndexerResult(BaseModel): query: IndexerQuery; results: List[DocumentInfo] = Field(default_factory=list); status: str = Field(default="success"); error_message: Optional[str] = None

router = APIRouter()

# --- Request Model (Announcement) ---

class AnnouncementPayload(BaseModel):
    cid: str = Field(..., description="IPFS Content Identifier of the newly uploaded content.")
    uploader_id: Optional[str] = Field(None, description="Identifier of the user who uploaded the content.")
    timestamp: Optional[str] = Field(None, description="Timestamp of the upload event.") # Consider using datetime
    user_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata provided by the user during upload.")

# --- Authentication Dependency (Placeholder) ---

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Placeholder dependency to verify the internal API key."""
    # TODO: Replace with actual key check against settings.INTERNAL_API_KEY
    if not x_api_key or x_api_key != "change-this-in-production": # Placeholder check
        print("Warning: Invalid or missing X-API-Key.")
        # Allow for now during development without enforcing key
        # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
        pass
    return x_api_key

# --- API Endpoints ---

@router.post(
    "/announce",
    summary="Announce New IPFS Content",
    description="Receives notification about new content added to IPFS and queues it for indexing.",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)] # Enable dependency injection for auth
)
async def announce_new_content(
    payload: AnnouncementPayload,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint to receive announcements and queue CIDs for processing.
    """
    print(f"Received announcement for CID: {payload.cid}")
    if not payload.cid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CID is required.")

    # Add the processing task to the background
    background_tasks.add_task(processing.process_cid, payload.cid, payload.user_metadata)
    print(f"Added CID {payload.cid} to background processing queue.")

    return {"message": "Announcement received and queued for processing."}


@router.post(
    "/query",
    response_model=IndexerResult,
    summary="Query Indexed Content",
    description="Searches the indexed IPFS data using keywords, semantic vectors, and metadata filters.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)] # Secure this endpoint too
)
async def query_index(query: IndexerQuery) -> IndexerResult:
    """
    Endpoint to handle search queries against the index.
    """
    print(f"Received index query: text='{query.query_text[:50] if query.query_text else None}', "
          f"keywords={query.keywords}, filter={query.metadata_filter}, top_k={query.top_k}")

    try:
        # Call the core logic function from logic.py
        result: IndexerResult = await logic.perform_search(query)
        return result

    except Exception as e:
        print(f"Error during index query processing: {e}")
        # Return an IndexerResult with error status
        return IndexerResult(query=query, status="error", error_message=f"Query failed unexpectedly: {e}")

# Removed asyncio import as simulation is removed