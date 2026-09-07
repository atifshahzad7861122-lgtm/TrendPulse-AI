"""Category exploration and product discovery strategy."""

from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import CrawlContentType, CrawlRequest, UniversalCrawlResult
from app.crawling.strategies.base import BaseCrawlStrategy


class CategoryCrawlStrategy(BaseCrawlStrategy):
    """
    Crawls category pages and extracts subcategories and product URLs.
    """

    @property
    def name(self) -> str:
        return "category"

    async def execute(
        self,
        request: CrawlRequest,
        adapter: BaseMarketplaceAdapterInterface,
        crawler: UniversalCrawlerInterface,
    ) -> UniversalCrawlResult:
        req = request.model_copy(update={"content_type": CrawlContentType.CATEGORY})
        response = await crawler.crawl(req)
        return adapter.parse_response(response, CrawlContentType.CATEGORY)
