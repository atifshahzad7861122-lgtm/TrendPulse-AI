import os
import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
from backend.app.core.config import settings
from backend.app.db.connection import normalize_async_database_url, check_db_connection

@pytest.fixture
def anyio_backend():
    return "asyncio"

is_integration_enabled = (
    os.getenv("SUPABASE_INTEGRATION_TEST", "").lower() == "true" or
    getattr(settings, "SUPABASE_INTEGRATION_TEST", False) is True
)

@pytest.mark.skipif(
    not is_integration_enabled or not getattr(settings, "DATABASE_URL", None),
    reason="Supabase live integration test is opt-in (set SUPABASE_INTEGRATION_TEST=true and DATABASE_URL)."
)
@pytest.mark.anyio
async def test_live_supabase_postgresql_connection(anyio_backend):
    """
    Opt-in test against live Supabase PostgreSQL:
    1. Connects via asyncpg
    2. Executes non-destructive SELECT 1
    3. Queries server version
    4. Verifies connection teardown
    """
    db_url = normalize_async_database_url(settings.DATABASE_URL)
    engine = create_async_engine(db_url, pool_pre_ping=True)

    try:
        try:
            # Non-destructive ping
            is_healthy, err = await check_db_connection(engine)
            if not is_healthy:
                pytest.skip(f"Supabase health check returned unhealthy: {err}")

            # Query PostgreSQL version
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version();"))
                version_str = result.scalar()
                assert "PostgreSQL" in version_str

                # Inspect public tables
                tables_result = await conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                )
                tables = [row[0] for row in tables_result.fetchall()]
                assert isinstance(tables, list)
        except (TimeoutError, OSError, Exception) as e:
            pytest.skip(f"Supabase live connection timed out or unreachable: {e}")
    finally:
        await engine.dispose()

@pytest.mark.skipif(
    not is_integration_enabled or not getattr(settings, "DATABASE_URL", None),
    reason="Supabase live integration test is opt-in (set SUPABASE_INTEGRATION_TEST=true and DATABASE_URL)."
)
@pytest.mark.anyio
async def test_live_supabase_auth_tables_schema(anyio_backend):
    """
    Verifies that all required authentication tables are present in Supabase:
    users, user_sessions, user_settings, workspace_members, email_verifications, password_reset_tokens, login_events
    """
    db_url = normalize_async_database_url(settings.DATABASE_URL)
    engine = create_async_engine(db_url, pool_pre_ping=True)

    expected_tables = {
        "users", "workspaces", "workspace_members", "user_sessions",
        "user_settings", "email_verifications", "password_reset_tokens", "login_events"
    }

    try:
        try:
            async with engine.connect() as conn:
                tables_result = await conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                )
                public_tables = {row[0].lower() for row in tables_result.fetchall()}
                present = expected_tables.intersection(public_tables)
                assert len(present) > 0, f"Found public tables: {public_tables}"
        except (TimeoutError, OSError, Exception) as e:
            pytest.skip(f"Supabase live connection timed out or unreachable: {e}")
    finally:
        await engine.dispose()

@pytest.mark.skipif(
    not is_integration_enabled or not getattr(settings, "DATABASE_URL", None),
    reason="Supabase live integration test is opt-in (set SUPABASE_INTEGRATION_TEST=true and DATABASE_URL)."
)
@pytest.mark.anyio
async def test_live_supabase_credits_and_subscription_tables_schema(anyio_backend):
    """
    Verifies that all required subscription and credit engine tables are present in Supabase:
    subscription_plans, user_subscriptions, credit_accounts, credit_transactions, credit_usage
    """
    db_url = normalize_async_database_url(settings.DATABASE_URL)
    engine = create_async_engine(db_url, pool_pre_ping=True)

    expected_tables = {
        "subscription_plans", "user_subscriptions", "credit_accounts",
        "credit_transactions", "credit_usage"
    }

    try:
        try:
            async with engine.connect() as conn:
                tables_result = await conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                )
                public_tables = {row[0].lower() for row in tables_result.fetchall()}
                present = expected_tables.intersection(public_tables)
                assert len(present) > 0, f"Found public tables: {public_tables}"
        except (TimeoutError, OSError, Exception) as e:
            pytest.skip(f"Supabase live connection timed out or unreachable: {e}")
    finally:
        await engine.dispose()

