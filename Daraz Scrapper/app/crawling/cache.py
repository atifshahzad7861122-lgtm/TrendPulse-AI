"""Content-addressable caching system for universal crawling operations."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.crawling.config import CrawlCacheMode
from app.crawling.models import CrawlResponse
from app.core.logging import logger


class UniversalCrawlCache:
    """
    Content-addressable disk/memory cache for crawl responses.
    Supports TTL expiration, cache modes (ENABLED, BYPASS, READ_ONLY, WRITE_ONLY),
    and force_refresh flags.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        default_ttl_seconds: int = 86400,
        cache_mode: CrawlCacheMode = CrawlCacheMode.ENABLED,
    ):
        self.cache_dir = cache_dir or Path("data/crawl_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = default_ttl_seconds
        self.cache_mode = cache_mode
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    def compute_cache_key(self, url: str, headers: Optional[Dict[str, str]] = None, config_version: str = "v1") -> str:
        """Deterministic SHA256 key for a crawl request."""
        clean_url = url.strip().split("#")[0]
        raw_str = f"{clean_url}|{config_version}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def get(self, url: str, force_refresh: bool = False, cache_mode: Optional[CrawlCacheMode] = None) -> Optional[CrawlResponse]:
        """Retrieve unexpired cached response if mode allows."""
        mode = cache_mode or self.cache_mode
        if mode in (CrawlCacheMode.DISABLED, CrawlCacheMode.BYPASS, CrawlCacheMode.WRITE_ONLY) or force_refresh:
            return None

        key = self.compute_cache_key(url)

        # 1. Check memory cache
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not self._is_expired(entry):
                resp_data = entry["response"]
                resp_data["is_cached"] = True
                resp_data["source_engine"] = "cache"
                return CrawlResponse(**resp_data)

        # 2. Check disk cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                entry = json.loads(cache_file.read_text(encoding="utf-8"))
                if not self._is_expired(entry):
                    self._memory_cache[key] = entry
                    resp_data = entry["response"]
                    resp_data["is_cached"] = True
                    resp_data["source_engine"] = "cache"
                    return CrawlResponse(**resp_data)
                else:
                    cache_file.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Error reading cache for {url}: {e}")

        return None

    def set(
        self,
        url: str,
        response: CrawlResponse,
        ttl_seconds: Optional[int] = None,
        cache_mode: Optional[CrawlCacheMode] = None,
    ) -> None:
        """Store response in cache if mode allows and response is valid."""
        mode = cache_mode or self.cache_mode
        if mode in (CrawlCacheMode.DISABLED, CrawlCacheMode.BYPASS, CrawlCacheMode.READ_ONLY):
            return

        if response.status_code not in (200, 301, 302) or not response.html:
            return

        key = self.compute_cache_key(url)
        ttl = ttl_seconds or self.default_ttl_seconds
        expires_at = datetime.now(timezone.utc).timestamp() + ttl

        entry = {
            "key": key,
            "url": url,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "response": response.model_dump(exclude={"screenshot_bytes"}, mode="json"),
        }

        self._memory_cache[key] = entry
        try:
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to write cache for {url}: {e}")

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        expires_at = entry.get("expires_at", 0)
        return datetime.now(timezone.utc).timestamp() > expires_at
