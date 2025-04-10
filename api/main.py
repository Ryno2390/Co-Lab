from fastapi import FastAPI
from contextlib import asynccontextmanager # Import for lifespan manager (alternative)
from ..tokenomics.ledger import connect_db, disconnect_db # Import ledger functions
from .routers import core_ai # Import the core_ai router module

# --- App Initialization ---
# Using lifespan context manager is the recommended way in newer FastAPI versions
# but on_event decorators are also common and clear. We'll use on_event here.

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Code to run on startup
#     await connect_db()
#     yield
#     # Code to run on shutdown
#     await disconnect_db()
# app = FastAPI(lifespan=lifespan, ...) # Pass lifespan to FastAPI constructor

app = FastAPI(
    title="Co-Lab API",
    description="API for interacting with the Co-Lab decentralized AI system.",
    version="0.1.0",
)

# --- Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """Connects to the database on application startup."""
    print("Application startup: Connecting to database...")
    await connect_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Disconnects from the database on application shutdown."""
    print("Application shutdown: Disconnecting from database...")
    await disconnect_db()


# --- API Endpoints ---
@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for basic health check.
    """
    return {"status": "ok", "message": "Welcome to Co-Lab API!"}

# --- Include API Routers ---
app.include_router(core_ai.router, prefix="/core", tags=["Core AI"])

# Placeholder for future routers:
# from .routers import data_router, token_router # Example
# app.include_router(data_router.router, prefix="/data", tags=["Data Management"])
# app.include_router(token_router.router, prefix="/token", tags=["Tokenomics"])
# ---

if __name__ == "__main__":
    # This block is for running locally, e.g., for debugging.
    # Production deployments should use a process manager like Gunicorn with Uvicorn workers.
    import uvicorn
    # It's often better to run uvicorn from the command line:
    # uvicorn Co-Lab.api.main:app --reload --host 0.0.0.0 --port 8000
    # But this block allows running the script directly (python -m Co-Lab.api.main)
    # Note: Startup/shutdown events might not run reliably when using this block directly
    # depending on how uvicorn handles it vs command-line execution.
    uvicorn.run(app, host="0.0.0.0", port=8000)