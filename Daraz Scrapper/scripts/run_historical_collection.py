"""Command-line script for executing historical data collection."""

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.crawling.models import MarketplaceType
from app.history import HistoricalCollectionConfig, HistoricalCollectionEngine


async def main():
    parser = argparse.ArgumentParser(description="TrendPulse Historical Collection CLI")
    parser.add_argument(
        "--marketplace",
        type=str,
        choices=["daraz", "amazon", "ebay", "aliexpress", "shopify"],
        default="daraz",
        help="Target marketplace platform",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        help="List of product URLs to collect historical observations for",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Max concurrent extraction workers",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Historical observation target window in days",
    )
    parser.add_argument(
        "--resume-crawl-id",
        type=str,
        default=None,
        help="Resume an in-progress crawl session by crawl_id",
    )

    args = parser.parse_args()
    mkt = MarketplaceType(args.marketplace)

    default_urls = {
        MarketplaceType.DARAZ: ["https://www.daraz.pk/products/laptop-stand-i100200-s300400.html"],
        MarketplaceType.AMAZON: ["https://www.amazon.com/dp/B08N5WRWNW"],
        MarketplaceType.EBAY: ["https://www.ebay.com/itm/123456789012"],
        MarketplaceType.ALIEXPRESS: ["https://www.aliexpress.com/item/1005001234567890.html"],
        MarketplaceType.SHOPIFY: ["https://shop.allbirds.com/products/mens-tree-runners.json"],
    }

    target_urls = args.urls or default_urls.get(mkt, [])

    print("=" * 80)
    print("HISTORICAL COLLECTION ENGINE")
    print("=" * 80)
    print(f"Marketplace:         {mkt.value}")
    print(f"Target Window:       {args.window_days} days")
    print(f"Concurrency Limit:   {args.concurrency}")
    print(f"Targets to Process:  {len(target_urls)}")
    print("=" * 80)

    config = HistoricalCollectionConfig(
        max_concurrency=args.concurrency,
        window_days=args.window_days,
    )
    engine = HistoricalCollectionEngine(config=config)

    t0 = time.monotonic()
    stats = await engine.collect_batch(
        targets=target_urls,
        marketplace=mkt,
        resume_crawl_id=args.resume_crawl_id,
    )
    elapsed = round(time.monotonic() - t0, 2)

    print("\n" + "=" * 80)
    print("HISTORICAL COLLECTION REPORT")
    print("=" * 80)
    print(f"Marketplace:            {mkt.value}")
    print(f"Window:                 {stats.window_days} days")
    print(f"Crawl ID:               {stats.crawl_id}")
    print(f"Products discovered:    {stats.products_discovered}")
    print(f"Products extracted:     {stats.products_extracted}")
    print(f"Successful:             {stats.successful}")
    print(f"Failed:                 {stats.failed}")
    print(f"Challenges:             {stats.challenges}")
    print(f"Observations created:   {stats.observations_created}")
    print(f"Duplicates prevented:   {stats.duplicates_prevented}")
    print(f"Rejected by Quality:    {stats.rejected}")
    print(f"Average latency:        {stats.avg_latency_ms} ms")
    print(f"Total Execution Time:   {elapsed} s")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
