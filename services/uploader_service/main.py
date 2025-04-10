from fastapi import FastAPI
# Import the api module we created
from . import api
# We might need settings later, potentially shared or service-specific
# from ...config import settings # Adjust import based on final structure

app = FastAPI(
    title="Co-Lab - Uploader Service",
    description="Handles user file uploads, interacts with IPFS, triggers indexing, and manages data contribution rewards.",
    version="0.1.0",
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# Include the router from api.py
app.include_router(api.router)

# Add startup/shutdown events if needed (e.g., for DB or IPFS client connections)
# @app.on_event("startup")
# async def startup_event():
#     # Initialize resources
#     pass
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     # Clean up resources
#     pass


if __name__ == "__main__":
    import uvicorn
    # Assign a port for the uploader service
    uvicorn.run("Co-Lab.services.uploader_service.main:app", host="0.0.0.0", port=8020, reload=True)