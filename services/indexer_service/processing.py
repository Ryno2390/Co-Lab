import asyncio
import io
from typing import Optional, Dict, Any, List
from PyPDF2 import PdfReader
from elasticsearch import AsyncElasticsearch # Import Elasticsearch async client

# Import clients from main data_layer and core_ai
# Assumes monorepo structure or installed package
try:
    from ...data_layer import ipfs_client
    from ...core_ai.routing import generate_embedding, EMBEDDING_DIMENSIONS
    from ...core_ai.routing import index as pinecone_index
    from ...config import settings # Import shared settings
except ImportError:
    print("Warning: Could not import shared clients/functions/settings. Processing will be purely simulated.")
    ipfs_client = None
    generate_embedding = None
    pinecone_index = None
    settings = None # Indicate settings are unavailable
    EMBEDDING_DIMENSIONS = 1536

# --- Initialize Elasticsearch Client ---
es_client: Optional[AsyncElasticsearch] = None
if settings:
    try:
        es_args = {}
        if settings.ELASTICSEARCH_CLOUD_ID:
            print(f"Connecting to Elasticsearch using Cloud ID: {settings.ELASTICSEARCH_CLOUD_ID}")
            es_args['cloud_id'] = settings.ELASTICSEARCH_CLOUD_ID
        elif settings.ELASTICSEARCH_HOSTS:
            # Parse comma-separated hosts if provided
            hosts = [h.strip() for h in settings.ELASTICSEARCH_HOSTS.split(',')]
            print(f"Connecting to Elasticsearch using Hosts: {hosts}")
            es_args['hosts'] = hosts
        else:
             raise ValueError("Elasticsearch connection requires ELASTICSEARCH_CLOUD_ID or ELASTICSEARCH_HOSTS")

        if settings.ELASTICSEARCH_API_KEY:
            print("Using Elasticsearch API Key authentication.")
            es_args['api_key'] = settings.ELASTICSEARCH_API_KEY
        # Add other auth methods like basic_auth if needed based on settings

        if es_args: # Only initialize if connection params are found
            es_client = AsyncElasticsearch(**es_args)
            # TODO: Consider adding a connection check/ping on startup
            print("Elasticsearch client initialized.")
        else:
             print("Warning: No valid Elasticsearch connection parameters found in settings.")

    except Exception as e:
        print(f"Error initializing Elasticsearch client: {e}")
        es_client = None
else:
    print("Warning: Settings not loaded, cannot initialize Elasticsearch client.")


