import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import Optional, List

# Load .env file variables if it exists
# Useful for local development
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    Environment variables take precedence over values loaded from a .env file.
    """
    # --- Core Project Config ---
    PROJECT_NAME: str = "Co-Lab"
    API_V1_STR: str = "/api/v1"
    # Set to 'development', 'staging', 'production' via environment variable
    ENVIRONMENT: str = "development"

    # --- API Keys (Loaded from Environment) ---
    # Required: Set these in your .env file or environment
    OPENAI_API_KEY: str
    PINECONE_API_KEY: str
    # ANTHROPIC_API_KEY: Optional[str] = None # Add if using Claude
    INTERNAL_API_KEY: str = "change-this-in-production" # For service-to-service auth, CHANGE THIS!
    ELASTICSEARCH_API_KEY: Optional[str] = None # For Elastic Cloud API Key auth

    # --- Service URLs / Connection Strings (Loaded from Environment or Defaults) ---
    # IPFS Daemon API
    IPFS_API_MULTIADDR: str = "/ip4/127.0.0.1/tcp/5001"
    # Indexer Service API Base URL
    INDEXER_API_URL: str = "http://localhost:8010" # Example, adjust port as needed
    # Tokenomics Ledger Database URL
    LEDGER_DATABASE_URL: str = "sqlite+aiosqlite:///./colab_ledger.db" # Use aiosqlite driver for async with databases lib
    # Elasticsearch Connection
    ELASTICSEARCH_HOSTS: Optional[str] = "http://localhost:9200" # Comma-separated if multiple nodes
    ELASTICSEARCH_CLOUD_ID: Optional[str] = None # For Elastic Cloud connection

    # --- Pinecone Specific Config ---
    # PINECONE_ENVIRONMENT: Optional[str] = None # Environment might not be needed for serverless v3+ client
    PINECONE_INDEX_NAME: str = "colab-sub-ai-index"

    # --- Elasticsearch Specific Config ---
    ELASTICSEARCH_INDEX_NAME: str = "colab_content_index" # Default index name for content

    # --- Core AI Config ---
    DECOMPOSITION_MODEL: str = "gpt-3.5-turbo" # Or specific OpenAI model / Claude model
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536 # Adjust if using lower dimensions with text-embedding-3
    SYNTHESIS_MODEL: str = "gpt-4o" # Or specific OpenAI model / Claude model
    ROUTING_CONFIDENCE_THRESHOLD: float = 0.75

    # --- Sub-AI Endpoints (Example - Consider a better discovery mechanism later) ---
    SUB_AI_CODE_GENERATION_URL: str = "http://localhost:8001/invoke"
    SUB_AI_IPFS_SEARCH_URL: str = "http://localhost:8002/invoke"
    SUB_AI_SUMMARIZATION_URL: str = "http://localhost:8004/invoke"
    SUB_AI_QA_URL: str = "http://localhost:8005/invoke"
    SUB_AI_DATA_ANALYSIS_URL: str = "http://localhost:8006/invoke"
    SUB_AI_DYNAMIC_BASE_URL: str = "http://localhost:8003/invoke"

    # --- Tokenomics V1 Config ---
    TOKEN_BASE_FEE: float = 1.0
    TOKEN_DECOMPOSITION_COST: float = 5.0
    TOKEN_ROUTING_COST_PER_TASK: float = 0.5
    TOKEN_SYNTHESIS_COST: float = 10.0
    TOKEN_INVOCATION_SIMPLE_FIXED: float = 2.0
    TOKEN_INVOCATION_COMPLEX_FIXED: float = 5.0
    TOKEN_INVOCATION_DYNAMIC: float = 10.0
    TOKEN_REWARD_PER_MB: float = 0.01
    TOKEN_METADATA_BONUS: float = 0.5
    REWARD_REQUIRED_METADATA_FIELDS: List[str] = ["filename", "description", "tags"]
    REWARD_MIN_FILE_SIZE_BYTES: int = 1
    REWARD_MAX_FILE_SIZE_BYTES: int = 1 * 1024**3 # 1 GB

    # Pydantic V2+ configuration using model_config dict
    model_config = SettingsConfigDict(
        env_file=".env", # Specifies the default .env file to load
        env_file_encoding='utf-8',
        extra='ignore', # Ignore extra fields not defined in the model
        # Allow case-insensitive environment variables
        case_sensitive=False
    )

# Instantiate settings - this automatically loads from .env and environment variables
settings = Settings()

# Example usage:
# from Co-Lab.config.settings import settings
# print(settings.OPENAI_API_KEY)
# print(settings.ELASTICSEARCH_HOSTS)
# print(settings.TOKEN_BASE_FEE)

# You would create a .env file in the Co-Lab directory like this:
# OPENAI_API_KEY="sk-..."
# PINECONE_API_KEY="..."
# INTERNAL_API_KEY="a-secure-random-string"
# ELASTICSEARCH_HOSTS="http://localhost:9200"
# ELASTICSEARCH_CLOUD_ID="YOUR_CLOUD_ID" # Optional: For Elastic Cloud
# ELASTICSEARCH_API_KEY="YOUR_API_KEY" # Optional: For Elastic Cloud API Key Auth
# INDEXER_API_URL="http://127.0.0.1:8010"
# LEDGER_DATABASE_URL="postgresql+asyncpg://user:pass@host:port/dbname" # Example for PostgreSQL
# TOKEN_BASE_FEE=1.5 # Example override