"""Crawl4AI Adapter integrating Crawl4AI AsyncWebCrawler into the UniversalCrawlerInterface."""

import asyncio
from typing import Any, Dict, List, Optional
import httpx

from app.crawling.browser import BrowserLifecycleManager
from app.crawling.cache import UniversalCrawlCache
from app.crawling.config import UniversalCrawlerConfig
from app.crawling.dispatcher import ConcurrencyDispatcher
from app.crawling.http import AsyncHttpClient
from app.crawling.interfaces import UniversalCrawlerInterface
from app.crawling.models import CrawlRequest, CrawlResponse
from app.core.logging import logger


class Crawl4AIAdapter(UniversalCrawlerInterface):
    """
    Adapter encapsulating Crawl4AI / Playwright browser and HTTP automation
    behind the marketplace-neutral UniversalCrawlerInterface.
    """

    def __init__(
        self,
        config: Optional[UniversalCrawlerConfig] = None,
        cache: Optional[UniversalCrawlCache] = None,
        dispatcher: Optional[ConcurrencyDispatcher] = None,
    ):
        self.config = config or UniversalCrawlerConfig()
        self.cache = cache or UniversalCrawlCache(cache_mode=self.config.cache_mode)
        self.dispatcher = dispatcher or ConcurrencyDispatcher(max_concurrency=self.config.max_concurrent_requests)
        self.http_client = AsyncHttpClient(config=self.config)
        self.browser_manager = BrowserLifecycleManager(config=self.config)
        self._crawl4ai_crawler = None

    async def crawl(self, request: CrawlRequest) -> CrawlResponse:
        """
        Execute single page crawl with caching, HTTP-first optimization,
        and browser fallback.
        """
        # 1. Check Cache
        if not request.force_refresh:
            cached_resp = self.cache.get(request.url, force_refresh=request.force_refresh)
            if cached_resp:
                return cached_resp

        # 2. HTTP-First Execution
        if self.config.enable_http_first and not request.use_browser:
            http_resp = await self.dispatcher.dispatch(self.http_client.fetch, request)
            
            is_csr_stub = (
                '"renderMode":"CSR"' in http_resp.html
                or "lzd-pdp-desktop-node" in http_resp.html
                or "lzd-search-desktop-node" in http_resp.html
                or ("window.g_config" in http_resp.html and "window.pageData" not in http_resp.html and "pdp-mod-product-badge-title" not in http_resp.html)
                or ('id="app"' in http_resp.html and len(http_resp.html) < 2500)
                or ('id="root"' in http_resp.html and len(http_resp.html) < 2500)
            )
            needs_browser = (
                self.config.auto_browser_fallback
                and (
                    http_resp.status_code not in (200, 301, 302, 404)
                    or is_csr_stub
                )
            )

            if not needs_browser and http_resp.status_code == 200 and http_resp.html:
                self.cache.set(request.url, http_resp)
                return http_resp

        # 3. Browser Rendering Fallback
        browser_resp = await self.dispatcher.dispatch(self.browser_manager.fetch, request)
        if browser_resp.status_code == 200 and browser_resp.html:
            self.cache.set(request.url, browser_resp)
        return browser_resp

    async def crawl_many(self, requests: List[CrawlRequest]) -> List[CrawlResponse]:
        """Fetch a batch of URLs with bounded concurrency."""
        tasks = [lambda r=req: self.crawl(r) for req in requests]
        results = await self.dispatcher.dispatch_all(tasks)
        return [r for r in results if isinstance(r, CrawlResponse)]

    async def close(self) -> None:
        """Release underlying HTTP and browser resources."""
        await self.http_client.close()
        await self.browser_manager.close()
