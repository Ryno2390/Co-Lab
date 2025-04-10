import asyncio
from typing import List, Optional, Dict, Any

# Import models from the main data_layer. Assumes monorepo structure.
try:
    from ...data_layer.indexer_client import IndexerQuery, IndexerResult, DocumentInfo
    # Need embedding generation capability (similar to routing)
    from ...core_ai.routing import generate_embedding, EMBEDDING_DIMENSIONS
    # Need Pinecone client (similar to routing)
    from ...core_ai.routing import index as pinecone_index # Reuse index connection from routing
    # Need Elasticsearch client (from processing)
    from .processing import es_client # Reuse ES client from processing
    from ...config import settings
except ImportError:
    print("Warning: Could not import shared clients/functions/settings for Indexer Logic. Using fallback simulation.")
    # Fallback definitions if imports fail
    from pydantic import BaseModel, Field
    class DocumentInfo(BaseModel): cid: str; score: Optional[float] = None; metadata: Optional[Dict[str, Any]] = None; snippet: Optional[str] = None
    class IndexerQuery(BaseModel): query_text: Optional[str] = None; query_vector: Optional[List[float]] = None; keywords: Optional[List[str]] = None; metadata_filter: Optional[Dict[str, Any]] = None; top_k: int = 5
    class IndexerResult(BaseModel): query: IndexerQuery; results: List[DocumentInfo] = Field(default_factory=list); status: str = Field(default="success"); error_message: Optional[str] = None
    async def generate_embedding(text: str) -> Optional[List[float]]: return [0.1] * 1536 # Simulate
    pinecone_index = None
    es_client = None
    settings = None


async def perform_search(query: IndexerQuery) -> IndexerResult:
    """
    Performs search against Pinecone (vector) and Elasticsearch (keyword/text)
    and combines the results.

    Args:
        query: The search query parameters.

    Returns:
        An IndexerResult object containing combined search results.
    """
    print(f"Indexer Logic: Performing search for query: {query.model_dump(exclude_none=True)}")
    combined_results: Dict[str, DocumentInfo] = {} # Use dict to handle duplicates by CID
    tasks = []
    query_vector = query.query_vector

    # 1. Generate embedding if text query is provided but no vector
    if query.query_text and not query.query_vector and generate_embedding:
        print("Generating embedding for query text...")
        query_vector = await generate_embedding(query.query_text)
        if not query_vector:
            print("Warning: Failed to generate query vector from text.")
        else:
             print("Embedding generated.")

    # 2. Prepare Pinecone Query Task (if vector available)
    if pinecone_index and query_vector:
        tasks.append(query_pinecone(query, query_vector))

    # 3. Prepare Elasticsearch Query Task (if text/keywords available)
    if es_client and (query.query_text or query.keywords) and settings:
        tasks.append(query_elasticsearch(query))

    # 4. Execute queries concurrently
    if not tasks:
        return IndexerResult(query=query, status="error", error_message="No valid query parameters provided for search.")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 5. Combine results (simple concatenation + deduplication by CID for V1)
    pinecone_results: List[DocumentInfo] = []
    es_results: List[DocumentInfo] = []

    for result in results:
        if isinstance(result, Exception):
            print(f"Error during search sub-task: {result}")
            # Optionally include partial results or just report overall error later
        elif isinstance(result, tuple): # Expecting (source, list[DocumentInfo])
            source, docs = result
            if source == "pinecone":
                pinecone_results = docs
            elif source == "elasticsearch":
                es_results = docs

    # Combine and deduplicate
    for doc in pinecone_results + es_results:
        if doc.cid not in combined_results:
            combined_results[doc.cid] = doc
        else:
            # Simple merge: keep existing, maybe update score if higher?
            # More advanced fusion (RRF) could be implemented here later.
            if doc.score and combined_results[doc.cid].score:
                 combined_results[doc.cid].score = max(doc.score, combined_results[doc.cid].score or 0.0)
            elif doc.score:
                 combined_results[doc.cid].score = doc.score


    final_results = sorted(combined_results.values(), key=lambda d: d.score or 0.0, reverse=True)

    print(f"Combined search yielded {len(final_results)} unique results.")

    return IndexerResult(query=query, results=final_results[:query.top_k], status="success")


async def query_pinecone(query: IndexerQuery, vector: List[float]) -> Tuple[str, List[DocumentInfo]]:
    """Helper function to query Pinecone."""
    print("Querying Pinecone...")
    results = []
    try:
        # Convert Pydantic filter to Pinecone format if needed (depends on complexity)
        pinecone_filter = query.metadata_filter # Assuming direct compatibility for simple cases
        loop = asyncio.get_running_loop()
        query_response = await loop.run_in_executor(
            None,
            lambda: pinecone_index.query(
                vector=vector,
                top_k=query.top_k * 2, # Fetch more initially for potential merging/ranking
                include_metadata=True,
                filter=pinecone_filter
            )
        )
        if query_response and query_response.matches:
            results = [
                DocumentInfo(
                    cid=match.id,
                    score=match.score,
                    metadata=match.metadata,
                    # Pinecone doesn't store snippets directly, get from metadata if stored there
                    snippet=match.metadata.get("processed_text_snippet") if match.metadata else None
                ) for match in query_response.matches
            ]
        print(f"Pinecone query returned {len(results)} results.")
    except Exception as e:
        print(f"Error querying Pinecone: {e}")
        # Raise or return empty list? Raising allows gather to catch it.
        raise e
    return "pinecone", results


async def query_elasticsearch(query: IndexerQuery) -> Tuple[str, List[DocumentInfo]]:
    """Helper function to query Elasticsearch."""
    print("Querying Elasticsearch...")
    results = []
    try:
        # Build ES query body (example: simple match query + filter)
        es_query_body: Dict[str, Any] = {"bool": {"must": [], "filter": []}}

        if query.query_text:
            es_query_body["bool"]["must"].append({"match": {"content": query.query_text}})
        elif query.keywords: # Use keywords if no query_text
             es_query_body["bool"]["must"].append({"terms": {"tags": query.keywords}}) # Assuming keywords map to 'tags' field

        if query.metadata_filter:
            # Basic filter conversion (assumes simple key:value)
             for key, value in query.metadata_filter.items():
                 es_query_body["bool"]["filter"].append({"term": {f"{key}.keyword": value}}) # Use .keyword for exact match on text fields usually

        if not es_query_body["bool"]["must"]:
             es_query_body["bool"]["must"].append({"match_all": {}}) # Match all if no text/keyword query

        if not es_query_body["bool"]["filter"]:
             del es_query_body["bool"]["filter"] # Remove empty filter array


        search_response = await es_client.search(
            index=settings.ELASTICSEARCH_INDEX_NAME,
            query=es_query_body["bool"], # Pass the bool query part
            size=query.top_k * 2, # Fetch more initially
            # Add source filtering if needed: _source=["cid", "metadata", ...]
        )

        if search_response and search_response.get("hits", {}).get("hits"):
            for hit in search_response["hits"]["hits"]:
                source = hit.get("_source", {})
                results.append(DocumentInfo(
                    cid=hit.get("_id"), # Assumes CID is used as document ID
                    score=hit.get("_score"),
                    metadata=source, # Return the whole source as metadata for now
                    snippet=source.get("content", "")[:500] # Example snippet from content
                ))
        print(f"Elasticsearch query returned {len(results)} results.")
    except Exception as e:
        print(f"Error querying Elasticsearch: {e}")
        raise e
    return "elasticsearch", results