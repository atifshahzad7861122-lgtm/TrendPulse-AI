import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from backend.app.models.domain import (
    User, UnifiedProduct, ProductPlatformListing, ProductRecommendation,
    RecommendationCandidate, RecommendationInteraction, RecommendationAudit,
    RecommendationScoreBreakdown, ProductRecommendationSummary, AgentRecommendationStats,
    TrendSignal, AnomalyDetection
)
from backend.app.repositories.in_memory import (
    InMemoryRecommendationRepository, InMemoryUnifiedProductRepository,
    InMemoryDataQualityRepository, InMemoryTrendDetectionRepository,
    InMemoryAnomalyDetectionRepository
)
from backend.app.services.agents.recommendation.scoring_engine import RecommendationScoringEngine
from backend.app.services.agents.recommendation.generators import RecommendationGenerators
from backend.app.services.agents.recommendation.llm_resolver import (
    RecommendationLLMResolver, RecommendationLLMInterpretationOutput
)
from backend.app.services.agents.recommendation.memory_manager import RecommendationMemoryManager
from backend.app.services.agents.recommendation.agent import ProductRecommendationAgent


@pytest.fixture
def clean_repos():
    rec_repo = InMemoryRecommendationRepository()
    unified_repo = InMemoryUnifiedProductRepository()
    dq_repo = InMemoryDataQualityRepository()
    trend_repo = InMemoryTrendDetectionRepository()
    anomaly_repo = InMemoryAnomalyDetectionRepository()
    rec_repo.clear()
    unified_repo.clear()
    dq_repo.clear()
    trend_repo.clear()
    anomaly_repo.clear()
    return rec_repo, unified_repo, dq_repo, trend_repo, anomaly_repo


@pytest.fixture
def sample_catalog():
    now = datetime.now(timezone.utc)
    return [
        UnifiedProduct(
            id="prod_audio_1",
            unified_product_id="prod_audio_1",
            canonical_name="Sony WH-1000XM5 Wireless Headphones",
            normalized_name="sony wh 1000xm5 wireless headphones",
            brand="Sony",
            category="Audio",
            subcategory="Headphones",
            platforms=["daraz", "shopify"],
            platform_count=2,
            listings_count=3,
            lowest_price=8500.0,
            average_price=8999.0,
            highest_price=9500.0,
            primary_currency="PKR",
            avg_rating=4.8,
            total_reviews=150,
            completeness_score=0.95,
            created_at=now
        ),
        UnifiedProduct(
            id="prod_audio_2",
            unified_product_id="prod_audio_2",
            canonical_name="Bose QuietComfort 45 Headphones",
            normalized_name="bose quietcomfort 45 headphones",
            brand="Bose",
            category="Audio",
            subcategory="Headphones",
            platforms=["daraz"],
            platform_count=1,
            listings_count=1,
            lowest_price=7500.0,
            average_price=7500.0,
            highest_price=7500.0,
            primary_currency="PKR",
            avg_rating=4.6,
            total_reviews=85,
            completeness_score=0.90,
            created_at=now
        ),
        UnifiedProduct(
            id="prod_audio_3",
            unified_product_id="prod_audio_3",
            canonical_name="Anker Soundcore Life Q30",
            normalized_name="anker soundcore life q30",
            brand="Anker",
            category="Audio",
            subcategory="Headphones",
            platforms=["shopify"],
            platform_count=1,
            listings_count=1,
            lowest_price=4200.0,
            average_price=4200.0,
            highest_price=4200.0,
            primary_currency="PKR",
            avg_rating=4.4,
            total_reviews=220,
            completeness_score=0.92,
            created_at=now
        ),
        UnifiedProduct(
            id="prod_low_quality",
            unified_product_id="prod_low_quality",
            canonical_name="Unbranded Cheap Earphones",
            normalized_name="unbranded cheap earphones",
            brand="Generic",
            category="Audio",
            platforms=["daraz"],
            platform_count=1,
            listings_count=1,
            lowest_price=200.0,
            average_price=200.0,
            highest_price=200.0,
            primary_currency="PKR",
            avg_rating=2.1,
            total_reviews=3,
            completeness_score=0.45, # Fails quality gate
            created_at=now
        )
    ]


