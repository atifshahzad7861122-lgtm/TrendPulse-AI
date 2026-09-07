"""Proxy configuration, health tracking, and rotation architecture."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.core.exceptions import ProxyError
from app.core.logging import logger


@dataclass
class ProxyConfig:
    """Configuration for an individual proxy endpoint."""
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    max_failures: int = 3
    cooldown_seconds: float = 60.0

    @property
    def formatted_url(self) -> str:
        """Return the fully authenticated proxy URL string."""
        if self.username and self.password:
            parsed = urlparse(self.url)
            scheme = parsed.scheme or "http"
            netloc = f"{self.username}:{self.password}@{parsed.hostname}:{parsed.port}"
            return f"{scheme}://{netloc}"
        return self.url


@dataclass
class ProxyHealth:
    """Dynamic health and metrics status for a proxy."""
    url: str
    is_healthy: bool = True
    consecutive_failures: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_used: Optional[float] = None
    last_failed: Optional[float] = None
    cooldown_until: float = 0.0


class ProxyProvider:
    """Manages a pool of proxies with health tracking, rotation, and failure cooldowns."""

    def __init__(
        self,
        proxies: Optional[List[ProxyConfig]] = None,
        enabled: bool = True,
    ):
        self.enabled = enabled
        self._proxies: List[ProxyConfig] = proxies or []
        self._health: Dict[str, ProxyHealth] = {
            p.url: ProxyHealth(url=p.url) for p in self._proxies
        }
        self._index: int = 0
        self._lock = asyncio.Lock()

    @property
    def has_proxies(self) -> bool:
        return self.enabled and len(self._proxies) > 0

    def add_proxy(self, proxy: ProxyConfig) -> None:
        """Add a new proxy configuration to the pool."""
        self._proxies.append(proxy)
        if proxy.url not in self._health:
            self._health[proxy.url] = ProxyHealth(url=proxy.url)

    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Retrieve the next available healthy proxy using round-robin rotation."""
        if not self.has_proxies:
            return None

        async with self._lock:
            now = time.monotonic()
            # Update cooldown states
            for p in self._proxies:
                health = self._health[p.url]
                if not health.is_healthy and now >= health.cooldown_until:
                    health.is_healthy = True
                    health.consecutive_failures = 0
                    logger.info(
                        f"Proxy '{p.url}' cooldown expired. Reinstating to pool.",
                        extra={"event": "proxy_reinstated", "proxy_url": p.url},
                    )

            # Search available healthy proxies
            healthy_proxies = [p for p in self._proxies if self._health[p.url].is_healthy]
            if not healthy_proxies:
                logger.warning("All proxies in pool are currently unhealthy/cooling down.", extra={"event": "all_proxies_down"})
                return None

            # Round robin selection
            self._index = self._index % len(healthy_proxies)
            chosen = healthy_proxies[self._index]
            self._index = (self._index + 1) % len(healthy_proxies)

            self._health[chosen.url].last_used = now
            return chosen

    async def record_success(self, proxy_url: str) -> None:
        """Record successful proxy operation."""
        async with self._lock:
            if proxy_url in self._health:
                health = self._health[proxy_url]
                health.total_successes += 1
                health.consecutive_failures = 0
                health.is_healthy = True

    async def record_failure(self, proxy_url: str, error: Optional[Exception] = None) -> None:
        """Record proxy failure and initiate cooldown if failure threshold exceeded."""
        async with self._lock:
            if proxy_url in self._health:
                health = self._health[proxy_url]
                health.total_failures += 1
                health.consecutive_failures += 1
                now = time.monotonic()
                health.last_failed = now

                proxy_cfg = next((p for p in self._proxies if p.url == proxy_url), None)
                max_f = proxy_cfg.max_failures if proxy_cfg else 3
                cooldown_sec = proxy_cfg.cooldown_seconds if proxy_cfg else 60.0

                if health.consecutive_failures >= max_f:
                    health.is_healthy = False
                    health.cooldown_until = now + cooldown_sec
                    logger.warning(
                        f"Proxy '{proxy_url}' exceeded {max_f} failures. Cooling down for {cooldown_sec}s. Error: {error}",
                        extra={
                            "event": "proxy_cooldown",
                            "proxy_url": proxy_url,
                            "cooldown_seconds": cooldown_sec,
                            "error": str(error),
                        },
                    )

    def get_httpx_proxy(self, proxy_config: Optional[ProxyConfig]) -> Optional[str]:
        """Convert ProxyConfig into HTTPX-compatible proxy string."""
        if not proxy_config or not self.enabled:
            return None
        return proxy_config.formatted_url

    def get_playwright_proxy(self, proxy_config: Optional[ProxyConfig]) -> Optional[Dict[str, str]]:
        """Convert ProxyConfig into Playwright-compatible proxy dict."""
        if not proxy_config or not self.enabled:
            return None
        parsed = urlparse(proxy_config.url)
        server = f"{parsed.scheme or 'http'}://{parsed.hostname}:{parsed.port}"
        result = {"server": server}
        if proxy_config.username:
            result["username"] = proxy_config.username
        if proxy_config.password:
            result["password"] = proxy_config.password
        return result
