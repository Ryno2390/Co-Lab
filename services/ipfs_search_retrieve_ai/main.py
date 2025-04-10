from fastapi import FastAPI
# Import the api module we created
from . import api
# We might need settings later, potentially shared or service-specific
# from ...config import settings # Adjust import based on final structure

app = FastAPI(
    title="Co-Lab - IPFS Search & Retrieve Sub-AI Service",
    description="A specialized AI service for querying the data index and retrieving info about relevant IPFS content.",
    version="0.1.0",
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# Include the router from api.py
app.include_router(api.router)

# Add startup/shutdown events if needed

if __name__ == "__main__":
    import uvicorn
    # Run on port 8002 as per sub_ai/client.py placeholder
    uvicorn.run("Co-Lab.services.ipfs_search_retrieve_ai.main:app", host="0.0.0.0", port=8002, reload=True)