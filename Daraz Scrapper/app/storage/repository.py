"""In-memory reference storage repository implementing BaseStorage interface."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.checkpoint import CrawlCheckpoint
from app.core.exceptions import StorageError
from app.models.category import Category
from app.models.crawl import CrawlRun
from app.models.image import Image
from app.models.product import Product
from app.models.raw_data import RawDataRecord
from app.models.review import Review
from app.models.seller import Seller
from app.storage.base import BaseStorage


class InMemoryStorage(BaseStorage):
    """Thread-safe and async-safe in-memory store for development, testing, and decoupling."""

    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._reviews: Dict[str, Review] = {}
        self._categories: Dict[str, Category] = {}
        self._sellers: Dict[str, Seller] = {}
        self._images: Dict[str, Image] = {}
        self._crawls: Dict[str, CrawlRun] = {}
        self._raw_records: Dict[str, RawDataRecord] = {}
        self._checkpoints: Dict[str, CrawlCheckpoint] = {}
        self._snapshots: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    # --- Product Operations ---
    async def save_product(self, product: Product) -> None:
        async with self._lock:
            try:
                self._products[product.product_id] = product
            except Exception as e:
                raise StorageError(f"Failed to save product {product.product_id}: {e}") from e

    async def save_products(self, products: List[Product]) -> int:
        async with self._lock:
            try:
                for p in products:
                    self._products[p.product_id] = p
                return len(products)
            except Exception as e:
                raise StorageError(f"Failed to bulk save products: {e}") from e

    async def get_product(self, product_id: str) -> Optional[Product]:
        async with self._lock:
            return self._products.get(product_id)

    # --- Review Operations ---
    async def save_review(self, review: Review) -> None:
        async with self._lock:
            try:
                self._reviews[review.review_id] = review
            except Exception as e:
                raise StorageError(f"Failed to save review {review.review_id}: {e}") from e

    async def save_reviews(self, reviews: List[Review]) -> int:
        async with self._lock:
            try:
                for r in reviews:
                    self._reviews[r.review_id] = r
                return len(reviews)
            except Exception as e:
                raise StorageError(f"Failed to bulk save reviews: {e}") from e

    # --- Classification & Entity Operations ---
    async def save_category(self, category: Category) -> None:
        async with self._lock:
            try:
                self._categories[category.category_id] = category
            except Exception as e:
                raise StorageError(f"Failed to save category {category.category_id}: {e}") from e

    async def save_seller(self, seller: Seller) -> None:
        async with self._lock:
            try:
                self._sellers[seller.seller_id] = seller
            except Exception as e:
                raise StorageError(f"Failed to save seller {seller.seller_id}: {e}") from e

    async def save_image(self, image: Image) -> None:
        async with self._lock:
            try:
                self._images[image.image_id] = image
            except Exception as e:
                raise StorageError(f"Failed to save image {image.image_id}: {e}") from e

    async def save_images(self, images: List[Image]) -> int:
        async with self._lock:
            try:
                for img in images:
                    self._images[img.image_id] = img
                return len(images)
            except Exception as e:
                raise StorageError(f"Failed to bulk save images: {e}") from e

    # --- Raw Data Preservation ---
    async def save_raw_data(self, record: RawDataRecord) -> None:
        async with self._lock:
            try:
                self._raw_records[record.raw_id] = record
            except Exception as e:
                raise StorageError(f"Failed to save raw data record {record.raw_id}: {e}") from e

    async def save_raw_data_batch(self, records: List[RawDataRecord]) -> int:
        async with self._lock:
            try:
                for rec in records:
                    self._raw_records[rec.raw_id] = rec
                return len(records)
            except Exception as e:
                raise StorageError(f"Failed to bulk save raw data records: {e}") from e

    async def get_raw_data(self, raw_id: str) -> Optional[RawDataRecord]:
        async with self._lock:
            return self._raw_records.get(raw_id)

    async def save_snapshot(self, entity_id: str, data: Dict[str, Any], entity_type: str = "product") -> None:
        async with self._lock:
            try:
                self._snapshots.append({
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "data": data,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                raise StorageError(f"Failed to save snapshot for {entity_id}: {e}") from e

    # --- Checkpoints & Session Runs ---
    async def save_checkpoint(self, checkpoint: CrawlCheckpoint) -> None:
        async with self._lock:
            try:
                self._checkpoints[checkpoint.crawl_id] = checkpoint
            except Exception as e:
                raise StorageError(f"Failed to save checkpoint for crawl {checkpoint.crawl_id}: {e}") from e

    async def get_checkpoint(self, crawl_id: str) -> Optional[CrawlCheckpoint]:
        async with self._lock:
            return self._checkpoints.get(crawl_id)

    async def create_crawl_run(self, crawl: CrawlRun) -> CrawlRun:
        async with self._lock:
            try:
                self._crawls[crawl.crawl_id] = crawl
                return crawl
            except Exception as e:
                raise StorageError(f"Failed to create crawl run {crawl.crawl_id}: {e}") from e

    async def update_crawl_run(self, crawl_id: str, **updates: Any) -> Optional[CrawlRun]:
        async with self._lock:
            try:
                existing = self._crawls.get(crawl_id)
                if not existing:
                    return None

                updated_dict = existing.model_dump()
                updated_dict.update(updates)
                updated = CrawlRun(**updated_dict)
                self._crawls[crawl_id] = updated
                return updated
            except Exception as e:
                raise StorageError(f"Failed to update crawl run {crawl_id}: {e}") from e

    async def get_crawl_run(self, crawl_id: str) -> Optional[CrawlRun]:
        async with self._lock:
            return self._crawls.get(crawl_id)

    # --- Discovery Engine Implementations ---
    async def save_category_target(self, target: Any) -> None:
        async with self._lock:
            if not hasattr(self, "_category_targets"):
                self._category_targets = {}
            self._category_targets[target.category_id] = target

    async def get_category_targets(self) -> List[Any]:
        async with self._lock:
            if not hasattr(self, "_category_targets"):
                self._category_targets = {}
            return list(self._category_targets.values())

    async def save_product_target(self, target: Any) -> None:
        async with self._lock:
            if not hasattr(self, "_product_targets"):
                self._product_targets = {}
            self._product_targets[target.product_id] = target

    async def save_product_targets(self, targets: List[Any]) -> int:
        async with self._lock:
            if not hasattr(self, "_product_targets"):
                self._product_targets = {}
            for t in targets:
                self._product_targets[t.product_id] = t
            return len(targets)

    async def get_product_targets(self) -> List[Any]:
        async with self._lock:
            if not hasattr(self, "_product_targets"):
                self._product_targets = {}
            return list(self._product_targets.values())

    async def save_discovery_run(self, run: Any) -> Any:
        async with self._lock:
            if not hasattr(self, "_discovery_runs"):
                self._discovery_runs = {}
            self._discovery_runs[run.crawl_id] = run
            return run

    async def get_discovery_run(self, crawl_id: str) -> Optional[Any]:
        async with self._lock:
            if not hasattr(self, "_discovery_runs"):
                self._discovery_runs = {}
            return self._discovery_runs.get(crawl_id)

    async def update_discovery_run(self, crawl_id: str, **updates: Any) -> Optional[Any]:
        async with self._lock:
            if not hasattr(self, "_discovery_runs"):
                self._discovery_runs = {}
            existing = self._discovery_runs.get(crawl_id)
            if not existing:
                return None
            updated_dict = existing.model_dump()
            updated_dict.update(updates)
            updated = type(existing)(**updated_dict)
            self._discovery_runs[crawl_id] = updated
            return updated

    async def save_snapshot(self, snapshot: Any) -> None:
        async with self._lock:
            self._snapshots.append(snapshot)

    async def get_snapshots(self, product_id: Optional[str] = None) -> List[Any]:
        async with self._lock:
            if product_id:
                return [
                    s for s in self._snapshots
                    if (isinstance(s, dict) and s.get("product_id") == product_id)
                    or getattr(s, "product_id", None) == product_id
                ]
            return list(self._snapshots)
