"""Unit tests for UniversalCrawlingEngine orchestration across marketplaces."""

from unittest.mock import AsyncMock
import pytest

from app.crawling.config import CrawlCacheMode, UniversalCrawlerConfig
from app.crawling.engine import UniversalCrawlingEngine
from app.crawling.models import CrawlContentType, CrawlRequest, CrawlResponse, MarketplaceType
from app.storage.repository import InMemoryStorage


@pytest.mark.asyncio
async def test_engine_resolves_adapters_and_crawls():
    storage = InMemoryStorage()
    config = UniversalCrawlerConfig(cache_mode=CrawlCacheMode.DISABLED)
    crawler_mock = AsyncMock()
    
    # Mock responses for different marketplaces
    amz_html = '<html><body><h1 id="productTitle">Echo Dot</h1><span class="a-price"><span class="a-offscreen">$49.99</span></span></body></html>'
    daraz_html = '<html><head><script type="application/ld+json">{"@type":"Product","name":"Daraz Wireless Earbuds","image":"https://img.daraz.pk/p/1.jpg"}</script></head><body></body></html>'

    async def mock_crawl(req: CrawlRequest):
        if "amazon.com" in req.url:
            return CrawlResponse(url=req.url, status_code=200, html=amz_html)
        elif "daraz.pk" in req.url:
            return CrawlResponse(url=req.url, status_code=200, html=daraz_html)
        return CrawlResponse(url=req.url, status_code=200, html="<html>Generic</html>")

    crawler_mock.crawl.side_effect = mock_crawl

    engine = UniversalCrawlingEngine(config=config, crawler=crawler_mock, storage=storage)

    # 1. Amazon crawl
    res_amz = await engine.crawl_product("https://www.amazon.com/dp/B07XJ8C8F5")
    assert res_amz.success is True
    assert res_amz.marketplace == MarketplaceType.AMAZON
    assert res_amz.product.title == "Echo Dot"
    assert res_amz.product.price == 49.99

    # 2. Daraz crawl
    res_daraz = await engine.crawl_product("https://www.daraz.pk/products/earbuds-i123456.html")
    assert res_daraz.success is True
    assert res_daraz.marketplace == MarketplaceType.DARAZ
    assert res_daraz.product.title == "Daraz Wireless Earbuds"


@pytest.mark.asyncio
async def test_engine_challenge_detection_pauses_and_checkpoints():
    storage = InMemoryStorage()
    config = UniversalCrawlerConfig(cache_mode=CrawlCacheMode.DISABLED)
    crawler_mock = AsyncMock()

    # Cloudflare challenge HTML
    cf_html = '<html><form id="challenge-form" action="?__cf_chl_f_tk=123"></form></html>'
    crawler_mock.crawl.return_value = CrawlResponse(
        url="https://www.amazon.com/dp/B00BLOCKED",
        status_code=200,
        html=cf_html,
    )

    engine = UniversalCrawlingEngine(config=config, crawler=crawler_mock, storage=storage)

    res = await engine.crawl_product("https://www.amazon.com/dp/B00BLOCKED")
    assert res.challenge_detected is True
    assert res.status.value == "manual_intervention"
    assert res.success is False

    # Checkpoint was saved
    resumable = engine.recovery.list_resumable_jobs()
    assert len(resumable) >= 1
