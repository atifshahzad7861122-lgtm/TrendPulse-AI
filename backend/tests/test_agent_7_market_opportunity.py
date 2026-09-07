import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, MarketOpportunity,
    MarketOpportunityCandidate, MarketOpportunityAudit, MarketOpportunityScoreBreakdown,
    MarketOpportunitySummary, AgentMarketOpportunityStats, AIAgentMemory, AIAgentMemoryEvent,
    DataQualityValidationResult, TrendSignal, AnomalyDetection
)
from backend.app.repositories.in_memory import (
    InMemoryMarketOpportunityRepository, InMemoryUnifiedProductRepository,
    InMemoryDataQualityRepository, InMemoryTaxonomyRepository,
    InMemoryTrendDetectionRepository, InMemoryAnomalyDetectionRepository,
    InMemoryRecommendationRepository
)
from backend.app.services.agents.market_opportunity.scoring_engine import MarketOpportunityScoringEngine
from backend.app.services.agents.market_opportunity.detectors import MarketOpportunityDetectors
from backend.app.services.agents.market_opportunity.llm_resolver import (
    MarketOpportunityLLMResolver, MarketOpportunityLLMOutput
)
from backend.app.services.agents.market_opportunity.memory_manager import MarketOpportunityMemoryManager
from backend.app.services.agents.market_opportunity.agent import MarketOpportunityIntelligenceAgent


# Fixtures
@pytest.fixture
def opp_repo():
    repo = InMemoryMarketOpportunityRepository()
    repo.clear()
    return repo


@pytest.fixture
def unified_repo():
    repo = InMemoryUnifiedProductRepository()
    repo.clear()
    return repo


@pytest.fixture
def dq_repo():
    repo = InMemoryDataQualityRepository()
    repo.clear()
    return repo


@pytest.fixture
def trend_repo():
    repo = InMemoryTrendDetectionRepository()
    repo.clear()
    return repo


@pytest.fixture
def anomaly_repo():
    repo = InMemoryAnomalyDetectionRepository()
    repo.clear()
    return repo


@pytest.fixture
def sample_product():
    return UnifiedProduct(
        id="uprod_audio_001",
        unified_product_id="uprod_audio_001",
        canonical_name="Sony WH-1000XM5 Wireless Headphones",
        normalized_name="sony wh-1000xm5 wireless headphones",
        brand="Sony",
        category="Audio",
        subcategory="Over-Ear Headphones",
        avg_rating=4.8,
        total_reviews=120,
        completeness_score=0.92,
        platforms=["Daraz"],
        platform_count=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_listings():
    return [
        ProductPlatformListing(
            id="list_daraz_001",
            listing_id="list_daraz_001",
            unified_product_id="uprod_audio_001",
            platform="Daraz",
            platform_product_id="daraz_sony_101",
            product_url="https://daraz.pk/p/101",
            title="Sony WH-1000XM5 Noise Cancelling Headphones",
            normalized_title="Sony WH-1000XM5 Noise Cancelling Headphones",
            price=85000.0,
            currency="PKR",
            rating=4.8,
            review_count=120,
            available=True
        ),
        ProductPlatformListing(
            id="list_shopify_001",
            listing_id="list_shopify_001",
            unified_product_id="uprod_audio_001",
            platform="Shopify",
            platform_product_id="shop_sony_101",
            product_url="https://store.shopify.com/products/sony-xm5",
            title="Sony WH-1000XM5 ANC Headset",
            normalized_title="Sony WH-1000XM5 ANC Headset",
            price=99000.0,
            currency="PKR",
            rating=4.7,
            review_count=45,
            available=True
        )
    ]


# 1. Scoring Engine Tests
def test_scoring_engine_quality_gate(sample_product):
    breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
        candidate_product=sample_product,
        data_quality_score=65.0, # Below 70 quality gate
        trend_score=80.0
    )
    assert breakdown.eligibility_status == "quality_gated"
    assert conf <= 0.40
    assert breakdown.total_opportunity_score < 50.0


def test_scoring_engine_anomaly_blocking(sample_product):
    critical_anomaly = [{
        "anomaly_type": "price_spike",
        "severity": "critical",
        "status": "active"
    }]
    breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
        candidate_product=sample_product,
        data_quality_score=90.0,
        active_anomalies=critical_anomaly,
        opportunity_type="price_opportunity"
    )
    assert breakdown.eligibility_status == "anomaly_blocked"
    assert breakdown.price_opportunity_score == 0.0


