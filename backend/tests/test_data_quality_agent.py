import pytest
from datetime import datetime, timezone, timedelta

from backend.app.models.domain import DataQualityValidationResult, AIAgentRun, AIAgentMemory
from backend.app.repositories.in_memory import InMemoryDataQualityRepository, InMemoryUnifiedProductRepository
from backend.app.services.agents.data_quality.rules_engine import DataQualityRulesEngine
from backend.app.services.agents.data_quality.scorer import DataQualityScorer
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.agents.data_quality.memory_manager import DataQualityMemoryManager
from backend.app.services.agents.data_quality.llm_resolver import DataQualityLLMResolver
from backend.app.services.llm.providers.mock_provider import MockLLMProvider
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService

@pytest.fixture
def repo():
    return InMemoryDataQualityRepository(data_file=":memory:")

@pytest.fixture
def mock_llm():
    return MockLLMProvider()

@pytest.fixture
def dq_agent(repo, mock_llm):
    return DataQualityAgent(
        repository=repo,
        llm_provider=mock_llm,
        staleness_days=30
    )

class TestDataQualityRulesEngine:
    def test_clean_valid_product(self):
        engine = DataQualityRulesEngine()
        payload = {
            "product_id": "DARAZ_1001",
            "title": "Anker Soundcore Life P2 True Wireless Earbuds",
            "brand": "Anker",
            "price": 6499.0,
            "currency": "PKR",
            "rating": 4.8,
            "review_count": 215,
            "product_url": "https://www.daraz.pk/products/anker-p2-i1001.html",
            "image_url": "https://img.daraz.pk/images/anker-p2.jpg",
            "category": "Audio & Headphones",
            "platform": "Daraz",
            "source_provider": "daraz_official"
        }
        issues, warnings, scores, needs_llm, _ = engine.evaluate(payload)
        assert len(issues) == 0
        assert len(warnings) == 0
        assert scores["price"] == 1.0
        assert scores["rating"] == 1.0

    def test_impossible_negative_price(self):
        engine = DataQualityRulesEngine()
        payload = {
            "product_id": "DARAZ_1002",
            "title": "Test Gaming Mouse RGB",
            "price": -150.0,
            "currency": "PKR",
            "product_url": "https://www.daraz.pk/products/mouse-i1002.html"
        }
        issues, warnings, scores, needs_llm, _ = engine.evaluate(payload)
        assert any(i.rule_name == "impossible_negative_or_zero_price" for i in issues)
        assert scores["price"] == 0.0

    def test_impossible_rating_and_negative_reviews(self):
        engine = DataQualityRulesEngine()
        payload = {
            "product_id": "DARAZ_1003",
            "title": "Overclocked GPU Cooler",
            "price": 4500.0,
            "currency": "PKR",
            "rating": 9.5,  # > 5.0
            "review_count": -5,  # < 0
            "product_url": "https://www.daraz.pk/products/gpu-i1003.html"
        }
        issues, warnings, scores, needs_llm, _ = engine.evaluate(payload)
        assert any(i.rule_name == "impossible_rating_range" for i in issues)
        assert any(i.rule_name == "impossible_negative_review_count" for i in issues)
        assert scores["rating"] == 0.0
        assert scores["reviews"] == 0.0

    def test_missing_mandatory_title_and_id(self):
        engine = DataQualityRulesEngine()
        payload = {
            "product_id": "",
            "title": "   ",
            "price": 100.0,
            "currency": "USD"
        }
        issues, warnings, scores, _, _ = engine.evaluate(payload)
        assert any(i.rule_name == "mandatory_product_id" for i in issues)
        assert any(i.rule_name == "mandatory_title" for i in issues)

    def test_stale_data_detection(self):
        engine = DataQualityRulesEngine(staleness_days=30)
        old_date = datetime.now(timezone.utc) - timedelta(days=45)
        payload = {
            "product_id": "SHOP_501",
            "title": "Vintage Leather Wallet",
            "price": 25.0,
            "currency": "USD",
            "product_url": "https://store.myshopify.com/products/wallet",
            "observed_at": old_date.isoformat()
        }
        issues, warnings, scores, _, _ = engine.evaluate(payload)
        assert any(w.rule_name == "stale_marketplace_data" for w in warnings)
        assert scores["freshness"] < 1.0


class TestDataQualityScorer:
    def test_clean_score(self):
        score, classification, is_trusted = DataQualityScorer.calculate_score([], [], {})
        assert score == 100.0
        assert classification == "valid"
        assert is_trusted is True

    def test_rejected_score_on_critical_issues(self):
        from backend.app.models.domain import DataQualityRuleViolation
        issues = [
            DataQualityRuleViolation(
                field="price",
                rule_name="impossible_negative_or_zero_price",
                severity="critical",
                message="Impossible price",
                penalty_score=40.0
            ),
            DataQualityRuleViolation(
                field="title",
                rule_name="mandatory_title",
                severity="critical",
                message="Missing title",
                penalty_score=35.0
            )
        ]
        score, classification, is_trusted = DataQualityScorer.calculate_score(issues, [], {})
        assert score <= 25.0
        assert classification == "rejected"
        assert is_trusted is False


