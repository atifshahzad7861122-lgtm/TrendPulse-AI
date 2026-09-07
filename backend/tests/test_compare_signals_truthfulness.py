import pytest
from datetime import datetime, timezone, timedelta
from backend.app.models.domain import Product, MarketplaceProduct, ProductMarketSnapshot, User
from backend.app.repositories.in_memory import (
    InMemoryProductRepository,
    InMemoryMarketplaceProductRepository,
    InMemoryWatchlistRepository,
    InMemoryPlatformRepository
)
from backend.app.services.intelligence import ProductIntelligenceEngine
from backend.app.services.watchlist_service import WatchlistService
from backend.app.services.daraz_service import DarazService
from backend.app.api.v1.endpoints.products import compare_products, _marketplace_product_to_product


def test_compare_two_real_persisted_products_truthful():
    """Verify comparing two real persisted products returns truthful metrics and authentic provenance."""
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    wl_repo = InMemoryWatchlistRepository()
    
    prod_repo._products.clear()
    mp_repo._products.clear()

    # Product A: Real Daraz scraped item with 1 snapshot
    now = datetime.now(timezone.utc)
    mp_a = MarketplaceProduct(
        id="daraz_item_101",
        product_id="101",
        platform="daraz",
        product_name="M10 Wireless Earbuds Bluetooth 5.1",
        price=1450.0,
        currency="PKR",
        rating=4.5,
        review_count=20,
        in_stock=True
    )
    mp_repo.upsert_product(mp_a)

    # Product B: Real Daraz scraped item with 2 snapshots (showing real price change)
    mp_b = MarketplaceProduct(
        id="daraz_item_202",
        product_id="202",
        platform="daraz",
        product_name="RGB Gaming Mouse Pad Extended",
        price=2200.0,
        currency="PKR",
        rating=4.8,
        review_count=50,
        in_stock=True
    )
    mp_repo.upsert_product(mp_b)

    snap1 = ProductMarketSnapshot(
        id="snap_b_1",
        platform="daraz",
        product_id="202",
        price=2000.0,
        currency="PKR",
        rating=4.8,
        review_count=45,
        observed_at=now - timedelta(days=5)
    )
    snap2 = ProductMarketSnapshot(
        id="snap_b_2",
        platform="daraz",
        product_id="202",
        price=2200.0,
        currency="PKR",
        rating=4.8,
        review_count=50,
        observed_at=now
    )
    mp_repo.batch_create_snapshots([snap1, snap2])

    intel_engine = ProductIntelligenceEngine(product_repo=prod_repo)
    wl_service = WatchlistService(watchlist_repo=wl_repo, product_repo=prod_repo)
    daraz_service = DarazService(marketplace_repo=mp_repo)
    current_user = User(id="usr_qa_1", email="qa@trendpulse.ai", full_name="QA User", hashed_password="dummy_hash")

    resp = compare_products(
        ids="daraz_101,daraz_202",
        intelligence=intel_engine,
        watchlist_service=wl_service,
        daraz_service=daraz_service,
        marketplace_repo=mp_repo,
        current_user=current_user
    )

    assert resp.success is True
    data = resp.data
    assert len(data) == 2

    # Verify Product A (1 observation -> growth_rate == 0.0, provenance == persisted_marketplace_observations)
    p_a = next(p for p in data if "101" in p.id)
    assert p_a.name == "M10 Wireless Earbuds Bluetooth 5.1"
    assert p_a.growth_rate == 0.0
    assert p_a.provenance == "persisted_marketplace_observations"
    assert p_a.observation_count == 1
    assert p_a.volume == 20
    assert p_a.sentiment_score == 0.9  # 4.5 / 5.0

    # Verify Product B (2 snapshots -> growth_rate == +10.0% from 2000 to 2200)
    p_b = next(p for p in data if "202" in p.id)
    assert p_b.name == "RGB Gaming Mouse Pad Extended"
    assert p_b.growth_rate == 10.0
    assert p_b.provenance == "persisted_marketplace_observations"
    assert p_b.observation_count == 3  # 1 product + 2 snapshots
    assert len(p_b.historical_prices) == 2


def test_empty_database_and_nonexistent_ids_produce_no_fake_data():
    """Verify non-existent IDs do not return synthetic or hardcoded demo models."""
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    wl_repo = InMemoryWatchlistRepository()
    
    prod_repo._products.clear()
    mp_repo._products.clear()

    intel_engine = ProductIntelligenceEngine(product_repo=prod_repo)
    wl_service = WatchlistService(watchlist_repo=wl_repo, product_repo=prod_repo)
    daraz_service = DarazService(marketplace_repo=mp_repo)
    current_user = User(id="usr_qa_2", email="qa@trendpulse.ai", full_name="QA User", hashed_password="dummy_hash")

    resp = compare_products(
        ids="nonexistent_id_1,nonexistent_id_2",
        intelligence=intel_engine,
        watchlist_service=wl_service,
        daraz_service=daraz_service,
        marketplace_repo=mp_repo,
        current_user=current_user
    )

    assert resp.success is True
    assert len(resp.data) == 0


def test_no_synthetic_growth_without_history():
    """Verify products with zero historical snapshots return 0.0 growth rate, never demo growth rates."""
    mp = MarketplaceProduct(
        id="daraz_fresh_01",
        product_id="fresh_01",
        platform="daraz",
        product_name="Fresh Scraped Earphones",
        price=999.0,
        currency="PKR",
        rating=4.0,
        review_count=5
    )
    # No snapshots passed
    prod = _marketplace_product_to_product(mp, [])
    assert prod.growth_rate == 0.0
    assert prod.historical_scores == []
    assert prod.historical_prices == []
    assert prod.provenance == "persisted_marketplace_observations"


def test_sentiment_requires_real_reviews_or_rating():
    """Verify products without rating or reviews produce 0.0 sentiment score."""
    mp = MarketplaceProduct(
        id="daraz_unrated_01",
        product_id="unrated_01",
        platform="daraz",
        product_name="Brand New Unrated Gadget",
        price=500.0,
        currency="PKR",
        rating=0.0,
        review_count=0
    )
    prod = _marketplace_product_to_product(mp, [])
    assert prod.sentiment_score == 0.0
    assert prod.trend_score == 0.0
    assert prod.velocity_label == "Insufficient Data"


def test_no_synthetic_demo_constants_in_comparison():
    """Verify known demo/seeded constants (340.5, 218.0, 156.9, 89.8, 80.9) are never fabricated."""
    mp = MarketplaceProduct(
        id="daraz_fresh_real",
        product_id="fresh_real",
        platform="daraz",
        product_name="Real Daraz Scraped Kitchen Blender",
        price=3500.0,
        currency="PKR",
        rating=4.2,
        review_count=12
    )
    prod = _marketplace_product_to_product(mp, [])
    
    # Assert none of the forbidden synthetic constants are fabricated
    forbidden_scores = [89.8, 80.9, 69.2]
    forbidden_growths = [340.5, 218.0, 156.9]

    assert prod.trend_score not in forbidden_scores
    assert prod.growth_rate not in forbidden_growths
    assert prod.growth_rate == 0.0  # single point -> 0.0
    assert prod.provenance == "persisted_marketplace_observations"
    assert prod.historical_observation_count == 0

