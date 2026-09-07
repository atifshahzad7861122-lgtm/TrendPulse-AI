"""Async HTTP fetcher for fast, lightweight marketplace crawling without browser overhead."""

from datetime import datetime, timezone
import time
from typing import Dict, Optional, Tuple
import httpx

from app.crawling.config import UniversalCrawlerConfig
from app.crawling.models import CrawlRequest, CrawlResponse
from app.core.logging import logger


class AsyncHttpClient:
    """
    High-throughput non-browser HTTP fetcher with connection pooling,
    automatic redirects, and custom header injection.
    """

    def __init__(self, config: Optional[UniversalCrawlerConfig] = None):
        self.config = config or UniversalCrawlerConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
                keepalive_expiry=30.0,
            )
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.http_timeout_seconds),
                limits=limits,
                follow_redirects=True,
                headers={"User-Agent": self.config.default_user_agent},
            )
        return self._client

    async def fetch(self, request: CrawlRequest) -> CrawlResponse:
        """Execute async HTTP GET request."""
        client = await self._get_client()
        headers = dict(request.custom_headers)
        if "User-Agent" not in headers:
            headers["User-Agent"] = self.config.default_user_agent

        start_time = time.perf_counter()
        try:
            resp = await client.get(request.url, headers=headers, cookies=request.custom_cookies)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return CrawlResponse(
                url=str(resp.url),
                status_code=resp.status_code,
                html=resp.text,
                headers=dict(resp.headers),
                source_engine="http",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(f"HTTP fetch failed for {request.url}: {e}")
            return CrawlResponse(
                url=request.url,
                status_code=0,
                html="",
                headers={},
                source_engine="http",
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )

    async def close(self) -> None:
        """Close httpx client connection pool."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
