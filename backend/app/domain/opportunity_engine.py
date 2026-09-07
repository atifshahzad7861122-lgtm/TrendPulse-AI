"""
Deterministic Product Opportunity Evaluation Engine for Phase 3.

Evaluates commercial opportunity for a product based on observed demand, market gap,
cross-platform arbitrage potential, rating acclaim, and price health.
"""

from typing import List, Optional, Dict, Any
from backend.app.models.domain import ProductOpportunityEvaluation


class ProductOpportunityEngine:
    """
    Evaluates commercial opportunity without fabricated competition data.
    """

    OPPORTUNITY_VERSION = "3.0.0"

    @classmethod
    def evaluate_opportunity(
        cls,
        demand_score: float = 50.0,
        market_score: float = 50.0,
        rating: float = 0.0,
        review_count: int = 0,
        price: float = 0.0,
        platform_count: int = 1,
        growth_rate: Optional[float] = None,
        data_quality_score: float = 80.0,
        seller_count_in_category: Optional[int] = None,
        category_seller_count: Optional[int] = None,
        **kwargs: Any
    ) -> ProductOpportunityEvaluation:
        """
        Calculates opportunity score, level, confidence, and explainable signals.
        """
        effective_seller_count = category_seller_count if category_seller_count is not None else seller_count_in_category
        score = 0.0
        reasoning = []
        signals = []

        # 1. Demand Pull (0 - 35 pts)
        if demand_score >= 80.0:
            score += 35.0
            signals.append(f"Very high consumer search and order conviction (Demand: {demand_score:.1f})")
            reasoning.append("Strong organic consumer demand provides immediate sales velocity.")
        elif demand_score >= 60.0:
            score += 25.0
            signals.append(f"Solid consumer demand (Demand: {demand_score:.1f})")
        else:
            score += max((demand_score / 60.0) * 15.0, 5.0)

        # 2. Market Sentiment & Acclaim (0 - 25 pts)
        if rating >= 4.5 and review_count >= 50:
            score += 25.0
            signals.append(f"Exceptional customer reception ({rating:.1f}★ with {review_count:,} reviews)")
            reasoning.append("High consumer satisfaction signals strong product-market fit and lower return risk.")
        elif rating >= 4.0:
            score += 15.0
            signals.append(f"Positive buyer reception ({rating:.1f}★)")
        elif rating > 0:
            score += 5.0

        # 3. Market Expansion & Platform Gap (0 - 20 pts)
        # Products that sell strongly on 1 platform represent expansion opportunities onto other marketplaces
        if platform_count == 1:
            score += 20.0
            signals.append("Single-channel exclusivity: Significant expansion arbitrage potential")
            reasoning.append("Currently available on only one marketplace, leaving opportunity to capture demand on untapped platforms.")
        elif platform_count == 2:
            score += 12.0
            signals.append("Emerging cross-platform presence (2 marketplaces)")
        else:
            score += 5.0
            signals.append("Established multi-platform distribution")

        # 4. Growth Momentum (0 - 20 pts)
        if growth_rate is not None and growth_rate > 30.0:
            score += 20.0
            signals.append(f"Rapid growth momentum (+{growth_rate:.1f}%)")
            reasoning.append("Accelerating order and interest velocity indicates an expanding market segment.")
        elif growth_rate is not None and growth_rate > 0.0:
            score += 10.0
        else:
            score += 8.0  # Baseline

        # Clamping score
        opportunity_score = round(min(max(score, 5.0), 99.0), 1)

        # Level classification
        if opportunity_score >= 80.0:
            level = "Exceptional"
        elif opportunity_score >= 65.0:
            level = "High"
        elif opportunity_score >= 45.0:
            level = "Moderate"
        else:
            level = "Low"

        # Competition level - strictly based on real seller observations
        if effective_seller_count is not None:
            if effective_seller_count >= 50:
                comp_level = "High"
            elif effective_seller_count >= 15:
                comp_level = "Moderate"
            else:
                comp_level = "Low"
        else:
            comp_level = "unavailable"

        # Confidence based on data quality score and observation richness
        conf = (data_quality_score / 100.0) * 0.70
        if review_count >= 10:
            conf += 0.15
        if comp_level != "unavailable":
            conf += 0.10
        confidence = round(min(max(conf, 0.25), 0.95), 2)

        return ProductOpportunityEvaluation(
            opportunity_score=opportunity_score,
            opportunity_level=level,
            confidence=confidence,
            competition_level=comp_level,
            reasoning=reasoning,
            supporting_signals=signals
        )
