from fastapi import APIRouter, HTTPException, status
from ...core_ai.orchestrator import process_user_prompt
from ...core_ai.models import UserInput, FinalResponse

router = APIRouter()

@router.post(
    "/prompt",
    response_model=FinalResponse,
    summary="Process a user prompt",
    description="Receives a user prompt, orchestrates the decomposition, routing, Sub-AI execution, and synthesis process, returning the final response.",
    status_code=status.HTTP_200_OK,
)
async def handle_prompt(user_input: UserInput) -> FinalResponse:
    """
    Endpoint to handle incoming user prompts.
    """
    try:
        final_response = await process_user_prompt(user_input)
        if final_response.status == "error":
            # You might want more specific error handling/status codes based on the error type
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=final_response.error_message or "An internal error occurred during processing."
            )
        return final_response
    except HTTPException as http_exc:
        # Re-raise HTTPException to let FastAPI handle it
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors during orchestration
        print(f"Unexpected API error for session {user_input.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )