"""Standard single URL crawl strategy with automatic content detection."""

from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import CrawlContentType, CrawlRequest, UniversalCrawlResult
from app.crawling.strategies.base import BaseCrawlStrategy


class StandardCrawlStrategy(BaseCrawlStrategy):
    """
    Executes a standard single-page crawl and invokes the marketplace adapter to parse entities.
    """

    @property
    def name(self) -> str:
        return "standard"

    async def execute(
        self,
        request: CrawlRequest,
        adapter: BaseMarketplaceAdapterInterface,
        crawler: UniversalCrawlerInterface,
    ) -> UniversalCrawlResult:
        response = await crawler.crawl(request)
        content_type = request.content_type
        if content_type == CrawlContentType.GENERIC:
            content_type = adapter.detect_content_type(request.url)

        return adapter.parse_response(response, content_type)
