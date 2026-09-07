"""Unit tests for HistoricalSnapshotManager and trend observations."""

import os
import shutil
import pytest

from app.crawling.models import MarketplaceType
from app.intelligence.history import HistoricalSnapshotManager
from app.intelligence.models import (
    HistoricalSnapshot,
    ImageRecord,
    ProductIntelligence,
)


@pytest.mark.asyncio
async def test_snapshot_creation_and_history_retrieval(tmp_path):
    snapshots_dir = str(tmp_path / "snapshots")
    mgr = HistoricalSnapshotManager(snapshots_dir=snapshots_dir)

    prod = ProductIntelligence(
        product_id="B08N5WRWNW",
        marketplace=MarketplaceType.AMAZON,
        source_url="https://www.amazon.com/dp/B08N5WRWNW",
        canonical_url="https://www.amazon.com/dp/B08N5WRWNW",
        title="Sony WH-1000XM4",
        price=278.0,
        original_price=348.0,
        currency="USD",
        rating=4.7,
        review_count=50000,
        sold_count=10000,
        raw_sold_text="10K+ bought in past month",
        seller_name="Sony Store",
        images=[ImageRecord(url="https://m.media-amazon.com/1.jpg", is_primary=True)],
    )

    # 1. First observation (Day 1)
    snap1 = mgr.create_snapshot(prod)
    await mgr.record_snapshot(snap1)

    # 2. Second observation (Price drop on Day 5)
    prod.price = 248.0
    snap2 = mgr.create_snapshot(prod)
    await mgr.record_snapshot(snap2)

    # 3. Retrieve history
    history = await mgr.get_snapshots_for_product(MarketplaceType.AMAZON, "B08N5WRWNW")
    assert len(history) == 2
    assert history[0].price == 278.0
    assert history[1].price == 248.0
    assert history[0].sold_count == 10000
