import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from backend.app.main import app
from backend.app.schemas.daraz import DarazProductItem, DarazSearchResponse
from backend.app.schemas.signals import LiveSignalsResponse, LiveSignalItem
from backend.app.services.live_signal_service import LiveSignalService
from backend.app.api.deps import get_live_signal_service

def test_generate_signals_from_daraz_product():
    service = LiveSignalService()
    product = DarazProductItem(
        product_id="265958567",
        name="Petiwala Pack of 10 Jet Black Retractable Ball Point Pen (Blue)",
        price=250.0,
        original_price=250.0,
        discount=0.0,
        discount_label="",
        currency="PKR",
        rating=4.9,
        review_count=11,
        in_stock=True,
        seller_name="Petiwala Stationary Mart",
        seller_id="12345",
        location="Pakistan",
        product_url="https://daraz.pk/products/petiwala-pen"
    )

    signals = service.generate_signals_from_daraz_product(product)
    assert len(signals) >= 3

    types = [s.type for s in signals]
    assert "PRICE" in types
    assert "RATING" in types
    assert "SELLER" in types
    assert "AVAILABILITY" in types

    price_sig = next(s for s in signals if s.type == "PRICE")
    assert price_sig.platform == "daraz"
    assert price_sig.product_id == "daraz_265958567"
    assert "PKR 250" in price_sig.description
    assert price_sig.source == "daraz.pk"
    assert price_sig.timestamp is not None

    rating_sig = next(s for s in signals if s.type == "RATING")
    assert "4.9★" in rating_sig.description
    assert "11 reviews" in rating_sig.description

    seller_sig = next(s for s in signals if s.type == "SELLER")
    assert "Petiwala Stationary Mart" in seller_sig.description

def test_live_signals_sparse_product_handling():
    service = LiveSignalService()
    product = DarazProductItem(
        product_id="99999",
        name="Minimal Generic Item",
        price=0.0,
        currency="PKR",
        rating=0.0,
        review_count=0,
        in_stock=False,
        seller_name=None,
        product_url=""
    )

    signals = service.generate_signals_from_daraz_product(product)
    assert len(signals) == 0

def test_live_signals_empty_response():
    mock_daraz = MagicMock()
    mock_daraz.search_products.return_value = DarazSearchResponse(
        query="laptop",
        page=1,
        total_products=0,
        has_next=False,
        source="daraz.pk",
        products=[]
    )

    service = LiveSignalService(daraz_service=mock_daraz, cache_ttl_seconds=60)
    response = service.get_live_signals(limit=10)

    assert response.total == 0
    assert len(response.signals) == 0

def test_live_signals_api_failure_handling():
    mock_daraz = MagicMock()
    mock_daraz.search_products.side_effect = Exception("Parse API connection error")

    service = LiveSignalService(daraz_service=mock_daraz, cache_ttl_seconds=60)
    response = service.get_live_signals(limit=10)

    assert response.total == 0
    assert isinstance(response.signals, list)

def test_live_signals_caching():
    mock_daraz = MagicMock()
    mock_daraz.search_products.return_value = DarazSearchResponse(
        query="wireless earbuds",
        page=1,
        total_products=1,
        has_next=False,
        source="daraz.pk",
        products=[
            DarazProductItem(
                product_id="932042187",
                name="Zero Evo Wireless Earbuds",
                price=2999.0,
                rating=4.8,
                review_count=1122,
                in_stock=True,
                seller_name="Zero Lifestyle"
            )
        ]
    )

    service = LiveSignalService(daraz_service=mock_daraz, cache_ttl_seconds=120)
    res1 = service.get_live_signals(limit=10)
    res2 = service.get_live_signals(limit=10)

    assert res1.total == res2.total
    # Exactly 2 calls for the 2 discovery queries, 0 additional calls on the cached second invocation
    assert mock_daraz.search_products.call_count == 2

def test_live_signals_endpoint_with_mock():
    mock_service = MagicMock()
    mock_service.get_live_signals.return_value = LiveSignalsResponse(
        signals=[
            LiveSignalItem(
                id="sig_test_1",
                type="PRICE",
                platform="daraz",
                title="PRICE UPDATE",
                description="Zero Evo Wireless Earbuds • PKR 2,999",
                product_id="daraz_932042187",
                product_name="Zero Evo Wireless Earbuds",
                signal_value="PKR 2,999",
                timestamp="2026-08-23T12:00:00Z",
                source="daraz.pk"
            )
        ],
        total=1,
        generated_at="2026-08-23T12:00:00Z"
    )

    app.dependency_overrides[get_live_signal_service] = lambda: mock_service
    client = TestClient(app)

    try:
        response = client.get("/api/v1/signals/live?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert len(data["data"]["signals"]) == 1
        sig = data["data"]["signals"][0]
        assert sig["type"] == "PRICE"
        assert sig["platform"] == "daraz"
        assert sig["product_id"] == "daraz_932042187"
        assert "PKR 2,999" in sig["description"]
    finally:
        app.dependency_overrides.clear()
