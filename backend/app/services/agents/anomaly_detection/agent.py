import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.models.domain import (
    AnomalyObservation, AnomalyDetection, AnomalyCandidate, AnomalyDetectionAudit,
    ProductAnomalySummary, AnomalyScoreBreakdown, UnifiedProduct
)
from backend.app.repositories.base import (
    AnomalyDetectionRepository, UnifiedProductRepository, DataQualityRepository
)
from backend.app.services.agents.anomaly_detection.baseline_engine import BaselineEngine, BaselineStats
from backend.app.services.agents.anomaly_detection.detector_rules import AnomalyDetectorRulesEngine
from backend.app.services.agents.anomaly_detection.scoring_engine import AnomalyScoringEngine
from backend.app.services.agents.anomaly_detection.llm_resolver import AnomalyDetectionLLMResolver
from backend.app.services.agents.anomaly_detection.memory_manager import AnomalyDetectionMemoryManager

logger = logging.getLogger(__name__)

class ProductAnomalyDetectionAgent:
    """
    Master Orchestrator for AI Agent 05: Anomaly Detection Agent.
    Analyzes historical and real-time marketplace metrics to detect statistical outliers,
    extreme price shifts, rating jumps/drops, review velocity spikes, availability transitions,
    and provider data corruption with strict anti-fabrication guards.
    """

    AGENT_ID = "agent_anomaly_detection"

    def __init__(
        self,
        anomaly_repo: AnomalyDetectionRepository,
        unified_product_repo: Optional[UnifiedProductRepository] = None,
        data_quality_repo: Optional[DataQualityRepository] = None,
        gemini_provider: Optional[Any] = None
    ):
        self.anomaly_repo = anomaly_repo
        self.unified_product_repo = unified_product_repo
        self.data_quality_repo = data_quality_repo
        self.gemini_provider = gemini_provider

    async def analyze_product_anomalies(
        self,
        unified_product_id: str,
        incoming_listings: Optional[List[Dict[str, Any]]] = None,
        provider_data: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None
    ) -> ProductAnomalySummary:
        """
        Executes full anomaly detection analysis for a product across its historical observations
        and newly provided platform listings.
        """
        run_id = run_id or f"anom_run_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)

        # 1. Fetch unified product metadata if available
        product_name = "Unknown Product"
        brand = None
        category = "Unknown"
        platforms: List[str] = []

        if self.unified_product_repo:
            unified_prod = None
            if hasattr(self.unified_product_repo, "get_unified_product"):
                unified_prod = self.unified_product_repo.get_unified_product(unified_product_id)
            elif hasattr(self.unified_product_repo, "get_by_id"):
                unified_prod = self.unified_product_repo.get_by_id(unified_product_id)
            if unified_prod:
                product_name = unified_prod.canonical_name
                brand = unified_prod.brand
                category = unified_prod.category
                platforms = list(unified_prod.platforms) if hasattr(unified_prod, "platforms") else []

        # 2. Fetch existing historical observations
        existing_obs = self.anomaly_repo.list_observations(unified_product_id, limit=200)

        # 3. Ingest incoming listings into new observations
        new_obs: List[AnomalyObservation] = []
        if incoming_listings:
            for lst in incoming_listings:
                plat = str(lst.get("platform", "unknown")).lower()
                if plat not in [p.lower() for p in platforms]:
                    platforms.append(plat)
                obs_list = BaselineEngine.build_observations_from_listing(
                    unified_product_id=unified_product_id,
                    listing=lst,
                    prior_observations=existing_obs
                )
                new_obs.extend(obs_list)

            if new_obs:
                self.anomaly_repo.batch_record_observations(new_obs)
                existing_obs = new_obs + existing_obs

        # Freshness Check
        freshness_status = BaselineEngine.calculate_freshness(existing_obs)

        # 4. Anti-Fabrication / Data Sufficiency Gate
        if len(existing_obs) < 2 or freshness_status == "insufficient_data":
            # Record audit
            audit = AnomalyDetectionAudit(
                id=f"aaud_{uuid.uuid4().hex[:12]}",
                agent_id=self.AGENT_ID,
                run_id=run_id,
                product_id=unified_product_id,
                detection_method="statistical_baseline",
                rule_name="insufficient_data_gate",
                confidence=1.0,
                evidence={"observations_count": len(existing_obs), "freshness": freshness_status},
                decision="insufficient_data",
                llm_used=False,
                created_at=now
            )
            self.anomaly_repo.record_audit(audit)

            return ProductAnomalySummary(
                unified_product_id=unified_product_id,
                canonical_name=product_name,
                brand=brand,
                category=category,
                platforms=platforms,
                anomaly_score=0.0,
                status="insufficient_data",
                confidence=0.0,
                freshness_status=freshness_status,
                active_anomalies=[],
                score_breakdown=AnomalyScoreBreakdown(
                    deviation_magnitude_score=0.0,
                    historical_consistency_score=0.0,
                    data_freshness_score=0.0,
                    baseline_quality_score=0.0,
                    cross_platform_score=0.0,
                    total_anomaly_score=0.0,
                    status="insufficient_data"
                ),
                recent_observations=existing_obs[:20],
                last_analyzed_at=now
            )

        # 5. Deterministic Anomaly Evaluation
        detected_anomalies = AnomalyDetectorRulesEngine.evaluate_all_anomalies(
            unified_product_id=unified_product_id,
            observations=existing_obs,
            active_platforms=platforms,
            platform_listings=incoming_listings,
            provider_data=provider_data
        )

        # Persist / Upsert detected anomalies
        persisted_anomalies: List[AnomalyDetection] = []
        for anom in detected_anomalies:
            upserted = self.anomaly_repo.upsert_anomaly(anom)
            persisted_anomalies.append(upserted)

            # Record in agent persistent memory
            if self.data_quality_repo:
                AnomalyDetectionMemoryManager.record_anomaly_pattern(
                    memory_store=self.data_quality_repo,
                    anomaly=upserted,
                    category=category
                )

        # 6. Baseline Statistics Map
        stats_map = {
            "price": BaselineEngine.compute_baseline(existing_obs, "price"),
            "rating": BaselineEngine.compute_baseline(existing_obs, "rating"),
            "review_count": BaselineEngine.compute_baseline(existing_obs, "review_count"),
            "availability": BaselineEngine.compute_baseline(existing_obs, "availability"),
            "discount": BaselineEngine.compute_baseline(existing_obs, "discount")
        }

        # 7. Compute Anomaly Score & Breakdown
        total_score, breakdown, anomaly_status = AnomalyScoringEngine.calculate_anomaly_score(
            anomalies=persisted_anomalies,
            observations=existing_obs,
            stats_map=stats_map,
            platforms_count=len(platforms),
            freshness_status=freshness_status
        )

        overall_confidence = max([a.confidence for a in persisted_anomalies]) if persisted_anomalies else 0.90

        # 8. Selective Gemini Reasoning
        llm_used = False
        if AnomalyDetectionLLMResolver.should_invoke_llm(persisted_anomalies, existing_obs):
            llm_interpretation = await AnomalyDetectionLLMResolver.interpret_anomalies_with_gemini(
                product_name=product_name,
                category=category,
                anomalies=persisted_anomalies,
                observations=existing_obs,
                platforms=platforms,
                gemini_provider=self.gemini_provider
            )
            llm_used = True
            # Augment evidence of primary anomaly with LLM explanation
            if persisted_anomalies:
                primary = persisted_anomalies[0]
                primary.evidence["gemini_interpretation"] = llm_interpretation.interpretation
                primary.evidence["gemini_explanations"] = llm_interpretation.possible_explanations
                self.anomaly_repo.upsert_anomaly(primary)

        # 9. Candidate Qualification for Human Review
        candidate = AnomalyScoringEngine.evaluate_candidate_qualification(
            unified_product_id=unified_product_id,
            anomalies=persisted_anomalies,
            total_score=total_score,
            confidence=overall_confidence
        )
        if candidate:
            self.anomaly_repo.create_candidate(candidate)

        # 10. Record Audit Trail
        audit = AnomalyDetectionAudit(
            id=f"aaud_{uuid.uuid4().hex[:12]}",
            agent_id=self.AGENT_ID,
            run_id=run_id,
            product_id=unified_product_id,
            detection_method="statistical_baseline_and_rules",
            rule_name="comprehensive_anomaly_evaluation",
            confidence=overall_confidence,
            evidence={
                "anomalies_count": len(persisted_anomalies),
                "total_score": total_score,
                "freshness": freshness_status
            },
            decision="anomaly_detected" if persisted_anomalies else "normal_variance",
            llm_used=llm_used,
            created_at=now
        )
        self.anomaly_repo.record_audit(audit)

        return ProductAnomalySummary(
            unified_product_id=unified_product_id,
            canonical_name=product_name,
            brand=brand,
            category=category,
            platforms=platforms,
            anomaly_score=total_score,
            status=anomaly_status,
            confidence=round(overall_confidence, 3),
            freshness_status=freshness_status,
            active_anomalies=persisted_anomalies,
            score_breakdown=breakdown,
            recent_observations=existing_obs[:20],
            last_analyzed_at=now
        )

    def resolve_candidate_review(
        self,
        candidate_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[AnomalyCandidate]:
        """
        Resolves an anomaly candidate in the human review queue.
        If marked as false positive, records a suppression rule in agent memory.
        """
        resolved = self.anomaly_repo.resolve_candidate(candidate_id, status, notes)
        if resolved and status == "false_positive" and self.data_quality_repo:
            AnomalyDetectionMemoryManager.record_false_positive_suppression(
                memory_store=self.data_quality_repo,
                anomaly_type=resolved.candidate_type,
                reason=notes or "Resolved as false positive by human reviewer"
            )
        return resolved
