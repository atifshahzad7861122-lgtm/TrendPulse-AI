"""Standalone Multi-Marketplace Product Intelligence Scraper CLI."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure root workspace is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.logging import setup_logger
from app.crawling.models import CrawlContentType, CrawlRequest, MarketplaceType
from app.history.checkpoints import HistoricalCheckpointManager
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.pipeline.engine import ProductIntelligenceEngine
from app.storage.export import DataExporter

logger = setup_logger("scrape_products_cli")


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
    parser = argparse.ArgumentParser(description="Standalone Multi-Marketplace Product Scraper & Exporter")
    parser.add_argument("--marketplace", type=str, default=None, choices=["daraz", "amazon", "ebay", "aliexpress", "shopify"], help="Override marketplace type")
    parser.add_argument("--urls", type=str, required=True, help="Comma-separated URLs or path to file containing URLs")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent workers")
    parser.add_argument("--browser", action="store_true", help="Force browser rendering execution")
    parser.add_argument("--checkpoint-dir", type=str, default="data/checkpoints", help="Directory to persist checkpoints")
    parser.add_argument("--output", type=str, default="data/scraped_products.json", help="Output file path")
    parser.add_argument("--format", type=str, default="json", choices=["json", "jsonl", "csv"], help="Export format")
    parser.add_argument("--export-reviews", type=str, default=None, help="Optional output path for extracted reviews")

    args = parser.parse_args()
    urls = load_urls(args.urls)

    if not urls:
        print("❌ No valid URLs provided.")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("🛒 STANDALONE MULTI-MARKETPLACE PRODUCT SCRAPER")
    print("=" * 65)
    print(f"Target URLs  : {len(urls)}")
    print(f"Concurrency  : {args.concurrency}")
    print(f"Browser Mode : {args.browser}")
    print(f"Output File  : {args.output} ({args.format.upper()})")
    print(f"Checkpoints  : {args.checkpoint_dir}")
    print("=" * 65 + "\n")

    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = checkpoint_dir / "scrape_checkpoint.json"
    checkpoint_data: dict = {}
    if checkpoint_file.exists():
        try:
            checkpoint_data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        except Exception:
            checkpoint_data = {}

    engine = ProductIntelligenceEngine()
    semaphore = asyncio.Semaphore(args.concurrency)
    extracted_products: List[ProductIntelligence] = []
    extracted_reviews: List[IntelligenceReview] = []

    async def scrape_single(target_url: str):
        async with semaphore:
            logger.info(f"Scraping product: {target_url}...")
            # Check checkpoint
            cached = checkpoint_data.get(target_url)
            if cached and cached.get("status") == "success" and "product" in cached:
                logger.info(f"Loaded {target_url} from checkpoint.")
                p = ProductIntelligence(**cached["product"])
                extracted_products.append(p)
                return

            res: IntelligenceExtractionResult = await engine.extract_product(target_url)
            if res.status == ExtractionStatus.CHALLENGE:
                logger.warning(f"⚠️ Challenge encountered on {target_url}. Flagged for manual review.")
            elif res.success and res.product:
                logger.info(f"✅ Successfully extracted {res.product.title[:40]} (Price: {res.product.price} {res.product.currency})")
                extracted_products.append(res.product)
                if res.reviews:
                    extracted_reviews.extend(res.reviews)
                # Save checkpoint
                checkpoint_data[target_url] = {
                    "status": res.status.value,
                    "product": res.product.model_dump(),
                    "confidence": res.overall_confidence,
                }
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, indent=2, default=str)
            else:
                logger.error(f"❌ Failed to extract {target_url}: {res.errors}")

    tasks = [scrape_single(u) for u in urls]
    await asyncio.gather(*tasks)

    # Export Scraped Products
    out_path = DataExporter.export_products(extracted_products, args.output, export_format=args.format)
    print(f"\n📦 Saved {len(extracted_products)} products to: {out_path}")

    # Export Reviews if requested
    if args.export_reviews and extracted_reviews:
        rev_path = DataExporter.export_reviews(extracted_reviews, args.export_reviews, export_format=args.format)
        print(f"💬 Saved {len(extracted_reviews)} reviews to: {rev_path}")

    print("\n" + "=" * 65)
    print("✨ Scrape Run Completed Successfully!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
