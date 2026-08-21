from fastapi import APIRouter, Response, status
from backend.app.core.config import settings
from backend.app.db.connection import check_db_connection

router = APIRouter()

@router.get("/database")
async def get_database_health(response: Response):
    """
    Database health check endpoint.
    Verifies connection health without ever exposing credentials or connection strings.
    """
    backend_mode = getattr(settings, "DATA_BACKEND", "in_memory").lower()

    if backend_mode == "in_memory":
        return {
            "status": "healthy",
            "database": "in_memory",
            "backend": "in_memory"
        }

    # PostgreSQL / Supabase mode
    is_healthy, error_msg = await check_db_connection()
    if is_healthy:
        return {
            "status": "healthy",
            "database": "supabase_postgresql",
            "backend": "postgres"
        }

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "unhealthy",
        "database": "supabase_postgresql",
        "backend": "postgres",
        "error": "Database connectivity check failed"
    }
