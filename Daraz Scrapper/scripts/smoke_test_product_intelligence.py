"""Controlled live smoke test for Universal Product Intelligence Extraction Engine.

Tests 1 target product per marketplace:
1. Daraz
2. Amazon
3. eBay
4. AliExpress
5. Shopify

Validates:
- Full intelligence extraction
- Review extraction & sentiments
- Sales volume normalization
- Quality gate validation & confidence scoring
- Historical point-in-time snapshot persistence
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.crawling.models import MarketplaceType
from app.intelligence import IntelligencePipelineConfig, ProductIntelligenceEngine


async def run_intelligence_smoke_test():
    print("=" * 80)
    print("UNIVERSAL PRODUCT INTELLIGENCE EXTRACTION ENGINE: CONTROLLED LIVE SMOKE TEST")
    print("=" * 80)

    config = IntelligencePipelineConfig(
        max_concurrency=2,
        preserve_raw_payloads=True,
        record_historical_snapshots=True,
        enforce_quality_gate=True,
        snapshots_dir="data/intelligence/snapshots",
    )
    engine = ProductIntelligenceEngine(config=config)

    targets = [
        {
            "name": "Daraz (Live Search/Product Target)",
            "marketplace": MarketplaceType.DARAZ,
            "url": "https://www.daraz.pk/products/laptop-stand-i100200-s300400.html",
        },
        {
            "name": "Amazon (Live Product)",
            "marketplace": MarketplaceType.AMAZON,
            "url": "https://www.amazon.com/dp/B08N5WRWNW",
        },
        {
            "name": "eBay (Live Product)",
            "marketplace": MarketplaceType.EBAY,
            "url": "https://www.ebay.com/itm/123456789012",
        },
        {
            "name": "AliExpress (Live Product)",
            "marketplace": MarketplaceType.ALIEXPRESS,
            "url": "https://www.aliexpress.com/item/1005001234567890.html",
        },
        {
            "name": "Shopify (Live Product JSON)",
            "marketplace": MarketplaceType.SHOPIFY,
            "url": "https://shop.allbirds.com/products/mens-tree-runners.json",
        },
    ]

    results_summary: List[Dict[str, Any]] = []

    for target in targets:
        print(f"\n---> Testing Intelligence Extraction on {target['name']}...")
        print(f"     URL: {target['url']}")

        t_start = time.monotonic()
        try:
            res = await engine.extract_product(target["url"], marketplace=target["marketplace"])
            elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)

            item_title = res.product.title if res.product else "N/A"
            item_price = res.product.price if res.product else 0.0
            item_rating = res.product.rating if res.product else None
            item_reviews = len(res.reviews) if res.reviews else (res.product.review_count if res.product else 0)
            item_sold = res.product.sold_count if res.product else None
            img_count = len(res.product.images) if res.product else 0
            var_count = len(res.product.variants) if res.product else 0
            conf_score = res.overall_confidence if res.product else 0.0

            summary = {
                "marketplace": target["marketplace"].value,
                "name": target["name"],
                "url": target["url"],
                "status": res.status.value,
                "success": res.success,
                "status_code": res.status_code,
                "title": item_title[:50],
                "price": item_price,
                "rating": item_rating,
                "review_count": item_reviews,
                "sold_count": item_sold,
                "image_count": img_count,
                "variant_count": var_count,
                "confidence": conf_score,
                "duration_ms": elapsed_ms,
                "snapshot_recorded": res.snapshot is not None,
                "warnings": res.warnings,
                "errors": res.errors,
            }
            results_summary.append(summary)

            print(f"     Status: {res.status.value} (HTTP {res.status_code})")
            print(f"     Success: {res.success}")
            print(f"     Title: {item_title[:60]}")
            print(f"     Price: {item_price} | Rating: {item_rating} | Sold: {item_sold}")
            print(f"     Images: {img_count} | Variants: {var_count} | Confidence: {conf_score}")
            print(f"     Snapshot Created: {res.snapshot is not None} | Duration: {elapsed_ms} ms")

        except Exception as exc:
            print(f"     ERROR: {exc}")
            results_summary.append({
                "marketplace": target["marketplace"].value,
                "name": target["name"],
                "url": target["url"],
                "status": "error",
                "success": False,
                "status_code": 0,
                "title": "Error",
                "price": 0.0,
                "rating": None,
                "review_count": 0,
                "sold_count": None,
                "image_count": 0,
                "variant_count": 0,
                "confidence": 0.0,
                "duration_ms": 0,
                "snapshot_recorded": False,
                "warnings": [],
                "errors": [str(exc)],
            })

    print("\n" + "=" * 80)
    print("MODULE 4 SMOKE TEST SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Marketplace':<12} | {'Status':<15} | {'Price':<8} | {'Rating':<6} | {'Sold':<6} | {'Imgs':<4} | {'Conf':<4} | {'Latency ms':<10}")
    print("-" * 80)
    for r in results_summary:
        r_str = f"{r['rating']}" if r['rating'] is not None else "N/A"
        s_str = f"{r['sold_count']}" if r['sold_count'] is not None else "N/A"
        print(f"{r['marketplace']:<12} | {r['status']:<15} | {r['price']:<8.2f} | {r_str:<6} | {s_str:<6} | {r['image_count']:<4} | {r['confidence']:<4.2f} | {r['duration_ms']:<10.1f}")
    print("=" * 80)

    # Save summary report JSON
    os.makedirs("data/smoke_test", exist_ok=True)
    out_path = "data/smoke_test/module4_smoke_test_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)
    print(f"\nModule 4 smoke test metrics persisted to: {out_path}\n")


if __name__ == "__main__":
    asyncio.run(run_intelligence_smoke_test())
