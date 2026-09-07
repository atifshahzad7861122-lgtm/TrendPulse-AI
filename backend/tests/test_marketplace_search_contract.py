"""
Phase 1: Canonical Marketplace Search Contract Test Suite.

Verifies domain models, canonical enums, validation rules, provider abstraction,
search limits, lifecycle states, provenance, persistence compatibility,
user context isolation, and strict absence of synthetic/fake data.
"""

import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.scraper.marketplace_search import (
    MarketplaceType,
    MarketplaceSearchStatus,
    SearchProviderName,
    MarketplaceSearchRequest,
    MarketplaceSearchCandidate,
    MarketplaceSearchResult,
    MarketplaceSearchProvider,
    MIN_CANDIDATES,
    DEFAULT_CANDIDATE_TARGET,
    DEFAULT_RESULT_LIMIT,
    MAX_RESULT_LIMIT,
)
from backend.app.models.domain import (
    MarketplaceProduct,
    UnifiedProduct,
    ProductPlatformListing,
    RawScrapedPayload,
)


@pytest.fixture
def client():
    return TestClient(app)


# --------------------------------------------------------------------------
# 1. Valid Daraz request is accepted
# --------------------------------------------------------------------------
def test_valid_daraz_request_accepted():
    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.DARAZ,
        keyword="mechanical keyboard"
    )
    assert req.marketplace == MarketplaceType.DARAZ
    assert req.keyword == "mechanical keyboard"
    assert req.desired_results == DEFAULT_RESULT_LIMIT
    assert req.candidate_target == DEFAULT_CANDIDATE_TARGET


# --------------------------------------------------------------------------
# 2. Valid Amazon request is accepted
# --------------------------------------------------------------------------
def test_valid_amazon_request_accepted():
    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.AMAZON,
        keyword="gaming mouse",
        desired_results=20,
        candidate_target=200
    )
    assert req.marketplace == MarketplaceType.AMAZON
    assert req.keyword == "gaming mouse"
    assert req.desired_results == 20
    assert req.candidate_target == 200


# --------------------------------------------------------------------------
# 3. Valid eBay request is accepted
# --------------------------------------------------------------------------
def test_valid_ebay_request_accepted():
    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.EBAY,
        keyword="vintage jacket",
        desired_results=15,
        candidate_target=220
    )
    assert req.marketplace == MarketplaceType.EBAY
    assert req.keyword == "vintage jacket"
    assert req.desired_results == 15
    assert req.candidate_target == 220


# --------------------------------------------------------------------------
# 4. Valid Shopify request is accepted
# --------------------------------------------------------------------------
def test_valid_shopify_request_accepted():
    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.SHOPIFY,
        keyword="organic skincare",
        desired_results=30,
        candidate_target=250
    )
    assert req.marketplace == MarketplaceType.SHOPIFY
    assert req.keyword == "organic skincare"
    assert req.desired_results == 30
    assert req.candidate_target == 250


# --------------------------------------------------------------------------
# 5. Empty keyword is rejected
# --------------------------------------------------------------------------
def test_empty_keyword_rejected():
    with pytest.raises(ValidationError) as exc_info:
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.DARAZ,
            keyword=""
        )
    assert "keyword" in str(exc_info.value).lower()


# --------------------------------------------------------------------------
# 6. Whitespace-only keyword is rejected
# --------------------------------------------------------------------------
def test_whitespace_only_keyword_rejected():
    with pytest.raises(ValidationError) as exc_info:
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.AMAZON,
            keyword="    \t \n   "
        )
    assert "keyword" in str(exc_info.value).lower()


# --------------------------------------------------------------------------
# 7. Invalid desired_results is rejected
# --------------------------------------------------------------------------
def test_invalid_desired_results_rejected():
    # Negative value
    with pytest.raises(ValidationError):
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.DARAZ,
            keyword="earbuds",
            desired_results=-5
        )

    # Zero value
    with pytest.raises(ValidationError):
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.DARAZ,
            keyword="earbuds",
            desired_results=0
        )


