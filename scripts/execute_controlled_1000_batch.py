import sys
import os
import json
import time
from datetime import datetime, timezone

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.app.api.deps import (
    get_marketplace_product_repository,
    get_data_quality_repository,
    get_daraz_service
)
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.daraz.ingestion_engine import (
    DarazIngestionEngine, DarazIngestionConfig
)


def main():
    print("================================================================================")
    print(" TRENDPULSE AI: CONTROLLED 1,000-PRODUCT PRODUCTION INGESTION BATCH")
    print("================================================================================")
    
    repo = get_marketplace_product_repository()
    dq_repo = get_data_quality_repository()
    daraz_service = get_daraz_service(marketplace_repo=repo)

    # Use Official Daraz Open Platform provider with active repository
    official_prov = DarazOfficialProvider(marketplace_repo=repo)

    active_token, auth_err = official_prov.get_active_token()
    print(f"[1/4] Checking Official Provider Connection:")
    print(f"      - App Key: {official_prov.app_key[:6]}***")
    print(f"      - Active Token Resolved: {bool(active_token)}")
    print(f"      - Configured: {official_prov.is_configured()}")

    # Check pre-run quota
    quota_before = repo.get_or_create_daily_quota()
    print(f"[2/4] Daily Quota Status Before Batch:")
    print(f"      - Date: {quota_before.date}")
    print(f"      - Requests Used: {quota_before.requests_used}")
    print(f"      - Daily Limit: {quota_before.daily_limit}")
    print(f"      - Remaining: {quota_before.remaining}")

    # Count DB before
    products_before = repo.count_products(platform="daraz")
    training_before = len(repo.list_training_dataset())
    print(f"      - Existing Daraz Products in DB: {products_before}")
    print(f"      - Existing Training Items in DB: {training_before}")

    # Configure Ingestion Engine for 1,000 products
    config = DarazIngestionConfig(
        target_count=1000,
        batch_size=50,
        delay_between_requests=0.15,
        safety_quota_margin=10000,
        search_filter="all"
    )

    engine = DarazIngestionEngine(
        provider=official_prov,
        repository=repo,
        dq_repository=dq_repo,
        config=config
    )

    print(f"\n[3/4] Executing Controlled 1,000-Product Batch Ingestion...")
    start_time = time.time()
    progress = engine.execute_batch_ingestion(target_count=1000)
    elapsed = time.time() - start_time

    print(f"\n[4/4] Ingestion Execution Finished in {elapsed:.2f}s:")
    print(f"      - Run ID: {progress.run_id}")
    print(f"      - Status: {progress.status}")
    print(f"      - Target Count: {progress.target_count}")
    print(f"      - Products Fetched: {progress.products_fetched}")
    print(f"      - Products Inserted: {progress.products_inserted}")
    print(f"      - Products Updated: {progress.products_updated}")
    print(f"      - Duplicates Prevented: {progress.duplicates_prevented}")
    print(f"      - Historical Snapshots Created: {progress.snapshots_created}")
    print(f"      - Agent 1 Valid: {progress.agent1_valid}")
    print(f"      - Agent 1 Warnings: {progress.agent1_warning}")
    print(f"      - Agent 1 Needs Review: {progress.agent1_needs_review}")
    print(f"      - Agent 1 Rejected: {progress.agent1_rejected}")
    print(f"      - Training Dataset Eligible: {progress.training_eligible}")
    print(f"      - API Requests Consumed: {progress.api_requests_consumed}")
    print(f"      - Daily Quota Remaining: {progress.daily_quota_remaining}")
    print(f"      - Products Per Second: {progress.products_per_second}")
    print(f"      - Error (if any): {progress.error_message}")

    # Post-run DB verification
    products_after = repo.count_products(platform="daraz")
    training_after = len(repo.list_training_dataset())
    quota_after = repo.get_or_create_daily_quota()

    print(f"\n================ DIRECT DATABASE VERIFICATION ================")
    print(f" - daraz_products total: {products_after} (+{products_after - products_before})")
    print(f" - daraz_training_dataset total: {training_after} (+{training_after - training_before})")
    print(f" - daraz_daily_quota requests used: {quota_after.requests_used}")
    print(f" - daraz_daily_quota remaining: {quota_after.remaining}")
    print(f" - daraz_ingestion_runs status: {progress.status}")

    # Output JSON summary for automated reporting
    summary = {
        "run_id": progress.run_id,
        "status": progress.status,
        "products_fetched": progress.products_fetched,
        "products_inserted": progress.products_inserted,
        "products_updated": progress.products_updated,
        "duplicates_prevented": progress.duplicates_prevented,
        "snapshots_created": progress.snapshots_created,
        "agent1_valid": progress.agent1_valid,
        "agent1_warning": progress.agent1_warning,
        "agent1_needs_review": progress.agent1_needs_review,
        "agent1_rejected": progress.agent1_rejected,
        "training_eligible": progress.training_eligible,
        "api_requests_consumed": progress.api_requests_consumed,
        "daily_quota_remaining": quota_after.remaining,
        "products_per_second": progress.products_per_second,
        "products_in_db": products_after,
        "training_in_db": training_after
    }
    with open("daraz_1000_batch_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("\nSummary saved to daraz_1000_batch_summary.json")


if __name__ == "__main__":
    main()
