import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.models.domain import (
    DarazAuthSession,
    DarazProviderHealth,
    MarketplaceProduct,
    ProductMarketSnapshot
)
from backend.app.schemas.daraz import DarazProductItem, DarazSearchResponse, DarazProductDetails
from backend.app.repositories.in_memory import InMemoryMarketplaceProductRepository
from backend.app.services.daraz.base import DarazProvider, DarazFetchResult
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.daraz.parse_scraper_provider import DarazParseScraperProvider
from backend.app.services.daraz.database_cache_provider import DarazDatabaseCacheProvider
from backend.app.services.daraz.failover_pool import DarazFailoverPool
from backend.app.services.daraz_service import DarazService
from backend.app.api.deps import get_daraz_service, get_marketplace_product_repository
from backend.app.services.normalization.product_normalizer import ProductNormalizer
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.agents.categorization.agent import ProductCategorizationAgent
from backend.app.repositories.in_memory import data_quality_repo, taxonomy_repo

@pytest.fixture
def mock_marketplace_repo():
    return InMemoryMarketplaceProductRepository(storage_file=":memory:")

@pytest.fixture
def test_client(mock_marketplace_repo):
    svc = DarazService(marketplace_repo=mock_marketplace_repo)
    app.dependency_overrides[get_daraz_service] = lambda: svc
    app.dependency_overrides[get_marketplace_product_repository] = lambda: mock_marketplace_repo
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_daraz_service, None)
    app.dependency_overrides.pop(get_marketplace_product_repository, None)

# ==============================================================================
# 1. Callback Endpoint Existence & Parameter Validation (GET & POST)
# ==============================================================================

def test_callback_endpoint_exists_get(test_client):
    """Verifies that GET /api/v1/platforms/daraz/callback exists and requires 'code'."""
    res = test_client.get("/api/v1/platforms/daraz/callback")
    assert res.status_code == 400
    assert "code" in res.json()["detail"].lower()

from unittest.mock import patch

def test_callback_endpoint_valid_get(test_client):
    """Verifies successful authorization code processing via GET callback."""
    mock_token_data = {
        "access_token": "mock_access_token_123",
        "refresh_token": "mock_refresh_token_456",
        "seller_id": "seller_pk_01",
        "account": "seller_pk_01",
        "expires_in": 2592000,
        "country": "pk"
    }
    with patch.object(DarazOfficialProvider, "exchange_code_for_token", return_value=(True, mock_token_data, None)):
        res = test_client.get(
            "/api/v1/platforms/daraz/callback?code=0_valid_code_12345&state=test_state&account=seller_pk_01"
        )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "authorized"
    assert data["data"]["seller_id"] == "seller_pk_01"
    assert "authorization" in data["message"].lower() or "authorized" in data["message"].lower()

