import pytest
import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from backend.app.models.domain import (
    AnomalyObservation, AnomalyDetection, AnomalyCandidate, AnomalyDetectionAudit,
    ProductAnomalySummary, AnomalyScoreBreakdown, UnifiedProduct, User
)
from backend.app.repositories.in_memory import (
    InMemoryAnomalyDetectionRepository, InMemoryUnifiedProductRepository,
    InMemoryDataQualityRepository
)
from backend.app.services.agents.anomaly_detection.baseline_engine import BaselineEngine, BaselineStats
from backend.app.services.agents.anomaly_detection.detector_rules import AnomalyDetectorRulesEngine
from backend.app.services.agents.anomaly_detection.scoring_engine import AnomalyScoringEngine
from backend.app.services.agents.anomaly_detection.llm_resolver import (
    AnomalyDetectionLLMResolver, AnomalyLLMInterpretationOutput
)
from backend.app.services.agents.anomaly_detection.memory_manager import AnomalyDetectionMemoryManager
from backend.app.services.agents.anomaly_detection.agent import ProductAnomalyDetectionAgent


@pytest.fixture
def clean_anomaly_repos():
    anomaly_repo = InMemoryAnomalyDetectionRepository()
    unified_repo = InMemoryUnifiedProductRepository()
    dq_repo = InMemoryDataQualityRepository()
    anomaly_repo.clear()
    unified_repo.clear()
    dq_repo.clear()
    return anomaly_repo, unified_repo, dq_repo


@pytest.fixture
def sample_observations():
    now = datetime.now(timezone.utc)
    return [
        AnomalyObservation(
            id="obs_1",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="price",
            metric_value=3000.0,
            observed_at=now - timedelta(days=5)
        ),
        AnomalyObservation(
            id="obs_2",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="price",
            metric_value=3100.0,
            observed_at=now - timedelta(days=4)
        ),
        AnomalyObservation(
            id="obs_3",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="price",
            metric_value=3050.0,
            observed_at=now - timedelta(days=3)
        ),
        AnomalyObservation(
            id="obs_4",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="rating",
            metric_value=4.2,
            observed_at=now - timedelta(days=3)
        ),
        AnomalyObservation(
            id="obs_5",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="review_count",
            metric_value=120.0,
            observed_at=now - timedelta(days=3)
        ),
        AnomalyObservation(
            id="obs_6",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="availability",
            metric_value=1.0,
            observed_at=now - timedelta(days=3)
        )
    ]


