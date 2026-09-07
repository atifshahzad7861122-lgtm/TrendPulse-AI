import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from backend.app.models.domain import (
    AIAgentMemory, AIAgentMemoryEvent, ProductTaxonomyAssignment, ProductTaxonomyCandidate,
    TaxonomyCategory, UnifiedProduct
)
from backend.app.repositories.in_memory import (
    InMemoryTaxonomyRepository, InMemoryLLMUsageRepository, InMemoryUnifiedProductRepository
)
from backend.app.services.agents.categorization.rules_engine import DeterministicTaxonomyEngine
from backend.app.services.agents.categorization.memory_manager import CategorizationMemoryManager
from backend.app.services.agents.categorization.llm_resolver import CategorizationLLMResolver
from backend.app.services.agents.categorization.agent import ProductCategorizationAgent
from backend.app.services.llm.provider import LLMResponse, LLMProvider
from backend.app.api.deps import get_taxonomy_repository, get_categorization_agent, get_unified_repository
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def tax_repo():
    repo = InMemoryTaxonomyRepository()
    repo.clear()
    return repo

@pytest.fixture
def usage_repo():
    repo = InMemoryLLMUsageRepository()
    repo.clear()
    return repo

@pytest.fixture
def mock_llm_provider():
    provider = MagicMock(spec=LLMProvider)
    provider.generate.return_value = LLMResponse(
        content='{"category": "Electronics", "subcategory": "Audio", "product_type": "Wireless Earbuds", "taxonomy_path": ["Electronics", "Audio", "Headphones & Earbuds", "Wireless Earbuds"], "brand": "Zero", "attributes": {"driver_size": "12mm", "connectivity": "Bluetooth 5.3"}, "confidence": 0.94, "classification_method": "llm", "needs_review": false}',
        parsed_json={
            "category": "Electronics",
            "subcategory": "Audio",
            "product_type": "Wireless Earbuds",
            "taxonomy_path": ["Electronics", "Audio", "Headphones & Earbuds", "Wireless Earbuds"],
            "brand": "Zero",
            "attributes": {"driver_size": "12mm", "connectivity": "Bluetooth 5.3"},
            "confidence": 0.94,
            "classification_method": "llm",
            "needs_review": False
        },
        provider="gemini",
        model="gemini-2.0-flash",
        input_tokens=120,
        output_tokens=45,
        total_tokens=165,
        estimated_cost=0.0001,
        latency_ms=180.0
    )

    return provider

@pytest.fixture
def categorization_agent(tax_repo, usage_repo, mock_llm_provider):
    return ProductCategorizationAgent(
        repository=tax_repo,
        llm_provider=mock_llm_provider,
        llm_usage_repo=usage_repo
    )

# -----------------------------------------------------------------------------
# Test Cases 1-10: Deterministic Rules & Keyword Scoring
# -----------------------------------------------------------------------------

def test_01_exact_marketplace_category_daraz():
    engine = DeterministicTaxonomyEngine()
    res, conf, method = engine.classify_deterministic(
        product_name="Generic Earphones In-Ear",
        original_category="mobiles & tablets > mobile accessories > headphones"
    )
    assert res is not None
    assert res["category"] == "Electronics"
    assert res["subcategory"] == "Audio"
    assert res["product_type"] == "Wireless Earbuds"
    assert conf >= 0.95
    assert method == "exact_marketplace_map"

def test_02_exact_marketplace_category_shopify():
    engine = DeterministicTaxonomyEngine()
    res, conf, method = engine.classify_deterministic(
        product_name="Cozy Winter Apparel",
        original_category="apparel / streetwear"
    )
    assert res is not None
    assert res["category"] == "Fashion"
    assert res["subcategory"] == "Men's Clothing"
    assert res["product_type"] == "Hoodies & Sweatshirts"
    assert conf >= 0.95
    assert method == "exact_marketplace_map"

def test_03_known_brand_mapping():
    engine = DeterministicTaxonomyEngine()
    # Apple
    brand_apple = engine.extract_brand("Apple iPhone 15 Pro Max Clear Case")
    assert brand_apple == "Apple"

    # Nike
    brand_nike = engine.extract_brand("Nike Air Force 1 07 Low White")
    assert brand_nike == "Nike"

    # The Ordinary
    brand_ord = engine.extract_brand("The Ordinary Niacinamide 10% + Zinc 1%")
    assert brand_ord == "The Ordinary"

