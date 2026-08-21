from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_async_session_factory

logger = logging.getLogger("trendpulse.db")

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI request-scoped database session dependency.
    Ensures safe transaction lifecycle:
    Open session -> yield -> commit on success -> rollback on error -> close safely.
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {type(e).__name__}")
            raise
        finally:
            await session.close()
