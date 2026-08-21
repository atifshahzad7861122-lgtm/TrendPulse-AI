import pytest
from backend.app.domain.scoring import TrendScoringEngine

def test_explainable_trend_score_components():
    detail = TrendScoringEngine.calculate_explainable_trend_score(
        growth_rate=320.0,
        volume=185000,
        sentiment_score=0.94,
        platform_count=3,
        engagement_rate=0.09,
        historical_trend=[60.0, 75.0, 92.0]
    )

    assert detail.trend_score >= 85.0
    assert detail.growth_component > 0
    assert detail.volume_component > 0
    assert detail.engagement_component > 0
    assert detail.dispersion_component > 0
    assert len(detail.top_contributors) > 0
    assert detail.velocity_label == "Explosive"
    assert detail.scoring_version == "2.4.0"

def test_trend_score_deterministic_consistency():
    d1 = TrendScoringEngine.calculate_explainable_trend_score(150.0, 80000, 0.88, 2)
    d2 = TrendScoringEngine.calculate_explainable_trend_score(150.0, 80000, 0.88, 2)
    assert d1.trend_score == d2.trend_score
    assert d1.growth_component == d2.growth_component
    assert d1.top_contributors == d2.top_contributors