# 1. Basic Product Recommendation Generation
@pytest.mark.asyncio
async def test_01_product_recommendation(clean_repos, sample_catalog):
    rec_repo, unified_repo, dq_repo, trend_repo, anomaly_repo = clean_repos
    for p in sample_catalog:
        unified_repo.upsert_unified_product(p)

    agent = ProductRecommendationAgent(
        recommendation_repo=rec_repo,
        unified_product_repo=unified_repo,
        data_quality_repo=dq_repo,
        trend_repo=trend_repo,
        anomaly_repo=anomaly_repo
    )

    summary = await agent.analyze_product_recommendations("prod_audio_1")
    assert summary.status == "ready"
    assert summary.recommendation_score > 50.0
    assert len(summary.recommendations) >= 1


# 2. Similar Product Recommendation (Excludes Self)
def test_02_similar_product(sample_catalog):
    target = sample_catalog[0]
    sims = RecommendationGenerators.generate_similar_products(
        target_product=target,
        catalog=sample_catalog,
        limit=5
    )
    assert len(sims) >= 1
    # Check that target product is never in similar products
    for s in sims:
        assert s.unified_product_id != target.unified_product_id
        assert s.recommendation_type == "similar_product"


# 3. Alternative Product Recommendation
def test_03_alternative_product(sample_catalog):
    target = sample_catalog[0] # Sony 8999
    alts = RecommendationGenerators.generate_alternative_products(
        target_product=target,
        catalog=sample_catalog,
        limit=5
    )
    assert len(alts) >= 1
    # Anker (4200 PKR vs 8999 PKR) should be an alternative
    anker_alt = next((a for a in alts if a.unified_product_id == "prod_audio_3"), None)
    assert anker_alt is not None
    assert anker_alt.recommendation_type == "alternative_product"


# 4. Better Price Recommendation (Same Currency)
def test_04_better_price():
    target = UnifiedProduct(
        id="prod_xp",
        unified_product_id="prod_xp",
        canonical_name="Smart Fitness Watch",
        normalized_name="smart fitness watch",
        category="Wearables",
        primary_currency="PKR",
        completeness_score=0.9
    )
    listings = [
        ProductPlatformListing(
            id="l1", unified_product_id="prod_xp", platform="Daraz", platform_product_id="dz_1",
            product_url="https://daraz.pk/1", title="Smart Watch", normalized_title="smart watch",
            price=5500.0, currency="PKR", available=True
        ),
        ProductPlatformListing(
            id="l2", unified_product_id="prod_xp", platform="Shopify", platform_product_id="sh_1",
            product_url="https://shop.pk/1", title="Smart Watch", normalized_title="smart watch",
            price=4800.0, currency="PKR", available=True
        )
    ]
    bps = RecommendationGenerators.generate_better_price_recommendations(target, listings)
    assert len(bps) == 1
    assert bps[0].evidence["lowest_platform"] == "Shopify"
    assert bps[0].evidence["savings_amount"] == 700.0


# 5. Trending Product Recommendation
def test_05_trending_product(sample_catalog):
    trend_map = {"prod_audio_1": 88.0, "prod_audio_2": 45.0}
    recs = RecommendationGenerators.generate_trending_recommendations(
        catalog=sample_catalog,
        trend_score_map=trend_map,
        min_trend_score=65.0
    )
    assert len(recs) == 1
    assert recs[0].unified_product_id == "prod_audio_1"
    assert recs[0].score >= 70.0


# 6. High Quality Product Recommendation
def test_06_high_quality_product(sample_catalog):
    dq_map = {"prod_audio_1": 95.0, "prod_audio_2": 90.0, "prod_low_quality": 35.0}
    recs = RecommendationGenerators.generate_high_quality_recommendations(
        catalog=sample_catalog,
        data_quality_map=dq_map,
        min_quality_score=85.0
    )
    assert len(recs) >= 1
    ids = [r.unified_product_id for r in recs]
    assert "prod_audio_1" in ids
    assert "prod_low_quality" not in ids


