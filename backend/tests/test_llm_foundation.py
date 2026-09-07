import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, ProductMarketSnapshot, LLMUsageRecord, User
)
from backend.app.repositories.in_memory import (
    InMemoryUnifiedProductRepository, InMemoryMarketplaceProductRepository, InMemoryLLMUsageRepository
)
from backend.app.services.llm.provider import (
    LLMRequest, LLMResponse, LLMProvider, LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMInvalidResponseError, LLMException
)
from backend.app.services.llm.providers.mock_provider import MockLLMProvider
from backend.app.services.llm.providers.openai_provider import OpenAIProvider
from backend.app.services.llm.context_builder import ContextBuilder
from backend.app.services.llm.cache import LLMResponseCache, llm_cache
from backend.app.services.llm.service import LLMService
from backend.app.schemas.llm import AIProductAnalysisResponse, DataFreshnessMeta
from backend.app.api.deps import get_current_user, get_unified_repository, get_marketplace_product_repository, get_llm_usage_repository, get_llm_service

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_user():
    return User(
        id="usr_test_999",
        email="analyst@trendpulse.ai",
        hashed_password="hashed_pw_mock_12345",
        full_name="Test Analyst",
        is_active=True,
        is_verified=True,
        role="member",
        workspace_id="ws_test_999"
    )



@pytest.fixture
def test_repos():
    unified_repo = InMemoryUnifiedProductRepository(data_file=None)
    marketplace_repo = InMemoryMarketplaceProductRepository(storage_file=None)
    usage_repo = InMemoryLLMUsageRepository(data_file=None)
    return unified_repo, marketplace_repo, usage_repo


