"""Command-line script for running 30-day velocity and trend analysis on historical products."""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.crawling.models import MarketplaceType
from app.history import DiskJsonlHistoricalStore, TrendEngine


async def main():
    parser = argparse.ArgumentParser(description="TrendPulse 30-Day Trend Analysis CLI")
    parser.add_argument(
        "--marketplace",
        type=str,
        choices=["daraz", "amazon", "ebay", "aliexpress", "shopify"],
        default=None,
        help="Optional marketplace filter",
    )
    parser.add_argument(
        "--product-id",
        type=str,
        default=None,
        help="Specific product ID to analyze",
    )
    parser.add_argument(
        "--observations-dir",
        type=str,
        default="data/history/observations",
        help="Path to historical observations storage directory",
    )

    args = parser.parse_args()
    mkt = MarketplaceType(args.marketplace) if args.marketplace else None

    store = DiskJsonlHistoricalStore(base_dir=args.observations_dir)
    products_to_analyze = []

    if args.product_id and mkt:
        products_to_analyze.append((mkt, args.product_id))
    else:
        products_to_analyze = await store.list_tracked_products(marketplace=mkt)

    print("=" * 80)
    print("HISTORICAL 30-DAY VELOCITY & TREND ANALYSIS ENGINE")
    print("=" * 80)
    print(f"Products Found in History: {len(products_to_analyze)}")
    print("=" * 80)

    if not products_to_analyze:
        print("No historical observation records found in store. Run historical collection first.")
        return

    print(f"{'Marketplace':<12} | {'Product ID':<16} | {'Obs':<4} | {'Sales/Day':<10} | {'30D Extrap':<10} | {'Trend Score':<12} | {'Signal':<15}")
    print("-" * 90)

    for m, pid in products_to_analyze:
        history = await store.get_all_observations_for_product(m, pid)
        trend = TrendEngine.analyze_trend(history, min_hours=0.01)

        spd_str = f"{trend.velocity.sales_per_day:.1f}" if trend.velocity and trend.velocity.sales_per_day is not None else "N/A"
        m30_str = f"{trend.velocity.sales_per_30_days:.0f}" if trend.velocity and trend.velocity.sales_per_30_days is not None else "N/A"

        print(
            f"{m.value:<12} | {pid:<16} | {len(history):<4} | {spd_str:<10} | {m30_str:<10} | {trend.score:<12.1f} | {trend.signal.value:<15}"
        )

    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())
