import asyncio
from typing import Optional, List, Any
from openai import AsyncOpenAI # Example using OpenAI

# Import the Indexer client from the main data_layer
try:
    from ...data_layer import indexer_client
    from ...data_layer.indexer_client import IndexerQuery, DocumentInfo # Import necessary models
except ImportError:
    print("Warning: Could not import indexer_client. QA RAG will not work.")
    indexer_client = None
    # Define fallbacks if needed for standalone testing
    from pydantic import BaseModel, Field
    class DocumentInfo(BaseModel): cid: str; score: Optional[float] = None; metadata: Optional[Dict[str, Any]] = None; snippet: Optional[str] = None
    class IndexerQuery(BaseModel): query_text: Optional[str] = None; query_vector: Optional[List[float]] = None; keywords: Optional[List[str]] = None; metadata_filter: Optional[Dict[str, Any]] = None; top_k: int = 5
    class IndexerResult(BaseModel): query: IndexerQuery; results: List[DocumentInfo] = Field(default_factory=list); status: str = Field(default="success"); error_message: Optional[str] = None


# Import settings, potentially shared or service-specific
try:
    from ...config import settings
    llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Choose a model suitable for QA/RAG
    QA_MODEL = settings.SYNTHESIS_MODEL # Example: Reuse synthesis model
except ImportError:
     print("Warning: Could not import main settings. Using fallback LLM client init.")
     import os
     llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
     QA_MODEL = "gpt-4o" # Fallback model
except Exception as e:
    print(f"Error initializing LLM client for QA: {e}")
    llm_client = None

# Removed fetch_and_decode helper function

async def answer_question(question: str) -> Optional[str]:
    """
    Answers a question using Retrieval-Augmented Generation (RAG).
    Fetches relevant context snippets from the Indexer based on the question,
    then uses an LLM to generate an answer based on the question and context.

    Args:
        question: The user's question.

    Returns:
        The generated answer string, or None if an error occurs.
    """
    if not llm_client:
        print("Error: LLM client not initialized for QA.")
        raise ConnectionError("LLM client not available for QA.")
    if not indexer_client:
        print("Error: Indexer client not available for QA context retrieval.")
        raise ConnectionError("Indexer client not available for QA context retrieval.")

    print(f"Answering question using RAG: '{question[:50]}...'")

    # 1. Retrieve relevant context snippets from Indexer
    context_string = ""
    try:
        # Use the question text for semantic search via the indexer
        # TODO: Make top_k configurable
        search_query = IndexerQuery(query_text=question, top_k=5)
        indexer_result = await indexer_client.query_indexer(search_query)

        if indexer_result.status != "success" or not indexer_result.results:
            print(f"Warning: Indexer query failed or returned no results for question. Error: {indexer_result.error_message}")
            # Decide how to proceed: Answer without context, or return error?
            # Let's try answering without external context for now.
            context_string = "[No relevant context found in index]"
        else:
            # Extract snippets or relevant parts from results
            snippets = []
            for doc in indexer_result.results:
                snippet = doc.snippet or doc.metadata.get("processed_text_snippet")
                if snippet:
                    snippets.append(f"Source CID {doc.cid}:\n{snippet}")
                elif doc.metadata: # Fallback to description if no snippet
                     snippet = doc.metadata.get("description")
                     if snippet:
                          snippets.append(f"Source CID {doc.cid} (Description):\n{snippet}")

            if not snippets:
                 context_string = "[No relevant context snippets found in index results]"
            else:
                 context_string = "\n\n---\n\n".join(snippets)

            # TODO: Consider chunking/summarizing context if it's too long for the LLM
            MAX_CONTEXT_LEN = 15000 # Reduce context limit for RAG vs full doc
            if len(context_string) > MAX_CONTEXT_LEN:
                print(f"Warning: Combined context length {len(context_string)} exceeds limit {MAX_CONTEXT_LEN}. Truncating.")
                context_string = context_string[:MAX_CONTEXT_LEN]

    except Exception as e:
        print(f"Error retrieving context from indexer: {e}")
        # Proceed without context or raise? Let's proceed without for now.
        context_string = "[Error retrieving context from index]"


    # 2. Construct RAG Prompt
    system_prompt = "You are an expert Question Answering AI. Answer the user's question based *only* on the provided context. If the answer cannot be found in the context, state that clearly. Be concise and directly answer the question."
    user_prompt = f"""
Context:
\"\"\"
{context_string}
\"\"\"

Question: {question}

Answer:"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # 3. Call LLM API
    try:
        print(f"Sending question and retrieved context to QA LLM ({QA_MODEL})...")
        response = await llm_client.chat.completions.create(
            model=QA_MODEL,
            messages=messages,
            temperature=0.1, # Low temperature for factual answers based on context
        )
        answer = response.choices[0].message.content
        print("Successfully received answer from QA LLM.")
        return answer.strip() if answer else None

    except Exception as e:
        print(f"Error calling LLM API for QA: {e}")
        raise Exception(f"LLM API call failed during QA: {e}")