"""Production-grade reusable async HTTP client with session management, circuit breaker, rate limiting, and challenge detection."""

import asyncio
from typing import Any, Dict, Optional
import httpx

from app.core.challenge_detector import ChallengeDetector
from app.core.circuit_breaker import CircuitBreaker
from app.core.config import Settings, get_settings
from app.core.constants import DEFAULT_HEADERS
from app.core.exceptions import (
    ChallengeDetectedError,
    CircuitBreakerOpenError,
    NetworkError,
    RateLimitError,
)
from app.core.logging import logger
from app.core.proxy import ProxyConfig, ProxyProvider
from app.core.rate_limiter import AsyncRateLimiter
from app.core.retry import with_retry
from app.core.runtime import RequestMetrics, get_current_crawl_id, runtime_metrics


class AsyncHttpClient:
    """Production-grade asynchronous HTTP client wrapper around httpx.AsyncClient."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        proxy_provider: Optional[ProxyProvider] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ):
        self.settings = settings or get_settings()
        self.rate_limiter = rate_limiter or AsyncRateLimiter(settings=self.settings)
        self.circuit_breaker = circuit_breaker or CircuitBreaker(name="http_client", failure_threshold=5, recovery_timeout=20.0)
        self.proxy_provider = proxy_provider or ProxyProvider(enabled=self.settings.PROXY_ENABLED)

        headers = DEFAULT_HEADERS.copy()
        headers["User-Agent"] = self.settings.SCRAPER_USER_AGENT
        if custom_headers:
            headers.update(custom_headers)

        self._client = httpx.AsyncClient(
            headers=headers,
            cookies=cookies,
            timeout=httpx.Timeout(self.settings.HTTP_TIMEOUT),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=self.settings.MAX_CONCURRENCY * 2,
                max_keepalive_connections=self.settings.MAX_CONCURRENCY,
            ),
        )
        self._is_closed = False

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send an async GET request with rate limiting, circuit breaker, and retry handling."""
        return await self.request("GET", url, params=params, headers=headers, **kwargs)

    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send an async POST request with rate limiting, circuit breaker, and retry handling."""
        return await self.request("POST", url, data=data, json=json, headers=headers, **kwargs)

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        inspect_challenges: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute HTTP request governed by circuit breaker, retry policy, rate limiting, and metrics."""
        if self._is_closed:
            raise NetworkError("HTTP client is already closed", url=url)

        @with_retry(
            max_retries=self.settings.MAX_RETRIES,
            settings=self.settings,
        )
        async def _execute() -> httpx.Response:
            metrics = RequestMetrics(url=url, method=method)
            crawl_id = get_current_crawl_id()

            # Pacing via Rate Limiter
            await self.rate_limiter.acquire(url=url)

            async def _do_request() -> httpx.Response:
                try:
                    response = await self._client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs,
                    )
                    metrics.finish(status_code=response.status_code)
                    await runtime_metrics.record_request(
                        status_code=response.status_code,
                        duration_ms=metrics.duration_ms,
                        is_error=response.is_error,
                    )

                    logger.debug(
                        f"HTTP {method} {url} -> {response.status_code} ({metrics.duration_ms:.1f}ms)",
                        extra={
                            "crawl_id": crawl_id,
                            "request_id": metrics.request_id,
                            "url": url,
                            "status": response.status_code,
                            "duration_ms": metrics.duration_ms,
                            "event": "http_request_success",
                        },
                    )

                    # Classify HTTP 429 Rate Limit responses first
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 5.0))
                        raise RateLimitError(
                            f"Remote rate limit exceeded (HTTP 429) for {url}",
                            retry_after=retry_after,
                        )

                    # Challenge Detection & Anti-bot inspection for security barriers
                    if inspect_challenges:
                        challenge_res = ChallengeDetector.inspect_response(
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            body=response.text,
                            url=str(response.url),
                        )
                        if challenge_res.is_challenge and challenge_res.challenge_type != "RATE_LIMITED":
                            await runtime_metrics.record_challenge(challenge_res.challenge_type or "unknown")
                            raise ChallengeDetectedError(
                                message=f"Anti-bot challenge: {challenge_res.reason}",
                                url=url,
                                challenge_type=challenge_res.challenge_type,
                                status_code=response.status_code,
                            )

                    if response.is_error:
                        raise NetworkError(
                            f"HTTP Error {response.status_code} requesting {url}",
                            status_code=response.status_code,
                            url=url,
                        )

                    return response

                except (httpx.TimeoutException, httpx.RequestError) as exc:
                    metrics.finish(error=str(exc))
                    await runtime_metrics.record_request(
                        status_code=None,
                        duration_ms=metrics.duration_ms,
                        is_error=True,
                    )
                    logger.warning(
                        f"HTTP Network Error on {url}: {exc}",
                        extra={
                            "crawl_id": crawl_id,
                            "request_id": metrics.request_id,
                            "url": url,
                            "event": "http_connection_error",
                            "error": str(exc),
                        },
                    )
                    raise NetworkError(f"HTTP connection failed: {exc}", url=url) from exc

            return await self.circuit_breaker.execute(_do_request)

        return await _execute()

    async def aclose(self):
        """Cleanly close underlying HTTP transport sessions."""
        if not self._is_closed:
            await self._client.aclose()
            self._is_closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
