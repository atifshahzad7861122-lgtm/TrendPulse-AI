"""Main FastAPI application providing health checks and scraper runtime status."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import get_settings
from app.core.logging import setup_logger

settings = get_settings()
logger = setup_logger(log_level=settings.LOG_LEVEL)

app = FastAPI(
    title="TrendPulse Daraz Scraper API",
    version=__version__,
    description="Core Architecture and Scraping Infrastructure for TrendPulse Daraz Scraper",
)


@app.get("/health", tags=["System"])
async def health_check():
    """Basic health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": __version__,
        }
    )


@app.get("/", tags=["System"])
async def root():
    """Root info endpoint."""
    return {
        "app": "TrendPulse Daraz Scraper",
        "version": __version__,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