class TestDataQualityAgent:
    def test_validate_clean_product(self, dq_agent):
        payload = {
            "product_id": "DARAZ_PROD_1",
            "title": "Sony WH-1000XM5 Noise Cancelling Headphones",
            "brand": "Sony",
            "price": 85000.0,
            "currency": "PKR",
            "rating": 4.9,
            "review_count": 89,
            "product_url": "https://www.daraz.pk/products/sony-xm5.html",
            "image_url": "https://img.daraz.pk/sony.jpg",
            "category": "Headphones"
        }
        res = dq_agent.validate_product(payload, platform="Daraz", source_provider="daraz_official")
        assert res.overall_score >= 90.0
        assert res.classification == "valid"
        assert res.is_trusted is True
        assert len(res.issues) == 0

    def test_validate_rejected_product(self, dq_agent):
        payload = {
            "product_id": "DARAZ_BAD_1",
            "title": "",
            "price": -50.0,
            "currency": "XYZ_INVALID",
            "rating": 12.0
        }
        res = dq_agent.validate_product(payload, platform="Daraz", source_provider="daraz_official")
        assert res.classification == "rejected"
        assert res.is_trusted is False
        assert res.overall_score < 50.0
        assert len(res.issues) >= 3

    def test_validate_batch_audited_run(self, dq_agent):
        batch = [
            {
                "product_id": f"P_{i}",
                "title": f"Valid Product Model {i} With Headphones",
                "brand": "SoundCorp",
                "price": 100.0 + i,
                "currency": "USD",
                "product_url": f"https://example.com/p/{i}",
                "image_url": f"https://example.com/img/{i}.jpg",
                "category": "Electronics"
            }
            for i in range(5)
        ]
        batch.append({
            "product_id": "P_FAIL",
            "title": "",
            "price": -10.0,
            "currency": "USD"
        })

        run, results = dq_agent.validate_batch(batch, platform="Daraz", source_provider="daraz_stream")
        assert run.items_processed == 6
        assert run.items_valid == 5
        assert run.items_rejected == 1
        assert run.status == "completed"


    def test_memory_learning(self, dq_agent):
        payload = {
            "product_id": "SHOP_MEM_1",
            "title": "Ergonomic Office Chair Mesh",
            "price": 199.0,
            "currency": "USD",
            "brand": "",  # missing brand
            "product_url": "https://store.myshopify.com/products/chair"
        }
        dq_agent.validate_product(payload, platform="Shopify", source_provider="shopify_scout")

        patterns = dq_agent.memory_manager.get_learned_patterns()
        assert len(patterns) >= 1
        rel_mem = next((m for m in patterns if m.memory_type == "reliability_score"), None)
        assert rel_mem is not None
        assert rel_mem.memory_value["provider"] == "shopify_scout"


class TestUnifiedIntelligenceDataQualityGate:
    def test_gate_blocks_rejected_listings(self, repo, mock_llm):
        unified_repo = InMemoryUnifiedProductRepository(data_file=":memory:")
        dq_agent = DataQualityAgent(repository=repo, llm_provider=mock_llm)
        service = UnifiedProductIntelligenceService(
            unified_repo=unified_repo,
            data_quality_agent=dq_agent
        )

        # Ingest invalid product (negative price & missing title)
        u_prod, listing, decision = service.match_and_upsert_listing(
            platform="Daraz",
            platform_product_id="BAD_101",
            title="",
            price=-100.0,
            product_url="https://www.daraz.pk/invalid"
        )
        assert u_prod is None
        assert listing is None
        assert decision.method == "data_quality_rejected"

        # Catalog remains empty
        assert len(unified_repo.list_unified_products()) == 0

    def test_gate_admits_valid_listings_with_quality_score(self, repo, mock_llm):
        unified_repo = InMemoryUnifiedProductRepository(data_file=":memory:")
        dq_agent = DataQualityAgent(repository=repo, llm_provider=mock_llm)
        service = UnifiedProductIntelligenceService(
            unified_repo=unified_repo,
            data_quality_agent=dq_agent
        )

        # Ingest clean product
        u_prod, listing, decision = service.match_and_upsert_listing(
            platform="Daraz",
            platform_product_id="CLEAN_202",
            title="Logitech MX Master 3S Wireless Mouse",
            price=28500.0,
            currency="PKR",
            product_url="https://www.daraz.pk/products/mx3s.html",
            image_url="https://img.daraz.pk/mx3s.jpg",
            category="Computers & Accessories"
        )
        assert u_prod is not None
        assert listing is not None
        assert listing.completeness_score >= 0.9
        assert len(unified_repo.list_unified_products()) == 1
