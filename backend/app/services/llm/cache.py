import hashlib
import json
import time
import threading
from typing import Dict, Any, Optional

class LLMResponseCache:
    """
    In-memory thread-safe cache for LLM analysis results.
    Prevents redundant LLM token expenditures on identical, unchanged product data.
    """

    def __init__(self, default_ttl_seconds: int = 86400):
        self._lock = threading.Lock()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds

    @staticmethod
    def generate_key(
        target_id: str,
        analysis_type: str,
        prompt_version: str,
        data_fingerprint: str,
        model: str
    ) -> str:
        """Computes a deterministic MD5 cache key."""
        raw = f"{target_id}::{analysis_type}::{prompt_version}::{data_fingerprint}::{model}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
            if time.time() > entry["expires_at"]:
                del self._cache[cache_key]
                return None
            return entry["data"]

    def set(self, cache_key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            ttl = ttl_seconds or self.default_ttl
            self._cache[cache_key] = {
                "data": data,
                "created_at": time.time(),
                "expires_at": time.time() + ttl
            }

    def invalidate(self, target_id: str) -> int:
        """Invalidates all cache entries for a given product or category ID."""
        with self._lock:
            keys_to_delete = [k for k, v in self._cache.items() if v.get("data", {}).get("unified_product_id") == target_id]
            for k in keys_to_delete:
                del self._cache[k]
            return len(keys_to_delete)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

llm_cache = LLMResponseCache()
