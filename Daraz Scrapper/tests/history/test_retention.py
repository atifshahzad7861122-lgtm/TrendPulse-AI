"""Unit tests for HistoricalRetentionManager."""

from datetime import datetime, timedelta, timezone
import pytest

from app.crawling.models import MarketplaceType
from app.history.models import HistoricalObservation
from app.history.retention import HistoricalRetentionManager
from app.history.store import InMemoryHistoricalStore


@pytest.mark.asyncio
async def test_retention_manager_pruning_and_dry_run():
    store = InMemoryHistoricalStore()
    manager = HistoricalRetentionManager(store=store, default_retention_days=365)
    now = datetime.now(timezone.utc)

    # 1. Observation 400 days old (Expired)
    obs_expired = HistoricalObservation(
        observation_id="old_obs",
        product_id="P1",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://daraz.pk/p1",
        observed_at=now - timedelta(days=400),
        title="Old Product",
        price=10.0,
    )

    # 2. Observation 100 days old (Valid/Active)
    obs_active = HistoricalObservation(
        observation_id="active_obs",
        product_id="P1",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://daraz.pk/p1",
        observed_at=now - timedelta(days=100),
        title="Active Product",
        price=12.0,
    )

    await store.save_observations([obs_expired, obs_active])

    # Test 1: Dry-Run Preview
    preview = await manager.preview_expired(cutoff_days=365)
    assert preview.is_dry_run is True
    assert preview.total_inspected == 2
    assert preview.expired_count == 1
    assert preview.deleted_count == 0
    assert preview.preserved_count == 1

    # Verify store still holds both records after dry-run
    history_after_dry_run = await store.get_all_observations_for_product(MarketplaceType.DARAZ, "P1")
    assert len(history_after_dry_run) == 2

    # Test 2: Permanent Retention Run
    result = await manager.run_retention(cutoff_days=365, dry_run=False)
    assert result.is_dry_run is False
    assert result.total_inspected == 2
    assert result.expired_count == 1
    assert result.deleted_count == 1
    assert result.preserved_count == 1

    # Verify expired record removed, active record preserved
    history_after_run = await store.get_all_observations_for_product(MarketplaceType.DARAZ, "P1")
    assert len(history_after_run) == 1
    assert history_after_run[0].observation_id == "active_obs"

    # Test 3: Idempotency (running again removes 0)
    second_run = await manager.run_retention(cutoff_days=365, dry_run=False)
    assert second_run.expired_count == 0
    assert second_run.deleted_count == 0
    assert second_run.preserved_count == 1
