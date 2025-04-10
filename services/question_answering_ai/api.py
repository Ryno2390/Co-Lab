from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Any

# Import the core logic function
from . import logic

router = APIRouter()

# --- Request/Response Models ---

class QARequest(BaseModel):
    question: str = Field(..., description="The specific question to be answered.")
    # Removed context_cids - the service will find context via indexer
    # Optional parameters to potentially guide context retrieval could be added later
    # e.g., search_keywords: Optional[List[str]] = None
    # e.g., top_k_context: int = 3

class QAResponse(BaseModel):
    answer: str | None = Field(None, description="The generated answer to the question.")
    error: str | None = Field(None, description="Error message if answering failed.")
    # Optional: Could include source CIDs/snippets used for the answer

# --- API Endpoint ---

@router.post(
    "/invoke",
    response_model=QAResponse,
    summary="Answer Question using Indexed Context",
    description="Answers a specific question by retrieving relevant context from the index and using an LLM.",
    status_code=status.HTTP_200_OK,
)
async def invoke_qa(request: QARequest) -> QAResponse:
    """
    Handles requests to the Question Answering Sub-AI using RAG.
    """
    print(f"Received QA request: question='{request.question[:50]}...'")
    # Removed check for context_cids

    try:
        # Call the core logic function from logic.py (now only needs question)
        answer_text = await logic.answer_question(
            question=request.question
            # Pass other optional params like top_k_context if added to request/logic
        )

        if answer_text is not None:
            return QAResponse(answer=answer_text)
        else:
             # Handle cases where logic returns None without raising an exception
             return QAResponse(error="Question answering failed internally (no answer returned).")

    except ConnectionError as e:
         print(f"Connection error during QA: {e}")
         return QAResponse(error=f"Connection error: {e}")
    # FileNotFoundError might still occur if IPFS fetch fails *within* logic.py
    except FileNotFoundError as e:
         print(f"File not found error during QA context fetch: {e}")
         return QAResponse(error=f"Context content not found: {e}")
    except ValueError as e: # E.g., if context isn't text or other logic error
         print(f"Value error during QA: {e}")
         return QAResponse(error=f"Input, context, or processing error: {e}")
    except Exception as e:
        # Catch-all for other unexpected errors from logic.py
        print(f"Unexpected error during QA logic: {e}")
        return QAResponse(error=f"Question answering failed unexpectedly: {e}")