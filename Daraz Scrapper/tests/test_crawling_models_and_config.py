"""Unit tests for universal crawl models and configuration."""

import pytest
from app.crawling.config import CrawlCacheMode, UniversalCrawlerConfig
from app.crawling.models import (
    CrawlContentType,
    CrawlRequest,
    CrawlResponse,
    CrawlStatus,
    MarketplaceType,
    UniversalCrawlResult,
)


def test_crawl_request_default_and_custom():
    req = CrawlRequest(url="https://www.amazon.com/dp/B08N5WRWNW")
    assert req.url == "https://www.amazon.com/dp/B08N5WRWNW"
    assert req.content_type == CrawlContentType.GENERIC
    assert req.force_refresh is False
    assert req.use_browser is False


def test_crawl_response_model():
    resp = CrawlResponse(
        url="https://www.daraz.pk/products/mouse-i123.html",
        status_code=200,
        html="<html><body><h1>Test</h1></body></html>",
        source_engine="http",
        duration_ms=120.5,
    )
    assert resp.status_code == 200
    assert resp.is_cached is False
    assert "Test" in resp.html


def test_universal_crawler_config():
    config = UniversalCrawlerConfig(
        max_concurrent_requests=10,
        requests_per_second=5.0,
        cache_mode=CrawlCacheMode.BYPASS,
    )
    assert config.max_concurrent_requests == 10
    assert config.requests_per_second == 5.0
    assert config.cache_mode == CrawlCacheMode.BYPASS