def test_04_wireless_earbuds_keyword_scoring():
    engine = DeterministicTaxonomyEngine()
    res, conf, method = engine.classify_deterministic(
        product_name="Zero Lifestyle Z-Buds TWS Wireless Earbuds Bluetooth 5.3"
    )
    assert res is not None
    assert res["category"] == "Electronics"
    assert res["subcategory"] == "Audio"
    assert res["product_type"] == "Wireless Earbuds"
    assert conf >= 0.85

def test_05_over_ear_headphones_keyword_scoring():
    engine = DeterministicTaxonomyEngine()
    res, conf, method = engine.classify_deterministic(
        product_name="Sony WH-1000XM5 Wireless Noise Cancelling Over-Ear Headphones"
    )
    assert res is not None
    assert res["category"] == "Electronics"
    assert res["subcategory"] == "Audio"
    assert res["product_type"] == "Over-Ear Headphones"

def test_06_gaming_keyboard_and_mouse_keyword_scoring():
    engine = DeterministicTaxonomyEngine()
    res_kb, _, _ = engine.classify_deterministic(
        product_name="Keychron K2 RGB Wireless Mechanical Gaming Keyboard"
    )
    assert res_kb is not None
    assert res_kb["category"] == "Electronics"
    assert res_kb["subcategory"] == "Computer Accessories"
    assert res_kb["product_type"] == "Gaming Keyboard"

    res_mouse, _, _ = engine.classify_deterministic(
        product_name="Logitech G Pro X Superlight Wireless Gaming Mouse"
    )
    assert res_mouse is not None
    assert res_mouse["category"] == "Electronics"
    assert res_mouse["subcategory"] == "Computer Accessories"
    assert res_mouse["product_type"] == "Gaming Mouse"

def test_07_mens_clothing_hoodies_keyword_scoring():
    engine = DeterministicTaxonomyEngine()
    res, conf, _ = engine.classify_deterministic(
        product_name="Men Oversized Heavyweight Cotton Fleece Streetwear Hoodie"
    )
    assert res is not None
    assert res["category"] == "Fashion"
    assert res["subcategory"] == "Men's Clothing"
    assert res["product_type"] == "Hoodies & Sweatshirts"

def test_08_skincare_face_serum_keyword_scoring():
    engine = DeterministicTaxonomyEngine()
    res, conf, _ = engine.classify_deterministic(
        product_name="Hyaluronic Acid + Vitamin C Brightening Face Serum 30ml"
    )
    assert res is not None
    assert res["category"] == "Beauty & Personal Care"
    assert res["subcategory"] == "Skincare"
    assert res["product_type"] == "Face Serum"

def test_09_sports_fitness_hydration_packs_keyword_scoring():
    engine = DeterministicTaxonomyEngine()
    res, conf, _ = engine.classify_deterministic(
        product_name="TitanFlex Ultra Marathon Running Vest Hydration Pack with Water Bladder"
    )
    assert res is not None
    assert res["category"] == "Sports & Fitness"
    assert res["subcategory"] == "Running & Outdoor"
    assert res["product_type"] == "Hydration Vests & Packs"

def test_10_tea_coffee_accessories_keyword_scoring():
    engine = DeterministicTaxonomyEngine()
    res, conf, _ = engine.classify_deterministic(
        product_name="Japanese Ceremonial Matcha Bamboo Whisk & Bowl Set"
    )
    assert res is not None
    assert res["category"] == "Home & Living"
    assert res["subcategory"] == "Kitchen & Dining"
    assert res["product_type"] == "Tea & Coffee Accessories"

# -----------------------------------------------------------------------------
# Test Cases 11-14: Attribute Extraction
# -----------------------------------------------------------------------------

def test_11_attribute_extraction_driver_size():
    engine = DeterministicTaxonomyEngine()
    attrs = engine.extract_attributes("Features powerful 14.2mm dynamic driver speakers")
    assert attrs.get("driver_size") == "14.2mm"

def test_12_attribute_extraction_battery_capacity():
    engine = DeterministicTaxonomyEngine()
    attrs = engine.extract_attributes("Built-in 10000mAh lithium-polymer power pack")
    assert attrs.get("battery_capacity") == "10000mAh"

def test_13_attribute_extraction_ram_storage():
    engine = DeterministicTaxonomyEngine()
    attrs = engine.extract_attributes("High performance laptop 16GB RAM with 512GB SSD storage")
    assert attrs.get("ram") == "16GB"
    assert attrs.get("storage") == "512GB"

