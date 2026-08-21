from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from backend.app.db.connection import get_async_engine

_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

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

def reset_session_factory() -> None:
    """Resets the singleton session factory for testing."""
    global _async_session_factory
    _async_session_factory = None
