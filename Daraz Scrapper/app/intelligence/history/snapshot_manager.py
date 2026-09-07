"""Historical snapshot management for 30-day and 365-day trend analytics."""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.crawling.models import MarketplaceType
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.snapshot import HistoricalSnapshot
from app.storage.base import BaseStorage


class HistoricalSnapshotManager:
    """
    Manages creation, appending, and retrieval of point-in-time product observation snapshots.
    Supports TrendPulse 30-day velocity, rating deterioration, and 365-day longevity analysis.
    Never overwrites or deletes historical observations.
    """

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        snapshots_dir: str = "data/intelligence/snapshots",
    ):
        self.storage = storage
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def create_snapshot(self, product: ProductIntelligence) -> HistoricalSnapshot:
        """Create a point-in-time HistoricalSnapshot from ProductIntelligence."""
        return HistoricalSnapshot(
            product_id=product.product_id,
            marketplace=product.marketplace,
            observed_at=datetime.now(timezone.utc),
            title=product.title,
            price=product.price,
            original_price=product.original_price,
            discount=product.discount,
            currency=product.currency,
            rating=product.rating,
            review_count=product.review_count,
            rating_count=product.rating_count,
            sold_count=product.sold_count,
            raw_sold_text=product.raw_sold_text,
            availability=product.availability,
            seller_name=product.seller_name,
            primary_image=product.primary_image,
            image_urls=[img.url for img in product.images],
            source_url=product.canonical_url,
            metadata=product.source_fields,
        )

    async def record_snapshot(self, snapshot: HistoricalSnapshot) -> None:
        """Persist snapshot record to storage and disk append-only log."""
        async with self._lock:
            # 1. Persist to storage repository if available
            if self.storage and hasattr(self.storage, "save_snapshot"):
                try:
                    await self.storage.save_snapshot(snapshot.model_dump(mode="json"))
                except Exception as e:
                    logger.warning(f"Failed to record snapshot to repository: {e}")

            # 2. Append to marketplace/product-specific disk ledger
            try:
                ledger_file = self.snapshots_dir / f"{snapshot.marketplace.value}_{snapshot.product_id}.jsonl"
                with open(ledger_file, "a", encoding="utf-8") as f:
                    f.write(snapshot.model_dump_json() + "\n")
            except Exception as e:
                logger.error(f"Failed to write snapshot to disk ledger: {e}")

    async def get_snapshots_for_product(
        self,
        marketplace: MarketplaceType,
        product_id: str,
    ) -> List[HistoricalSnapshot]:
        """Retrieve all historical point-in-time snapshots for a given product."""
        ledger_file = self.snapshots_dir / f"{marketplace.value}_{product_id}.jsonl"
        if not ledger_file.exists():
            return []

        snapshots: List[HistoricalSnapshot] = []
        try:
            with open(ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line.strip())
                        snapshots.append(HistoricalSnapshot(**data))
        except Exception as e:
            logger.error(f"Error reading snapshot history for {product_id}: {e}")

        return snapshots
