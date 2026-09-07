"""Unit tests for HistoricalCollectionEngine."""

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock

from app.crawling.models import MarketplaceType
from app.discovery.models import ProductTarget
from app.history.collector import HistoricalCollectionConfig, HistoricalCollectionEngine
from app.history.store import InMemoryHistoricalStore
from app.intelligence.models import (
    ExtractionStatus,
    IntelligenceExtractionResult,
    ProductIntelligence,
)
from app.intelligence.pipeline import ProductIntelligenceEngine


@pytest.mark.asyncio
async def test_historical_collector_single_target(tmp_path):
    store = InMemoryHistoricalStore()
    mock_intel_engine = AsyncMock(spec=ProductIntelligenceEngine)

    prod = ProductIntelligence(
        product_id="B08N5WRWNW",
        marketplace=MarketplaceType.AMAZON,
        source_url="https://www.amazon.com/dp/B08N5WRWNW",
        canonical_url="https://www.amazon.com/dp/B08N5WRWNW",
        title="PlayStation 5 Console",
        price=499.99,
        rating=4.9,
        review_count=15000,
        sold_count=50000,
        seller_id="amazon-retail",
        seller_name="Amazon.com",
    )
    res = IntelligenceExtractionResult(
        extraction_id="ext_001",
        product_id="B08N5WRWNW",
        marketplace=MarketplaceType.AMAZON,
        url="https://www.amazon.com/dp/B08N5WRWNW",
        status=ExtractionStatus.SUCCESS,
        success=True,
        product=prod,
        overall_confidence=0.95,
    )
    mock_intel_engine.extract_product.return_value = res

    config = HistoricalCollectionConfig(
        checkpoints_dir=str(tmp_path / "checkpoints"),
        observations_dir=str(tmp_path / "observations"),
    )
    engine = HistoricalCollectionEngine(store=store, intelligence_engine=mock_intel_engine, config=config)

    target = ProductTarget(
        product_id="B08N5WRWNW",
        url="https://www.amazon.com/dp/B08N5WRWNW",
        marketplace=MarketplaceType.AMAZON,
    )

    obs = await engine.collect_target(target)
    assert obs is not None
    assert obs.product_id == "B08N5WRWNW"
    assert obs.price == 499.99
    assert obs.sold_count == 50000
    assert obs.content_hash is not None
    assert obs.quality_status == "accepted"

    # Verify store has the observation
    stored = await store.get_latest_observation(MarketplaceType.AMAZON, "B08N5WRWNW")
    assert stored is not None
    assert stored.product_id == "B08N5WRWNW"


@pytest.mark.asyncio
async def test_historical_collector_batch_execution(tmp_path):
    store = InMemoryHistoricalStore()
    mock_intel_engine = AsyncMock(spec=ProductIntelligenceEngine)

    def _mock_extract(url, marketplace=None):
        pid = url.split("/")[-1]
        prod = ProductIntelligence(
            product_id=pid,
            marketplace=MarketplaceType.AMAZON,
            source_url=url,
            canonical_url=url,
            title=f"Item {pid}",
            price=29.99,
        )
        return IntelligenceExtractionResult(
            extraction_id=f"ext_{pid}",
            product_id=pid,
            marketplace=MarketplaceType.AMAZON,
            url=url,
            status=ExtractionStatus.SUCCESS,
            success=True,
            product=prod,
            overall_confidence=0.85,
        )

    mock_intel_engine.extract_product.side_effect = _mock_extract

    config = HistoricalCollectionConfig(
        max_concurrency=2,
        batch_size=2,
        checkpoints_dir=str(tmp_path / "checkpoints"),
        observations_dir=str(tmp_path / "observations"),
    )
    engine = HistoricalCollectionEngine(store=store, intelligence_engine=mock_intel_engine, config=config)

    targets = [
        "https://www.amazon.com/dp/P1",
        "https://www.amazon.com/dp/P2",
        "https://www.amazon.com/dp/P3",
    ]

    stats = await engine.collect_batch(targets, marketplace=MarketplaceType.AMAZON)
    assert stats.products_discovered == 3
    assert stats.observations_created == 3
    assert stats.failed == 0
