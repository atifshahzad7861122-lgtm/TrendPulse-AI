"""Pytest configuration and global fixtures."""

import pytest
from app.core.config import Settings
from app.core.constants import Environment
from app.storage.repository import InMemoryStorage


@pytest.fixture
def mock_settings() -> Settings:
    """Fixture providing isolated mock settings."""
    return Settings(
        ENVIRONMENT=Environment.TESTING,
        LOG_LEVEL="DEBUG",
        DATABASE_URL="sqlite:///:memory:",
        HTTP_TIMEOUT=5.0,
        BROWSER_TIMEOUT=10.0,
        MAX_CONCURRENCY=3,
        MAX_RETRIES=2,
        REQUEST_DELAY_MIN=0.01,
        REQUEST_DELAY_MAX=0.05,
        CHECKPOINT_INTERVAL=10,
    )


@pytest.fixture
def storage() -> InMemoryStorage:
    """Fixture providing fresh in-memory storage."""
    return InMemoryStorage()