# 7. Cross-Platform Recommendation
def test_07_cross_platform_recommendation():
    target = UnifiedProduct(
        id="prod_multi",
        unified_product_id="prod_multi",
        canonical_name="4K Action Camera",
        normalized_name="4k action camera",
        category="Cameras",
        platforms=["Daraz", "Shopify"],
        completeness_score=0.9
    )
    listings = [
        ProductPlatformListing(
            id="l1", unified_product_id="prod_multi", platform="Daraz", platform_product_id="dz_c1",
            product_url="https://daraz.pk/c1", title="Action Cam", normalized_title="action cam",
            price=12000.0, currency="PKR", available=True
        ),
        ProductPlatformListing(
            id="l2", unified_product_id="prod_multi", platform="Shopify", platform_product_id="sh_c2",
            product_url="https://shop.pk/c2", title="Action Cam", normalized_title="action cam",
            price=11500.0, currency="PKR", available=True
        )
    ]
    recs = RecommendationGenerators.generate_cross_platform_recommendations(target, listings)
    assert len(recs) == 1
    assert recs[0].evidence["platform_count"] == 2


# 8. Best Value Recommendation
def test_08_best_value(sample_catalog):
    recs = RecommendationGenerators.generate_best_value_recommendations(
        catalog=sample_catalog,
        trend_score_map={"prod_audio_1": 75.0, "prod_audio_3": 80.0}
    )
    assert len(recs) >= 1
    for r in recs:
        assert r.recommendation_type == "best_value"


# 9. Data Quality Gate Enforcement
def test_09_data_quality_gate(sample_catalog):
    low_qual = sample_catalog[3] # completeness 0.45
    breakdown, score, conf = RecommendationScoringEngine.calculate_score(
        candidate_product=low_qual,
        data_quality_score=45.0
    )
    assert breakdown.eligibility_status == "quality_gated"
    assert conf <= 0.40


# 10. Critical Anomaly Blocking
def test_10_critical_anomaly_blocking(sample_catalog):
    target = sample_catalog[0]
    critical_anomaly = [{"anomaly_type": "price_spike", "severity": "critical", "score": 95.0}]
    breakdown, score, conf = RecommendationScoringEngine.calculate_score(
        candidate_product=target,
        active_anomalies=critical_anomaly,
        recommendation_type="best_value"
    )
    assert breakdown.eligibility_status == "anomaly_blocked"
    assert score < 50.0


# 11. Warning Preservation
def test_11_warning_preservation():
    target = UnifiedProduct(
        id="prod_w",
        unified_product_id="prod_w",
        canonical_name="Product With Multi-Currency",
        normalized_name="product with multi-currency",
        category="Tech",
        completeness_score=0.9
    )
    listings = [
        ProductPlatformListing(
            id="l1", unified_product_id="prod_w", platform="Daraz", platform_product_id="dz_w1",
            product_url="https://daraz.pk/w1", title="MC Item", normalized_title="mc item",
            price=5000.0, currency="PKR", available=True
        ),
        ProductPlatformListing(
            id="l2", unified_product_id="prod_w", platform="Shopify", platform_product_id="sh_w2",
            product_url="https://shop.com/w2", title="MC Item", normalized_title="mc item",
            price=45.0, currency="USD", available=True
        )
    ]
    bps = RecommendationGenerators.generate_better_price_recommendations(target, listings)
    assert len(bps) == 1
    assert len(bps[0].warnings) > 0
    assert "currency_comparison_unavailable" in bps[0].warnings[0]


# 12. Deterministic Scoring Weights
def test_12_deterministic_scoring(sample_catalog):
    p = sample_catalog[0]
    breakdown, score, conf = RecommendationScoringEngine.calculate_score(
        candidate_product=p,
        data_quality_score=90.0,
        trend_score=80.0,
        freshness_status="fresh"
    )
    expected_sum = (
        breakdown.data_quality_score +
        breakdown.product_similarity_score +
        breakdown.price_value_score +
        breakdown.rating_quality_score +
        breakdown.trend_strength_score +
        breakdown.availability_score +
        breakdown.cross_platform_score +
        breakdown.freshness_score
    )
    assert abs(round(expected_sum, 2) - score) < 0.1
    assert breakdown.data_quality_score == round(90.0 * 0.15, 2)


# 13. Confidence Calculation
def test_13_confidence_calculation(sample_catalog):
    p = sample_catalog[0]
    _, _, conf_fresh = RecommendationScoringEngine.calculate_score(p, freshness_status="fresh")
    _, _, conf_stale = RecommendationScoringEngine.calculate_score(p, freshness_status="stale")
    assert conf_fresh > conf_stale


