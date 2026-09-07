"""Controlled live smoke test for Module 3 Daraz Product Extraction Engine."""

import asyncio
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.discovery.models import ProductTarget
from app.extraction.config import DarazExtractionConfig
from app.extraction.engine import DarazProductExtractionEngine
from app.storage.repository import InMemoryStorage


async def run_live_product_extraction_smoke_test():
    print("=======================================================")
    print("      DARAZ PRODUCT EXTRACTION ENGINE SMOKE TEST       ")
    print("=======================================================")

    storage = InMemoryStorage()
    config = DarazExtractionConfig(
        max_concurrency=1,
        enable_http_first=True,
        auto_browser_fallback=True,
        prefer_high_res_images=True,
    )
    engine = DarazProductExtractionEngine(config=config, storage=storage)

    # Use live discovered target from Module 2 smoke test
    sample_target = ProductTarget(
        product_id="1965496866",
        url="https://www.daraz.pk/products/stn-28-i1965496866.html",
    )

    print(f"[*] Target Product: {sample_target.url}")
    print(f"[*] Product ID:     {sample_target.product_id}")
    print(f"[*] Engine Mode:    HTTP-first with automatic Browser fallback")
    print("\n[1] Executing live product extraction...")

    try:
        result = await engine.extract_product(sample_target)

        print("\n[2] Extraction Results Breakdown:")
        print(f"    - Extraction Success:    {result.success}")
        print(f"    - Validation Status:     {result.validation_status.value}")
        print(f"    - Overall Confidence:    {result.overall_confidence:.2f}")
        print(f"    - Source Engine Used:    {result.source_engine}")
        print(f"    - Duration:              {result.extraction_duration_ms:.1f} ms")

        if result.product:
            p = result.product
            print("\n[3] Extracted Product Payload:")
            print(f"    - Product ID:       {p.product_id}")
            print(f"    - Title:            {p.title}")
            print(f"    - Price:            {p.currency} {p.price:,.2f}")
            if p.original_price:
                print(f"    - Original Price:   {p.currency} {p.original_price:,.2f}")
            if p.discount:
                print(f"    - Discount:         {p.discount}%")
            print(f"    - In Stock:         {p.availability}")
            print(f"    - Rating:           {p.rating if p.rating is not None else 'N/A'}")
            print(f"    - Review Count:     {p.review_count}")
            print(f"    - Sold Count:       {p.sold_count if p.sold_count is not None else 'N/A'}")
            print(f"    - Brand:            {p.brand or 'N/A'}")
            print(f"    - Seller Name:      {p.seller_name or 'N/A'} (ID: {p.seller_id or 'N/A'})")
            print(f"    - Category:         {p.category_name or 'N/A'}")
            print(f"    - Images Extracted: {len(p.images)}")
            if p.images:
                print(f"      * Primary Image:  {p.images[0].url}")
            if p.specifications:
                print(f"    - Specifications:   {len(p.specifications)} keys found")

        print("\n[4] Field Confidence Breakdown:")
        for field, score in result.field_confidence.items():
            print(f"    - {field:15s}: {score.confidence:.2f} (Source: {score.source.value})")

        if result.validation_report:
            print("\n[5] Quality Validation Report:")
            print(f"    - Passed Checks:    {len(result.validation_report.passed_checks)}")
            print(f"    - Warnings:         {result.validation_report.warnings}")
            print(f"    - Errors:           {result.validation_report.errors}")

        print("\n=======================================================")
        print("      MODULE 3 LIVE SMOKE TEST COMPLETED               ")
        print("=======================================================")

    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(run_live_product_extraction_smoke_test())
