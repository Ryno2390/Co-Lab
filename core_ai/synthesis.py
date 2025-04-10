from typing import List, Dict, Any
from openai import AsyncOpenAI
import json # For pre-processing JSON content

from .models import SubTask, SubAIResponse
from ..config import settings

# Initialize the Async OpenAI client (can potentially reuse client from decomposition)
# Ensure OPENAI_API_KEY is set in your environment or .env file
try:
    # Consider using a different client instance if different settings are needed
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Choose a powerful model suitable for synthesis
    SYNTHESIS_MODEL = "gpt-4o" # Or "gpt-4-turbo", or Claude 3 Sonnet/Opus via anthropic client
except Exception as e:
    print(f"Error initializing LLM client for synthesis: {e}. Make sure API key is set.")
    client = None

def _preprocess_responses_for_synthesis(
    sub_tasks: List[SubTask],
    sub_ai_responses: List[SubAIResponse]
) -> str:
    """
    Formats the sub-tasks and responses into a string suitable for the synthesis prompt.
    """
    processed_text = "--- Relevant Information from Sub-Tasks ---\n"
    response_map: Dict[str, SubAIResponse] = {res.sub_task_id: res for res in sub_ai_responses}

    for task in sub_tasks:
        processed_text += f"\nSub-Task Instruction: {task.instruction}\n"
        response = response_map.get(task.sub_task_id)
        if response:
            processed_text += f"Source AI: {response.source_sub_ai_id}\n"
            if response.status == "success":
                content = response.content
                # Basic handling to convert dict/list to JSON string for the prompt
                if isinstance(content, (dict, list)):
                    try:
                        content_str = json.dumps(content, indent=2)
                    except TypeError:
                        content_str = str(content) # Fallback
                else:
                    content_str = str(content)
                processed_text += f"Response Content:\n```\n{content_str}\n```\n"
            else:
                processed_text += f"Response Status: {response.status}\n"
                if response.error_message:
                    processed_text += f"Error: {response.error_message}\n"
        else:
            processed_text += "Response: [No response received for this sub-task]\n"

    processed_text += "\n--- End Relevant Information ---\n"
    return processed_text


async def synthesize_responses(
    original_prompt: str,
    sub_tasks: List[SubTask],
    sub_ai_responses: List[SubAIResponse]
) -> str:
    """
    Uses the configured Synthesizer LLM API to generate a final coherent response.

    Args:
        original_prompt: The initial prompt from the user.
        sub_tasks: The list of decomposed sub-tasks.
        sub_ai_responses: The list of responses received from Sub-AIs.

    Returns:
        The synthesized final answer as a string.

    Raises:
        Exception: If the API call fails.
    """
    if not client:
        raise Exception("LLM Client not initialized for synthesis. Check API key configuration.")

    if not sub_ai_responses:
        print("Warning: No Sub-AI responses received for synthesis.")
        # Handle case with no responses - maybe return a specific message
        return "No information could be gathered to answer the prompt."

    # 1. Pre-process responses into a formatted string
    processed_info = _preprocess_responses_for_synthesis(sub_tasks, sub_ai_responses)

    # 2. Construct the synthesis prompt
    system_prompt = """
You are a highly intelligent synthesis AI. Your task is to combine the provided information from various sub-tasks
into a single, coherent, and comprehensive response that directly addresses the original user prompt.
Ensure all aspects of the original prompt are covered. Identify and resolve any contradictions or conflicts
in the information provided by the sub-tasks, prioritizing a unified conclusion where possible. If resolution is
impossible, briefly note the differing perspectives. Consolidate redundant information. Structure the final
response logically with clear explanations. Do NOT simply list the sub-task responses; synthesize them into a
flowing narrative or answer. Do not refer to the sub-tasks or source AIs directly in your final output unless
absolutely necessary for clarity regarding conflicting information.
"""

    final_prompt = f"""
Original User Prompt:
\"\"\"
{original_prompt}
\"\"\"

Relevant Information Gathered from Sub-Tasks:
{processed_info}

Based *only* on the original prompt and the relevant information provided above, generate the final synthesized response:
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": final_prompt}
    ]

    # 3. Call the Synthesizer LLM API
    try:
        print(f"Sending {len(sub_ai_responses)} responses to Synthesizer LLM ({SYNTHESIS_MODEL})...")
        response = await client.chat.completions.create(
            model=SYNTHESIS_MODEL,
            messages=messages,
            temperature=0.5, # Allow for some creativity in synthesis but keep it grounded
            # max_tokens can be set if needed
        )

        synthesized_answer = response.choices[0].message.content
        print("Received synthesized answer from LLM.")
        return synthesized_answer if synthesized_answer else ""

    except Exception as e:
        print(f"Error calling Synthesizer LLM API: {e}")
        raise Exception(f"Synthesizer LLM API call failed: {e}")