from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from backend.app.models.domain import (
    UnifiedProduct, MarketOpportunityScoreBreakdown
)


class MarketOpportunityScoringEngine:
    """
    Deterministic scoring and confidence engine for AI Agent 07 (Market Opportunity Intelligence Agent).

    Scoring Weights (0 to 100):
      1. Evidence Strength:         25%
      2. Trend Strength:            20%
      3. Market Coverage Gap:       15%
      4. Price Opportunity:         15%
      5. Product Quality:           10%
      6. Cross-Platform Evidence:   10%
      7. Freshness:                  5%
    """

    WEIGHT_EVIDENCE = 0.25
    WEIGHT_TREND = 0.20
    WEIGHT_COVERAGE_GAP = 0.15
    WEIGHT_PRICE_OPP = 0.15
    WEIGHT_QUALITY = 0.10
    WEIGHT_CROSS_PLAT = 0.10
    WEIGHT_FRESHNESS = 0.05

    QUALITY_GATE_THRESHOLD = 70.0

    @classmethod
    def calculate_score(
        cls,
        candidate_product: Optional[UnifiedProduct] = None,
        category: Optional[str] = None,
        data_quality_score: float = 85.0,
        trend_score: float = 50.0,
        coverage_gap_ratio: float = 0.5, # 0.0 to 1.0 (e.g. 1 out of 2 observed platforms missing = 0.5)
        price_spread_pct: float = 0.0,    # e.g. 15.0% price difference
        cross_platform_count: int = 1,
        active_anomalies: Optional[List[Dict[str, Any]]] = None,
        freshness_status: str = "fresh",
        opportunity_type: str = "product_gap"
    ) -> Tuple[MarketOpportunityScoreBreakdown, float, float]:
        """
        Calculates deterministic 0-100 score, confidence (0.0-1.0), and breakdown.
        """
        anomalies = active_anomalies or []
        has_critical_anomaly = any(
            a.get("severity") in ("critical", "high") and "price" in str(a.get("anomaly_type", "")).lower()
            for a in anomalies
        )

        # 1. Product Quality Gate Check
        if data_quality_score < cls.QUALITY_GATE_THRESHOLD:
            breakdown = MarketOpportunityScoreBreakdown(
                evidence_strength_score=round(data_quality_score * cls.WEIGHT_EVIDENCE, 2),
                trend_strength_score=0.0,
                market_coverage_gap_score=0.0,
                price_opportunity_score=0.0,
                product_quality_score=round(data_quality_score * cls.WEIGHT_QUALITY, 2),
                cross_platform_evidence_score=0.0,
                freshness_score=0.0,
                total_opportunity_score=round(data_quality_score * (cls.WEIGHT_EVIDENCE + cls.WEIGHT_QUALITY), 2),
                eligibility_status="quality_gated"
            )
            return breakdown, breakdown.total_opportunity_score, 0.40

        # 2. Critical Anomaly Block Check (e.g. for price_opportunity or product_launch_opportunity)
        if has_critical_anomaly and opportunity_type in ("price_opportunity", "product_launch_opportunity"):
            breakdown = MarketOpportunityScoreBreakdown(
                evidence_strength_score=15.0,
                trend_strength_score=round(trend_score * cls.WEIGHT_TREND, 2),
                market_coverage_gap_score=round(coverage_gap_ratio * 100.0 * cls.WEIGHT_COVERAGE_GAP, 2),
                price_opportunity_score=0.0, # blocked
                product_quality_score=round(data_quality_score * cls.WEIGHT_QUALITY, 2),
                cross_platform_evidence_score=5.0,
                freshness_score=4.0,
                total_opportunity_score=35.0,
                eligibility_status="anomaly_blocked"
            )
            return breakdown, 35.0, 0.45

        # 3. Evidence Strength Component (25%)
        # Based on completeness, review volume, and rating credibility
        evidence_raw = 50.0
        if candidate_product:
            if candidate_product.total_reviews >= 50:
                evidence_raw += 25.0
            elif candidate_product.total_reviews >= 10:
                evidence_raw += 15.0
            else:
                evidence_raw += 5.0

            if candidate_product.avg_rating >= 4.5:
                evidence_raw += 25.0
            elif candidate_product.avg_rating >= 4.0:
                evidence_raw += 15.0
            elif candidate_product.avg_rating >= 3.0:
                evidence_raw += 5.0
        else:
            evidence_raw = 70.0 # category-level aggregation
        evidence_score = round(min(100.0, evidence_raw) * cls.WEIGHT_EVIDENCE, 2)

        # 4. Trend Strength Component (20%)
        trend_raw = max(0.0, min(100.0, trend_score))
        trend_component = round(trend_raw * cls.WEIGHT_TREND, 2)

        # 5. Market Coverage Gap Component (15%)
        gap_raw = min(100.0, max(0.0, coverage_gap_ratio * 100.0))
        coverage_gap_component = round(gap_raw * cls.WEIGHT_COVERAGE_GAP, 2)

        # 6. Price Opportunity Component (15%)
        # Normalized based on verified price variance or competitive pricing
        price_opp_raw = 50.0
        if price_spread_pct > 0:
            if price_spread_pct >= 25.0:
                price_opp_raw = 95.0
            elif price_spread_pct >= 15.0:
                price_opp_raw = 80.0
            elif price_spread_pct >= 5.0:
                price_opp_raw = 65.0
        price_opp_component = round(price_opp_raw * cls.WEIGHT_PRICE_OPP, 2)

        # 7. Product Quality Component (10%)
        quality_component = round(data_quality_score * cls.WEIGHT_QUALITY, 2)

        # 8. Cross-Platform Evidence Component (10%)
        cross_plat_raw = 40.0
        if cross_platform_count >= 2:
            cross_plat_raw = 95.0
        elif cross_platform_count == 1:
            cross_plat_raw = 70.0
        cross_plat_component = round(cross_plat_raw * cls.WEIGHT_CROSS_PLAT, 2)

        # 9. Freshness Component (5%)
        if freshness_status == "fresh":
            fresh_raw = 100.0
        elif freshness_status == "recent":
            fresh_raw = 75.0
        elif freshness_status == "stale":
            fresh_raw = 40.0
        else:
            fresh_raw = 0.0
        freshness_component = round(fresh_raw * cls.WEIGHT_FRESHNESS, 2)

        total_score = round(
            evidence_score +
            trend_component +
            coverage_gap_component +
            price_opp_component +
            quality_component +
            cross_plat_component +
            freshness_component,
            2
        )

        # 10. Confidence Calculation
        # Grounded in data completeness, platform verification, and freshness
        base_confidence = 0.85
        if data_quality_score >= 90.0:
            base_confidence += 0.05
        elif data_quality_score < 75.0:
            base_confidence -= 0.10

        if cross_platform_count >= 2:
            base_confidence += 0.05

        if freshness_status == "fresh":
            base_confidence += 0.03
        elif freshness_status == "stale":
            base_confidence -= 0.15
        elif freshness_status == "insufficient_data":
            base_confidence = 0.30

        confidence = round(min(0.99, max(0.10, base_confidence)), 3)

        breakdown = MarketOpportunityScoreBreakdown(
            evidence_strength_score=evidence_score,
            trend_strength_score=trend_component,
            market_coverage_gap_score=coverage_gap_component,
            price_opportunity_score=price_opp_component,
            product_quality_score=quality_component,
            cross_platform_evidence_score=cross_plat_component,
            freshness_score=freshness_component,
            total_opportunity_score=total_score,
            eligibility_status="eligible"
        )

        return breakdown, total_score, confidence

    @classmethod
    def get_confidence_tier(cls, confidence: float) -> str:
        if confidence >= 0.90:
            return "High"
        elif confidence >= 0.75:
            return "Medium"
        elif confidence >= 0.50:
            return "Low"
        else:
            return "Needs Review"