# --------------------------------------------------------------------------
# 8. Invalid candidate_target is rejected
# --------------------------------------------------------------------------
def test_invalid_candidate_target_rejected():
    # Negative candidate target
    with pytest.raises(ValidationError):
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.DARAZ,
            keyword="earbuds",
            desired_results=10,
            candidate_target=-100
        )

    # Zero candidate target
    with pytest.raises(ValidationError):
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.DARAZ,
            keyword="earbuds",
            desired_results=10,
            candidate_target=0
        )


# --------------------------------------------------------------------------
# 9. candidate_target smaller than desired_results is rejected
# --------------------------------------------------------------------------
def test_candidate_target_smaller_than_desired_results_rejected():
    with pytest.raises(ValidationError) as exc_info:
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.EBAY,
            keyword="smart watch",
            desired_results=25,
            candidate_target=10  # Smaller than desired_results!
        )
    assert "candidate_target" in str(exc_info.value).lower()


# --------------------------------------------------------------------------
# 10. Default desired_results is 30
# --------------------------------------------------------------------------
def test_default_desired_results_is_30():
    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.DARAZ,
        keyword="drone"
    )
    assert req.desired_results == 30
    assert req.desired_results == DEFAULT_RESULT_LIMIT


# --------------------------------------------------------------------------
# 11. Default candidate_target is 250
# --------------------------------------------------------------------------
def test_default_candidate_target_is_250():
    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.DARAZ,
        keyword="drone"
    )
    assert req.candidate_target == 250
    assert req.candidate_target == DEFAULT_CANDIDATE_TARGET


# --------------------------------------------------------------------------
# 12. Maximum result limit cannot exceed 30
# --------------------------------------------------------------------------
def test_maximum_result_limit_cannot_exceed_30():
    assert MAX_RESULT_LIMIT == 30
    with pytest.raises(ValidationError) as exc_info:
        MarketplaceSearchRequest(
            marketplace=MarketplaceType.DARAZ,
            keyword="monitor",
            desired_results=31
        )
    assert "max_result_limit" in str(exc_info.value).lower() or "30" in str(exc_info.value)


# --------------------------------------------------------------------------
# 13. Unknown marketplace is rejected
# --------------------------------------------------------------------------
def test_unknown_marketplace_rejected():
    # Arbitrary strings rejected
    with pytest.raises(ValidationError):
        MarketplaceSearchRequest(
            marketplace="unsupported_store",  # type: ignore
            keyword="shoes"
        )

    # Walmart rejected (not in Phase 1 canonical enum)
    with pytest.raises(ValidationError):
        MarketplaceSearchRequest(
            marketplace="walmart",  # type: ignore
            keyword="shoes"
        )


# --------------------------------------------------------------------------
# 14. Optional product fields can remain None
# --------------------------------------------------------------------------
def test_optional_product_fields_can_remain_none():
    candidate = MarketplaceSearchCandidate(
        marketplace=MarketplaceType.DARAZ,
        title="Minimal Product",
        url="https://www.daraz.pk/products/minimal-item.html",
        source_provider="daraz_specialized"
    )
    assert candidate.external_product_id is None
    assert candidate.image_url is None
    assert candidate.price is None
    assert candidate.currency is None
    assert candidate.original_price is None
    assert candidate.seller is None
    assert candidate.brand is None
    assert candidate.category is None
    assert candidate.rating is None
    assert candidate.review_count is None
    assert candidate.availability is None
    assert candidate.description is None
    assert candidate.source_url is None
    assert candidate.raw_payload_reference is None


# --------------------------------------------------------------------------
# 15. No synthetic product values are generated
# --------------------------------------------------------------------------
def test_no_synthetic_product_values_generated():
    # Instantiating candidate must never populate phantom ratings or review counts
    candidate = MarketplaceSearchCandidate(
        marketplace=MarketplaceType.AMAZON,
        title="Authentic Product Test",
        url="https://www.amazon.com/dp/B000TEST",
        source_provider="universal"
    )
    # Price, rating, and review count MUST NOT have fake non-zero defaults
    assert candidate.price is not 0.0
    assert candidate.price is None
    assert candidate.rating is not 5.0
    assert candidate.rating is None
    assert candidate.review_count is not 0
    assert candidate.review_count is None
    assert candidate.seller is None


