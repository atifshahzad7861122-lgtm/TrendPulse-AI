"""Centralized exception hierarchy for the scraper."""

from typing import Any, Dict, Optional


class ScraperError(Exception):
    """Base exception for all scraper-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(ScraperError):
    """Raised when application or module configuration is invalid or missing."""
    pass


class NetworkError(ScraperError):
    """Raised when an HTTP or low-level network operation fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if status_code is not None:
            details["status_code"] = status_code
        if url is not None:
            details["url"] = url
        super().__init__(message, details=details)
        self.status_code = status_code
        self.url = url


class RateLimitError(ScraperError):
    """Raised when client or remote server rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(message, details=details)
        self.retry_after = retry_after


class ChallengeDetectedError(ScraperError):
    """Raised when an anti-bot challenge (CAPTCHA, Cloudflare, Akamai, punish page) is detected."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        challenge_type: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if url:
            details["url"] = url
        if challenge_type:
            details["challenge_type"] = challenge_type
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details=details)
        self.url = url
        self.challenge_type = challenge_type
        self.status_code = status_code


class CircuitBreakerOpenError(ScraperError):
    """Raised when an operation is blocked by an open circuit breaker."""

    def __init__(self, message: str, reset_timeout: float, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["reset_timeout"] = reset_timeout
        super().__init__(message, details=details)
        self.reset_timeout = reset_timeout


class ProxyError(ScraperError):
    """Raised when proxy connection, rotation, or authentication fails."""
    pass


class SessionError(ScraperError):
    """Raised when session creation, persistence, or restoration fails."""
    pass


class CheckpointError(ScraperError):
    """Raised when saving or restoring a crawl checkpoint fails."""
    pass


class BrowserError(ScraperError):
    """Raised when browser automation (Playwright/headless) experiences a failure."""
    pass


class ParserError(ScraperError):
    """Raised when page extraction or parsing fails."""
    pass


class ValidationError(ScraperError):
    """Raised when extracted data fails model or schema validation."""
    pass


class StorageError(ScraperError):
    """Raised when saving, updating or retrieving records from storage fails."""
    pass


class CrawlError(ScraperError):
    """Raised when crawl job lifecycle or execution encounters an unrecoverable failure."""
    pass
