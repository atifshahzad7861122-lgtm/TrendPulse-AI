import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest

from backend.app.models.domain import MarketplaceProduct, ProductMarketSnapshot
from backend.app.repositories.in_memory import InMemoryMarketplaceProductRepository
from backend.app.schemas.daraz import DarazProductItem, DarazSearchResponse
from backend.app.services.daraz_service import (
    DarazService, DarazRateLimitError, DarazUpstreamError
)
from backend.app.services.dashboard_service import DashboardService
from backend.app.repositories.in_memory import (
    product_repo, alert_repo, platform_repo
)


@pytest.fixture
def temp_repo():
    """Provides a fresh, isolated InMemoryMarketplaceProductRepository with a temporary backing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "test_marketplace_store.json")
        repo = InMemoryMarketplaceProductRepository(storage_file=store_path)
        yield repo


def test_insert_new_marketplace_product(temp_repo):
    now = datetime.now(timezone.utc)
    product = MarketplaceProduct(
        id="daraz_1001",
        platform="daraz",
        product_id="1001",
        product_name="Lenovo ThinkPad Wireless Mouse",
        product_url="https://www.daraz.pk/products/lenovo-mouse-i1001.html",
        image_url="https://static-01.daraz.pk/p/mouse.jpg",
        seller_name="Official Lenovo Store",
        seller_id="seller_lenovo_01",
        category="Computers & Laptops",
        price=1850.0,
        original_price=2500.0,
        discount_percentage=26.0,
        discount_label="-26%",
        rating=4.8,
        review_count=142,
        stock_status="in_stock",
        in_stock=True,
        currency="PKR",
        location="Pakistan",
        first_seen_at=now,
        last_seen_at=now,
        last_synced_at=now,
        raw_source_data={"raw_id": "1001"}
    )

    saved = temp_repo.upsert_product(product)
    assert saved.product_id == "1001"
    assert saved.platform == "daraz"
    assert saved.price == 1850.0

    retrieved = temp_repo.get_product("daraz", "1001")
    assert retrieved is not None
    assert retrieved.product_name == "Lenovo ThinkPad Wireless Mouse"
    assert retrieved.seller_name == "Official Lenovo Store"


def test_upsert_preserves_first_seen_and_updates_price_rating(temp_repo):
    original_time = datetime.now(timezone.utc) - timedelta(days=5)
    product_v1 = MarketplaceProduct(
        id="daraz_2002",
        platform="daraz",
        product_id="2002",
        product_name="Audionic Airbud 550 TWS",
        product_url="https://www.daraz.pk/products/airbud-i2002.html",
        image_url="https://static-01.daraz.pk/p/airbud.jpg",
        seller_name="Audionic Pakistan",
        category="Wireless Earbuds",
        price=3500.0,
        original_price=5000.0,
        discount_percentage=30.0,
        rating=4.5,
        review_count=89,
        stock_status="in_stock",
        first_seen_at=original_time,
        last_seen_at=original_time,
        last_synced_at=original_time
    )
    temp_repo.upsert_product(product_v1)

    # Simulate subsequent sync with price drop and new reviews
    sync_time = datetime.now(timezone.utc)
    product_v2 = MarketplaceProduct(
        id="daraz_2002",
        platform="daraz",
        product_id="2002",
        product_name="Audionic Airbud 550 TWS",
        product_url="https://www.daraz.pk/products/airbud-i2002.html",
        image_url="https://static-01.daraz.pk/p/airbud.jpg",
        seller_name="Audionic Pakistan",
        category="Wireless Earbuds",
        price=2999.0,  # Price drop
        original_price=5000.0,
        discount_percentage=40.0,
        rating=4.7,  # Improved rating
        review_count=120,  # More reviews
        stock_status="in_stock",
        first_seen_at=sync_time,  # Should be ignored and preserved
        last_seen_at=sync_time,
        last_synced_at=sync_time
    )
    updated = temp_repo.upsert_product(product_v2)

    assert updated.price == 2999.0
    assert updated.rating == 4.7
    assert updated.review_count == 120
    # first_seen_at MUST be preserved from original_time
    assert updated.first_seen_at == original_time
    assert updated.last_seen_at == sync_time


def test_duplicate_prevention_on_platform_and_product_id(temp_repo):
    now = datetime.now(timezone.utc)
    p1 = MarketplaceProduct(
        id="daraz_3003",
        platform="daraz",
        product_id="3003",
        product_name="M10 TWS Wireless Earbuds",
        product_url="https://www.daraz.pk/products/m10-i3003.html",
        price=850.0,
        first_seen_at=now
    )
    p2 = MarketplaceProduct(
        id="daraz_3003",
        platform="daraz",
        product_id="3003",
        product_name="M10 TWS Wireless Earbuds Gaming Edition",
        product_url="https://www.daraz.pk/products/m10-i3003.html",
        price=820.0,
        first_seen_at=now
    )

    temp_repo.batch_upsert_products([p1, p2])
    all_products = temp_repo.list_products(platform="daraz")
    assert len(all_products) == 1
    assert all_products[0].product_id == "3003"
    assert all_products[0].price == 820.0


def test_market_snapshot_recording(temp_repo):
    t1 = datetime.now(timezone.utc) - timedelta(hours=2)
    t2 = datetime.now(timezone.utc)

    s1 = ProductMarketSnapshot(
        id="snap_1",
        product_id="4004",
        platform="daraz",
        price=4500.0,
        original_price=6000.0,
        discount=25.0,
        rating=4.2,
        review_count=10,
        stock_status="in_stock",
        observed_at=t1
    )
    s2 = ProductMarketSnapshot(
        id="snap_2",
        product_id="4004",
        platform="daraz",
        price=3999.0,
        original_price=6000.0,
        discount=33.3,
        rating=4.4,
        review_count=15,
        stock_status="in_stock",
        observed_at=t2
    )

    temp_repo.create_snapshot(s1)
    temp_repo.create_snapshot(s2)

    history = temp_repo.get_snapshots("daraz", "4004")
    assert len(history) == 2
    # Returned in descending chronological order (newest observed first)
    assert history[0].price == 3999.0
    assert history[1].price == 4500.0


def test_daraz_service_auto_persistence_on_search(temp_repo):
    service = DarazService(api_key="pmx_test_key", marketplace_repo=temp_repo)

    mock_raw_response = {
        "data": {
            "products": [
                {
                    "item_id": 5005,
                    "title": "Baseus Bowie H1 Pro ANC Headphones",
                    "price": 12500,
                    "original_price": 16000,
                    "discount": "22%",
                    "rating": 4.9,
                    "reviews_count": 78,
                    "seller_name": "Baseus Official Flagship",
                    "product_url": "https://www.daraz.pk/products/baseus-i5005.html",
                    "image": "https://static-01.daraz.pk/p/baseus.jpg"
                }
            ]
        }
    }

    with patch.object(service, "_execute_request", return_value=mock_raw_response):
        res = service.search_products("headphones", page=1)

    assert len(res.products) == 1
    assert res.products[0].name == "Baseus Bowie H1 Pro ANC Headphones"

    # Verify auto-persisted in temp_repo
    persisted = temp_repo.get_product("daraz", "5005")
    assert persisted is not None
    assert persisted.product_name == "Baseus Bowie H1 Pro ANC Headphones"
    assert persisted.price == 12500.0
    assert persisted.rating == 4.9

    snapshots = temp_repo.get_snapshots("daraz", "5005")
    assert len(snapshots) >= 1
    assert snapshots[0].price == 12500.0


def test_daraz_service_fallback_on_429_rate_limit(temp_repo):
    now = datetime.now(timezone.utc)
    # Seed persistent repository with real product
    temp_repo.upsert_product(
        MarketplaceProduct(
            id="daraz_6006",
            platform="daraz",
            product_id="6006",
            product_name="Logitech MX Master 3S Wireless Mouse",
            product_url="https://www.daraz.pk/products/logitech-i6006.html",
            image_url="https://static-01.daraz.pk/p/logitech.jpg",
            seller_name="Logitech Store",
            category="Computers",
            price=24500.0,
            original_price=28000.0,
            discount_percentage=12.5,
            rating=4.9,
            review_count=320,
            in_stock=True,
            first_seen_at=now,
            last_seen_at=now,
            last_synced_at=now
        )
    )

    service = DarazService(api_key="pmx_test_key", marketplace_repo=temp_repo)

    # Simulate 429 RateLimitError from Parse upstream
    with patch.object(service, "_execute_request", side_effect=DarazRateLimitError("Rate limit exceeded")):
        res = service.search_products("mouse", page=1)

    assert res is not None
    assert res.source == "database_cache"
    assert len(res.products) >= 1
    assert res.products[0].product_id == "6006"
    assert res.products[0].name == "Logitech MX Master 3S Wireless Mouse"
    assert res.products[0].price == 24500.0


def test_daraz_service_fallback_on_network_timeout(temp_repo):
    now = datetime.now(timezone.utc)
    temp_repo.upsert_product(
        MarketplaceProduct(
            id="daraz_7007",
            platform="daraz",
            product_id="7007",
            product_name="Apple MacBook Pro M3 14-inch",
            product_url="https://www.daraz.pk/products/macbook-i7007.html",
            price=495000.0,
            first_seen_at=now
        )
    )

    service = DarazService(api_key="pmx_test_key", marketplace_repo=temp_repo)

    with patch.object(service, "_execute_request", side_effect=DarazUpstreamError("Upstream timeout")):
        res = service.search_products("macbook", page=1)

    assert res is not None
    assert res.source == "database_cache"
    assert len(res.products) == 1
    assert res.products[0].product_id == "7007"


def test_dashboard_service_with_persistent_database_cache(temp_repo):
    sync_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    temp_repo.upsert_product(
        MarketplaceProduct(
            id="daraz_8008",
            platform="daraz",
            product_id="8008",
            product_name="Anker Soundcore Space One ANC",
            product_url="https://www.daraz.pk/products/anker-i8008.html",
            image_url="https://static-01.daraz.pk/p/anker.jpg",
            seller_name="Anker Official Store",
            category="Consumer Electronics",
            price=19999.0,
            original_price=24999.0,
            discount_percentage=20.0,
            rating=4.8,
            review_count=185,
            in_stock=True,
            first_seen_at=sync_time,
            last_seen_at=sync_time,
            last_synced_at=sync_time
        )
    )

    daraz_service = DarazService(api_key="pmx_test_key", marketplace_repo=temp_repo)
    dashboard_service = DashboardService(
        product_repo=product_repo,
        alert_repo=alert_repo,
        platform_repo=platform_repo,
        daraz_service=daraz_service,
        marketplace_repo=temp_repo
    )

    # Live requests fail, triggering database fallback
    with patch.object(daraz_service, "_execute_request", side_effect=DarazRateLimitError("429")):
        summary = dashboard_service.get_summary(time_range="30d")

    assert summary.total_trends_monitored >= 1
    assert summary.data_source == "database_cache"
    assert summary.is_live is False
    assert "Cached Daraz Pakistan Data" in summary.system_status
    assert len(summary.top_surging) >= 1
    assert summary.top_surging[0]["name"] == "Anker Soundcore Space One ANC"
    assert summary.metrics[0].value == str(summary.total_trends_monitored)


def test_disk_store_serialization_across_restarts():
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "persistent_store.json")

        now = datetime.now(timezone.utc)
        p = MarketplaceProduct(
            id="daraz_9009",
            platform="daraz",
            product_id="9009",
            product_name="Keychron K2 Pro Mechanical Keyboard",
            product_url="https://www.daraz.pk/products/keychron-i9009.html",
            price=22000.0,
            rating=4.9,
            review_count=45,
            first_seen_at=now,
            last_seen_at=now,
            last_synced_at=now
        )
        snap = ProductMarketSnapshot(
            id="snap_k2",
            product_id="9009",
            platform="daraz",
            price=22000.0,
            rating=4.9,
            observed_at=now
        )

        # Instance 1: write and save
        repo1 = InMemoryMarketplaceProductRepository(storage_file=store_path)
        repo1.upsert_product(p)
        repo1.create_snapshot(snap)

        assert os.path.exists(store_path)

        # Instance 2: new process / reboot simulation
        repo2 = InMemoryMarketplaceProductRepository(storage_file=store_path)
        loaded = repo2.get_product("daraz", "9009")
        assert loaded is not None
        assert loaded.product_name == "Keychron K2 Pro Mechanical Keyboard"
        assert loaded.price == 22000.0

        snaps2 = repo2.get_snapshots("daraz", "9009")
        assert len(snaps2) == 1
        assert snaps2[0].price == 22000.0
