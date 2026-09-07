import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.app.api.deps import (
    get_marketplace_product_repository,
    get_data_quality_repository
)
from backend.app.services.daraz.parse_scraper_provider import DarazParseScraperProvider
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.models.domain import (
    MarketplaceProduct, ProductMarketSnapshot, DarazSeller,
    DarazIngestionRun, DarazApiTelemetry, DarazTrainingDataset
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("controlled_100_parse_batch")


def execute_controlled_100_test():
    print("=" * 70)
    print("TRENDPULSE AI: PARSE DARAZ API CONTROLLED 100-PRODUCT MARKETPLACE TEST")
    print("=" * 70)

    repo = get_marketplace_product_repository()
    dq_repo = get_data_quality_repository()
    dq_agent = DataQualityAgent(repository=dq_repo)
    provider = DarazParseScraperProvider()

    if not provider.is_configured():
        print("[ERROR] Parse API Key is not configured.")
        return

    products_before = repo.count_products(platform="daraz")
    print(f"Existing Daraz products in database before test: {products_before}")

    run_id = f"daraz_parse_100_{int(time.time())}"
    start_time = time.time()
    now = datetime.now(timezone.utc)

    ingestion_run = DarazIngestionRun(
        id=run_id,
        provider_name="parse_daraz_api",
        status="running",
        trigger_type="manual",
        search_query="marketplace_wide_controlled_100",
        products_fetched=0,
        products_inserted=0,
        products_updated=0,
        snapshots_created=0,
        metadata_json={
            "target_count": 100,
            "provider": "parse_daraz_api",
            "batch_type": "controlled_100"
        },
        started_at=now,
        created_at=now
    )
    repo.create_ingestion_run(ingestion_run)

    # Multi-query distribution to reach exactly 100 products with maximum category diversity
    # 40 from 'laptop', 40 from 'mobile', 20 from 'headphones'
    query_plan = [
        {"query": "laptop", "page": 1, "take": 40},
        {"query": "mobile", "page": 1, "take": 40},
        {"query": "headphones", "page": 1, "take": 20}
    ]

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    duplicates_prevented = 0
    snapshots_created = 0
    training_created = 0
    api_requests_count = 0
    api_latencies = []

    agent1_valid = 0
    agent1_warning = 0
    agent1_needs_review = 0
    agent1_rejected = 0

    t0_all = time.time()
    total_agent1_time = 0.0
    total_db_time = 0.0

    for plan in query_plan:
        if total_fetched >= 100:
            break

        q = plan["query"]
        take = plan["take"]
        req_start = time.time()
        print(f"\n[API Request {api_requests_count + 1}] Fetching '{q}' from Parse Daraz API...")
        res = provider.search_products(query=q, page=1)
        req_latency = round((time.time() - req_start) * 1000, 2)
        api_latencies.append(req_latency)
        api_requests_count += 1

        # Record API Telemetry
        repo.record_api_telemetry(DarazApiTelemetry(
            id=str(uuid.uuid4()),
            endpoint="search_products",
            method="POST",
            provider_name="parse_daraz_api",
            status_code=200 if res.success else (res.error_code or 500),
            latency_ms=req_latency,
            success=res.success,
            error_message=res.error_message,
            request_params={"query": q, "page": 1},
            response_size_bytes=len(str(res.data)) if res.data else 0
        ))

        if not res.success or not res.data or not res.data.products:
            print(f"  [WARN] Request for '{q}' returned 0 products or failed: {res.error_message}")
            continue

        products_chunk = res.data.products[:take]
        print(f"  Received {len(res.data.products)} items, taking {len(products_chunk)} for quota limit (Latency: {req_latency}ms)")

        for item in products_chunk:
            if total_fetched >= 100:
                break

            total_fetched += 1
            p_id = str(item.product_id)

            # Check existing
            t_db_start = time.time()
            existing = repo.get_product(platform="daraz", product_id=p_id)
            total_db_time += (time.time() - t_db_start)

            # Agent 1 Validation
            t_dq_start = time.time()
            payload = {
                "product_id": p_id,
                "title": item.name,
                "name": item.name,
                "price": item.price,
                "original_price": item.original_price,
                "currency": "PKR",
                "rating": item.rating,
                "review_count": item.review_count,
                "seller_name": item.seller_name,
                "seller_id": item.seller_id,
                "brand": item.brand,
                "category": item.category or q,
                "image_url": item.image_url,
                "product_url": item.product_url,
                "platform": "daraz",
                "source_provider": "parse_daraz_api"
            }

            dq_result = dq_agent.validate_product(
                payload=payload,
                platform="daraz",
                source_provider="parse_daraz_api",
                allow_llm=False
            )
            total_agent1_time += (time.time() - t_dq_start)

            cls_name = dq_result.classification
            if cls_name == "valid":
                agent1_valid += 1
            elif cls_name in ("valid_with_warnings", "warning"):
                agent1_warning += 1
            elif cls_name == "needs_review":
                agent1_needs_review += 1
            else:
                agent1_rejected += 1

            if cls_name == "rejected":
                continue

            # Persist Product
            t_db_start = time.time()
            m_prod = MarketplaceProduct(
                id=existing.id if existing else f"daraz_{p_id}",
                platform="daraz",
                product_id=p_id,
                product_name=item.name,
                price=item.price,
                original_price=item.original_price,
                discount_percentage=item.discount,
                discount_label=item.discount_label,
                currency="PKR",
                rating=item.rating,
                review_count=item.review_count,
                seller_name=item.seller_name,
                seller_id=item.seller_id,
                brand=item.brand,
                category=item.category or q,
                image_url=item.image_url,
                product_url=item.product_url,
                sku=item.sku,
                in_stock=item.in_stock,
                source="parse_daraz_api",
                last_synced_at=datetime.now(timezone.utc),
                raw_data=item.raw_data or {}
            )
            repo.upsert_product(m_prod)

            if existing:
                total_updated += 1
                duplicates_prevented += 1
            else:
                total_inserted += 1

            # Market Snapshot
            snap = ProductMarketSnapshot(
                id=str(uuid.uuid4()),
                product_id=p_id,
                platform="daraz",
                price=item.price,
                original_price=item.original_price,
                discount=item.discount,
                rating=item.rating,
                review_count=item.review_count,
                stock_status="in_stock" if item.in_stock else "out_of_stock",
                observed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            repo.create_snapshot(snap)
            snapshots_created += 1

            # Seller Persistence
            if item.seller_id or item.seller_name:
                s_id = str(item.seller_id or f"s_{hash(item.seller_name) % 1000000}")
                repo.upsert_seller(DarazSeller(
                    id=f"seller_{s_id}",
                    seller_id=s_id,
                    seller_name=item.seller_name or f"Daraz Seller {s_id}",
                    shop_url=f"https://www.daraz.pk/shop/{s_id}",
                    rating=item.rating if item.rating > 0 else 4.5,
                    positive_ratings_percentage=95.0,
                    location="pk",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                ))

            # Training Dataset Item (if high quality)
            if dq_result.quality_score >= 0.70:
                repo.add_training_dataset_item(DarazTrainingDataset(
                    id=f"train_{p_id}",
                    product_id=p_id,
                    title=item.name,
                    category=item.category or q,
                    brand=item.brand,
                    price=item.price,
                    rating=item.rating,
                    review_count=item.review_count,
                    features={
                        "discount": item.discount,
                        "seller": item.seller_name,
                        "source": "parse_daraz_api"
                    },
                    quality_score=dq_result.quality_score,
                    agent_label="daraz_marketplace_product",
                    is_validated=(cls_name in ("valid", "valid_with_warnings", "warning")),
                    created_at=datetime.now(timezone.utc)
                ))
                training_created += 1

            total_db_time += (time.time() - t_db_start)

    total_elapsed = time.time() - start_time
    products_after = repo.count_products(platform="daraz")

    # Update Ingestion Run Status
    ingestion_run.status = "completed"
    ingestion_run.products_fetched = total_fetched
    ingestion_run.products_inserted = total_inserted
    ingestion_run.products_updated = total_updated
    ingestion_run.snapshots_created = snapshots_created
    ingestion_run.completed_at = datetime.now(timezone.utc)
    ingestion_run.metadata_json = {
        "target_count": 100,
        "products_fetched": total_fetched,
        "products_inserted": total_inserted,
        "products_updated": total_updated,
        "duplicates_prevented": duplicates_prevented,
        "snapshots_created": snapshots_created,
        "training_eligible": training_created,
        "agent1_valid": agent1_valid,
        "agent1_warning": agent1_warning,
        "agent1_needs_review": agent1_needs_review,
        "agent1_rejected": agent1_rejected,
        "api_requests_consumed": api_requests_count,
        "elapsed_seconds": round(total_elapsed, 2),
        "products_per_second": round(total_fetched / max(0.01, total_elapsed), 2),
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    repo.update_ingestion_run(ingestion_run)

    avg_api_latency = round(sum(api_latencies) / len(api_latencies), 2) if api_latencies else 0.0
    avg_proc_time_ms = round((total_elapsed / max(1, total_fetched)) * 1000, 2)
    ppm = round((total_fetched / max(0.01, total_elapsed)) * 60, 1)

    print("\n" + "=" * 70)
    print("CONTROLLED 100-PRODUCT TEST RESULTS")
    print("=" * 70)
    print(f"Products requested: 100")
    print(f"Real products fetched: {total_fetched}")
    print(f"Products inserted (new): {total_inserted}")
    print(f"Products updated (existing): {total_updated}")
    print(f"Duplicates prevented: {duplicates_prevented}")
    print(f"Snapshots created: {snapshots_created}")
    print(f"Training dataset records: {training_created}")
    print(f"\nAgent 1 Data Quality:")
    print(f" - Valid: {agent1_valid}")
    print(f" - Warning: {agent1_warning}")
    print(f" - Needs Review: {agent1_needs_review}")
    print(f" - Rejected: {agent1_rejected}")
    print(f" - Training Eligible: {training_created}")
    print(f"\nPerformance:")
    print(f" - Total elapsed time: {total_elapsed:.2f}s")
    print(f" - Average API latency: {avg_api_latency}ms")
    print(f" - Agent 1 validation time: {total_agent1_time:.2f}s")
    print(f" - Database persistence time: {total_db_time:.2f}s")
    print(f" - Average processing time per product: {avg_proc_time_ms}ms")
    print(f" - Ingestion throughput: {ppm} products/minute")
    print(f"\nCatalog Totals:")
    print(f" - Products before: {products_before}")
    print(f" - Products after: {products_after}")
    print(f" - Net increase: {products_after - products_before}")
    print("=" * 70)


if __name__ == "__main__":
    execute_controlled_100_test()
