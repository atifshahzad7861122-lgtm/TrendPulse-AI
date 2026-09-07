"""Standalone Multi-Marketplace Product Discovery CLI."""

import argparse
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure root workspace is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.logging import setup_logger
from app.crawling.models import MarketplaceType
from app.discovery.engine import DarazDiscoveryEngine
from app.discovery.models import CategoryTarget, ProductTarget
from app.storage.export import DataExporter

logger = setup_logger("discover_products_cli")


async def main():
    parser = argparse.ArgumentParser(description="Standalone Multi-Marketplace Product Discovery Engine")
    parser.add_argument("--marketplace", type=str, default="daraz", choices=["daraz", "amazon", "ebay", "aliexpress", "shopify"], help="Target marketplace")
    parser.add_argument("--keyword", type=str, default=None, help="Search keyword (e.g. 'mechanical keyboard')")
    parser.add_argument("--category", type=str, default=None, help="Category URL / slug")
    parser.add_argument("--max-products", type=int, default=10, help="Maximum products to discover")
    parser.add_argument("--output", type=str, default="data/discovered_products.json", help="Output filepath")
    parser.add_argument("--format", type=str, default="json", choices=["json", "jsonl", "csv"], help="Export format")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🚀 STANDALONE MULTI-MARKETPLACE PRODUCT DISCOVERY")
    print("=" * 60)
    print(f"Marketplace : {args.marketplace.upper()}")
    print(f"Keyword     : {args.keyword or 'N/A'}")
    print(f"Category    : {args.category or 'N/A'}")
    print(f"Max Targets : {args.max_products}")
    print(f"Output File : {args.output} ({args.format.upper()})")
    print("=" * 60 + "\n")

    if not args.keyword and not args.category:
        print("❌ Error: Must provide either --keyword or --category to start discovery.")
        sys.exit(1)

    targets = []
    if args.marketplace.lower() == "daraz":
        engine = DarazDiscoveryEngine()
        if args.keyword:
            logger.info(f"Running Daraz keyword discovery for '{args.keyword}'...")
            targets = await engine.discover_keyword_products(keyword=args.keyword, max_pages=2)
        elif args.category:
            cat = CategoryTarget(category_id="cat_01", name="Custom Category", url=args.category)
            logger.info(f"Running Daraz category discovery for '{args.category}'...")
            targets = await engine.discover_category_products(category_target=cat, max_pages=2)
        
        targets = targets[:args.max_products]
        logger.info(f"Discovered {len(targets)} unique Daraz product targets.")
    else:
        # Generic discovery URL constructor for other marketplaces
        logger.info(f"Generating discovery queue for marketplace: {args.marketplace.upper()}...")
        # Stub query targets
        if args.keyword:
            kw_slug = args.keyword.replace(' ', '+')
            if args.marketplace == "amazon":
                sample_url = f"https://www.amazon.com/s?k={kw_slug}"
            elif args.marketplace == "ebay":
                sample_url = f"https://www.ebay.com/sch/i.html?_nkw={kw_slug}"
            elif args.marketplace == "aliexpress":
                sample_url = f"https://www.aliexpress.com/w/wholesale-{kw_slug}.html"
            else:
                sample_url = f"https://kith.com/collections/all"
            targets.append(ProductTarget(product_id="target_001", url=sample_url, marketplace=MarketplaceType(args.marketplace.lower())))

    # Export Discovered Targets
    target_dicts = [t.model_dump() for t in targets]
    out_path = Path(args.output)
    if args.format == "jsonl":
        DataExporter.export_jsonl(target_dicts, out_path)
    elif args.format == "csv":
        DataExporter.export_csv(target_dicts, out_path)
    else:
        DataExporter.export_json(target_dicts, out_path)

    print("\n" + "=" * 60)
    print(f"✅ Discovery Complete: {len(targets)} targets saved to {out_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