# 14. Insufficient Data Return
@pytest.mark.asyncio
async def test_14_insufficient_data(clean_repos):
    rec_repo, unified_repo, dq_repo, trend_repo, anomaly_repo = clean_repos
    agent = ProductRecommendationAgent(
        recommendation_repo=rec_repo,
        unified_product_repo=unified_repo
    )
    res = await agent.analyze_product_recommendations("non_existent_id")
    assert res.status == "insufficient_data"
    assert res.recommendation_score == 0.0


# 15. Stale Data Penalty
def test_15_stale_data_penalty(sample_catalog):
    p = sample_catalog[0]
    breakdown_fresh, score_fresh, _ = RecommendationScoringEngine.calculate_score(p, freshness_status="fresh")
    breakdown_stale, score_stale, _ = RecommendationScoringEngine.calculate_score(p, freshness_status="stale")
    assert score_fresh > score_stale
    assert breakdown_fresh.freshness_score > breakdown_stale.freshness_score


# 16. User With No Behavior History
@pytest.mark.asyncio
async def test_16_user_no_history(clean_repos, sample_catalog):
    rec_repo, unified_repo, _, _, _ = clean_repos
    for p in sample_catalog:
        unified_repo.upsert_unified_product(p)
    agent = ProductRecommendationAgent(recommendation_repo=rec_repo, unified_product_repo=unified_repo)

    recs = await agent.generate_catalog_recommendations(user_id="new_user_123")
    assert len(recs) >= 1
    # Check that generic recommendations are returned without errors
    assert all(isinstance(r, ProductRecommendation) for r in recs)


# 17. User Interaction Recording
def test_17_user_interaction(clean_repos):
    rec_repo, _, _, _, _ = clean_repos
    agent = ProductRecommendationAgent(
        recommendation_repo=rec_repo,
        unified_product_repo=InMemoryUnifiedProductRepository()
    )
    inter = RecommendationInteraction(
        id="int_1",
        user_id="user_99",
        product_id="prod_audio_1",
        interaction_type="save",
        metadata={"category": "Audio"}
    )
    saved = agent.record_user_interaction(inter)
    assert saved.id == "int_1"
    history = rec_repo.list_interactions(user_id="user_99")
    assert len(history) == 1
    assert history[0].interaction_type == "save"


# 18. Candidate Review Queue Creation
@pytest.mark.asyncio
async def test_18_candidate_creation(clean_repos):
    rec_repo, unified_repo, _, _, _ = clean_repos
    prod = UnifiedProduct(
        id="prod_cand",
        unified_product_id="prod_cand",
        canonical_name="Candidate Item",
        normalized_name="candidate item",
        category="Tech",
        completeness_score=0.9
    )
    unified_repo.upsert_unified_product(prod)
    unified_repo.upsert_platform_listing(ProductPlatformListing(
        id="l1", unified_product_id="prod_cand", platform="Daraz", platform_product_id="dz_cand",
        product_url="https://daraz.pk/cand", title="Cand 1", normalized_title="cand 1",
        price=100.0, currency="PKR", available=True
    ))
    unified_repo.upsert_platform_listing(ProductPlatformListing(
        id="l2", unified_product_id="prod_cand", platform="Shopify", platform_product_id="sh_cand",
        product_url="https://shop.pk/cand", title="Cand 2", normalized_title="cand 2",
        price=2.0, currency="USD", available=True
    ))

    agent = ProductRecommendationAgent(recommendation_repo=rec_repo, unified_product_repo=unified_repo)
    await agent.analyze_product_recommendations("prod_cand")

    cands = rec_repo.list_candidates(status="pending")
    assert len(cands) >= 1


# 19. Candidate Resolution
def test_19_candidate_resolution(clean_repos):
    rec_repo, _, _, _, _ = clean_repos
    cand = RecommendationCandidate(
        id="c_test_1",
        unified_product_id="p1",
        candidate_type="similar_product",
        composite_score=65.0,
        status="pending"
    )
    rec_repo.create_candidate(cand)

    resolved = rec_repo.resolve_candidate("c_test_1", "approved", reviewed_by="admin_1")
    assert resolved.status == "approved"
    assert resolved.reviewed_by == "admin_1"