def test_14_attribute_extraction_connectivity_and_color():
    engine = DeterministicTaxonomyEngine()
    attrs = engine.extract_attributes("True wireless earbuds with Bluetooth 5.3 in Matte Black color for Men")
    assert attrs.get("connectivity") == "Bluetooth 5.3"
    assert attrs.get("color") == "Matte Black"
    assert attrs.get("gender") == "Men"

# -----------------------------------------------------------------------------
# Test Cases 15-18: Gemini LLM Resolution, Tokens, Insufficient Data & Candidates
# -----------------------------------------------------------------------------

def test_15_selective_gemini_llm_resolution(categorization_agent, mock_llm_provider):
    payload = {
        "title": "Quantum Vibe Device",
        "description": "Ultra acoustic miniature wireless listening device",
        "platform": "Daraz"
    }
    assignment = categorization_agent.classify_product(
        payload=payload,
        allow_llm=True
    )
    assert assignment is not None
    assert assignment.category == "Electronics"
    assert assignment.subcategory == "Audio"
    assert assignment.product_type == "Wireless Earbuds"
    assert assignment.classification_method == "llm"
    assert mock_llm_provider.generate.called

def test_16_gemini_token_usage_tracking(categorization_agent, usage_repo):
    payload = {
        "title": "Mysterious sound gadget",
        "description": "Sound emitting device",
        "platform": "Shopify"
    }
    categorization_agent.classify_product(payload=payload, allow_llm=True)
    records = usage_repo.list_usage(request_type="product_categorization")
    assert len(records) > 0
    assert records[0].provider == "gemini"
    assert records[0].total_tokens == 165


def test_17_insufficient_data_unknown_fallback(tax_repo):
    # Agent without LLM provider
    agent = ProductCategorizationAgent(repository=tax_repo, llm_provider=None)
    payload = {
        "title": "??? !!! ###",
        "description": "12345",
        "platform": "Daraz"
    }
    assignment = agent.classify_product(payload=payload, allow_llm=False)
    assert assignment.category == "Unknown"
    assert assignment.subcategory == "Unknown"
    assert assignment.product_type == "Unknown"
    assert assignment.needs_review is True
    assert assignment.confidence < 0.50

def test_18_candidate_creation_for_low_confidence(tax_repo):
    agent = ProductCategorizationAgent(repository=tax_repo, llm_provider=None)
    payload = {
        "product_id": "item_9999",
        "title": "Unidentified Object",
        "description": "",
        "platform": "Daraz"
    }
    agent.classify_product(payload=payload, allow_llm=False, save_result=True)
    candidates = tax_repo.list_candidates()
    assert len(candidates) > 0
    assert candidates[0].product_id == "item_9999"
    assert candidates[0].confidence < 0.50

# -----------------------------------------------------------------------------
# Test Cases 19-21: Memory Learning, Reinforcement, and Auditing
# -----------------------------------------------------------------------------

