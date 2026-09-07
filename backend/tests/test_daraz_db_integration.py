import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.app.models.domain import (
    MarketplaceProduct,
    ProductMarketSnapshot,
    DarazSeller,
    DarazCategory,
    DarazReview,
    DarazIngestionRun,
    DarazApiTelemetry,
    DarazDailyQuota,
    DarazTrainingDataset
)
from backend.app.schemas.daraz import (
    DarazProductItem,
    DarazProductDetails,
    DarazSellerInfo
)
from backend.app.repositories.in_memory import InMemoryMarketplaceProductRepository
from backend.app.services.daraz_service import DarazService
from backend.app.services.daraz.official_provider import DarazOfficialProvider


import tempfile
import os

@pytest.fixture
def repo():
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "test_marketplace_products_store.json")
    return InMemoryMarketplaceProductRepository(storage_file=temp_file)


def test_product_upsert_and_duplicate_prevention(repo):
    p1 = MarketplaceProduct(
        id="daraz_1001",
        platform="daraz",
        product_id="1001",
        product_name="Wireless Earbuds V1",
        price=2500.0,
        original_price=3000.0,
        rating=4.5,
        review_count=120,
        currency="PKR"
    )
    repo.upsert_product(p1)
    assert repo.count_products(platform="daraz") == 1

    # Upsert with new price
    p1_updated = p1.model_copy(update={"price": 2200.0, "product_name": "Wireless Earbuds V2"})
    repo.upsert_product(p1_updated)

    # Must prevent duplicate product rows
    assert repo.count_products(platform="daraz") == 1
    fetched = repo.get_product(platform="daraz", product_id="1001")
    assert fetched is not None
    assert fetched.price == 2200.0
    assert fetched.product_name == "Wireless Earbuds V2"


def test_market_snapshots_persistence(repo):
    now = datetime.now(timezone.utc)
    s1 = ProductMarketSnapshot(
        id=str(uuid.uuid4()),
        product_id="1001",
        platform="daraz",
        price=2500.0,
        rating=4.5,
        review_count=100,
        observed_at=now
    )
    s2 = ProductMarketSnapshot(
        id=str(uuid.uuid4()),
        product_id="1001",
        platform="daraz",
        price=2300.0,
        rating=4.6,
        review_count=110,
        observed_at=now
    )
    repo.batch_create_snapshots([s1, s2])

    snaps = repo.get_snapshots(platform="daraz", product_id="1001")
    assert len(snaps) == 2
    assert snaps[0].product_id == "1001"


def test_seller_upsert_and_query(repo):
    seller = DarazSeller(
        id="seller_daraz_store_1",
        seller_id="daraz_store_1",
        seller_name="Official Audio Store",
        shop_url="https://www.daraz.pk/shop/audio-store",
        rating=4.8,
        positive_ratings_percentage=96.5,
        location="Karachi",
        is_official_store=True,
        total_products=45
    )
    repo.upsert_seller(seller)

    fetched = repo.get_seller("daraz_store_1")
    assert fetched is not None
    assert fetched.seller_name == "Official Audio Store"
    assert fetched.is_official_store is True

    # Update seller
    updated_seller = seller.model_copy(update={"total_products": 50, "rating": 4.9})
    repo.upsert_seller(updated_seller)

    sellers = repo.list_sellers()
    assert len(sellers) == 1
    assert sellers[0].total_products == 50
    assert sellers[0].rating == 4.9


def test_category_hierarchy_and_query(repo):
    cat1 = DarazCategory(
        id="cat_electronics",
        category_id="electronics",
        name="Electronics",
        slug="electronics",
        level=1,
        leaf=False
    )
    cat2 = DarazCategory(
        id="cat_audio",
        category_id="audio",
        parent_id="electronics",
        name="Audio & Headphones",
        slug="audio-headphones",
        level=2,
        leaf=True
    )
    repo.upsert_category(cat1)
    repo.upsert_category(cat2)

    assert repo.get_category("electronics").name == "Electronics"
    children = repo.list_categories(parent_id="electronics")
    assert len(children) == 1
    assert children[0].category_id == "audio"


def test_reviews_persistence_and_query(repo):
    now = datetime.now(timezone.utc)
    rev = DarazReview(
        id="rev_5501",
        review_id="5501",
        product_id="1001",
        seller_id="daraz_store_1",
        rating=5.0,
        reviewer_name="Ali Khan",
        review_title="Excellent Sound Quality",
        review_content="Battery lasts for 6 hours easily. Original product!",
        verified_purchase=True,
        review_date=now,
        sentiment_score=0.92
    )
    repo.create_review(rev)

    reviews = repo.list_reviews("1001")
    assert len(reviews) == 1
    assert reviews[0].review_id == "5501"
    assert reviews[0].sentiment_score == 0.92


