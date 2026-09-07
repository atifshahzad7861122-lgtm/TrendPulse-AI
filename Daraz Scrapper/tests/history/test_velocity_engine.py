"""Unit tests for SalesVelocityEngine."""

from datetime import datetime, timedelta, timezone
from app.crawling.models import MarketplaceType
from app.history.models import HistoricalObservation
from app.history.velocity import SalesVelocityEngine


def test_velocity_calculation_across_time_interval():
    t0 = datetime(2026, 8, 20, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 8, 25, 0, 0, 0, tzinfo=timezone.utc)  # 5 days later

    obs1 = HistoricalObservation(
        product_id="P1",
        marketplace=MarketplaceType.ALIEXPRESS,
        product_url="https://aliexpress.com/item/P1.html",
        observed_at=t0,
        title="Phone Holder",
        price=10.0,
        review_count=100,
        sold_count=500,
    )

    obs2 = HistoricalObservation(
        product_id="P1",
        marketplace=MarketplaceType.ALIEXPRESS,
        product_url="https://aliexpress.com/item/P1.html",
        observed_at=t1,
        title="Phone Holder",
        price=10.0,
        review_count=120,
        sold_count=650,
    )

    vel = SalesVelocityEngine.calculate_velocity_from_observations([obs1, obs2])
    assert vel.window_days == 5.0
    assert vel.sales_per_day == 30.0  # (650 - 500) / 5 = 30 / day
    assert vel.sales_per_7_days == 210.0  # 30 * 7
    assert vel.sales_per_30_days == 900.0  # 30 * 30
    assert vel.review_growth_rate_per_day == 4.0  # (120 - 100) / 5 = 4 / day


def test_velocity_single_observation_returns_none_metrics():
    now = datetime.now(timezone.utc)
    obs = HistoricalObservation(
        product_id="P1",
        marketplace=MarketplaceType.ALIEXPRESS,
        product_url="https://aliexpress.com/item/P1.html",
        observed_at=now,
        title="Phone Holder",
        price=10.0,
        sold_count=500,
    )

    vel = SalesVelocityEngine.calculate_velocity_from_observations([obs])
    assert vel.sales_per_day is None
    assert vel.window_days == 0.0
    assert vel.observation_count == 1