# --------------------------------------------------------------------------
# 16. Search status only accepts defined lifecycle states
# --------------------------------------------------------------------------
def test_search_status_only_accepts_defined_lifecycle_states():
    valid_states = {"queued", "running", "processing", "completed", "failed", "insufficient_data"}
    enum_states = {s.value for s in MarketplaceSearchStatus}
    assert enum_states == valid_states

    # Active states
    assert MarketplaceSearchStatus.QUEUED.is_active() is True
    assert MarketplaceSearchStatus.RUNNING.is_active() is True
    assert MarketplaceSearchStatus.PROCESSING.is_active() is True
    assert MarketplaceSearchStatus.COMPLETED.is_active() is False

    # Terminal states
    assert MarketplaceSearchStatus.COMPLETED.is_terminal() is True
    assert MarketplaceSearchStatus.FAILED.is_terminal() is True
    assert MarketplaceSearchStatus.INSUFFICIENT_DATA.is_terminal() is True
    assert MarketplaceSearchStatus.RUNNING.is_terminal() is False

    # Unsupported value rejected
    with pytest.raises(ValidationError):
        MarketplaceSearchResult(
            marketplace=MarketplaceType.DARAZ,
            keyword="phone",
            status="partially_ready"  # type: ignore
        )


# --------------------------------------------------------------------------
# 17. Search result correctly preserves candidate_count
# --------------------------------------------------------------------------
def test_search_result_correctly_preserves_candidate_count():
    res = MarketplaceSearchResult(
        marketplace=MarketplaceType.DARAZ,
        keyword="camera",
        candidate_count=237
    )
    assert res.candidate_count == 237


# --------------------------------------------------------------------------
# 18. Search result correctly preserves returned_count
# --------------------------------------------------------------------------
def test_search_result_correctly_preserves_returned_count():
    res = MarketplaceSearchResult(
        marketplace=MarketplaceType.AMAZON,
        keyword="camera lens",
        candidate_count=250,
        normalized_count=240,
        quality_passed_count=210,
        deduplicated_count=180,
        returned_count=30
    )
    assert res.returned_count == 30
    assert res.returned_count <= MAX_RESULT_LIMIT


# --------------------------------------------------------------------------
# 19. Source provider provenance is preserved
# --------------------------------------------------------------------------
def test_source_provider_provenance_is_preserved():
    c1 = MarketplaceSearchCandidate(
        marketplace=MarketplaceType.DARAZ,
        title="Daraz Item",
        url="https://daraz.pk/p1",
        source_provider=SearchProviderName.DARAZ_SPECIALIZED.value
    )
    c2 = MarketplaceSearchCandidate(
        marketplace=MarketplaceType.AMAZON,
        title="Amazon Item",
        url="https://amazon.com/p2",
        source_provider=SearchProviderName.SCRAPEGRAPHAI.value
    )
    assert c1.source_provider == "daraz_specialized"
    assert c2.source_provider == "scrapegraphai"


# --------------------------------------------------------------------------
# 20. Marketplace identity is preserved
# --------------------------------------------------------------------------
def test_marketplace_identity_is_preserved():
    for mp in [MarketplaceType.DARAZ, MarketplaceType.AMAZON, MarketplaceType.EBAY, MarketplaceType.SHOPIFY]:
        candidate = MarketplaceSearchCandidate(
            marketplace=mp,
            title=f"{mp.value} product",
            url=f"https://{mp.value}.com/item",
            source_provider="universal"
        )
        assert candidate.marketplace == mp
        assert candidate.marketplace.value == mp.value


# --------------------------------------------------------------------------
# 21. Search IDs are unique
# --------------------------------------------------------------------------
def test_search_ids_are_unique():
    res1 = MarketplaceSearchResult(
        marketplace=MarketplaceType.DARAZ,
        keyword="laptop"
    )
    res2 = MarketplaceSearchResult(
        marketplace=MarketplaceType.DARAZ,
        keyword="laptop"
    )
    assert res1.search_id != res2.search_id
    assert len(res1.search_id) > 0
    assert len(res2.search_id) > 0