@pytest.fixture
def sample_unified_product(test_repos):
    unified_repo, _, _ = test_repos
    prod = UnifiedProduct(
        id="up_test_earbuds",
        unified_product_id="up_test_earbuds",
        canonical_name="Soundcore by Anker Life P2 Mini Wireless Earbuds",
        normalized_name="soundcore anker life p2 mini wireless earbuds",
        brand="Soundcore",
        category="Audio & Headphones",
        description="A" * 1200,  # Long description to test truncation
        identifiers={"model_number": "A3944", "sku": "A3944Z"},
        platforms=["daraz", "shopify"],
        lowest_price=3400.0,
        highest_price=39.99,
        first_seen_at=datetime.now(timezone.utc) - timedelta(days=5),
        last_seen_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    unified_repo.upsert_unified_product(prod)


    listing_daraz = ProductPlatformListing(
        id="list_daraz_1",
        unified_product_id="up_test_earbuds",
        platform="daraz",
        platform_product_id="daraz_9988",
        product_url="https://daraz.pk/products/9988.html",
        title="Soundcore Life P2 Mini Earbuds",
        normalized_title="soundcore life p2 mini earbuds",
        price=3400.0,
        original_price=4500.0,
        currency="PKR",
        discount_percentage=24.0,
        seller_name="Anker Flagship Store",
        rating=4.8,
        review_count=320,
        available=True,
        source_provider="parse_daraz",
        last_synced_at=datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    unified_repo.upsert_platform_listing(listing_daraz)

    listing_shopify = ProductPlatformListing(
        id="list_shopify_1",
        unified_product_id="up_test_earbuds",
        platform="shopify",
        platform_product_id="shopify_7766",
        store_domain="anker.com",
        product_url="https://anker.com/products/soundcore-p2",
        title="Soundcore Life P2 Mini - Black",
        normalized_title="soundcore life p2 mini black",
        price=39.99,
        original_price=49.99,
        currency="USD",
        discount_percentage=20.0,
        vendor="Soundcore Official",
        rating=4.9,
        review_count=1250,
        available=True,
        source_provider="shopify_scout",
        last_synced_at=datetime.now(timezone.utc) - timedelta(minutes=10)
    )
    unified_repo.upsert_platform_listing(listing_shopify)
    return prod


# -----------------------------------------------------------------------------
# 1. Provider Initialization
# -----------------------------------------------------------------------------
def test_provider_initialization():
    mock_prov = MockLLMProvider(api_key="mock-key", model="mock-model")
    assert mock_prov.api_key == "mock-key"
    assert mock_prov.model == "mock-model"

# -----------------------------------------------------------------------------
# 2. Missing API Key Handling
# -----------------------------------------------------------------------------
def test_missing_api_key():
    openai_prov = OpenAIProvider(api_key="")
    req = LLMRequest(prompt="Hello")
    with pytest.raises(LLMAuthError) as exc_info:
        openai_prov.generate(req)
    assert "missing" in str(exc_info.value).lower()

# -----------------------------------------------------------------------------
# 3. Valid API Configuration
# -----------------------------------------------------------------------------
def test_valid_api_configuration():
    prov = OpenAIProvider(api_key="sk-test-valid-key", model="gpt-4o-mini")
    assert prov.api_key == "sk-test-valid-key"
    assert prov.model == "gpt-4o-mini"
    assert prov.base_url == "https://api.openai.com/v1"

# -----------------------------------------------------------------------------
# 4. Context Building
# -----------------------------------------------------------------------------
def test_context_building(sample_unified_product, test_repos):
    unified_repo, _, _ = test_repos
    listings = unified_repo.list_listings_for_product(sample_unified_product.unified_product_id)
    ctx = ContextBuilder.build_product_context(sample_unified_product, listings)

    assert ctx["unified_product_id"] == "up_test_earbuds"
    assert ctx["canonical_name"] == sample_unified_product.canonical_name
    assert ctx["brand"] == "Soundcore"
    assert len(ctx["platform_listings"]) == 2
    assert ctx["data_freshness"]["data_status"] == "live"

# -----------------------------------------------------------------------------
# 5. Context Size Limits & Truncation
# -----------------------------------------------------------------------------
def test_context_size_limits(sample_unified_product, test_repos):
    unified_repo, _, _ = test_repos
    listings = unified_repo.list_listings_for_product(sample_unified_product.unified_product_id)
    snapshots = [
        ProductMarketSnapshot(
            id=f"snap_{i}",
            product_id="daraz_9988",
            platform="daraz",
            price=3400.0 + i,
            rating=4.8,
            review_count=300 + i,
            observed_at=datetime.now(timezone.utc) - timedelta(hours=i)
        )
        for i in range(25)  # 25 snapshots (should cap at 10)
    ]
    ctx = ContextBuilder.build_product_context(sample_unified_product, listings, snapshots)

    # Description capped
    assert len(ctx["description"]) <= ContextBuilder.MAX_DESCRIPTION_LENGTH + 20
    assert "[truncated]" in ctx["description"]

    # History capped at max 10
    assert len(ctx["recent_snapshot_history"]) == 10

# -----------------------------------------------------------------------------
# 6. Data Freshness Metadata
# -----------------------------------------------------------------------------
def test_data_freshness_metadata():
    # Fresh data (<15m)
    fresh_listings = [
        ProductPlatformListing(
            id="l1", unified_product_id="up_1", platform="daraz", platform_product_id="d1",
            product_url="http://example.com", title="Item", normalized_title="item", price=100.0,
            currency="PKR", source_provider="parse_daraz",
            last_synced_at=datetime.now(timezone.utc) - timedelta(minutes=2)
        )
    ]
    meta_fresh = ContextBuilder.calculate_data_freshness(fresh_listings)
    assert meta_fresh.data_status == "live"
    assert "daraz" in meta_fresh.source_platforms
    assert "parse_daraz" in meta_fresh.source_providers
    assert meta_fresh.data_age_seconds < 300

    # Stale data (>15m)
    stale_listings = [
        ProductPlatformListing(
            id="l2", unified_product_id="up_2", platform="shopify", platform_product_id="s1",
            product_url="http://example.com", title="Item 2", normalized_title="item 2", price=20.0,
            currency="USD", source_provider="shopify_scout",
            last_synced_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
    ]
    meta_stale = ContextBuilder.calculate_data_freshness(stale_listings)
    assert meta_stale.data_status == "cached"
    assert meta_stale.data_age_seconds >= 7200

# -----------------------------------------------------------------------------
# 7. Structured Output Validation
# -----------------------------------------------------------------------------
def test_structured_output_validation(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    service = LLMService(
        unified_repo=unified_repo,
        marketplace_repo=marketplace_repo,
        usage_repo=usage_repo,
        provider=MockLLMProvider()
    )
    res = service.analyze_product(sample_unified_product.unified_product_id)
    assert isinstance(res, AIProductAnalysisResponse)
    assert res.confidence_score > 0.5
    assert len(res.key_signals) > 0
    assert len(res.recommendations) > 0

# -----------------------------------------------------------------------------
# 8. Invalid LLM JSON Handling & Repair
# -----------------------------------------------------------------------------
def test_invalid_llm_json_repair(test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    service = LLMService(unified_repo, marketplace_repo, usage_repo, MockLLMProvider())

    # Test repairing markdown json fence
    raw_markdown = "```json\n{\"summary\": \"Clean result\", \"confidence_score\": 0.92}\n```"
    repaired = service._repair_and_parse_json(raw_markdown)
    assert repaired["summary"] == "Clean result"
    assert repaired["confidence_score"] == 0.92

    # Test fatal corrupt json
    corrupt_text = "This is not JSON at all."
    with pytest.raises(LLMInvalidResponseError):
        service._repair_and_parse_json(corrupt_text)

# -----------------------------------------------------------------------------
# 9. LLM Timeout Handling
# -----------------------------------------------------------------------------
def test_llm_timeout_handling(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    timeout_provider = MockLLMProvider(simulate_error="timeout")
    service = LLMService(unified_repo, marketplace_repo, usage_repo, timeout_provider)

    with pytest.raises(LLMTimeoutError):
        service.analyze_product(sample_unified_product.unified_product_id)

# -----------------------------------------------------------------------------
# 10. LLM Rate Limit Handling
# -----------------------------------------------------------------------------
def test_llm_rate_limit_handling(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    rate_limit_prov = MockLLMProvider(simulate_error="rate_limit")
    service = LLMService(unified_repo, marketplace_repo, usage_repo, rate_limit_prov)

    with pytest.raises(LLMRateLimitError):
        service.analyze_product(sample_unified_product.unified_product_id)

# -----------------------------------------------------------------------------
# 11. Provider Unavailable Handling
# -----------------------------------------------------------------------------
def test_provider_unavailable_handling(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    prov = MagicMock()
    prov.generate.side_effect = LLMException("Upstream server is temporarily unavailable", status_code=502)
    service = LLMService(unified_repo, marketplace_repo, usage_repo, prov)

    with pytest.raises(LLMException) as exc_info:
        service.analyze_product(sample_unified_product.unified_product_id)
    assert exc_info.value.status_code == 502

# -----------------------------------------------------------------------------
# 12. Retry Logic on Transient Errors
# -----------------------------------------------------------------------------
def test_retry_logic_on_transient_errors():
    prov = MagicMock()
    prov.model = "test-model"
    # Fails twice on rate limit, succeeds on 3rd attempt
    prov.generate.side_effect = [
        LLMRateLimitError("429 Too Many Requests"),
        LLMTimeoutError("Request timed out"),
        LLMResponse(
            content='{"summary": "Succeeded on retry"}',
            parsed_json={"summary": "Succeeded on retry"},
            input_tokens=50,
            output_tokens=20,
            total_tokens=70,
            estimated_cost=0.0001,
            latency_ms=120.0,
            model="test-model",
            provider="mock"
        )
    ]
    service = LLMService(MagicMock(), MagicMock(), MagicMock(), prov)
    req = LLMRequest(prompt="Test prompt")
    resp = service._execute_with_retry(req, max_retries=3)

    assert resp.parsed_json["summary"] == "Succeeded on retry"
    assert prov.generate.call_count == 3

# -----------------------------------------------------------------------------
# 13. Permanent Authentication Error (No Retries)
# -----------------------------------------------------------------------------
def test_permanent_auth_error_no_retries():
    prov = MagicMock()
    prov.generate.side_effect = LLMAuthError("Invalid API key")
    service = LLMService(MagicMock(), MagicMock(), MagicMock(), prov)
    req = LLMRequest(prompt="Test prompt")

    with pytest.raises(LLMAuthError):
        service._execute_with_retry(req, max_retries=3)

    # Must immediately abort after 1st attempt
    assert prov.generate.call_count == 1

# -----------------------------------------------------------------------------
# 14. Usage Tracking
# -----------------------------------------------------------------------------
def test_usage_tracking(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    service = LLMService(unified_repo, marketplace_repo, usage_repo, MockLLMProvider())

    service.analyze_product(
        sample_unified_product.unified_product_id,
        user_id="usr_test_1",
        workspace_id="ws_test_1"
    )

    records = usage_repo.list_usage(user_id="usr_test_1")
    assert len(records) == 1
    rec = records[0]
    assert rec.request_type == "product_analysis"
    assert rec.user_id == "usr_test_1"
    assert rec.workspace_id == "ws_test_1"
    assert rec.status == "success"

# -----------------------------------------------------------------------------
# 15. Token Tracking
# -----------------------------------------------------------------------------
def test_token_tracking(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    service = LLMService(unified_repo, marketplace_repo, usage_repo, MockLLMProvider())

    res = service.summarize_product(
        sample_unified_product.unified_product_id,
        user_id="usr_tok_1"
    )

    assert res.tokens_used > 0
    summary = usage_repo.get_summary(user_id="usr_tok_1")
    assert summary["total_tokens"] == res.tokens_used

# -----------------------------------------------------------------------------
# 16. Cost Calculation
# -----------------------------------------------------------------------------
def test_cost_calculation():
    prov = MockLLMProvider()
    cost_gpt4o_mini = prov.calculate_cost("gpt-4o-mini", input_tokens=1000000, output_tokens=1000000)
    # $0.15 + $0.60 = $0.75
    assert cost_gpt4o_mini == 0.75

    cost_claude = prov.calculate_cost("claude-3-5-sonnet", input_tokens=1000000, output_tokens=1000000)
    # $3.00 + $15.00 = $18.00
    assert cost_claude == 18.00

# -----------------------------------------------------------------------------
# 17. Cache Hit
# -----------------------------------------------------------------------------
def test_cache_hit(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    llm_cache.clear()

    mock_prov = MagicMock()
    mock_prov.model = "mock-model"
    mock_prov.generate.return_value = LLMResponse(
        content='{"summary": "First run"}',
        parsed_json={"summary": "First run", "confidence_score": 0.95},
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        estimated_cost=0.0001,
        latency_ms=150.0,
        model="mock-model",
        provider="mock"
    )

    service = LLMService(unified_repo, marketplace_repo, usage_repo, mock_prov)

    # 1st call -> Cache miss
    res1 = service.analyze_product(sample_unified_product.unified_product_id)
    assert res1.is_cached is False
    assert mock_prov.generate.call_count == 1

    # 2nd call -> Cache hit (no new provider generate call)
    res2 = service.analyze_product(sample_unified_product.unified_product_id)
    assert res2.is_cached is True
    assert mock_prov.generate.call_count == 1

# -----------------------------------------------------------------------------
# 18. Cache Invalidation / Force Refresh
# -----------------------------------------------------------------------------
def test_cache_invalidation_force_refresh(sample_unified_product, test_repos):
    unified_repo, marketplace_repo, usage_repo = test_repos
    llm_cache.clear()

    mock_prov = MagicMock()
    mock_prov.model = "mock-model"
    mock_prov.generate.return_value = LLMResponse(
        content='{"summary": "Fresh run"}',
        parsed_json={"summary": "Fresh run", "confidence_score": 0.95},
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        estimated_cost=0.0001,
        latency_ms=150.0,
        model="mock-model",
        provider="mock"
    )

    service = LLMService(unified_repo, marketplace_repo, usage_repo, mock_prov)

    # 1st call
    service.analyze_product(sample_unified_product.unified_product_id)
    assert mock_prov.generate.call_count == 1

    # 2nd call with force_refresh=True -> recomputes
    service.analyze_product(sample_unified_product.unified_product_id, force_refresh=True)
    assert mock_prov.generate.call_count == 2

# -----------------------------------------------------------------------------
# 19. Workspace Authorization
# -----------------------------------------------------------------------------
def test_workspace_authorization(test_repos):
    _, _, usage_repo = test_repos
    usage_repo.clear()
    usage_repo.record_usage(
        LLMUsageRecord(
            id="rec_ws1",
            user_id="usr_1",
            workspace_id="ws_alpha",
            provider="mock",
            model="mock",
            request_type="product_analysis",
            total_tokens=100,
            status="success",
            created_at=datetime.now(timezone.utc)
        )
    )

    usage_repo.record_usage(
        LLMUsageRecord(
            id="rec_ws2",
            user_id="usr_2",
            workspace_id="ws_beta",
            provider="mock",
            model="mock",
            request_type="product_analysis",
            total_tokens=200,
            status="success",
            created_at=datetime.now(timezone.utc)
        )
    )

    # Query for ws_alpha only
    alpha_records = usage_repo.list_usage(workspace_id="ws_alpha")
    assert len(alpha_records) == 1
    assert alpha_records[0].workspace_id == "ws_alpha"

    beta_summary = usage_repo.get_summary(workspace_id="ws_beta")
    assert beta_summary["total_tokens"] == 200

# -----------------------------------------------------------------------------
# 20. No Fabricated Values (Zero-Hallucination)
# -----------------------------------------------------------------------------
def test_no_fabricated_values(test_repos):
    sparse_product = UnifiedProduct(
        id="up_sparse_1",
        unified_product_id="up_sparse_1",
        canonical_name="Unknown Accessory",
        normalized_name="unknown accessory",
        brand=None,
        category=None,
        description=None,
        platforms=[]
    )
    ctx = ContextBuilder.build_product_context(sparse_product, listings=[])
    assert ctx["brand"] == "Unbranded / Independent"
    assert ctx["category"] == "General"
    assert ctx["description"] == "Data unavailable"
    assert ctx["active_listings_count"] == 0

# -----------------------------------------------------------------------------
# 21. Product Analysis Endpoint
# -----------------------------------------------------------------------------
def test_product_analysis_endpoint(sample_unified_product, test_repos, mock_user):
    unified_repo, marketplace_repo, usage_repo = test_repos
    service = LLMService(unified_repo, marketplace_repo, usage_repo, MockLLMProvider())

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_unified_repository] = lambda: unified_repo
    app.dependency_overrides[get_marketplace_product_repository] = lambda: marketplace_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: usage_repo
    app.dependency_overrides[get_llm_service] = lambda: service

    client = TestClient(app)
    try:
        resp = client.post(
            "/api/v1/llm/product-analysis",
            json={"unified_product_id": sample_unified_product.unified_product_id, "force_refresh": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unified_product_id"] == sample_unified_product.unified_product_id
        assert "summary" in data
        assert "confidence_score" in data
        assert data["data_freshness"]["data_status"] == "live"
    finally:
        app.dependency_overrides.clear()

# -----------------------------------------------------------------------------
# 22. Trend Analysis Endpoint
# -----------------------------------------------------------------------------
def test_trend_analysis_endpoint(sample_unified_product, test_repos, mock_user):
    unified_repo, marketplace_repo, usage_repo = test_repos
    service = LLMService(unified_repo, marketplace_repo, usage_repo, MockLLMProvider())

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_unified_repository] = lambda: unified_repo
    app.dependency_overrides[get_marketplace_product_repository] = lambda: marketplace_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: usage_repo
    app.dependency_overrides[get_llm_service] = lambda: service

    client = TestClient(app)
    try:
        resp = client.post(
            "/api/v1/llm/trend-analysis",
            json={"unified_product_id": sample_unified_product.unified_product_id, "force_refresh": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unified_product_id"] == sample_unified_product.unified_product_id
        assert "trend_trajectory" in data
        assert "volatility_risk" in data
        assert "predictive_outlook_30d" in data
    finally:
        app.dependency_overrides.clear()

# -----------------------------------------------------------------------------
# 23. Market Comparison Endpoint
# -----------------------------------------------------------------------------
def test_market_comparison_endpoint(sample_unified_product, test_repos, mock_user):
    unified_repo, marketplace_repo, usage_repo = test_repos
    service = LLMService(unified_repo, marketplace_repo, usage_repo, MockLLMProvider())

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_unified_repository] = lambda: unified_repo
    app.dependency_overrides[get_marketplace_product_repository] = lambda: marketplace_repo
    app.dependency_overrides[get_llm_usage_repository] = lambda: usage_repo
    app.dependency_overrides[get_llm_service] = lambda: service

    client = TestClient(app)
    try:
        resp = client.post(
            "/api/v1/llm/market-comparison",
            json={"unified_product_id": sample_unified_product.unified_product_id, "force_refresh": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unified_product_id"] == sample_unified_product.unified_product_id
        assert "cross_platform_overview" in data
        assert "price_arbitrage_analysis" in data
        assert len(data["platform_comparison_breakdown"]) > 0
    finally:
        app.dependency_overrides.clear()
