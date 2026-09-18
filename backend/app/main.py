"""Main FastAPI application entry point."""

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import routes_resume, routes_query, routes_scoring, routes_memory
from app.jobs.ingestion_queue import close_arq_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(routes_resume.router, prefix="/api", tags=["Resume"])
app.include_router(routes_query.router, prefix="/api", tags=["Query"])
app.include_router(routes_scoring.router, prefix="/api", tags=["Scoring"])
app.include_router(routes_memory.router, prefix="/api", tags=["Memory"])


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    loop = asyncio.get_running_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=max(1, settings.sync_thread_pool_workers)))
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("Initializing vector store...")
    # Vector store will be initialized lazily on first use


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    await close_arq_pool()
    logger.info("Shutting down application...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
