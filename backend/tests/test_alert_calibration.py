import pytest
from backend.app.models.domain import Product
from backend.app.services.alert_service import AlertService
from backend.app.repositories.in_memory import InMemoryAlertRepository, InMemoryProductRepository

def test_alert_calibration_critical_surge():
    alert_repo = InMemoryAlertRepository()
    prod_repo = InMemoryProductRepository()
    service = AlertService(alert_repo, prod_repo)

    prod = Product(
        id="prod_surge",
        name="Surge Product",
        category="Beauty & Personal Care",
        trend_score=96.0,
        growth_rate=340.0,
        volume=180000,
        velocity_label="Explosive",
        price_range="$25",
        primary_platform="TikTok",
        platforms=["TikTok"],
        ai_summary="",
        signals_count=100,
        sentiment_score=0.92,
        tags=["Viral"]
    )

    alert = service.evaluate_product_signals(prod)
    assert alert is not None
    assert alert.severity == "Critical"
    assert alert.trigger == "growth_velocity_surge"
    assert alert.threshold == 300.0
    assert alert.actual_value == 340.0

def test_alert_calibration_warning():
    alert_repo = InMemoryAlertRepository()
    prod_repo = InMemoryProductRepository()
    service = AlertService(alert_repo, prod_repo)

    prod = Product(
        id="prod_warn",
        name="Warning Product",
        category="Sports & Outdoor",
        trend_score=91.0,
        growth_rate=210.0,
        volume=120000,
        velocity_label="Breakout",
        price_range="$40",
        primary_platform="YouTube",
        platforms=["YouTube"],
        ai_summary="",
        signals_count=60,
        sentiment_score=0.88,
        tags=["Fitness"]
    )

    alert = service.evaluate_product_signals(prod)
    assert alert is not None
    assert alert.severity == "Warning"
    assert alert.trigger == "trend_breakout_warning"
