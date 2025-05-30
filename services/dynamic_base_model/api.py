from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Any

# Import the core logic function
from . import logic

router = APIRouter()

# --- Request/Response Models ---

class DynamicInvokeRequest(BaseModel):
    prompt: str = Field(..., description="The dynamically constructed prompt for the base LLM.")
    # Optional parameters like temperature, max_tokens could be added

class DynamicInvokeResponse(BaseModel):
    content: Any | None = Field(None, description="The content generated by the base LLM (can be text, JSON, etc.).")
    error: str | None = Field(None, description="Error message if generation failed.")

# --- API Endpoint ---

@router.post(
    "/invoke",
    response_model=DynamicInvokeResponse,
    summary="Invoke Dynamic Base Model",
    description="Receives a dynamically constructed prompt and executes it using a general-purpose base LLM.",
    status_code=status.HTTP_200_OK,
)
async def invoke_dynamic_model(request: DynamicInvokeRequest) -> DynamicInvokeResponse:
    """
    Handles requests to the dynamic base model service.
    """
    print(f"Received dynamic invoke request: prompt='{request.prompt[:100]}...'") # Log truncated prompt
    try:
        # Call the core logic function from logic.py
        generated_content = await logic.run_dynamic_prompt(
            prompt=request.prompt
        )

        if generated_content is not None:
             # Content can be complex (JSON, text, etc.)
            return DynamicInvokeResponse(content=generated_content)
        else:
             # Handle cases where logic returns None without raising an exception
             return DynamicInvokeResponse(error="Dynamic model execution failed internally (no content returned).")

    except ConnectionError as e:
         print(f"Connection error during dynamic model invocation: {e}")
         return DynamicInvokeResponse(error=f"Connection error: {e}")
    except Exception as e:
        # Catch-all for other unexpected errors from logic.py
        print(f"Unexpected error during dynamic model invocation logic: {e}")
        # Return error in the response body
        return DynamicInvokeResponse(error=f"Dynamic model invocation failed unexpectedly: {e}")

# Removed asyncio import as simulation is removed