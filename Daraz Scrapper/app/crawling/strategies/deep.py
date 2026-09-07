"""Deep crawling strategy with BFS/DFS graph traversal and domain boundary constraints."""

import asyncio
from collections import deque
from typing import Deque, Dict, List, Optional, Set
from urllib.parse import urlparse

from app.crawling.interfaces import (
    BaseMarketplaceAdapterInterface,
    UniversalCrawlerInterface,
)
from app.crawling.models import (
    CrawlContentType,
    CrawlRequest,
    CrawlStatus,
    DeepCrawlNode,
    UniversalCrawlResult,
)
from app.crawling.strategies.base import BaseCrawlStrategy
from app.models.product import Product
from app.core.logging import logger


class DeepCrawlStrategy(BaseCrawlStrategy):
    """
    Executes recursive graph-based crawling with depth constraints,
    domain boundaries, and duplicate filtering.
    """

    def __init__(self, max_depth: int = 2, max_pages: int = 50, mode: str = "bfs"):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.mode = mode.lower()  # 'bfs' or 'dfs'

    @property
    def name(self) -> str:
        return "deep"

    async def execute(
        self,
        request: CrawlRequest,
        adapter: BaseMarketplaceAdapterInterface,
        crawler: UniversalCrawlerInterface,
    ) -> UniversalCrawlResult:
        root_domain = urlparse(request.url).netloc.lower()
        visited: Set[str] = set()
        queue: Deque[DeepCrawlNode] = deque()
        queue.append(DeepCrawlNode(url=request.url, depth=0))

        all_products: List[Product] = []
        all_discovered: List[str] = []
        pages_crawled = 0
        last_result = None

        while queue and pages_crawled < self.max_pages:
            node = queue.popleft() if self.mode == "bfs" else queue.pop()
            if node.url in visited or node.depth > self.max_depth:
                continue

            visited.add(node.url)
            pages_crawled += 1

            req = request.model_copy(update={"url": node.url, "depth": node.depth})
            try:
                response = await crawler.crawl(req)
                content_type = adapter.detect_content_type(node.url)
                result = adapter.parse_response(response, content_type)
                last_result = result

                if result.product:
                    all_products.append(result.product)
                if result.products:
                    all_products.extend(result.products)

                # Queue newly discovered links if within depth limit
                if node.depth < self.max_depth and result.discovered_urls:
                    for next_url in result.discovered_urls:
                        if next_url not in all_discovered:
                            all_discovered.append(next_url)
                        # Domain boundary check
                        next_domain = urlparse(next_url).netloc.lower()
                        if next_domain == root_domain and next_url not in visited:
                            queue.append(DeepCrawlNode(
                                url=next_url,
                                depth=node.depth + 1,
                                parent_url=node.url,
                            ))
            except Exception as e:
                logger.warning(f"Deep crawl node failed for {node.url}: {e}")

        if last_result:
            return last_result.model_copy(update={
                "products": all_products,
                "discovered_urls": all_discovered,
                "status": CrawlStatus.COMPLETED,
            })

        req = request.model_copy()
        resp = await crawler.crawl(req)
        return adapter.parse_response(resp, request.content_type)
