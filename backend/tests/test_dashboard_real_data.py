import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.deps import get_daraz_service
from backend.app.schemas.daraz import DarazProductItem, DarazSearchResponse
from backend.app.schemas.entities import DashboardSummaryResponse
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.live_signal_service import LiveSignalService
from backend.app.repositories.in_memory import product_repo, alert_repo, platform_repo

def _sample_products():
    return [
        DarazProductItem(
            product_id="932042187",
            name="Zero® Evo Wireless Earbuds | 10mm Base Driver",
            price=2999.0,
            original_price=14999.0,
            discount=79.0,
            discount_label="-79%",
            rating=4.8,
            review_count=1122,
            seller_name="Zero Lifestyle",
            in_stock=True,
            location="Punjab",
            image_url="https://img.drz.lazcdn.com/static/pk/p/zero-evo.jpg",
            product_url="https://www.daraz.pk/products/zero-evo-i932042187.html",
            category="Consumer Electronics",
            source="daraz.pk"
        ),
        DarazProductItem(
            product_id="1964603364",
            name="Dell Core i7 12th Gen Laptop 16GB RAM",
            price=85000.0,
            original_price=110000.0,
            discount=22.7,
            discount_label="-23%",
            rating=4.6,
            review_count=84,
            seller_name="TechMart Official",
            in_stock=True,
            location="Sindh",
            image_url="https://img.drz.lazcdn.com/static/pk/p/dell-i7.jpg",
            product_url="https://www.daraz.pk/products/dell-i7-i1964603364.html",
            category="Laptops",
            source="daraz.pk"
        ),
        DarazProductItem(
            product_id="516331392",
            name="Mechanical Gaming Keyboard RGB Backlit",
            price=4500.0,
            original_price=6000.0,
            discount=25.0,
            discount_label="-25%",
            rating=4.4,
            review_count=210,
            seller_name="Gaming Gear PK",
            in_stock=False,
            location="Islamabad",
            image_url="https://img.drz.lazcdn.com/static/pk/p/keyboard.jpg",
            product_url="https://www.daraz.pk/products/keyboard-i516331392.html",
            category="Consumer Electronics",
            source="daraz.pk"
        )
    ]

def test_dashboard_service_with_real_daraz_products():
    mock_daraz = MagicMock()
    mock_daraz._cache = {}
    mock_daraz._cache_lock = MagicMock()
    mock_daraz._cache_lock.__enter__ = MagicMock()
    mock_daraz._cache_lock.__exit__ = MagicMock()

    products = _sample_products()

    mock_daraz.search_products.return_value = DarazSearchResponse(
        query="wireless earbuds",
        page=1,
        total_products=3,
        has_next=False,
        source="daraz.pk",
        products=products
    )

    live_signals = LiveSignalService(daraz_service=mock_daraz)
    service = DashboardService(
        product_repo=product_repo,
        alert_repo=alert_repo,
        platform_repo=platform_repo,
        daraz_service=mock_daraz,
        live_signal_service=live_signals
    )

    summary = service.get_summary(time_range="30d", category="all")

    assert summary.total_trends_monitored == 3
    assert summary.system_status == "Live Daraz Pakistan Feed Active"

    # Verify Metric Cards
    metrics_map = {m.title: m for m in summary.metrics}
    
    # 1. Live Products Monitored
    assert "Live Products Monitored" in metrics_map
    assert metrics_map["Live Products Monitored"].value == "3"
    assert metrics_map["Live Products Monitored"].change == "Daraz Pakistan"

    # 2. Average Market Price: (2999 + 85000 + 4500) / 3 = 30833
    assert "Average Market Price" in metrics_map
    assert "PKR 30,833" in metrics_map["Average Market Price"].value
    assert "PKR 2,999 - 85,000" in metrics_map["Average Market Price"].change

    # 3. Average Buyer Rating: (4.8 + 4.6 + 4.4) / 3 = 4.6
    assert "Average Buyer Rating" in metrics_map
    assert "4.6★" in metrics_map["Average Buyer Rating"].value

    # 4. Inventory In-Stock Rate: 2 / 3 = 67%
    assert "Inventory In-Stock Rate" in metrics_map
    assert "67%" in metrics_map["Inventory In-Stock Rate"].value
    assert "2/3 In Stock" in metrics_map["Inventory In-Stock Rate"].change

    # Verify Top Surging Products
    assert len(summary.top_surging) == 3
    top_p = summary.top_surging[0]
    assert top_p["id"] == "daraz_932042187"
    assert top_p["product_id"] == "932042187"
    assert "Zero" in top_p["name"]
    assert top_p["price"] == 2999.0
    assert "PKR 2,999" in top_p["price_formatted"]
    assert top_p["original_price_formatted"] == "PKR 14,999"
    assert top_p["discount_label"] == "-79%"
    assert top_p["seller_name"] == "Zero Lifestyle"
    assert top_p["rating"] == 4.8
    assert top_p["review_count"] == 1122
    assert top_p["in_stock"] is True
    assert top_p["platform"] == "Daraz Pakistan"

    # Verify Live Signals
    assert len(summary.live_signals) > 0
    first_sig = summary.live_signals[0]
    assert first_sig.platform == "Daraz"
    assert "Zero" in first_sig.text or "Earbuds" in first_sig.text
    assert first_sig.product_id is not None

