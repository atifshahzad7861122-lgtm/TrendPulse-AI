import pytest
from datetime import datetime, timezone
from backend.app.models.domain import Product, Category, MarketplaceProduct
from backend.app.repositories.in_memory import (
    InMemoryCategoryRepository,
    InMemoryProductRepository,
    InMemoryMarketplaceProductRepository,
    InMemoryPlatformRepository
)
from backend.app.services.category_service import CategoryService
from backend.app.services.platform_service import PlatformService
from backend.app.domain.aggregation import AggregationEngine


def test_empty_database_returns_no_fake_category_metrics():
    """Verify empty database returns 0 counts and no fabricated scores or growth."""
    cat_repo = InMemoryCategoryRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    # Clear products
    prod_repo._products.clear()
    mp_repo._products.clear()

    service = CategoryService(category_repo=cat_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    categories = service.list_categories()

    for c in categories:
        assert c.product_count == 0
        assert c.avg_trend_score == 0.0
        assert c.growth_rate == 0.0
        assert c.velocity_label == "No Data"
        assert c.provenance == "none"
        assert c.observation_count == 0


def test_no_hardcoded_demo_values():
    """Verify no hardcoded demo values (89.8, 80.9, 340.5, 218) are returned for empty categories."""
    cat_repo = InMemoryCategoryRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()

    service = CategoryService(category_repo=cat_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    categories = service.list_categories()

    demo_scores = {89.8, 80.9, 69.2, 92.4, 89.6, 88.1}
    demo_growths = {340.5, 218.0, 156.9, 245.8, 194.2}

    for c in categories:
        assert c.avg_trend_score not in demo_scores
        assert c.growth_rate not in demo_growths


def test_real_category_product_count_and_daraz_integration():
    """Verify real persisted Daraz marketplace items contribute accurately to canonical categories."""
    cat_repo = InMemoryCategoryRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()

    # Add 2 Daraz products in Electronics and 1 in Beauty
    p1 = MarketplaceProduct(
        id="daraz_item_1",
        product_id="d1",
        platform="daraz",
        product_name="M10 Wireless Bluetooth Earbuds Stereo Audio",
        price=1499.0,
        currency="PKR"
    )
    p2 = MarketplaceProduct(
        id="daraz_item_2",
        product_id="d2",
        platform="daraz",
        product_name="Fast USB-C Wireless Charger Dock",
        price=2200.0,
        currency="PKR"
    )
    p3 = MarketplaceProduct(
        id="daraz_item_3",
        product_id="d3",
        platform="daraz",
        product_name="Organic Vitamin C Face Serum Glowing Skin",
        price=850.0,
        currency="PKR"
    )
    mp_repo.upsert_product(p1)
    mp_repo.upsert_product(p2)
    mp_repo.upsert_product(p3)

    service = CategoryService(category_repo=cat_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    categories = service.list_categories()
    cats_by_slug = {c.slug: c for c in categories}

    electronics = cats_by_slug["consumer-electronics"]
    beauty = cats_by_slug["beauty-personal-care"]
    sports = cats_by_slug["sports-outdoor"]

    assert electronics.product_count == 2
    assert electronics.provenance == "persisted_marketplace_observations"
    assert "Daraz" in electronics.top_platforms

    assert beauty.product_count == 1
    assert beauty.provenance == "persisted_marketplace_observations"
    assert "Daraz" in beauty.top_platforms

    assert sports.product_count == 0
    assert sports.provenance == "none"


def test_growth_calculated_only_when_historical_data_exists():
    """Verify growth rate is 0.0 when no historical growth baseline exists."""
    cat_repo = InMemoryCategoryRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()

    # Add product without growth rate or historical scores
    p = Product(
        id="p_test_1",
        name="Wireless Ergonomic Mouse",
        category="Consumer Electronics",
        trend_score=75.0,
        growth_rate=0.0,
        volume=5000,
        primary_platform="YouTube",
        platforms=["YouTube"]
    )
    prod_repo.update(p)

    service = CategoryService(category_repo=cat_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    c = service.get_category_by_id("consumer-electronics")

    assert c is not None
    assert c.product_count == 1
    assert c.avg_trend_score == 75.0
    assert c.growth_rate == 0.0
    assert c.velocity_label == "Surging"


def test_category_normalization_and_platform_provenance_intact():
    """Verify taxonomy normalization works and Bug #4 platform provenance is preserved."""
    cat_repo = InMemoryCategoryRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    plt_repo = InMemoryPlatformRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()

    p = MarketplaceProduct(
        id="d_shoe_1",
        product_id="ds1",
        platform="daraz",
        product_name="Running Shoes Trail Sports Gear",
        price=3200.0,
        currency="PKR"
    )
    mp_repo.upsert_product(p)

    cat_svc = CategoryService(category_repo=cat_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    sports = cat_svc.get_category_by_id("sports-outdoor")
    assert sports is not None
    assert sports.product_count == 1
    assert sports.provenance == "persisted_marketplace_observations"

    # Verify PlatformService also maintains Bug #4 behavior
    plt_svc = PlatformService(platform_repo=plt_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    daraz_plt = plt_svc.get_platform_by_slug("daraz")
    assert daraz_plt.status == "Connected"
    assert daraz_plt.provenance == "persisted_marketplace_observations"
    assert daraz_plt.total_signals >= 1