def test_scoring_engine_deterministic_weights(sample_product):
    breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
        candidate_product=sample_product,
        data_quality_score=90.0,
        trend_score=80.0,
        coverage_gap_ratio=0.5,
        price_spread_pct=15.0,
        cross_platform_count=2,
        freshness_status="fresh"
    )
    assert breakdown.eligibility_status == "eligible"
    assert score > 70.0
    assert conf >= 0.85
    assert breakdown.evidence_strength_score > 0
    assert breakdown.trend_strength_score > 0
    assert breakdown.market_coverage_gap_score > 0
    assert breakdown.price_opportunity_score > 0
    assert breakdown.product_quality_score > 0
    assert breakdown.cross_platform_evidence_score > 0
    assert breakdown.freshness_score > 0


def test_scoring_engine_freshness_tiers(sample_product):
    bd_fresh, s_fresh, _ = MarketOpportunityScoringEngine.calculate_score(sample_product, freshness_status="fresh")
    bd_stale, s_stale, _ = MarketOpportunityScoringEngine.calculate_score(sample_product, freshness_status="stale")
    assert bd_fresh.freshness_score > bd_stale.freshness_score
    assert s_fresh > s_stale


def test_confidence_tiers():
    assert MarketOpportunityScoringEngine.get_confidence_tier(0.95) == "High"
    assert MarketOpportunityScoringEngine.get_confidence_tier(0.80) == "Medium"
    assert MarketOpportunityScoringEngine.get_confidence_tier(0.60) == "Low"
    assert MarketOpportunityScoringEngine.get_confidence_tier(0.30) == "Needs Review"


# 2. Detectors Tests
def test_detect_product_gaps_single_platform(sample_product):
    opps = MarketOpportunityDetectors.detect_product_gaps(
        target_product=sample_product,
        data_quality_score=88.0,
        trend_score=75.0
    )
    assert len(opps) == 1
    opp = opps[0]
    assert opp.opportunity_type == "product_gap"
    assert "Shopify" in opp.missing_observed_platforms
    assert opp.score > 60.0
    assert opp.fingerprint is not None


def test_detect_product_gaps_multi_platform():
    multi_plat_prod = UnifiedProduct(
        id="uprod_002",
        unified_product_id="uprod_002",
        canonical_name="Bose 700",
        normalized_name="bose 700",
        platforms=["Daraz", "Shopify"],
        platform_count=2
    )
    opps = MarketOpportunityDetectors.detect_product_gaps(multi_plat_prod)
    assert len(opps) == 0


def test_detect_price_opportunities(sample_product, sample_listings):
    opps = MarketOpportunityDetectors.detect_price_opportunities(
        target_product=sample_product,
        platform_listings=sample_listings,
        data_quality_score=90.0
    )
    assert len(opps) == 1
    opp = opps[0]
    assert opp.opportunity_type == "price_opportunity"
    assert opp.evidence["price_spread_pct"] > 10.0
    assert opp.evidence["lowest_platform"] == "Daraz"


def test_detect_price_opportunities_currency_mismatch(sample_product):
    mixed_listings = [
        ProductPlatformListing(
            id="l1",
            listing_id="l1",
            unified_product_id="uprod_001",
            platform="Daraz",
            platform_product_id="p1",
            product_url="http://daraz/1",
            title="Sony Headset",
            normalized_title="Sony Headset",
            price=85000.0,
            currency="PKR"
        ),
        ProductPlatformListing(
            id="l2",
            listing_id="l2",
            unified_product_id="uprod_001",
            platform="Shopify",
            platform_product_id="p2",
            product_url="http://shop/1",
            title="Sony Headset",
            normalized_title="Sony Headset",
            price=399.0,
            currency="USD"
        )
    ]
    opps = MarketOpportunityDetectors.detect_price_opportunities(sample_product, mixed_listings)
    assert len(opps) == 1
    opp = opps[0]
    assert opp.status == "insufficient_data"
    assert "currency_comparison_unavailable" in opp.warnings


def test_detect_category_opportunities(sample_product):
    opps = MarketOpportunityDetectors.detect_category_opportunities(
        category="Audio",
        category_products=[sample_product],
        category_trend_score=75.0,
        data_quality_score=90.0
    )
    assert len(opps) == 1
    opp = opps[0]
    assert opp.opportunity_type == "category_opportunity"
    assert opp.category == "Audio"


