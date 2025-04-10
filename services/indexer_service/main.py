from fastapi import FastAPI
# Import the api module we created
from . import api
# We might need settings later, potentially shared or service-specific
# from ...config import settings # Adjust import based on final structure
# We will need background task processing later
# from . import processing

app = FastAPI(
    title="Co-Lab - Indexer Service",
    description="Receives announcements of new IPFS content, fetches, processes, and indexes it.",
    version="0.1.0",
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# Include the router from api.py
app.include_router(api.router)

# Add startup/shutdown events if needed
# @app.on_event("startup")
# async def startup_event():
#     # Initialize resources like DB connections, IPFS client, queue connection
#     # Start background worker task(s)
#     # processing.start_workers()
#     pass
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     # Clean up resources, stop workers gracefully
#     # await processing.stop_workers()
#     pass


if __name__ == "__main__":
    import uvicorn
    # Run on port 8010 as per indexer_client.py placeholder
    uvicorn.run("Co-Lab.services.indexer_service.main:app", host="0.0.0.0", port=8010, reload=True)