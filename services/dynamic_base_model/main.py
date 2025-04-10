from fastapi import FastAPI
# Import the api module we created
from . import api
# We might need settings later, potentially shared or service-specific
# from ...config import settings # Adjust import based on final structure

app = FastAPI(
    title="Co-Lab - Dynamic Base Model Service",
    description="A general-purpose AI service that handles dynamically assigned sub-tasks.",
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
    # Run on port 8003 as per sub_ai/client.py placeholder
    uvicorn.run("Co-Lab.services.dynamic_base_model.main:app", host="0.0.0.0", port=8003, reload=True)