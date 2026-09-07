import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.domain import (
    User, ShopifyProduct, ShopifyProductSnapshot, ShopifyProviderHealth, ShopifySyncRun
)
from backend.app.repositories.in_memory import InMemoryShopifyRepository, user_repo
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.services.shopify.base import ShopifyProvider, ShopifyFetchResult
from backend.app.services.shopify.failover_pool import ShopifyFailoverPool
from backend.app.services.shopify.service import ShopifyService

# Mock Providers for controlled unit test scenarios
class MockProvider(ShopifyProvider):
    def __init__(self, name: str, priority: int, display_name: str, behavior: str = "success", error_code: int = 500):
        self.name = name
        self.priority = priority
        self.display_name = display_name
        self.behavior = behavior  # "success", "timeout", "rate_limit", "500_error", "malformed", "empty_valid"
        self.error_code = error_code
        self.call_count = 0

    def validate_store(self, store_domain: str) -> bool:
        return True

    def fetch_products(self, store_domain: str, limit: int = 50, page: int = 1, collection=None) -> ShopifyFetchResult:
        self.call_count += 1
        now = datetime.now(timezone.utc)
        if self.behavior == "success":
            prods = [
                ShopifyProduct(
                    id=f"sp_{store_domain}_101",
                    store_domain=store_domain,
                    product_id="101",
                    title="Seamless Training T-Shirt",
                    handle="seamless-training-tee",
                    product_url=f"https://{store_domain}/products/seamless-training-tee",
                    image_url="https://cdn.shopify.com/s/files/1/01/tshirt.jpg",
                    images=["https://cdn.shopify.com/s/files/1/01/tshirt.jpg"],
                    vendor="GymBrand",
                    product_type="Apparel",
                    category="Apparel",
                    tags=["Fitness", "Tops"],
                    price=38.0,
                    compare_at_price=50.0,
                    discount_percentage=24.0,
                    discount_label="-24%",
                    currency="USD",
                    available=True,
                    rating=4.7,
                    review_count=120,
                    source_provider=self.name,
                    variants_count=3,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_synced_at=now,
                    created_at=now,
                    updated_at=now
                ),
                ShopifyProduct(
                    id=f"sp_{store_domain}_102",
                    store_domain=store_domain,
                    product_id="102",
                    title="Performance Running Shorts",
                    handle="performance-shorts",
                    product_url=f"https://{store_domain}/products/performance-shorts",
                    image_url="https://cdn.shopify.com/s/files/1/01/shorts.jpg",
                    images=["https://cdn.shopify.com/s/files/1/01/shorts.jpg"],
                    vendor="GymBrand",
                    product_type="Apparel",
                    category="Apparel",
                    tags=["Running", "Shorts"],
                    price=45.0,
                    compare_at_price=None,
                    discount_percentage=0.0,
                    currency="USD",
                    available=True,
                    rating=4.9,
                    review_count=85,
                    source_provider=self.name,
                    variants_count=2,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_synced_at=now,
                    created_at=now,
                    updated_at=now
                )
            ]
            return ShopifyFetchResult(
                success=True,
                products=prods,
                total_count=len(prods),
                has_next=False,
                raw_response={"count": 2}
            )
        elif self.behavior == "timeout":
            return ShopifyFetchResult(
                success=False,
                error_code=408,
                error_message="Gateway connection timed out",
                is_timeout=True
            )
        elif self.behavior == "rate_limit":
            return ShopifyFetchResult(
                success=False,
                error_code=429,
                error_message="HTTP 429 Too Many Requests: Upstream rate limit reached",
                is_rate_limited=True
            )
        elif self.behavior == "empty_valid":
            return ShopifyFetchResult(
                success=True,
                products=[],
                total_count=0,
                is_empty_valid=True
            )
        else:
            return ShopifyFetchResult(
                success=False,
                error_code=self.error_code,
                error_message=f"HTTP {self.error_code} Internal Error"
            )

    def fetch_product(self, store_domain: str, product_id_or_handle: str):
        return None

    def health_check(self) -> bool:
        return True


@pytest.fixture
def repo():
    # Fresh in-memory repo without disk load for isolated tests
    r = InMemoryShopifyRepository(store_path="backend/app/data/test_shopify_store.json")
    r._products.clear()
    r._snapshots.clear()
    r._sync_runs.clear()
    r._init_default_providers()
    return r


# 1. Provider 1 Success: P1 called, P2..P5 not called
def test_provider_1_success(repo):
    p1 = MockProvider("shopify_scout", 1, "Shopify Scout", behavior="success")
    p2 = MockProvider("shopscraper", 2, "ShopScraper", behavior="success")
    p3 = MockProvider("shopify_apps_spy", 3, "Apps Spy", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2, p3])

    products, source, is_live, status, attempts, sync_run = pool.execute_sync("gymshark.com")
    
    assert status == "success"
    assert is_live is True
    assert source == "shopify_scout"
    assert len(products) == 2
    assert p1.call_count == 1
    assert p2.call_count == 0  # Not called
    assert p3.call_count == 0  # Not called
    assert len(attempts) == 1
    assert attempts[0]["status"] == "success"


