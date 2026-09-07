"""Tests for CheckpointManager and CrawlJob recovery lifecycle."""

import pytest
from app.core.checkpoint import CheckpointManager, CrawlCheckpoint
from app.core.constants import CrawlStatus
from app.crawler.job import CrawlJob
from app.storage.repository import InMemoryStorage


@pytest.mark.asyncio
async def test_checkpoint_manager_lifecycle():
    storage = InMemoryStorage()
    manager = CheckpointManager(
        storage=storage,
        crawl_id="test-crawl-cp",
        target="electronics",
        checkpoint_interval=2,
    )

    # 1. Record item 1 (below interval)
    await manager.record_progress(position=1, item_id="item-1", url="https://daraz.pk/1", success=True)
    assert await storage.get_checkpoint("test-crawl-cp") is None

    # 2. Record item 2 (triggers interval save)
    await manager.record_progress(position=2, item_id="item-2", url="https://daraz.pk/2", success=True)
    saved = await storage.get_checkpoint("test-crawl-cp")
    assert saved is not None
    assert saved.current_position == 2
    assert saved.completed_items == 2
    assert saved.last_successful_item == "item-2"

    # 3. Simulate crash and resume
    resumed_manager = CheckpointManager(
        storage=storage,
        crawl_id="test-crawl-cp",
        target="electronics",
    )
    resumed = await resumed_manager.resume_checkpoint()
    assert resumed is not None
    assert resumed.completed_items == 2
    assert resumed.current_position == 2


@pytest.mark.asyncio
async def test_crawl_job_manual_intervention_and_checkpoint():
    storage = InMemoryStorage()
    job = CrawlJob(
        storage=storage,
        crawl_id="intervention-crawl",
        target="laptops",
        checkpoint_interval=1,
    )

    await job.start()
    assert job.crawl_run.status == CrawlStatus.RUNNING

    await job.record_processed(position=1, item_id="lap-1", url="https://daraz.pk/lap-1")
    assert job.crawl_run.items_processed == 1

    # Security barrier triggered -> manual intervention
    await job.request_manual_intervention(reason="Slide CAPTCHA required", url="https://sec.daraz.pk/punish")
    assert job.crawl_run.status == CrawlStatus.MANUAL_INTERVENTION

    # Verify persisted in storage
    stored_run = await storage.get_crawl_run("intervention-crawl")
    assert stored_run.status == CrawlStatus.MANUAL_INTERVENTION

    stored_cp = await storage.get_checkpoint("intervention-crawl")
    assert stored_cp.status == CrawlStatus.MANUAL_INTERVENTION
    assert stored_cp.completed_items == 1
