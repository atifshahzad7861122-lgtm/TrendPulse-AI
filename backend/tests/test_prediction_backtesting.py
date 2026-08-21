import pytest
from backend.app.models.domain import Product
from backend.app.domain.prediction import TrendPredictionService
from backend.app.domain.backtesting import PredictionBacktester

def test_prediction_insufficient_history_safeguard():
    # Product with only 1 observation point
    prod_sparse = Product(
        id="prod_sparse",
        name="Sparse History Product",
        category="Consumer Electronics",
        trend_score=75.0,
        growth_rate=45.0,
        volume=12000,
        velocity_label="Steady",
        price_range="$20",
        primary_platform="YouTube",
        platforms=["YouTube"],
        ai_summary="",
        signals_count=10,
        sentiment_score=0.8,
        tags=["Tech"],
        historical_scores=[{"date": "2026-05-01", "score": 75.0, "volume": 12000}]
    )

    pred = TrendPredictionService.predict_product_trajectory(prod_sparse)
    assert pred.prediction_status == "insufficient_history"
    assert pred.confidence == 0
    assert pred.predicted_score_7d is None
    assert pred.predicted_score_30d is None

def test_prediction_sufficient_history_forecast():
    prod_rich = Product(
        id="prod_rich",
        name="Rich History Product",
        category="Beauty & Personal Care",
        trend_score=94.0,
        growth_rate=280.0,
        volume=150000,
        velocity_label="Explosive",
        price_range="$30",
        primary_platform="TikTok",
        platforms=["TikTok", "YouTube"],
        ai_summary="",
        signals_count=80,
        sentiment_score=0.92,
        tags=["Beauty"],
        historical_scores=[
            {"date": "2026-04-01", "score": 60.0, "volume": 50000},
            {"date": "2026-04-15", "score": 75.0, "volume": 90000},
            {"date": "2026-05-01", "score": 94.0, "volume": 150000}
        ]
    )

    pred = TrendPredictionService.predict_product_trajectory(prod_rich)
    assert pred.prediction_status == "ready"
    assert pred.confidence >= 65
    assert pred.predicted_score_7d is not None
    assert pred.direction == "rising"

def test_prediction_backtester_evaluation():
    prod_rich = Product(
        id="prod_rich",
        name="Rich History Product",
        category="Beauty & Personal Care",
        trend_score=94.0,
        growth_rate=280.0,
        volume=150000,
        velocity_label="Explosive",
        price_range="$30",
        primary_platform="TikTok",
        platforms=["TikTok", "YouTube"],
        ai_summary="",
        signals_count=80,
        sentiment_score=0.92,
        tags=["Beauty"],
        historical_scores=[
            {"date": "2026-03-01", "score": 45.0, "volume": 30000},
            {"date": "2026-03-15", "score": 60.0, "volume": 50000},
            {"date": "2026-04-01", "score": 75.0, "volume": 90000},
            {"date": "2026-04-15", "score": 88.0, "volume": 120000},
            {"date": "2026-05-01", "score": 94.0, "volume": 150000}
        ]
    )

    report = PredictionBacktester.run_catalog_backtest([prod_rich])
    assert report.status == "evaluated"
    assert report.sample_count >= 2
    assert report.mae_7d >= 0.0
    assert report.directional_accuracy_7d >= 50.0
