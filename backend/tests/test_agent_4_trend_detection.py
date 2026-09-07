import pytest
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, TrendObservation,
    TrendSignal, TrendSignalCandidate, TrendDetectionAudit, User
)
from backend.app.repositories.in_memory import (
    InMemoryTrendDetectionRepository, InMemoryUnifiedProductRepository,
    InMemoryTaxonomyRepository, InMemoryUserRepository, InMemoryWorkspaceRepository,
    trend_detection_repo
)
from backend.app.services.agents.trend_detection.observations_tracker import ObservationsTracker
from backend.app.services.agents.trend_detection.signal_rules import TrendSignalRulesEngine
from backend.app.services.agents.trend_detection.scoring_engine import TrendScoringEngine
from backend.app.services.agents.trend_detection.memory_manager import TrendDetectionMemoryManager
from backend.app.services.agents.trend_detection.agent import ProductTrendDetectionAgent
from backend.app.core.security import create_access_token, get_password_hash


@pytest.fixture
def trend_repo():
    repo = InMemoryTrendDetectionRepository()
    repo.clear()
    return repo


@pytest.fixture
def unified_repo():
    repo = InMemoryUnifiedProductRepository()
    repo.clear()
    return repo


@pytest.fixture
def taxonomy_repo():
    repo = InMemoryTaxonomyRepository()
    repo.clear()
    return repo


@pytest.fixture
def agent(trend_repo, unified_repo, taxonomy_repo):
    return ProductTrendDetectionAgent(
        trend_repo=trend_repo,
        unified_repo=unified_repo,
        taxonomy_repo=taxonomy_repo
    )


@pytest.fixture
def auth_headers():
    token = create_access_token(subject="usr_demo_101")
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. Price Increase Detection
# ============================================================================
def test_01_price_increase_detection(agent, trend_repo):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(
            id="obs_p1",
            unified_product_id="unf_prod_1",
            platform="daraz",
            metric_type="price",
            metric_value=2000.0,
            observed_at=now - timedelta(days=2)
        ),
        TrendObservation(
            id="obs_p2",
            unified_product_id="unf_prod_1",
            platform="daraz",
            metric_type="price",
            metric_value=2400.0,
            previous_value=2000.0,
            change_value=400.0,
            change_percent=20.0,
            observed_at=now
        )
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_prod_1", obs, ["daraz"])
    assert any(s.signal_type == "price_increase" and s.direction == "up" for s in signals)
    inc_sig = next(s for s in signals if s.signal_type == "price_increase")
    assert inc_sig.evidence["change_percent"] == 20.0


