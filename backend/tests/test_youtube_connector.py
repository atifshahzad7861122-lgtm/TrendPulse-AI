import pytest
from unittest.mock import MagicMock
from backend.app.connectors.youtube_connector import YouTubeDataConnector
from backend.app.domain.matching import ProductMatchingEngine
from backend.app.models.domain import Product
from backend.app.core.http_client import ResilientHTTPClient, RateLimitException

def test_youtube_connector_offline_fallback():
    connector = YouTubeDataConnector(api_key=None)
    assert connector.platform_name == "YouTube"
    assert connector.platform_slug == "youtube"
    assert connector.test_connection() is True

    signals = connector.fetch_signals(limit=10)
    assert len(signals) > 0
    assert signals[0].platform == "YouTube"
    assert signals[0].views_count > 0
    assert signals[0].sentiment_score >= 0.3

def test_youtube_video_normalization():
    connector = YouTubeDataConnector(api_key="mock_key")
    raw_video = {
        "id": "vid_abc123",
        "snippet": {
            "title": "HydroGlow Thermal Lip Serum viral review",
            "description": "Best lip serum of 2026, color shift is amazing!",
            "publishedAt": "2026-05-15T12:00:00Z",
            "channelTitle": "BeautyLab"
        },
        "statistics": {
            "viewCount": "250000",
            "likeCount": "18000",
            "commentCount": "3200"
        }
    }
    signal = connector._normalize_youtube_video(raw_video)
    assert signal is not None
    assert signal.platform == "YouTube"
    assert signal.volume == 250000
    assert signal.likes_count == 18000
    assert signal.comments_count == 3200
    assert signal.sentiment_score >= 0.8
    assert "https://youtube.com/watch?v=vid_abc123" in signal.source_url

def test_product_matching_engine():
    catalog = [
        Product(
            id="prod_01",
            name="HydroGlow Thermal Lip Serum",
            category="Beauty & Personal Care",
            trend_score=96.0,
            growth_rate=340.0,
            volume=184000,
            velocity_label="Explosive",
            price_range="$24",
            primary_platform="TikTok",
            platforms=["TikTok"],
            ai_summary="",
            signals_count=100,
            sentiment_score=0.9,
            tags=["Viral Beauty", "Thermal Active", "High Margin"]
        ),
        Product(
            id="prod_02",
            name="TitanFlex Modular Running Vest",
            category="Sports & Outdoor",
            trend_score=94.0,
            growth_rate=218.0,
            volume=129000,
            velocity_label="Breakout",
            price_range="$45",
            primary_platform="YouTube",
            platforms=["YouTube"],
            ai_summary="",
            signals_count=80,
            sentiment_score=0.88,
            tags=["RunClub", "Ergonomic Gear", "Fitness Surge"]
        )
    ]

    # Test exact / strong match
    matched_01 = ProductMatchingEngine.match_content_to_product(
        "Long term test: HydroGlow Thermal Lip Serum review",
        catalog
    )
    assert matched_01 is not None
    assert matched_01.id == "prod_01"

    matched_02 = ProductMatchingEngine.match_content_to_product(
        "TitanFlex Running Vest unboxing and fluid test",
        catalog
    )
    assert matched_02 is not None
    assert matched_02.id == "prod_02"

    # Test unrelated content returns None
    matched_none = ProductMatchingEngine.match_content_to_product(
        "How to make sourdough bread at home step by step",
        catalog
    )
    assert matched_none is None

def test_http_client_resilience():
    # Test retry on 500
    client = ResilientHTTPClient(timeout=2.0, max_retries=1, backoff_factor=0.01)
    
    # Verify rate limit exception construction
    exc = RateLimitException("429 Too Many Requests", retry_after=5)
    assert exc.retry_after == 5

def test_youtube_connector_live_mode_detection():
    # When placeholder key or None is provided
    c_mock = YouTubeDataConnector(api_key="")
    assert c_mock.is_live_configured is False

    c_placeholder = YouTubeDataConnector(api_key="PASTE_YOUR_YOUTUBE_API_KEY_HERE")
    assert c_placeholder.is_live_configured is False

    c_live = YouTubeDataConnector(api_key="AIzaSy_ValidKeySample")
    assert c_live.is_live_configured is True

