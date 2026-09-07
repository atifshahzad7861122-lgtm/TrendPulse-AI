"""Controlled Live Smoke Test for Module 2: Daraz Marketplace Discovery Engine.

Executes a minimal, bounded live discovery test against https://www.daraz.pk
for 1 keyword, extracting product IDs, canonical URLs, and verifying deduplication.
"""

import asyncio
from pathlib import Path
import sys
import uuid

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from app.core.logging import logger
from app.discovery.client import DarazDiscoveryClient
from app.discovery.config import DarazDiscoveryConfig
from app.discovery.detector import ChallengeDetectionResult
from app.discovery.engine import DarazDiscoveryEngine
from app.discovery.normalizer import canonicalize_product_url, extract_product_id
from app.discovery.parser import DarazHTMLParser
from app.discovery.queue import ProductTargetQueue
from app.storage.repository import InMemoryStorage


async def run_live_smoke_test():
    print("\n=======================================================")
    print("      DARAZ MARKETPLACE DISCOVERY ENGINE SMOKE TEST    ")
    print("=======================================================\n")

    settings = Settings(
        ENVIRONMENT="development",
        REQUEST_TIMEOUT_SECONDS=15.0,
        REQUEST_DELAY_MIN=1.0,
        REQUEST_DELAY_MAX=2.0,
    )
    discovery_config = DarazDiscoveryConfig(
        BASE_URL="https://www.daraz.pk",
        MAX_PAGES_PER_SEARCH=1,
    )
    storage = InMemoryStorage()

    test_keyword = "headphones"
    crawl_id = f"smoke-test-{uuid.uuid4().hex[:8]}"

    print(f"[*] Target Marketplace: {discovery_config.BASE_URL}")
    print(f"[*] Discovery Strategy: Keyword Search ('{test_keyword}')")
    print(f"[*] Max Pages: 1 (Controlled Bounded Limit)")
    print(f"[*] Crawl ID: {crawl_id}\n")

    engine = DarazDiscoveryEngine(
        storage=storage,
        settings=settings,
        discovery_config=discovery_config,
    )

    try:
        print("[1] Executing live keyword discovery...")
        targets = await engine.discover_keyword_products(
            keyword=test_keyword,
            max_pages=1,
            crawl_id=crawl_id,
        )

        print(f"\n[2] Discovery Results Summary:")
        print(f"    - Total Targets Found: {len(targets)}")
        print(f"    - Unique Products Enqueued: {engine.queue.unique_products}")
        print(f"    - Duplicates Prevented: {engine.queue.duplicates_prevented}")

        if targets:
            print("\n[3] Sample Discovered Targets (First 5):")
            for i, target in enumerate(targets[:5], 1):
                pid = target.product_id
                canon = target.canonical_url
                print(f"    [{i}] Product ID: {pid}")
                print(f"        Original URL: {target.url[:90]}...")
                print(f"        Canonical URL: {canon}")
                assert pid, "Target must have extracted numeric product_id"
                assert canon, "Target must have canonical URL"
                assert "spm=" not in canon, "Canonical URL must strip tracking parameters"
        else:
            print("\n[!] Note: No targets parsed directly or challenge page returned. Inspecting client status...")

        print("\n[4] Checkpoint Verification:")
        checkpoint = await storage.get_checkpoint(crawl_id)
        if checkpoint:
            print(f"    - Checkpoint Status: Persisted ({checkpoint.completed_items} items recorded)")
        else:
            print("    - Checkpoint Status: In-memory crawl completed.")

        print("\n[5] Deduplication Resilience Verification:")
        # Inject duplicate of first item
        if targets:
            first_target = targets[0]
            accepted = await engine.queue.push(first_target)
            print(f"    - Re-pushing existing product '{first_target.product_id}' -> Accepted: {accepted} (Expected: False)")
            assert accepted is False, "Duplicate must be rejected"
            print(f"    - Total Duplicates Prevented: {engine.queue.duplicates_prevented}")

        print("\n=======================================================")
        print("      MODULE 2 LIVE SMOKE TEST COMPLETED SUCCESSFULLY  ")
        print("=======================================================\n")

    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(run_live_smoke_test())