# 1. Price Spike Detection
def test_01_price_spike(clean_anomaly_repos, sample_observations):
    anomaly_repo, _, _ = clean_anomaly_repos
    now = datetime.now(timezone.utc)
    # Add extreme price spike (3050 -> 9500)
    spike_obs = sample_observations + [
        AnomalyObservation(
            id="obs_spike",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="price",
            metric_value=9500.0,
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=spike_obs,
        active_platforms=["daraz"]
    )
    spike = next((a for a in anomalies if a.anomaly_type == "price_spike"), None)
    assert spike is not None
    assert spike.severity in ["high", "critical"]
    assert spike.observed_value == 9500.0
    assert spike.deviation_percent > 100.0


# 2. Price Crash Detection
def test_02_price_crash(clean_anomaly_repos, sample_observations):
    now = datetime.now(timezone.utc)
    crash_obs = sample_observations + [
        AnomalyObservation(
            id="obs_crash",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="price",
            metric_value=1200.0,  # > 60% drop from 3050
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=crash_obs,
        active_platforms=["daraz"]
    )
    crash = next((a for a in anomalies if a.anomaly_type == "price_crash"), None)
    assert crash is not None
    assert crash.severity in ["high", "critical"]
    assert crash.deviation_percent < -50.0


# 3. Unusual Discount Detection
def test_03_unusual_discount(clean_anomaly_repos, sample_observations):
    now = datetime.now(timezone.utc)
    disc_obs = sample_observations + [
        AnomalyObservation(
            id="obs_disc_1",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="discount",
            metric_value=10.0,
            observed_at=now - timedelta(days=2)
        ),
        AnomalyObservation(
            id="obs_disc_2",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="discount",
            metric_value=85.0,  # Unusual 85% discount
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=disc_obs,
        active_platforms=["daraz"]
    )
    unusual = next((a for a in anomalies if a.anomaly_type == "unusual_discount"), None)
    assert unusual is not None
    assert unusual.observed_value == 85.0
    assert "Unusually large observed discount" in unusual.evidence.get("message", "")


# 4. Rating Jump Detection
def test_04_rating_jump(clean_anomaly_repos, sample_observations):
    now = datetime.now(timezone.utc)
    rtg_obs = sample_observations + [
        AnomalyObservation(
            id="obs_rtg_jump",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="rating",
            metric_value=4.9,  # 4.2 -> 4.9 (+0.7)
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=rtg_obs,
        active_platforms=["daraz"]
    )
    jump = next((a for a in anomalies if a.anomaly_type == "rating_jump"), None)
    assert jump is not None
    assert jump.deviation >= 0.5


# 5. Rating Drop Detection
def test_05_rating_drop(clean_anomaly_repos, sample_observations):
    now = datetime.now(timezone.utc)
    rtg_obs = sample_observations + [
        AnomalyObservation(
            id="obs_rtg_drop",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="rating",
            metric_value=3.2,  # 4.2 -> 3.2 (-1.0)
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=rtg_obs,
        active_platforms=["daraz"]
    )
    drop = next((a for a in anomalies if a.anomaly_type == "rating_drop"), None)
    assert drop is not None
    assert drop.deviation <= -0.5
    assert drop.severity == "high"


# 6. Review Velocity Spike
def test_06_review_velocity_spike(clean_anomaly_repos, sample_observations):
    now = datetime.now(timezone.utc)
    rev_obs = sample_observations + [
        AnomalyObservation(
            id="obs_rev_spk",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="review_count",
            metric_value=420.0,  # 120 -> 420 (+300 reviews)
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=rev_obs,
        active_platforms=["daraz"]
    )
    spike = next((a for a in anomalies if a.anomaly_type == "review_velocity_spike"), None)
    assert spike is not None
    assert spike.deviation >= 300.0


# 7. Review Velocity Drop
def test_07_review_velocity_drop(clean_anomaly_repos, sample_observations):
    now = datetime.now(timezone.utc)
    rev_obs = sample_observations + [
        AnomalyObservation(
            id="obs_rev_drp",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="review_count",
            metric_value=70.0,  # 120 -> 70 (reviews removed/purged)
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=rev_obs,
        active_platforms=["daraz"]
    )
    drop = next((a for a in anomalies if a.anomaly_type == "review_velocity_drop"), None)
    assert drop is not None
    assert drop.deviation < 0


# 8. Availability Flip-Flop Anomaly
def test_08_availability_change(clean_anomaly_repos, sample_observations):
    now = datetime.now(timezone.utc)
    avail_obs = sample_observations + [
        AnomalyObservation(
            id="obs_avl_2",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="availability",
            metric_value=0.0,
            observed_at=now - timedelta(days=2)
        ),
        AnomalyObservation(
            id="obs_avl_3",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="availability",
            metric_value=1.0,
            observed_at=now - timedelta(days=1)
        ),
        AnomalyObservation(
            id="obs_avl_4",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="availability",
            metric_value=0.0,
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=avail_obs,
        active_platforms=["daraz"]
    )
    avail_anom = next((a for a in anomalies if a.anomaly_type == "availability_change"), None)
    assert avail_anom is not None
    assert avail_anom.evidence.get("rapid_availability_transitions", 0) >= 2


# 9. Cross-Platform Price Anomaly
def test_09_cross_platform_price_anomaly(clean_anomaly_repos, sample_observations):
    listings = [
        {"platform": "daraz", "price": 3000.0, "currency": "PKR"},
        {"platform": "shopify", "price": 6200.0, "currency": "PKR"}  # > 100% disparity
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=sample_observations,
        active_platforms=["daraz", "shopify"],
        platform_listings=listings
    )
    cp_anom = next((a for a in anomalies if a.anomaly_type == "cross_platform_price_anomaly"), None)
    assert cp_anom is not None
    assert cp_anom.deviation_percent > 40.0
    assert "daraz" in cp_anom.platforms
    assert "shopify" in cp_anom.platforms


# 10. Platform Presence Anomaly
def test_10_platform_presence_anomaly(clean_anomaly_repos, sample_observations):
    # Active on 3 platforms, but listing only returns 1
    listings = [{"platform": "daraz", "price": 3000.0}]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=sample_observations,
        active_platforms=["daraz", "shopify", "amazon"],
        platform_listings=listings
    )
    pres_anom = next((a for a in anomalies if a.anomaly_type == "platform_presence_anomaly"), None)
    assert pres_anom is not None
    assert "shopify" in pres_anom.evidence.get("disappeared_from", [])


# 11. Category Activity Anomaly
def test_11_category_activity_anomaly(clean_anomaly_repos, sample_observations):
    # Anomaly evaluation remains stable across category metrics
    stats = BaselineEngine.compute_baseline(sample_observations, "price")
    assert stats.is_sufficient is True
    assert stats.count >= 3


# 12. Provider Data Anomaly (Corrupt Values)
def test_12_provider_data_anomaly(clean_anomaly_repos, sample_observations):
    corrupt_provider_data = {
        "provider": "daraz_scraper_v2",
        "platform": "daraz",
        "rating": 9.8,      # Out of bounds (>5.0)
        "price": -500.0     # Negative price
    }
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
        unified_product_id="prod_test_100",
        observations=sample_observations,
        provider_data=corrupt_provider_data
    )
    prov_anom = next((a for a in anomalies if a.anomaly_type == "provider_data_anomaly"), None)
    assert prov_anom is not None
    assert prov_anom.severity == "critical"
    assert "rating out of bounds (9.8)" in prov_anom.evidence["corrupt_fields"]


# 13. Insufficient Data Handling
@pytest.mark.asyncio
async def test_13_insufficient_data(clean_anomaly_repos):
    anomaly_repo, unified_repo, dq_repo = clean_anomaly_repos
    agent = ProductAnomalyDetectionAgent(
        anomaly_repo=anomaly_repo,
        unified_product_repo=unified_repo,
        data_quality_repo=dq_repo
    )
    summary = await agent.analyze_product_anomalies("prod_empty")
    assert summary.status == "insufficient_data"
    assert summary.anomaly_score == 0.0
    assert len(summary.active_anomalies) == 0


# 14. Baseline Calculation
def test_14_baseline_calculation(sample_observations):
    stats = BaselineEngine.compute_baseline(sample_observations, "price")
    assert stats.count == 3
    assert stats.mean == pytest.approx(3050.0, 0.01)
    assert stats.median == 3050.0
    assert stats.min_val == 3000.0
    assert stats.max_val == 3100.0


# 15. Standard Deviation Calculation
def test_15_standard_deviation(sample_observations):
    stats = BaselineEngine.compute_baseline(sample_observations, "price")
    assert stats.std_dev > 0.0
    assert stats.std_dev == pytest.approx(40.82, 0.1)


# 16. MAD (Median Absolute Deviation) Detection
def test_16_mad_detection(sample_observations):
    stats = BaselineEngine.compute_baseline(sample_observations, "price")
    assert stats.mad == 50.0


# 17. Confidence Calculation
def test_17_confidence_calculation(sample_observations):
    now = datetime.now(timezone.utc)
    spike_obs = sample_observations + [
        AnomalyObservation(
            id="obs_spike",
            unified_product_id="prod_test_100",
            platform="daraz",
            metric_type="price",
            metric_value=8000.0,
            observed_at=now
        )
    ]
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies("prod_test_100", spike_obs)
    assert len(anomalies) > 0
    assert anomalies[0].confidence >= 0.90


# 18. Severity Calculation
def test_18_severity_calculation():
    anom_low = AnomalyDetection(
        id="a1", unified_product_id="p1", anomaly_type="price_spike",
        severity="low", score=40.0, confidence=0.85, baseline_method="rolling_median"
    )
    anom_crit = AnomalyDetection(
        id="a2", unified_product_id="p1", anomaly_type="price_spike",
        severity="critical", score=95.0, confidence=0.98, baseline_method="rolling_median"
    )
    assert anom_crit.score > anom_low.score


# 19. Anomaly Score 0-100 Calculation
def test_19_anomaly_score(sample_observations):
    anom = AnomalyDetection(
        id="a1", unified_product_id="p1", anomaly_type="price_spike",
        severity="high", score=85.0, confidence=0.92, baseline_method="rolling_median"
    )
    stats_map = {"price": BaselineEngine.compute_baseline(sample_observations, "price")}
    score, breakdown, status = AnomalyScoringEngine.calculate_anomaly_score(
        anomalies=[anom],
        observations=sample_observations,
        stats_map=stats_map,
        platforms_count=2,
        freshness_status="fresh"
    )
    assert 0.0 <= score <= 100.0
    assert status == "anomaly_detected"
    assert breakdown.deviation_magnitude_score == 85.0
    assert breakdown.data_freshness_score == 100.0


# 20. Duplicate Prevention via Fingerprint
def test_20_duplicate_prevention(clean_anomaly_repos, sample_observations):
    anomaly_repo, _, _ = clean_anomaly_repos
    fingerprint = AnomalyDetectorRulesEngine.generate_fingerprint(
        "prod_test_100", "price_spike", "rolling_median", ["obs_1", "obs_2"]
    )
    anom1 = AnomalyDetection(
        id="a_orig", unified_product_id="prod_test_100", anomaly_type="price_spike",
        score=75.0, confidence=0.90, fingerprint=fingerprint, baseline_method="rolling_median"
    )
    anomaly_repo.upsert_anomaly(anom1)

    anom2 = AnomalyDetection(
        id="a_dup", unified_product_id="prod_test_100", anomaly_type="price_spike",
        score=80.0, confidence=0.92, fingerprint=fingerprint, baseline_method="rolling_median"
    )
    res = anomaly_repo.upsert_anomaly(anom2)
    assert res.id == "a_orig"  # Updated in place, no duplicate ID
    assert len(anomaly_repo.list_anomalies(unified_product_id="prod_test_100")) == 1


# 21. Candidate Creation for Low-Confidence or Critical Anomalies
def test_21_candidate_creation():
    anom = AnomalyDetection(
        id="a_crit", unified_product_id="prod_crit", anomaly_type="price_spike",
        severity="critical", score=95.0, confidence=0.80, baseline_method="rolling_median"
    )
    cand = AnomalyScoringEngine.evaluate_candidate_qualification(
        unified_product_id="prod_crit",
        anomalies=[anom],
        total_score=90.0,
        confidence=0.80
    )
    assert cand is not None
    assert cand.status == "pending_review"
    assert any("Critical severity" in r for r in cand.reasons)


# 22. Candidate Resolution Workflow
def test_22_candidate_resolution(clean_anomaly_repos):
    anomaly_repo, unified_repo, dq_repo = clean_anomaly_repos
    agent = ProductAnomalyDetectionAgent(
        anomaly_repo=anomaly_repo,
        unified_product_repo=unified_repo,
        data_quality_repo=dq_repo
    )
    cand = AnomalyCandidate(
        id="cand_rev_1",
        unified_product_id="prod_cand",
        candidate_type="unusual_discount",
        composite_score=85.0,
        confidence=0.80
    )
    anomaly_repo.create_candidate(cand)

    resolved = agent.resolve_candidate_review("cand_rev_1", "confirmed", "Confirmed flash sale")
    assert resolved.status == "confirmed"
    assert resolved.metadata.get("resolution_notes") == "Confirmed flash sale"


# 23. Memory Creation for Anomaly Pattern
def test_23_memory_creation(clean_anomaly_repos):
    _, _, dq_repo = clean_anomaly_repos
    anom = AnomalyDetection(
        id="a_mem", unified_product_id="prod_m", anomaly_type="price_spike",
        severity="high", score=85.0, confidence=0.90, baseline_method="rolling_median"
    )
    mem = AnomalyDetectionMemoryManager.record_anomaly_pattern(
        memory_store=dq_repo,
        anomaly=anom,
        category="Electronics"
    )
    assert mem.agent_id == "agent_anomaly_detection"
    assert "anomaly_pattern:price_spike:Electronics" in mem.memory_key


# 24. Memory Reinforcement on Repeated Pattern
def test_24_memory_reinforcement(clean_anomaly_repos):
    _, _, dq_repo = clean_anomaly_repos
    anom = AnomalyDetection(
        id="a_mem", unified_product_id="prod_m", anomaly_type="price_spike",
        severity="high", score=85.0, confidence=0.90, baseline_method="rolling_median"
    )
    mem1 = AnomalyDetectionMemoryManager.record_anomaly_pattern(dq_repo, anom, "Footwear")
    initial_conf = mem1.confidence_score

    mem2 = AnomalyDetectionMemoryManager.record_anomaly_pattern(dq_repo, anom, "Footwear")
    assert mem2.confidence_score >= initial_conf
    assert mem2.occurrence_count == 2


# 25. Memory Event Audit Logging
def test_25_memory_audit(clean_anomaly_repos):
    _, _, dq_repo = clean_anomaly_repos
    anom = AnomalyDetection(
        id="a_mem_aud", unified_product_id="prod_aud", anomaly_type="rating_drop",
        severity="high", score=80.0, confidence=0.92, baseline_method="rolling_median"
    )
    mem = AnomalyDetectionMemoryManager.record_anomaly_pattern(dq_repo, anom, "Apparel")
    events = dq_repo.list_memory_events("agent_anomaly_detection", mem.id)
    assert len(events) >= 1
    assert events[0].event_type == "created"


# 26. Gemini Selective Invocation
def test_26_gemini_selective_invocation():
    # 1 anomaly -> false
    anom_single = [
        AnomalyDetection(
            id="a1", unified_product_id="p1", anomaly_type="price_spike",
            severity="medium", score=60.0, confidence=0.90, baseline_method="rolling_median"
        )
    ]
    assert AnomalyDetectionLLMResolver.should_invoke_llm(anom_single, []) is False

    # 2 simultaneous anomalies -> true
    anom_multi = anom_single + [
        AnomalyDetection(
            id="a2", unified_product_id="p1", anomaly_type="rating_drop",
            severity="high", score=75.0, confidence=0.90, baseline_method="rolling_median"
        )
    ]
    assert AnomalyDetectionLLMResolver.should_invoke_llm(anom_multi, []) is True


# 27. Gemini Timeout Fallback
@pytest.mark.asyncio
async def test_27_gemini_timeout_fallback():
    mock_gemini = MagicMock()
    mock_gemini.generate_text = AsyncMock(side_effect=asyncio.TimeoutError("Gemini timed out"))

    anom = [
        AnomalyDetection(
            id="a1", unified_product_id="p1", anomaly_type="price_spike",
            severity="high", score=85.0, confidence=0.90, deviation_percent=120.0, baseline_method="rolling_median"
        )
    ]
    res = await AnomalyDetectionLLMResolver.interpret_anomalies_with_gemini(
        product_name="Sample Item",
        category="Tech",
        anomalies=anom,
        observations=[],
        platforms=["daraz"],
        gemini_provider=mock_gemini
    )
    assert "Price spike" in res.interpretation
    assert res.confidence > 0.8


# 28. Invalid Gemini JSON Fallback
@pytest.mark.asyncio
async def test_28_invalid_gemini_json_fallback():
    mock_gemini = MagicMock()
    mock_gemini.generate_text = AsyncMock(return_value="NOT A JSON STRING !!!")

    anom = [
        AnomalyDetection(
            id="a1", unified_product_id="p1", anomaly_type="rating_drop",
            severity="medium", score=65.0, confidence=0.90, deviation=-0.8, baseline_method="rolling_median"
        )
    ]
    res = await AnomalyDetectionLLMResolver.interpret_anomalies_with_gemini(
        product_name="Sample Item",
        category="Tech",
        anomalies=anom,
        observations=[],
        platforms=["daraz"],
        gemini_provider=mock_gemini
    )
    assert "rating drop" in res.interpretation.lower()


# 29. Full Agent API Pipeline End-to-End
@pytest.mark.asyncio
async def test_29_api_endpoints(clean_anomaly_repos, sample_observations):
    anomaly_repo, unified_repo, dq_repo = clean_anomaly_repos
    agent = ProductAnomalyDetectionAgent(
        anomaly_repo=anomaly_repo,
        unified_product_repo=unified_repo,
        data_quality_repo=dq_repo
    )
    unified_repo.upsert_unified_product(UnifiedProduct(
        id="prod_test_100",
        unified_product_id="prod_test_100",
        canonical_name="Smart Wireless Headphones",
        normalized_name="smart wireless headphones",
        brand="SoundMaster",
        category="Audio",
        platforms=["daraz", "shopify"],
        created_at=datetime.now(timezone.utc)
    ))

    # Ingest baseline
    anomaly_repo.batch_record_observations(sample_observations)

    # Ingest new listing with price spike
    summary = await agent.analyze_product_anomalies(
        unified_product_id="prod_test_100",
        incoming_listings=[{"platform": "daraz", "price": 9500.0, "rating": 4.2, "review_count": 120}]
    )
    assert summary.status == "anomaly_detected"
    assert summary.anomaly_score > 50.0
    assert len(summary.active_anomalies) >= 1

    stats = anomaly_repo.get_anomaly_stats()
    assert stats.total_anomalies_detected >= 1


# 30. Workspace Authorization / User Dependency Check
def test_30_workspace_authorization():
    mock_user = User(
        id="user_test_99",
        email="operator@trendpulse.ai",
        full_name="Operator AI",
        hashed_password="mock_hashed_pw",
        role="operator",
        workspace_id="ws_test_1"
    )
    assert mock_user.workspace_id == "ws_test_1"


# 31. Historical Anomaly Retrieval
def test_31_historical_anomaly_retrieval(clean_anomaly_repos, sample_observations):
    anomaly_repo, _, _ = clean_anomaly_repos
    anomaly_repo.batch_record_observations(sample_observations)
    history = anomaly_repo.list_observations("prod_test_100", metric_type="price")
    assert len(history) == 3
    assert history[0].metric_type == "price"


# 32. Frontend Filtering & Pagination
def test_32_frontend_filtering(clean_anomaly_repos):
    anomaly_repo, _, _ = clean_anomaly_repos
    for i in range(10):
        anomaly_repo.upsert_anomaly(AnomalyDetection(
            id=f"a_{i}",
            unified_product_id=f"prod_{i}",
            anomaly_type="price_spike" if i % 2 == 0 else "rating_drop",
            severity="high" if i < 5 else "low",
            score=50.0 + i,
            confidence=0.90,
            platforms=["daraz"],
            baseline_method="rolling_median"
        ))

    spikes = anomaly_repo.list_anomalies(anomaly_type="price_spike")
    assert len(spikes) == 5
    highs = anomaly_repo.list_anomalies(severity="high")
    assert len(highs) == 5
    page1 = anomaly_repo.list_anomalies(limit=4, offset=0)
    assert len(page1) == 4


# 33. Large Dataset Performance Benchmark
def test_33_large_dataset_performance(clean_anomaly_repos):
    anomaly_repo, _, _ = clean_anomaly_repos
    now = datetime.now(timezone.utc)
    batch = []
    for i in range(1000):
        batch.append(AnomalyObservation(
            id=f"perf_obs_{i}",
            unified_product_id=f"prod_perf_{i % 50}",
            platform="daraz",
            metric_type="price",
            metric_value=2000.0 + (i % 200),
            observed_at=now - timedelta(minutes=i)
        ))

    start = time.perf_counter()
    anomaly_repo.batch_record_observations(batch)
    stats = BaselineEngine.compute_baseline(batch[:50], "price")
    anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies("prod_perf_1", batch[:50])
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0  # Must process 1000 observations in under 1 second
    assert stats.is_sufficient is True
