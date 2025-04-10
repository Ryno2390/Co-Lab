from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Any

# Import the core logic function
from . import logic

router = APIRouter()

# --- Request/Response Models ---

class SummarizationRequest(BaseModel):
    instruction: str = Field(..., description="Instruction containing text to summarize or CID pointing to content.")
    # Optional parameters for summarization
    cid: Optional[str] = Field(None, description="Optional IPFS CID if instruction refers to IPFS content.")
    max_length: Optional[int] = Field(None, description="Optional max length for the summary.")
    # Add other parameters like summary style, etc.

class SummarizationResponse(BaseModel):
    content: str | None = Field(None, description="The generated summary text.")
    error: str | None = Field(None, description="Error message if summarization failed.")

# --- API Endpoint ---

@router.post(
    "/invoke",
    response_model=SummarizationResponse,
    summary="Generate a summary",
    description="Receives text or an IPFS CID and generates a summary.",
    status_code=status.HTTP_200_OK,
)
async def invoke_summarization(request: SummarizationRequest) -> SummarizationResponse:
    """
    Handles requests to the summarization Sub-AI.
    """
    print(f"Received summarization request: instruction='{request.instruction[:50]}...', cid='{request.cid}'")
    try:
        # Call the core logic function from logic.py
        summary_text = await logic.generate_summary(
            instruction=request.instruction,
            cid=request.cid,
            max_length=request.max_length
        )

        if summary_text is not None: # Check if summary was generated (might be empty string)
            return SummarizationResponse(content=summary_text)
        else:
            # Handle cases where logic returns None without raising an exception
             return SummarizationResponse(error="Summary generation failed internally (no content returned).")

    except ConnectionError as e:
         print(f"Connection error during summarization: {e}")
         return SummarizationResponse(error=f"Connection error: {e}")
    except FileNotFoundError as e:
         print(f"File not found error during summarization: {e}")
         return SummarizationResponse(error=f"Content not found: {e}")
    except ValueError as e:
         print(f"Value error during summarization: {e}")
         return SummarizationResponse(error=f"Input error: {e}")
    except Exception as e:
        # Catch-all for other unexpected errors from logic.py
        print(f"Unexpected error during summarization logic: {e}")
        # Return error in the response body
        return SummarizationResponse(error=f"Summarization failed unexpectedly: {e}")

# Removed asyncio import as simulation is removed