def test_19_memory_learning_new_pattern(tax_repo):
    mem_mgr = CategorizationMemoryManager(tax_repo)
    assignment = ProductTaxonomyAssignment(
        id="pta_1",
        unified_product_id="unf_1",
        category="Electronics",
        subcategory="Audio",
        product_type="Wireless Earbuds",
        taxonomy_path=["Electronics", "Audio", "Wireless Earbuds"],
        brand="Zero",
        attributes={},
        confidence=0.96,
        classification_method="exact_marketplace_map",
        needs_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    mem_mgr.record_classification_memory(
        assignment=assignment,
        original_category="daraz > audio > headphones",
        brand="Zero"
    )
    learned = mem_mgr.get_learned_mapping("marketplace_category_mapping", "daraz > audio > headphones")
    assert learned is not None
    assert learned["category"] == "Electronics"

def test_20_memory_reinforcement_increments_occurrence(tax_repo):
    mem_mgr = CategorizationMemoryManager(tax_repo)
    assignment = ProductTaxonomyAssignment(
        id="pta_1",
        unified_product_id="unf_1",
        category="Electronics",
        subcategory="Audio",
        product_type="Wireless Earbuds",
        taxonomy_path=["Electronics", "Audio", "Wireless Earbuds"],
        brand="Zero",
        attributes={},
        confidence=0.96,
        classification_method="exact_marketplace_map",
        needs_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    # First observation
    mem_mgr.record_classification_memory(assignment, "gadgets > sound", "Zero")
    # Second observation
    mem_mgr.record_classification_memory(assignment, "gadgets > sound", "Zero")

    mem = tax_repo.get_memory("agent_categorization", "marketplace_category_mapping", "gadgets > sound")
    assert mem is not None
    assert mem.occurrence_count == 2

def test_21_memory_event_auditing(tax_repo):
    mem_mgr = CategorizationMemoryManager(tax_repo)
    assignment = ProductTaxonomyAssignment(
        id="pta_1",
        unified_product_id="unf_1",
        category="Fashion",
        subcategory="Men's Clothing",
        product_type="T-Shirts",
        taxonomy_path=["Fashion", "Men's Clothing", "T-Shirts"],
        brand="Nike",
        attributes={},
        confidence=0.95,
        classification_method="exact_marketplace_map",
        needs_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    mem_mgr.record_classification_memory(assignment, "apparel > men tees", "Nike", run_id="run_123")
    events = tax_repo.get_memory_events("agent_categorization")
    assert len(events) > 0
    assert events[0].event_type == "created"
    assert events[0].trigger_run_id == "run_123"

# -----------------------------------------------------------------------------
# Test Cases 22-24: Taxonomy Tree, Repository Counts, and REST API Endpoints
# -----------------------------------------------------------------------------

def test_22_taxonomy_tree_building_and_counts(tax_repo):
    tree = tax_repo.get_taxonomy_tree()
    assert len(tree) >= 18
    cat_names = [c.name for c in tree]
    assert "Electronics" in cat_names
    assert "Fashion" in cat_names
    assert "Beauty & Personal Care" in cat_names

    # Add assignment
    tax_repo.upsert_assignment(ProductTaxonomyAssignment(
        id="pta_101",
        unified_product_id="unf_101",
        category="Electronics",
        subcategory="Audio",
        product_type="Wireless Earbuds",
        taxonomy_path=["Electronics", "Audio", "Wireless Earbuds"],
        attributes={},
        confidence=0.95,
        classification_method="keyword_rule",
        needs_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    ))
    counts = tax_repo.get_category_product_counts()
    assert counts.get("Electronics") == 1

def test_23_rest_api_categorization_endpoints(categorization_agent, tax_repo):
    client = TestClient(app)
    unf_repo = InMemoryUnifiedProductRepository()
    now = datetime.now(timezone.utc)
    # Seed unified product
    unf_repo.upsert_unified_product(UnifiedProduct(
        id="unf_test_1",
        unified_product_id="unf_test_1",
        canonical_name="Zero Z-Buds Pro Wireless Earbuds",
        normalized_name="zero z-buds pro wireless earbuds",
        brand="Zero",
        category="Audio",
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now
    ))
    app.dependency_overrides[get_unified_repository] = lambda: unf_repo
    app.dependency_overrides[get_taxonomy_repository] = lambda: tax_repo
    app.dependency_overrides[get_categorization_agent] = lambda: categorization_agent

    # 1. Classify product
    resp = client.post("/api/v1/agents/categorization/classify/unf_test_1", json={"force_reclassify": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "Electronics"
    assert data["subcategory"] == "Audio"
    assert data["product_type"] == "Wireless Earbuds"

    # 2. Get active assignment
    resp_get = client.get("/api/v1/agents/categorization/unf_test_1")
    assert resp_get.status_code == 200
    assert resp_get.json()["category"] == "Electronics"

    # 3. Get history
    resp_hist = client.get("/api/v1/agents/categorization/unf_test_1/history")
    assert resp_hist.status_code == 200
    assert resp_hist.json()["total"] >= 1

    # 4. Get memory
    resp_mem = client.get("/api/v1/agents/categorization/memory")
    assert resp_mem.status_code == 200


    # 5. Get candidates
    resp_cands = client.get("/api/v1/agents/categorization/candidates")
    assert resp_cands.status_code == 200

    app.dependency_overrides.clear()

def test_24_rest_api_taxonomy_endpoints(tax_repo):
    client = TestClient(app)
    app.dependency_overrides[get_taxonomy_repository] = lambda: tax_repo

    # 1. List Categories
    resp_cats = client.get("/api/v1/taxonomy/categories")
    assert resp_cats.status_code == 200
    assert resp_cats.json()["total"] >= 18

    # 2. Get Tree
    resp_tree = client.get("/api/v1/taxonomy/tree")
    assert resp_tree.status_code == 200
    assert resp_tree.json()["total_nodes"] >= 18

    # 3. Search Taxonomy
    resp_search = client.get("/api/v1/taxonomy/search?q=earbuds")
    assert resp_search.status_code == 200
    assert resp_search.json()["total"] >= 1

    # 4. Get Category Counts
    resp_counts = client.get("/api/v1/taxonomy/counts")
    assert resp_counts.status_code == 200

    app.dependency_overrides.clear()
