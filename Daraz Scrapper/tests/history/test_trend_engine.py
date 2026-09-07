"""Unit tests for TrendEngine."""

from datetime import datetime, timedelta, timezone
from app.crawling.models import MarketplaceType
from app.history.models import HistoricalObservation, TrendSignal
from app.history.trends import TrendEngine


def test_trend_engine_insufficient_data():
    now = datetime.now(timezone.utc)
    obs = HistoricalObservation(
        product_id="P1",
        marketplace=MarketplaceType.AMAZON,
        product_url="https://amazon.com/dp/P1",
        observed_at=now,
        title="Product One",
        price=50.0,
    )

    res = TrendEngine.analyze_trend([obs])
    assert res.signal == TrendSignal.INSUFFICIENT_DATA
    assert res.score == 0.0


def test_trend_engine_detects_rising_signal():
    t0 = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)

    obs1 = HistoricalObservation(
        product_id="P1",
        marketplace=MarketplaceType.AMAZON,
        product_url="https://amazon.com/dp/P1",
        observed_at=t0,
        title="Viral Gadget",
        price=50.0,
        rating=4.5,
        review_count=100,
        sold_count=1000,
        availability=True,
    )
    obs2 = HistoricalObservation(
        product_id="P1",
        marketplace=MarketplaceType.AMAZON,
        product_url="https://amazon.com/dp/P1",
        observed_at=t1,
        title="Viral Gadget",
        price=45.0,
        discount=10.0,
        rating=4.7,
        review_count=250,
        sold_count=2500,  # 1500 sales over 9 days = ~166/day
        availability=True,
    )

    res = TrendEngine.analyze_trend([obs1, obs2])
    assert res.signal == TrendSignal.RISING
    assert res.score >= 65.0
    assert "Rising trend" in res.summary


def test_trend_engine_detects_declining_signal():
    t0 = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)

    obs1 = HistoricalObservation(
        product_id="P2",
        marketplace=MarketplaceType.AMAZON,
        product_url="https://amazon.com/dp/P2",
        observed_at=t0,
        title="Old Gadget",
        price=50.0,
        rating=4.2,
        review_count=100,
        sold_count=500,
        availability=True,
    )
    obs2 = HistoricalObservation(
        product_id="P2",
        marketplace=MarketplaceType.AMAZON,
        product_url="https://amazon.com/dp/P2",
        observed_at=t1,
        title="Old Gadget",
        price=50.0,
        rating=2.8,  # Degraded rating
        review_count=100,
        sold_count=500,  # Zero sales growth
        availability=False,  # Out of stock
    )

    res = TrendEngine.analyze_trend([obs1, obs2])
    assert res.signal == TrendSignal.DECLINING
    assert res.score <= 35.0
