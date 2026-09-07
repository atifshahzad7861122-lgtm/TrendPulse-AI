"""Historical collection engine orchestrating crawl, intelligence extraction, deltas, and storage."""

import asyncio
from datetime import datetime, timezone
import hashlib
import time
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.crawling.models import MarketplaceType
from app.discovery.models import ProductTarget
from app.history.checkpoints import HistoricalCheckpoint, HistoricalCheckpointManager
from app.history.delta import HistoricalDeltaEngine
from app.history.models import (
    HistoricalCollectionStats,
    HistoricalObservation,
)
from app.history.store import BaseHistoricalStore, DiskJsonlHistoricalStore
from app.intelligence.models import ExtractionStatus
from app.intelligence.pipeline import ProductIntelligenceEngine
from app.intelligence.validation import DataQualityGate

logger = get_logger(__name__)


class HistoricalCollectionConfig(BaseModel):
    """Configuration options for historical product collection pipeline."""
    max_concurrency: int = Field(default=3, ge=1, le=10, description="Max concurrent extractions")
    window_days: int = Field(default=30, ge=1, description="Target collection window in days")
    bucket_hours: int = Field(default=1, ge=1, description="Deduplication time bucket in hours")
    enforce_quality_gate: bool = Field(default=True, description="Whether to reject/flag malformed data")
    batch_size: int = Field(default=10, ge=1, description="Checkpoint and write batch interval")
    checkpoints_dir: str = Field(default="data/history/checkpoints", description="Checkpoint persistence folder")
    observations_dir: str = Field(default="data/history/observations", description="Observation persistence folder")


