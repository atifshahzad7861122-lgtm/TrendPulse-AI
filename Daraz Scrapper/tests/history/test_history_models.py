"""Unit tests for HistoricalObservation and supporting data contracts."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.crawling.models import MarketplaceType
from app.history.models import (
    HistoricalObservation,
    ObservationDeltas,
    TrendScore,
    TrendSignal,
    VelocityMetrics,
)


def test_historical_observation_creation_and_immutability():
    obs = HistoricalObservation(
        product_id="D100200",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://www.daraz.pk/products/item-i100200.html",
        title="Gaming Mechanical Keyboard RGB",
        price=4500.0,
        original_price=6000.0,
        discount=25.0,
        currency="PKR",
        rating=4.6,
        review_count=120,
        sold_count=850,
        raw_sold_text="850 sold",
        seller_id="official-gaming-store",
        seller_name="Gaming Official",
        variants_count=3,
        specifications_count=5,
    )

    assert obs.product_id == "D100200"
    assert obs.marketplace == MarketplaceType.DARAZ
    assert obs.price == 4500.0
    assert obs.sold_count == 850
    assert obs.variants_count == 3
    assert obs.quality_status == "accepted"

    # Immutability validation (frozen model)
    with pytest.raises(ValidationError):
        obs.price = 5000.0


def test_deterministic_observation_id_generation():
    dt1 = datetime(2026, 8, 27, 10, 15, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 8, 27, 10, 45, 0, tzinfo=timezone.utc)
    dt_next_hour = datetime(2026, 8, 27, 11, 5, 0, tzinfo=timezone.utc)

    # Same hour bucket should produce identical observation IDs
    id1 = HistoricalObservation.generate_deterministic_id(
        MarketplaceType.AMAZON, "B08N5WRWNW", dt1, bucket_hours=1
    )
    id2 = HistoricalObservation.generate_deterministic_id(
        MarketplaceType.AMAZON, "B08N5WRWNW", dt2, bucket_hours=1
    )
    assert id1 == id2

    # Different hour bucket produces different ID
    id3 = HistoricalObservation.generate_deterministic_id(
        MarketplaceType.AMAZON, "B08N5WRWNW", dt_next_hour, bucket_hours=1
    )
    assert id1 != id3


def test_trend_score_and_velocity_models():
    vel = VelocityMetrics(
        sales_per_day=25.5,
        sales_per_7_days=178.5,
        sales_per_30_days=765.0,
        review_growth_rate_per_day=3.2,
        window_days=5.0,
        observation_count=3,
    )

    trend = TrendScore(
        score=78.5,
        signal=TrendSignal.RISING,
        confidence=0.92,
        velocity=vel,
        observation_count=3,
        summary="Rapidly climbing demand",
    )

    assert trend.signal == TrendSignal.RISING
    assert trend.score == 78.5
    assert trend.velocity.sales_per_30_days == 765.0
