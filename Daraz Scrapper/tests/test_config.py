"""Tests for configuration management and environment parsing."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.constants import Environment
from app.core.exceptions import (
    ConfigurationError,
    NetworkError,
    RateLimitError,
    BrowserError,
    ParserError,
    ScraperError,
    StorageError,
    CrawlError,
)


def test_default_settings():
    settings = Settings()
    assert settings.ENVIRONMENT in [Environment.DEVELOPMENT, Environment.TESTING, Environment.STAGING, Environment.PRODUCTION]
    assert settings.HTTP_TIMEOUT > 0
    assert settings.BROWSER_TIMEOUT > 0
    assert settings.MAX_CONCURRENCY >= 1
    assert settings.REQUEST_DELAY_MIN <= settings.REQUEST_DELAY_MAX
    assert settings.CHECKPOINT_INTERVAL >= 1


def test_custom_settings():
    settings = Settings(
        ENVIRONMENT=Environment.PRODUCTION,
        LOG_LEVEL="WARNING",
        HTTP_TIMEOUT=15.0,
        MAX_CONCURRENCY=10,
        REQUEST_DELAY_MIN=2.0,
        REQUEST_DELAY_MAX=5.0,
    )
    assert settings.ENVIRONMENT == Environment.PRODUCTION
    assert settings.LOG_LEVEL == "WARNING"
    assert settings.HTTP_TIMEOUT == 15.0
    assert settings.MAX_CONCURRENCY == 10
    assert settings.REQUEST_DELAY_MIN == 2.0
    assert settings.REQUEST_DELAY_MAX == 5.0


def test_invalid_log_level():
    with pytest.raises(ValidationError):
        Settings(LOG_LEVEL="INVALID_LEVEL")


def test_invalid_delay_bounds():
    with pytest.raises(ValidationError):
        Settings(REQUEST_DELAY_MIN=5.0, REQUEST_DELAY_MAX=2.0)


def test_get_settings_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_exception_hierarchy():
    # Verify inheritance
    assert issubclass(ConfigurationError, ScraperError)
    assert issubclass(NetworkError, ScraperError)
    assert issubclass(RateLimitError, ScraperError)
    assert issubclass(BrowserError, ScraperError)
    assert issubclass(ParserError, ScraperError)
    assert issubclass(StorageError, ScraperError)
    assert issubclass(CrawlError, ScraperError)

    net_err = NetworkError("Failed to fetch", status_code=503, url="https://example.com")
    assert net_err.status_code == 503
    assert net_err.url == "https://example.com"
    assert "status_code" in net_err.details
    assert "https://example.com" in str(net_err)