class HistoricalCollectionEngine:
    """
    Coordinates historical data ingestion from discovery targets into timestamped,
    immutable observations with delta calculations and rolling retention support.
    """

    def __init__(
        self,
        store: Optional[BaseHistoricalStore] = None,
        intelligence_engine: Optional[ProductIntelligenceEngine] = None,
        config: Optional[HistoricalCollectionConfig] = None,
    ):
        self.config = config or HistoricalCollectionConfig()
        self.store = store or DiskJsonlHistoricalStore(base_dir=self.config.observations_dir)
        self.intelligence_engine = intelligence_engine or ProductIntelligenceEngine()
        self.checkpoint_manager = HistoricalCheckpointManager(checkpoints_dir=self.config.checkpoints_dir)

    def _compute_content_hash(self, title: str, price: float, currency: str, desc: Optional[str]) -> str:
        payload = f"{title.strip()}|{price}|{currency}|{(desc or '').strip()[:200]}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _compute_images_hash(self, urls: List[str]) -> str:
        payload = ",".join(sorted(urls))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def collect_target(
        self,
        target: Union[ProductTarget, Dict[str, Any], str],
        marketplace: Optional[MarketplaceType] = None,
        crawl_id: Optional[str] = None,
    ) -> Optional[HistoricalObservation]:
        """
        Execute discovery -> intelligence extraction -> validation -> delta calculation -> persistence
        for a single product target.
        """
        # Resolve URL and marketplace
        url: str = ""
        pid: Optional[str] = None
        target_mkt = marketplace

        if isinstance(target, str):
            url = target
        elif isinstance(target, ProductTarget):
            url = target.url
            pid = target.product_id
            target_mkt = getattr(target, "marketplace", marketplace) or marketplace
        elif isinstance(target, dict):
            url = target.get("url", "")
            pid = target.get("product_id")
            if "marketplace" in target:
                m_val = target["marketplace"]
                target_mkt = MarketplaceType(m_val) if isinstance(m_val, str) else m_val

        if not url:
            logger.error("Cannot collect target without valid URL")
            return None

        # 1. Extract intelligence
        res = await self.intelligence_engine.extract_product(url, marketplace=target_mkt)

        if res.status == ExtractionStatus.CHALLENGE:
            logger.warning(f"Anti-bot challenge encountered on {url}. Safe pause required.")
            return None

        if not res.success or not res.product:
            logger.warning(f"Intelligence extraction failed for {url}: {res.errors}")
            return None

        product = res.product
        mkt = product.marketplace
        resolved_pid = product.product_id or pid or "unknown"
        now_utc = datetime.now(timezone.utc)

        # 2. Quality Gate Verification
        quality_status = "accepted"
        validation_msgs = []
        if self.config.enforce_quality_gate:
            is_valid, errs, warns = DataQualityGate.validate(product)
            validation_msgs = errs + warns
            if not is_valid:
                quality_status = "rejected"
                logger.warning(f"Product {resolved_pid} rejected by DataQualityGate: {errs}")
            elif warns:
                quality_status = "warning"

        # 3. Deduplication Check (Same hour bucket)
        is_dup, obs_id = self.checkpoint_manager.is_duplicate_observation(
            marketplace=mkt,
            product_id=resolved_pid,
            observed_at=now_utc,
            bucket_hours=self.config.bucket_hours,
        )
        if is_dup:
            logger.info(f"Duplicate observation skipped for {mkt.value}:{resolved_pid} in bucket")
            return None

        # 4. Hashes Calculation
        content_h = self._compute_content_hash(
            title=product.title,
            price=product.price,
            currency=product.currency,
            desc=product.description_text,
        )
        img_urls = [img.url for img in product.images] if product.images else []
        if product.primary_image and product.primary_image not in img_urls:
            img_urls.insert(0, product.primary_image)
        images_h = self._compute_images_hash(img_urls)

        # 5. Fetch previous observation and calculate deltas
        previous_obs = await self.store.get_latest_observation(marketplace=mkt, product_id=resolved_pid)

        # Pre-construct observation without deltas to feed delta engine
        temp_obs = HistoricalObservation(
            observation_id=obs_id,
            product_id=resolved_pid,
            marketplace=mkt,
            product_url=product.canonical_url or url,
            observed_at=now_utc,
            crawl_id=crawl_id,
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
            seller_id=product.seller_id,
            seller_name=product.seller_name,
            category_id=product.category_id,
            category_path=product.category_path,
            variants_count=len(product.variants),
            specifications_count=len(product.specifications),
            images_hash=images_h,
            content_hash=content_h,
            source="historical_collector",
            extraction_confidence=res.overall_confidence,
            raw_data_reference=None,
            quality_status=quality_status,
            validation_messages=validation_msgs,
        )

        deltas = HistoricalDeltaEngine.calculate_deltas(temp_obs, previous_obs)

        # Final immutable observation with deltas attached
        final_obs = HistoricalObservation(
            observation_id=obs_id,
            product_id=resolved_pid,
            marketplace=mkt,
            product_url=product.canonical_url or url,
            observed_at=now_utc,
            crawl_id=crawl_id,
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
            deltas=deltas,
            availability=product.availability,
            seller_id=product.seller_id,
            seller_name=product.seller_name,
            category_id=product.category_id,
            category_path=product.category_path,
            variants_count=len(product.variants),
            specifications_count=len(product.specifications),
            images_hash=images_h,
            content_hash=content_h,
            source="historical_collector",
            extraction_confidence=res.overall_confidence,
            raw_data_reference=None,
            quality_status=quality_status,
            validation_messages=validation_msgs,
        )

        # 6. Store observation
        await self.store.save_observation(final_obs)
        return final_obs

    async def collect_batch(
        self,
        targets: List[Union[ProductTarget, Dict[str, Any], str]],
        marketplace: Optional[MarketplaceType] = None,
        resume_crawl_id: Optional[str] = None,
    ) -> HistoricalCollectionStats:
        """
        Execute concurrent historical observation collection over a list of targets
        with crash-recovery checkpointing and challenge detection pause.
        """
        t_start = time.monotonic()
        crawl_id = resume_crawl_id or str(uuid.uuid4())

        checkpoint = None
        if resume_crawl_id:
            checkpoint = self.checkpoint_manager.load_checkpoint(resume_crawl_id)

        if not checkpoint:
            checkpoint = HistoricalCheckpoint(
                crawl_id=crawl_id,
                marketplace=marketplace,
                started_at=datetime.now(timezone.utc),
            )

        sem = asyncio.Semaphore(self.config.max_concurrency)
        total_discovered = len(targets)
        created_count = checkpoint.observations_created
        failed_count = len(checkpoint.failed_product_ids)
        challenge_count = len(checkpoint.challenge_product_ids)
        rejection_count = checkpoint.rejections
        dup_count = checkpoint.duplicates_prevented
        latencies: List[float] = []

        async def _worker(target_item: Any) -> Optional[HistoricalObservation]:
            nonlocal created_count, failed_count, challenge_count, rejection_count, dup_count
            # Identify target key
            t_url = target_item.url if isinstance(target_item, ProductTarget) else (
                target_item.get("url") if isinstance(target_item, dict) else str(target_item)
            )
            t_pid = target_item.product_id if isinstance(target_item, ProductTarget) else (
                target_item.get("product_id", t_url) if isinstance(target_item, dict) else t_url
            )

            if t_pid in checkpoint.processed_product_ids:
                return None  # Already processed in prior run

            async with sem:
                t0 = time.monotonic()
                try:
                    obs = await self.collect_target(target_item, marketplace=marketplace, crawl_id=crawl_id)
                    latencies.append((time.monotonic() - t0) * 1000)

                    if obs is not None:
                        created_count += 1
                        checkpoint.processed_product_ids.add(t_pid)
                        checkpoint.last_processed_id = t_pid
                        if obs.quality_status == "rejected":
                            rejection_count += 1
                        return obs
                    else:
                        # Check if it was duplicate or failed
                        failed_count += 1
                        checkpoint.failed_product_ids.add(t_pid)
                        return None
                except Exception as exc:
                    logger.error(f"Historical collection worker error on {t_url}: {exc}")
                    failed_count += 1
                    checkpoint.failed_product_ids.add(t_pid)
                    return None

        # Execute in batches
        for i in range(0, len(targets), self.config.batch_size):
            batch = targets[i : i + self.config.batch_size]
            tasks = [_worker(t) for t in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Update and persist checkpoint
            checkpoint.observations_created = created_count
            checkpoint.rejections = rejection_count
            checkpoint.duplicates_prevented = dup_count
            self.checkpoint_manager.save_checkpoint(checkpoint)

        checkpoint.status = "completed"
        self.checkpoint_manager.save_checkpoint(checkpoint)

        avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        return HistoricalCollectionStats(
            crawl_id=crawl_id,
            started_at=checkpoint.started_at,
            completed_at=datetime.now(timezone.utc),
            marketplace=marketplace,
            window_days=self.config.window_days,
            products_discovered=total_discovered,
            products_extracted=created_count + failed_count,
            successful=created_count,
            failed=failed_count,
            challenges=challenge_count,
            observations_created=created_count,
            duplicates_prevented=dup_count,
            rejected=rejection_count,
            avg_latency_ms=avg_lat,
        )
