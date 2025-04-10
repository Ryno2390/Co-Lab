from typing import Optional
import httpx # Needed if calling LLM API directly, or use specific client like openai
from openai import AsyncOpenAI # Example using OpenAI

# Import the IPFS client from the main data_layer
# This assumes a monorepo structure or that the Co-Lab package is installed
try:
    from ...data_layer import ipfs_client
except ImportError:
    print("Warning: Could not import ipfs_client. IPFS fetching will not work.")
    ipfs_client = None

# Import settings, potentially shared or service-specific
try:
    from ...config import settings
    # Initialize LLM client (reuse or create new)
    llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Choose a model suitable for summarization
    SUMMARY_MODEL = "gpt-3.5-turbo" # Example, could be configurable
except ImportError:
     print("Warning: Could not import main settings. Using fallback LLM client init.")
     # Fallback if running standalone or settings not found
     import os
     llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
     SUMMARY_MODEL = "gpt-3.5-turbo"
except Exception as e:
    print(f"Error initializing LLM client for summarization: {e}")
    llm_client = None


async def generate_summary(
    instruction: str,
    cid: Optional[str] = None,
    max_length: Optional[int] = None
) -> Optional[str]:
    """
    Generates a summary for the given instruction, potentially fetching content from IPFS.

    Args:
        instruction: Original instruction (may contain text if no CID).
        cid: Optional IPFS CID of the content to summarize.
        max_length: Optional desired maximum length of the summary (in tokens or words - depends on prompt).

    Returns:
        The generated summary string, or None if an error occurs.
    """
    text_to_summarize: Optional[str] = None

    # 1. Get content to summarize
    if cid:
        if not ipfs_client or not ipfs_client.client:
            print(f"Error: IPFS client not available, cannot fetch CID {cid}")
            raise ConnectionError(f"IPFS client not available to fetch CID {cid}")
        try:
            print(f"Fetching content from IPFS for CID: {cid}")
            content_bytes = await ipfs_client.get_ipfs_content(cid)
            if content_bytes:
                # Attempt to decode as UTF-8, handle potential errors
                try:
                    text_to_summarize = content_bytes.decode('utf-8')
                    print(f"Successfully decoded {len(text_to_summarize)} chars from CID {cid}")
                except UnicodeDecodeError:
                    print(f"Error: Could not decode content from CID {cid} as UTF-8.")
                    raise ValueError(f"Content for CID {cid} is not valid UTF-8 text.")
            else:
                raise FileNotFoundError(f"Content for CID {cid} not found or fetch failed.")
        except Exception as e:
            print(f"Error fetching or decoding IPFS content for CID {cid}: {e}")
            raise e # Re-raise to be caught by the API endpoint handler
    else:
        # Assume the instruction itself contains the text if no CID is provided
        # Basic check: is the instruction reasonably long enough to be summarized?
        if len(instruction) > 50: # Arbitrary threshold
             text_to_summarize = instruction
             print("Using instruction text directly for summarization.")
        else:
            raise ValueError("Instruction too short to summarize and no CID provided.")

    if not text_to_summarize:
        # Should have been caught above, but as a safeguard
        raise ValueError("No text available to summarize.")

    # 2. Call LLM for summarization
    if not llm_client:
        print("Error: LLM client not initialized for summarization.")
        raise ConnectionError("LLM client not available for summarization.")

    system_prompt = "You are an expert summarization AI. Generate a concise summary of the following text."
    user_prompt = f"Please summarize the following text:"
    if max_length:
        user_prompt += f" Keep the summary concise, ideally around {max_length} words." # Adjust prompt based on how max_length is interpreted
    user_prompt += f"\n\nTEXT:\n\"\"\"\n{text_to_summarize[:15000]}\n\"\"\"" # Limit input length to avoid excessive costs/context limits

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        print(f"Sending text (first 100 chars: '{text_to_summarize[:100]}...') to LLM for summarization.")
        response = await llm_client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=messages,
            temperature=0.3, # Lower temperature for factual summary
            # max_tokens can be set based on max_length if needed
        )
        summary = response.choices[0].message.content
        print("Successfully received summary from LLM.")
        return summary.strip() if summary else None

    except Exception as e:
        print(f"Error calling LLM API for summarization: {e}")
        raise Exception(f"LLM API call failed during summarization: {e}")