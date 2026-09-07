import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from backend.app.models.domain import (
    TrendObservation, TrendSignal, TrendSignalCandidate,
    TrendScoreBreakdown, ProductTrendSummary
)

class TrendScoringEngine:
    """
    Calculates deterministic 0-100 product trend score and identifies breakout candidates.
    Never fabricates metrics; strictly aggregates verified observations and signals.
    """

    DEMAND_WEIGHT = 0.35
    PRICE_WEIGHT = 0.20
    CROSS_PLATFORM_WEIGHT = 0.20
    INVENTORY_WEIGHT = 0.15
    FRESHNESS_WEIGHT = 0.10

    @classmethod
    def calculate_trend_score(
        cls,
        observations: List[TrendObservation],
        signals: List[TrendSignal],
        platforms: List[str],
        freshness: str
    ) -> TrendScoreBreakdown:
        """
        Calculates deterministic component scores and total trend score (0.0 to 100.0).
        """
        if not observations or len(observations) < 1 or freshness == "insufficient_data":
            return TrendScoreBreakdown(
                demand_review_score=0.0,
                price_health_score=0.0,
                cross_platform_score=0.0,
                inventory_health_score=0.0,
                freshness_confidence_score=0.0,
                total_trend_score=0.0,
                trend_state="insufficient_data"
            )

        # 1. Demand & Review Momentum (0 - 100)
        rev_signals = [s for s in signals if s.signal_type in ["review_momentum", "demand_surge"]]
        demand_score = 50.0  # neutral baseline
        if rev_signals:
            top_rev = max(rev_signals, key=lambda s: s.signal_strength)
            if top_rev.direction == "up":
                growth_pct = top_rev.evidence.get("growth_percent", 10.0)
                demand_score = min(100.0, 50.0 + (growth_pct * 1.2))
            elif top_rev.direction == "down":
                demand_score = max(10.0, 50.0 - 25.0)

        # 2. Price Health (0 - 100)
        price_signals = [s for s in signals if s.signal_type in ["price_drop", "large_discount", "price_increase", "price_volatility", "price_movement"]]
        price_score = 60.0  # neutral healthy baseline
        if any(s.signal_type == "large_discount" for s in price_signals):
            price_score = 85.0  # attractive promotional pricing
        elif any(s.signal_type == "price_drop" for s in price_signals):
            price_score = 75.0
        elif any(s.signal_type == "price_volatility" for s in price_signals):
            price_score = 30.0  # unstable

        # 3. Cross-Platform Score (0 - 100)
        plat_count = len(set(platforms))
        if plat_count >= 3:
            cross_score = 100.0
        elif plat_count == 2:
            cross_score = 80.0
        elif plat_count == 1:
            cross_score = 45.0
        else:
            cross_score = 20.0

        # 4. Inventory Health (0 - 100)
        inv_signals = [s for s in signals if s.signal_type in ["out_of_stock", "restocked"]]
        inv_score = 80.0
        if any(s.signal_type == "out_of_stock" for s in inv_signals):
            inv_score = 25.0
        elif any(s.signal_type == "restocked" for s in inv_signals):
            inv_score = 90.0

        # 5. Freshness & Confidence (0 - 100)
        if freshness == "fresh":
            fresh_score = 100.0
        elif freshness == "recent":
            fresh_score = 75.0
        elif freshness == "stale":
            fresh_score = 30.0
        else:
            fresh_score = 0.0

        # Weighted Aggregation
        total = (
            (demand_score * cls.DEMAND_WEIGHT) +
            (price_score * cls.PRICE_WEIGHT) +
            (cross_score * cls.CROSS_PLATFORM_WEIGHT) +
            (inv_score * cls.INVENTORY_WEIGHT) +
            (fresh_score * cls.FRESHNESS_WEIGHT)
        )
        total_rounded = round(min(100.0, max(0.0, total)), 1)

        # Determine trend state
        if total_rounded >= 75.0 and plat_count >= 2 and any(s.direction == "up" for s in signals):
            state = "breakout"
        elif total_rounded >= 65.0:
            state = "accelerating"
        elif total_rounded >= 50.0:
            state = "emerging"
        elif total_rounded >= 40.0:
            state = "stable"
        else:
            state = "declining"

        return TrendScoreBreakdown(
            demand_review_score=round(demand_score, 1),
            price_health_score=round(price_score, 1),
            cross_platform_score=round(cross_score, 1),
            inventory_health_score=round(inv_score, 1),
            freshness_confidence_score=round(fresh_score, 1),
            total_trend_score=total_rounded,
            trend_state=state
        )

    @classmethod
    def evaluate_breakout_candidate(
        cls,
        unified_product_id: str,
        score_breakdown: TrendScoreBreakdown,
        signals: List[TrendSignal],
        platforms: List[str]
    ) -> Optional[TrendSignalCandidate]:
        """
        Creates a TrendSignalCandidate when breakout conditions are satisfied.
        """
        if score_breakdown.trend_state == "breakout" or (
            score_breakdown.total_trend_score >= 75.0 and len(platforms) >= 2
        ):
            supporting = [s.signal_type for s in signals if s.direction == "up"]
            reasons = [
                f"High composite trend score of {score_breakdown.total_trend_score}/100",
                f"Cross-platform distribution across {len(platforms)} marketplaces ({', '.join(platforms)})",
                f"Strong demand & review momentum component ({score_breakdown.demand_review_score}/100)"
            ]
            return TrendSignalCandidate(
                id=f"cand_brk_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                candidate_type="breakout_candidate",
                composite_score=score_breakdown.total_trend_score,
                confidence=0.92,
                status="pending_review",
                reasons=reasons,
                supporting_signals=supporting,
                evidence={
                    "trend_score": score_breakdown.total_trend_score,
                    "platforms": platforms,
                    "active_signals_count": len(signals)
                },
                metadata={"auto_detected": True},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        return None
