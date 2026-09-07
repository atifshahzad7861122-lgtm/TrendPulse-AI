"""Controlled live smoke test for Historical Data Collection & Retention Engine.

Tests 1 target product per marketplace:
1. Daraz
2. Amazon
3. eBay
4. AliExpress
5. Shopify

Validates:
- HistoricalObservation creation with content/image hashes
- Previous observation retrieval & delta calculation
- Quality gate validation integration
- Safe anti-bot pause & checkpointing
- Disk persistence in data/history/observations/
"""

import asyncio
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.crawling.models import MarketplaceType
from app.history import (
    DiskJsonlHistoricalStore,
    HistoricalCollectionConfig,
    HistoricalCollectionEngine,
    HistoricalRetentionManager,
    TrendEngine,
)


async def run_history_smoke_test():
    print("=" * 80)
    print("HISTORICAL COLLECTION & RETENTION ENGINE: CONTROLLED LIVE SMOKE TEST")
    print("=" * 80)

    obs_dir = "data/history/observations"
    checkpoints_dir = "data/history/checkpoints"
    store = DiskJsonlHistoricalStore(base_dir=obs_dir)

    config = HistoricalCollectionConfig(
        max_concurrency=2,
        window_days=30,
        bucket_hours=1,
        enforce_quality_gate=True,
        checkpoints_dir=checkpoints_dir,
        observations_dir=obs_dir,
    )
    engine = HistoricalCollectionEngine(store=store, config=config)

    targets = [
        {
            "name": "Daraz (Live Search/Product Target)",
            "marketplace": MarketplaceType.DARAZ,
            "url": "https://www.daraz.pk/products/laptop-stand-i100200-s300400.html",
        },
        {
            "name": "Amazon (Live Product Target)",
            "marketplace": MarketplaceType.AMAZON,
            "url": "https://www.amazon.com/dp/B08N5WRWNW",
        },
        {
            "name": "eBay (Live Product Target)",
            "marketplace": MarketplaceType.EBAY,
            "url": "https://www.ebay.com/itm/123456789012",
        },
        {
            "name": "AliExpress (Live Product Target)",
            "marketplace": MarketplaceType.ALIEXPRESS,
            "url": "https://www.aliexpress.com/item/1005001234567890.html",
        },
        {
            "name": "Shopify (Live Product JSON Target)",
            "marketplace": MarketplaceType.SHOPIFY,
            "url": "https://shop.allbirds.com/products/mens-tree-runners.json",
        },
    ]

    results: List[Dict[str, Any]] = []

    for target in targets:
        print(f"\n---> Collecting Historical Observation for {target['name']}...")
        print(f"     URL: {target['url']}")

        t_start = time.monotonic()
        try:
            obs = await engine.collect_target(
                target=target["url"],
                marketplace=target["marketplace"],
                crawl_id="smoke_test_crawl_001",
            )
            elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)

            if obs is not None:
                print(f"     Status: SUCCESS (Obs ID: {obs.observation_id})")
                print(f"     Title: {obs.title[:50]}")
                print(f"     Price: {obs.price} {obs.currency} | Sold: {obs.sold_count} | Rating: {obs.rating}")
                print(f"     Content Hash: {obs.content_hash[:12]}... | Images Hash: {obs.images_hash[:12]}...")
                print(f"     Quality Status: {obs.quality_status}")
                print(f"     Deltas: {obs.deltas.model_dump() if obs.deltas else 'None (First Observation)'}")

                results.append({
                    "marketplace": target["marketplace"].value,
                    "name": target["name"],
                    "url": target["url"],
                    "status": "success",
                    "observation_id": obs.observation_id,
                    "title": obs.title[:50],
                    "price": obs.price,
                    "sold_count": obs.sold_count,
                    "rating": obs.rating,
                    "quality_status": obs.quality_status,
                    "has_content_hash": bool(obs.content_hash),
                    "has_images_hash": bool(obs.images_hash),
                    "duration_ms": elapsed_ms,
                })
            else:
                print(f"     Status: SKIPPED/PAUSED/FAILED (Elapsed: {elapsed_ms} ms)")
                results.append({
                    "marketplace": target["marketplace"].value,
                    "name": target["name"],
                    "url": target["url"],
                    "status": "failed_or_challenged",
                    "observation_id": None,
                    "title": "N/A",
                    "price": 0.0,
                    "sold_count": None,
                    "rating": None,
                    "quality_status": "none",
                    "has_content_hash": False,
                    "has_images_hash": False,
                    "duration_ms": elapsed_ms,
                })

        except Exception as exc:
            print(f"     ERROR: {exc}")
            results.append({
                "marketplace": target["marketplace"].value,
                "name": target["name"],
                "url": target["url"],
                "status": "error",
                "observation_id": None,
                "title": "Error",
                "price": 0.0,
                "sold_count": None,
                "rating": None,
                "quality_status": "error",
                "has_content_hash": False,
                "has_images_hash": False,
                "duration_ms": 0,
            })

    # Test Retention Dry Run
    print("\n---> Verifying 365-Day Rolling Retention Preview...")
    retention_mgr = HistoricalRetentionManager(store=store, default_retention_days=365)
    retention_preview = await retention_mgr.preview_expired()
    print(f"     Total Inspected: {retention_preview.total_inspected}")
    print(f"     Expired Records (> 365d): {retention_preview.expired_count}")
    print(f"     Preserved Active Records: {retention_preview.preserved_count}")

    print("\n" + "=" * 80)
    print("MODULE 5 SMOKE TEST SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Marketplace':<12} | {'Status':<20} | {'Price':<8} | {'Sold':<6} | {'Quality':<10} | {'Latency ms':<10}")
    print("-" * 80)
    for r in results:
        s_str = f"{r['sold_count']}" if r['sold_count'] is not None else "N/A"
        print(f"{r['marketplace']:<12} | {r['status']:<20} | {r['price']:<8.2f} | {s_str:<6} | {r['quality_status']:<10} | {r['duration_ms']:<10.1f}")
    print("=" * 80)

    # Save summary report JSON
    os.makedirs("data/smoke_test", exist_ok=True)
    out_path = "data/smoke_test/module5_smoke_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nModule 5 smoke test metrics persisted to: {out_path}\n")


if __name__ == "__main__":
    asyncio.run(run_history_smoke_test())
