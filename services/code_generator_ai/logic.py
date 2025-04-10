from typing import Optional, List, Tuple
from openai import AsyncOpenAI # Example using OpenAI

# Import clients for IPFS/Indexer if context fetching is needed
# try:
#     from ...data_layer import ipfs_client, indexer_client
# except ImportError:
#     print("Warning: Could not import data_layer clients.")
#     ipfs_client = None
#     indexer_client = None

# Import settings, potentially shared or service-specific
try:
    from ...config import settings
    llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Choose a model suitable for code generation
    CODE_GEN_MODEL = "gpt-4o" # Or gpt-4-turbo, or specialized code models
except ImportError:
     print("Warning: Could not import main settings. Using fallback LLM client init.")
     import os
     llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
     CODE_GEN_MODEL = "gpt-4o"
except Exception as e:
    print(f"Error initializing LLM client for code generation: {e}")
    llm_client = None


async def generate_code(
    instruction: str,
    language: Optional[str] = None,
    context_cids: Optional[List[str]] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generates code based on instructions, potentially using context from IPFS.

    Args:
        instruction: Natural language instruction.
        language: Optional target programming language.
        context_cids: Optional list of IPFS CIDs for context.

    Returns:
        A tuple containing the generated code string (or None) and the detected/used language (or None).
    """
    if not llm_client:
        print("Error: LLM client not initialized for code generation.")
        raise ConnectionError("LLM client not available for code generation.")

    print(f"Generating code for instruction: '{instruction[:50]}...'")
    if language: print(f"  Target language hint: {language}")
    if context_cids: print(f"  Context CIDs provided: {context_cids}")

    # --- Placeholder for Context Fetching ---
    context_text = ""
    if context_cids:
        print("  TODO: Implement fetching and processing context from CIDs via IPFS/Indexer clients.")
        # Example:
        # fetched_contexts = []
        # for cid in context_cids:
        #     content_bytes = await ipfs_client.get_ipfs_content(cid)
        #     if content_bytes:
        #         try:
        #             fetched_contexts.append(content_bytes.decode('utf-8'))
        #         except UnicodeDecodeError:
        #             print(f"Warning: Could not decode context CID {cid}")
        # context_text = "\n---\n".join(fetched_contexts)
        context_text = "\n# [Context from CIDs would be inserted here]\n"
    # --- End Placeholder ---

    # --- Construct LLM Prompt ---
    system_prompt = "You are an expert code generation AI. Generate only the code requested by the user, without any introductory phrases, explanations, or markdown formatting unless specifically asked for."
    user_prompt = instruction
    if language:
        user_prompt = f"Generate the following code in {language}:\n{instruction}"
    if context_text:
        user_prompt += f"\n\nUse the following code as context if relevant:\n```\n{context_text}\n```"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # --- Call LLM API ---
    try:
        print(f"Sending prompt to Code Gen LLM ({CODE_GEN_MODEL})...")
        response = await llm_client.chat.completions.create(
            model=CODE_GEN_MODEL,
            messages=messages,
            temperature=0.2, # Lower temperature for more predictable code
            # Consider adding stop sequences if needed
        )
        generated_code = response.choices[0].message.content
        # Basic language detection placeholder (LLM might indicate it, or use a library)
        detected_language = language or "unknown" # TODO: Improve language detection
        print("Successfully received code from LLM.")
        # Strip potential markdown code fences if the LLM adds them
        if generated_code and generated_code.startswith("```") and generated_code.endswith("```"):
             lines = generated_code.splitlines()
             if len(lines) > 1:
                 # Try to extract language from ```python etc.
                 first_line_lang = lines[0].strip('`').strip()
                 if first_line_lang:
                     detected_language = first_line_lang
                 generated_code = "\n".join(lines[1:-1]) # Remove first and last lines
             else:
                 generated_code = generated_code.strip('`') # Handle single line case


        return generated_code.strip() if generated_code else None, detected_language

    except Exception as e:
        print(f"Error calling LLM API for code generation: {e}")
        raise Exception(f"LLM API call failed during code generation: {e}")