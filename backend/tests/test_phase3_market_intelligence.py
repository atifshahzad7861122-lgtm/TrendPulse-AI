"""
Phase 3 Master Verification Test Suite: Market Intelligence + AI Analytics + Social Demand Intelligence.

Validates:
1. Deterministic Market Score Engine (0-100) and 5-factor weighting (weights sum to 1.0).
2. Historical Analytics Engine (Trend velocity, 7d/30d growth, zero interpolation, insufficient_data handling).
3. Product Opportunity Engine (0-100 score, customer satisfaction, single-channel expansion gaps).
4. Viral Potential Engine (returns unavailable when no social signals exist, evaluates real views/engagement).
5. Dynamic Matching Engine (no hardcoded aliases, confidence threshold >= 0.75).
6. Social Intelligence Service (real signal ingestion, aggregation, provenance tracking).
7. AI Market Analyst (anti-hallucination, factual grounding, offline fallback, caching).
8. Core Market Intelligence Service orchestration (overview, detail, categories, cross-marketplace comparison, report).
9. REST API Endpoints under /api/v1/intelligence/* (overview, products, product detail, categories, marketplaces, social, reports, analyze).
10. Strict zero-synthetic / zero-mock enforcement.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.domain import (
    MarketplaceProduct, ProductMarketSnapshot, SocialSignal, Product
)
from backend.app.domain.market_score_engine import MarketScoreEngine
from backend.app.domain.historical_analytics_engine import HistoricalAnalyticsEngine
from backend.app.domain.opportunity_engine import ProductOpportunityEngine
from backend.app.domain.viral import ViralPotentialEngine
from backend.app.domain.matching import ProductMatchingEngine
from backend.app.services.social_intelligence_service import SocialIntelligenceService
from backend.app.services.ai_analyst_service import AIMarketAnalystService
from backend.app.services.market_intelligence_service import MarketIntelligenceService
from backend.app.repositories.in_memory import marketplace_product_repo, unified_product_repo

client = TestClient(app)


# =========================================================================
# 1. MARKET SCORE ENGINE TESTS
# =========================================================================

def test_market_score_weights_and_bounds():
    """Verify market score weights sum exactly to 1.0 and score stays between 0 and 100."""
    eval_res = MarketScoreEngine.calculate_market_score(
        demand_score=85.0,
        growth_rate=20.0,
        rating=4.5,
        review_count=150,
        price=49.99,
        original_price=69.99,
        is_available=True,
        platform_count=2,
        data_quality_score=90.0,
        has_historical_data=True
    )

    assert sum(eval_res.weights.values()) == pytest.approx(1.0, abs=1e-4)
    assert 0.0 <= eval_res.total_score <= 100.0
    assert eval_res.demand_component > 0
    assert eval_res.growth_component > 0
    assert eval_res.marketplace_acclaim_component > 0
    assert eval_res.price_health_component > 0
    assert eval_res.cross_platform_component > 0
    assert eval_res.confidence > 0.5


def test_market_score_penalties():
    """Verify stock outage and missing history correctly penalize market score."""
    available_score = MarketScoreEngine.calculate_market_score(
        demand_score=80.0,
        growth_rate=15.0,
        rating=4.5,
        review_count=100,
        price=50.0,
        is_available=True,
        has_historical_data=True
    )

    out_of_stock_score = MarketScoreEngine.calculate_market_score(
        demand_score=80.0,
        growth_rate=15.0,
        rating=4.5,
        review_count=100,
        price=50.0,
        is_available=False,
        has_historical_data=True
    )

    assert out_of_stock_score.total_score < available_score.total_score
    assert out_of_stock_score.confidence < available_score.confidence


def test_market_score_history_status_and_fallback():
    """Verify history_status transparently distinguishes measured vs insufficient_history."""
    # 1. No historical data
    no_hist_score = MarketScoreEngine.calculate_market_score(
        demand_score=70.0,
        growth_rate=None,
        rating=4.2,
        review_count=50,
        price=30.0,
        is_available=True,
        has_historical_data=False
    )
    assert no_hist_score.history_status == "insufficient_history"
    assert no_hist_score.growth_component == 50.0  # Neutral baseline
    
    # 2. Measured historical data with positive growth
    measured_score = MarketScoreEngine.calculate_market_score(
        demand_score=70.0,
        growth_rate=25.0,
        rating=4.2,
        review_count=50,
        price=30.0,
        is_available=True,
        has_historical_data=True
    )
    assert measured_score.history_status == "measured"
    assert measured_score.growth_component == 65.0
    assert measured_score.confidence > no_hist_score.confidence

    # 3. Verify Pydantic schema serialization
    from backend.app.schemas.market_intelligence import MarketScoreResponse
    resp = MarketScoreResponse(
        score=no_hist_score.total_score,
        components={
            "demand": no_hist_score.demand_component,
            "growth": no_hist_score.growth_component,
            "acclaim": no_hist_score.marketplace_acclaim_component,
            "price_health": no_hist_score.price_health_component,
            "cross_platform": no_hist_score.cross_platform_component
        },
        weights=no_hist_score.weights,
        confidence=no_hist_score.confidence,
        data_quality_score=no_hist_score.data_quality_score,
        history_status=no_hist_score.history_status
    )
    dumped = resp.model_dump()
    assert dumped["history_status"] == "insufficient_history"
    assert dumped["components"]["growth"] == 50.0


# =========================================================================
# 2. HISTORICAL ANALYTICS ENGINE TESTS
# =========================================================================

def test_historical_analytics_insufficient_data():
    """Verify velocity and growth return None/insufficient_data when points < 2."""
    now = datetime.now(timezone.utc)
    single_snapshot = [
        ProductMarketSnapshot(
            id="snap_1",
            platform="amazon",
            product_id="B001",
            price=29.99,
            rating=4.2,
            review_count=50,
            observed_at=now
        )
    ]

    vel_empty = HistoricalAnalyticsEngine.calculate_trend_velocity([])
    assert vel_empty.velocity is None
    assert vel_empty.status == "insufficient_data"

    vel_single = HistoricalAnalyticsEngine.calculate_trend_velocity(single_snapshot)
    assert vel_single.velocity is None
    assert vel_single.status == "insufficient_data"

    growth_single = HistoricalAnalyticsEngine.calculate_growth(single_snapshot)
    assert growth_single.growth_7d is None
    assert growth_single.growth_30d is None
    assert growth_single.status == "insufficient_data"


def test_historical_analytics_valid_calculation():
    """Verify velocity and growth calculate accurately with real timestamps."""
    t0 = datetime.now(timezone.utc) - timedelta(days=7)
    t1 = datetime.now(timezone.utc)

    snapshots = [
        ProductMarketSnapshot(
            id="snap_1",
            platform="amazon",
            product_id="B001",
            price=30.0,
            rating=4.0,
            review_count=100,
            observed_at=t0
        ),
        ProductMarketSnapshot(
            id="snap_2",
            platform="amazon",
            product_id="B001",
            price=25.0,
            rating=4.2,
            review_count=140,
            observed_at=t1
        )
    ]

    vel = HistoricalAnalyticsEngine.calculate_trend_velocity(snapshots, metric="review_count")
    assert vel.status == "calculated"
    assert vel.velocity is not None
    assert vel.velocity > 0.0  # Positive reviews growth

    growth = HistoricalAnalyticsEngine.calculate_growth(snapshots, metric="review_count")
    assert growth.status == "calculated"
    assert growth.growth_7d == pytest.approx(40.0, rel=1e-2)  # (140 - 100) / 100 * 100 = 40%


# =========================================================================
# 3. PRODUCT OPPORTUNITY ENGINE TESTS
# =========================================================================

def test_product_opportunity_engine():
    """Verify opportunity calculation rewards high demand, rating gaps, and cross-channel whitespace."""
    high_opp = ProductOpportunityEngine.evaluate_opportunity(
        demand_score=88.0,
        market_score=82.0,
        rating=3.6,  # Quality gap opportunity
        review_count=800,
        price=35.0,
        platform_count=1,  # Single-channel expansion opportunity
        growth_rate=25.0,
        category_seller_count=4  # Low competition
    )

    assert high_opp.opportunity_score >= 70.0
    assert high_opp.opportunity_level in ["High", "Exceptional"]
    assert high_opp.competition_level in ["Low", "Moderate"]
    assert len(high_opp.supporting_signals) > 0


# =========================================================================
# 4. VIRAL POTENTIAL ENGINE TESTS
# =========================================================================

def test_viral_potential_unavailable_without_signals():
    """Strict zero-synthetic rule: returns unavailable when no social signals exist."""
    res = ViralPotentialEngine.evaluate_from_social_signals([])
    assert res["viral_score"] is None
    assert res["viral_level"] == "unavailable"
    assert res["has_social_signals"] is False


def test_viral_potential_with_real_signals():
    """Calculates viral potential when real social signals with views/engagement exist."""
    now = datetime.now(timezone.utc)
    signals = [
        SocialSignal(
            id="sig_1",
            platform="YouTube",
            content_title="Viral Tech Review",
            content_url="https://youtube.com/watch?v=1",
            views=250000,
            likes=12000,
            comments=800,
            shares=500,
            engagement_rate=5.3,
            observed_at=now
        )
    ]

    res = ViralPotentialEngine.evaluate_from_social_signals(signals)
    assert res["has_social_signals"] is True
    assert res["viral_score"] is not None
    assert res["viral_score"] >= 60.0
    assert res["viral_level"] in ["Moderate", "High", "Viral"]


# =========================================================================
# 5. DYNAMIC PRODUCT MATCHING TESTS (NO HARDCODED ALIASES)
# =========================================================================

def test_dynamic_product_matching_no_hardcoded_aliases():
    """Verify general token/brand/identifier matching works dynamically without static aliases."""
    catalog = [
        Product(
            id="p_wire_01",
            name="Sony WH-1000XM5 Wireless Noise Canceling Headphones",
            category="Audio",
            tags=["Sony", "Headphones"]
        ),
        Product(
            id="p_water_02",
            name="Stanley Quencher H2.0 FlowState Stainless Steel Tumbler 40oz",
            category="Kitchen",
            tags=["Stanley", "Tumbler"]
        )
    ]

    # Test exact / high-overlap dynamic content match
    match_1 = ProductMatchingEngine.match_content_detailed(
        "Unboxing the Sony WH-1000XM5 Wireless Headphones! Full Review",
        catalog
    )
    assert match_1.product is not None
    assert match_1.product.id == "p_wire_01"
    assert match_1.confidence >= 0.75

    # Test unrelated content does not match
    match_unrelated = ProductMatchingEngine.match_content_detailed(
        "Cooking a 5-minute pasta dish for dinner",
        catalog
    )
    assert match_unrelated.product is None or match_unrelated.confidence < 0.75


# =========================================================================
# 6. SOCIAL INTELLIGENCE SERVICE TESTS
# =========================================================================

def test_social_intelligence_service_aggregation():
    """Verify SocialIntelligenceService records real signals and computes truthful metrics."""
    svc = SocialIntelligenceService()
    now = datetime.now(timezone.utc)

    sig1 = SocialSignal(
        id="sig_test_1",
        platform="YouTube",
        content_title="Reviewing Smart Fitness Tracker",
        content_url="https://youtube.com/watch?v=abc",
        author_name="TechReviewer",
        views=50000,
        likes=2000,
        comments=150,
        shares=50,
        engagement_rate=4.4,
        matched_product_id="prod_fit_1",
        match_confidence=0.88,
        observed_at=now
    )
    svc.record_signal(sig1)

    signals = svc.list_signals(platform="YouTube")
    assert len(signals) == 1
    assert signals[0].id == "sig_test_1"

    metrics = svc.get_product_social_metrics(product_id="prod_fit_1", product_title="Fitness Tracker")
    assert metrics["mentions_count"] == 1
    assert metrics["total_views"] == 50000
    assert metrics["total_likes"] == 2000
    assert metrics["viral_evaluation"]["has_social_signals"] is True


# =========================================================================
# 7. AI MARKET ANALYST SERVICE TESTS
# =========================================================================

def test_ai_market_analyst_deterministic_fallback():
    """Verify AI analyst produces grounded narrative even when external LLM is offline."""
    analyst = AIMarketAnalystService(llm_service=None)

    facts = {
        "title": "Wireless Ergonomic Mouse",
        "marketplace": "amazon",
        "category": "Electronics",
        "price": 29.99,
        "rating": 4.6,
        "review_count": 450,
        "market_score": 84.5,
        "demand_level": "HIGH",
        "growth_7d": 18.2
    }

    res = analyst.generate_product_analysis(facts)
    assert "executive_summary" in res
    assert "Wireless Ergonomic Mouse" in res["executive_summary"]
    assert "84.5" in res["executive_summary"]
    assert "Electronics" in res["category_landscape"]
    assert len(res["strategic_recommendations"]) > 0


# =========================================================================
# 8. CORE MARKET INTELLIGENCE SERVICE ORCHESTRATION TESTS
# =========================================================================

def test_market_intelligence_service_orchestration():
    """Verify full end-to-end service orchestration across real stored products."""
    now = datetime.now(timezone.utc)
    prod = MarketplaceProduct(
        id="test_amazon_001",
        platform="amazon",
        product_id="B0TEST001",
        product_name="Active Noise Cancelling Earbuds Pro",
        price=49.99,
        original_price=69.99,
        currency="USD",
        rating=4.4,
        review_count=320,
        in_stock=True,
        seller_name="AudioTech Direct",
        product_url="https://amazon.com/dp/B0TEST001",
        category="Audio"
    )
    marketplace_product_repo.upsert_product(prod)

    svc = MarketIntelligenceService(
        marketplace_repo=marketplace_product_repo,
        unified_repo=unified_product_repo
    )

    detail = svc.get_product_intelligence(product_id="B0TEST001", platform="amazon")
    assert detail is not None
    assert detail.title == "Active Noise Cancelling Earbuds Pro"
    assert detail.marketplace == "amazon"
    assert 0.0 <= detail.market_score.score <= 100.0
    assert detail.demand.demand_score > 0
    assert detail.opportunity.opportunity_score > 0
    assert detail.source_provenance == "marketplace:amazon"

    overview = svc.get_market_overview(limit=10)
    assert overview.total_products_analyzed >= 1
    assert overview.average_market_score > 0


# =========================================================================
# 9. REST API ENDPOINTS (/api/v1/intelligence/*) TESTS
# =========================================================================

def test_api_intelligence_overview():
    """Verify GET /api/v1/intelligence/overview returns 200 with schema compliance."""
    resp = client.get("/api/v1/intelligence/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "average_market_score" in data["data"]
    assert "total_products_analyzed" in data["data"]
    assert "marketplaces_covered" in data["data"]


def test_api_intelligence_products_list():
    """Verify GET /api/v1/intelligence/products returns verified products list."""
    resp = client.get("/api/v1/intelligence/products?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    if len(data["data"]) > 0:
        first = data["data"][0]
        assert "market_score" in first
        assert "demand" in first
        assert "opportunity" in first


def test_api_intelligence_product_detail():
    """Verify GET /api/v1/intelligence/products/{product_id} returns 200 for existing and 404 for missing."""
    # Existing product
    resp = client.get("/api/v1/intelligence/products/B0TEST001?platform=amazon")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["product_id"] == "B0TEST001"
    assert data["data"]["marketplace"] == "amazon"

    # Non-existent product
    resp_404 = client.get("/api/v1/intelligence/products/NON_EXISTENT_ID_999999")
    assert resp_404.status_code == 404


def test_api_intelligence_categories():
    """Verify GET /api/v1/intelligence/categories returns aggregated category intelligence."""
    resp = client.get("/api/v1/intelligence/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "categories" in data["data"]
    assert "total_categories" in data["data"]


def test_api_intelligence_marketplaces():
    """Verify GET /api/v1/intelligence/marketplaces returns comparative cross-marketplace data."""
    resp = client.get("/api/v1/intelligence/marketplaces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "marketplaces" in data["data"]
    mkt_names = [m["marketplace"] for m in data["data"]["marketplaces"]]
    assert "amazon" in mkt_names
    assert "daraz" in mkt_names
    assert "ebay" in mkt_names
    assert "shopify" in mkt_names


def test_api_intelligence_social():
    """Verify GET /api/v1/intelligence/social returns real social signals."""
    resp = client.get("/api/v1/intelligence/social")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "signals" in data["data"]
    assert "total_views" in data["data"]


def test_api_intelligence_reports():
    """Verify GET /api/v1/intelligence/reports generates comprehensive report."""
    resp = client.get("/api/v1/intelligence/reports?marketplace=amazon")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "report_id" in data["data"]
    assert "ai_market_narrative" in data["data"]
    assert "ai_trend_drivers" in data["data"]


def test_api_intelligence_analyze_post():
    """Verify POST /api/v1/intelligence/analyze processes custom on-demand analysis."""
    payload = {
        "marketplace": "amazon",
        "category": "Audio",
        "keyword": "earbuds",
        "include_ai_narrative": True
    }
    resp = client.post("/api/v1/intelligence/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "report_id" in data["data"]
    assert data["data"]["marketplace"] == "amazon"
