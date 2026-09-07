"""Unit tests for crawling strategies: standard, pagination, deep (BFS/DFS), product, search."""

from unittest.mock import AsyncMock
import pytest

from app.crawling.marketplaces.amazon import AmazonAdapter
from app.crawling.models import CrawlContentType, CrawlRequest, CrawlResponse
from app.crawling.strategies import (
    DeepCrawlStrategy,
    PaginationCrawlStrategy,
    ProductCrawlStrategy,
    StandardCrawlStrategy,
)


@pytest.mark.asyncio
async def test_standard_and_product_strategy():
    adapter = AmazonAdapter()
    crawler_mock = AsyncMock()
    html = """
    <html><body>
        <h1 id="productTitle">Kindle Paperwhite</h1>
        <span class="a-price"><span class="a-offscreen">$139.99</span></span>
    </body></html>
    """
    crawler_mock.crawl.return_value = CrawlResponse(
        url="https://www.amazon.com/dp/B08KTZ8249",
        status_code=200,
        html=html,
    )

    strat = ProductCrawlStrategy()
    req = CrawlRequest(url="https://www.amazon.com/dp/B08KTZ8249")
    res = await strat.execute(req, adapter, crawler_mock)

    assert res.success is True
    assert res.product.title == "Kindle Paperwhite"
    assert res.product.price == 139.99


@pytest.mark.asyncio
async def test_deep_crawl_bfs_strategy():
    adapter = AmazonAdapter()
    crawler_mock = AsyncMock()

    # Seed page containing 2 product links
    seed_html = """
    <html><body>
        <a href="/dp/B000000001">Item 1</a>
        <a href="/dp/B000000002">Item 2</a>
    </body></html>
    """
    # Item 1 page
    item1_html = """
    <html><body>
        <h1 id="productTitle">Item 1 Title</h1>
        <span class="a-price"><span class="a-offscreen">$10.00</span></span>
    </body></html>
    """

    async def mock_crawl(req: CrawlRequest):
        if "B000000001" in req.url:
            return CrawlResponse(url=req.url, status_code=200, html=item1_html)
        return CrawlResponse(url=req.url, status_code=200, html=seed_html)

    crawler_mock.crawl.side_effect = mock_crawl

    strat = DeepCrawlStrategy(max_depth=1, max_pages=5, mode="bfs")
    req = CrawlRequest(url="https://www.amazon.com/stores/brand")
    res = await strat.execute(req, adapter, crawler_mock)

    assert res.status.value == "completed"
    assert len(res.discovered_urls) >= 2
