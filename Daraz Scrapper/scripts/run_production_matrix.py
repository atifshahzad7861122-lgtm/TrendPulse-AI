"""Multi-tier production validation matrix script running Levels 1 to 5 (3, 10, 50, 100, 1000 items)."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.logging import setup_logger
from app.crawling.models import MarketplaceType
from app.discovery.engine import DarazDiscoveryEngine
from app.intelligence.pipeline.engine import ProductIntelligenceEngine
from app.intelligence.validation.completeness import CompletenessLevel, ProductCompletenessValidator
from app.orchestration.models import OrchestratorConfig
from app.orchestration.orchestrator import ProductionScrapingOrchestrator
from app.storage.export import DataExporter

logger = setup_logger("production_matrix")

LEVEL_TARGETS = {
    1: 3,
    2: 10,
    3: 50,
    4: 100,
    5: 1000,
}


async def run_matrix_level(
    level: int,
    marketplace: MarketplaceType,
    keyword: str,
    workers: int = 4,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """Execute a single matrix level test and return granular performance & completeness metrics."""
    target_count = LEVEL_TARGETS.get(level, 3)
    logger.info(f"\n==================================================")
    logger.info(f"🏁 STARTING MATRIX LEVEL {level} ({target_count} PRODUCTS) - {marketplace.value.upper()}")
    logger.info(f"==================================================")

    t0 = time.time()
    crawl_id = f"matrix_lvl{level}_{marketplace.value}_{int(time.time())}"

    # 1. Discover Target URLs
    logger.info(f"Discovering up to {target_count} products for keyword '{keyword}' on {marketplace.value.upper()}...")
    disc_engine = DarazDiscoveryEngine()
    max_pages = max(2, (target_count // 40) + 1)
    
    discovered_targets = await disc_engine.discover_keyword_products(keyword=keyword, max_pages=max_pages)
    unique_discovered = list({t.product_id: t for t in discovered_targets}.values())
    selected_targets = unique_discovered[:target_count]
    
    target_urls = [t.url for t in selected_targets]
    discovery_time = round(time.time() - t0, 2)
    logger.info(f"Discovered {len(unique_discovered)} unique targets in {discovery_time}s. Selected {len(target_urls)} for crawl.")

    # 2. Execute Orchestrated Crawl
    config = OrchestratorConfig(
        max_workers=workers,
        batch_size=batch_size,
        enable_browser=True,
    )
    orchestrator = ProductionScrapingOrchestrator(config=config)
    out_csv = f"data/matrix_level_{level}_{marketplace.value}.csv"

    t_crawl_start = time.time()
    summary = await orchestrator.execute_crawl(
        crawl_id=crawl_id,
        marketplace=marketplace,
        urls=target_urls,
        max_products=len(target_urls),
        output_file=out_csv,
        export_format="csv",
    )
    crawl_duration = round(time.time() - t_crawl_start, 2)

    # 3. Evaluate Completeness of Output Products
    complete_count = 0
    partial_count = 0
    invalid_count = 0

    for p in orchestrator._extracted_products:
        report = ProductCompletenessValidator.evaluate(p)
        if report.level == CompletenessLevel.COMPLETE:
            complete_count += 1
        elif report.level == CompletenessLevel.PARTIAL:
            partial_count += 1
        else:
            invalid_count += 1

    total_duration = round(time.time() - t0, 2)
    ppm = round((summary.completed_count / crawl_duration) * 60, 1) if crawl_duration > 0 else 0.0

    metrics = {
        "level": level,
        "target_count": target_count,
        "marketplace": marketplace.value,
        "keyword": keyword,
        "products_discovered": len(unique_discovered),
        "products_selected": len(target_urls),
        "products_completed": summary.completed_count,
        "products_failed": summary.failed_count,
        "products_challenged": summary.challenged_count,
        "completeness_complete": complete_count,
        "completeness_partial": partial_count,
        "completeness_invalid": invalid_count,
        "duration_seconds": total_duration,
        "crawl_duration_seconds": crawl_duration,
        "products_per_minute": ppm,
        "avg_latency_ms": summary.average_latency_ms,
        "output_file": out_csv,
        "status": summary.status,
    }

    logger.info(f"\n--- LEVEL {level} METRICS SUMMARY ---")
    logger.info(f"Completed    : {metrics['products_completed']}/{metrics['products_selected']}")
    logger.info(f"Completeness : Complete={complete_count}, Partial={partial_count}, Invalid={invalid_count}")
    logger.info(f"Challenged   : {metrics['products_challenged']}")
    logger.info(f"Failed       : {metrics['products_failed']}")
    logger.info(f"Throughput   : {ppm} products/min")
    logger.info(f"Total Time   : {total_duration}s")
    logger.info(f"Output CSV   : {out_csv}\n")

    return metrics


async def main():
    parser = argparse.ArgumentParser(description="Multi-tier Production Validation Matrix Runner")
    parser.add_argument("--marketplace", type=str, default="daraz", choices=["daraz", "amazon", "ebay", "aliexpress", "shopify"])
    parser.add_argument("--keyword", type=str, default="wireless mouse", help="Search keyword")
    parser.add_argument("--levels", type=str, default="1,2", help="Comma-separated matrix levels to execute (e.g. 1,2,3)")
    parser.add_argument("--workers", type=int, default=3, help="Max workers")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch persistence size")
    parser.add_argument("--output-json", type=str, default="data/matrix_validation_summary.json")

    args = parser.parse_args()
    mkt = MarketplaceType(args.marketplace.lower())
    levels_to_run = [int(l.strip()) for l in args.levels.split(",") if l.strip()]

    all_metrics: List[Dict[str, Any]] = []

    print("\n" + "=" * 80)
    print("🏭 PRODUCTION VALIDATION MATRIX RUNNER")
    print("=" * 80)
    print(f"Marketplace : {mkt.value.upper()}")
    print(f"Keyword     : {args.keyword}")
    print(f"Levels      : {levels_to_run}")
    print(f"Workers     : {args.workers}")
    print("=" * 80 + "\n")

    for lvl in levels_to_run:
        metric = await run_matrix_level(
            level=lvl,
            marketplace=mkt,
            keyword=args.keyword,
            workers=args.workers,
            batch_size=args.batch_size,
        )
        all_metrics.append(metric)

        # Halt escalation if challenge or heavy failure observed
        if metric["products_challenged"] > 0 or (metric["products_completed"] == 0 and metric["products_selected"] > 0):
            print(f"🛑 Halting further matrix levels due to challenge wall or 0% completion at Level {lvl}.")
            break

    # Save summary JSON
    out_p = Path(args.output_json)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(all_metrics, indent=2), encoding="utf-8")
    print(f"✅ Matrix Summary written to {out_p}")


if __name__ == "__main__":
    asyncio.run(main())
