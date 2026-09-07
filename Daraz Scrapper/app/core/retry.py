"""Centralized retry policy, classification, and backoff utilities."""

import asyncio
import functools
import random
from typing import Any, Callable, Coroutine, Optional, Set, Tuple, Type, TypeVar
import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ChallengeDetectedError,
    CircuitBreakerOpenError,
    ConfigurationError,
    NetworkError,
    ParserError,
    RateLimitError,
    ScraperError,
    ValidationError,
)
from app.core.logging import logger
from app.core.runtime import runtime_metrics

T = TypeVar("T")

# HTTP status codes that are candidates for retrying
RETRYABLE_STATUS_CODES: Set[int] = {408, 429, 500, 502, 503, 504}

# Exceptions that are inherently non-retryable
NON_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ChallengeDetectedError,
    CircuitBreakerOpenError,
    ConfigurationError,
    ParserError,
    ValidationError,
    ValueError,
    KeyError,
)

# Exceptions that are retryable
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    RateLimitError,
    NetworkError,
)


def is_retryable_exception(exc: Exception) -> bool:
    """Determine if a raised exception is eligible for retry."""
    if isinstance(exc, NON_RETRYABLE_EXCEPTIONS):
        return False

    if isinstance(exc, NetworkError) and exc.status_code is not None:
        if exc.status_code in {400, 401, 403}:
            return False
        return exc.status_code in RETRYABLE_STATUS_CODES

    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in {400, 401, 403}:
            return False
        return exc.response.status_code in RETRYABLE_STATUS_CODES

    if isinstance(exc, RETRYABLE_EXCEPTIONS):
        return True

    return False


def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0, jitter: bool = True) -> float:
    """Compute exponential backoff delay with optional full jitter."""
    delay = min(max_delay, base_delay * (2 ** attempt))
    if jitter:
        delay = random.uniform(0.5 * delay, delay)
    return delay


def with_retry(
    max_retries: Optional[int] = None,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    settings: Optional[Settings] = None,
):
    """Decorator for retrying async functions upon encountering retryable errors."""
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            cfg = settings or get_settings()
            retries = max_retries if max_retries is not None else cfg.MAX_RETRIES

            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    attempt += 1
                    if not is_retryable_exception(exc) or attempt > retries:
                        logger.warning(
                            f"Operation failed permanently or exhausted retries ({attempt}/{retries}): {exc}",
                            extra={"event": "retry_exhausted", "error": str(exc), "status": "failed"},
                        )
                        raise

                    await runtime_metrics.record_retry()
                    backoff = calculate_backoff(attempt - 1, base_delay=base_delay, max_delay=max_delay)
                    logger.info(
                        f"Retrying operation ({attempt}/{retries}) after {backoff:.2f}s due to: {exc}",
                        extra={
                            "event": "retry_attempt",
                            "attempt": attempt,
                            "max_retries": retries,
                            "backoff_s": backoff,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(backoff)

        return wrapper
    return decorator
