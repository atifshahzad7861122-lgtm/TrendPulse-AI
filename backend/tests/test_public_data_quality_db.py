import pytest
from datetime import datetime, timezone
from backend.app.services.agents.data_quality import DataQualityAgent
from backend.app.services.agents.data_quality.rules_engine import DataQualityRulesEngine
from backend.app.services.agents.data_quality.scorer import DataQualityScorer
from backend.app.services.agents.data_quality.llm_resolver import DataQualityLLMResolver
from backend.app.services.agents.data_quality.memory_manager import DataQualityMemoryManager
from backend.app.repositories.in_memory import (
    InMemoryDataQualityRepository,
    InMemoryUnifiedProductRepository
)
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
from backend.app.models.domain import DataQualityValidationResult, PublicDataQualityItem


@pytest.fixture
def dq_repo():
    repo = InMemoryDataQualityRepository()
    repo.clear()
    return repo


@pytest.fixture
def agent(dq_repo):
    return DataQualityAgent(
        repository=dq_repo,
        llm_provider=None
    )




@pytest.fixture
def unified_service(dq_repo, agent):
    unified_repo = InMemoryUnifiedProductRepository()
    unified_repo.clear()
    return UnifiedProductIntelligenceService(
        unified_repo=unified_repo,
        data_quality_agent=agent
    )


def test_1_rejected_product_persists(agent, dq_repo):
    """1. Test that a rejected product is permanently saved in data_quality_validation_results."""
    payload = {
        "product_id": "REJ_001",
        "title": "Abusive spam keyword product",
        "price": -50.0,  # Negative price -> Rejected
        "category": "Electronics"
    }
    result = agent.validate_product(payload=payload, platform="daraz", save_result=True)
    assert result.classification == "rejected"
    assert result.is_trusted is False
    assert result.data_quality_category == "Data Quality Issues"

    # Verify persisted in repository
    saved = dq_repo.get_validation_result(result.id)
    assert saved is not None
    assert saved.id == result.id
    assert saved.classification == "rejected"
    assert len(saved.rejection_reasons) > 0


def test_2_negative_price_product_persists(agent, dq_repo):
    """2. Test that a negative-price product is caught, rejected, and persisted."""
    payload = {
        "product_id": "NEG_PRICE_99",
        "title": "USB Cable 1M",
        "price": -199.99,
        "currency": "PKR",
        "category": "Cables"
    }
    result = agent.validate_product(payload=payload, platform="daraz", save_result=True)
    assert result.classification == "rejected"
    assert any("negative" in iss.rule_name for iss in result.issues)
    assert "price" in result.invalid_fields

    saved = dq_repo.get_validation_result(result.id)
    assert saved is not None
    assert saved.price == -199.99
    assert saved.data_quality_category == "Data Quality Issues"


def test_3_invalid_rating_product_persists(agent, dq_repo):
    """3. Test that a product with an impossible rating (> 5.0) is flagged and persisted."""
    payload = {
        "product_id": "FAKE_RATING_101",
        "title": "Wireless Mouse",
        "price": 1200.0,
        "rating": 9.5,  # Impossible rating
        "category": "Accessories"
    }
    result = agent.validate_product(payload=payload, platform="shopify", save_result=True)
    assert any("impossible_rating_range" in iss.rule_name for iss in result.issues)
    assert "rating" in result.invalid_fields

    saved = dq_repo.get_validation_result(result.id)
    assert saved is not None
    assert saved.rating == 9.5



def test_4_missing_field_product_persists(agent, dq_repo):
    """4. Test that a product with missing mandatory product_id is rejected and persisted."""
    payload = {
        "title": "Unidentified Bluetooth Speaker",
        "price": 3500.0,
        "category": "Audio"
    }
    result = agent.validate_product(payload=payload, platform="daraz", save_result=True)
    assert result.classification == "rejected"
    assert any("mandatory_product_id" in iss.rule_name for iss in result.issues)
    assert "product_id" in result.missing_fields

    saved = dq_repo.get_validation_result(result.id)
    assert saved is not None
    assert saved.classification == "rejected"


def test_5_category_is_preserved(agent, dq_repo):
    """5. Test that original marketplace category is preserved cleanly."""
    payload = {
        "product_id": "CAT_PRESERVE_1",
        "title": "Mechanical Keyboard RGB",
        "price": 8500.0,
        "category": "Gaming Keyboards & Mice"
    }
    result = agent.validate_product(payload=payload, platform="daraz", save_result=True)
    assert result.original_category == "Gaming Keyboards & Mice"
    assert result.normalized_category == "Gaming Keyboards & Mice"

    saved = dq_repo.get_validation_result(result.id)
    assert saved.original_category == "Gaming Keyboards & Mice"
    assert saved.normalized_category == "Gaming Keyboards & Mice"


