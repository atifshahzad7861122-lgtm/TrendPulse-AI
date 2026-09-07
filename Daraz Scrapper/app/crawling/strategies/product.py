"""Product detail page crawl strategy."""

from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import CrawlContentType, CrawlRequest, UniversalCrawlResult
from app.crawling.strategies.base import BaseCrawlStrategy


class ProductCrawlStrategy(BaseCrawlStrategy):
    """
    Crawls and extracts full product information from PDPs.
    """

    @property
    def name(self) -> str:
        return "product"

    async def execute(
        self,
        request: CrawlRequest,
        adapter: BaseMarketplaceAdapterInterface,
        crawler: UniversalCrawlerInterface,
    ) -> UniversalCrawlResult:
        req = request.model_copy(update={"content_type": CrawlContentType.PRODUCT})
        response = await crawler.crawl(req)
        return adapter.parse_response(response, CrawlContentType.PRODUCT)
