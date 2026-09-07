"""Pagination crawl strategy for multi-page catalog and search traversal."""

from typing import List
from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import CrawlContentType, CrawlRequest, UniversalCrawlResult
from app.crawling.strategies.base import BaseCrawlStrategy
from app.models.product import Product


class PaginationCrawlStrategy(BaseCrawlStrategy):
    """
    Traverses paginated search or category pages up to max_pages.
    """

    def __init__(self, max_pages: int = 5):
        self.max_pages = max(1, max_pages)

    @property
    def name(self) -> str:
        return "pagination"

    async def execute(
        self,
        request: CrawlRequest,
        adapter: BaseMarketplaceAdapterInterface,
        crawler: UniversalCrawlerInterface,
    ) -> UniversalCrawlResult:
        all_discovered: List[str] = []
        all_products: List[Product] = []
        last_result = None

        for page_num in range(1, self.max_pages + 1):
            if "page=" in request.url:
                page_url = request.url
            else:
                sep = "&" if "?" in request.url else "?"
                page_url = f"{request.url}{sep}page={page_num}"

            req = request.model_copy(update={"url": page_url})
            response = await crawler.crawl(req)
            result = adapter.parse_response(response, request.content_type)
            last_result = result

            if result.discovered_urls:
                for u in result.discovered_urls:
                    if u not in all_discovered:
                        all_discovered.append(u)
            if result.products:
                all_products.extend(result.products)

            # Stop condition: no items discovered on this page
            if not result.discovered_urls and not result.products:
                break

        if last_result:
            return last_result.model_copy(update={
                "discovered_urls": all_discovered,
                "products": all_products,
            })

        req = request.model_copy()
        resp = await crawler.crawl(req)
        return adapter.parse_response(resp, request.content_type)