def test_ingestion_runs_lifecycle(repo):
    now = datetime.now(timezone.utc)
    run = DarazIngestionRun(
        id="run_daraz_001",
        provider_name="daraz_official_open_platform",
        status="running",
        trigger_type="manual",
        category="Electronics",
        started_at=now
    )
    repo.create_ingestion_run(run)

    fetched = repo.get_ingestion_run("run_daraz_001")
    assert fetched is not None
    assert fetched.status == "running"

    # Complete the run
    updated_run = run.model_copy(update={
        "status": "completed",
        "products_fetched": 25,
        "products_inserted": 20,
        "products_updated": 5,
        "snapshots_created": 25,
        "completed_at": datetime.now(timezone.utc)
    })
    repo.update_ingestion_run(updated_run)

    completed = repo.get_ingestion_run("run_daraz_001")
    assert completed.status == "completed"
    assert completed.products_fetched == 25


def test_daily_quota_and_telemetry_tracking(repo):
    date_str = "2026-08-26"
    quota = repo.get_or_create_daily_quota(date=date_str, daily_limit=6000000)
    assert quota.daily_limit == 6000000
    assert quota.requests_used == 0
    assert quota.remaining == 6000000

    # Increment quota by 5
    repo.increment_daily_quota(date=date_str, count=5, is_rate_limited=False)
    updated_quota = repo.get_or_create_daily_quota(date=date_str)
    assert updated_quota.requests_used == 5
    assert updated_quota.remaining == 5999995
    assert updated_quota.rate_limit_hits == 0

    # Record API telemetry
    t = DarazApiTelemetry(
        id="telem_01",
        endpoint="/products/get",
        method="POST",
        provider_name="daraz_official_open_platform",
        status_code=200,
        latency_ms=145.2,
        success=True,
        response_size_bytes=1024
    )
    repo.record_api_telemetry(t)
    telemetry_logs = repo.get_api_telemetry()
    assert len(telemetry_logs) == 1
    assert telemetry_logs[0].endpoint == "/products/get"
    assert telemetry_logs[0].latency_ms == 145.2


def test_ai_training_dataset_records(repo):
    item = DarazTrainingDataset(
        id="train_1001",
        product_id="1001",
        title="Wireless Bluetooth ANC Earbuds",
        category="Electronics > Audio",
        brand="SoundCore",
        price=3500.0,
        rating=4.8,
        review_count=350,
        features={"anc": True, "battery_hours": 30},
        quality_score=0.96,
        agent_label="daraz_top_selling_earbuds",
        is_validated=True
    )
    repo.add_training_dataset_item(item)

    items = repo.list_training_dataset(category="Audio")
    assert len(items) == 1
    assert items[0].product_id == "1001"
    assert items[0].quality_score == 0.96


def test_daraz_service_persists_full_product_graph(repo):
    service = DarazService(marketplace_repo=repo)
    
    raw_item = DarazProductItem(
        platform="daraz",
        product_id="778899",
        name="Realme Buds Wireless 3",
        price=4500.0,
        original_price=6000.0,
        discount=25.0,
        rating=4.7,
        review_count=85,
        seller_name="Realme Official Flagship Store",
        seller_id="seller_realme_pk",
        brand="Realme",
        category="Audio & Accessories",
        in_stock=True,
        location="Lahore"
    )

    # Persist via service
    service._persist_products([raw_item])

    # 1. Check product persisted
    prod = repo.get_product("daraz", "778899")
    assert prod is not None
    assert prod.product_name == "Realme Buds Wireless 3"
    assert prod.price == 4500.0

    # 2. Check snapshot persisted
    snaps = repo.get_snapshots("daraz", "778899")
    assert len(snaps) == 1
    assert snaps[0].price == 4500.0

    # 3. Check seller persisted
    seller = repo.get_seller("seller_realme_pk")
    assert seller is not None
    assert seller.seller_name == "Realme Official Flagship Store"

    # 4. Check category persisted
    cat = repo.get_category("audio-&-accessories")
    assert cat is not None
    assert cat.name == "Audio & Accessories"

    # 5. Check training dataset record generated
    training_items = repo.list_training_dataset()
    assert len(training_items) >= 1
    assert any(ti.product_id == "778899" for ti in training_items)


def test_official_provider_telemetry_on_call(repo):
    provider = DarazOfficialProvider(
        app_key="505830",
        app_secret="saqUGC7PGXzq6waTIDjSYLT2TitjwZRX",
        marketplace_repo=repo
    )

    with patch("backend.app.services.daraz.official_provider.requests.post") as mock_post, \
         patch("backend.app.services.daraz.official_provider.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": "0", "data": {"products": []}}
        mock_resp.content = b'{"code": "0"}'
        mock_post.return_value = mock_resp
        mock_get.return_value = mock_resp

        success, data, code, err = provider._execute_api_call("/products/get", {"category_id": "123"}, require_auth=False)
        assert success is True

        # Check telemetry recorded
        telemetry = repo.get_api_telemetry()
        assert len(telemetry) == 1
        assert telemetry[0].endpoint == "/products/get"
        assert telemetry[0].status_code == 200

        # Check quota decremented / tracked
        quota = repo.get_or_create_daily_quota()
        assert quota.requests_used == 1
        assert quota.remaining == 5999999
