from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

# Import the core logic function
from . import logic

router = APIRouter()

# --- Request/Response Models ---

class DataAnalysisRequest(BaseModel):
    instruction: str = Field(..., description="Natural language instruction describing the analysis to perform.")
    context_cids: List[str] = Field(..., description="List of IPFS CIDs pointing to structured data (e.g., CSV, JSON).")
    # Optional parameters like output format hint ('json', 'text', 'plot_description')
    output_format_hint: Optional[str] = None

class DataAnalysisResponse(BaseModel):
    result: Any | None = Field(None, description="The result of the data analysis (can be JSON, text, etc.).")
    result_type: Optional[str] = Field(None, description="Indicates the type of result (e.g., 'table', 'statistics', 'text_summary', 'plot_data').")
    error: str | None = Field(None, description="Error message if analysis failed.")

# --- API Endpoint ---

@router.post(
    "/invoke",
    response_model=DataAnalysisResponse,
    summary="Analyze Structured Data from IPFS",
    description="Performs data analysis based on instructions and structured data retrieved from IPFS CIDs.",
    status_code=status.HTTP_200_OK,
)
async def invoke_data_analysis(request: DataAnalysisRequest) -> DataAnalysisResponse:
    """
    Handles requests to the Data Analysis Sub-AI.
    """
    print(f"Received data analysis request: instruction='{request.instruction[:50]}...', cids='{request.context_cids}'")
    if not request.context_cids:
         return DataAnalysisResponse(error="At least one context CID is required.")

    try:
        # Call the core logic function from logic.py
        analysis_result, result_type = await logic.analyze_data(
            instruction=request.instruction,
            context_cids=request.context_cids,
            output_format_hint=request.output_format_hint
        )

        if analysis_result is not None:
            return DataAnalysisResponse(result=analysis_result, result_type=result_type)
        else:
             # Handle cases where logic returns None without raising an exception
             # (logic.py currently raises exceptions for major failures, but could return None)
             return DataAnalysisResponse(error="Data analysis failed internally (no result returned).")

    except ConnectionError as e:
         print(f"Connection error during data analysis: {e}")
         return DataAnalysisResponse(error=f"Connection error: {e}")
    except FileNotFoundError as e: # If logic.py tries to fetch context CIDs
         print(f"File not found error during data analysis: {e}")
         return DataAnalysisResponse(error=f"Context data not found: {e}")
    except ValueError as e: # E.g., if data isn't parsable CSV/JSON or other logic error
         print(f"Value error during data analysis: {e}")
         return DataAnalysisResponse(error=f"Input, data format, or analysis error: {e}")
    except Exception as e:
        # Catch-all for other unexpected errors from logic.py
        print(f"Unexpected error during data analysis logic: {e}")
        return DataAnalysisResponse(error=f"Data analysis failed unexpectedly: {e}")

# Removed asyncio import as simulation is removed