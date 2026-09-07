"""Unit tests for UniversalCheckpointRecovery and resumable crawling jobs."""

import pytest
from app.crawling.models import CrawlStatus, MarketplaceType
from app.crawling.recovery import CrawlJobSnapshot, UniversalCheckpointRecovery


def test_checkpoint_save_load_and_resumption(tmp_path):
    recovery = UniversalCheckpointRecovery(checkpoints_dir=tmp_path)
    snapshot = CrawlJobSnapshot(
        crawl_id="crawl_ebay_001",
        marketplace=MarketplaceType.EBAY,
        strategy_name="pagination",
        status=CrawlStatus.PAUSED,
        discovered_urls=["https://www.ebay.com/itm/111", "https://www.ebay.com/itm/222"],
        pending_urls=["https://www.ebay.com/itm/222"],
        processed_urls=["https://www.ebay.com/itm/111"],
        current_page=2,
    )

    recovery.save_checkpoint(snapshot)

    # Reload
    loaded = recovery.load_checkpoint("crawl_ebay_001")
    assert loaded is not None
    assert loaded.crawl_id == "crawl_ebay_001"
    assert loaded.status == CrawlStatus.PAUSED
    assert loaded.pending_urls == ["https://www.ebay.com/itm/222"]

    resumable = recovery.list_resumable_jobs()
    assert len(resumable) == 1
    assert resumable[0].crawl_id == "crawl_ebay_001"