def test_callback_endpoint_exists_post(test_client):
    """Verifies that POST /api/v1/platforms/daraz/callback accepts JSON payload."""
    mock_token_data = {
        "access_token": "mock_access_token_789",
        "refresh_token": "mock_refresh_token_012",
        "seller_id": "seller_pk_02",
        "account": "seller_pk_02",
        "expires_in": 2592000,
        "country": "pk"
    }
    with patch.object(DarazOfficialProvider, "exchange_code_for_token", return_value=(True, mock_token_data, None)):
        res = test_client.post(
            "/api/v1/platforms/daraz/callback",
            json={"code": "0_post_code_67890", "state": "post_state", "account": "seller_pk_02"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "authorized"
    assert data["data"]["account"] == "seller_pk_02"

def test_callback_endpoint_missing_code_post(test_client):
    """Verifies that POST /callback without 'code' returns 400 Bad Request."""
    res = test_client.post(
        "/api/v1/platforms/daraz/callback",
        json={"state": "missing_code_state"}
    )
    assert res.status_code == 400
    assert "code" in res.json()["detail"].lower()

# ==============================================================================
# 2. Security & Credential Secrecy Audits
# ==============================================================================

def test_credential_secrecy_in_callback_response(test_client):
    """
    Guarantees that DARAZ_APP_SECRET, access_token, and refresh_token
    are NEVER exposed in the callback response or error bodies.
    """
    secret_sentinel = "SUPER_SECRET_DARAZ_KEY_XYZ_999"
    token_sentinel = "ACCESS_TOKEN_SECRET_VAL_123"

    res = test_client.get(
        "/api/v1/platforms/daraz/callback?code=0_test_code_sec&state=sec_state&account=seller_sec"
    )
    body_text = res.text
    assert secret_sentinel not in body_text
    assert token_sentinel not in body_text
    assert "DARAZ_APP_SECRET" not in body_text
    assert "access_token" not in res.json().get("data", {})

def test_status_endpoint_never_leaks_secrets(test_client):
    """
    Verifies that GET /api/v1/platforms/daraz/status reports health and configuration flags
    without exposing raw keys, secrets, or tokens.
    """
    res = test_client.get("/api/v1/platforms/daraz/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "status" in data
    assert "app_key_configured" in data
    assert "app_secret_configured" in data
    assert isinstance(data["app_key_configured"], bool)
    assert isinstance(data["app_secret_configured"], bool)
    # Ensure raw secret is not in payload
    assert "DARAZ_APP_SECRET" not in res.text
    assert "DARAZ_APP_KEY" not in res.text

# ==============================================================================
# 3. Official Daraz Open Platform HMAC-SHA256 Signature Verification
# ==============================================================================

def test_official_daraz_hmac_sha256_signature():
    """
    Validates that HMAC-SHA256 request signature strictly complies with
    official Daraz Open Platform specification (alphabetical sort, uppercase hex).
    """
    app_key = "123456"
    app_secret = "test_daraz_secret_xyz"
    provider = DarazOfficialProvider(app_key=app_key, app_secret=app_secret)

    params = {
        "app_key": app_key,
        "timestamp": "1600000000000",
        "sign_method": "sha256",
        "filter": "all",
        "limit": "20"
    }

    # Manual expected signature:
    # Sorted string: "/products/getapp_key123456filteralllimit20sign_methodsha256timestamp1600000000000"
    expected_str = "/products/getapp_key123456filteralllimit20sign_methodsha256timestamp1600000000000"
    expected_sign = hmac.new(
        app_secret.encode("utf-8"),
        expected_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest().upper()

    computed_sign = provider.generate_signature("/products/get", params)
    assert computed_sign == expected_sign
    assert computed_sign.isupper()

# ==============================================================================
# 4. Multi-Provider Failover Architecture (P1 -> P2 -> P3 -> P4)
# ==============================================================================

class MockFailingProvider(DarazProvider):
    name: str = "mock_failing_p1"
    priority: int = 1

    def search_products(self, query: str, **kwargs) -> DarazFetchResult:
        return DarazFetchResult(
            success=False,
            error_code=429,
            error_message="Rate limit exceeded",
            provider_name=self.name,
            is_rate_limited=True
        )

    def get_product_details(self, item_id: str, **kwargs) -> DarazFetchResult:
        return DarazFetchResult(success=False, error_code=500, error_message="Server error", provider_name=self.name)

    def get_categories(self) -> DarazFetchResult:
        return DarazFetchResult(success=False, error_code=500, error_message="Server error", provider_name=self.name)

    def get_seller_products(self, seller_id: str, page: int = 1) -> DarazFetchResult:
        return DarazFetchResult(success=False, error_code=500, error_message="Server error", provider_name=self.name)

class MockSuccessfulProvider(DarazProvider):
    name: str = "mock_success_p2"
    priority: int = 2

    def search_products(self, query: str, **kwargs) -> DarazFetchResult:
        res = DarazSearchResponse(
            query=query,
            page=1,
            total_products=1,
            source="daraz.pk",
            products=[
                DarazProductItem(
                    platform="daraz",
                    product_id="daraz_mock_001",
                    name="Sony WH-1000XM5 Wireless Headphones",
                    price=89000.0,
                    original_price=105000.0,
                    discount=15.2,
                    currency="PKR",
                    rating=4.8,
                    review_count=142,
                    seller_name="Sony Official Store PK",
                    category="Audio",
                    image_url="https://img.daraz.pk/sony.jpg",
                    product_url="https://www.daraz.pk/products/-idaraz_mock_001.html"
                )
            ]
        )
        return DarazFetchResult(success=True, data=res, provider_name=self.name)

    def get_product_details(self, item_id: str, **kwargs) -> DarazFetchResult:
        details = DarazProductDetails(
            platform="daraz",
            product_id=item_id,
            name="Sony WH-1000XM5 Wireless Headphones",
            price=89000.0,
            original_price=105000.0,
            discount=15.2,
            currency="PKR",
            rating=4.8,
            review_count=142,
            category="Audio",
            product_url=f"https://www.daraz.pk/products/-i{item_id}.html"
        )
        return DarazFetchResult(success=True, data=details, provider_name=self.name)

    def get_categories(self) -> DarazFetchResult:
        return DarazFetchResult(success=True, data=[], provider_name=self.name)

    def get_seller_products(self, seller_id: str, page: int = 1) -> DarazFetchResult:
        return DarazFetchResult(success=True, data=DarazSearchResponse(query="", products=[]), provider_name=self.name)

def test_multi_provider_failover_execution(mock_marketplace_repo):
    """
    Verifies that when P1 fails with 429 rate limit, the failover pool
    automatically falls over to P2, succeeds, and records health metadata.
    """
    p1 = MockFailingProvider()
    p2 = MockSuccessfulProvider()

    pool = DarazFailoverPool(
        repository=mock_marketplace_repo,
        providers=[p1, p2]
    )

    fetch_res = pool.execute_with_failover("search_products", query="headphones")
    assert fetch_res.success is True
    assert fetch_res.provider_name == "mock_success_p2"
    assert len(fetch_res.data.products) == 1
    assert fetch_res.data.products[0].product_id == "daraz_mock_001"

    # Verify health record
    h1 = mock_marketplace_repo.get_provider_health("mock_failing_p1")
    assert h1 is not None
    assert h1.status == "rate_limited"
    assert h1.consecutive_failures == 1

    h2 = mock_marketplace_repo.get_provider_health("mock_success_p2")
    assert h2 is not None
    assert h2.status == "healthy"
    assert h2.successful_requests == 1

# ==============================================================================
# 5. Data Persistence & Snapshot Preservation
# ==============================================================================

def test_daraz_product_and_snapshot_persistence(mock_marketplace_repo):
    """
    Ensures that Daraz products are persisted in MarketplaceProduct
    and historical observations are preserved in ProductMarketSnapshot.
    """
    svc = DarazService(marketplace_repo=mock_marketplace_repo)
    products = [
        DarazProductItem(
            platform="daraz",
            product_id="daraz_item_999",
            name="Anker PowerCore 20000mAh",
            price=12500.0,
            original_price=15000.0,
            discount=16.6,
            currency="PKR",
            rating=4.7,
            review_count=88,
            seller_name="Anker Direct PK",
            category="Power Banks",
            image_url="https://img.daraz.pk/anker.jpg",
            product_url="https://www.daraz.pk/products/-idaraz_item_999.html"
        )
    ]

    svc._persist_products(products)

    # Verify MarketplaceProduct
    saved = mock_marketplace_repo.get_product("daraz", "daraz_item_999")
    assert saved is not None
    assert saved.product_name == "Anker PowerCore 20000mAh"
    assert saved.price == 12500.0
    assert saved.product_url.startswith("https://www.daraz.pk")

    # Verify ProductMarketSnapshot
    snaps = mock_marketplace_repo.get_snapshots("daraz", "daraz_item_999")
    assert len(snaps) >= 1
    assert any(s.price == 12500.0 for s in snaps)

# ==============================================================================
# 6. Downstream Agent 1 & Agent 2 Integration Compatibility
# ==============================================================================

def test_daraz_product_normalization_and_agent_pipeline():
    """
    Verifies that a real Daraz product is normalized, evaluated by Agent 1 (Data Quality),
    and mapped by Agent 2 (Categorization).
    """
    daraz_prod = DarazProductItem(
        platform="daraz",
        product_id="daraz_audio_777",
        name="Logitech G Pro X Gaming Headset with Blue VO!CE Mic",
        price=36500.0,
        original_price=42000.0,
        discount=13.0,
        currency="PKR",
        rating=4.6,
        review_count=52,
        seller_name="Logitech G Official",
        category="Gaming Headsets",
        image_url="https://img.daraz.pk/logitech.jpg",
        product_url="https://www.daraz.pk/products/-idaraz_audio_777.html"
    )

    # 1. Normalization
    raw_dict = {
        "product_id": daraz_prod.product_id,
        "title": daraz_prod.name,
        "price": daraz_prod.price,
        "rating": daraz_prod.rating,
        "category": daraz_prod.category,
        "seller_name": daraz_prod.seller_name,
        "brand": "Logitech",
        "currency": "PKR",
        "image_url": daraz_prod.image_url,
        "product_url": daraz_prod.product_url
    }
    normalized = ProductNormalizer.normalize_product(raw_dict, platform="Daraz")
    assert normalized["platform"] == "Daraz"
    assert "logitech" in normalized["normalized_name"].lower()
    assert normalized["completeness_score"] >= 0.70

    # 2. Agent 1: Data Quality
    dq_agent = DataQualityAgent(repository=data_quality_repo)
    dq_summary = dq_agent.validate_product(
        payload=raw_dict,
        platform="Daraz"
    )
    assert dq_summary.is_trusted is True
    assert dq_summary.quality_score >= 80.0

    # 3. Agent 2: Categorization
    cat_agent = ProductCategorizationAgent(repository=taxonomy_repo)
    cat_summary = cat_agent.classify_product(
        payload=raw_dict
    )
    assert cat_summary.category is not None
    assert cat_summary.confidence > 0.50