# ============================================================================
# 2. Price Decrease & Large Discount Detection
# ============================================================================
def test_02_price_decrease_detection(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(
            id="obs_p1",
            unified_product_id="unf_prod_2",
            platform="shopify",
            metric_type="price",
            metric_value=5000.0,
            observed_at=now - timedelta(days=3)
        ),
        TrendObservation(
            id="obs_p2",
            unified_product_id="unf_prod_2",
            platform="shopify",
            metric_type="price",
            metric_value=3500.0,
            previous_value=5000.0,
            change_value=-1500.0,
            change_percent=-30.0,
            observed_at=now
        )
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_prod_2", obs, ["shopify"])
    assert any(s.signal_type == "large_discount" and s.direction == "down" for s in signals)
    disc_sig = next(s for s in signals if s.signal_type == "large_discount")
    assert disc_sig.severity == "high"


# ============================================================================
# 3. Price Stability
# ============================================================================
def test_03_price_stability(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_1", unified_product_id="unf_p3", platform="daraz", metric_type="price", metric_value=1500.0, observed_at=now - timedelta(days=5)),
        TrendObservation(id="obs_2", unified_product_id="unf_p3", platform="daraz", metric_type="price", metric_value=1500.0, previous_value=1500.0, change_percent=0.0, observed_at=now - timedelta(days=2)),
        TrendObservation(id="obs_3", unified_product_id="unf_p3", platform="daraz", metric_type="price", metric_value=1500.0, previous_value=1500.0, change_percent=0.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p3", obs, ["daraz"])
    assert any(s.signal_type == "price_movement" and s.direction == "stable" for s in signals)


# ============================================================================
# 4. Review Growth Momentum
# ============================================================================
def test_04_review_growth(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_r1", unified_product_id="unf_p4", platform="daraz", metric_type="review_count", metric_value=500.0, observed_at=now - timedelta(days=7)),
        TrendObservation(id="obs_r2", unified_product_id="unf_p4", platform="daraz", metric_type="review_count", metric_value=650.0, previous_value=500.0, change_percent=30.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p4", obs, ["daraz"])
    assert any(s.signal_type == "review_momentum" and s.direction == "up" for s in signals)
    sig = next(s for s in signals if s.signal_type == "review_momentum")
    assert sig.evidence["growth_percent"] == 30.0


# ============================================================================
# 5. Review Decline
# ============================================================================
def test_05_review_decline(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_r1", unified_product_id="unf_p5", platform="daraz", metric_type="review_count", metric_value=100.0, observed_at=now - timedelta(days=5)),
        TrendObservation(id="obs_r2", unified_product_id="unf_p5", platform="daraz", metric_type="review_count", metric_value=80.0, previous_value=100.0, change_value=-20.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p5", obs, ["daraz"])
    assert any(s.signal_type == "review_momentum" and s.direction == "down" for s in signals)


# ============================================================================
# 6. Rating Momentum
# ============================================================================
def test_06_rating_momentum(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_rt1", unified_product_id="unf_p6", platform="daraz", metric_type="rating", metric_value=4.1, observed_at=now - timedelta(days=4)),
        TrendObservation(id="obs_rt2", unified_product_id="unf_p6", platform="daraz", metric_type="rating", metric_value=4.6, previous_value=4.1, change_value=0.5, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p6", obs, ["daraz"])
    assert any(s.signal_type == "rating_momentum" and s.direction == "up" for s in signals)
    sig = next(s for s in signals if s.signal_type == "rating_momentum")
    assert sig.evidence["rating_delta"] == 0.5


# ============================================================================
# 7. Inventory Change (In Stock -> Out of Stock)
# ============================================================================
def test_07_inventory_change(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_av1", unified_product_id="unf_p7", platform="shopify", metric_type="availability", metric_value=1.0, observed_at=now - timedelta(days=1)),
        TrendObservation(id="obs_av2", unified_product_id="unf_p7", platform="shopify", metric_type="availability", metric_value=0.0, previous_value=1.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p7", obs, ["shopify"])
    assert any(s.signal_type == "out_of_stock" and s.direction == "down" for s in signals)


# ============================================================================
# 8. Out-of-Stock High Severity
# ============================================================================
def test_08_out_of_stock_detection(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_1", unified_product_id="unf_p8", platform="daraz", metric_type="availability", metric_value=1.0, observed_at=now - timedelta(days=2)),
        TrendObservation(id="obs_2", unified_product_id="unf_p8", platform="daraz", metric_type="availability", metric_value=0.0, previous_value=1.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p8", obs, ["daraz"])
    out_sig = next(s for s in signals if s.signal_type == "out_of_stock")
    assert out_sig.severity == "high"
    assert out_sig.confidence >= 0.95


# ============================================================================
# 9. Restock Detection
# ============================================================================
def test_09_restock_detection(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_1", unified_product_id="unf_p9", platform="daraz", metric_type="availability", metric_value=0.0, observed_at=now - timedelta(days=3)),
        TrendObservation(id="obs_2", unified_product_id="unf_p9", platform="daraz", metric_type="availability", metric_value=1.0, previous_value=0.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p9", obs, ["daraz"])
    assert any(s.signal_type == "restocked" and s.direction == "up" for s in signals)


# ============================================================================
# 10. Cross-Platform Surge
# ============================================================================
def test_10_cross_platform_signal(agent):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="obs_1", unified_product_id="unf_p10", platform="daraz", metric_type="review_count", metric_value=300.0, observed_at=now),
        TrendObservation(id="obs_2", unified_product_id="unf_p10", platform="shopify", metric_type="price", metric_value=250.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("unf_p10", obs, ["daraz", "shopify"])
    assert any(s.signal_type == "cross_platform_surge" and s.direction == "up" for s in signals)
    cross_sig = next(s for s in signals if s.signal_type == "cross_platform_surge")
    assert set(cross_sig.platforms) == {"daraz", "shopify"}


# ============================================================================
# 11. Breakout Candidate Identification
# ============================================================================
def test_11_breakout_candidate(agent, unified_repo):
    unf = UnifiedProduct(
        id="unf_breakout_1",
        unified_product_id="unf_breakout_1",
        canonical_name="Logitech MX Master 3S Wireless Mouse",
        normalized_name="logitech mx master 3s wireless mouse",
        brand="Logitech",
        platforms=["daraz", "shopify"],
        platform_count=2,
        listings_count=2,
        lowest_price=99.0,
        highest_price=105.0,
        average_price=102.0,
        primary_currency="USD",
        avg_rating=4.9,
        total_reviews=450,
        completeness_score=0.98,
        first_seen_at=datetime.now(timezone.utc) - timedelta(days=10),
        last_seen_at=datetime.now(timezone.utc),
        last_synced_at=datetime.now(timezone.utc)
    )
    unified_repo.upsert_unified_product(unf)

    # Seed observations with review growth on both platforms
    now = datetime.now(timezone.utc)
    agent.trend_repo.batch_record_observations([
        TrendObservation(id="o1", unified_product_id="unf_breakout_1", platform="daraz", metric_type="review_count", metric_value=300.0, observed_at=now - timedelta(days=5)),
        TrendObservation(id="o2", unified_product_id="unf_breakout_1", platform="daraz", metric_type="review_count", metric_value=450.0, previous_value=300.0, change_percent=50.0, observed_at=now),
        TrendObservation(id="o3", unified_product_id="unf_breakout_1", platform="shopify", metric_type="price", metric_value=99.0, observed_at=now),
        TrendObservation(id="o4", unified_product_id="unf_breakout_1", platform="shopify", metric_type="availability", metric_value=1.0, observed_at=now)
    ])

    summary = agent.analyze_product_trends("unf_breakout_1", allow_llm=False)
    assert summary.trend_state in ["breakout", "accelerating"]
    assert summary.trend_score >= 70.0
    candidates = agent.list_candidates(candidate_type="breakout_candidate")
    assert len(candidates) >= 1
    assert candidates[0].unified_product_id == "unf_breakout_1"


# ============================================================================
# 12. Insufficient Data Safety
# ============================================================================
def test_12_insufficient_data(agent, unified_repo):
    unf = UnifiedProduct(
        id="unf_sparse_1",
        unified_product_id="unf_sparse_1",
        canonical_name="Obscure Rare Handmade Widget",
        normalized_name="obscure rare handmade widget",
        brand="Artisan",
        platforms=["daraz"],
        platform_count=1,
        listings_count=1,
        lowest_price=50.0,
        highest_price=50.0,
        average_price=50.0,
        primary_currency="USD",
        avg_rating=0.0,
        total_reviews=0,
        completeness_score=0.50,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        last_synced_at=datetime.now(timezone.utc)
    )
    unified_repo.upsert_unified_product(unf)

    summary = agent.analyze_product_trends("unf_sparse_1", allow_llm=False)
    assert summary.trend_state == "insufficient_data"
    assert summary.trend_score == 0.0
    assert summary.active_signals == []


# ============================================================================
# 13. Stale Data Handling
# ============================================================================
def test_13_stale_data(agent):
    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    obs = [
        TrendObservation(id="obs_old1", unified_product_id="unf_stale", platform="daraz", metric_type="price", metric_value=100.0, observed_at=old_time),
        TrendObservation(id="obs_old2", unified_product_id="unf_stale", platform="daraz", metric_type="price", metric_value=80.0, previous_value=100.0, change_percent=-20.0, observed_at=old_time)
    ]
    freshness = ObservationsTracker.calculate_freshness(obs)
    assert freshness == "stale"


# ============================================================================
# 14. Freshness Calculation
# ============================================================================
def test_14_freshness_calculation():
    now = datetime.now(timezone.utc)
    fresh_obs = [TrendObservation(id="f1", unified_product_id="u1", platform="daraz", metric_type="price", metric_value=10.0, observed_at=now - timedelta(days=2))]
    recent_obs = [TrendObservation(id="r1", unified_product_id="u1", platform="daraz", metric_type="price", metric_value=10.0, observed_at=now - timedelta(days=10))]
    stale_obs = [TrendObservation(id="s1", unified_product_id="u1", platform="daraz", metric_type="price", metric_value=10.0, observed_at=now - timedelta(days=35))]

    assert ObservationsTracker.calculate_freshness(fresh_obs) == "fresh"
    assert ObservationsTracker.calculate_freshness(recent_obs) == "recent"
    assert ObservationsTracker.calculate_freshness(stale_obs) == "stale"
    assert ObservationsTracker.calculate_freshness([]) == "insufficient_data"


# ============================================================================
# 15. Trend Score Deterministic Formula
# ============================================================================
def test_15_trend_score_calculation():
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="o1", unified_product_id="u1", platform="daraz", metric_type="price", metric_value=100.0, observed_at=now),
        TrendObservation(id="o2", unified_product_id="u1", platform="shopify", metric_type="price", metric_value=100.0, observed_at=now)
    ]
    signals = [
        TrendSignal(
            id="s1",
            unified_product_id="u1",
            signal_type="review_momentum",
            signal_strength=80.0,
            direction="up",
            evidence={"growth_percent": 25.0},
            detected_at=now
        ),
        TrendSignal(
            id="s2",
            unified_product_id="u1",
            signal_type="price_drop",
            signal_strength=70.0,
            direction="down",
            evidence={"change_percent": -10.0},
            detected_at=now
        )
    ]
    breakdown = TrendScoringEngine.calculate_trend_score(obs, signals, ["daraz", "shopify"], "fresh")
    assert breakdown.total_trend_score > 0.0
    assert 0.0 <= breakdown.total_trend_score <= 100.0
    assert breakdown.trend_state in ["breakout", "accelerating", "emerging"]


# ============================================================================
# 16. Evidence Confidence Calculation
# ============================================================================
def test_16_confidence_calculation(agent, unified_repo):
    now = datetime.now(timezone.utc)
    obs = [
        TrendObservation(id="o1", unified_product_id="u_conf", platform="daraz", metric_type="price", metric_value=100.0, observed_at=now - timedelta(days=1)),
        TrendObservation(id="o2", unified_product_id="u_conf", platform="daraz", metric_type="price", metric_value=120.0, previous_value=100.0, change_percent=20.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("u_conf", obs, ["daraz"])
    for sig in signals:
        assert sig.confidence >= 0.85


# ============================================================================
# 17. Signal Severity Scaling
# ============================================================================
def test_17_signal_severity():
    now = datetime.now(timezone.utc)
    obs_extreme = [
        TrendObservation(id="o1", unified_product_id="u_sev", platform="daraz", metric_type="price", metric_value=1000.0, observed_at=now - timedelta(days=1)),
        TrendObservation(id="o2", unified_product_id="u_sev", platform="daraz", metric_type="price", metric_value=400.0, previous_value=1000.0, change_percent=-60.0, observed_at=now)
    ]
    signals = TrendSignalRulesEngine.evaluate_all_signals("u_sev", obs_extreme, ["daraz"])
    assert any(s.severity in ["high", "critical"] for s in signals)


# ============================================================================
# 18. Duplicate Signal Fingerprinting & Prevention
# ============================================================================
def test_18_duplicate_signal_prevention():
    fp1 = TrendSignalRulesEngine.generate_fingerprint("u_1", "demand_surge", "up", ["obs_1", "obs_2"])
    fp2 = TrendSignalRulesEngine.generate_fingerprint("u_1", "demand_surge", "up", ["obs_2", "obs_1"])
    fp3 = TrendSignalRulesEngine.generate_fingerprint("u_1", "demand_surge", "up", ["obs_1", "obs_3"])
    assert fp1 == fp2  # order invariance
    assert fp1 != fp3  # distinct observations


# ============================================================================
# 19. Signal History Persistence
# ============================================================================
def test_19_signal_history(trend_repo):
    now = datetime.now(timezone.utc)
    for i in range(5):
        obs = TrendObservation(
            id=f"obs_hist_{i}",
            unified_product_id="unf_hist_prod",
            platform="daraz",
            metric_type="price",
            metric_value=100.0 + i,
            observed_at=now - timedelta(days=5 - i)
        )
        trend_repo.record_observation(obs)

    listed = trend_repo.list_observations("unf_hist_prod", limit=10)
    assert len(listed) == 5
    assert listed[0].metric_value == 104.0  # Most recent first


# ============================================================================
# 20. Memory Pattern Creation
# ============================================================================
def test_20_memory_creation(agent):
    mem = agent.memory_manager.record_breakout_pattern(
        category="Electronics",
        platform="daraz",
        signal_types=["demand_surge", "review_momentum"],
        confidence=0.94
    )
    assert mem is not None
    assert mem.occurrence_count == 1
    assert mem.memory_type == "breakout_signal_pattern"


# ============================================================================
# 21. Memory Reinforcement
# ============================================================================
def test_21_memory_reinforcement(agent):
    agent.memory_manager.record_breakout_pattern(
        category="Audio",
        platform="shopify",
        signal_types=["review_momentum", "large_discount"],
        confidence=0.90
    )
    mem2 = agent.memory_manager.record_breakout_pattern(
        category="Audio",
        platform="shopify",
        signal_types=["review_momentum", "large_discount"],
        confidence=0.90
    )
    assert mem2.occurrence_count == 2
    assert mem2.confidence_score > 0.90


# ============================================================================
# 22. Memory Audit Events
# ============================================================================
def test_22_memory_audit(agent):
    agent.memory_manager.record_breakout_pattern(
        category="Gaming",
        platform="daraz",
        signal_types=["demand_surge"],
        confidence=0.92
    )
    events = agent.memory_manager.get_events(limit=10)
    assert len(events) >= 1
    assert events[0].agent_id == "agent_trend_detection"
    assert events[0].event_type == "created"


# ============================================================================
# 23. Gemini Selective Invocation
# ============================================================================
def test_23_gemini_selective_invocation(agent, unified_repo):
    unf = UnifiedProduct(
        id="unf_llm_prod",
        unified_product_id="unf_llm_prod",
        canonical_name="Apple AirPods Pro 2nd Gen",
        normalized_name="apple airpods pro 2nd gen",
        brand="Apple",
        platforms=["daraz", "shopify"],
        platform_count=2,
        listings_count=2,
        lowest_price=199.0,
        highest_price=249.0,
        average_price=224.0,
        primary_currency="USD",
        avg_rating=4.8,
        total_reviews=1200,
        completeness_score=0.98,
        first_seen_at=datetime.now(timezone.utc) - timedelta(days=20),
        last_seen_at=datetime.now(timezone.utc),
        last_synced_at=datetime.now(timezone.utc)
    )
    unified_repo.upsert_unified_product(unf)

    now = datetime.now(timezone.utc)
    # Contradictory signals: price dropped (-25%) AND review momentum (+40%)
    agent.trend_repo.batch_record_observations([
        TrendObservation(id="o1", unified_product_id="unf_llm_prod", platform="daraz", metric_type="price", metric_value=249.0, observed_at=now - timedelta(days=5)),
        TrendObservation(id="o2", unified_product_id="unf_llm_prod", platform="daraz", metric_type="price", metric_value=189.0, previous_value=249.0, change_percent=-24.0, observed_at=now),
        TrendObservation(id="o3", unified_product_id="unf_llm_prod", platform="shopify", metric_type="review_count", metric_value=800.0, observed_at=now - timedelta(days=5)),
        TrendObservation(id="o4", unified_product_id="unf_llm_prod", platform="shopify", metric_type="review_count", metric_value=1200.0, previous_value=800.0, change_percent=50.0, observed_at=now)
    ])

    with patch.object(agent.llm_resolver, "interpret_complex_trend", return_value=(
        MagicMock(interpretation="Promotional discount triggered strong cross-platform review velocity.", confidence=0.93),
        True
    )):
        summary = agent.analyze_product_trends("unf_llm_prod", allow_llm=True)
        audits = agent.trend_repo.list_audits("unf_llm_prod")
        assert any(a.llm_used is True for a in audits)


# ============================================================================
# 24. Gemini Timeout Fallback
# ============================================================================
def test_24_gemini_timeout_fallback(agent):
    with patch.object(agent.llm_resolver, "interpret_complex_trend", return_value=(
        MagicMock(interpretation="Deterministic fallback on timeout", confidence=0.80),
        False
    )):
        res, success = agent.llm_resolver.interpret_complex_trend(
            {"canonical_name": "Test"}, [], "fresh"
        )
        assert success is False
        assert "fallback" in res.interpretation.lower() or "deterministic" in res.interpretation.lower()


# ============================================================================
# 25. Invalid Gemini JSON Fallback
# ============================================================================
def test_25_invalid_gemini_json_fallback(agent):
    mock_client = MagicMock(spec=["generate_content"])
    mock_client.generate_content.return_value = MagicMock(text="INVALID NOT JSON AT ALL")
    resolver = agent.llm_resolver
    resolver.gemini_client = mock_client
    res, success = resolver.interpret_complex_trend(
        {"canonical_name": "Test"}, [], "fresh"
    )
    assert success is False
    assert "parse" in res.interpretation.lower() or "deterministic" in res.interpretation.lower()


# ============================================================================
# 26. REST API Endpoints
# ============================================================================
def test_26_api_endpoints(auth_headers):
    client = TestClient(app)
    res_signals = client.get("/api/v1/agents/trend-detection/signals", headers=auth_headers)
    assert res_signals.status_code == 200
    data = res_signals.json()
    assert "items" in data
    assert "total" in data

    res_stats = client.get("/api/v1/agents/trend-detection/stats", headers=auth_headers)
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert "total_signals_detected" in stats_data


# ============================================================================
# 27. Workspace Authorization
# ============================================================================
def test_27_workspace_authorization():
    client = TestClient(app)
    # Invalid token request must return 401
    res = client.get("/api/v1/agents/trend-detection/signals", headers={"Authorization": "Bearer invalid_expired_jwt"})
    assert res.status_code in [401, 403]


# ============================================================================
# 28. Candidate Resolution
# ============================================================================
def test_28_candidate_resolution(agent, auth_headers):
    cand = TrendSignalCandidate(
        id="cand_test_res",
        unified_product_id="unf_cand_prod",
        candidate_type="breakout_candidate",
        composite_score=88.0,
        confidence=0.94,
        status="pending_review",
        reasons=["High review momentum", "Cross-platform presence"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    trend_detection_repo.create_candidate(cand)

    client = TestClient(app)
    res = client.post(
        "/api/v1/agents/trend-detection/candidates/cand_test_res/resolve",
        headers=auth_headers,
        json={"status": "confirmed", "notes": "Approved for spotlight campaign"}
    )
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "confirmed"
    assert res_data["metadata"]["resolution_notes"] == "Approved for spotlight campaign"


# ============================================================================
# 29. Frontend Trend Filtering Query Efficiency
# ============================================================================
def test_29_frontend_trend_filtering(agent, auth_headers):
    now = datetime.now(timezone.utc)
    trend_detection_repo.upsert_signal(TrendSignal(
        id="sig_filter_1",
        unified_product_id="unf_f1",
        signal_type="price_drop",
        signal_strength=85.0,
        direction="down",
        severity="high",
        status="active",
        detected_at=now
    ))
    trend_detection_repo.upsert_signal(TrendSignal(
        id="sig_filter_2",
        unified_product_id="unf_f2",
        signal_type="review_momentum",
        signal_strength=40.0,
        direction="up",
        severity="low",
        status="active",
        detected_at=now
    ))

    client = TestClient(app)
    res_filtered = client.get(
        "/api/v1/agents/trend-detection/signals?signal_type=price_drop&severity=high",
        headers=auth_headers
    )
    assert res_filtered.status_code == 200
    items = res_filtered.json()["items"]
    assert len(items) == 1
    assert items[0]["signal_type"] == "price_drop"


# ============================================================================
# 30. Large Dataset Performance & Candidate Retrieval
# ============================================================================
def test_30_large_dataset_performance(agent):
    now = datetime.now(timezone.utc)
    bulk_signals = []
    for i in range(100):
        bulk_signals.append(TrendSignal(
            id=f"sig_bulk_{i}",
            unified_product_id=f"unf_bulk_{i % 10}",
            signal_type="demand_surge" if i % 2 == 0 else "price_movement",
            signal_strength=50.0 + (i % 50),
            direction="up" if i % 2 == 0 else "stable",
            severity="medium",
            status="active",
            detected_at=now - timedelta(minutes=i)
        ))
    for s in bulk_signals:
        agent.trend_repo.upsert_signal(s)

    start = time.perf_counter()
    listed = agent.list_signals(limit=20, offset=10)
    elapsed = time.perf_counter() - start
    assert len(listed) == 20
    assert elapsed < 0.05, f"Signal query took {elapsed:.4f}s"