async def process_cid(cid: str, user_metadata: Optional[Dict[str, Any]] = None):
    """
    Background task to fetch, process, and index content for a given CID.
    """
    print(f"[Indexer Worker] Starting processing for CID: {cid}")
    metadata_to_store = user_metadata or {} # Use provided metadata or empty dict

    # 1. Fetch content from IPFS
    content_bytes: Optional[bytes] = None
    # ... (IPFS fetch logic remains the same) ...
    if ipfs_client:
        try:
            content_bytes = await ipfs_client.get_ipfs_content(cid)
            if not content_bytes:
                print(f"[Indexer Worker] Error: Failed to fetch content for CID {cid}.")
                return
            print(f"[Indexer Worker] Fetched {len(content_bytes)} bytes for CID {cid}.")
        except Exception as e:
            print(f"[Indexer Worker] Error fetching IPFS content for {cid}: {e}")
            return
    else:
        print("[Indexer Worker] Skipping IPFS fetch (client unavailable).")
        return

    # 2. Process Content - Extract Text
    processed_text: Optional[str] = None
    # ... (Text extraction logic remains the same) ...
    content_type = metadata_to_store.get("content_type", "").lower()
    filename = metadata_to_store.get("filename", "").lower()
    print(f"[Indexer Worker] Attempting text extraction for CID {cid} (type: {content_type}, filename: {filename})")
    try:
        if "application/pdf" in content_type or filename.endswith(".pdf"):
            pdf_file = io.BytesIO(content_bytes)
            reader = PdfReader(pdf_file)
            extracted_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
            processed_text = "\n".join(extracted_pages)
            if processed_text: print(f"[Indexer Worker] Extracted text from PDF CID {cid} ({len(reader.pages)} pages).")
            else: print(f"[Indexer Worker] Warning: No text extracted from PDF CID {cid}.")
        elif content_type.startswith("text/") or any(filename.endswith(ext) for ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']):
            processed_text = content_bytes.decode('utf-8')
            print(f"[Indexer Worker] Decoded text content for CID {cid}.")
        else:
            print(f"[Indexer Worker] Warning: Unsupported content type '{content_type}' or filename '{filename}' for text extraction.")
            processed_text = None
    except Exception as e:
        print(f"[Indexer Worker] Error during content processing for CID {cid}: {e}")
        processed_text = None

    if not processed_text:
        print(f"[Indexer Worker] No text extracted for CID {cid}. Aborting further indexing steps.")
        return

    MAX_TEXT_LENGTH = 20000
    if len(processed_text) > MAX_TEXT_LENGTH:
        print(f"[Indexer Worker] Truncating extracted text from {len(processed_text)} to {MAX_TEXT_LENGTH} chars for embedding.")
        processed_text = processed_text[:MAX_TEXT_LENGTH]

    # 3. Generate Embedding
    content_embedding: Optional[List[float]] = None
    # ... (Embedding generation logic remains the same) ...
    if generate_embedding:
        try:
            content_embedding = await generate_embedding(processed_text)
            if content_embedding: print(f"[Indexer Worker] Generated embedding for CID {cid} (dim: {len(content_embedding)}).")
            else: print(f"[Indexer Worker] Failed to generate embedding for CID {cid}.")
        except Exception as e:
            print(f"[Indexer Worker] Error generating embedding for {cid}: {e}")
            content_embedding = None
    else:
        print("[Indexer Worker] Skipping embedding generation (function unavailable).")


    # 4. Upsert to Vector Database (Pinecone)
    # ... (Pinecone upsert logic remains the same) ...
    if pinecone_index and content_embedding:
        try:
            metadata_to_store["processed_text_snippet"] = processed_text[:500]
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: pinecone_index.upsert(vectors=[(cid, content_embedding, metadata_to_store)])
            )
            print(f"[Indexer Worker] Upserted vector for CID {cid} to Pinecone.")
        except Exception as e:
            print(f"[Indexer Worker] Error upserting vector for {cid} to Pinecone: {e}")
    else:
        print("[Indexer Worker] Skipping Pinecone upsert (index unavailable or no embedding).")


    # 5. Index in Keyword Search (Elasticsearch)
    if es_client and processed_text and settings:
        try:
            # Construct the document to index
            doc_to_index = {
                "cid": cid, # Store CID for reference
                "content": processed_text, # Index the main extracted text
                "filename": metadata_to_store.get("filename"),
                "content_type": metadata_to_store.get("content_type"),
                "tags": metadata_to_store.get("tags"),
                "description": metadata_to_store.get("description"),
                "uploader_id": metadata_to_store.get("uploader_id"),
                "timestamp": metadata_to_store.get("timestamp") # Or use current time
                # Add any other relevant metadata fields
            }
            # Remove None values before indexing
            doc_to_index = {k: v for k, v in doc_to_index.items() if v is not None}

            # Use the async client's index method
            response = await es_client.index(
                index=settings.ELASTICSEARCH_INDEX_NAME,
                id=cid, # Use CID as the document ID (ensures updates overwrite)
                document=doc_to_index
            )
            print(f"[Indexer Worker] Indexed document for CID {cid} in Elasticsearch. Result: {response.get('result')}")
        except Exception as e:
            print(f"[Indexer Worker] Error indexing document for {cid} in Elasticsearch: {e}")
    else:
        print("[Indexer Worker] Skipping Elasticsearch indexing (client unavailable, no text, or settings missing).")

    print(f"[Indexer Worker] Finished processing for CID: {cid}")

# Placeholder for starting/stopping background workers if not using simple BackgroundTasks
# async def start_workers(): ...
# async def stop_workers(): ...