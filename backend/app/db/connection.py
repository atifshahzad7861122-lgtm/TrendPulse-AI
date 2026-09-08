from typing import Optional, Tuple, Any, Dict
import logging
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text
from backend.app.core.config import settings

logger = logging.getLogger("trendpulse.db")

_async_engine: Optional[AsyncEngine] = None

def normalize_async_database_url(url: str) -> str:
    """
    Normalizes standard PostgreSQL URLs to async driver protocols.
    - postgresql+psycopg2:// -> postgresql+asyncpg://
    - postgresql:// -> postgresql+asyncpg://
    - postgres:// -> postgresql+asyncpg://
    - sqlite:// -> sqlite+aiosqlite://
    """
    if not url:
        return ""
    clean = url.strip()
    if clean.startswith("postgresql+psycopg2://"):
        clean = "postgresql+asyncpg://" + clean[len("postgresql+psycopg2://"):]
    elif clean.startswith("postgres://"):
        clean = "postgresql+asyncpg://" + clean[len("postgres://"):]
    elif clean.startswith("postgresql://") and not clean.startswith("postgresql+"):
        clean = "postgresql+asyncpg://" + clean[len("postgresql://"):]
    elif clean.startswith("sqlite://") and not clean.startswith("sqlite+"):
        clean = "sqlite+aiosqlite://" + clean[len("sqlite://"):]

    # Normalize ?sslmode= to ?ssl= for asyncpg
    if "sqlite" not in clean:
        if "?sslmode=" in clean:
            clean = clean.replace("?sslmode=", "?ssl=")
        elif "&sslmode=" in clean:
            clean = clean.replace("&sslmode=", "&ssl=")

    return clean

def normalize_sync_database_url(url: str) -> str:
    """
    Normalizes database URLs to synchronous driver protocols for SQLAlchemy (psycopg2).
    - postgresql+asyncpg:// -> postgresql+psycopg2://
    - postgres:// -> postgresql+psycopg2://
    - postgresql:// -> postgresql+psycopg2://
    - sqlite+aiosqlite:// -> sqlite://
    - sqlite:// -> sqlite://
    """
    if not url:
        return ""
    clean = url.strip()
    if clean.startswith("postgresql+asyncpg://"):
        clean = "postgresql+psycopg2://" + clean[len("postgresql+asyncpg://"):]
    elif clean.startswith("postgres://"):
        clean = "postgresql+psycopg2://" + clean[len("postgres://"):]
    elif clean.startswith("postgresql://") and not clean.startswith("postgresql+"):
        clean = "postgresql+psycopg2://" + clean[len("postgresql://"):]
    elif clean.startswith("sqlite+aiosqlite://"):
        clean = "sqlite://" + clean[len("sqlite+aiosqlite://"):]

    # Normalize ?ssl= to ?sslmode= for psycopg2
    if "sqlite" not in clean:
        if "?ssl=" in clean:
            clean = clean.replace("?ssl=", "?sslmode=")
        elif "&ssl=" in clean:
            clean = clean.replace("&ssl=", "&sslmode=")

    return clean


def sanitize_db_url_for_logging(url: str) -> str:
    """
    Strips credentials from database URL for safe logging.
    """
    if not url:
        return "None"
    try:
        parsed = urlparse(url)
        netloc = parsed.hostname or "localhost"
        if parsed.port:
            netloc += f":{parsed.port}"
        return f"{parsed.scheme}://***:***@{netloc}{parsed.path}"
    except Exception:
        return "postgresql://***:***@[sanitized]"

def get_async_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """
    Retrieves or creates the application singleton AsyncEngine.
    """
    global _async_engine
    if _async_engine is not None:
        return _async_engine

    raw_url = database_url or settings.DATABASE_URL
    if not raw_url:
        raise ValueError(
            "Cannot initialize PostgreSQL engine: DATABASE_URL is not configured in environment."
        )

    async_url = normalize_async_database_url(raw_url)
    sanitized = sanitize_db_url_for_logging(async_url)
    logger.info(f"Initializing PostgreSQL AsyncEngine with connection pool: {sanitized}")

    engine_kwargs: Dict[str, Any] = {
        "echo": settings.DB_ECHO,
        "future": True,
    }

    # Only add pool arguments for PostgreSQL (SQLite memory/file doesn't support max_overflow/size)
    if "sqlite" not in async_url:
        import os
        is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
        if is_serverless:
            from sqlalchemy.pool import NullPool
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update({
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "pool_recycle": settings.DB_POOL_RECYCLE,
                "pool_pre_ping": True,
            })

    _async_engine = create_async_engine(async_url, **engine_kwargs)
    return _async_engine

def reset_async_engine() -> None:
    """Resets the singleton engine for testing/reconfiguration."""
    global _async_engine
    _async_engine = None

async def check_db_connection(engine: Optional[AsyncEngine] = None) -> Tuple[bool, Optional[str]]:
    """
    Performs a non-destructive SELECT 1 health verification.
    Returns: (is_healthy, error_message)
    """
    target_engine = engine or _async_engine or (get_async_engine() if settings.DATABASE_URL else None)
    if not target_engine:
        return False, "No active database engine or DATABASE_URL configured."

    try:
        async with target_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        error_msg = f"Database health check failed: {type(e).__name__}"
        logger.error(error_msg)
        return False, error_msg
