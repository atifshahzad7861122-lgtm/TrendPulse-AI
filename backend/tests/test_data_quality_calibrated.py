import pytest
from datetime import datetime, timezone
from backend.app.domain.signals import PlatformSignal
from backend.app.domain.data_quality import DataQualityService

def test_data_quality_high_confidence_signal():
    signal = PlatformSignal(
        id="sig_test_01",
        platform="YouTube",
        product_id="prod_01",
        product_name="HydroGlow Thermal Lip Serum in-depth review",
        category="Beauty & Personal Care",
        timestamp=datetime.now(timezone.utc),
        volume=50000,
        engagement_rate=0.08,
        shares_count=2000,
        views_count=50000,
        likes_count=3500,
        comments_count=450,
        sentiment_score=0.92,
        mode="live"
    )

    is_valid, quality_score, reasons, warnings = DataQualityService.evaluate_quality(signal)
    assert is_valid is True
    assert quality_score >= 90.0
    assert len(reasons) == 0
    assert signal.like_rate == round(3500 / 50000, 4)
    assert signal.comment_rate == round(450 / 50000, 4)

def test_data_quality_penalizes_spam():
    signal = PlatformSignal(
        id="sig_test_02",
        platform="YouTube",
        product_id="prod_01",
        product_name="FREE MONEY CRYPTO GIVEAWAY CLICK HERE NOW",
        category="General",
        timestamp=datetime.now(timezone.utc),
        volume=10000,
        engagement_rate=0.05,
        views_count=10000,
        likes_count=100,
        comments_count=10,
        mode="mock"
    )

    is_valid, quality_score, reasons, warnings = DataQualityService.evaluate_quality(signal)
    assert "SPAM_PATTERN_DETECTED" in signal.quality_flags
    assert quality_score < 80.0

def test_data_quality_rejects_negative_metrics():
    signal = PlatformSignal(
        id="sig_test_03",
        platform="YouTube",
        product_id="prod_01",
        product_name="Valid Name",
        category="General",
        timestamp=datetime.now(timezone.utc),
        volume=-500,
        engagement_rate=0.05,
        views_count=-500,
        likes_count=-10,
        comments_count=-2
    )

    is_valid, quality_score, reasons, warnings = DataQualityService.evaluate_quality(signal)
    assert is_valid is False
    assert len(reasons) >= 2