# --------------------------------------------------------------------------
# 22. Four supported marketplaces use the same canonical contract
# --------------------------------------------------------------------------
def test_four_supported_marketplaces_use_same_canonical_contract():
    marketplaces = [
        MarketplaceType.DARAZ,
        MarketplaceType.AMAZON,
        MarketplaceType.EBAY,
        MarketplaceType.SHOPIFY,
    ]
    results = []
    for mp in marketplaces:
        req = MarketplaceSearchRequest(marketplace=mp, keyword="headphones")
        res = MarketplaceSearchResult(
            marketplace=req.marketplace,
            keyword=req.keyword,
            status=MarketplaceSearchStatus.QUEUED
        )
        results.append(res)

    assert len(results) == 4
    for r in results:
        assert isinstance(r, MarketplaceSearchResult)
        assert r.keyword == "headphones"
        assert r.status == MarketplaceSearchStatus.QUEUED


# --------------------------------------------------------------------------
# 23. User/search context does not leak between searches
# --------------------------------------------------------------------------
def test_user_search_context_does_not_leak():
    user_a_id = "user_alpha_123"
    user_b_id = "user_beta_456"

    req_a = MarketplaceSearchRequest(
        marketplace=MarketplaceType.DARAZ,
        keyword="headphones",
        user_id=user_a_id,
        session_id="sess_a"
    )
    req_b = MarketplaceSearchRequest(
        marketplace=MarketplaceType.DARAZ,
        keyword="headphones",
        user_id=user_b_id,
        session_id="sess_b"
    )

    assert req_a.user_id != req_b.user_id
    assert req_a.session_id != req_b.session_id
    assert req_a.user_id == user_a_id
    assert req_b.user_id == user_b_id


# --------------------------------------------------------------------------
# 24. Existing marketplace product models remain compatible
# --------------------------------------------------------------------------
def test_existing_marketplace_product_models_remain_compatible():
    now = datetime.now(timezone.utc)
    mp_prod = MarketplaceProduct(
        id="mp_prod_001",
        platform="daraz",
        product_id="daraz_1001",
        product_name="Wireless Mouse",
        price=1500.0,
        currency="PKR",
        first_seen_at=now,
        last_seen_at=now
    )
    assert mp_prod.product_id == "daraz_1001"
    assert mp_prod.platform == "daraz"

    # Conversion/compatibility check: Candidate can be formed from MarketplaceProduct
    candidate = MarketplaceSearchCandidate(
        external_product_id=mp_prod.product_id,
        marketplace=MarketplaceType.DARAZ,
        title=mp_prod.product_name,
        url=mp_prod.product_url or "https://daraz.pk/p/1001",
        price=mp_prod.price,
        currency=mp_prod.currency,
        source_provider="daraz_specialized",
        observed_at=mp_prod.last_seen_at
    )
    assert candidate.external_product_id == "daraz_1001"
    assert candidate.price == 1500.0


# --------------------------------------------------------------------------
# 25. Candidate model preserves raw payload references
# --------------------------------------------------------------------------
def test_candidate_model_preserves_raw_payload_references():
    raw_ref = {
        "raw_payload_id": "raw_payload_999",
        "scraped_checksum": "sha256:abc123def456",
        "page_number": 1
    }
    candidate = MarketplaceSearchCandidate(
        marketplace=MarketplaceType.EBAY,
        title="Collector Coin",
        url="https://ebay.com/itm/123",
        source_provider="universal",
        raw_payload_reference=raw_ref
    )
    assert candidate.raw_payload_reference is not None
    assert candidate.raw_payload_reference["raw_payload_id"] == "raw_payload_999"


# --------------------------------------------------------------------------
# 26. Candidate model preserves observation timestamps
# --------------------------------------------------------------------------
def test_candidate_model_preserves_observation_timestamps():
    exact_time = datetime(2026, 9, 6, 10, 0, 0, tzinfo=timezone.utc)
    candidate = MarketplaceSearchCandidate(
        marketplace=MarketplaceType.SHOPIFY,
        title="Artisan Soap",
        url="https://soapstore.com/item",
        source_provider="universal",
        observed_at=exact_time
    )
    assert candidate.observed_at == exact_time


