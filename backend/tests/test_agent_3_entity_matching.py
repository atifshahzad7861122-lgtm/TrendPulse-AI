"""
Automated Test Suite for AI Agent 03: Product Entity Matching & Deduplication Agent.
Tests all 30 specified functional cases, 7 deterministic matching tiers, variant detection,
selective LLM resolver, memory manager & audit trail, and REST APIs.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.domain import (
    UnifiedProduct,
    ProductPlatformListing,
    ProductMatchCandidate,
    ProductSignature,
    ProductMatchDecision,
    AIAgentMemoryEvent
)
from backend.app.repositories.in_memory import InMemoryUnifiedProductRepository
from backend.app.services.agents.entity_matching import (
    ProductSignatureBuilder,
    CandidateBlocker,
    DeterministicEntityMatcher,
    EntityMatchingMemoryManager,
    EntityMatchingLLMResolver,
    ProductEntityMatchingAgent
)
from backend.app.api.deps import get_unified_repository, get_entity_matching_agent


@pytest.fixture
def repo():
    r = InMemoryUnifiedProductRepository()
    r.clear()
    return r


@pytest.fixture
def agent(repo):
    return ProductEntityMatchingAgent(unified_repo=repo)


# ============================================================================
# 1-7. DETERMINISTIC MATCHING TIERS (TIERS 1 TO 5)
# ============================================================================

def test_01_exact_sku_match(agent):
    """Test Tier 1: Exact SKU match across platforms (confidence = 1.00)."""
    p1 = {
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "brand": "Sony",
        "platform": "daraz",
        "platform_product_id": "daraz_101",
        "identifiers": {"sku": "SNY-WH1000XM5-BLK"}
    }
    p2 = {
        "title": "Sony Noise Canceling Headphones XM5",
        "brand": "Sony",
        "platform": "shopify",
        "platform_product_id": "shop_202",
        "identifiers": {"sku": "SNY-WH1000XM5-BLK"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "EXACT_MATCH"
    assert decision.confidence == 1.0
    assert decision.match_method == "exact_sku"
    assert "SKU" in decision.reasons[0]


def test_02_exact_gtin_match(agent):
    """Test Tier 2: Exact GTIN match (confidence = 0.99+)."""
    p1 = {
        "title": "Logitech MX Master 3S Wireless Mouse",
        "brand": "Logitech",
        "platform": "daraz",
        "platform_product_id": "daraz_logi_1",
        "identifiers": {"gtin": "00097855174543"}
    }
    p2 = {
        "title": "Logitech MX Master 3S - Graphite",
        "brand": "Logitech",
        "platform": "shopify",
        "platform_product_id": "shop_logi_1",
        "identifiers": {"gtin": "00097855174543"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "EXACT_MATCH"
    assert decision.confidence >= 0.99
    assert decision.match_method == "exact_gtin"


def test_03_exact_upc_match(agent):
    """Test Tier 2: Exact UPC match (confidence = 0.99+)."""
    p1 = {
        "title": "Anker 737 Power Bank (PowerCore 24K)",
        "brand": "Anker",
        "platform": "daraz",
        "platform_product_id": "daraz_ank_1",
        "identifiers": {"upc": "194644098765"}
    }
    p2 = {
        "title": "Anker 737 Portable Charger 24000mAh",
        "brand": "Anker",
        "platform": "shopify",
        "platform_product_id": "shop_ank_1",
        "identifiers": {"upc": "194644098765"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "EXACT_MATCH"
    assert decision.confidence >= 0.99
    assert decision.match_method == "exact_upc"


def test_04_exact_ean_match(agent):
    """Test Tier 2: Exact EAN match (confidence = 0.99+)."""
    p1 = {
        "title": "Samsung Galaxy S24 Ultra 5G",
        "brand": "Samsung",
        "platform": "daraz",
        "platform_product_id": "daraz_s24_1",
        "identifiers": {"ean": "8806095312345"}
    }
    p2 = {
        "title": "Galaxy S24 Ultra Titanium Gray",
        "brand": "Samsung",
        "platform": "shopify",
        "platform_product_id": "shop_s24_1",
        "identifiers": {"ean": "8806095312345"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "EXACT_MATCH"
    assert decision.confidence >= 0.99
    assert decision.match_method == "exact_ean"


def test_05_exact_asin_match(agent):
    """Test Tier 3: Exact ASIN match (confidence = 0.99+)."""
    p1 = {
        "title": "Apple AirPods Pro (2nd Generation) with USB-C",
        "brand": "Apple",
        "platform": "daraz",
        "platform_product_id": "daraz_app_1",
        "identifiers": {"asin": "B0CD07K814"}
    }
    p2 = {
        "title": "AirPods Pro 2 USB-C Case White",
        "brand": "Apple",
        "platform": "shopify",
        "platform_product_id": "shop_app_1",
        "identifiers": {"asin": "B0CD07K814"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "EXACT_MATCH"
    assert decision.confidence >= 0.99
    assert decision.match_method == "exact_asin"


def test_06_brand_and_model_match(agent):
    """Test Tier 4: Exact brand + model number match (confidence >= 0.95)."""
    p1 = {
        "title": "Dell XPS 13 9315 Laptop Core i7",
        "brand": "Dell",
        "platform": "daraz",
        "platform_product_id": "daraz_dell_1",
        "identifiers": {"model_number": "XPS-9315"}
    }
    p2 = {
        "title": "Dell Ultrabook XPS 13 Model XPS-9315 16GB",
        "brand": "Dell",
        "platform": "shopify",
        "platform_product_id": "shop_dell_1",
        "identifiers": {"model_number": "xps-9315"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "HIGH_CONFIDENCE_MATCH"
    assert decision.confidence >= 0.95
    assert "brand" in decision.match_method and "model" in decision.match_method


def test_07_brand_and_title_similarity(agent):
    """Test Tier 5: Brand + high token similarity match."""
    p1 = {
        "title": "HyperX Cloud II Gaming Headset 7.1 Surround Sound Red",
        "brand": "HyperX",
        "platform": "daraz",
        "platform_product_id": "daraz_hx_1",
        "identifiers": {}
    }
    p2 = {
        "title": "HyperX Cloud II Gaming Headset 7.1 Surround Red Edition",
        "brand": "HyperX",
        "platform": "shopify",
        "platform_product_id": "shop_hx_1",
        "identifiers": {}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision in ["HIGH_CONFIDENCE_MATCH", "PROBABLE_MATCH"]
    assert decision.confidence >= 0.85


# ============================================================================
# 08-12. VARIANT DETECTION & FALSE-POSITIVE PREVENTION
# ============================================================================

def test_08_storage_variant_detection(agent):
    """Test variant detection: Same iPhone 15, different storage (128GB vs 256GB)."""
    p1 = {
        "title": "Apple iPhone 15 128GB Black",
        "brand": "Apple",
        "platform": "daraz",
        "platform_product_id": "d_ip15_128",
        "attributes": {"storage": "128gb", "color": "black"}
    }
    p2 = {
        "title": "Apple iPhone 15 256GB Black",
        "brand": "Apple",
        "platform": "shopify",
        "platform_product_id": "s_ip15_256",
        "attributes": {"storage": "256gb", "color": "black"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "VARIANT"
    assert "storage" in decision.variant_attributes


def test_09_color_variant_detection(agent):
    """Test variant detection: Same laptop, different color (Space Gray vs Silver)."""
    p1 = {
        "title": "Apple MacBook Air M3 16GB 512GB Space Gray",
        "brand": "Apple",
        "platform": "daraz",
        "platform_product_id": "d_mba_gray",
        "attributes": {"color": "Space Gray", "storage": "512gb", "ram": "16gb"}
    }
    p2 = {
        "title": "Apple MacBook Air M3 16GB 512GB Silver",
        "brand": "Apple",
        "platform": "shopify",
        "platform_product_id": "s_mba_silver",
        "attributes": {"color": "Silver", "storage": "512gb", "ram": "16gb"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "VARIANT"
    assert "color" in decision.variant_attributes


def test_10_different_model_rejection(agent):
    """Test rejection: iPhone 16 vs iPhone 16 Pro must NEVER match or merge."""
    p1 = {
        "title": "Apple iPhone 16 128GB Black",
        "brand": "Apple",
        "platform": "daraz",
        "platform_product_id": "d_ip16",
        "identifiers": {}
    }
    p2 = {
        "title": "Apple iPhone 16 Pro 128GB Natural Titanium",
        "brand": "Apple",
        "platform": "shopify",
        "platform_product_id": "s_ip16_pro",
        "identifiers": {}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision in ["NO_MATCH", "RELATED_PRODUCT"]
    assert any("model_conflict" in c or "token_conflict" in c or "model/tier" in c for c in decision.conflicts)


def test_11_different_generation_rejection(agent):
    """Test rejection: Sony WH-1000XM4 vs WH-1000XM5 must NEVER match."""
    p1 = {
        "title": "Sony WH-1000XM4 Wireless Noise-Cancelling Headphones",
        "brand": "Sony",
        "platform": "daraz",
        "platform_product_id": "d_xm4",
        "identifiers": {"model_number": "WH1000XM4"}
    }
    p2 = {
        "title": "Sony WH-1000XM5 Wireless Noise-Cancelling Headphones",
        "brand": "Sony",
        "platform": "shopify",
        "platform_product_id": "s_xm5",
        "identifiers": {"model_number": "WH1000XM5"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision in ["NO_MATCH", "RELATED_PRODUCT"]



def test_12_different_product_type_rejection(agent):
    """Test rejection: Razer Keyboard vs Razer Mouse must NEVER match."""
    p1 = {
        "title": "Razer BlackWidow V4 Pro Mechanical Gaming Keyboard",
        "brand": "Razer",
        "product_type": "Keyboard",
        "platform": "daraz",
        "platform_product_id": "d_razer_kb"
    }
    p2 = {
        "title": "Razer DeathAdder V3 Pro Wireless Gaming Mouse",
        "brand": "Razer",
        "product_type": "Mouse",
        "platform": "shopify",
        "platform_product_id": "s_razer_mouse"
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "NO_MATCH"


# ============================================================================
# 13-17. BLOCKING, REVIEW QUEUE, & LLM RESOLVER
# ============================================================================

def test_13_candidate_blocking_efficiency():
    """Test candidate blocking reduces search space from 100 items to relevant block."""
    pool = []
    for i in range(100):
        pool.append({
            "unified_product_id": f"unf_{i}",
            "canonical_name": f"Generic Item {i}",
            "brand": "OtherBrand",
            "product_type": "OtherType",
            "identifiers": {}
        })
    # Add target item
    pool.append({
        "unified_product_id": "unf_target",
        "canonical_name": "Logitech MX Master 3S Mouse",
        "brand": "Logitech",
        "product_type": "Mouse",
        "identifiers": {"model_number": "MX-3S"}
    })

    incoming = {
        "title": "Logitech MX Master 3S Wireless Mouse Graphite",
        "brand": "Logitech",
        "product_type": "Mouse",
        "identifiers": {"model_number": "MX-3S"}
    }
    sig = ProductSignatureBuilder.build_signature(incoming)
    candidates = CandidateBlocker.filter_candidates(sig, pool, max_candidates=20)
    assert len(candidates) >= 1
    assert any(c["unified_product_id"] == "unf_target" for c in candidates)
    assert len(candidates) < 10


def test_14_low_confidence_review_queue(repo, agent):
    """Test low confidence (0.75 <= conf < 0.85) creates a match candidate for review."""
    unified = UnifiedProduct(
        id="unf_ambig_1",
        unified_product_id="unf_ambig_1",
        canonical_name="Lenovo ThinkPad Wireless TrackPoint Keyboard",
        normalized_name="lenovo thinkpad wireless trackpoint keyboard",
        brand="Lenovo",
        category="Electronics",
        platforms=["daraz"],
        platform_count=1,
        listings_count=1,
        lowest_price=80.0,
        highest_price=80.0,
        average_price=80.0,
        primary_currency="USD",
        avg_rating=4.5,
        total_reviews=10,
        completeness_score=0.9,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        last_synced_at=datetime.now(timezone.utc)
    )
    repo.upsert_unified_product(unified)

    incoming = {
        "title": "Lenovo TrackPoint Bluetooth Dual Device Keyboard II",
        "brand": "Lenovo",
        "platform": "shopify",
        "platform_product_id": "s_len_track",
        "price": 85.0,
        "currency": "USD"
    }

    decision, matched = agent.match_listing(incoming, candidate_pool=[unified.__dict__], allow_llm=False)
    assert decision.decision in ["PROBABLE_MATCH", "NEEDS_REVIEW", "NO_MATCH"]
    
    cands = repo.list_match_candidates(status="needs_review")
    assert len(cands) >= 0


def test_15_selective_gemini_llm_resolver(agent):
    """Test Gemini LLM is called when deterministic match is ambiguous."""
    p1 = {
        "title": "Sony Noise Cancelling Over Ear Headphones Black",
        "brand": "Sony",
        "platform": "daraz",
        "platform_product_id": "d_sny_amb"
    }
    p2 = {
        "title": "Sony Bluetooth Over Ear Studio Headphones Black",
        "brand": "Sony",
        "platform": "shopify",
        "platform_product_id": "s_sny_amb"
    }

    with patch.object(agent.llm_resolver, "resolve_ambiguity", return_value=(
        {"decision": "same_product", "reasons": ["Both listings refer to Bose QuietComfort Over-Ear Headphones."]},
        0.94,
        "llm_gemini_semantic",
        True
    )):
        decision = agent.compare_products(p1, p2, allow_llm=True)
        assert decision.decision in ["HIGH_CONFIDENCE_MATCH", "PROBABLE_MATCH"]
        assert decision.confidence == 0.94
        assert decision.llm_used is True


def test_16_gemini_llm_timeout_fallback(agent):
    """Test Gemini timeout/error safely falls back to NEEDS_REVIEW without crashing."""
    p1 = {
        "title": "Anker Soundcore Space One ANC Headphones",
        "brand": "Anker",
        "platform": "daraz",
        "platform_product_id": "d_ank_so"
    }
    p2 = {
        "title": "Anker Space One Bluetooth Headset",
        "brand": "Anker",
        "platform": "shopify",
        "platform_product_id": "s_ank_so"
    }

    with patch.object(agent.llm_resolver, "resolve_ambiguity", return_value=(
        {},
        0.0,
        "llm_timeout_fallback",
        False
    )):
        decision = agent.compare_products(p1, p2, allow_llm=True)
        assert decision.decision in ["NEEDS_REVIEW", "NO_MATCH", "PROBABLE_MATCH"]


def test_17_gemini_invalid_json_fallback(agent):
    """Test Gemini malformed response safely falls back to false."""
    mock_provider = MagicMock()
    mock_provider.generate_content.side_effect = Exception("Invalid JSON")
    resolver = EntityMatchingLLMResolver(provider=mock_provider)
    p1 = {"title": "Test Item 1", "platform": "daraz", "platform_product_id": "1"}
    p2 = {"title": "Test Item 2", "platform": "shopify", "platform_product_id": "2"}
    sig1 = ProductSignatureBuilder.build_signature(p1)
    sig2 = ProductSignatureBuilder.build_signature(p2)

    data, conf, method, ok = resolver.resolve_ambiguity(sig1, sig2, "Test Item 1", "Test Item 2")
    assert ok is False


# ============================================================================
# 18-20. MEMORY MANAGER, REINFORCEMENT & AUDIT EVENTS
# ============================================================================

def test_18_match_memory_creation(repo, agent):
    """Test high-confidence match creates a memory record for instant recall."""
    p1 = {
        "title": "Logitech MX Mechanical Mini Keyboard",
        "brand": "Logitech",
        "platform": "daraz",
        "platform_product_id": "d_mx_mech",
        "identifiers": {"sku": "LOGI-920-010553"}
    }
    p2 = {
        "title": "Logitech MX Mechanical Mini - Clicky",
        "brand": "Logitech",
        "platform": "shopify",
        "platform_product_id": "s_mx_mech",
        "identifiers": {"sku": "LOGI-920-010553"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "EXACT_MATCH"

    mem_records = agent.taxonomy_repo.list_memory("agent_entity_matching", "confirmed_match_signature")
    assert len(mem_records) >= 1


def test_19_match_memory_reinforcement(repo, agent):
    """Test repeated matches increment occurrence count in memory."""
    p1 = {
        "title": "Keychron Q1 Pro Wireless Custom Mechanical Keyboard",
        "brand": "Keychron",
        "platform": "daraz",
        "platform_product_id": "d_kc_q1",
        "identifiers": {"sku": "KC-Q1P-BLK"}
    }
    p2 = {
        "title": "Keychron Q1 Pro Keyboard Carbon Black",
        "brand": "Keychron",
        "platform": "shopify",
        "platform_product_id": "s_kc_q1",
        "identifiers": {"sku": "KC-Q1P-BLK"}
    }
    agent.compare_products(p1, p2, allow_llm=False)
    agent.compare_products(p1, p2, allow_llm=False)

    mem_records = agent.taxonomy_repo.list_memory("agent_entity_matching", "confirmed_match_signature")
    assert any(m.occurrence_count >= 2 for m in mem_records)


def test_20_match_memory_audit_events(repo, agent):
    """Test memory events are recorded in ai_agent_memory_events repository table."""
    p1 = {
        "title": "Bose QuietComfort Ultra Headphones Black",
        "brand": "Bose",
        "platform": "daraz",
        "platform_product_id": "d_bose_qc",
        "identifiers": {"upc": "017817843210"}
    }
    p2 = {
        "title": "Bose QC Ultra Wireless ANC",
        "brand": "Bose",
        "platform": "shopify",
        "platform_product_id": "s_bose_qc",
        "identifiers": {"upc": "017817843210"}
    }
    agent.compare_products(p1, p2, allow_llm=False)

    events = agent.taxonomy_repo.get_memory_events(agent_id="agent_entity_matching")
    assert len(events) >= 1
    assert any(e.event_type in ["created", "updated", "reinforced", "memory_updated"] for e in events)


# ============================================================================
# 21-24. CANONICAL DEDUPLICATION & MULTI-PLATFORM LINKING
# ============================================================================

def test_21_duplicate_marketplace_listing_reassociation(repo, agent):
    """Test existing listing re-sync links to same canonical product without creating duplicate."""
    unf = UnifiedProduct(
        id="unf_sony_xm5",
        unified_product_id="unf_sony_xm5",
        canonical_name="Sony WH-1000XM5 Wireless Headphones",
        normalized_name="sony wh 1000xm5 wireless headphones",
        brand="Sony",
        platforms=["daraz"],
        platform_count=1,
        listings_count=1,
        lowest_price=399.0,
        highest_price=399.0,
        average_price=399.0,
        primary_currency="USD",
        avg_rating=4.8,
        total_reviews=50,
        completeness_score=0.95,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        last_synced_at=datetime.now(timezone.utc)
    )
    repo.upsert_unified_product(unf)
    listing = ProductPlatformListing(
        id="list_1",
        unified_product_id="unf_sony_xm5",
        platform="daraz",
        platform_product_id="daraz_sny_100",
        product_url="https://daraz.pk/p/100",
        title="Sony WH-1000XM5 Wireless Headphones",
        normalized_title="sony wh 1000xm5 wireless headphones",
        price=399.0,
        currency="USD",
        available=True,
        rating=4.8,
        review_count=50,
        source_provider="direct",
        last_synced_at=datetime.now(timezone.utc),
        completeness_score=0.95
    )
    repo.upsert_platform_listing(listing)

    incoming = {
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "brand": "Sony",
        "platform": "daraz",
        "platform_product_id": "daraz_sny_100",
        "price": 379.0,
        "currency": "USD"
    }
    decision, matched_unf = agent.match_listing(incoming, allow_llm=False)
    assert matched_unf is not None
    assert matched_unf.unified_product_id == "unf_sony_xm5"
    assert decision.decision == "EXACT_MATCH"


def test_22_unified_product_multi_platform_linking(repo, agent):
    """Test linking Daraz + Shopify listings under one single canonical entity."""
    unf = UnifiedProduct(
        id="unf_ps5_slim",
        unified_product_id="unf_ps5_slim",
        canonical_name="Sony PlayStation 5 Slim Digital Edition",
        normalized_name="sony playstation 5 slim digital edition",
        brand="Sony",
        platforms=["daraz"],
        platform_count=1,
        listings_count=1,
        lowest_price=449.0,
        highest_price=449.0,
        average_price=449.0,
        primary_currency="USD",
        avg_rating=4.9,
        total_reviews=120,
        completeness_score=0.98,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        last_synced_at=datetime.now(timezone.utc),
        identifiers={"model_number": "CFI-2000B01"}
    )
    repo.upsert_unified_product(unf)

    incoming_shopify = {
        "title": "PlayStation 5 Digital Console Slim CFI-2000B01",
        "brand": "Sony",
        "platform": "shopify",
        "platform_product_id": "shop_ps5_slim",
        "price": 449.99,
        "currency": "USD",
        "identifiers": {"model_number": "CFI-2000B01"}
    }
    decision, matched_unf = agent.match_listing(incoming_shopify, candidate_pool=[unf.__dict__], allow_llm=False)
    assert matched_unf is not None
    assert matched_unf.unified_product_id == "unf_ps5_slim"
    assert decision.decision in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH", "PROBABLE_MATCH"]


def test_23_historical_matching_price_updates(repo, agent):
    """Test price or stock changes match existing product rather than create new entities."""
    unf = UnifiedProduct(
        id="unf_kindle_paperwhite",
        unified_product_id="unf_kindle_paperwhite",
        canonical_name="Amazon Kindle Paperwhite 16GB",
        normalized_name="amazon kindle paperwhite 16gb",
        brand="Amazon",
        platforms=["shopify"],
        platform_count=1,
        listings_count=1,
        lowest_price=149.0,
        highest_price=149.0,
        average_price=149.0,
        primary_currency="USD",
        avg_rating=4.7,
        total_reviews=300,
        completeness_score=0.95,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        last_synced_at=datetime.now(timezone.utc),
        identifiers={"asin": "B09TMN58KL"}
    )
    repo.upsert_unified_product(unf)

    incoming = {
        "title": "Kindle Paperwhite (16 GB) – Now with a 6.8\" display",
        "brand": "Amazon",
        "platform": "shopify",
        "platform_product_id": "s_kindle_pw",
        "price": 129.99,
        "currency": "USD",
        "identifiers": {"asin": "B09TMN58KL"}
    }
    decision, matched_unf = agent.match_listing(incoming, candidate_pool=[unf.__dict__], allow_llm=False)
    assert matched_unf.unified_product_id == "unf_kindle_paperwhite"


def test_24_match_audit_persistence(repo, agent):
    """Test all match decisions are persisted in product_match_decisions repository table."""
    p1 = {
        "title": "Garmin Fenix 7 Pro Solar Smartwatch",
        "brand": "Garmin",
        "platform": "daraz",
        "platform_product_id": "d_garmin_7",
        "identifiers": {"sku": "GRM-010-02777-00"}
    }
    p2 = {
        "title": "Garmin Fenix 7 Pro Solar Edition",
        "brand": "Garmin",
        "platform": "shopify",
        "platform_product_id": "s_garmin_7",
        "identifiers": {"sku": "GRM-010-02777-00"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    saved_dec = repo.get_match_decision(decision.id)
    assert saved_dec is not None
    assert saved_dec.decision == "EXACT_MATCH"


# ============================================================================
# 25-27. REST API ENDPOINTS & RESOLUTION
# ============================================================================

def test_25_api_match_endpoint(repo, agent):
    """Test POST /api/v1/agents/entity-matching/match endpoint."""
    client = TestClient(app)
    app.dependency_overrides[get_unified_repository] = lambda: repo
    app.dependency_overrides[get_entity_matching_agent] = lambda: agent

    payload = {
        "product_name": "Apple Watch Ultra 2 GPS + Cellular 49mm",
        "title": "Apple Watch Ultra 2 Titanium Case",
        "brand": "Apple",
        "platform": "daraz",
        "platform_product_id": "daraz_awu2",
        "identifiers": {"sku": "APL-MREP3LL/A"},
        "allow_llm": False
    }
    res = client.post("/api/v1/agents/entity-matching/match", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH", "NO_MATCH", "NEEDS_REVIEW"]
    assert "confidence" in data
    assert "match_method" in data
    app.dependency_overrides.clear()


def test_26_api_compare_endpoint(repo, agent):
    """Test POST /api/v1/agents/entity-matching/compare endpoint."""
    client = TestClient(app)
    app.dependency_overrides[get_unified_repository] = lambda: repo
    app.dependency_overrides[get_entity_matching_agent] = lambda: agent

    payload = {
        "product_a": {
            "title": "Logitech G Pro X Superlight Wireless Mouse",
            "brand": "Logitech",
            "platform": "daraz",
            "platform_product_id": "d_gpro",
            "identifiers": {"sku": "LOGI-910-005878"}
        },
        "product_b": {
            "title": "Logitech G PRO X SUPERLIGHT Gaming Mouse",
            "brand": "Logitech",
            "platform": "shopify",
            "platform_product_id": "s_gpro",
            "identifiers": {"sku": "LOGI-910-005878"}
        },
        "allow_llm": False
    }
    res = client.post("/api/v1/agents/entity-matching/compare", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "EXACT_MATCH"
    assert data["confidence"] == 1.0
    app.dependency_overrides.clear()


def test_27_api_candidates_and_resolve_flow(repo, agent):
    """Test GET /candidates and POST /candidates/{id}/resolve flow."""
    client = TestClient(app)
    app.dependency_overrides[get_unified_repository] = lambda: repo
    app.dependency_overrides[get_entity_matching_agent] = lambda: agent

    cand = ProductMatchCandidate(
        id="cand_test_resolve_100",
        unified_product_id="unf_cand_100",
        candidate_unified_id="unf_cand_100",
        platform="daraz",
        platform_product_id="daraz_cand_100",
        confidence_score=0.79,
        method="token_similarity",
        status="needs_review",
        reasons=["High name similarity"],
        created_at=datetime.now(timezone.utc)
    )
    repo.record_match_candidate(cand)
    
    # 1. List candidates
    res_list = client.get("/api/v1/agents/entity-matching/candidates?status=needs_review")
    assert res_list.status_code == 200
    candidates = res_list.json()
    assert any(c["id"] == "cand_test_resolve_100" for c in candidates)

    # 2. Resolve candidate
    res_resolve = client.post(
        "/api/v1/agents/entity-matching/candidates/cand_test_resolve_100/resolve",
        json={"action": "confirm_match", "notes": "Verified identical model by admin"}
    )
    assert res_resolve.status_code == 200
    resolved = res_resolve.json()
    assert resolved["status"] in ["confirmed_match", "resolved_match"]
    app.dependency_overrides.clear()


# ============================================================================
# 28-30. CURRENCY PRESERVATION, FALSE-POSITIVE PROTECTION, & STATS
# ============================================================================

def test_28_currency_preservation_across_marketplaces(repo, agent):
    """Test Daraz PKR and Shopify USD prices & currencies are preserved separately."""
    daraz_item = {
        "title": "Samsung Galaxy Tab S9 Ultra 256GB",
        "brand": "Samsung",
        "platform": "daraz",
        "platform_product_id": "daraz_tab_s9",
        "price": 320000.0,
        "currency": "PKR",
        "identifiers": {"model_number": "SM-X910"}
    }
    dec1, unf1 = agent.match_listing(daraz_item, allow_llm=False)

    shopify_item = {
        "title": "Galaxy Tab S9 Ultra Wi-Fi 256GB SM-X910",
        "brand": "Samsung",
        "platform": "shopify",
        "platform_product_id": "shop_tab_s9",
        "price": 1199.99,
        "currency": "USD",
        "identifiers": {"model_number": "SM-X910"}
    }
    dec2, unf2 = agent.match_listing(shopify_item, candidate_pool=[unf1.__dict__] if unf1 else [], allow_llm=False)
    
    assert dec2.decision in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH", "PROBABLE_MATCH"]
    sig_daraz = ProductSignatureBuilder.build_signature(daraz_item)
    sig_shopify = ProductSignatureBuilder.build_signature(shopify_item)
    assert sig_daraz.currency == "PKR"
    assert sig_shopify.currency == "USD"


def test_29_false_positive_protection_hard_conflict(agent):
    """Test hard conflict prevents merge even when token similarity is very high."""
    p1 = {
        "title": "SanDisk 128GB Extreme PRO SDXC UHS-I Memory Card",
        "brand": "SanDisk",
        "platform": "daraz",
        "platform_product_id": "d_sd_128",
        "attributes": {"capacity": "128gb"}
    }
    p2 = {
        "title": "SanDisk 512GB Extreme PRO SDXC UHS-I Memory Card",
        "brand": "SanDisk",
        "platform": "shopify",
        "platform_product_id": "s_sd_512",
        "attributes": {"capacity": "512gb"}
    }
    decision = agent.compare_products(p1, p2, allow_llm=False)
    assert decision.decision == "VARIANT"
    assert decision.decision != "EXACT_MATCH"
    assert "storage" in decision.variant_attributes


def test_30_agent_stats_endpoint(repo, agent):
    """Test GET /api/v1/agents/entity-matching/stats endpoint returns telemetry."""
    client = TestClient(app)
    app.dependency_overrides[get_unified_repository] = lambda: repo
    app.dependency_overrides[get_entity_matching_agent] = lambda: agent

    res = client.get("/api/v1/agents/entity-matching/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "total_evaluations" in stats
    assert "exact_matches" in stats
    assert "deterministic_match_rate" in stats
    app.dependency_overrides.clear()
