from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Any

# Import the core logic function
from . import logic

router = APIRouter()

# --- Request/Response Models ---

class CodeGenRequest(BaseModel):
    instruction: str = Field(..., description="Natural language instruction describing the code to generate.")
    # Optional parameters for code generation
    language: Optional[str] = Field(None, description="Optional target programming language (e.g., 'python', 'javascript').")
    context_cids: Optional[list[str]] = Field(None, description="Optional list of IPFS CIDs providing context (e.g., related code files).")
    # Add other parameters like style guidelines, etc.

class CodeGenResponse(BaseModel):
    content: str | None = Field(None, description="The generated code snippet.")
    language_detected: Optional[str] = Field(None, description="The language detected or used for generation.")
    error: str | None = Field(None, description="Error message if code generation failed.")

# --- API Endpoint ---

@router.post(
    "/invoke",
    response_model=CodeGenResponse,
    summary="Generate Code Snippet",
    description="Receives a natural language instruction and generates code.",
    status_code=status.HTTP_200_OK,
)
async def invoke_code_generation(request: CodeGenRequest) -> CodeGenResponse:
    """
    Handles requests to the code generation Sub-AI.
    """
    print(f"Received code gen request: instruction='{request.instruction[:50]}...', lang='{request.language}'")
    try:
        # Call the core logic function from logic.py
        generated_code, detected_lang = await logic.generate_code(
            instruction=request.instruction,
            language=request.language,
            context_cids=request.context_cids
        )

        if generated_code is not None:
            return CodeGenResponse(content=generated_code, language_detected=detected_lang)
        else:
             # Handle cases where logic returns None without raising an exception
             return CodeGenResponse(error="Code generation failed internally (no content returned).")

    except ConnectionError as e:
         print(f"Connection error during code generation: {e}")
         return CodeGenResponse(error=f"Connection error: {e}")
    except FileNotFoundError as e: # If logic.py tries to fetch context CIDs
         print(f"File not found error during code generation: {e}")
         return CodeGenResponse(error=f"Context content not found: {e}")
    except ValueError as e:
         print(f"Value error during code generation: {e}")
         return CodeGenResponse(error=f"Input error: {e}")
    except Exception as e:
        # Catch-all for other unexpected errors from logic.py
        print(f"Unexpected error during code generation logic: {e}")
        # Return error in the response body
        return CodeGenResponse(error=f"Code generation failed unexpectedly: {e}")

# Removed asyncio import as simulation is removed