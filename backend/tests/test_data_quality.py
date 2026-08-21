from datetime import datetime, timezone
from backend.app.domain.data_quality import DataQualityService
from backend.app.domain.signals import PlatformSignal

def test_data_quality_valid_signal():
    signal = PlatformSignal(
        id="sig_test_01",
        platform="YouTube",
        product_id="prod_01",
        product_name="HydroGlow Thermal Lip Serum Review",
        category="Beauty & Personal Care",
        timestamp=datetime.now(timezone.utc),
        volume=120000,
        engagement_rate=0.08,
        shares_count=5000,
        views_count=120000,
        likes_count=8000,
        comments_count=1600,
        sentiment_score=0.9
    )
    is_valid, reasons, warnings = DataQualityService.validate_signal(signal)
    assert is_valid is True
    assert len(reasons) == 0

def test_data_quality_negative_counters_rejected():
    signal = PlatformSignal(
        id="sig_test_02",
        platform="YouTube",
        product_id="prod_01",
        product_name="Invalid Negative Metrics",
        category="Beauty",
        timestamp=datetime.now(timezone.utc),
        volume=-500,
        engagement_rate=0.05,
        shares_count=0,
        views_count=-500,
        likes_count=-10,
        comments_count=0,
        sentiment_score=0.5
    )
    is_valid, reasons, warnings = DataQualityService.validate_signal(signal)
    assert is_valid is False
    assert any("negative" in r.lower() for r in reasons)

def test_data_quality_engagement_clamping():
    signal = PlatformSignal(
        id="sig_test_03",
        platform="YouTube",
        product_id="prod_01",
        product_name="High Engagement Video",
        category="Beauty",
        timestamp=datetime.now(timezone.utc),
        volume=1000,
        engagement_rate=1.8,  # > 1.0
        shares_count=100,
        views_count=1000,
        likes_count=800,
        comments_count=1000,
        sentiment_score=1.5   # > 1.0
    )
    is_valid, reasons, warnings = DataQualityService.validate_signal(signal)
    assert is_valid is True
    assert signal.engagement_rate == 1.0
    assert signal.sentiment_score == 1.0
    assert len(warnings) >= 2
