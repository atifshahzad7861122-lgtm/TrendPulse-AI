"""Unit tests for HistoricalCheckpointManager."""

from datetime import datetime, timezone
from pathlib import Path
from app.crawling.models import MarketplaceType
from app.history.checkpoints import HistoricalCheckpoint, HistoricalCheckpointManager


def test_checkpoint_persistence_and_resume(tmp_path):
    checkpoints_dir = str(tmp_path / "checkpoints")
    manager = HistoricalCheckpointManager(checkpoints_dir=checkpoints_dir)

    cp = HistoricalCheckpoint(
        crawl_id="test-crawl-123",
        marketplace=MarketplaceType.AMAZON,
        processed_product_ids={"B001", "B002"},
        failed_product_ids={"B003"},
        observations_created=2,
    )

    manager.save_checkpoint(cp)

    # Load back
    loaded = manager.load_checkpoint("test-crawl-123")
    assert loaded is not None
    assert loaded.crawl_id == "test-crawl-123"
    assert "B001" in loaded.processed_product_ids
    assert "B003" in loaded.failed_product_ids
    assert loaded.observations_created == 2


def test_checkpoint_deduplication():
    manager = HistoricalCheckpointManager()
    now = datetime.now(timezone.utc)

    # First call: not duplicate
    is_dup1, id1 = manager.is_duplicate_observation(MarketplaceType.DARAZ, "100200", now, bucket_hours=1)
    assert is_dup1 is False

    # Second call in same bucket: duplicate detected
    is_dup2, id2 = manager.is_duplicate_observation(MarketplaceType.DARAZ, "100200", now, bucket_hours=1)
    assert is_dup2 is True
    assert id1 == id2