def test_dashboard_service_empty_or_unavailable_state():
    mock_daraz = MagicMock()
    mock_daraz._cache = {}
    mock_daraz._cache_lock = MagicMock()
    mock_daraz._cache_lock.__enter__ = MagicMock()
    mock_daraz._cache_lock.__exit__ = MagicMock()
    mock_daraz.search_products.return_value = DarazSearchResponse(
        query="empty",
        page=1,
        total_products=0,
        has_next=False,
        source="daraz.pk",
        products=[]
    )

    service = DashboardService(
        product_repo=product_repo,
        alert_repo=alert_repo,
        platform_repo=platform_repo,
        daraz_service=mock_daraz,
        live_signal_service=None
    )

    summary = service.get_summary(time_range="30d", category="all")
    assert summary.total_trends_monitored == 0
    assert summary.top_surging == []
    assert summary.live_signals == []
    assert "Waiting" in summary.system_status

    trends = service.get_trends(time_range="30d")
    assert trends == []

def test_dashboard_endpoint_with_auth():
    mock_daraz = MagicMock()
    mock_daraz._cache = {}
    mock_daraz._cache_lock = MagicMock()
    mock_daraz._cache_lock.__enter__ = MagicMock()
    mock_daraz._cache_lock.__exit__ = MagicMock()
    mock_daraz.search_products.return_value = DarazSearchResponse(
        query="wireless earbuds",
        page=1,
        total_products=3,
        has_next=False,
        source="daraz.pk",
        products=_sample_products()
    )

    app.dependency_overrides[get_daraz_service] = lambda: mock_daraz
    try:
        client = TestClient(app)

        # 1. Login to obtain JWT
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "demo@trendpulse.ai",
            "password": "Password123!",
            "remember_me": True
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Dashboard Summary
        summary_resp = client.get("/api/v1/dashboard/summary", headers=headers)
        assert summary_resp.status_code == 200
        s_data = summary_resp.json()
        assert s_data["success"] is True
        assert "metrics" in s_data["data"]
        assert "live_signals" in s_data["data"]
        assert "top_surging" in s_data["data"]
        assert len(s_data["data"]["top_surging"]) == 3
        assert s_data["data"]["top_surging"][0]["platform"] == "Daraz Pakistan"

        # 3. Get Dashboard Trends
        trends_resp = client.get("/api/v1/dashboard/trends", headers=headers)
        assert trends_resp.status_code == 200
        t_data = trends_resp.json()
        assert t_data["success"] is True
        assert isinstance(t_data["data"], list)
        assert len(t_data["data"]) > 0
    finally:
        app.dependency_overrides.pop(get_daraz_service, None)
