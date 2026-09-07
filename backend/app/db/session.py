from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from backend.app.db.connection import get_async_engine
from backend.app.core.config import settings

_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_sync_session_factory: Optional[sessionmaker[Session]] = None

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

from sqlalchemy.pool import NullPool
from sqlalchemy.orm import scoped_session, sessionmaker, Session

_sync_session_factory: Optional[scoped_session[Session]] = None

def get_sync_session_factory() -> scoped_session[Session]:
    """
    Retrieves or creates the synchronous scoped session factory for PostgreSQL repositories.
    """
    global _sync_session_factory
    if _sync_session_factory is not None:
        return _sync_session_factory

    raw_url = getattr(settings, "DATABASE_URL", None) or ""
    if raw_url.startswith("postgresql+asyncpg://"):
        sync_url = "postgresql://" + raw_url[len("postgresql+asyncpg://"):]
    elif raw_url.startswith("sqlite+aiosqlite://"):
        sync_url = "sqlite://" + raw_url[len("sqlite+aiosqlite://"):]
    else:
        sync_url = raw_url

    engine = create_engine(sync_url, poolclass=NullPool)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    _sync_session_factory = scoped_session(session_factory)
    return _sync_session_factory

def get_sync_session() -> Optional[Session]:
    """Returns a thread-safe synchronous scoped session if DATABASE_URL is configured."""
    if not getattr(settings, "DATABASE_URL", None):
        return None
    try:
        factory = get_sync_session_factory()
        return factory()
    except Exception:
        return None

def reset_session_factory() -> None:
    """Resets the singleton session factory for testing."""
    global _async_session_factory, _sync_session_factory
    _async_session_factory = None
    _sync_session_factory = None


