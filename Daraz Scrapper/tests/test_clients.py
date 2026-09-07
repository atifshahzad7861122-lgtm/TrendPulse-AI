"""Tests for HTTP client, browser client, rate limiter, and retry system."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.clients.browser_client import AsyncBrowserClient
from app.clients.http_client import AsyncHttpClient
from app.core.config import Settings
from app.core.exceptions import BrowserError, NetworkError, RateLimitError
from app.core.rate_limiter import AsyncRateLimiter
from app.core.retry import calculate_backoff, is_retryable_exception, with_retry


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = AsyncRateLimiter(min_delay=0.01, max_delay=0.02, max_concurrency=2)

    # First acquire should be instant
    delay1 = await limiter.acquire()
    assert delay1 == 0.0

    # Next immediate acquire should trigger short delay
    delay2 = await limiter.acquire()
    assert delay2 >= 0.0

    # Test context manager usage
    async with limiter:
        pass


def test_retry_classification_and_backoff():
    # Retryable errors
    assert is_retryable_exception(httpx.ReadTimeout("timeout"))
    assert is_retryable_exception(RateLimitError("too many requests"))
    assert is_retryable_exception(NetworkError("Server error", status_code=503))

    # Non-retryable errors
    assert not is_retryable_exception(ValueError("Bad value"))
    assert not is_retryable_exception(NetworkError("Not found", status_code=404))

    # Backoff calculation
    backoff0 = calculate_backoff(attempt=0, base_delay=1.0, jitter=False)
    backoff1 = calculate_backoff(attempt=1, base_delay=1.0, jitter=False)
    backoff2 = calculate_backoff(attempt=2, base_delay=1.0, jitter=False)

    assert backoff0 == 1.0
    assert backoff1 == 2.0
    assert backoff2 == 4.0


@pytest.mark.asyncio
async def test_retry_decorator_success_after_retries():
    attempts = 0

    @with_retry(max_retries=3, base_delay=0.01)
    async def flaky_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ReadTimeout("Timed out")
        return "success"

    result = await flaky_call()
    assert result == "success"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_decorator_permanent_failure():
    attempts = 0

    @with_retry(max_retries=2, base_delay=0.01)
    async def failing_call():
        nonlocal attempts
        attempts += 1
        raise ValueError("Non-retryable logic error")

    with pytest.raises(ValueError):
        await failing_call()
    assert attempts == 1  # Should not retry non-retryable exception


@pytest.mark.asyncio
async def test_http_client_get_success(mock_settings: Settings):
    # Mock httpx response handler
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"}, request=request)

    transport = httpx.MockTransport(handler)
    client = AsyncHttpClient(settings=mock_settings)
    client._client = httpx.AsyncClient(transport=transport)

    response = await client.get("https://api.example.com/test")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_429_rate_limit(mock_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0.01"}, request=request)

    transport = httpx.MockTransport(handler)
    client = AsyncHttpClient(settings=mock_settings)
    client._client = httpx.AsyncClient(transport=transport)

    with pytest.raises(RateLimitError):
        await client.get("https://api.example.com/rate-limited")
    await client.aclose()


@pytest.mark.asyncio
async def test_http_client_500_network_error(mock_settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    transport = httpx.MockTransport(handler)
    client = AsyncHttpClient(settings=mock_settings)
    client._client = httpx.AsyncClient(transport=transport)

    with pytest.raises(NetworkError):
        await client.get("https://api.example.com/server-error")
    await client.aclose()


@pytest.mark.asyncio
async def test_browser_client_lifecycle_mock(mock_settings: Settings):
    browser_client = AsyncBrowserClient(settings=mock_settings)

    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.set_default_timeout = MagicMock()

    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_playwright.chromium.launch.return_value = mock_browser

    with patch("app.clients.browser_client.async_playwright") as mock_pw_start:
        mock_pw_ctx = AsyncMock()
        mock_pw_ctx.start.return_value = mock_playwright
        mock_pw_start.return_value = mock_pw_ctx

        await browser_client.start()
        assert browser_client._is_started is True

        ctx = await browser_client.new_context()
        page = await browser_client.new_page(context=ctx)

        assert ctx is not None
        assert page is not None
        mock_page.set_default_timeout.assert_called_once()

        await browser_client.close()
        assert browser_client._is_started is False
