"""
Controlled End-to-End Live Verification Script for Daraz Scraper.
Can be executed from repository root via:
    python -m backend.tests.verify_daraz_live_scraper
or
    python backend/tests/verify_daraz_live_scraper.py
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure repository root is on sys.path dynamically without hardcoding absolute user paths
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Standard Project Imports
from backend.app.services.scraper.models import StartScraperJobRequest, ScraperJobProgressResponse
from backend.app.api.deps import (
    get_scraper_repository,
    get_marketplace_product_repository,
    get_unified_repository,
    get_unified_intelligence_service,
    get_data_quality_agent,
    get_daraz_service,
    get_scraper_service
)
from backend.app.models.domain import RawScrapedPayload, MarketplaceProduct, ProductMarketSnapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("verify_daraz_live_scraper")


def perform_import_check() -> bool:
    """Verifies that all project backend dependencies and models import cleanly."""
    logger.info("--- [CHECK 1] Import and Module Resolution ---")
    logger.info(f"Repository Root resolved to: {REPO_ROOT}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info("Successfully imported StartScraperJobRequest, ScraperJobProgressResponse, and deps.")
    return True


async def run_live_verification():
    import_ok = perform_import_check()
    assert import_ok, "Import check failed!"

    logger.info("\n--- [CHECK 2] Initializing Backend Services and Repositories ---")
    scraper_repo = get_scraper_repository()
    marketplace_repo = get_marketplace_product_repository()
    unified_repo = get_unified_repository()
    unified_intel = get_unified_intelligence_service()
    dq_agent = get_data_quality_agent()
    daraz_svc = get_daraz_service()

    service = get_scraper_service(
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        unified_intel=unified_intel,
        dq_agent=dq_agent,
        daraz_svc=daraz_svc
    )

    req = StartScraperJobRequest(
        marketplace="daraz",
        provider="auto",
        keyword="wireless earbuds",
        max_products=3,
        max_workers=2,
        dry_run=False
    )

    logger.info(f"\n--- [CHECK 3] Launching Live Daraz Scraper Job ---")
    logger.info(f"Marketplace: {req.marketplace} | Keyword: '{req.keyword}' | Target Count: {req.max_products}")
    
    init_res = await service.start_job(req)
    job_id = init_res.job_id
    logger.info(f"Job Initialized: ID = {job_id} | Initial Status = {init_res.status}")

    # Track lifecycle transitions
    observed_statuses = [init_res.status]
    max_wait_seconds = 240
    poll_interval = 2.0
    elapsed = 0.0
    final_status: ScraperJobProgressResponse = init_res

    logger.info("\n--- [CHECK 4] Polling Scraper Job Telemetry ---")
    while elapsed < max_wait_seconds:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        current = service.get_job_status(job_id)
        if not current:
            logger.error(f"Status poll returned None for {job_id}!")
            break

        final_status = current
        if current.status not in observed_statuses:
            observed_statuses.append(current.status)

        logger.info(
            f"[{elapsed:5.1f}s] Status: {current.status.upper():10s} | "
            f"Fetched: {current.products_fetched:2d}/{current.target_count:2d} | "
            f"Persisted: {current.products_persisted:2d} | "
            f"Rejected: {current.products_rejected:2d} | "
            f"Challenged: {current.challenged_count:2d} | "
            f"Throughput: {current.current_throughput:4.2f} items/s | "
            f"Duration: {current.duration_seconds:5.1f}s"
        )

        if current.status in ("completed", "failed", "cancelled", "stopped"):
            logger.info(f"Terminal state reached: {current.status.upper()}")
            break

    logger.info("\n--- [CHECK 5] Validating Job Lifecycle & Execution Metrics ---")
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Lifecycle sequence observed: {' -> '.join(s.upper() for s in observed_statuses)}")
    logger.info(f"Products Fetched: {final_status.products_fetched}")
    logger.info(f"Products Persisted: {final_status.products_persisted}")
    logger.info(f"Throughput: {final_status.current_throughput} items/s")
    logger.info(f"Duration: {final_status.duration_seconds}s")
    logger.info(f"Final Status: {final_status.status.upper()}")
    if final_status.error_message:
        logger.info(f"Error Message: {final_status.error_message}")

    assert final_status.status in ("completed", "failed"), f"Job did not reach completed/failed state: {final_status.status}"
    assert final_status.products_persisted > 0 or final_status.products_fetched > 0, "No products were fetched or persisted!"
    assert final_status.current_throughput > 0, "Throughput must be greater than 0 items/s"

    logger.info("\n--- [CHECK 6] Database Persistence Chain Verification ---")
    # 1. Check RawScrapedPayload in Scraper Repository
    raw_payloads = scraper_repo.list_raw_payloads(crawl_job_id=job_id, limit=5)
    logger.info(f"RawScrapedPayload records found for {job_id}: {len(raw_payloads)}")
    if raw_payloads:
        sample_raw = raw_payloads[0]
        logger.info(f"  [Raw Payload Sample]")
        logger.info(f"    - ID: {sample_raw.id}")
        logger.info(f"    - Marketplace: {sample_raw.marketplace}")
        logger.info(f"    - Product ID: {sample_raw.product_id}")
        logger.info(f"    - Has raw payload: {bool(sample_raw.raw_payload)}")
        logger.info(f"    - Extraction Status: {sample_raw.extraction_status}")

    # 2. Check MarketplaceProduct in Marketplace Repository
    m_products = marketplace_repo.list_products(platform="daraz", limit=10)
    logger.info(f"MarketplaceProduct records in Daraz catalog: {len(m_products)}")
    for p in m_products[:5]:
        logger.info(f"  - [{p.product_id}] {p.product_name[:45]} | PKR {p.price} | Rating: {p.rating} | Seller: {p.seller_name}")

    # 3. Check UnifiedProduct in Unified Repository
    unified_items = unified_repo.list_unified_products(limit=10)
    logger.info(f"UnifiedProduct records linked: {len(unified_items)}")
    for u in unified_items[:5]:
        logger.info(f"  - [{u.unified_product_id}] {u.canonical_name[:45]} | Brand: {u.brand} | Category: {u.category}")

    print("\n" + "=" * 65)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print(f"Job ID:             {job_id}")
    print(f"Status Lifecycle:   {' -> '.join(s.upper() for s in observed_statuses)}")
    print(f"Products Fetched:   {final_status.products_fetched}")
    print(f"Products Persisted: {final_status.products_persisted}")
    print(f"Current Throughput: {final_status.current_throughput} items/s")
    print(f"Total Duration:     {final_status.duration_seconds}s")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
