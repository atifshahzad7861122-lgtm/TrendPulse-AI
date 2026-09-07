"""Unit tests for ProductIntelligenceEngine pipeline execution."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.crawling.engine import UniversalCrawlingEngine
from app.crawling.models import CrawlResponse, MarketplaceType
from app.intelligence.models import ExtractionStatus
from app.intelligence.pipeline import IntelligencePipelineConfig, ProductIntelligenceEngine


@pytest.mark.asyncio
async def test_intelligence_pipeline_single_extraction(tmp_path):
    snapshots_dir = str(tmp_path / "snapshots")
    config = IntelligencePipelineConfig(snapshots_dir=snapshots_dir)
    
    mock_crawler_engine = MagicMock(spec=UniversalCrawlingEngine)
    mock_crawler = MagicMock()
    mock_crawler_engine.crawler = mock_crawler

    html = """
    <html>
        <body>
            <span id="productTitle">Sony WH-1000XM4 Headphones</span>
            <span class="a-price"><span class="a-offscreen">$278.00</span></span>
            <span id="acrPopover"><span class="a-icon-alt">4.7 out of 5 stars</span></span>
            <span id="acrCustomerReviewText">5,000 ratings</span>
            <img id="landingImage" src="https://m.media-amazon.com/headphone.jpg" />
        </body>
    </html>
    """
    mock_resp = CrawlResponse(
        url="https://www.amazon.com/dp/B08N5WRWNW",
        status_code=200,
        html=html,
    )
    mock_crawler.crawl = AsyncMock(return_value=mock_resp)

    engine = ProductIntelligenceEngine(config=config, crawler_engine=mock_crawler_engine)
    res = await engine.extract_product("https://www.amazon.com/dp/B08N5WRWNW")

    assert res.success is True
    assert res.status == ExtractionStatus.SUCCESS
    assert res.product.title == "Sony WH-1000XM4 Headphones"
    assert res.product.price == 278.0
    assert res.snapshot is not None


@pytest.mark.asyncio
async def test_intelligence_pipeline_challenge_pauses(tmp_path):
    snapshots_dir = str(tmp_path / "snapshots")
    config = IntelligencePipelineConfig(snapshots_dir=snapshots_dir)
    
    mock_crawler_engine = MagicMock(spec=UniversalCrawlingEngine)
    mock_crawler = MagicMock()
    mock_crawler_engine.crawler = mock_crawler

    # Blocked response
    mock_resp = CrawlResponse(
        url="https://www.ebay.com/itm/123",
        status_code=403,
        html="<html><body>Access Denied</body></html>",
    )
    mock_crawler.crawl = AsyncMock(return_value=mock_resp)

    engine = ProductIntelligenceEngine(config=config, crawler_engine=mock_crawler_engine)
    res = await engine.extract_product("https://www.ebay.com/itm/123")

    assert res.success is False
    assert res.status == ExtractionStatus.CHALLENGE
    assert any("Bot challenge detected" in e for e in res.errors)


@pytest.mark.asyncio
async def test_intelligence_pipeline_batch_failure_isolation(tmp_path):
    snapshots_dir = str(tmp_path / "snapshots")
    config = IntelligencePipelineConfig(snapshots_dir=snapshots_dir, max_concurrency=2)
    
    mock_crawler_engine = MagicMock(spec=UniversalCrawlingEngine)
    mock_crawler = MagicMock()
    mock_crawler_engine.crawler = mock_crawler

    async def mock_crawl(req):
        if "item1" in req.url:
            return CrawlResponse(
                url=req.url,
                status_code=200,
                html="<html><body><h1 class='pdp-mod-product-badge-title'>Item 1</h1><span class='pdp-price'>Rs. 100</span></body></html>",
            )
        else:
            return CrawlResponse(
                url=req.url,
                status_code=404,
                html="<html><body>Not Found</body></html>",
            )

    mock_crawler.crawl = AsyncMock(side_effect=mock_crawl)
    engine = ProductIntelligenceEngine(config=config, crawler_engine=mock_crawler_engine)

    targets = [
        "https://www.daraz.pk/products/item1-i1.html",
        "https://www.daraz.pk/products/item2-i2.html",
    ]
    results = await engine.extract_batch(targets)

    assert len(results) == 2
    assert results[0].success is True
    assert results[1].status == ExtractionStatus.NOT_FOUND
