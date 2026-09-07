import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.domain import ScraperCrawlJob, RawScrapedPayload, ScraperMarketplaceHealth
from backend.app.repositories.in_memory import (
    InMemoryScraperRepository, InMemoryMarketplaceProductRepository,
    InMemoryUnifiedProductRepository, InMemoryDataQualityRepository
)
from backend.app.services.scraper.bridge import ScraperIntegrationBridge
from backend.app.services.scraper.service import ScraperService
from backend.app.services.scraper.models import StartScraperJobRequest

import sys
from pathlib import Path
_SCRAPER_ROOT = Path(__file__).resolve().parents[2] / "Daraz Scrapper"
if str(_SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRAPER_ROOT))

# Import Scraper intelligence models
from app.crawling.models import MarketplaceType
from app.intelligence.models.product import (
    ProductIntelligence, Variant, Specification, ImageRecord
)



@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def scraper_repo():
    return InMemoryScraperRepository()


@pytest.fixture
def marketplace_repo():
    return InMemoryMarketplaceProductRepository()


@pytest.fixture
def unified_repo():
    return InMemoryUnifiedProductRepository()


@pytest.fixture
def dq_repo():
    return InMemoryDataQualityRepository()


def test_scraper_job_crud_in_memory(scraper_repo):
    now = datetime.now(timezone.utc)
    job = ScraperCrawlJob(
        id="job_test_daraz_001",
        marketplace="daraz",
        trigger_type="manual",
        keywords=["wireless earbuds"],
        urls=["https://www.daraz.pk/products/test-item.html"],
        target_count=5,
        max_workers=2,
        status="queued",
        created_at=now,
        updated_at=now
    )

    created = scraper_repo.create_job(job)
    assert created.id == "job_test_daraz_001"
    assert created.marketplace == "daraz"

    fetched = scraper_repo.get_job("job_test_daraz_001")
    assert fetched is not None
    assert fetched.keywords == ["wireless earbuds"]

    # Update job
    fetched.status = "running"
    fetched.products_fetched = 3
    updated = scraper_repo.update_job(fetched)
    assert updated.status == "running"
    assert updated.products_fetched == 3

    # List jobs
    jobs = scraper_repo.list_jobs(marketplace="daraz")
    assert len(jobs) == 1
    assert jobs[0].id == "job_test_daraz_001"

    count = scraper_repo.count_jobs(marketplace="daraz")
    assert count == 1


def test_scraper_raw_payload_and_health(scraper_repo):
    now = datetime.now(timezone.utc)
    raw = RawScrapedPayload(
        id="raw_daraz_prod_12345",
        marketplace="daraz",
        product_id="prod_12345",
        crawl_job_id="job_001",
        source_url="https://www.daraz.pk/products/item-12345.html",
        raw_payload={"title": "M10 TWS Wireless Earbuds", "price": 1250.0},
        normalized_payload={"title": "M10 TWS Wireless Earbuds", "price": 1250.0},
        parser_version="2.0.0",
        extraction_status="complete",
        quality_status="valid",
        confidence_score=0.98,
        scraped_at=now,
        created_at=now
    )

    saved = scraper_repo.save_raw_payload(raw)
    assert saved.product_id == "prod_12345"

    retrieved = scraper_repo.get_raw_payload("daraz", "prod_12345")
    assert retrieved is not None
    assert retrieved.raw_payload["title"] == "M10 TWS Wireless Earbuds"

    # Marketplace health
    health_list = scraper_repo.list_marketplace_health()
    assert len(health_list) >= 5
    daraz_health = scraper_repo.get_marketplace_health("daraz")
    assert daraz_health is not None
    assert daraz_health.status == "healthy"


