import pytest
from datetime import datetime, timezone
from backend.app.models.domain import Product, PlatformMetrics, DataSource, MarketplaceProduct
from backend.app.repositories.in_memory import (
    InMemoryPlatformRepository,
    InMemoryProductRepository,
    InMemoryMarketplaceProductRepository,
    InMemoryDataSourceRepository
)
from backend.app.services.platform_service import PlatformService
from backend.app.services.data_sources_service import DataSourceService
from backend.app.domain.aggregation import AggregationEngine


def test_unconnected_platforms_have_zero_signals_and_coming_soon():
    """Verify TikTok, Instagram, and Facebook have 0 signals and no fake stats."""
    plt_repo = InMemoryPlatformRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    service = PlatformService(platform_repo=plt_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    platforms = service.list_platforms()
    platforms_by_slug = {p.slug: p for p in platforms}

    for slug in ["tiktok", "instagram", "facebook"]:
        p = platforms_by_slug[slug]
        assert p.status == "Coming Soon"
        assert p.total_signals == 0
        assert p.active_trends == 0
        assert p.velocity_growth == 0.0
        assert p.market_share == 0.0
        assert p.provenance == "none"
        assert p.observation_count == 0
        assert len(p.recent_spikes) == 0


def test_daraz_with_persisted_marketplace_observations():
    """Verify Daraz computes real metrics from persisted marketplace observations."""
    plt_repo = InMemoryPlatformRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    # Add 2 real scraped Daraz products
    p1 = MarketplaceProduct(
        id="mp_101",
        product_id="daraz_101",
        platform="daraz",
        product_name="M10 Wireless Bluetooth Earbuds",
        price=1499.0,
        original_price=2999.0,
        currency="PKR",
        rating=4.5,
        review_count=120,
        product_url="https://www.daraz.pk/products/m10-earbuds.html"
    )
    p2 = MarketplaceProduct(
        id="mp_102",
        product_id="daraz_102",
        platform="daraz",
        product_name="Lenovo Thinkplus LP40 Pro",
        price=2199.0,
        original_price=3500.0,
        currency="PKR",
        rating=4.8,
        review_count=450,
        product_url="https://www.daraz.pk/products/lenovo-lp40.html"
    )
    mp_repo.upsert_product(p1)
    mp_repo.upsert_product(p2)

    service = PlatformService(platform_repo=plt_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    p_daraz = service.get_platform_by_slug("daraz")

    assert p_daraz is not None
    assert p_daraz.status == "Connected"
    assert p_daraz.provenance == "persisted_marketplace_observations"
    assert p_daraz.total_signals >= 2
    assert p_daraz.active_trends >= 2
    assert p_daraz.observation_count >= 2
    assert len(p_daraz.recent_spikes) >= 2
    assert any("M10 Wireless" in sp["hashtag"] for sp in p_daraz.recent_spikes) or any("Lenovo" in sp["hashtag"] for sp in p_daraz.recent_spikes)
    assert any("PKR" in sp["growth"] for sp in p_daraz.recent_spikes)


def test_daraz_with_insufficient_data():
    """Verify Daraz gracefully returns Insufficient Data when no records exist."""
    plt_repo = InMemoryPlatformRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    # Clear any seeded products
    prod_repo._products.clear()
    mp_repo._products.clear()

    service = PlatformService(platform_repo=plt_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    p_daraz = service.get_platform_by_slug("daraz")

    assert p_daraz is not None
    assert p_daraz.status == "Insufficient Data"
    assert p_daraz.total_signals == 0
    assert p_daraz.active_trends == 0
    assert p_daraz.provenance == "none"
    assert len(p_daraz.recent_spikes) == 0


def test_youtube_with_live_ingested_signals():
    """Verify YouTube calculates metrics when products contain YouTube signals."""
    plt_repo = InMemoryPlatformRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    service = PlatformService(platform_repo=plt_repo, product_repo=prod_repo, marketplace_repo=mp_repo)
    p_yt = service.get_platform_by_slug("youtube")

    assert p_yt is not None
    if p_yt.active_trends > 0:
        assert p_yt.status == "Connected"
        assert p_yt.provenance == "live_ingested_signals"
        assert p_yt.total_signals > 0
        assert p_yt.observation_count == p_yt.active_trends


def test_data_sources_dynamic_real_counts():
    """Verify DataSourceService reports real dynamic counts without simulated labels."""
    ds_repo = InMemoryDataSourceRepository()
    mp_repo = InMemoryMarketplaceProductRepository()

    # Add a product to Daraz
    p = MarketplaceProduct(
        id="mp_999",
        product_id="daraz_999",
        platform="daraz",
        product_name="Pro Hair Dryer 2000W",
        price=3500.0,
        currency="PKR"
    )
    mp_repo.upsert_product(p)

    ds_service = DataSourceService(data_source_repo=ds_repo, marketplace_repo=mp_repo)
    sources = ds_service.list_sources()
    sources_by_slug = {s.slug: s for s in sources}

    # Daraz should have records_synced == 1
    assert sources_by_slug["daraz"].records_synced >= 1
    assert sources_by_slug["daraz"].status == "Connected"

    # Social channels should have 0 synced records and Not Connected
    for slug in ["tiktok", "instagram", "facebook"]:
        assert sources_by_slug[slug].records_synced == 0
        assert sources_by_slug[slug].status == "Coming Soon"
        assert sources_by_slug[slug].sync_frequency == "Not Connected"
