"""Controlled Live Smoke Test for Standalone Multi-Marketplace Scraper."""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure root workspace is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.logging import setup_logger
from app.crawling.models import MarketplaceType
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult
from app.intelligence.pipeline.engine import ProductIntelligenceEngine
from app.storage.export import DataExporter

logger = setup_logger("smoke_test_scraper")

# Controlled Real-World Test Targets (1-2 per marketplace)
TARGETS = [
    # 1. Daraz
    {
        "marketplace": MarketplaceType.DARAZ,
        "url": "https://www.daraz.pk/products/m10-tws-wireless-earbuds-bluetooth-51-earphones-stereo-sound-noise-cancelling-touch-control-waterproof-headsets-with-microphone-charging-case-i426980036-s2027209867.html",
    },
    # 2. Amazon
    {
        "marketplace": MarketplaceType.AMAZON,
        "url": "https://www.amazon.com/dp/B08N5WRWNW",
    },
    # 3. eBay
    {
        "marketplace": MarketplaceType.EBAY,
        "url": "https://www.ebay.com/itm/386123456789",
    },
    # 4. AliExpress
    {
        "marketplace": MarketplaceType.ALIEXPRESS,
        "url": "https://www.aliexpress.com/item/1005006123456789.html",
    },
    # 5. Shopify
    {
        "marketplace": MarketplaceType.SHOPIFY,
        "url": "https://kith.com/products/khm032338-101.json",
    },
]


async def run_controlled_test():
    print("\n" + "=" * 80)
    print("🧪 MODULE 5 HARDENING: CONTROLLED LIVE MARKETPLACE EXTRACTION TEST")
    print("=" * 80)
    print(f"Total Targets: {len(TARGETS)} (Daraz, Amazon, eBay, AliExpress, Shopify)")
    print("Rules        : No CAPTCHA bypass, no fake data, honest error classification")
    print("=" * 80 + "\n")

    engine = ProductIntelligenceEngine()
    test_results: List[Dict[str, Any]] = []

    for idx, target in enumerate(TARGETS, 1):
        m_name = target["marketplace"].value.upper()
        url = target["url"]
        print(f"\n[{idx}/{len(TARGETS)}] Testing {m_name} Target: {url[:70]}...")

        t_start = time.time()
        res: IntelligenceExtractionResult = await engine.extract_product(url, force_refresh=True)
        latency_ms = round((time.time() - t_start) * 1000, 1)

        # Status normalization
        raw_status = res.status
        is_challenge = raw_status == ExtractionStatus.CHALLENGE or (res.status_code in (403, 429))
        
        if is_challenge:
            status_label = "CHALLENGE"
        elif res.status_code == 0:
            status_label = "NETWORK_ERROR"
        elif raw_status == ExtractionStatus.NOT_FOUND:
            status_label = "TARGET_UNAVAILABLE"
        elif res.success and res.product:
            if res.overall_confidence >= 0.70 and res.product.price > 0:
                status_label = "SUCCESS"
            else:
                status_label = "PARTIAL"
        else:
            status_label = "EXTRACTION_FAILED"

        # Field extraction check
        p = res.product
        title = p.title if p else "N/A"
        price = p.price if p else 0.0
        currency = p.currency if p else "USD"
        rating = p.rating if p else None
        rev_count = p.review_count if p else 0
        sold_count = p.sold_count if p else None
        img_count = len(p.images) if p else 0
        confidence = res.overall_confidence
        missing = res.fields_missing

        print(f"   ► Status         : {status_label}")
        print(f"   ► HTTP Status    : {res.status_code}")
        print(f"   ► Challenge Wall : {'YES (Detected & Paused)' if is_challenge else 'NO'}")
        print(f"   ► Title          : {title[:50]}...")
        print(f"   ► Price          : {price} {currency}")
        print(f"   ► Rating         : {rating or 'N/A'} ({rev_count} reviews)")
        print(f"   ► Sold Count     : {sold_count or 'N/A'}")
        print(f"   ► Image Count    : {img_count}")
        print(f"   ► Confidence     : {confidence:.2f}")
        print(f"   ► Missing Fields : {missing or 'None'}")
        print(f"   ► Latency        : {latency_ms} ms")

        test_results.append({
            "marketplace": m_name,
            "url": url,
            "product_id": res.product_id,
            "status": status_label,
            "http_status": res.status_code,
            "challenge_detected": is_challenge,
            "title": title,
            "price": price,
            "currency": currency,
            "rating": rating,
            "review_count": rev_count,
            "sold_count": sold_count,
            "image_count": img_count,
            "confidence": confidence,
            "missing_fields": missing,
            "latency_ms": latency_ms,
            "errors": res.errors,
        })

    # Summary Table
    print("\n" + "=" * 80)
    print("📊 LIVE EXTRACTION HARDENING SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Marketplace':<14} | {'Status':<18} | {'HTTP':<5} | {'Price':<12} | {'Confidence':<10} | {'Latency':<8}")
    print("-" * 80)
    for r in test_results:
        price_str = f"{r['price']} {r['currency']}" if r['price'] > 0 else "N/A"
        print(f"{r['marketplace']:<14} | {r['status']:<18} | {r['http_status']:<5} | {price_str:<12} | {r['confidence']:<10.2f} | {r['latency_ms']:<6.0f}ms")
    print("=" * 80)

    # Save summary report
    DataExporter.export_json(test_results, "data/smoke_test_scraper_results.json")
    print(f"\nDetailed run metrics saved to data/smoke_test_scraper_results.json\n")


if __name__ == "__main__":
    asyncio.run(run_controlled_test())
