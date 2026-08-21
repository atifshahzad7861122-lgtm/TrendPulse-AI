import os
import re
import pytest
from pathlib import Path
from backend.app.db.models import Base

EXPECTED_TABLES = [
    "users",
    "workspaces",
    "workspace_members",
    "user_sessions",
    "email_verifications",
    "password_reset_tokens",
    "login_events",
    "user_settings",
    "products",
    "categories",
    "platforms",
    "watchlists",
    "alerts",
    "notifications",
    "reports",
    "data_sources",
    "subscription_plans",
    "user_subscriptions",
    "credit_accounts",
    "credit_transactions",
    "credit_usage"
]

def test_migration_file_exists_and_readable():
    migration_path = Path(__file__).parent.parent / "migrations" / "001_initial_schema.sql"
    assert migration_path.exists(), "Migration file 001_initial_schema.sql not found!"
    assert migration_path.stat().st_size > 1000, "Migration file is too small or empty!"

def test_all_21_tables_in_migration_sql():
    migration_path = Path(__file__).parent.parent / "migrations" / "001_initial_schema.sql"
    content = migration_path.read_text(encoding="utf-8").lower()

    for table_name in EXPECTED_TABLES:
        pattern = rf"create\s+table\s+(if\s+not\s+exists\s+)?{table_name}\s*\("
        match = re.search(pattern, content)
        assert match is not None, f"Table '{table_name}' definition missing in 001_initial_schema.sql"

def test_orm_models_match_migration_tables():
    orm_table_names = [table.name for table in Base.metadata.tables.values()]
    for table_name in EXPECTED_TABLES:
        assert table_name in orm_table_names, f"ORM model definition missing for table '{table_name}'"

def test_credit_system_critical_columns_in_migration():
    migration_path = Path(__file__).parent.parent / "migrations" / "001_initial_schema.sql"
    content = migration_path.read_text(encoding="utf-8")

    # Verify credit_accounts
    assert "current_balance" in content
    assert "lifetime_granted" in content
    assert "lifetime_used" in content

    # Verify credit_transactions
    assert "balance_before" in content
    assert "balance_after" in content
    assert "transaction_type" in content

    # Verify credit_usage
    assert "credits_used" in content
    assert "feature" in content

    # Verify user_subscriptions
    assert "plan_id" in content
    assert "current_period_end" in content

def test_idempotent_ddl_syntax():
    migration_path = Path(__file__).parent.parent / "migrations" / "001_initial_schema.sql"
    content = migration_path.read_text(encoding="utf-8")

    # Ensure IF NOT EXISTS is used
    assert "CREATE TABLE IF NOT EXISTS" in content
    assert "CREATE INDEX IF NOT EXISTS" in content