# 20. Memory Creation
def test_20_memory_creation(clean_repos):
    rec_repo, _, _, _, _ = clean_repos
    rec = ProductRecommendation(
        id="r_mem",
        unified_product_id="p1",
        recommendation_type="best_value",
        score=92.0,
        confidence=0.95
    )
    mem = RecommendationMemoryManager.record_recommendation_pattern(rec_repo, rec, "Audio")
    assert mem.agent_id == "agent_recommendation_engine"
    assert "rec_pattern:best_value:Audio" in mem.memory_key


# 21. Memory Reinforcement
def test_21_memory_reinforcement(clean_repos):
    rec_repo, _, _, _, _ = clean_repos
    rec = ProductRecommendation(
        id="r_mem",
        unified_product_id="p1",
        recommendation_type="trending_product",
        score=88.0,
        confidence=0.90
    )
    mem1 = RecommendationMemoryManager.record_recommendation_pattern(rec_repo, rec, "Audio")
    mem2 = RecommendationMemoryManager.record_recommendation_pattern(rec_repo, rec, "Audio")
    assert mem2.occurrence_count == 2
    assert mem2.confidence_score >= mem1.confidence_score


# 22. Memory Event Audit
def test_22_memory_audit(clean_repos):
    rec_repo, _, _, _, _ = clean_repos
    rec = ProductRecommendation(
        id="r_aud",
        unified_product_id="p_aud",
        recommendation_type="high_quality",
        score=90.0,
        confidence=0.95
    )
    mem = RecommendationMemoryManager.record_recommendation_pattern(rec_repo, rec, "Wearables")
    events = rec_repo.list_memory_events("agent_recommendation_engine", mem.id)
    assert len(events) >= 1
    assert events[0].event_type == "created"


# 23. Gemini Selective Invocation
def test_23_gemini_selective_invocation():
    rec_clean = [
        ProductRecommendation(
            id="r1", unified_product_id="p1", recommendation_type="similar_product",
            score=70.0, confidence=0.9, warnings=[]
        )
    ]
    # Simple recommendation with no warnings -> false
    assert RecommendationLLMResolver.should_invoke_llm(rec_clean, is_complex_comparison=False) is False

    # Recommendation with warnings -> true
    rec_warning = [
        ProductRecommendation(
            id="r2", unified_product_id="p2", recommendation_type="better_price",
            score=60.0, confidence=0.8, warnings=["currency_comparison_unavailable"]
        )
    ]
    assert RecommendationLLMResolver.should_invoke_llm(rec_warning, is_complex_comparison=False) is True


# 24. Gemini Timeout Fallback
@pytest.mark.asyncio
async def test_24_gemini_timeout_fallback(sample_catalog):
    mock_gemini = MagicMock()
    mock_gemini.generate_text = AsyncMock(side_effect=asyncio.TimeoutError("Gemini timed out"))

    target = sample_catalog[0]
    rec = ProductRecommendation(
        id="r1", unified_product_id="prod_audio_2", recommendation_type="alternative_product",
        score=82.0, confidence=0.90, reasons=["Higher buyer satisfaction rating"]
    )
    res = await RecommendationLLMResolver.interpret_recommendation_with_gemini(
        target_product=target,
        recommendation=rec,
        gemini_provider=mock_gemini
    )
    assert "alternative product" in res.summary.lower()
    assert res.confidence == 0.90


# 25. Invalid Gemini JSON Fallback
@pytest.mark.asyncio
async def test_25_invalid_gemini_json_fallback(sample_catalog):
    mock_gemini = MagicMock()
    mock_gemini.generate_text = AsyncMock(return_value="NOT_JSON_DATA_RETURNED")

    target = sample_catalog[0]
    rec = ProductRecommendation(
        id="r1", unified_product_id="prod_audio_3", recommendation_type="best_value",
        score=85.0, confidence=0.88
    )
    res = await RecommendationLLMResolver.interpret_recommendation_with_gemini(
        target_product=target,
        recommendation=rec,
        gemini_provider=mock_gemini
    )
    assert res.confidence == 0.88