# 2. Provider 1 Timeout -> Provider 2 Success
def test_provider_1_timeout_failover_to_provider_2(repo):
    p1 = MockProvider("shopify_scout", 1, "Shopify Scout", behavior="timeout")
    p2 = MockProvider("shopscraper", 2, "ShopScraper", behavior="success")
    p3 = MockProvider("shopify_apps_spy", 3, "Apps Spy", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2, p3])

    products, source, is_live, status, attempts, sync_run = pool.execute_sync("gymshark.com")

    assert status == "success"
    assert is_live is True
    assert source == "shopscraper"
    assert len(products) == 2
    assert p1.call_count == 1
    assert p2.call_count == 1
    assert p3.call_count == 0
    assert len(attempts) == 2
    assert attempts[0]["status"] == "failed"
    assert attempts[1]["status"] == "success"

    # Health check for P1 and P2
    h1 = repo.get_provider_health("shopify_scout")
    assert h1.consecutive_failures == 1
    assert h1.failed_requests == 1
    assert h1.cooldown_until is not None

    h2 = repo.get_provider_health("shopscraper")
    assert h2.consecutive_failures == 0
    assert h2.successful_requests == 1


# 3. Provider 1 HTTP 429 -> Provider 2 Success with Backoff Cooldown
def test_provider_1_rate_limit_failover(repo):
    p1 = MockProvider("shopify_scout", 1, "Shopify Scout", behavior="rate_limit")
    p2 = MockProvider("shopscraper", 2, "ShopScraper", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2])

    products, source, is_live, status, attempts, sync_run = pool.execute_sync("gymshark.com")

    assert status == "success"
    assert source == "shopscraper"
    assert p1.call_count == 1
    assert p2.call_count == 1

    h1 = repo.get_provider_health("shopify_scout")
    assert h1.status == "rate_limited"
    assert h1.rate_limited_requests == 1
    assert h1.cooldown_until is not None


# 4. Providers 1 & 2 Fail -> Provider 3 Success
def test_providers_1_and_2_fail_provider_3_success(repo):
    p1 = MockProvider("shopify_scout", 1, "Shopify Scout", behavior="500_error", error_code=500)
    p2 = MockProvider("shopscraper", 2, "ShopScraper", behavior="500_error", error_code=502)
    p3 = MockProvider("shopify_apps_spy", 3, "Apps Spy", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2, p3])

    products, source, is_live, status, attempts, sync_run = pool.execute_sync("gymshark.com")

    assert status == "success"
    assert source == "shopify_apps_spy"
    assert p1.call_count == 1
    assert p2.call_count == 1
    assert p3.call_count == 1
    assert len(attempts) == 3


# 5. Providers 1..4 Fail -> Provider 5 Success
def test_providers_1_to_4_fail_provider_5_success(repo):
    p1 = MockProvider("shopify_scout", 1, "P1", behavior="timeout")
    p2 = MockProvider("shopscraper", 2, "P2", behavior="rate_limit")
    p3 = MockProvider("shopify_apps_spy", 3, "P3", behavior="500_error", error_code=503)
    p4 = MockProvider("xtracto", 4, "P4", behavior="500_error", error_code=504)
    p5 = MockProvider("bornoo", 5, "P5", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2, p3, p4, p5])

    products, source, is_live, status, attempts, sync_run = pool.execute_sync("allbirds.com")

    assert status == "success"
    assert source == "bornoo"
    assert p5.call_count == 1
    assert len(attempts) == 5


# 6. All Providers Fail -> Database Cache Fallback
def test_all_providers_fail_database_cache_fallback(repo):
    # Pre-seed cached product
    now = datetime.now(timezone.utc) - timedelta(minutes=10)
    cached_p = ShopifyProduct(
        id="sp_gymshark.com_999",
        store_domain="gymshark.com",
        product_id="999",
        title="Vital Seamless Leggings",
        handle="vital-seamless-leggings",
        product_url="https://gymshark.com/products/vital-seamless-leggings",
        price=54.0,
        currency="USD",
        available=True,
        source_provider="shopify_scout",
        first_seen_at=now,
        last_seen_at=now,
        last_synced_at=now,
        created_at=now,
        updated_at=now
    )
    repo.upsert_product(cached_p)

    p1 = MockProvider("shopify_scout", 1, "P1", behavior="500_error")
    p2 = MockProvider("shopscraper", 2, "P2", behavior="rate_limit")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2])

    products, source, is_live, status, attempts, sync_run = pool.execute_sync("gymshark.com")

    assert status == "cached"
    assert is_live is False
    assert source == "database_cache"
    assert len(products) == 1
    assert products[0].product_id == "999"
    assert sync_run.status == "cached"


