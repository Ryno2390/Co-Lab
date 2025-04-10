from fastapi import FastAPI
# Import the api module we created
from . import api
# We might need settings later, potentially shared or service-specific
# from ...config import settings # Adjust import based on final structure

app = FastAPI(
    title="Co-Lab - Question Answering Sub-AI Service",
    description="A specialized AI service for answering specific questions based on provided context (e.g., IPFS documents).",
    version="0.1.0",
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

# Include the router from api.py
app.include_router(api.router)

# Add startup/shutdown events if needed (e.g., for IPFS client)
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
    # Run on port 8005 as per settings.py placeholder
    uvicorn.run("Co-Lab.services.question_answering_ai.main:app", host="0.0.0.0", port=8005, reload=True)