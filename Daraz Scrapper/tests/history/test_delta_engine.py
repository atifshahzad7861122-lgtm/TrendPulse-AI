"""Unit tests for HistoricalDeltaEngine."""

from datetime import datetime, timedelta, timezone
from app.crawling.models import MarketplaceType
from app.history.delta import HistoricalDeltaEngine
from app.history.models import HistoricalObservation


def test_delta_engine_first_observation_returns_empty_deltas():
    now = datetime.now(timezone.utc)
    obs = HistoricalObservation(
        product_id="D100",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://daraz.pk/products/item.html",
        observed_at=now,
        title="Test Item",
        price=100.0,
        sold_count=500,
    )

    deltas = HistoricalDeltaEngine.calculate_deltas(current_obs=obs, previous_obs=None)
    assert deltas.sales_delta is None
    assert deltas.price_delta is None
    assert deltas.time_delta_seconds == 0.0


def test_delta_engine_calculates_exact_differences_and_percentages():
    t0 = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)

    prev_obs = HistoricalObservation(
        product_id="D100",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://daraz.pk/products/item.html",
        observed_at=t0,
        title="Test Item",
        price=100.0,
        rating=4.2,
        review_count=50,
        sold_count=500,
    )

    curr_obs = HistoricalObservation(
        product_id="D100",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://daraz.pk/products/item.html",
        observed_at=t1,
        title="Test Item",
        price=80.0,
        rating=4.5,
        review_count=65,
        sold_count=650,
    )

    deltas = HistoricalDeltaEngine.calculate_deltas(current_obs=curr_obs, previous_obs=prev_obs)
    assert deltas.time_delta_days == 5.0
    assert deltas.sales_delta == 150
    assert deltas.sales_pct_change == 30.0  # (150/500)*100
    assert deltas.review_delta == 15
    assert deltas.review_pct_change == 30.0  # (15/50)*100
    assert deltas.price_delta == -20.0
    assert deltas.price_pct_change == -20.0  # (-20/100)*100
    assert deltas.rating_delta == 0.3


def test_delta_engine_handles_missing_and_zero_values():
    t0 = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 8, 21, 12, 0, 0, tzinfo=timezone.utc)

    prev_obs = HistoricalObservation(
        product_id="D200",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://daraz.pk/products/item2.html",
        observed_at=t0,
        title="Item 2",
        price=0.0,
        review_count=0,
        sold_count=0,
    )

    curr_obs = HistoricalObservation(
        product_id="D200",
        marketplace=MarketplaceType.DARAZ,
        product_url="https://daraz.pk/products/item2.html",
        observed_at=t1,
        title="Item 2",
        price=25.0,
        review_count=5,
        sold_count=10,
    )

    deltas = HistoricalDeltaEngine.calculate_deltas(current_obs=curr_obs, previous_obs=prev_obs)
    assert deltas.sales_delta == 10
    assert deltas.sales_pct_change is None  # Avoid divide-by-zero
    assert deltas.review_delta == 5
    assert deltas.review_pct_change is None
    assert deltas.price_delta == 25.0
