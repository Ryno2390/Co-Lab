from fastapi import APIRouter, HTTPException, status, File, UploadFile, Form, Depends
from pydantic import BaseModel, Field, Json
from typing import Optional, List, Dict, Any

# Import the core logic function
from . import logic
# We might need settings for API key validation if uploads require auth
# from ...config import settings

router = APIRouter()

# --- Request/Response Models ---

class UploadResponse(BaseModel):
    message: str
    cid: Optional[str] = None
    reward_amount: Optional[float] = None
    error: Optional[str] = None

# --- API Endpoint ---

@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload File to IPFS",
    description="Uploads a file, adds it to IPFS, triggers indexing, and potentially rewards the user.",
    # Consider appropriate success status code (200 OK, 201 Created, 202 Accepted)
    status_code=status.HTTP_200_OK,
)
async def upload_file(
    # File upload part
    file: UploadFile = File(..., description="The file to upload."),
    # Metadata part - received as form fields
    user_id: str = Form(..., description="Identifier of the user uploading the file."),
    description: Optional[str] = Form(None, description="Description of the file content."),
    tags_json: Optional[str] = Form(None, description="JSON string representing a list of tags (e.g., '[\"llm\", \"research\"]')"),
    # Add other metadata fields as needed
):
    """
    Handles file uploads, pinning to IPFS, and triggering downstream processes.
    """
    print(f"Received upload request for file: {file.filename}, user: {user_id}")
    content_bytes: bytes
    try:
        content_bytes = await file.read()
        file_size_bytes = len(content_bytes)
        print(f"File size: {file_size_bytes} bytes")
    except Exception as e:
         print(f"Error reading uploaded file: {e}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error reading file: {e}")
    finally:
        await file.close() # Ensure file handle is closed

    # Parse metadata
    user_metadata = {
        "filename": file.filename,
        "content_type": file.content_type,
        "description": description,
        "tags": []
    }
    if tags_json:
        try:
            # Use Pydantic's Json type for validation within the endpoint
            tags_list = Json[List[str]](tags_json)
            user_metadata["tags"] = tags_list
        except Exception as e:
            print(f"Warning: Could not parse tags_json: {e}")
            # Optionally raise HTTPException for invalid metadata format
            # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid format for tags_json: {e}")

    try:
        # Call the core logic function from logic.py
        result = await logic.handle_upload(
            user_id=user_id,
            content_bytes=content_bytes,
            user_metadata=user_metadata
        )

        if result.get("error"):
             # Handle errors reported by the logic layer - return 500 for internal processing errors
             # Consider mapping specific logic errors to different HTTP status codes if needed
             return UploadResponse(
                 message="Upload processing failed.",
                 error=result["error"]
             )
             # Or: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["error"])

        # Success case
        return UploadResponse(
            message="File uploaded and processing initiated successfully.",
            cid=result.get("cid"),
            reward_amount=result.get("reward_amount")
        )

    except HTTPException as http_exc:
        raise http_exc # Re-raise FastAPI exceptions
    except Exception as e:
        # Catch any other unexpected errors during processing
        print(f"Unexpected error during file upload processing: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload processing failed unexpectedly: {e}")

# Removed asyncio import as simulation is removed