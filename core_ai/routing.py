from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel
import asyncio

from .models import SubTask
from ..config import settings
# Assuming OpenAI for embeddings and Pinecone for vector DB, based on previous steps
from openai import AsyncOpenAI
# import pinecone # Deprecated client
from pinecone import Pinecone, ServerlessSpec # Import Pinecone client

# --- Client Initialization ---
# Embedding Client (reuse from decomposition or create new instance)
try:
    embedding_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    # Specify the embedding model consistent with architecture doc
    EMBEDDING_MODEL = "text-embedding-3-small"
    # Consider dimensionality if using text-embedding-3
    EMBEDDING_DIMENSIONS = 1536 # Or lower if configured
except Exception as e:
    print(f"Error initializing OpenAI client for embeddings: {e}")
    embedding_client = None

# Pinecone Client
try:
    # pc = pinecone.init(api_key=settings.PINECONE_API_KEY, environment=settings.PINECONE_ENVIRONMENT) # Deprecated
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    # TODO: Define index name in settings
    PINECONE_INDEX_NAME = "colab-sub-ai-index" # Example name
    # Check if index exists, create if not (basic example)
    if PINECONE_INDEX_NAME not in pc.list_indexes().names:
         print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
         # Ensure dimensions match the embedding model
         pc.create_index(
             PINECONE_INDEX_NAME,
             dimension=EMBEDDING_DIMENSIONS,
             metric="cosine", # Or "dotproduct" / "euclidean"
             spec=ServerlessSpec(cloud="aws", region="us-west-2") # Example serverless spec
             # For pod-based: spec=PodSpec(environment=settings.PINECONE_ENVIRONMENT, pod_type="p1.x1")
         )
         print("Index created.")
    index = pc.Index(PINECONE_INDEX_NAME)
    print(f"Pinecone client initialized for index '{PINECONE_INDEX_NAME}'.")
except Exception as e:
    print(f"Error initializing Pinecone client: {e}")
    index = None

# --- Routing Logic ---

# Define a structure to hold routing results
class RoutingDecision(BaseModel):
    sub_task: SubTask
    route_type: str # 'fixed_specialist' or 'dynamic_instance'
    target_id: Optional[str] = None # ID of the fixed specialist if route_type is 'fixed_specialist'
    target_metadata: Optional[Dict[str, Any]] = None # Metadata of the matched specialist
    confidence_score: Optional[float] = None # Similarity score from vector search

# TODO: Define confidence threshold in settings
ROUTING_CONFIDENCE_THRESHOLD = 0.75 # Example threshold

async def generate_embedding(text: str) -> Optional[List[float]]:
    """Generates embedding for a given text using the configured model."""
    if not embedding_client:
        print("Error: Embedding client not initialized.")
        return None
    try:
        response = await embedding_client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
            # dimensions=EMBEDDING_DIMENSIONS # Add if using text-embedding-3 and want specific dims
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding for text '{text[:50]}...': {e}")
        return None

async def route_sub_tasks(sub_tasks: List[SubTask]) -> List[RoutingDecision]:
    """
    Routes a list of sub-tasks to appropriate Sub-AIs (fixed or dynamic).

    Args:
        sub_tasks: A list of SubTask objects.

    Returns:
        A list of RoutingDecision objects indicating the target for each sub-task.
    """
    if not index or not embedding_client:
        raise Exception("Routing components (Pinecone index or Embedding client) not initialized.")

    routing_decisions: List[RoutingDecision] = []

    # Generate embeddings for all tasks (can be done concurrently)
    embedding_tasks = [generate_embedding(task.instruction) for task in sub_tasks]
    embeddings = await asyncio.gather(*embedding_tasks)

    for i, task in enumerate(sub_tasks):
        task_embedding = embeddings[i]
        route_decision = RoutingDecision(sub_task=task, route_type='dynamic_instance') # Default to dynamic

        if task_embedding:
            try:
                # Query Pinecone for top matching fixed specialists
                query_response = index.query(
                    vector=task_embedding,
                    top_k=1, # Find the single best match
                    include_metadata=True,
                    filter={ # Example filter: only route to active specialists
                        "status": {"$eq": "active"}
                    }
                )

                if query_response.matches:
                    best_match = query_response.matches[0]
                    match_score = best_match.score
                    match_id = best_match.id
                    match_metadata = best_match.metadata

                    print(f"Routing task '{task.instruction[:50]}...': Best match '{match_id}' score {match_score:.4f}")

                    if match_score >= ROUTING_CONFIDENCE_THRESHOLD:
                        route_decision.route_type = 'fixed_specialist'
                        route_decision.target_id = match_id
                        route_decision.target_metadata = match_metadata
                        route_decision.confidence_score = match_score
                    else:
                         print(f"Match score {match_score:.4f} below threshold {ROUTING_CONFIDENCE_THRESHOLD}. Falling back to dynamic.")
                else:
                    print(f"No active fixed specialist found for task '{task.instruction[:50]}...'. Falling back to dynamic.")

            except Exception as e:
                print(f"Error querying Pinecone for task '{task.instruction[:50]}...': {e}. Falling back to dynamic.")
                # Keep default decision (dynamic_instance)

        else:
             print(f"Could not generate embedding for task '{task.instruction[:50]}...'. Falling back to dynamic.")
             # Keep default decision (dynamic_instance)

        routing_decisions.append(route_decision)

    return routing_decisions