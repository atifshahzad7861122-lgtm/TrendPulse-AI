import sys
from pathlib import Path

# Ensure root folder is in python path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.v1.router import api_router

import logging
from contextlib import asynccontextmanager
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("trendpulse.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables if PostgreSQL backend is enabled
    try:
        backend_mode = getattr(settings, "DATA_BACKEND", "in_memory").lower()
        if backend_mode == "postgres" and getattr(settings, "DATABASE_URL", None):
            from backend.app.db.session import get_sync_engine
            from backend.app.db.models import Base
            engine = get_sync_engine()
            if engine:
                Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning(f"Database schema check during startup: {type(e).__name__}")

    try:
        from backend.app.api.deps import get_scraper_service
        service = get_scraper_service()
        service.reconcile_orphaned_jobs()
    except Exception:
        pass
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Global exception handler to guarantee CORS headers on unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on [{request.method}] {request.url.path}: {type(exc).__name__}: {str(exc)}")
    origin = request.headers.get("origin")
    headers = {}
    if origin and (origin in settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Headers"] = "*"
        headers["Access-Control-Allow-Methods"] = "*"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred. Please check system logs."},
        headers=headers
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo Mode Read-Only Middleware
@app.middleware("http")
async def demo_mode_read_only_middleware(request: Request, call_next):
    """
    Enforces strict read-only access for public demo sessions.
    Rejects any mutating operations (POST, PUT, PATCH, DELETE) with HTTP 403.
    """
    if request.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
        path = request.url.path
        # Allow obtaining demo session and normal logout
        if not path.endswith("/auth/demo-session") and not path.endswith("/auth/logout"):
            auth_header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
            if auth_header.startswith("Bearer ") or auth_header.startswith("bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                try:
                    from jose import jwt
                    payload = jwt.decode(
                        token,
                        settings.SECRET_KEY,
                        algorithms=[settings.ALGORITHM]
                    )
                    if payload.get("role") == "demo" or payload.get("is_demo") is True:
                        origin = request.headers.get("origin")
                        headers = {}
                        if origin and (origin in settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS):
                            headers["Access-Control-Allow-Origin"] = origin
                            headers["Access-Control-Allow-Credentials"] = "true"
                            headers["Access-Control-Allow-Headers"] = "*"
                            headers["Access-Control-Allow-Methods"] = "*"
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": "Demo mode is read-only. Modifying data or executing mutations is not permitted."
                            },
                            headers=headers
                        )
                except Exception:
                    pass

    return await call_next(request)


# Health endpoints
@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {"status": "ok"}

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Direct alias mounts for specified platform endpoints (/api/platforms/daraz/...)
from backend.app.api.v1.endpoints.daraz import router as daraz_router
app.include_router(daraz_router, prefix="/api/platforms/daraz", tags=["daraz-direct"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
