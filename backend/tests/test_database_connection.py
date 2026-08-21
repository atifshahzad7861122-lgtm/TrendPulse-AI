import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.connection import (
    normalize_async_database_url, sanitize_db_url_for_logging,
    get_async_engine, check_db_connection, reset_async_engine
)
from backend.app.db.session import get_async_session_factory, reset_session_factory
from backend.app.db.dependencies import get_db_session
from backend.app.api.deps import get_user_repository, get_product_repository
from backend.app.repositories.in_memory import InMemoryUserRepository, InMemoryProductRepository
from backend.app.repositories.postgres import PostgresUserRepository, PostgresProductRepository

client = TestClient(app)

@pytest.fixture
def anyio_backend():
    return "asyncio"

def test_normalize_async_database_url():
    pg_url = "postgresql://postgres:secret123@db.supabase.co:5432/postgres"
    assert normalize_async_database_url(pg_url) == "postgresql+asyncpg://postgres:secret123@db.supabase.co:5432/postgres"

    p_url = "postgres://postgres:secret123@db.supabase.co:5432/postgres"
    assert normalize_async_database_url(p_url) == "postgresql+asyncpg://postgres:secret123@db.supabase.co:5432/postgres"

    already_async = "postgresql+asyncpg://postgres:secret123@db.supabase.co:5432/postgres"
    assert normalize_async_database_url(already_async) == already_async

    sqlite_url = "sqlite:///:memory:"
    assert normalize_async_database_url(sqlite_url) == "sqlite+aiosqlite:///:memory:"

def test_sanitize_db_url_for_logging():
    url = "postgresql+asyncpg://postgres:SuperSecretPassword123@db.xyz.supabase.co:5432/postgres"
    sanitized = sanitize_db_url_for_logging(url)
    assert "SuperSecretPassword123" not in sanitized
    assert "db.xyz.supabase.co:5432" in sanitized
    assert "***:***" in sanitized

@pytest.mark.anyio
async def test_sqlite_async_engine_and_health_check(anyio_backend):
    reset_async_engine()
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    is_healthy, err = await check_db_connection(test_engine)
    assert is_healthy is True
    assert err is None
    await test_engine.dispose()
    reset_async_engine()

@pytest.mark.anyio
async def test_session_lifecycle_commit_and_rollback(anyio_backend):
    reset_async_engine()
    reset_session_factory()
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = get_async_session_factory(test_engine)

    # 1. Normal session commit flow
    async with session_factory() as session:
        res = await session.execute(text("SELECT 1"))
        assert res.scalar() == 1
        await session.commit()

    # 2. Rollback on simulated exception
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            raise RuntimeError("Simulated transaction fault")
    except RuntimeError:
        pass  # Rollback handled cleanly

    await test_engine.dispose()
    reset_async_engine()
    reset_session_factory()

def test_health_database_endpoint_in_memory():
    res = client.get("/api/v1/health/database")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "in_memory"
    assert data["backend"] == "in_memory"

def test_repository_selection_in_memory_default():
    orig_backend = settings.DATA_BACKEND
    try:
        settings.DATA_BACKEND = "in_memory"
        u_repo = get_user_repository()
        p_repo = get_product_repository()
        assert isinstance(u_repo, InMemoryUserRepository)
        assert isinstance(p_repo, InMemoryProductRepository)
    finally:
        settings.DATA_BACKEND = orig_backend

def test_repository_selection_postgres_requires_database_url():
    orig_backend = settings.DATA_BACKEND
    orig_url = settings.DATABASE_URL
    try:
        settings.DATA_BACKEND = "postgres"
        settings.DATABASE_URL = None
        with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
            get_user_repository()
    finally:
        settings.DATA_BACKEND = orig_backend
        settings.DATABASE_URL = orig_url

def test_repository_selection_postgres_with_url():
    orig_backend = settings.DATA_BACKEND
    orig_url = settings.DATABASE_URL
    try:
        settings.DATA_BACKEND = "postgres"
        settings.DATABASE_URL = "postgresql+asyncpg://postgres:pass@localhost:5432/postgres"
        u_repo = get_user_repository()
        p_repo = get_product_repository()
        assert isinstance(u_repo, PostgresUserRepository)
        assert isinstance(p_repo, PostgresProductRepository)
    finally:
        settings.DATA_BACKEND = orig_backend
        settings.DATABASE_URL = orig_url
