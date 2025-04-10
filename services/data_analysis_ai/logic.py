import asyncio
import io
import json
import pandas as pd # Import pandas for data handling
from typing import Optional, List, Any, Dict, Tuple

# Import the IPFS client from the main data_layer
try:
    from ...data_layer import ipfs_client
except ImportError:
    print("Warning: Could not import ipfs_client. IPFS fetching will not work.")
    ipfs_client = None

# Import settings and LLM client
try:
    from ...config import settings
    from openai import AsyncOpenAI
    llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Choose a model capable of data analysis based on text/samples
    ANALYSIS_MODEL = settings.SYNTHESIS_MODEL # Reuse synthesis model (e.g., GPT-4o)
except ImportError:
     print("Warning: Could not import main settings/OpenAI client. Using fallback.")
     import os
     from openai import AsyncOpenAI
     llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
     ANALYSIS_MODEL = "gpt-4o" # Fallback model
except Exception as e:
    print(f"Error initializing LLM client for Data Analysis: {e}")
    llm_client = None


async def fetch_and_parse_data(cid: str) -> Optional[pd.DataFrame | Dict | List]:
    """Helper to fetch IPFS content and parse as CSV or JSON."""
    # ... (fetch_and_parse_data function remains the same) ...
    if not ipfs_client or not ipfs_client.client:
        print(f"IPFS client unavailable, cannot fetch {cid}")
        return None
    try:
        content_bytes = await ipfs_client.get_ipfs_content(cid)
        if not content_bytes:
            print(f"No content found for CID {cid}")
            return None
        try:
            data = json.loads(content_bytes.decode('utf-8'))
            print(f"Parsed CID {cid} as JSON.")
            return data
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                data_file = io.BytesIO(content_bytes)
                df = pd.read_csv(data_file)
                print(f"Parsed CID {cid} as CSV. Shape: {df.shape}")
                return df
            except Exception as csv_e:
                print(f"Could not parse CID {cid} as JSON or CSV: {csv_e}")
                return None
    except Exception as e:
        print(f"Error fetching/parsing CID {cid}: {e}")
        return None


async def analyze_data(
    instruction: str,
    context_cids: List[str],
    output_format_hint: Optional[str] = None # Hint not used in this V1 LLM approach yet
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Performs analysis on structured data fetched from IPFS CIDs using an LLM.

    Args:
        instruction: Natural language instruction for the analysis.
        context_cids: List of IPFS CIDs pointing to structured data.
        output_format_hint: Optional hint for the desired output format (currently unused).

    Returns:
        A tuple containing the analysis result (text summary/result) and result type hint ('llm_analysis_text'),
        or (None, None) if an error occurs.
    """
    print(f"Analyzing data for instruction: '{instruction[:50]}...' using CIDs: {context_cids}")

    if not llm_client:
        print("Error: LLM client not initialized for Data Analysis.")
        raise ConnectionError("LLM client not available for Data Analysis.")

    # 1. Fetch and parse data from IPFS concurrently
    fetch_tasks = [fetch_and_parse_data(cid) for cid in context_cids]
    fetched_data_list = await asyncio.gather(*fetch_tasks)

    parsed_data: Optional[pd.DataFrame | Dict | List] = None
    for data in fetched_data_list:
        if data is not None:
            parsed_data = data
            break # Use the first valid dataset found

    if parsed_data is None:
        print("Error: Could not retrieve or parse valid structured data from any provided CIDs.")
        raise ValueError("Failed to retrieve valid structured data from provided CIDs.")

    # 2. Prepare data sample for LLM prompt
    data_sample_str: str = "[Could not generate data sample]"
    try:
        if isinstance(parsed_data, pd.DataFrame):
            # Provide header and first few rows in markdown format
            # Requires 'tabulate' package: pip install tabulate
            data_sample_str = parsed_data.head().to_markdown(index=False)
        elif isinstance(parsed_data, list):
            # Show first few items (up to a char limit)
            sample = parsed_data[:5]
            data_sample_str = json.dumps(sample, indent=2, default=str)
        elif isinstance(parsed_data, dict):
            # Show dict (up to a char limit)
            data_sample_str = json.dumps(parsed_data, indent=2, default=str)

        # Truncate sample if too long
        MAX_SAMPLE_LEN = 4000
        if len(data_sample_str) > MAX_SAMPLE_LEN:
            data_sample_str = data_sample_str[:MAX_SAMPLE_LEN] + "\n... (data truncated)"

    except Exception as sample_e:
        print(f"Error creating data sample string: {sample_e}")
        data_sample_str = "[Error generating data sample]"


    # 3. Construct LLM Prompt for Analysis
    system_prompt = """You are an expert Data Analysis AI. Analyze the provided data based on the user's instruction.
Provide a clear, concise answer summarizing the findings or the result of the calculation.
If the data sample is insufficient or the instruction is unclear, state that."""

    user_prompt = f"""
Instruction: {instruction}

Data Sample:
```
{data_sample_str}
```

Analysis Result:"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # 4. Call LLM API
    analysis_result: Optional[str] = None
    result_type: Optional[str] = None
    try:
        print(f"Sending analysis instruction and data sample to LLM ({ANALYSIS_MODEL})...")
        response = await llm_client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=messages,
            temperature=0.3, # Lower temperature for more factual analysis
        )
        analysis_result = response.choices[0].message.content
        result_type = "llm_analysis_text" # Indicate the result is text from LLM
        print("Successfully received analysis result from LLM.")
        analysis_result = analysis_result.strip() if analysis_result else None

    except Exception as e:
        print(f"Error calling LLM API for data analysis: {e}")
        raise Exception(f"LLM API call failed during data analysis: {e}")

    return analysis_result, result_type