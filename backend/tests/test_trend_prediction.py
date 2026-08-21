from backend.app.domain.prediction import TrendPredictionService
from backend.app.models.domain import Product

def test_trend_prediction_rising():
    prod = Product(
        id="prod_rising",
        name="Surging Item",
        category="Beauty & Personal Care",
        trend_score=92.0,
        growth_rate=320.0,
        volume=200000,
        velocity_label="Explosive",
        price_range="$25",
        primary_platform="TikTok",
        platforms=["TikTok"],
        ai_summary="",
        signals_count=50,
        sentiment_score=0.9,
        historical_scores=[
            {"date": "2026-05-01", "score": 75.0, "volume": 100000},
            {"date": "2026-05-08", "score": 84.0, "volume": 150000},
            {"date": "2026-05-15", "score": 92.0, "volume": 200000}
        ]
    )
    pred = TrendPredictionService.predict_product_trajectory(prod)
    assert pred.direction == "rising"
    assert pred.confidence >= 70
    assert pred.predicted_score_7d >= prod.trend_score
    assert pred.predicted_score_30d >= pred.predicted_score_7d
    assert pred.horizon_days == 30

def test_trend_prediction_declining():
    prod = Product(
        id="prod_declining",
        name="Fading Item",
        category="Fashion",
        trend_score=55.0,
        growth_rate=-20.0,
        volume=40000,
        velocity_label="Fading",
        price_range="$30",
        primary_platform="Instagram",
        platforms=["Instagram"],
        ai_summary="",
        signals_count=10,
        sentiment_score=0.4,
        historical_scores=[
            {"date": "2026-05-01", "score": 75.0, "volume": 80000},
            {"date": "2026-05-08", "score": 65.0, "volume": 60000},
            {"date": "2026-05-15", "score": 55.0, "volume": 40000}
        ]
    )
    pred = TrendPredictionService.predict_product_trajectory(prod)
    assert pred.direction == "declining"
    assert pred.predicted_score_7d <= prod.trend_score
    assert pred.predicted_score_30d <= pred.predicted_score_7d