# --------------------------------------------------------------------------
# 27. Search result supports insufficient_data state
# --------------------------------------------------------------------------
def test_search_result_supports_insufficient_data_state():
    res = MarketplaceSearchResult(
        marketplace=MarketplaceType.DARAZ,
        keyword="extremely_rare_unobtainable_item_xyz",
        status=MarketplaceSearchStatus.INSUFFICIENT_DATA,
        candidate_count=2,
        normalized_count=0,
        quality_passed_count=0,
        deduplicated_count=0,
        returned_count=0,
        products=[],
        message="Insufficient search candidate volume to meet threshold"
    )
    assert res.status == MarketplaceSearchStatus.INSUFFICIENT_DATA
    assert res.status.is_terminal() is True
    assert len(res.products) == 0


# --------------------------------------------------------------------------
# 28. Search result supports failed state
# --------------------------------------------------------------------------
def test_search_result_supports_failed_state():
    res = MarketplaceSearchResult(
        marketplace=MarketplaceType.AMAZON,
        keyword="server rack",
        status=MarketplaceSearchStatus.FAILED,
        error="Network timeout reaching target marketplace",
        products=[]
    )
    assert res.status == MarketplaceSearchStatus.FAILED
    assert res.status.is_terminal() is True
    assert res.error == "Network timeout reaching target marketplace"


# --------------------------------------------------------------------------
# 29. Search result supports completed state
# --------------------------------------------------------------------------
def test_search_result_supports_completed_state():
    now = datetime.now(timezone.utc)
    res = MarketplaceSearchResult(
        marketplace=MarketplaceType.DARAZ,
        keyword="bluetooth speaker",
        status=MarketplaceSearchStatus.COMPLETED,
        candidate_count=245,
        normalized_count=230,
        quality_passed_count=210,
        deduplicated_count=190,
        returned_count=30,
        completed_at=now
    )
    assert res.status == MarketplaceSearchStatus.COMPLETED
    assert res.status.is_terminal() is True
    assert res.returned_count == 30
    assert res.completed_at == now


# --------------------------------------------------------------------------
# 30. No demo/fake marketplace data is introduced
# --------------------------------------------------------------------------
def test_no_demo_or_fake_marketplace_data_introduced():
    # Empty search response must have zero default products
    res = MarketplaceSearchResult(
        marketplace=MarketplaceType.DARAZ,
        keyword="test query"
    )
    assert res.products == []
    assert res.candidate_count == 0
    assert res.returned_count == 0

    # Request must not contain hardcoded demo products
    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.AMAZON,
        keyword="test query"
    )
    assert hasattr(req, "demo_products") is False


# --------------------------------------------------------------------------
# 31. Provider Abstraction Subclass Compliance
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_provider_abstraction_compliance():
    class MockAmazonProvider(MarketplaceSearchProvider):
        async def search(self, request: MarketplaceSearchRequest):
            return []

        def get_provider_name(self) -> str:
            return "mock_amazon"

        def get_supported_marketplaces(self):
            return [MarketplaceType.AMAZON]

    provider = MockAmazonProvider()
    assert provider.get_provider_name() == "mock_amazon"
    assert provider.get_supported_marketplaces() == [MarketplaceType.AMAZON]

    req = MarketplaceSearchRequest(
        marketplace=MarketplaceType.AMAZON,
        keyword="wireless mouse"
    )
    candidates = await provider.search(req)
    assert candidates == []


# --------------------------------------------------------------------------
# 32. API Endpoint Contract Compliance (POST /api/v1/marketplace-search)
# --------------------------------------------------------------------------
def test_api_endpoint_contract_compliance(client):
    payload = {
        "marketplace": "daraz",
        "keyword": "wireless earbuds",
        "desired_results": 30,
        "candidate_target": 250
    }
    response = client.post("/api/v1/marketplace-search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    search_data = data["data"]
    assert search_data["marketplace"] == "daraz"
    assert search_data["keyword"] == "wireless earbuds"
    assert search_data["status"] == "queued"
    assert search_data["candidate_count"] == 0
    assert search_data["returned_count"] == 0
    assert search_data["products"] == []
    assert "search_id" in search_data