def test_6_missing_category_becomes_unknown(agent, dq_repo):
    """6. Test that missing category defaults to 'Unknown' and is never hallucinated/invented."""
    payload = {
        "product_id": "NO_CAT_77",
        "title": "Standard Mystery Item 100",
        "price": 500.0
        # No category provided
    }
    result = agent.validate_product(payload=payload, platform="daraz", save_result=True)
    assert result.original_category is None
    assert result.normalized_category == "Unknown"

    saved = dq_repo.get_validation_result(result.id)
    assert saved.normalized_category == "Unknown"


def test_7_revalidation_creates_a_new_record(agent, dq_repo):
    """7. Test that validating the same product twice creates two independent records with unique IDs."""
    payload = {
        "product_id": "REVAL_PROD_1",
        "title": "Smart Watch Pro",
        "price": -100.0,  # First attempt: rejected
        "category": "Wearables"
    }
    res1 = agent.validate_product(payload=payload, platform="daraz", save_result=True)
    assert res1.classification == "rejected"

    # Second attempt: fixed price
    payload_fixed = {
        "product_id": "REVAL_PROD_1",
        "title": "Smart Watch Pro",
        "price": 4500.0,
        "category": "Wearables"
    }
    res2 = agent.validate_product(payload=payload_fixed, platform="daraz", save_result=True)

    # Must be distinct records
    assert res1.id != res2.id
    assert dq_repo.count_validation_results() == 2


def test_8_previous_rejection_remains_in_history(agent, dq_repo):
    """8. Test that audit history query returns both the prior rejection and the subsequent successful validation."""
    payload_bad = {
        "product_id": "HIST_PROD_50",
        "title": "Portable Charger 10000mAh",
        "price": -250.0,
        "category": "Power Banks"
    }
    res1 = agent.validate_product(payload=payload_bad, platform="daraz", save_result=True)

    payload_good = {
        "product_id": "HIST_PROD_50",
        "title": "Portable Charger 10000mAh",
        "price": 2500.0,
        "category": "Power Banks"
    }
    res2 = agent.validate_product(payload=payload_good, platform="daraz", save_result=True)

    history = dq_repo.get_product_validation_history(platform="daraz", platform_product_id="HIST_PROD_50")
    assert len(history) == 2
    # Latest attempt is first
    assert history[0].id == res2.id
    assert history[0].classification in ["valid", "valid_with_warnings"]
    # Previous rejection is preserved in history
    assert history[1].id == res1.id
    assert history[1].classification == "rejected"


def test_9_public_read_model_does_not_expose_sensitive_fields(agent, dq_repo):
    """9. Test that public feed items only expose safe public fields without private system data."""
    payload = {
        "product_id": "PUB_READ_01",
        "title": "Gaming Headset 7.1",
        "price": -999.0,
        "category": "Audio"
    }
    agent.validate_product(payload=payload, platform="daraz", save_result=True)

    items, total = dq_repo.get_public_feed(classification="rejected")
    assert total >= 1
    pub_item = items[0]

    assert isinstance(pub_item, PublicDataQualityItem)
    assert pub_item.product_name == "Gaming Headset 7.1"
    assert pub_item.public_status == "Rejected By Data Quality Checks"
    assert pub_item.data_quality_category == "Data Quality Issues"

    # Verify forbidden sensitive attributes do not exist on PublicDataQualityItem model
    assert not hasattr(pub_item, "workspace_id")
    assert not hasattr(pub_item, "raw_payload")
    assert not hasattr(pub_item, "llm_credentials")
    assert not hasattr(pub_item, "memory_id")
    assert not hasattr(pub_item, "internal_error_trace")


def test_10_trusted_catalog_remains_free_of_rejected_products(agent, dq_repo, unified_service):
    """10. Test that the Unified Product Intelligence gate halts rejected products from entering unified_products."""
    unified_prod, listing, decision = unified_service.match_and_upsert_listing(
        platform="daraz",
        platform_product_id="REJ_CATALOG_CHECK_99",
        title="Broken Price Product",
        price=-1500.0,
        product_url="https://daraz.pk/p/99",
        category="Electronics",
        source_provider="daraz_official"
    )

    # Gate must block catalog creation
    assert unified_prod is None
    assert listing is None
    assert decision.method == "data_quality_rejected"
    assert decision.is_match is False

    # Verify rejected record WAS saved to validation history
    history = dq_repo.get_product_validation_history(platform="daraz", platform_product_id="REJ_CATALOG_CHECK_99")
    assert len(history) == 1
    assert history[0].classification == "rejected"

    # Verify trusted unified catalog is completely empty
    all_trusted = unified_service.unified_repo.list_unified_products()
    assert len(all_trusted) == 0

