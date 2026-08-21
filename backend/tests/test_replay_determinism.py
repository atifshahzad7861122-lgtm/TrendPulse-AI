import pytest
from datetime import datetime, timezone
from backend.app.domain.signals import PlatformSignal
from backend.app.repositories.in_memory import InMemoryProductRepository
from backend.app.services.intelligence import ProductIntelligenceEngine
from backend.app.domain.matching import ProductMatchingEngine
from backend.app.domain.data_quality import DataQualityService

def test_replay_deterministic_invariance():
    """
    Verifies that replaying the exact same incoming dataset twice produces
    deterministic, mathematically invariant intelligence output.
    """
    raw_signal = PlatformSignal(
        id="sig_replay_01",
        platform="YouTube",
        product_id="prod_01",
        product_name="HydroGlow Thermal Lip Serum Color Shift Review",
        category="Beauty & Personal Care",
        timestamp=datetime.now(timezone.utc),
        volume=120000,
        engagement_rate=0.088,
        views_count=120000,
        likes_count=9800,
        comments_count=1200,
        sentiment_score=0.91,
        mode="live"
    )

    # Ingestion Run 1
    repo1 = InMemoryProductRepository()
    engine1 = ProductIntelligenceEngine(repo1)
    p1 = repo1.get_by_id("prod_01")
    p1.volume += raw_signal.volume
    enriched1 = engine1._enrich_product(p1)

    # Ingestion Run 2
    repo2 = InMemoryProductRepository()
    engine2 = ProductIntelligenceEngine(repo2)
    p2 = repo2.get_by_id("prod_01")
    p2.volume += raw_signal.volume
    enriched2 = engine2._enrich_product(p2)

    assert enriched1.trend_score == enriched2.trend_score
    assert enriched1.velocity_label == enriched2.velocity_label
    assert enriched1.raw_data["scoring_detail"]["top_contributors"] == enriched2.raw_data["scoring_detail"]["top_contributors"]
    assert enriched1.raw_data["demand_detail"]["demand_score"] == enriched2.raw_data["demand_detail"]["demand_score"]
    assert enriched1.raw_data["viral_detail"]["viral_score"] == enriched2.raw_data["viral_detail"]["viral_score"]
