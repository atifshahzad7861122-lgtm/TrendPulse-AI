from typing import Optional, Dict, Any
import logging
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from backend.app.db.connection import (
    get_async_engine,
    normalize_sync_database_url,
    sanitize_db_url_for_logging
)
from backend.app.core.config import settings

logger = logging.getLogger("trendpulse.db")

_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_sync_engine: Optional[Engine] = None
_sync_session_factory: Optional[scoped_session[Session]] = None


def get_async_session_factory(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """
    Retrieves or creates the async session factory.
    """
    global _async_session_factory
    if _async_session_factory is not None and engine is None:
        return _async_session_factory

    target_engine = engine or get_async_engine()
    _async_session_factory = async_sessionmaker(
        bind=target_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    return _async_session_factory

def get_sync_engine(database_url: Optional[str] = None) -> Optional[Engine]:
    """
    Retrieves or creates the application singleton synchronous Engine (psycopg2).
    """
    global _sync_engine
    if _sync_engine is not None and database_url is None:
        return _sync_engine

    raw_url = database_url or getattr(settings, "DATABASE_URL", None)
    if not raw_url:
        return None

    sync_url = normalize_sync_database_url(raw_url)
    sanitized = sanitize_db_url_for_logging(sync_url)
    logger.info(f"Initializing PostgreSQL SyncEngine (psycopg2): {sanitized}")

    engine_kwargs: dict = {
        "echo": settings.DB_ECHO,
        "pool_pre_ping": True,
    }

    import os
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

    if "sqlite" in sync_url:
        from sqlalchemy.pool import StaticPool
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    elif is_serverless:
        from sqlalchemy.pool import NullPool
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
        engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

    _sync_engine = create_engine(sync_url, **engine_kwargs)
    return _sync_engine

def get_sync_session_factory() -> Optional[scoped_session[Session]]:
    """
    Retrieves or creates the synchronous scoped session factory for PostgreSQL repositories.
    """
    global _sync_session_factory
    if _sync_session_factory is not None:
        return _sync_session_factory

    engine = get_sync_engine()
    if not engine:
        return None

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    _sync_session_factory = scoped_session(session_factory)
    return _sync_session_factory

def get_sync_session() -> Optional[Session]:
    """Returns a thread-safe synchronous scoped session if DATABASE_URL is configured."""
    if not getattr(settings, "DATABASE_URL", None):
        return None
    try:
        factory = get_sync_session_factory()
        if not factory:
            return None
        session = factory()
        if session.is_active:
            trans = session.get_transaction()
            if trans and not trans.is_active:
                session.rollback()
        return session
    except Exception as e:
        logger.error(f"Failed to obtain sync database session: {type(e).__name__}")
        return None

def reset_session_factory() -> None:
    """Resets the singleton session factory and engines for testing."""
    global _async_session_factory, _sync_session_factory, _sync_engine
    if _sync_session_factory is not None:
        try:
            _sync_session_factory.remove()
        except Exception:
            pass
    if _sync_engine is not None:
        try:
            _sync_engine.dispose()
        except Exception:
            pass
    _async_session_factory = None
    _sync_session_factory = None
    _sync_engine = None



