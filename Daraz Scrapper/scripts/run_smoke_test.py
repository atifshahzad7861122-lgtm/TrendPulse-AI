"""Controlled live smoke test script for Daraz Product Extraction Engine."""

import asyncio
from pathlib import Path
import sys

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.discovery.client import DarazDiscoveryClient
from app.discovery.models import ProductTarget
from app.extraction.engine import DarazProductExtractor
from app.storage.repository import InMemoryStorage


async def main():
    print("=================================================================")
    print("Starting Controlled Live Smoke Test (1-3 Products)...")
    print("=================================================================")

    storage = InMemoryStorage()
    discovery_client = DarazDiscoveryClient()
    extractor = DarazProductExtractor(storage=storage)

    # Step 1: Discover 1-3 live product targets via search query
    sample_query = "mouse"
    print(f"\n[Step 1] Discovering live sample targets for '{sample_query}' via Browser Client...")
    search_url = f"https://www.daraz.pk/catalog/?q={sample_query}"

    status_code, html, final_url, challenge = await discovery_client.fetch_page(search_url, use_browser=True)
    print(f"Discovery HTTP Status: {status_code} on {final_url}")

    from app.discovery.parser import daraz_parser
    discovered_targets = daraz_parser.parse_product_targets(html, source_query=sample_query)
    print(f"Discovered {len(discovered_targets)} raw targets from live page.")

    # Select up to 2 live product targets (controlled, no bulk crawl)
    sample_targets = discovered_targets[:2]
    if not sample_targets:
        # Fallback to known live product URL format if discovery returned 0 due to bot challenge
        sample_targets = [
            ProductTarget(
                product_id="40001",
                url="https://www.daraz.pk/products/wireless-optical-mouse-i40001.html",
                source_query=sample_query,
            )
        ]

    print(f"\n[Step 2] Executing extraction on {len(sample_targets)} sample target(s)...")

    for i, target in enumerate(sample_targets, 1):
        print(f"\n--- Testing Target {i}/{len(sample_targets)}: {target.url} ---")
        # Attempt extraction with browser rendering
        result = await extractor.extract_product(target, use_browser=True)

        print(f"Status / Success        : {result.success}")
        print(f"Source Engine           : {result.source_engine}")
        print(f"Extraction Duration     : {result.extraction_duration_ms:.2f} ms")
        print(f"Fields Extracted        : {result.fields_extracted}")
        print(f"Fields Missing          : {result.fields_missing}")
        print(f"Warnings                : {result.warnings}")
        print(f"Errors                  : {result.errors}")

        if result.product:
            p = result.product
            print(f"Product ID              : {p.product_id}")
            print(f"Title                   : {p.title}")
            print(f"Price                   : {p.price} {p.currency}")
            print(f"Original Price          : {p.original_price}")
            print(f"Discount                : {p.discount}")
            print(f"Rating / Review Count   : {p.rating} / {p.review_count}")
            print(f"Sales Signal (Sold)     : {p.sold_count}")
            print(f"Images Found            : {len(p.images)}")
            print(f"Brand                   : {p.brand}")
            print(f"Seller                  : {p.seller_name}")
            print(f"Category                : {p.category_name}")

    await discovery_client.close()
    await extractor.close()
    print("\n=================================================================")
    print("Controlled Live Smoke Test Completed.")
    print("=================================================================")


if __name__ == "__main__":
    asyncio.run(main())
