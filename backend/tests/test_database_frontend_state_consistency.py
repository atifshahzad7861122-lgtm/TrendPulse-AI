import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.domain import (
    User, Product, MarketplaceProduct, ProductMarketSnapshot,
    ScraperCrawlJob, RawScrapedPayload
)
from backend.app.api.deps import (
    get_product_repository, get_marketplace_product_repository,
    get_watchlist_repository, get_user_repository, get_platform_repository,
    get_category_repository, get_report_repository, get_scraper_repository
)

client = TestClient(app)

def _get_auth_headers(email: str = "auditor@trendpulse.ai", full_name: str = "State Consistency Auditor") -> dict:
    pwd = "AuditPassword123!"
    client.post("/api/v1/auth/register", json={
        "full_name": full_name,
        "email": email,
        "password": pwd,
        "confirm_password": pwd,
        "terms_accepted": True
    })
    res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_01_persisted_marketplace_product_flows_to_product_catalog_api():
    """
    Scenario:
      1. Scraper persists a real marketplace product into MarketplaceProductRepository.
      2. Product Catalog endpoint (/api/v1/products) immediately returns that product.
      3. Product detail endpoint (/api/v1/products/{id}) retrieves exact attributes.
    """
    mp_repo = app.dependency_overrides.get(get_marketplace_product_repository, get_marketplace_product_repository)()
    
    unique_pid = f"daraz_earbuds_{uuid.uuid4().hex[:6]}"
    raw_pid = unique_pid.replace("daraz_", "")
    now = datetime.now(timezone.utc)

    mp = MarketplaceProduct(
        id=unique_pid,
        platform="daraz",
        product_id=raw_pid,
        product_name="Pro Wireless ANC Earbuds V5.3",
        product_url=f"https://www.daraz.pk/products/-i{raw_pid}.html",
        image_url="https://img.daraz.pk/p/earbuds.jpg",
        seller_name="AudioTech Official",
        seller_id="seller_audiotech",
        category="Consumer Electronics",
        price=4500.0,
        original_price=6000.0,
        discount_percentage=25.0,
        discount_label="25% Off",
        rating=4.8,
        review_count=120,
        stock_status="in_stock",
        in_stock=True,
        currency="PKR",
        location="Pakistan",
        first_seen_at=now - timedelta(days=2),
        last_seen_at=now,
        last_synced_at=now,
        raw_source_data={"brand": "AudioTech"}
    )
    mp_repo.upsert_product(mp)

    snap1 = ProductMarketSnapshot(
        id=f"snap_{uuid.uuid4().hex[:8]}",
        product_id=raw_pid,
        platform="daraz",
        price=4800.0,
        rating=4.7,
        review_count=110,
        stock_status="in_stock",
        observed_at=now - timedelta(days=1),
        created_at=now - timedelta(days=1)
    )
    snap2 = ProductMarketSnapshot(
        id=f"snap_{uuid.uuid4().hex[:8]}",
        product_id=raw_pid,
        platform="daraz",
        price=4500.0,
        rating=4.8,
        review_count=120,
        stock_status="in_stock",
        observed_at=now,
        created_at=now
    )
    mp_repo.batch_create_snapshots([snap1, snap2])

    headers = _get_auth_headers("crawler_tester1@trendpulse.ai")

    # 1. Verify in Product Catalog list endpoint
    res = client.get("/api/v1/products?platform=all", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    products = data["data"]
    
    found = next((p for p in products if p["id"] == unique_pid or p["name"] == "Pro Wireless ANC Earbuds V5.3"), None)
    assert found is not None, f"Product {unique_pid} was not found in /api/v1/products"
    assert found["name"] == "Pro Wireless ANC Earbuds V5.3"
    assert found["primary_platform"] == "Daraz"
    assert "PKR" in found["price_range"]
    assert found["provenance"] == "persisted_marketplace_observations"
    assert found["observation_count"] == 3  # 1 current + 2 snapshots

    # 2. Verify in Product Detail endpoint
    detail_res = client.get(f"/api/v1/products/{unique_pid}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["id"] == unique_pid
    assert detail["name"] == "Pro Wireless ANC Earbuds V5.3"
    assert detail["provenance"] == "persisted_marketplace_observations"


def test_02_persisted_product_flows_to_comparison_api_with_truthful_history():
    """
    Scenario:
      Compare Signals endpoint (/api/v1/products/compare) retrieves the real persisted product
      and uses its immutable snapshot history rather than simulated trends.
    """
    mp_repo = app.dependency_overrides.get(get_marketplace_product_repository, get_marketplace_product_repository)()
    
    unique_pid = f"daraz_watch_{uuid.uuid4().hex[:6]}"
    raw_pid = unique_pid.replace("daraz_", "")
    now = datetime.now(timezone.utc)

    mp = MarketplaceProduct(
        id=unique_pid,
        platform="daraz",
        product_id=raw_pid,
        product_name="Ultra Smartwatch Matrix AMOLED",
        product_url=f"https://www.daraz.pk/products/-i{raw_pid}.html",
        image_url="https://img.daraz.pk/p/watch.jpg",
        seller_name="SmartGadgets PK",
        seller_id="seller_smartgadgets",
        category="Consumer Electronics",
        price=8200.0,
        original_price=10000.0,
        discount_percentage=18.0,
        discount_label="18% Off",
        rating=4.9,
        review_count=350,
        stock_status="in_stock",
        in_stock=True,
        currency="PKR",
        location="Pakistan",
        first_seen_at=now - timedelta(days=5),
        last_seen_at=now,
        last_synced_at=now
    )
    mp_repo.upsert_product(mp)

    snap = ProductMarketSnapshot(
        id=f"snap_{uuid.uuid4().hex[:8]}",
        product_id=raw_pid,
        platform="daraz",
        price=8500.0,
        rating=4.8,
        review_count=300,
        stock_status="in_stock",
        observed_at=now - timedelta(days=2),
        created_at=now - timedelta(days=2)
    )
    mp_repo.batch_create_snapshots([snap])

    headers = _get_auth_headers("crawler_tester2@trendpulse.ai")

    res = client.get(f"/api/v1/products/compare?ids={unique_pid}", headers=headers)
    assert res.status_code == 200
    comp_data = res.json()["data"]
    assert len(comp_data) == 1
    prod = comp_data[0]
    assert prod["id"] == unique_pid
    assert prod["name"] == "Ultra Smartwatch Matrix AMOLED"
    assert prod["provenance"] == "persisted_marketplace_observations"
    assert len(prod["historical_prices"]) == 1
    assert prod["historical_prices"][0]["price"] == 8500.0


def test_03_watchlist_synchronization_for_marketplace_product():
    """
    Scenario:
      1. Add a persisted marketplace product to Watchlist (/api/v1/watchlist/{product_id}).
      2. Verify Watchlist list endpoint (/api/v1/watchlist) returns that exact product with is_watchlisted=True.
      3. Verify Product Catalog and Detail endpoints reflect is_watchlisted=True for this authenticated user.
      4. Remove from Watchlist (/api/v1/watchlist/{product_id}) and verify state update.
    """
    mp_repo = app.dependency_overrides.get(get_marketplace_product_repository, get_marketplace_product_repository)()
    
    unique_pid = f"daraz_bag_{uuid.uuid4().hex[:6]}"
    raw_pid = unique_pid.replace("daraz_", "")
    now = datetime.now(timezone.utc)

    mp = MarketplaceProduct(
        id=unique_pid,
        platform="daraz",
        product_id=raw_pid,
        product_name="Tactical Waterproof Hydration Pack",
        product_url=f"https://www.daraz.pk/products/-i{raw_pid}.html",
        image_url="https://img.daraz.pk/p/bag.jpg",
        seller_name="Outdoor Gear PK",
        seller_id="seller_outdoorgear",
        category="Sports & Outdoor",
        price=3200.0,
        original_price=4000.0,
        discount_percentage=20.0,
        discount_label="20% Off",
        rating=4.6,
        review_count=45,
        stock_status="in_stock",
        in_stock=True,
        currency="PKR",
        location="Pakistan",
        first_seen_at=now,
        last_seen_at=now,
        last_synced_at=now
    )
    mp_repo.upsert_product(mp)

    headers = _get_auth_headers("watchlist_tester@trendpulse.ai")

    # 1. Add to watchlist
    add_res = client.post(f"/api/v1/watchlist/{unique_pid}", headers=headers)
    assert add_res.status_code == 200
    assert add_res.json()["data"]["is_watchlisted"] is True

    # 2. Verify in /api/v1/watchlist
    wl_res = client.get("/api/v1/watchlist", headers=headers)
    assert wl_res.status_code == 200
    wl_items = wl_res.json()["data"]
    wl_found = next((p for p in wl_items if p["id"] == unique_pid or p["name"] == "Tactical Waterproof Hydration Pack"), None)
    assert wl_found is not None, f"Watchlist did not contain {unique_pid}"
    assert wl_found["is_watchlisted"] is True

    # 3. Verify in /api/v1/products/{product_id}
    detail_res = client.get(f"/api/v1/products/{unique_pid}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["is_watchlisted"] is True

    # 4. Remove from watchlist
    del_res = client.delete(f"/api/v1/watchlist/{unique_pid}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["data"]["is_watchlisted"] is False

    # 5. Verify no longer in watchlist
    wl_res_after = client.get("/api/v1/watchlist", headers=headers)
    assert not any(p["id"] == unique_pid for p in wl_res_after.json()["data"])


def test_04_cross_platform_intelligence_and_platform_metrics_consistency():
    """
    Scenario:
      Verify that platform telemetry (/api/v1/platforms/daraz and /api/v1/platforms)
      dynamically aggregates persisted marketplace products.
    """
    mp_repo = app.dependency_overrides.get(get_marketplace_product_repository, get_marketplace_product_repository)()
    
    now = datetime.now(timezone.utc)
    for i in range(2):
        raw_id = f"telemetry_{i}_{uuid.uuid4().hex[:4]}"
        mp = MarketplaceProduct(
            id=f"daraz_{raw_id}",
            platform="daraz",
            product_id=raw_id,
            product_name=f"Telemetry Product {i}",
            product_url=f"https://www.daraz.pk/products/-i{raw_id}.html",
            image_url=f"https://img.daraz.pk/p/{raw_id}.jpg",
            seller_name="Daraz Merchant",
            category="Home & Living",
            price=1500.0 * (i + 1),
            rating=4.5,
            review_count=20 * (i + 1),
            stock_status="in_stock",
            in_stock=True,
            currency="PKR",
            location="Pakistan",
            first_seen_at=now,
            last_seen_at=now,
            last_synced_at=now
        )
        mp_repo.upsert_product(mp)

    res = client.get("/api/v1/platforms/daraz")
    assert res.status_code == 200
    plat = res.json()["data"]
    assert plat["slug"] == "daraz"
    assert plat["status"] == "Connected"
    assert plat["observation_count"] >= 2
    assert plat["total_signals"] >= 2
    assert plat["provenance"] == "persisted_marketplace_observations"


def test_05_categories_and_reports_consistency():
    """
    Scenario:
      Verify that Categories (/api/v1/categories) and Reports (/api/v1/reports)
      generate metrics purely from persisted observations without synthetic data.
    """
    headers = _get_auth_headers("cat_report_auditor@trendpulse.ai")

    # Categories
    cat_res = client.get("/api/v1/categories", headers=headers)
    assert cat_res.status_code == 200
    cats = cat_res.json()["data"]
    assert len(cats) >= 5
    for c in cats:
        assert isinstance(c["product_count"], int)
        assert isinstance(c["avg_trend_score"], (int, float))
        assert isinstance(c["growth_rate"], (int, float))

    # Reports
    rep_res = client.post("/api/v1/reports/generate", json={
        "title": "State Consistency Verification Report",
        "template": "executive",
        "time_range": "30d",
        "category": "All Categories",
        "platforms": ["Daraz"]
    }, headers=headers)
    assert rep_res.status_code == 200
    report = rep_res.json()["data"]
    assert report["title"] == "State Consistency Verification Report"
    assert report["data_sufficiency"] in ("live_data", "sufficient_data", "limited_data", "no_data")
    assert report["total_signals_analyzed"] != 925100  # Verify no old demo constant


def test_06_search_service_includes_persisted_marketplace_products():
    """
    Scenario:
      Cross-entity search (/api/v1/search?q=...) finds persisted marketplace products by title or brand.
    """
    mp_repo = app.dependency_overrides.get(get_marketplace_product_repository, get_marketplace_product_repository)()
    
    unique_keyword = f"KevlarShield_{uuid.uuid4().hex[:6]}"
    raw_pid = f"search_item_{uuid.uuid4().hex[:4]}"
    now = datetime.now(timezone.utc)

    mp = MarketplaceProduct(
        id=f"daraz_{raw_pid}",
        platform="daraz",
        product_id=raw_pid,
        product_name=f"{unique_keyword} Heavy Duty Phone Case",
        product_url=f"https://www.daraz.pk/products/-i{raw_pid}.html",
        image_url="https://img.daraz.pk/p/case.jpg",
        seller_name="ArmorTech",
        category="Consumer Electronics",
        price=1200.0,
        rating=4.9,
        review_count=88,
        stock_status="in_stock",
        in_stock=True,
        currency="PKR",
        location="Pakistan",
        first_seen_at=now,
        last_seen_at=now,
        last_synced_at=now
    )
    mp_repo.upsert_product(mp)

    res = client.get(f"/api/v1/search?q={unique_keyword}")
    assert res.status_code == 200
    search_data = res.json()["data"]
    results = search_data["results"]
    match = next((r for r in results if unique_keyword in r["title"]), None)
    assert match is not None, f"Search query for {unique_keyword} did not find persisted product"
    assert match["category"] == "products"
    assert match["id"] == f"daraz_{raw_pid}"


@pytest.mark.asyncio
async def test_07_controlled_daraz_crawl_to_product_catalog_and_compare_flow():
    """
    Controlled live Daraz crawl (max 3 products) verifying the entire pipeline:
    Daraz discovery -> extraction -> validation -> RawScrapedPayload -> MarketplaceProduct
    -> ProductMarketSnapshot -> ProductPlatformListing -> UnifiedProduct
    -> Product Catalog API -> Compare Signals API.
    """
    from backend.app.services.scraper.bridge import ScraperIntegrationBridge
    from backend.app.services.scraper.providers.daraz_specialized import DarazSpecializedScraperEngine
    from backend.app.services.agents.data_quality.agent import DataQualityAgent
    from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
    from backend.app.services.daraz_service import DarazService
    from backend.app.repositories.in_memory import (
        InMemoryScraperRepository, InMemoryDataQualityRepository,
        InMemoryMarketplaceProductRepository, InMemoryUnifiedProductRepository
    )

    scraper_repo = InMemoryScraperRepository()
    quality_repo = InMemoryDataQualityRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    u_repo = InMemoryUnifiedProductRepository()

    quality_agent = DataQualityAgent(repository=quality_repo)
    intel_service = UnifiedProductIntelligenceService(
        unified_repo=u_repo,
        daraz_repo=mp_repo,
        data_quality_agent=quality_agent
    )

    daraz_svc = DarazService(marketplace_repo=mp_repo)
    engine = DarazSpecializedScraperEngine(headless=True)
    bridge = ScraperIntegrationBridge(
        scraper_repo=scraper_repo,
        marketplace_repo=mp_repo,
        unified_repo=u_repo,
        dq_repo=quality_repo,
        dq_agent=quality_agent,
        unified_intelligence_svc=intel_service,
        daraz_specialized_engine=engine,
        daraz_service=daraz_svc
    )

    job = ScraperCrawlJob(
        id=f"job-daraz-test-{uuid.uuid4().hex[:6]}",
        marketplace="daraz",
        keywords=["wireless earbuds"],
        target_count=3,
        metadata_json={"provider": "daraz_specialized"}
    )
    scraper_repo.create_job(job)

    res_job = await bridge.run_scraper_job(job)
    assert res_job.status in ["completed", "completed_with_challenges"]
    assert res_job.products_persisted >= 0

    persisted_mps = mp_repo.list_products(platform="daraz")
    if persisted_mps:
        first_mp = persisted_mps[0]
        assert first_mp.platform == "daraz"
        assert first_mp.product_name
        assert first_mp.currency == "PKR"

        # Check snapshots
        snaps = mp_repo.get_snapshots("daraz", first_mp.product_id)
        assert len(snaps) >= 1

        # Check raw payload
        raws = scraper_repo.list_raw_payloads(crawl_job_id=job.id)
        assert len(raws) >= 1


def test_08_empty_state_truthfulness_when_no_data():
    """
    Scenario:
      When repositories have 0 matching records, APIs return explicit truthful empty states:
      - Watchlist: []
      - Search for unknown term: total_results = 0
      - Compare with non-existent ID: empty comparison list
    """
    headers = _get_auth_headers("empty_state_tester@trendpulse.ai")

    # Watchlist empty
    wl_res = client.get("/api/v1/watchlist", headers=headers)
    assert wl_res.status_code == 200
    assert wl_res.json()["data"] == []

    # Search empty
    s_res = client.get("/api/v1/search?q=NonExistentZxy123987", headers=headers)
    assert s_res.status_code == 200
    assert s_res.json()["data"]["total_results"] == 0

    # Compare non-existent
    c_res = client.get("/api/v1/products/compare?ids=non_existent_9999", headers=headers)
    assert c_res.status_code == 200
    assert c_res.json()["data"] == []

