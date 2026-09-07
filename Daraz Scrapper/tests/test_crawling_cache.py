"""Unit tests for UniversalCrawlCache behavior and modes."""

import time
import pytest
from app.crawling.cache import UniversalCrawlCache
from app.crawling.config import CrawlCacheMode
from app.crawling.models import CrawlResponse


def test_cache_set_and_get(tmp_path):
    cache = UniversalCrawlCache(cache_dir=tmp_path, default_ttl_seconds=3600)
    url = "https://www.ebay.com/itm/1234567890"
    resp = CrawlResponse(
        url=url,
        status_code=200,
        html="<html><body>Product Page</body></html>",
        source_engine="http",
    )

    # Initially missing
    assert cache.get(url) is None

    # Set and retrieve
    cache.set(url, resp)
    cached = cache.get(url)
    assert cached is not None
    assert cached.url == url
    assert cached.is_cached is True
    assert cached.source_engine == "cache"


def test_cache_force_refresh_bypasses_cache(tmp_path):
    cache = UniversalCrawlCache(cache_dir=tmp_path, default_ttl_seconds=3600)
    url = "https://www.aliexpress.com/item/1005001234.html"
    resp = CrawlResponse(
        url=url,
        status_code=200,
        html="<html><body>AliExpress Item</body></html>",
    )
    cache.set(url, resp)

    # force_refresh=True returns None
    assert cache.get(url, force_refresh=True) is None
    # standard get returns cached response
    assert cache.get(url, force_refresh=False) is not None


def test_cache_ttl_expiration(tmp_path):
    cache = UniversalCrawlCache(cache_dir=tmp_path, default_ttl_seconds=1)
    url = "https://www.amazon.com/dp/B00TEST123"
    resp = CrawlResponse(url=url, status_code=200, html="<html>Amazon</html>")
    
    cache.set(url, resp, ttl_seconds=1)
    assert cache.get(url) is not None

    time.sleep(1.1)
    assert cache.get(url) is None
