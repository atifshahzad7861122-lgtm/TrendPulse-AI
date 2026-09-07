"""Command-line script for executing 365-day rolling retention pruning."""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.history import DiskJsonlHistoricalStore, HistoricalRetentionManager


async def main():
    parser = argparse.ArgumentParser(description="TrendPulse 365-Day Rolling Retention CLI")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=365,
        help="Maximum age of historical observations in days (default: 365)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run retention in preview mode without deleting any records from disk",
    )
    parser.add_argument(
        "--observations-dir",
        type=str,
        default="data/history/observations",
        help="Path to historical observations storage directory",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("HISTORICAL 365-DAY ROLLING RETENTION ENGINE")
    print("=" * 80)
    print(f"Retention Window:       {args.retention_days} days")
    print(f"Dry Run Mode:           {args.dry_run}")
    print(f"Storage Directory:      {args.observations_dir}")
    print("=" * 80)

    store = DiskJsonlHistoricalStore(base_dir=args.observations_dir)
    manager = HistoricalRetentionManager(store=store, default_retention_days=args.retention_days)

    res = await manager.run_retention(cutoff_days=args.retention_days, dry_run=args.dry_run)
    stats = await manager.get_retention_statistics()

    print("\n" + "=" * 80)
    print("RETENTION EXECUTION REPORT")
    print("=" * 80)
    print(f"Status:                 {'PREVIEW (DRY-RUN)' if res.is_dry_run else 'EXECUTED (PERMANENT)'}")
    print(f"Total Inspected:        {res.total_inspected}")
    print(f"Expired (> {args.retention_days}d):      {res.expired_count}")
    print(f"Deleted Records:        {res.deleted_count}")
    print(f"Preserved Records:      {res.preserved_count}")
    print(f"Oldest Active Date:     {res.oldest_preserved_date or 'N/A'}")
    print(f"Tracked Products Left:  {stats.get('tracked_products', 0)}")
    print(f"Total History Size:     {stats.get('total_size_bytes', 0)} bytes")
    print(f"Execution Latency:      {res.execution_time_ms} ms")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
