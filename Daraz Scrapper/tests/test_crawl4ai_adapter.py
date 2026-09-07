"""Unit tests for Crawl4AIAdapter behavior and interface conformity."""

from unittest.mock import AsyncMock, patch
import pytest

from app.crawling.adapters.crawl4ai_adapter import Crawl4AIAdapter
from app.crawling.config import CrawlCacheMode, UniversalCrawlerConfig
from app.crawling.interfaces import UniversalCrawlerInterface
from app.crawling.models import CrawlRequest, CrawlResponse


def test_crawl4ai_adapter_implements_interface():
    adapter = Crawl4AIAdapter()
    assert isinstance(adapter, UniversalCrawlerInterface)


@pytest.mark.asyncio
async def test_crawl4ai_adapter_http_success():
    config = UniversalCrawlerConfig(cache_mode=CrawlCacheMode.DISABLED, enable_http_first=True)
    adapter = Crawl4AIAdapter(config=config)
    
    # Mock http client response
    mock_resp = CrawlResponse(
        url="https://www.amazon.com/dp/B08N5WRWNW",
        status_code=200,
        html="<html><body><div class='a-price'>$100</div></body></html>",
        source_engine="http",
    )
    adapter.http_client.fetch = AsyncMock(return_value=mock_resp)

    req = CrawlRequest(url="https://www.amazon.com/dp/B08N5WRWNW")
    resp = await adapter.crawl(req)

    assert resp.status_code == 200
    assert resp.source_engine == "http"
    assert "a-price" in resp.html


@pytest.mark.asyncio
async def test_crawl4ai_adapter_crawl_many():
    config = UniversalCrawlerConfig(cache_mode=CrawlCacheMode.DISABLED, auto_browser_fallback=False)
    adapter = Crawl4AIAdapter(config=config)

    mock_resp = CrawlResponse(
        url="https://www.ebay.com/itm/123",
        status_code=200,
        html="<html><body>Item</body></html>",
    )
    adapter.http_client.fetch = AsyncMock(return_value=mock_resp)

    requests = [
        CrawlRequest(url="https://www.ebay.com/itm/123"),
        CrawlRequest(url="https://www.ebay.com/itm/456"),
    ]
    responses = await adapter.crawl_many(requests)
    assert len(responses) == 2
    assert responses[0].status_code == 200
