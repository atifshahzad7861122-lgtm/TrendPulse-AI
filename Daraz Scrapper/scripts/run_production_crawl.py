"""Production Scraping Orchestrator CLI."""

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import List

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure root workspace is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.logging import setup_logger
from app.crawling.models import MarketplaceType
from app.history.retention import HistoricalRetentionManager
from app.history.store import DiskJsonlHistoricalStore
from app.orchestration.health import MarketplaceHealthTracker
from app.orchestration.models import OrchestratorConfig
from app.orchestration.orchestrator import ProductionScrapingOrchestrator

logger = setup_logger("production_crawl_cli")


def load_urls(input_arg: str) -> List[str]:
    """Parse comma-separated URLs or load from file (TXT, JSON, JSONL)."""
    p = Path(input_arg)
    if p.exists() and p.is_file():
        text = p.read_text(encoding="utf-8").strip()
        if p.suffix == ".json":
            data = json.loads(text)
            if isinstance(data, list):
                urls = []
                for item in data:
                    if isinstance(item, str):
                        urls.append(item)
                    elif isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
                return urls
        elif p.suffix == ".jsonl":
            urls = []
            for line in text.splitlines():
                if line.strip():
                    item = json.loads(line)
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
                    elif isinstance(item, str):
                        urls.append(item)
            return urls
        else:
            return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    else:
        return [u.strip() for u in input_arg.split(",") if u.strip()]


async def main():
    parser = argparse.ArgumentParser(description="Production Scraping Orchestrator")
    parser.add_argument("--marketplace", type=str, default=None, choices=["daraz", "amazon", "ebay", "aliexpress", "shopify"], help="Target marketplace")
    parser.add_argument("--keyword", type=str, default=None, help="Search keyword for discovery")
    parser.add_argument("--category", type=str, default=None, help="Category path for discovery")
    parser.add_argument("--urls", type=str, default=None, help="Direct URLs (comma-separated or file path)")
    parser.add_argument("--max-products", type=int, default=10, help="Maximum products to process")
    parser.add_argument("--workers", type=int, default=4, help="Max concurrent worker coroutines")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch persistence size")
    parser.add_argument("--crawl-id", type=str, default=None, help="Explicit crawl session ID")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted crawl from checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Plan crawl tasks without executing requests")
    parser.add_argument("--output", type=str, default="data/production_output.json", help="Output file path")
    parser.add_argument("--format", type=str, default="json", choices=["json", "jsonl", "csv"], help="Export format")
    parser.add_argument("--no-browser", action="store_true", help="Disable dynamic browser rendering fallback")
    parser.add_argument("--health", action="store_true", help="Inspect and display marketplace health metrics")
    parser.add_argument("--retention-preview", action="store_true", help="Preview 365-day historical retention cleanup")
    parser.add_argument("--retention-execute", action="store_true", help="Execute 365-day historical retention cleanup")

    args = parser.parse_args()

    # 1. Health Inspection Command
    if args.health:
        tracker = MarketplaceHealthTracker()
        print("\n" + "=" * 80)
        print("🏥 MARKETPLACE HEALTH AUDIT MONITOR")
        print("=" * 80)
        print(f"{'Marketplace':<14} | {'Status':<18} | {'Success Rate':<14} | {'Avg Latency':<12}")
        print("-" * 80)
        for m, rep in tracker.get_all_health().items():
            print(f"{m.value.upper():<14} | {rep.status.value.upper():<18} | {rep.success_rate * 100:>10.1f}% | {rep.average_latency_ms:>8.1f}ms")
        print("=" * 80 + "\n")
        return

    # 2. Retention Preview / Execute Command
    if args.retention_preview or args.retention_execute:
        store = DiskJsonlHistoricalStore(base_dir="data/production/history")
        mgr = HistoricalRetentionManager(store=store, default_retention_days=365)
        print("\n" + "=" * 70)
        print("🗄️ 365-DAY HISTORICAL RETENTION MANAGEMENT")
        print("=" * 70)
        
        preview = await mgr.preview_expired()
        print(f"Total Inspected    : {preview.total_inspected}")
        print(f"Active Preserved   : {preview.preserved_count}")
        print(f"Expired (>365d)    : {preview.expired_count}")

        if args.retention_execute:
            print("\nExecuting retention purge...")
            res = await mgr.delete_expired()
            print(f"✅ Retention Completed. Removed {res.deleted_count} expired records.")
        print("=" * 70 + "\n")
        return

    # 3. Production Crawl Execution
    parsed_urls = load_urls(args.urls) if args.urls else None
    m_enum = MarketplaceType(args.marketplace.lower()) if args.marketplace else None

    print("\n" + "=" * 75)
    print("🚀 PRODUCTION SCRAPING ORCHESTRATOR")
    print("=" * 75)
    print(f"Marketplace : {args.marketplace.upper() if args.marketplace else 'AUTO / MULTI'}")
    print(f"Keyword     : {args.keyword or 'N/A'}")
    print(f"Category    : {args.category or 'N/A'}")
    print(f"Target URLs : {len(parsed_urls) if parsed_urls else 'Discovery Queue'}")
    print(f"Workers     : {args.workers}")
    print(f"Batch Size  : {args.batch_size}")
    print(f"Browser Mode: {not args.no_browser}")
    print(f"Resume Mode : {args.resume}")
    print(f"Dry Run     : {args.dry_run}")
    print(f"Output File : {args.output} ({args.format.upper()})")
    print("=" * 75 + "\n")

    config = OrchestratorConfig(
        max_workers=args.workers,
        batch_size=args.batch_size,
        enable_browser=not args.no_browser,
    )
    orchestrator = ProductionScrapingOrchestrator(config=config)

    summary = await orchestrator.execute_crawl(
        crawl_id=args.crawl_id,
        marketplace=m_enum,
        keyword=args.keyword,
        category=args.category,
        urls=parsed_urls,
        max_products=args.max_products,
        resume=args.resume,
        dry_run=args.dry_run,
        output_file=args.output,
        export_format=args.format,
    )

    print("\n" + "=" * 75)
    print("📊 CRAWL JOB SUMMARY REPORT")
    print("=" * 75)
    print(f"Crawl Session ID  : {summary.crawl_id}")
    print(f"Execution Status  : {summary.status.upper()}")
    print(f"Duration          : {summary.duration_seconds}s")
    print(f"Total Tasks       : {summary.total_tasks}")
    print(f"Completed         : {summary.completed_count}")
    print(f"Challenged        : {summary.challenged_count}")
    print(f"Failed            : {summary.failed_count}")
    print(f"Retried Tasks     : {summary.retried_count}")
    print(f"Products Saved    : {summary.products_persisted}")
    print(f"History Recorded  : {summary.observations_recorded}")
    print(f"Avg Latency       : {summary.average_latency_ms:.1f}ms")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
