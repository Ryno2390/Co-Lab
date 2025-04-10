from typing import List, Any
from .models import UserInput, SubTask, SubAIResponse, FinalResponse
from .decomposition import decompose_prompt
from .routing import route_sub_tasks, RoutingDecision
from ..sub_ai.client import invoke_sub_ai
from .synthesis import synthesize_responses
# Import tokenomics service functions
from ..tokenomics.service import calculate_query_cost, charge_user_for_query
# from ..config import settings # Example for accessing settings

import asyncio

async def process_user_prompt(user_input: UserInput) -> FinalResponse:
    """
    Main orchestration function for processing a user prompt through the Co-Lab pipeline.
    Includes cost calculation and charging the user.

    Args:
        user_input: The UserInput object containing the prompt and session info.

    Returns:
        A FinalResponse object containing the synthesized answer or an error.
    """
    print(f"Received prompt for session {user_input.session_id}: {user_input.prompt}")
    # Check for user_id early if charging is mandatory
    if not user_input.user_id:
        print(f"Error: user_id is required for charging. Session: {user_input.session_id}")
        return FinalResponse(
            session_id=user_input.session_id,
            original_prompt=user_input.prompt,
            synthesized_answer="",
            status="error",
            error_message="User ID not provided, cannot process chargeable request."
        )

    sub_tasks: List[SubTask] = []
    sub_ai_responses: List[SubAIResponse] = []

    try:
        # 1. Decomposition
        sub_tasks = await decompose_prompt(user_input.prompt)
        print(f"Decomposed into {len(sub_tasks)} sub-tasks.")
        if not sub_tasks:
             print(f"Warning: Decomposition returned no sub-tasks for prompt: {user_input.prompt}")
             return FinalResponse(
                 session_id=user_input.session_id,
                 original_prompt=user_input.prompt,
                 synthesized_answer="Could not decompose the prompt into actionable tasks.",
                 status="success_empty"
             )

        # 2. Routing
        routing_decisions: List[RoutingDecision] = await route_sub_tasks(sub_tasks)
        print(f"Generated {len(routing_decisions)} routing decisions.")

        # 3. Cost Calculation & Charging
        query_cost = calculate_query_cost(routing_decisions)
        print(f"Calculated query cost: {query_cost} COLAB for user {user_input.user_id}")

        charge_successful = await charge_user_for_query(user_input.user_id, query_cost)
        if not charge_successful:
            # Handle insufficient funds or other charging errors
            print(f"Charging failed for user {user_input.user_id}. Aborting.")
            return FinalResponse(
                session_id=user_input.session_id,
                original_prompt=user_input.prompt,
                synthesized_answer="",
                status="error_charge_failed",
                error_message="Failed to charge for query (e.g., insufficient funds)."
                # Optionally include cost: "metadata": {"cost": query_cost}
            )
        print(f"Successfully charged user {user_input.user_id} {query_cost} COLAB.")

        # 4. Sub-AI Invocation (Only proceed if charge was successful)
        invocation_tasks = [invoke_sub_ai(decision) for decision in routing_decisions]
        sub_ai_responses = await asyncio.gather(*invocation_tasks)
        print(f"Received {len(sub_ai_responses)} responses from Sub-AIs (via client).")

        successful_responses = [res for res in sub_ai_responses if res and res.status == "success"]
        print(f"Number of successful Sub-AI responses: {len(successful_responses)}")
        if not successful_responses:
             # If all invocations failed after successful charge, maybe refund or just report error?
             # For now, report error. Refunding logic could be added later.
             raise Exception("All Sub-AI invocations failed after successful charge.")

        # 5. Synthesis
        final_answer_text: str = await synthesize_responses(
            original_prompt=user_input.prompt,
            sub_tasks=sub_tasks,
            sub_ai_responses=successful_responses
        )

        # 6. Construct Final Response
        final_response = FinalResponse(
            session_id=user_input.session_id,
            original_prompt=user_input.prompt,
            synthesized_answer=final_answer_text,
            status="success" # Consider 'partial_success' if some sub-tasks failed but synthesis worked
        )
        print(f"Successfully generated final response for session {user_input.session_id}")

    except Exception as e:
        print(f"Error processing prompt for session {user_input.session_id}: {e}")
        # Basic error handling
        final_response = FinalResponse(
            session_id=user_input.session_id,
            original_prompt=user_input.prompt,
            synthesized_answer="",
            status="error",
            error_message=str(e)
        )

    return final_response