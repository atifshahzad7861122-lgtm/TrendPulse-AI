"""Unit tests for InMemoryHistoricalStore and DiskJsonlHistoricalStore."""

from datetime import datetime, timedelta, timezone
import os
import shutil
import pytest

from app.crawling.models import MarketplaceType
from app.history.models import HistoricalObservation
from app.history.store import DiskJsonlHistoricalStore, InMemoryHistoricalStore


@pytest.mark.asyncio
async def test_in_memory_store_lifecycle():
    store = InMemoryHistoricalStore()
    now = datetime.now(timezone.utc)

    obs1 = HistoricalObservation(
        observation_id="obs_001",
        product_id="P1",
        marketplace=MarketplaceType.AMAZON,
        product_url="https://amazon.com/dp/P1",
        observed_at=now - timedelta(days=2),
        title="Widget A",
        price=19.99,
        sold_count=100,
    )
    obs2 = HistoricalObservation(
        observation_id="obs_002",
        product_id="P1",
        marketplace=MarketplaceType.AMAZON,
        product_url="https://amazon.com/dp/P1",
        observed_at=now,
        title="Widget A",
        price=17.99,
        sold_count=130,
    )

    await store.save_observation(obs1)
    await store.save_observation(obs2)

    latest = await store.get_latest_observation(MarketplaceType.AMAZON, "P1")
    assert latest is not None
    assert latest.observation_id == "obs_002"
    assert latest.price == 17.99

    history = await store.get_all_observations_for_product(MarketplaceType.AMAZON, "P1")
    assert len(history) == 2
    assert history[0].observation_id == "obs_001"
    assert history[1].observation_id == "obs_002"

    # Test window query
    window = await store.get_observations_in_window(
        MarketplaceType.AMAZON, "P1", start_date=now - timedelta(days=1)
    )
    assert len(window) == 1
    assert window[0].observation_id == "obs_002"


@pytest.mark.asyncio
async def test_disk_jsonl_store_lifecycle(tmp_path):
    store_dir = str(tmp_path / "observations")
    store = DiskJsonlHistoricalStore(base_dir=store_dir)
    now = datetime.now(timezone.utc)

    obs1 = HistoricalObservation(
        observation_id="disk_obs_001",
        product_id="EBAY123",
        marketplace=MarketplaceType.EBAY,
        product_url="https://ebay.com/itm/EBAY123",
        observed_at=now - timedelta(days=5),
        title="Vintage Watch",
        price=150.0,
        sold_count=10,
    )
    obs2 = HistoricalObservation(
        observation_id="disk_obs_002",
        product_id="EBAY123",
        marketplace=MarketplaceType.EBAY,
        product_url="https://ebay.com/itm/EBAY123",
        observed_at=now,
        title="Vintage Watch",
        price=140.0,
        sold_count=15,
    )

    await store.save_observations([obs1, obs2])

    latest = await store.get_latest_observation(MarketplaceType.EBAY, "EBAY123")
    assert latest is not None
    assert latest.observation_id == "disk_obs_002"
    assert latest.price == 140.0

    all_obs = await store.get_all_observations_for_product(MarketplaceType.EBAY, "EBAY123")
    assert len(all_obs) == 2

    # Verify deduplication on re-save
    saved_count = await store.save_observations([obs1, obs2])
    assert saved_count == 0  # No duplicate lines written
