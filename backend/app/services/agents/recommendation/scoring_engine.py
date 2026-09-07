from typing import Dict, Any, List, Optional, Tuple
from backend.app.models.domain import (
    UnifiedProduct, ProductRecommendation, RecommendationScoreBreakdown
)


class RecommendationScoringEngine:
    """
    Deterministic scoring and eligibility engine for Agent 06.
    Calculates 0-100 recommendation scores based on 8 weighted components:
    - Data Quality: 15%
    - Product Similarity: 20%
    - Price Value: 20%
    - Rating Quality: 15%
    - Trend Strength: 15%
    - Availability: 5%
    - Cross-Platform Presence: 5%
    - Freshness: 5%
    """

    MIN_TRUSTED_QUALITY_SCORE = 70.0

    @classmethod
    def calculate_score(
        cls,
        candidate_product: UnifiedProduct,
        target_product: Optional[UnifiedProduct] = None,
        data_quality_score: Optional[float] = None,
        trend_score: Optional[float] = None,
        anomaly_status: Optional[str] = None,
        active_anomalies: Optional[List[Dict[str, Any]]] = None,
        freshness_status: str = "fresh",
        recommendation_type: str = "similar_product"
    ) -> Tuple[RecommendationScoreBreakdown, float, float]:
        """
        Calculates the exact deterministic score, confidence, and score breakdown.
        Returns: (breakdown, total_score, confidence)
        """
        # 1. Data Quality Gate & Score (15% weight)
        raw_quality = data_quality_score if data_quality_score is not None else (candidate_product.completeness_score * 100.0)
        quality_score_val = max(0.0, min(100.0, float(raw_quality)))
        dq_weighted = quality_score_val * 0.15

        # Check quality gate
        if quality_score_val < cls.MIN_TRUSTED_QUALITY_SCORE:
            breakdown = RecommendationScoreBreakdown(
                data_quality_score=dq_weighted,
                total_recommendation_score=round(dq_weighted, 2),
                eligibility_status="quality_gated"
            )
            return breakdown, round(dq_weighted, 2), 0.40

        # 2. Product Similarity Score (20% weight)
        similarity_val = cls._calculate_similarity(candidate_product, target_product, recommendation_type)
        similarity_weighted = similarity_val * 0.20

        # 3. Price Value Score (20% weight)
        price_val = cls._calculate_price_value(candidate_product, target_product)
        price_weighted = price_val * 0.20

        # 4. Rating Quality Score (15% weight)
        rating_val = cls._calculate_rating_quality(candidate_product.avg_rating, candidate_product.total_reviews)
        rating_weighted = rating_val * 0.15

        # 5. Trend Strength Score (15% weight)
        trend_val = max(0.0, min(100.0, float(trend_score if trend_score is not None else 50.0)))
        trend_weighted = trend_val * 0.15

        # 6. Availability Score (5% weight)
        availability_val = 100.0 if candidate_product.listings_count > 0 else 50.0
        availability_weighted = availability_val * 0.05

        # 7. Cross-Platform Presence (5% weight)
        plat_count = len(candidate_product.platforms) if candidate_product.platforms else candidate_product.platform_count
        cross_plat_val = 100.0 if plat_count >= 2 else (60.0 if plat_count == 1 else 0.0)
        cross_plat_weighted = cross_plat_val * 0.05

        # 8. Freshness Score (5% weight)
        freshness_multipliers = {
            "fresh": 100.0,
            "recent": 75.0,
            "stale": 40.0,
            "insufficient_data": 0.0
        }
        fresh_val = freshness_multipliers.get(freshness_status.lower(), 50.0)
        freshness_weighted = fresh_val * 0.05

        # Raw Total Score
        total_score = (
            dq_weighted +
            similarity_weighted +
            price_weighted +
            rating_weighted +
            trend_weighted +
            availability_weighted +
            cross_plat_weighted +
            freshness_weighted
        )
        total_score = max(0.0, min(100.0, total_score))

        # Check Anomaly Blocking
        eligibility = "eligible"
        if active_anomalies:
            critical_or_high = [a for a in active_anomalies if a.get("severity") in ("critical", "high")]
            if critical_or_high:
                # If best_value or better_price, block or heavily penalize
                if recommendation_type in ("best_value", "better_price"):
                    eligibility = "anomaly_blocked"
                    total_score = max(10.0, total_score * 0.40)
                else:
                    total_score = max(15.0, total_score * 0.75)

        # Confidence Calculation
        # Confidence is derived from data completeness, observation density, and absence of anomalies
        conf = 0.80
        if quality_score_val >= 85:
            conf += 0.08
        if candidate_product.total_reviews >= 20:
            conf += 0.05
        if plat_count >= 2:
            conf += 0.04
        if freshness_status == "fresh":
            conf += 0.03
        elif freshness_status == "stale":
            conf -= 0.15
        elif freshness_status == "insufficient_data":
            conf -= 0.35

        if active_anomalies:
            conf -= 0.10

        conf = max(0.20, min(0.99, conf))

        breakdown = RecommendationScoreBreakdown(
            data_quality_score=round(dq_weighted, 2),
            product_similarity_score=round(similarity_weighted, 2),
            price_value_score=round(price_weighted, 2),
            rating_quality_score=round(rating_weighted, 2),
            trend_strength_score=round(trend_weighted, 2),
            availability_score=round(availability_weighted, 2),
            cross_platform_score=round(cross_plat_weighted, 2),
            freshness_score=round(freshness_weighted, 2),
            total_recommendation_score=round(total_score, 2),
            eligibility_status=eligibility
        )

        return breakdown, round(total_score, 2), round(conf, 3)

    @classmethod
    def _calculate_similarity(
        cls,
        candidate: UnifiedProduct,
        target: Optional[UnifiedProduct],
        recommendation_type: str
    ) -> float:
        """
        Calculates similarity index (0-100).
        If no target product is provided (e.g. trending/high_quality/best_value catalog discovery),
        returns a baseline suitability score.
        """
        if not target:
            return 80.0

        # Never recommend the exact same canonical product as a similar/alternative product!
        if candidate.id == target.id or candidate.unified_product_id == target.unified_product_id:
            if recommendation_type in ("similar_product", "alternative_product"):
                return 0.0 # Excluded

        score = 30.0 # Base

        # Category match
        if candidate.category and target.category and candidate.category.lower() == target.category.lower():
            score += 35.0

        # Subcategory match
        if candidate.subcategory and target.subcategory and candidate.subcategory.lower() == target.subcategory.lower():
            score += 15.0

        # Brand match (or complementary)
        if candidate.brand and target.brand:
            if candidate.brand.lower() == target.brand.lower():
                score += 10.0
            else:
                score += 5.0

        # Attribute overlap
        if candidate.identifiers and target.identifiers:
            cand_keys = set(candidate.identifiers.keys())
            target_keys = set(target.identifiers.keys())
            if cand_keys.intersection(target_keys):
                score += 10.0

        return min(100.0, score)

    @classmethod
    def _calculate_price_value(
        cls,
        candidate: UnifiedProduct,
        target: Optional[UnifiedProduct]
    ) -> float:
        """
        Calculates price value score (0-100).
        """
        cand_price = candidate.average_price or candidate.lowest_price
        if cand_price is None or cand_price <= 0:
            return 50.0

        if not target:
            # General price health
            return 75.0

        target_price = target.average_price or target.lowest_price
        if target_price is None or target_price <= 0:
            return 70.0

        # Check currency safety
        cand_curr = (candidate.primary_currency or "USD").upper()
        target_curr = (target.primary_currency or "USD").upper()
        if cand_curr != target_curr:
            # Cannot compare directly without verified exchange rate
            return 50.0

        diff = (target_price - cand_price) / target_price
        if diff > 0.30: # 30%+ cheaper
            return 95.0
        elif diff > 0.15: # 15-30% cheaper
            return 85.0
        elif diff >= 0: # 0-15% cheaper
            return 75.0
        elif diff > -0.20: # Up to 20% more expensive
            return 60.0
        else: # Significantly more expensive
            return 40.0

    @classmethod
    def _calculate_rating_quality(
        cls,
        rating: float,
        reviews: int
    ) -> float:
        """
        Calculates rating quality score (0-100).
        """
        r = max(0.0, min(5.0, float(rating or 0.0)))
        rev = max(0, int(reviews or 0))

        # Base from rating: 0-5 -> 0-70 points
        rating_points = (r / 5.0) * 70.0

        # Review volume credibility: up to 30 points
        if rev >= 500:
            review_points = 30.0
        elif rev >= 100:
            review_points = 25.0
        elif rev >= 25:
            review_points = 18.0
        elif rev >= 5:
            review_points = 10.0
        else:
            review_points = 3.0

        return min(100.0, rating_points + review_points)