def test_detect_competitive_gaps(sample_product):
    competitor = UnifiedProduct(
        id="uprod_audio_002",
        unified_product_id="uprod_audio_002",
        canonical_name="Generic BT Headphone",
        normalized_name="generic bt headphone",
        category="Audio",
        avg_rating=3.9,
        total_reviews=15,
        platforms=["Daraz"]
    )
    opps = MarketOpportunityDetectors.detect_competitive_gaps(
        target_product=sample_product,
        competitors=[sample_product, competitor],
        data_quality_score=90.0
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "competitive_gap"
    assert opps[0].evidence["competitor_product_id"] == "uprod_audio_002"


def test_detect_cross_platform_gaps(sample_product):
    opps = MarketOpportunityDetectors.detect_cross_platform_gaps(
        target_product=sample_product,
        data_quality_score=85.0
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "cross_platform_gap"
    assert "Shopify" in opps[0].missing_observed_platforms


def test_detect_availability_opportunities(sample_product):
    listings = [
        ProductPlatformListing(
            id="l1",
            listing_id="l1",
            unified_product_id=sample_product.unified_product_id,
            platform="Daraz",
            platform_product_id="p1",
            product_url="http://daraz/1",
            title="Sony XM5",
            normalized_title="Sony XM5",
            price=85000.0,
            available=False
        )
    ]
    opps = MarketOpportunityDetectors.detect_availability_opportunities(sample_product, listings)
    assert len(opps) == 1
    assert opps[0].opportunity_type == "availability_opportunity"
    assert "Daraz" in opps[0].evidence["out_of_stock_platforms"]


def test_detect_quality_gaps():
    p1 = UnifiedProduct(id="p1", unified_product_id="p1", canonical_name="P1", normalized_name="p1", category="Audio", completeness_score=0.5)
    p2 = UnifiedProduct(id="p2", unified_product_id="p2", canonical_name="P2", normalized_name="p2", category="Audio", completeness_score=0.9)
    opps = MarketOpportunityDetectors.detect_quality_gaps(
        category="Audio",
        category_products=[p1, p2],
        quality_score_map={"p1": 50.0, "p2": 90.0}
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "quality_gap"
    assert "data_quality_opportunity" in opps[0].warnings


def test_detect_rising_category():
    opps = MarketOpportunityDetectors.detect_rising_category(
        category="Wearables",
        category_trend_score=82.0,
        breakout_count=3
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "rising_category"
    assert opps[0].score == 82.0


def test_detect_rising_product(sample_product):
    opps = MarketOpportunityDetectors.detect_rising_product(
        target_product=sample_product,
        trend_score=88.0,
        trend_signals=["velocity_spike", "sentiment_burst"]
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "rising_product"
    assert opps[0].confidence >= 0.90


def test_detect_marketplace_expansion(sample_product):
    opps = MarketOpportunityDetectors.detect_marketplace_expansion(
        target_product=sample_product,
        data_quality_score=85.0
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "marketplace_expansion"
    assert "Shopify" in opps[0].missing_observed_platforms


def test_detect_underserved_category(sample_product):
    opps = MarketOpportunityDetectors.detect_underserved_category(
        category="Audio",
        category_products=[sample_product], # only 1 product
        category_trend_score=80.0
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "underserved_category"
    assert opps[0].score >= 80.0


def test_detect_product_launch_opportunities(sample_product):
    opps = MarketOpportunityDetectors.detect_product_launch_opportunities(
        target_product=sample_product,
        data_quality_score=92.0,
        trend_score=80.0
    )
    assert len(opps) == 1
    assert opps[0].opportunity_type == "product_launch_opportunity"


def test_sha256_fingerprint_idempotency():
    fp1 = MarketOpportunityDetectors.generate_fingerprint("uprod_01", "product_gap", ["k1", "k2"])
    fp2 = MarketOpportunityDetectors.generate_fingerprint("uprod_01", "product_gap", ["k2", "k1"]) # same keys different order
    assert fp1 == fp2
    assert len(fp1) == 64


# 3. Memory Manager Tests
def test_memory_manager_record_and_reinforce(opp_repo, sample_product):
    opp = MarketOpportunity(
        id="opp_test_01",
        unified_product_id=sample_product.unified_product_id,
        category=sample_product.category,
        opportunity_type="product_gap",
        score=85.0,
        confidence=0.88,
        status="active"
    )

    mem1 = MarketOpportunityMemoryManager.record_opportunity_pattern(opp_repo, opp, "Audio")
    assert mem1.occurrence_count == 1

    mem2 = MarketOpportunityMemoryManager.record_opportunity_pattern(opp_repo, opp, "Audio")
    assert mem2.occurrence_count == 2
    assert mem2.confidence_score > mem1.confidence_score

    # Check memory events
    events = opp_repo.list_memory_events("agent_market_opportunity_intelligence")
    assert len(events) == 2
    assert events[0].event_type in ("created", "reinforced")


def test_memory_manager_global_rule(opp_repo):
    rule_def = {"min_quality_threshold": 70.0, "min_reviews": 10}
    mem = MarketOpportunityMemoryManager.record_global_rule_memory(opp_repo, "rule_quality_gate", rule_def)
    assert mem.memory_key == "mem_market_opportunity_rules"
    assert "rule_quality_gate" in mem.memory_value


# 4. LLM Resolver Tests
@pytest.mark.asyncio
async def test_llm_resolver_deterministic_fallback(sample_product):
    opp = MarketOpportunity(
        id="opp_01",
        unified_product_id=sample_product.unified_product_id,
        opportunity_type="cross_platform_gap",
        score=75.0,
        confidence=0.85,
        reasons=["Observed single platform presence on Daraz."]
    )
    # No gemini provider provided -> should return deterministic fallback
    res = await MarketOpportunityLLMResolver.interpret_opportunity_with_gemini(sample_product, opp, gemini_provider=None)
    assert isinstance(res, MarketOpportunityLLMOutput)
    assert res.confidence == 0.85
    assert len(res.reasons) > 0


def test_llm_resolver_gating(sample_product):
    opp_clean = MarketOpportunity(id="o1", opportunity_type="product_gap", warnings=[])
    opp_warn = MarketOpportunity(id="o2", opportunity_type="price_opportunity", warnings=["currency_comparison_unavailable"])

    assert MarketOpportunityLLMResolver.should_invoke_llm([opp_clean], is_complex_strategy=False) is False
    assert MarketOpportunityLLMResolver.should_invoke_llm([opp_warn], is_complex_strategy=False) is True
    assert MarketOpportunityLLMResolver.should_invoke_llm([opp_clean], is_complex_strategy=True) is True


# 5. Agent Orchestrator Tests
@pytest.mark.asyncio
async def test_agent_analyze_product_opportunities(
    opp_repo, unified_repo, dq_repo, trend_repo, anomaly_repo, sample_product, sample_listings
):
    # Seed data
    unified_repo.upsert_unified_product(sample_product)
    for l in sample_listings:
        unified_repo.upsert_platform_listing(l)

    agent = MarketOpportunityIntelligenceAgent(
        opp_repo=opp_repo,
        unified_product_repo=unified_repo,
        data_quality_repo=dq_repo,
        trend_repo=trend_repo,
        anomaly_repo=anomaly_repo
    )

    summary = await agent.analyze_product_opportunities(sample_product.unified_product_id)
    assert isinstance(summary, MarketOpportunitySummary)
    assert summary.target_id == sample_product.unified_product_id
    assert summary.status == "ready"
    assert len(summary.opportunities) > 0
    assert summary.opportunity_score > 0

    # Verify repository persistence
    saved_opps = opp_repo.list_opportunities(unified_product_id=sample_product.unified_product_id)
    assert len(saved_opps) == len(summary.opportunities)

    # Verify audits
    audits = opp_repo.list_audits()
    assert len(audits) >= len(summary.opportunities)


@pytest.mark.asyncio
async def test_agent_analyze_category_opportunities(
    opp_repo, unified_repo, sample_product
):
    unified_repo.upsert_unified_product(sample_product)

    agent = MarketOpportunityIntelligenceAgent(
        opp_repo=opp_repo,
        unified_product_repo=unified_repo
    )

    summary = await agent.analyze_category_opportunities("Audio")
    assert summary.status == "ready"
    assert summary.category == "Audio"
    assert len(summary.opportunities) > 0


@pytest.mark.asyncio
async def test_agent_idempotent_rerun(
    opp_repo, unified_repo, sample_product
):
    unified_repo.upsert_unified_product(sample_product)
    agent = MarketOpportunityIntelligenceAgent(
        opp_repo=opp_repo,
        unified_product_repo=unified_repo
    )

    summary1 = await agent.analyze_product_opportunities(sample_product.unified_product_id)
    count1 = opp_repo.count_opportunities(unified_product_id=sample_product.unified_product_id)

    summary2 = await agent.analyze_product_opportunities(sample_product.unified_product_id)
    count2 = opp_repo.count_opportunities(unified_product_id=sample_product.unified_product_id)

    assert count1 == count2 # No duplicates created


@pytest.mark.asyncio
async def test_agent_pipeline_scan(
    opp_repo, unified_repo, sample_product
):
    unified_repo.upsert_unified_product(sample_product)
    agent = MarketOpportunityIntelligenceAgent(
        opp_repo=opp_repo,
        unified_product_repo=unified_repo
    )

    results = await agent.run_market_opportunity_pipeline(category="Audio", min_score=50.0)
    assert len(results) > 0


# 6. Repository Tests
def test_repo_filter_and_stats(opp_repo):
    opp1 = MarketOpportunity(
        id="opp_01",
        unified_product_id="prod_01",
        category="Audio",
        opportunity_type="product_gap",
        score=85.0,
        confidence=0.92,
        current_platforms=["Daraz"],
        status="active"
    )
    opp2 = MarketOpportunity(
        id="opp_02",
        unified_product_id="prod_02",
        category="Wearables",
        opportunity_type="price_opportunity",
        score=72.0,
        confidence=0.80,
        current_platforms=["Shopify"],
        status="active"
    )

    opp_repo.save_opportunity(opp1)
    opp_repo.save_opportunity(opp2)

    assert len(opp_repo.list_opportunities(category="Audio")) == 1
    assert len(opp_repo.list_opportunities(opportunity_type="price_opportunity")) == 1
    assert len(opp_repo.list_opportunities(min_score=80.0)) == 1

    stats = opp_repo.get_opportunity_stats()
    assert stats.total_opportunities == 2
    assert stats.high_confidence_count == 1
    assert stats.high_score_count == 1


def test_repo_candidate_review_workflow(opp_repo):
    cand = MarketOpportunityCandidate(
        id="cand_01",
        unified_product_id="prod_01",
        candidate_type="cross_platform_gap",
        composite_score=75.0,
        confidence=0.70,
        status="pending"
    )
    opp_repo.create_candidate(cand)

    pending = opp_repo.list_candidates(status="pending")
    assert len(pending) == 1

    resolved = opp_repo.resolve_candidate("cand_01", status="approved", reviewed_by="usr_admin")
    assert resolved.status == "approved"
    assert resolved.reviewed_by == "usr_admin"

    assert len(opp_repo.list_candidates(status="pending")) == 0


def test_scoring_engine_insufficient_data(sample_product):
    breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
        candidate_product=sample_product,
        freshness_status="insufficient_data"
    )
    assert conf == 0.30
    assert breakdown.freshness_score == 0.0


def test_detect_price_opportunities_zero_price(sample_product):
    zero_price_listings = [
        ProductPlatformListing(
            id="l1",
            listing_id="l1",
            unified_product_id="uprod_001",
            platform="Daraz",
            platform_product_id="p1",
            product_url="http://daraz/1",
            title="Sony Headset",
            normalized_title="Sony Headset",
            price=0.0,
            currency="PKR"
        ),
        ProductPlatformListing(
            id="l2",
            listing_id="l2",
            unified_product_id="uprod_001",
            platform="Shopify",
            platform_product_id="p2",
            product_url="http://shop/1",
            title="Sony Headset",
            normalized_title="Sony Headset",
            price=85000.0,
            currency="PKR"
        )
    ]
    opps = MarketOpportunityDetectors.detect_price_opportunities(sample_product, zero_price_listings)
    assert len(opps) == 0


def test_detect_competitive_gaps_no_competitors(sample_product):
    opps = MarketOpportunityDetectors.detect_competitive_gaps(
        target_product=sample_product,
        competitors=[sample_product], # no rival products
        data_quality_score=90.0
    )
    assert len(opps) == 0


@pytest.mark.asyncio
async def test_agent_missing_product(opp_repo, unified_repo):
    agent = MarketOpportunityIntelligenceAgent(
        opp_repo=opp_repo,
        unified_product_repo=unified_repo
    )
    summary = await agent.analyze_product_opportunities("non_existent_prod_999")
    assert summary.status == "insufficient_data"
    assert summary.confidence == 0.0
    assert "Target product not found in repository" in summary.warnings

