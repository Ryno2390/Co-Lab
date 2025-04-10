import asyncio
from typing import Any
import httpx # Import httpx
# Assuming RoutingDecision is defined in core_ai.routing
# Adjust import path if structure changes
from ..core_ai.routing import RoutingDecision
from ..core_ai.models import SubAIResponse
from ..config import settings # Import settings to potentially get base URLs or API keys later

# Placeholder for Sub-AI endpoint configuration
# TODO: Move to settings or a dynamic service discovery mechanism
SUB_AI_ENDPOINTS = {
    "CodeGeneration": "http://localhost:8001/invoke", # Example endpoint
    "IPFSSearch": "http://localhost:8002/invoke",     # Example endpoint
    "SummarizationAI": "http://localhost:8004/invoke", # Added example
    "QuestionAnsweringAI": "http://localhost:8005/invoke", # Added example
    "DataAnalysisAI": "http://localhost:8006/invoke", # Added example
    "DynamicBaseModel": "http://localhost:8003/invoke" # Example endpoint for the base model
}
# Define standard timeouts
DEFAULT_TIMEOUT = 60.0
DYNAMIC_TIMEOUT = 120.0

async def invoke_sub_ai(decision: RoutingDecision) -> SubAIResponse:
    """
    Invokes the appropriate Sub-AI via HTTP based on the routing decision.

    Args:
        decision: The RoutingDecision object containing the sub-task and target info.

    Returns:
        A SubAIResponse object.
    """
    sub_task = decision.sub_task
    target_id = decision.target_id # Will be None for dynamic instances initially
    source_id_for_response = "unknown"
    response_content: Any = None
    status = "error" # Default to error
    error_message: str | None = None
    endpoint: str | None = None
    payload: dict = {}
    timeout: float = DEFAULT_TIMEOUT

    try:
        if decision.route_type == 'fixed_specialist' and target_id:
            endpoint = SUB_AI_ENDPOINTS.get(target_id)
            source_id_for_response = target_id
            if not endpoint:
                raise ValueError(f"No endpoint configured for fixed specialist: {target_id}")
            payload = {"instruction": sub_task.instruction}
            timeout = DEFAULT_TIMEOUT
            print(f"Calling FIXED specialist '{target_id}' at {endpoint} for task: {sub_task.sub_task_id}")

        elif decision.route_type == 'dynamic_instance':
            endpoint = SUB_AI_ENDPOINTS.get("DynamicBaseModel")
            source_id_for_response = f"dynamic_instance_{sub_task.sub_task_id}" # Example ID
            if not endpoint:
                raise ValueError("No endpoint configured for DynamicBaseModel")
            # TODO: Construct the dynamic prompt more robustly, potentially including context fetched based on task
            dynamic_prompt = f"Act as an expert and perform the following task: {sub_task.instruction}"
            payload = {"prompt": dynamic_prompt} # Assuming base model takes 'prompt'
            timeout = DYNAMIC_TIMEOUT # Allow longer for potentially complex dynamic tasks
            print(f"Calling DYNAMIC base model at {endpoint} for task: {sub_task.sub_task_id}")

        else:
            raise ValueError(f"Invalid route_type in decision: {decision.route_type}")

        # --- Actual HTTP call ---
        async with httpx.AsyncClient() as client:
            # TODO: Add internal API Key authentication header from settings if needed
            # headers = {"X-API-Key": settings.INTERNAL_API_KEY}
            headers = {} # Placeholder
            response = await client.post(endpoint, json=payload, timeout=timeout, headers=headers)
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            # Assuming the Sub-AI endpoint returns JSON like {"content": ...}
            response_data = response.json()
            response_content = response_data.get("content")
            status = "success"
            print(f"Successful response received from {source_id_for_response} for task {sub_task.sub_task_id}")
        # --- End HTTP call ---

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (e.g., 4xx, 5xx) specifically
        error_message = f"HTTP error calling {source_id_for_response}: {e.response.status_code} - {e.response.text}"
        print(error_message)
    except httpx.RequestError as e:
        # Handle network-related errors (e.g., connection refused, timeout)
        error_message = f"Network error calling {source_id_for_response}: {e}"
        print(error_message)
    except ValueError as e:
        # Handle configuration errors (e.g., missing endpoint)
        error_message = str(e)
        print(error_message)
    except Exception as e:
        # Catch any other unexpected errors
        error_message = f"Unexpected error invoking {source_id_for_response}: {e}"
        print(error_message)
        # Ensure content is None on error
        response_content = None

    return SubAIResponse(
        sub_task_id=sub_task.sub_task_id,
        source_sub_ai_id=source_id_for_response,
        content=response_content,
        status=status,
        error_message=error_message
    )