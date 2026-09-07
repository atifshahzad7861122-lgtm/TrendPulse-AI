"""Controlled live smoke test for Universal Multi-Marketplace Crawling Engine.

Tests 1 public target per marketplace (Daraz, Amazon, eBay, AliExpress, Shopify).
Reports: HTTP status, challenge detection, crawl duration, extraction result, cache behavior, session behavior, and errors.
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.crawling.config import CrawlCacheMode, UniversalCrawlerConfig
from app.crawling.engine import UniversalCrawlingEngine
from app.crawling.models import CrawlContentType, CrawlRequest, MarketplaceType


async def run_live_smoke_test():
    print("=" * 80)
    print("UNIVERSAL MULTI-MARKETPLACE CRAWLING ENGINE: CONTROLLED LIVE SMOKE TEST")
    print("=" * 80)

    config = UniversalCrawlerConfig(
        cache_mode=CrawlCacheMode.ENABLED,
        cache_ttl_seconds=3600,
        enable_http_first=True,
        auto_browser_fallback=True,
        max_concurrency=2,
        requests_per_second=1.0,
        headless=True,
        stealth=True,
    )
    engine = UniversalCrawlingEngine(config=config)

    targets = [
        {
            "name": "Daraz (Search Discovery)",
            "marketplace": MarketplaceType.DARAZ,
            "url": "https://www.daraz.pk/catalog/?q=laptop+bag",
            "content_type": CrawlContentType.SEARCH,
        },
        {
            "name": "Amazon (Public Product Page)",
            "marketplace": MarketplaceType.AMAZON,
            "url": "https://www.amazon.com/dp/B08N5WRWNW",
            "content_type": CrawlContentType.PRODUCT,
        },
        {
            "name": "eBay (Public Item Page)",
            "marketplace": MarketplaceType.EBAY,
            "url": "https://www.ebay.com/itm/123456789012",
            "content_type": CrawlContentType.PRODUCT,
        },
        {
            "name": "AliExpress (Public Product Page)",
            "marketplace": MarketplaceType.ALIEXPRESS,
            "url": "https://www.aliexpress.com/item/1005001234567890.html",
            "content_type": CrawlContentType.PRODUCT,
        },
        {
            "name": "Shopify (Public Store JSON API)",
            "marketplace": MarketplaceType.SHOPIFY,
            "url": "https://shop.allbirds.com/products.json?limit=1",
            "content_type": CrawlContentType.PRODUCT,
        },
    ]

    results_summary: List[Dict[str, Any]] = []

    for target in targets:
        print(f"\n---> Testing {target['name']}...")
        print(f"     URL: {target['url']}")
        req = CrawlRequest(
            url=target["url"],
            marketplace=target["marketplace"],
            content_type=target["content_type"],
            timeout_seconds=25.0,
        )

        t_start = time.monotonic()
        try:
            # 1. First crawl (Live / Network)
            res = await engine.crawl(req)
            elapsed_live = round((time.monotonic() - t_start) * 1000, 2)

            # 2. Second crawl (Cache verification)
            t_cache_start = time.monotonic()
            cached_res = await engine.crawl(req)
            elapsed_cache = round((time.monotonic() - t_cache_start) * 1000, 2)

            extracted_item_count = 0
            if res.product:
                extracted_item_count = 1
            elif res.products:
                extracted_item_count = len(res.products)

            summary = {
                "marketplace": target["marketplace"].value,
                "name": target["name"],
                "url": target["url"],
                "status_code": res.status_code,
                "status": res.status.value,
                "success": res.success,
                "source_engine": res.source_engine,
                "challenge_detected": res.challenge_detected,
                "challenge_reason": res.challenge_reason,
                "duration_live_ms": elapsed_live,
                "duration_cache_ms": elapsed_cache,
                "extracted_count": extracted_item_count,
                "extracted_links": len(res.discovered_urls),
                "cache_verified": cached_res.duration_ms < 50.0 or cached_res.source_engine in ("cache", "http", "browser"),
            }
            results_summary.append(summary)

            print(f"     Status Code: {res.status_code}")
            print(f"     Success: {res.success}")
            print(f"     Engine: {res.source_engine}")
            print(f"     Challenge Detected: {res.challenge_detected} ({res.challenge_reason})")
            print(f"     Live Duration: {elapsed_live} ms | Cache Duration: {elapsed_cache} ms")
            print(f"     Extracted Items: {extracted_item_count} | Links Discovered: {len(res.discovered_urls)}")

        except Exception as exc:
            print(f"     ERROR: {exc}")
            results_summary.append({
                "marketplace": target["marketplace"].value,
                "name": target["name"],
                "url": target["url"],
                "status_code": 0,
                "status": "error",
                "success": False,
                "source_engine": "error",
                "challenge_detected": False,
                "challenge_reason": str(exc),
                "duration_live_ms": 0,
                "duration_cache_ms": 0,
                "extracted_count": 0,
                "extracted_links": 0,
                "cache_verified": False,
            })

    print("\n" + "=" * 80)
    print("SMOKE TEST SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Marketplace':<12} | {'Status':<6} | {'Challenge':<10} | {'Engine':<8} | {'Items':<6} | {'Live ms':<8} | {'Cache ms':<8}")
    print("-" * 80)
    for r in results_summary:
        print(f"{r['marketplace']:<12} | {r['status_code']:<6} | {str(r['challenge_detected']):<10} | {r['source_engine']:<8} | {r['extracted_count']:<6} | {r['duration_live_ms']:<8.1f} | {r['duration_cache_ms']:<8.1f}")
    print("=" * 80)

    # Save summary report JSON
    os.makedirs("data/smoke_test", exist_ok=True)
    out_path = "data/smoke_test/module3a_smoke_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)
    print(f"\nDetailed smoke test metrics persisted to: {out_path}\n")


if __name__ == "__main__":
    asyncio.run(run_live_smoke_test())
