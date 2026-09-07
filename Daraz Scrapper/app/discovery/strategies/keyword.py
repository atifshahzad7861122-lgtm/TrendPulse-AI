"""Keyword-based search discovery strategy for Daraz marketplace products."""

from typing import List, Optional
from urllib.parse import urlencode, urljoin

from app.core.logging import logger
from app.discovery.client import DarazDiscoveryClient
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config
from app.discovery.normalizer import normalize_search_keyword
from app.discovery.parser import DarazHTMLParser
from app.discovery.queue import ProductTargetQueue
from app.discovery.strategies.pagination import PaginationRunner, PaginationStats


class KeywordDiscoveryStrategy:
    """Strategy for discovering product targets across configurable search keywords."""

    def __init__(
        self,
        client: DarazDiscoveryClient,
        parser: DarazHTMLParser,
        queue: ProductTargetQueue,
        config: Optional[DarazDiscoveryConfig] = None,
    ):
        self.client = client
        self.parser = parser
        self.queue = queue
        self.config = config or default_discovery_config
        self.pagination_runner = PaginationRunner(
            client=self.client,
            parser=self.parser,
            queue=self.queue,
            config=self.config,
        )

    def build_search_url(self, keyword: str) -> str:
        """Construct the search catalog endpoint URL for a given keyword."""
        clean_kw = normalize_search_keyword(keyword)
        base = self.config.BASE_URL.rstrip("/")
        path = self.config.SEARCH_PATH.lstrip("/")
        query = urlencode({"q": clean_kw})
        return f"{base}/{path}?{query}"

    async def crawl_keyword(
        self,
        keyword: str,
        start_page: int = 1,
        max_pages: Optional[int] = None,
        crawl_id: Optional[str] = None,
    ) -> PaginationStats:
        """Execute paginated discovery for a single keyword query."""
        clean_kw = normalize_search_keyword(keyword)
        search_url = self.build_search_url(clean_kw)
        limit_pages = max_pages or self.config.MAX_PAGES_PER_SEARCH

        logger.info(
            f"Starting search discovery for keyword '{clean_kw}' on {search_url} (max {limit_pages} pages)",
            extra={"crawl_id": crawl_id, "keyword": clean_kw, "max_pages": limit_pages},
        )

        stats = await self.pagination_runner.paginate(
            start_url=search_url,
            start_page=start_page,
            max_pages=limit_pages,
            source_query=clean_kw,
            crawl_id=crawl_id,
        )

        logger.info(
            f"Keyword discovery for '{clean_kw}' finished: {stats.total_targets_found} targets found across {stats.pages_processed} pages ({stats.stopped_reason})",
            extra={
                "crawl_id": crawl_id,
                "keyword": clean_kw,
                "targets": stats.total_targets_found,
                "pages": stats.pages_processed,
                "reason": stats.stopped_reason,
            },
        )
        return stats

    async def crawl_keywords(
        self,
        keywords: Optional[List[str]] = None,
        max_pages_per_keyword: Optional[int] = None,
        crawl_id: Optional[str] = None,
    ) -> List[PaginationStats]:
        """Iteratively or concurrently discover products across a list of keywords."""
        terms = keywords or self.config.DEFAULT_KEYWORDS
        results: List[PaginationStats] = []

        for kw in terms:
            stats = await self.crawl_keyword(
                keyword=kw,
                max_pages=max_pages_per_keyword,
                crawl_id=crawl_id,
            )
            results.append(stats)
            if "challenge_detected" in stats.stopped_reason:
                logger.warning("Aborting remaining keywords due to anti-bot challenge.")
                break

        return results
