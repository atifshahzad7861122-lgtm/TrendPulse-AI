"""Keyword search crawling strategy."""

from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import CrawlContentType, CrawlRequest, UniversalCrawlResult
from app.crawling.strategies.base import BaseCrawlStrategy


class SearchCrawlStrategy(BaseCrawlStrategy):
    """
    Crawls keyword search pages and extracts product candidate listings.
    """

    @property
    def name(self) -> str:
        return "search"

    async def execute(
        self,
        request: CrawlRequest,
        adapter: BaseMarketplaceAdapterInterface,
        crawler: UniversalCrawlerInterface,
    ) -> UniversalCrawlResult:
        req = request.model_copy(update={"content_type": CrawlContentType.SEARCH})
        response = await crawler.crawl(req)
        return adapter.parse_response(response, CrawlContentType.SEARCH)
