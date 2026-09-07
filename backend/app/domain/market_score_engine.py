"""
Transparent, Deterministic Market Scoring Engine for Phase 3 Market Intelligence.

Calculates a composite Market Score (0.0 to 100.0) based strictly on verified,
observed inputs without random numbers or synthetic interpolation.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from backend.app.models.domain import MarketScoreBreakdown


class MarketScoreEngine:
    """
    Transparent mathematical scoring engine calculating canonical Market Score.

    Weighting Matrix:
      1. Demand Conviction:       30% (Demand score derived from views, reviews, search presence)
      2. Growth Momentum:         20% (Verified historical growth or neutral baseline)
      3. Marketplace Acclaim:     20% (Rating volume & average star score)
      4. Price Health & Stability:15% (Availability, reasonable discount, competitive pricing)
      5. Cross-Platform Presence: 15% (Multi-marketplace validation or single-platform presence)
    """

    WEIGHT_DEMAND = 0.30
    WEIGHT_GROWTH = 0.20
    WEIGHT_ACCLAIM = 0.20
    WEIGHT_PRICE_HEALTH = 0.15
    WEIGHT_CROSS_PLATFORM = 0.15

    SCORING_VERSION = "3.0.0"

    @classmethod
    def calculate_market_score(
        cls,
        demand_score: float = 50.0,
        growth_rate: Optional[float] = None,
        rating: float = 0.0,
        review_count: int = 0,
        price: float = 0.0,
        original_price: Optional[float] = None,
        is_available: bool = True,
        platform_count: int = 1,
        data_quality_score: float = 80.0,
        has_historical_data: bool = False
    ) -> MarketScoreBreakdown:
        """
        Calculates a calibrated composite market score (0 - 100) with complete explainability.
        """
        # 1. Demand Component (0 - 100)
        demand_comp = round(min(max(demand_score, 0.0), 100.0), 2)

        # 2. Growth Component (0 - 100)
        # If real historical data exists, normalize growth rate; otherwise use neutral baseline 50.0
        if has_historical_data and growth_rate is not None:
            # -50% to +150% growth mapped to 0-100
            if growth_rate >= 100.0:
                growth_comp = 95.0
            elif growth_rate >= 50.0:
                growth_comp = 80.0
            elif growth_rate >= 10.0:
                growth_comp = 65.0
            elif growth_rate >= 0.0:
                growth_comp = 55.0
            elif growth_rate >= -20.0:
                growth_comp = 40.0
            else:
                growth_comp = 20.0
        else:
            growth_comp = 50.0  # Neutral baseline when history is unavailable

        # 3. Marketplace Acclaim Component (0 - 100)
        # Combines average rating (4.0-5.0) with review count credibility
        if rating > 0:
            rating_base = min(max((rating - 2.0) / 3.0, 0.0), 1.0) * 60.0  # 0 to 60 based on rating
        else:
            rating_base = 30.0  # unrated baseline

        if review_count >= 500:
            volume_bonus = 40.0
        elif review_count >= 100:
            volume_bonus = 30.0
        elif review_count >= 20:
            volume_bonus = 20.0
        elif review_count > 0:
            volume_bonus = 10.0
        else:
            volume_bonus = 0.0

        acclaim_comp = round(min(rating_base + volume_bonus, 100.0), 2)

        # 4. Price Health & Stability Component (0 - 100)
        if not is_available:
            price_health_comp = 20.0  # Penalize out of stock
        elif price <= 0:
            price_health_comp = 30.0  # Missing or invalid price
        else:
            base_health = 70.0
            # Check discount sanity
            if original_price and original_price > price:
                discount_pct = ((original_price - price) / original_price) * 100.0
                if 5.0 <= discount_pct <= 50.0:
                    base_health += 20.0  # Attractive real discount
                elif discount_pct > 70.0:
                    base_health -= 15.0  # Suspicious / steep discount
            price_health_comp = round(min(base_health, 100.0), 2)

        # 5. Cross-Platform Coverage Component (0 - 100)
        if platform_count >= 4:
            cross_comp = 100.0
        elif platform_count == 3:
            cross_comp = 85.0
        elif platform_count == 2:
            cross_comp = 70.0
        elif platform_count == 1:
            cross_comp = 50.0
        else:
            cross_comp = 20.0

        # Weighted Total Score
        total_score = (
            (demand_comp * cls.WEIGHT_DEMAND) +
            (growth_comp * cls.WEIGHT_GROWTH) +
            (acclaim_comp * cls.WEIGHT_ACCLAIM) +
            (price_health_comp * cls.WEIGHT_PRICE_HEALTH) +
            (cross_comp * cls.WEIGHT_CROSS_PLATFORM)
        )
        total_score = round(min(max(total_score, 5.0), 99.5), 1)

        # Confidence Calculation
        # Adjusted by data quality score, presence of real reviews, and historical data
        conf = (data_quality_score / 100.0) * 0.60
        if review_count >= 20:
            conf += 0.20
        elif review_count > 0:
            conf += 0.10
        if has_historical_data:
            conf += 0.20
        else:
            conf += 0.05
        if not is_available:
            conf -= 0.10
        confidence = round(min(max(conf, 0.20), 0.98), 2)

        weights_dict = {
            "demand": cls.WEIGHT_DEMAND,
            "growth": cls.WEIGHT_GROWTH,
            "acclaim": cls.WEIGHT_ACCLAIM,
            "price_health": cls.WEIGHT_PRICE_HEALTH,
            "cross_platform": cls.WEIGHT_CROSS_PLATFORM
        }

        history_status = "measured" if (has_historical_data and growth_rate is not None) else "insufficient_history"

        return MarketScoreBreakdown(
            demand_component=demand_comp,
            growth_component=growth_comp,
            marketplace_acclaim_component=acclaim_comp,
            price_health_component=price_health_comp,
            cross_platform_component=cross_comp,
            total_score=total_score,
            weights=weights_dict,
            confidence=confidence,
            data_quality_score=data_quality_score,
            history_status=history_status,
            calculation_timestamp=datetime.now(timezone.utc)
        )
