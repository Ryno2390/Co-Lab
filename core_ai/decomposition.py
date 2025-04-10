import json
from typing import List
from openai import AsyncOpenAI # Use AsyncOpenAI for non-blocking calls
import pydantic

from .models import SubTask
from ..config import settings # To get API keys, etc.

# Initialize the Async OpenAI client
# Ensure OPENAI_API_KEY is set in your environment or .env file
# loaded by settings.py
try:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Note: For Anthropic, you'd use:
    # from anthropic import AsyncAnthropic
    # client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) # Assuming key is in settings
except Exception as e:
    print(f"Error initializing LLM client: {e}. Make sure API key is set.")
    client = None

# Define a Pydantic model for the expected JSON structure from the LLM
class DecomposedTasksResponse(BaseModel):
    sub_tasks: List[SubTask]

async def decompose_prompt(prompt_text: str) -> List[SubTask]:
    """
    Uses the configured Decomposer LLM API to decompose a user prompt into sub-tasks.

    Args:
        prompt_text: The user's natural language prompt.

    Returns:
        A list of SubTask objects.

    Raises:
        Exception: If the API call fails or the response is invalid.
    """
    if not client:
        raise Exception("LLM Client not initialized. Check API key configuration.")

    system_prompt = """
You are a task decomposition agent. Analyze the following user request and break it down into distinct,
self-contained sub-tasks that require specialized knowledge or actions. For each sub-task, formulate a clear instruction.
Output the results ONLY as a valid JSON object containing a single key "sub_tasks", which is a list of objects,
where each object has an "instruction" key with the sub-task description. Example:
{"sub_tasks": [{"instruction": "Sub-task 1 description"}, {"instruction": "Sub-task 2 description"}]}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_text}
    ]

    try:
        print(f"Sending prompt to Decomposer LLM: '{prompt_text[:100]}...'")
        # Using OpenAI's chat completions endpoint with JSON mode
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", # Or another suitable model like gpt-4o-mini, claude-3-haiku-20240307
            messages=messages,
            response_format={"type": "json_object"}, # Enforce JSON output
            temperature=0.2, # Lower temperature for more deterministic decomposition
        )

        response_content = response.choices[0].message.content
        print(f"Received raw response from Decomposer LLM: {response_content}")

        # Parse and validate the JSON response using Pydantic
        try:
            # The response content should be a JSON string
            parsed_json = json.loads(response_content)
            validated_response = DecomposedTasksResponse.model_validate(parsed_json)
            print(f"Successfully decomposed into {len(validated_response.sub_tasks)} sub-tasks.")
            return validated_response.sub_tasks
        except json.JSONDecodeError as json_err:
            print(f"Error decoding LLM JSON response: {json_err}")
            print(f"Raw response was: {response_content}")
            raise Exception(f"Failed to decode JSON from LLM: {json_err}")
        except pydantic.ValidationError as val_err:
            print(f"Error validating LLM response structure: {val_err}")
            print(f"Raw response was: {response_content}")
            raise Exception(f"Invalid response structure from LLM: {val_err}")

    except Exception as e:
        print(f"Error calling Decomposer LLM API: {e}")
        # Re-raise the exception to be handled by the orchestrator
        raise Exception(f"Decomposer LLM API call failed: {e}")