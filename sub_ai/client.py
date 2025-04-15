import asyncio
from typing import Any, Optional
import httpx # Import httpx
import numpy as np
# from scipy.linalg import svd # Import if/when SVD is implemented
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

            # --- Transformer Squared: Pass 2 - Model Adaptation ---
            adapted_model_instance = None # Placeholder for the adapted model
            if decision.task_category:
                print(f"Task category '{decision.task_category}' detected. Attempting SVF adaptation.")

                # Placeholder Step 1: Retrieve SVF Vector (z)
                # TODO: Implement get_svf_vector function
                # def get_svf_vector(category: str) -> Optional[np.ndarray]:
                #     # Logic to load/fetch the pre-trained SVF vector for the category
                #     # Example: Load from a file, database, or model registry
                #     print(f"Placeholder: Retrieving SVF vector for category '{category}'")
                #     # Return np.random.rand(vector_dimension) # Example return
                #     return None # Placeholder return
                # svf_vector_z = get_svf_vector(decision.task_category)
                svf_vector_z = None # Placeholder value

                if svf_vector_z is not None:
                    print("Placeholder: SVF vector retrieved. Proceeding with adaptation.")
                    # Placeholder Step 2: Apply SVF Adaptation
                    # TODO: Implement the actual model adaptation logic
                    # 1. Identify the target model instance (e.g., load the base model)
                    #    target_model = load_model(endpoint or "DynamicBaseModel") # Hypothetical
                    # 2. Identify target weight matrices (W) within the model
                    #    target_layers = ['attention.query', 'attention.key', 'mlp.fc1'] # Example layers
                    # 3. For each target weight matrix W:
                    #    a. Perform SVD: U, S, Vt = svd(W, full_matrices=False) # Using scipy.linalg.svd
                    #    b. Create diagonal matrix from SVF vector: Z_diag = np.diag(svf_vector_z)
                    #       (Ensure dimensions match S. May need padding/truncation)
                    #    c. Calculate adapted singular values: S_adapted = S * Z_diag # Element-wise if Z_diag is vector, or matrix mul if diagonal
                    #    d. Reconstruct adapted weights: W_prime = U @ np.diag(S_adapted) @ Vt # Or U @ (S_adapted_matrix) @ Vt
                    #    e. Update the model in memory with W_prime
                    #       set_model_weight(target_model, layer_name, W_prime) # Hypothetical
                    # adapted_model_instance = target_model # Assign the adapted model
                    print("Placeholder: SVF adaptation applied to model weights.")

                    # Placeholder Step 3: Invoke Adapted Model
                    # The subsequent HTTP call should ideally use the adapted_model_instance
                    # This might involve:
                    # - A different endpoint/method for adapted models.
                    # - Serializing adapted weights and sending them.
                    # - Assuming the current endpoint can handle an adapted model state (if state is managed server-side).
                    # For now, we'll just note that the call below *should* use the adapted model.
                    print("Placeholder: Proceeding to invoke the *adapted* model.")

                else:
                    print("Placeholder: SVF vector not found or adaptation failed. Using original model.")
            else:
                print("No task category provided. Using original model.")
            # --- End Model Adaptation ---

            # If adaptation was successful and modified the model in memory,
            # the existing call below might implicitly use it.
            # If adaptation requires a different call/endpoint, modify the logic here.

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

            # --- Transformer Squared: Post-Inference ---
            # Placeholder Step 4: Revert Weights (Optional)
            # If the adaptation was temporary for this request, revert weights here.
            # TODO: Implement weight reversion if needed
            # if adapted_model_instance and svf_vector_z is not None:
            #     print("Placeholder: Reverting model weights to original state.")
            #     # Logic to restore original weights to the model instance
            # --- End Post-Inference ---

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