# 7. All Providers Fail & Database Empty -> Honest Unavailable State
def test_all_providers_fail_and_database_empty(repo):
    p1 = MockProvider("shopify_scout", 1, "P1", behavior="500_error")
    p2 = MockProvider("shopscraper", 2, "P2", behavior="500_error")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2])

    products, source, is_live, status, attempts, sync_run = pool.execute_sync("unknownstore.com")

    assert status == "unavailable"
    assert is_live is False
    assert source == "none"
    assert products == []
    assert sync_run.status == "unavailable"


# 8. Provider Recovery After Cooldown
def test_provider_recovery_after_cooldown_expires(repo):
    p1 = MockProvider("shopify_scout", 1, "Shopify Scout", behavior="500_error")
    p2 = MockProvider("shopscraper", 2, "ShopScraper", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1, p2])

    # First sync: P1 fails, P2 succeeds -> P1 enters cooldown
    pool.execute_sync("gymshark.com")
    h1 = repo.get_provider_health("shopify_scout")
    assert h1.consecutive_failures == 1
    assert h1.cooldown_until is not None

    # Immediate second sync: P1 skipped due to cooldown, P2 called directly
    p1.call_count = 0
    p2.call_count = 0
    pool.execute_sync("gymshark.com")
    assert p1.call_count == 0  # Skipped because cooldown is active
    assert p2.call_count == 1

    # Simulate cooldown expiry (set cooldown_until in the past)
    h1.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    repo.update_provider_health(h1)

    # Now make P1 healthy/succeeding
    p1.behavior = "success"
    p1.call_count = 0
    p2.call_count = 0

    # Third sync: P1 cooldown expired -> P1 is tried first again and succeeds!
    products, source, is_live, status, attempts, sync_run = pool.execute_sync("gymshark.com")
    assert source == "shopify_scout"
    assert p1.call_count == 1
    assert p2.call_count == 0  # P2 not called! Automatic recovery verified!

    h1_after = repo.get_provider_health("shopify_scout")
    assert h1_after.status == "healthy"
    assert h1_after.consecutive_failures == 0


# 9. Product UPSERT & First Seen Preservation
def test_product_upsert_preserves_first_seen_and_updates_price(repo):
    p1 = MockProvider("shopify_scout", 1, "P1", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1])

    # Initial sync
    t0 = datetime.now(timezone.utc) - timedelta(days=2)
    p_initial = ShopifyProduct(
        id="sp_gymshark.com_101",
        store_domain="gymshark.com",
        product_id="101",
        title="Seamless Training T-Shirt",
        product_url="https://gymshark.com/products/seamless-training-tee",
        price=30.0,
        currency="USD",
        source_provider="shopify_scout",
        first_seen_at=t0,
        last_seen_at=t0,
        last_synced_at=t0,
        created_at=t0,
        updated_at=t0
    )
    repo.upsert_product(p_initial)

    # Re-sync with new price ($38.0)
    products, source, is_live, status, attempts, sync_run = pool.execute_sync("gymshark.com")

    updated_p = repo.get_product("gymshark.com", "101")
    assert updated_p is not None
    assert updated_p.price == 38.0
    assert updated_p.first_seen_at == t0  # Preserved!
    assert updated_p.last_synced_at > t0   # Updated!
    assert sync_run.products_updated == 1
    assert sync_run.products_inserted == 1  # 102 was new


# 10. Historical Snapshot Recording
def test_historical_snapshot_creation(repo):
    p1 = MockProvider("shopify_scout", 1, "P1", behavior="success")
    pool = ShopifyFailoverPool(repository=repo, providers=[p1])

    pool.execute_sync("gymshark.com")
    pool.execute_sync("gymshark.com")

    snaps = repo.get_snapshots("gymshark.com", "101")
    assert len(snaps) == 2
    assert snaps[0].price == 38.0
    assert snaps[0].source_provider == "shopify_scout"


# 11. End-to-End API Router Verification
def test_shopify_api_endpoints():
    test_user = User(
        id="usr_shopify_test_01",
        email="shopify_tester@trendpulse.ai",
        full_name="Shopify Tester",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True
    )
    user_repo.create(test_user)
    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    client = TestClient(app)
    
    # Status endpoint
    status_resp = client.get("/api/v1/platforms/shopify/status", headers=headers)
    assert status_resp.status_code == 200
    data = status_resp.json()["data"]
    assert "overall_status" in data
    assert len(data["providers"]) == 5

    # Sync endpoint with dummy domain
    sync_resp = client.post("/api/v1/platforms/shopify/sync", json={
        "store_domain": "gymshark.com",
        "limit": 10
    }, headers=headers)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()["data"]
    assert sync_data["store_domain"] == "gymshark.com"
    assert "source_provider" in sync_data

    # Products listing endpoint
    prod_resp = client.get("/api/v1/platforms/shopify/products?store_domain=gymshark.com", headers=headers)
    assert prod_resp.status_code == 200
    prods_data = prod_resp.json()["data"]
    assert "items" in prods_data
    assert "source_platform" in prods_data
    assert prods_data["source_platform"] == "Shopify"