@pytest.mark.asyncio
async def test_scraper_bridge_persist_scraped_product(scraper_repo, marketplace_repo, unified_repo, dq_repo):
    bridge = ScraperIntegrationBridge(
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        dq_repo=dq_repo
    )

    # Construct real ProductIntelligence model
    prod_intel = ProductIntelligence(
        product_id="daraz_item_999",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://www.daraz.pk/products/m10-earbuds-999.html",
        canonical_url="https://www.daraz.pk/products/m10-earbuds-999.html",
        title="M10 TWS Bluetooth 5.1 Earphones Touch Control",
        price=1499.0,
        original_price=2999.0,
        discount=50.0,
        currency="PKR",
        rating=4.7,
        review_count=128,
        sold_count=500,
        seller_name="Official Audio Store PK",
        seller_id="seller_pk_888",
        seller_rating=4.8,
        seller_url="https://www.daraz.pk/shop/official-audio-pk",
        category_name="Audio & Headphones",
        category_path="Electronics > Audio > Headphones",
        primary_image="https://img.daraz.pk/p/m10-thumb.jpg",
        images=[ImageRecord(url="https://img.daraz.pk/p/m10-1.jpg", is_primary=True)],
        specifications=[
            Specification(key="Bluetooth Version", value="5.1"),
            Specification(key="Battery Life", value="4-5 Hours")
        ],
        variants=[
            Variant(sku_id="var_black", name="Black Color", price=1499.0)
        ],
        raw_data="<div>M10 TWS</div>",
        extraction_confidence={"price": 0.95, "title": 0.98},
        overall_confidence=0.95
    )

    job = ScraperCrawlJob(
        id="job_persist_test",
        marketplace="daraz",
        target_count=1
    )
    scraper_repo.create_job(job)

    # Execute persistence
    await bridge._persist_scraped_product(prod_intel, job)

    assert job.products_persisted == 1

    # Verify MarketplaceProduct exists
    mp = marketplace_repo.get_product("daraz", "daraz_item_999")
    assert mp is not None
    assert mp.product_name == "M10 TWS Bluetooth 5.1 Earphones Touch Control"
    assert mp.price == 1499.0
    assert mp.currency == "PKR"
    assert mp.discount_percentage == 50.0
    assert mp.seller_name == "Official Audio Store PK"

    # Verify RawScrapedPayload exists
    raw = scraper_repo.get_raw_payload("daraz", "daraz_item_999")
    assert raw is not None
    assert raw.raw_payload["specifications"]["Bluetooth Version"] == "5.1"

    # Verify historical snapshot exists
    snapshots = marketplace_repo.get_snapshots("daraz", "daraz_item_999")
    assert len(snapshots) >= 1
    assert snapshots[0].price == 1499.0


def test_scraper_api_endpoints(client):
    # 1. Start job with dry_run
    start_payload = {
        "marketplace": "amazon",
        "keywords": ["gaming mouse"],
        "max_products": 2,
        "max_workers": 1,
        "dry_run": True
    }
    r = client.post("/api/v1/scraper/jobs/start", json=start_payload)
    assert r.status_code == 200
    res_data = r.json()
    assert res_data["success"] is True
    job_id = res_data["data"]["job_id"]
    assert job_id.startswith("job_amazon_")

    # 2. Get job status
    r_status = client.get(f"/api/v1/scraper/jobs/{job_id}/status")
    assert r_status.status_code == 200
    assert r_status.json()["data"]["job_id"] == job_id

    # 3. List jobs
    r_jobs = client.get("/api/v1/scraper/jobs")
    assert r_jobs.status_code == 200
    assert r_jobs.json()["data"]["total"] >= 1

    # 4. Marketplaces health
    r_health = client.get("/api/v1/scraper/marketplaces/health")
    assert r_health.status_code == 200
    health_items = r_health.json()["data"]
    assert len(health_items) >= 5

    # 5. List products
    r_prods = client.get("/api/v1/scraper/products")
    assert r_prods.status_code == 200
    assert "products" in r_prods.json()["data"]

    # 6. Stop job
    r_stop = client.post(f"/api/v1/scraper/jobs/{job_id}/stop")
    assert r_stop.status_code == 200
    assert r_stop.json()["data"]["stopped"] is True
