import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from backend.app.models.domain import (
    TrendObservation, TrendSignal, TrendSignalCandidate, TrendDetectionAudit,
    ProductTrendSummary, TrendScoreBreakdown, AgentTrendDetectionStats,
    UnifiedProduct, ProductPlatformListing
)
from backend.app.repositories.base import (
    TrendDetectionRepository, UnifiedProductRepository, TaxonomyRepository
)
from backend.app.repositories.in_memory import (
    InMemoryTrendDetectionRepository, InMemoryUnifiedProductRepository, InMemoryTaxonomyRepository
)
from backend.app.services.agents.trend_detection.observations_tracker import ObservationsTracker
from backend.app.services.agents.trend_detection.signal_rules import TrendSignalRulesEngine
from backend.app.services.agents.trend_detection.scoring_engine import TrendScoringEngine
from backend.app.services.agents.trend_detection.llm_resolver import TrendDetectionLLMResolver
from backend.app.services.agents.trend_detection.memory_manager import TrendDetectionMemoryManager


class ProductTrendDetectionAgent:
    """
    AI Agent 04: Trend Detection & Signal Discovery Agent.
    Analyzes verified marketplace observations to detect grounded product signals,
    calculate deterministic 0-100 trend scores, and identify breakout candidates.
    """

    AGENT_ID = "agent_trend_detection"

    def __init__(
        self,
        trend_repo: Optional[TrendDetectionRepository] = None,
        unified_repo: Optional[UnifiedProductRepository] = None,
        taxonomy_repo: Optional[TaxonomyRepository] = None,
        gemini_client: Optional[Any] = None
    ):
        self.trend_repo = trend_repo or InMemoryTrendDetectionRepository()
        self.unified_repo = unified_repo or InMemoryUnifiedProductRepository()
        self.taxonomy_repo = taxonomy_repo or InMemoryTaxonomyRepository()
        self.llm_resolver = TrendDetectionLLMResolver(gemini_client=gemini_client)
        self.memory_manager = TrendDetectionMemoryManager(repository=self.taxonomy_repo)

    def analyze_product_trends(
        self,
        unified_product_id: str,
        new_listing: Optional[Dict[str, Any]] = None,
        allow_llm: bool = True,
        run_id: Optional[str] = None
    ) -> ProductTrendSummary:
        """
        Main entrypoint: analyzes historical metric observations and new listing inputs
        to discover product signals and compute deterministic trend scores.
        """
        now = datetime.now(timezone.utc)
        run_id = run_id or f"run_trd_{uuid.uuid4().hex[:12]}"

        # 1. Fetch Unified Product
        unf = self.unified_repo.get_unified_product(unified_product_id)
        product_name = unf.canonical_name if unf else "Unknown Product"
        brand_name = unf.brand if unf else None
        active_platforms = list(unf.platforms) if unf else []

        # 2. Fetch existing observations
        existing_obs = self.trend_repo.list_observations(unified_product_id, limit=200)

        # 3. If new listing provided, generate and record new observations
        if new_listing:
            plat = str(new_listing.get("platform", "unknown")).lower()
            if plat and plat not in active_platforms:
                active_platforms.append(plat)
            new_obs_items = ObservationsTracker.build_observations_from_listing(
                unified_product_id=unified_product_id,
                listing=new_listing,
                prior_observations=existing_obs
            )
            for obs in new_obs_items:
                self.trend_repo.record_observation(obs)
                existing_obs.insert(0, obs)

        # 4. If no observations exist, seed initial baseline from platform listings
        if not existing_obs and unf:
            listings = self.unified_repo.list_listings_for_product(unified_product_id)
            for lst in listings:
                baseline_obs = ObservationsTracker.build_observations_from_listing(
                    unified_product_id=unified_product_id,
                    listing={
                        "platform": lst.platform,
                        "price": lst.price,
                        "currency": lst.currency,
                        "rating": lst.rating,
                        "review_count": lst.review_count,
                        "available": lst.available
                    },
                    prior_observations=[]
                )
                for b_obs in baseline_obs:
                    self.trend_repo.record_observation(b_obs)
                    existing_obs.append(b_obs)

        # 5. Check data freshness and sufficiency
        freshness = ObservationsTracker.calculate_freshness(existing_obs)

        # If data is insufficient, return safe un-fabricated summary
        if not existing_obs or len(existing_obs) < 2 or freshness == "insufficient_data":
            score_breakdown = TrendScoreBreakdown(
                demand_review_score=0.0,
                price_health_score=0.0,
                cross_platform_score=0.0,
                inventory_health_score=0.0,
                freshness_confidence_score=0.0,
                total_trend_score=0.0,
                trend_state="insufficient_data"
            )
            self._record_audit_log(
                run_id=run_id,
                product_id=unified_product_id,
                method="insufficient_data_check",
                rule_name="min_observations_gate",
                confidence=0.0,
                evidence={"observation_count": len(existing_obs), "freshness": freshness},
                decision="insufficient_data"
            )
            return ProductTrendSummary(
                unified_product_id=unified_product_id,
                canonical_name=product_name,
                brand=brand_name,
                category="Unknown",
                platforms=active_platforms,
                trend_score=0.0,
                trend_state="insufficient_data",
                confidence=0.0,
                freshness_status=freshness,
                active_signals=[],
                score_breakdown=score_breakdown,
                recent_observations=existing_obs[:10],
                last_analyzed_at=now
            )

        # 6. Evaluate all deterministic signals
        signals = TrendSignalRulesEngine.evaluate_all_signals(
            unified_product_id=unified_product_id,
            observations=existing_obs,
            active_platforms=active_platforms
        )

        # Upsert detected signals (with deduplication via fingerprint)
        persisted_signals: List[TrendSignal] = []
        for sig in signals:
            saved_sig = self.trend_repo.upsert_signal(sig)
            persisted_signals.append(saved_sig)

        # 7. Compute deterministic trend score
        score_breakdown = TrendScoringEngine.calculate_trend_score(
            observations=existing_obs,
            signals=persisted_signals,
            platforms=active_platforms,
            freshness=freshness
        )

        # 8. Check for Breakout Candidate
        candidate = TrendScoringEngine.evaluate_breakout_candidate(
            unified_product_id=unified_product_id,
            score_breakdown=score_breakdown,
            signals=persisted_signals,
            platforms=active_platforms
        )
        if candidate:
            self.trend_repo.create_candidate(candidate)
            # Learn breakout pattern into persistent memory
            if self.memory_manager:
                self.memory_manager.record_breakout_pattern(
                    category="general",
                    platform=active_platforms[0] if active_platforms else "multi_platform",
                    signal_types=[s.signal_type for s in persisted_signals],
                    confidence=candidate.confidence,
                    run_id=run_id
                )

        # 9. Selective Gemini reasoning for complex multi-signal clusters
        llm_used = False
        llm_explanation = None
        has_contradictions = (
            any(s.direction == "up" for s in persisted_signals) and
            any(s.direction == "down" for s in persisted_signals)
        )
        if allow_llm and (has_contradictions or candidate is not None):
            sig_dicts = [
                {
                    "signal_type": s.signal_type,
                    "direction": s.direction,
                    "strength": s.signal_strength,
                    "severity": s.severity,
                    "evidence": s.evidence
                }
                for s in persisted_signals
            ]
            interpretation_out, success = self.llm_resolver.interpret_complex_trend(
                product_info={
                    "canonical_name": product_name,
                    "brand": brand_name,
                    "platforms": active_platforms
                },
                observed_signals=sig_dicts,
                freshness=freshness
            )
            if success:
                llm_used = True
                llm_explanation = interpretation_out.interpretation

        # 10. Record Audit Trail
        self._record_audit_log(
            run_id=run_id,
            product_id=unified_product_id,
            method="deterministic_scoring_and_signals",
            rule_name="trend_score_v1",
            confidence=0.92,
            evidence={
                "trend_score": score_breakdown.total_trend_score,
                "trend_state": score_breakdown.trend_state,
                "signals_count": len(persisted_signals),
                "platforms": active_platforms
            },
            decision=score_breakdown.trend_state,
            llm_used=llm_used
        )

        return ProductTrendSummary(
            unified_product_id=unified_product_id,
            canonical_name=product_name,
            brand=brand_name,
            category="Unknown",
            platforms=active_platforms,
            trend_score=score_breakdown.total_trend_score,
            trend_state=score_breakdown.trend_state,
            confidence=0.92 if freshness == "fresh" else 0.80,
            freshness_status=freshness,
            active_signals=persisted_signals,
            score_breakdown=score_breakdown,
            recent_observations=existing_obs[:20],
            last_analyzed_at=now
        )

    def _record_audit_log(
        self,
        run_id: str,
        product_id: str,
        method: str,
        rule_name: str,
        confidence: float,
        evidence: Dict[str, Any],
        decision: str,
        llm_used: bool = False
    ):
        audit = TrendDetectionAudit(
            id=f"tda_{uuid.uuid4().hex[:12]}",
            agent_id=self.AGENT_ID,
            run_id=run_id,
            product_id=product_id,
            detection_method=method,
            rule_name=rule_name,
            confidence=confidence,
            evidence=evidence,
            decision=decision,
            llm_used=llm_used,
            created_at=datetime.now(timezone.utc)
        )
        self.trend_repo.record_audit(audit)

    def get_product_trend_summary(self, unified_product_id: str) -> Optional[ProductTrendSummary]:
        return self.analyze_product_trends(unified_product_id, allow_llm=False)

    def list_signals(
        self,
        unified_product_id: Optional[str] = None,
        signal_type: Optional[str] = None,
        direction: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        min_strength: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TrendSignal]:
        return self.trend_repo.list_signals(
            unified_product_id=unified_product_id,
            signal_type=signal_type,
            direction=direction,
            severity=severity,
            status=status,
            min_strength=min_strength,
            limit=limit,
            offset=offset
        )

    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TrendSignalCandidate]:
        return self.trend_repo.list_candidates(
            status=status,
            candidate_type=candidate_type,
            limit=limit,
            offset=offset
        )

    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[TrendSignalCandidate]:
        return self.trend_repo.resolve_candidate(candidate_id, status=status, notes=notes)

    def get_stats(self) -> AgentTrendDetectionStats:
        return self.trend_repo.get_trend_stats()
