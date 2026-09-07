"""Tests for HybridClient HTTP-first, Browser fallback, and validation checks."""

from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest

from app.clients.browser_client import AsyncBrowserClient
from app.clients.http_client import AsyncHttpClient
from app.clients.hybrid_client import HybridClient
from app.core.config import Settings
from app.core.constants import ScrapingMode
from app.core.exceptions import NetworkError


@pytest.mark.asyncio
async def test_hybrid_client_http_mode_success():
    settings = Settings(ENVIRONMENT="testing")
    http_client = AsyncHttpClient(settings=settings)

    def mock_handler(request: httpx.Request):
        return httpx.Response(200, text="<html><body>Direct HTTP Content</body></html>", request=request)

    http_client._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

    hybrid = HybridClient(settings=settings, http_client=http_client)
    content, mode = await hybrid.fetch("https://www.daraz.pk/test", mode=ScrapingMode.HTTP)

    assert "Direct HTTP Content" in content
    assert mode == "http"
    await hybrid.close()


@pytest.mark.asyncio
async def test_hybrid_client_hybrid_fallback_on_incomplete_content():
    settings = Settings(ENVIRONMENT="testing")
    http_client = AsyncHttpClient(settings=settings)

    # Incomplete initial HTML missing hydration
    def mock_handler(request: httpx.Request):
        return httpx.Response(200, text="<html><body><div id='root'>Loading...</div></body></html>", request=request)

    http_client._client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))

    # Mock browser client
    browser_client = AsyncBrowserClient(settings=settings)
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body><div id='root'>Full Hydrated Content</div></body></html>")
    mock_page.url = "https://www.daraz.pk/test"
    mock_page.goto = AsyncMock()
    mock_page.close = AsyncMock()

    mock_context = AsyncMock()
    mock_context.cookies = AsyncMock(return_value=[])
    mock_context.new_page = AsyncMock(return_value=mock_page)

    browser_client.new_context = AsyncMock(return_value=mock_context)
    browser_client.new_page = AsyncMock(return_value=mock_page)
    browser_client.inspect_page_challenges = AsyncMock()

    hybrid = HybridClient(
        settings=settings,
        http_client=http_client,
        browser_client=browser_client,
        default_mode=ScrapingMode.HYBRID,
    )

    # Content validator checks that "Loading..." is not valid
    is_valid = lambda html: "Full Hydrated Content" in html

    content, mode = await hybrid.fetch(
        "https://www.daraz.pk/test",
        is_content_valid=is_valid,
    )

    assert "Full Hydrated Content" in content
    assert mode == "browser"
    await hybrid.close()
