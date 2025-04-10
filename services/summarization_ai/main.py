from fastapi import FastAPI
# Import the api module we created
from . import api
# We might need settings later, potentially shared or service-specific
# from ...config import settings # Adjust import based on final structure

app = FastAPI(
    title="Co-Lab - Summarization Sub-AI Service",
    description="A specialized AI service for generating summaries from text or IPFS content.",
    version="0.1.0",
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# Include the router from api.py
app.include_router(api.router)

# Add startup/shutdown events if needed (e.g., for IPFS client connection)
# @app.on_event("startup")
# async def startup_event():
#     # Initialize resources like DB connections, IPFS client if needed here
#     pass
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     # Clean up resources
#     pass


if __name__ == "__main__":
    import uvicorn
    # Run on a different port than the main API gateway
    uvicorn.run("Co-Lab.services.summarization_ai.main:app", host="0.0.0.0", port=8004, reload=True) # Port 8004 as example, added reload and app path