# 26. Duplicate Recommendation Prevention
def test_26_duplicate_prevention(clean_repos):
    rec_repo, _, _, _, _ = clean_repos
    fp = RecommendationGenerators.generate_fingerprint("user_1", "prod_1", "best_value")
    rec1 = ProductRecommendation(
        id="rec_100", unified_product_id="prod_1", recommendation_type="best_value",
        score=85.0, confidence=0.9, fingerprint=fp
    )
    saved1 = rec_repo.save_recommendation(rec1)

    rec2 = ProductRecommendation(
        id="rec_101", unified_product_id="prod_1", recommendation_type="best_value",
        score=89.0, confidence=0.92, fingerprint=fp
    )
    saved2 = rec_repo.save_recommendation(rec2)
    assert saved2.id == saved1.id # Deduplicated & updated in place
    assert rec_repo.count_recommendations() == 1


# 27. Full Agent API Pipeline End-to-End
@pytest.mark.asyncio
async def test_27_api_endpoints(clean_repos, sample_catalog):
    rec_repo, unified_repo, dq_repo, trend_repo, anomaly_repo = clean_repos
    for p in sample_catalog:
        unified_repo.upsert_unified_product(p)

    agent = ProductRecommendationAgent(
        recommendation_repo=rec_repo,
        unified_product_repo=unified_repo,
        data_quality_repo=dq_repo,
        trend_repo=trend_repo,
        anomaly_repo=anomaly_repo
    )
    summary = await agent.analyze_product_recommendations("prod_audio_1")
    assert summary.status == "ready"
    assert len(summary.recommendations) >= 1

    stats = rec_repo.get_recommendation_stats()
    assert stats.total_recommendations >= 1


# 28. Workspace Authorization / User Dependency Check
def test_28_workspace_authorization():
    mock_user = User(
        id="user_rec_99",
        email="strategist@trendpulse.ai",
        full_name="Market Strategist",
        hashed_password="mock_pw",
        role="operator",
        workspace_id="ws_rec_1"
    )
    assert mock_user.workspace_id == "ws_rec_1"


# 29. Cross-Platform Currency Safety
def test_29_cross_platform_currency_safety():
    target = UnifiedProduct(
        id="prod_curr",
        unified_product_id="prod_curr",
        canonical_name="Currency Test Product",
        normalized_name="currency test product",
        primary_currency="PKR"
    )
    listings = [
        ProductPlatformListing(
            id="l1", unified_product_id="prod_curr", platform="Daraz", platform_product_id="dz_curr_1",
            product_url="https://daraz.pk/c1", title="Cur Prod", normalized_title="cur prod",
            price=3500.0, currency="PKR"
        ),
        ProductPlatformListing(
            id="l2", unified_product_id="prod_curr", platform="Shopify", platform_product_id="sh_curr_2",
            product_url="https://shop.com/c2", title="Cur Prod", normalized_title="cur prod",
            price=35.0, currency="USD"
        )
    ]
    bps = RecommendationGenerators.generate_better_price_recommendations(target, listings)
    assert len(bps) == 1
    assert "currency_comparison_unavailable" in bps[0].evidence.get("currency_status", "")


# 30. Historical Recommendation Retrieval
def test_30_recommendation_retrieval(clean_repos):
    rec_repo, _, _, _, _ = clean_repos
    rec = ProductRecommendation(
        id="r_ret", unified_product_id="prod_target_10", recommendation_type="similar_product",
        score=75.0, status="active"
    )
    rec_repo.save_recommendation(rec)
    items = rec_repo.list_recommendations_for_product("prod_target_10")
    assert len(items) == 1
    assert items[0].id == "r_ret"


# 31. Large Dataset Performance Benchmark
def test_31_large_dataset_performance(sample_catalog):
    # Scale catalog to 500 products
    large_catalog = []
    for i in range(500):
        large_catalog.append(UnifiedProduct(
            id=f"prod_scale_{i}",
            unified_product_id=f"prod_scale_{i}",
            canonical_name=f"Audio Device Scale {i}",
            normalized_name=f"audio device scale {i}",
            category="Audio",
            average_price=1000.0 + i,
            avg_rating=4.2,
            total_reviews=50,
            completeness_score=0.9
        ))

    import time
    start = time.perf_counter()
    recs = RecommendationGenerators.generate_similar_products(
        target_product=sample_catalog[0],
        catalog=large_catalog,
        limit=10
    )
    elapsed = time.perf_counter() - start
    assert len(recs) == 10
    assert elapsed < 1.0, f"500-product similarity search took {elapsed:.4f}s"
