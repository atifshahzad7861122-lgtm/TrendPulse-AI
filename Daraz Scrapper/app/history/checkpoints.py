"""Historical collection checkpoint and deduplication manager."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.crawling.models import MarketplaceType
from app.history.models import HistoricalObservation


class HistoricalCheckpoint(BaseModel):
    """Progress state checkpoint for an in-flight historical collection session."""
    crawl_id: str
    marketplace: Optional[MarketplaceType] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "in_progress"  # in_progress, paused_challenge, completed, failed
    processed_product_ids: Set[str] = Field(default_factory=set)
    failed_product_ids: Set[str] = Field(default_factory=set)
    challenge_product_ids: Set[str] = Field(default_factory=set)
    observations_created: int = 0
    duplicates_prevented: int = 0
    rejections: int = 0
    last_processed_id: Optional[str] = None


class HistoricalCheckpointManager:
    """
    Persists and restores progress checkpoints to enable pause, resume, and crash recovery.
    Also handles deterministic observation ID deduplication.
    """

    def __init__(self, checkpoints_dir: str = "data/history/checkpoints"):
        self.checkpoints_dir = Path(checkpoints_dir)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._seen_observation_ids: Set[str] = set()

    def _get_checkpoint_path(self, crawl_id: str) -> Path:
        safe_id = "".join(c for c in crawl_id if c.isalnum() or c in ("-", "_"))
        return self.checkpoints_dir / f"checkpoint_{safe_id}.json"

    def save_checkpoint(self, checkpoint: HistoricalCheckpoint) -> None:
        """Persist checkpoint to disk atomically."""
        checkpoint.updated_at = datetime.now(timezone.utc)
        path = self._get_checkpoint_path(checkpoint.crawl_id)
        temp_path = path.with_suffix(".tmp")

        data = checkpoint.model_dump(mode="json")
        # Ensure sets are serialized to lists
        data["processed_product_ids"] = list(checkpoint.processed_product_ids)
        data["failed_product_ids"] = list(checkpoint.failed_product_ids)
        data["challenge_product_ids"] = list(checkpoint.challenge_product_ids)

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_path.replace(path)

    def load_checkpoint(self, crawl_id: str) -> Optional[HistoricalCheckpoint]:
        """Load an existing checkpoint by crawl_id."""
        path = self._get_checkpoint_path(crawl_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["processed_product_ids"] = set(data.get("processed_product_ids", []))
                data["failed_product_ids"] = set(data.get("failed_product_ids", []))
                data["challenge_product_ids"] = set(data.get("challenge_product_ids", []))
                return HistoricalCheckpoint.model_validate(data)
        except Exception:
            return None

    def is_duplicate_observation(
        self,
        marketplace: MarketplaceType,
        product_id: str,
        observed_at: datetime,
        bucket_hours: int = 1,
    ) -> Tuple[bool, str]:
        """
        Check if an observation has already been recorded in the current bucket.
        Returns (is_duplicate, deterministic_observation_id).
        """
        obs_id = HistoricalObservation.generate_deterministic_id(
            marketplace=marketplace,
            product_id=product_id,
            observed_at=observed_at,
            bucket_hours=bucket_hours,
        )
        if obs_id in self._seen_observation_ids:
            return True, obs_id

        self._seen_observation_ids.add(obs_id)
        return False, obs_id
