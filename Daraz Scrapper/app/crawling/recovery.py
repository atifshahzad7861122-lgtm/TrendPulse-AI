"""Checkpoint persistence and crash recovery for long-running universal crawl jobs."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.crawling.models import CrawlStatus, MarketplaceType
from app.core.logging import logger


class CrawlJobSnapshot(BaseModel):
    """Snapshot model for checkpointing a crawl job state."""
    crawl_id: str
    marketplace: MarketplaceType
    strategy_name: str
    status: CrawlStatus
    discovered_urls: List[str] = Field(default_factory=list)
    processed_urls: List[str] = Field(default_factory=list)
    pending_urls: List[str] = Field(default_factory=list)
    failed_urls: List[str] = Field(default_factory=list)
    duplicate_count: int = 0
    extracted_product_count: int = 0
    current_page: int = 1
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UniversalCheckpointRecovery:
    """
    Manages periodic checkpointing and crash resumption for universal crawling jobs.
    """

    def __init__(self, checkpoints_dir: Optional[Path] = None):
        self.checkpoints_dir = checkpoints_dir or Path("data/checkpoints")
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots: Dict[str, CrawlJobSnapshot] = {}

    def save_checkpoint(self, snapshot: CrawlJobSnapshot) -> None:
        """Write job snapshot to memory and disk."""
        snapshot.updated_at = datetime.now(timezone.utc)
        self._snapshots[snapshot.crawl_id] = snapshot
        try:
            file_path = self.checkpoints_dir / f"{snapshot.crawl_id}.json"
            file_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint for crawl {snapshot.crawl_id}: {e}")

    def load_checkpoint(self, crawl_id: str) -> Optional[CrawlJobSnapshot]:
        """Load job snapshot by crawl ID."""
        if crawl_id in self._snapshots:
            return self._snapshots[crawl_id]

        file_path = self.checkpoints_dir / f"{crawl_id}.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                snapshot = CrawlJobSnapshot(**data)
                self._snapshots[crawl_id] = snapshot
                return snapshot
            except Exception as e:
                logger.warning(f"Failed to parse checkpoint file {file_path}: {e}")

        return None

    def list_resumable_jobs(self) -> List[CrawlJobSnapshot]:
        """List all pending/paused/manual intervention checkpoints."""
        resumable = []
        for f in self.checkpoints_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snapshot = CrawlJobSnapshot(**data)
                if snapshot.status in (CrawlStatus.PAUSED, CrawlStatus.MANUAL_INTERVENTION, CrawlStatus.RUNNING):
                    resumable.append(snapshot)
            except Exception:
                pass
        return resumable
