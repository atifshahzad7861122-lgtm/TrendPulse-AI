import pytest
from backend.app.domain.scoring import TrendScoringEngine
from backend.app.domain.demand import DemandSignalEngine
from backend.app.domain.viral import ViralPotentialEngine
from backend.app.domain.aggregation import AggregationEngine
from backend.app.connectors.mock_connectors import (
    MockTikTokConnector, MockDarazConnector, MockInstagramConnector,
    MockYouTubeConnector, MockFacebookConnector
)
from backend.app.models.domain import Product

def test_trend_scoring_growth_rate():
    # Test normal growth
    assert TrendScoringEngine.calculate_growth_rate(200.0, 100.0) == 100.0
    assert TrendScoringEngine.calculate_growth_rate(450.0, 100.0) == 350.0
    # Test zero baseline
    assert TrendScoringEngine.calculate_growth_rate(100.0, 0.0) == 100.0
    assert TrendScoringEngine.calculate_growth_rate(0.0, 0.0) == 0.0

def test_trend_scoring_velocity():
    hist = [10000.0, 25000.0, 45000.0]
    vel = TrendScoringEngine.calculate_velocity(hist, days_delta=7.0)
    assert vel == round((45000.0 - 10000.0) / 7.0, 2)

def test_trend_scoring_composite_score():
    score = TrendScoringEngine.calculate_trend_score(
        growth_rate=340.0,
        volume=184000,
        sentiment_score=0.92,
        platform_count=3,
        historical_trend=[68.0, 74.0, 94.0]
    )
    assert 80.0 <= score <= 100.0

def test_velocity_labels():
    assert TrendScoringEngine.get_velocity_label(96.0, 320.0) == "Explosive"
    assert TrendScoringEngine.get_velocity_label(91.0, 190.0) == "Breakout"
    assert TrendScoringEngine.get_velocity_label(82.0, 90.0) == "Surging"
    assert TrendScoringEngine.get_velocity_label(50.0, 20.0) == "Steady"

def test_demand_signal_engine():
    label_high, index_high = DemandSignalEngine.evaluate_demand(
        volume=200000,
        sentiment_score=0.95,
        growth_rate=300.0
    )
    assert label_high == "Very Strong"
    assert index_high >= 85.0

    label_low, index_low = DemandSignalEngine.evaluate_demand(
        volume=5000,
        sentiment_score=0.4,
        growth_rate=10.0
    )
    assert label_low in ["Low", "Moderate"]
    assert index_low < 70.0

def test_viral_potential_engine():
    pot_very_high = ViralPotentialEngine.calculate_viral_potential(
        growth_rate=280.0,
        platforms=["TikTok", "Instagram", "Daraz"],
        platform_shares={"TikTok": 55.0, "Instagram": 30.0},
        velocity_label="Explosive"
    )
    assert pot_very_high in ["Very High", "High"]

    pot_low = ViralPotentialEngine.calculate_viral_potential(
        growth_rate=15.0,
        platforms=["Facebook"],
        platform_shares={"Facebook": 100.0},
        velocity_label="Steady"
    )
    assert pot_low == "Low"

def test_aggregation_category_metrics():
    prods = [
        Product(
            id="p1",
            name="Serum",
            category="Beauty & Personal Care",
            trend_score=95.0,
            growth_rate=300.0,
            volume=100000,
            velocity_label="Explosive",
            price_range="$20",
            primary_platform="TikTok",
            platforms=["TikTok", "Instagram"],
            ai_summary="Viral",
            signals_count=500,
            sentiment_score=0.9
        ),
        Product(
            id="p2",
            name="Cream",
            category="Beauty & Personal Care",
            trend_score=85.0,
            growth_rate=150.0,
            volume=50000,
            velocity_label="Breakout",
            price_range="$30",
            primary_platform="Instagram",
            platforms=["Instagram", "Daraz"],
            ai_summary="Steady",
            signals_count=300,
            sentiment_score=0.85
        )
    ]
    cat = AggregationEngine.aggregate_category_metrics(
        category_name="Beauty & Personal Care",
        category_slug="beauty-personal-care",
        category_desc="Beauty products",
        products=prods
    )
    assert cat.product_count == 2
    assert cat.avg_trend_score == 90.0
    assert cat.growth_rate == 225.0
    assert "Instagram" in cat.top_platforms

def test_mock_connectors():
    connectors = [
        MockTikTokConnector(),
        MockDarazConnector(),
        MockInstagramConnector(),
        MockYouTubeConnector(),
        MockFacebookConnector()
    ]
    for conn in connectors:
        assert conn.test_connection() is True
        signals = conn.fetch_signals(limit=10)
        assert len(signals) > 0
        assert signals[0].platform == conn.platform_name
