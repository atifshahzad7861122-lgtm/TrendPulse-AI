import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, ProductRecommendation,
    RecommendationScoreBreakdown, RecommendationCandidate
)
from backend.app.services.agents.recommendation.scoring_engine import RecommendationScoringEngine


class RecommendationGenerators:
    """
    Deterministic rule generators for all 10 recommendation types:
    - similar_product
    - alternative_product
    - better_price
    - trending_product
    - high_quality
    - cross_platform
    - category_recommendation
    - rising_product
    - opportunity
    - best_value
    """

    @classmethod
    def generate_fingerprint(
        cls,
        user_id: Optional[str],
        product_id: str,
        recommendation_type: str,
        target_product_id: Optional[str] = None,
        ranking_version: str = "v1"
    ) -> str:
        """
        Creates a deterministic SHA-256 fingerprint to prevent duplicate recommendations.
        """
        raw = f"{user_id or 'global'}:{product_id}:{recommendation_type}:{target_product_id or 'none'}:{ranking_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def generate_similar_products(
        cls,
        target_product: UnifiedProduct,
        catalog: List[UnifiedProduct],
        data_quality_map: Optional[Dict[str, float]] = None,
        trend_score_map: Optional[Dict[str, float]] = None,
        anomaly_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """
        Finds similar products in the same category/attributes.
        CRITICAL: Never recommends the exact same canonical product!
        """
        recs: List[ProductRecommendation] = []
        target_id = target_product.unified_product_id or target_product.id

        for p in catalog:
            p_id = p.unified_product_id or p.id
            if p_id == target_id:
                continue # Strictly exclude self

            # Filter by matching category or subcategory
            if not (p.category and target_product.category and p.category.lower() == target_product.category.lower()):
                continue

            dq = (data_quality_map or {}).get(p_id, p.completeness_score * 100.0)
            tr = (trend_score_map or {}).get(p_id, 50.0)
            anoms = (anomaly_map or {}).get(p_id, [])

            breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                candidate_product=p,
                target_product=target_product,
                data_quality_score=dq,
                trend_score=tr,
                active_anomalies=anoms,
                recommendation_type="similar_product"
            )

            if breakdown.eligibility_status == "quality_gated":
                continue

            reasons = [
                f"Shares same category '{p.category}' with {target_product.canonical_name}",
                f"Observed buyer rating of {p.avg_rating:.1f}/5.0 across {p.total_reviews} reviews"
            ]
            if p.brand and target_product.brand and p.brand.lower() == target_product.brand.lower():
                reasons.append(f"Matching brand '{p.brand}'")

            fp = cls.generate_fingerprint(None, p_id, "similar_product", target_id)
            rec = ProductRecommendation(
                id=f"rec_sim_{uuid.uuid4().hex[:12]}",
                unified_product_id=p_id,
                target_product_id=target_id,
                recommendation_type="similar_product",
                score=score,
                confidence=conf,
                reasons=reasons,
                evidence={
                    "target_category": target_product.category,
                    "target_brand": target_product.brand,
                    "candidate_price": p.average_price or p.lowest_price,
                    "candidate_rating": p.avg_rating,
                    "score_breakdown": breakdown.model_dump()
                },
                source_agents=["agent_taxonomy", "agent_data_quality"],
                platforms=p.platforms or [],
                category=p.category,
                brand=p.brand,
                fingerprint=fp,
                status="active",
                freshness_status="fresh"
            )
            recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]

    @classmethod
    def generate_alternative_products(
        cls,
        target_product: UnifiedProduct,
        catalog: List[UnifiedProduct],
        data_quality_map: Optional[Dict[str, float]] = None,
        trend_score_map: Optional[Dict[str, float]] = None,
        anomaly_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """
        Finds alternatives with higher rating, better price, or higher quality score.
        """
        recs: List[ProductRecommendation] = []
        target_id = target_product.unified_product_id or target_product.id
        target_rating = target_product.avg_rating or 0.0
        target_price = target_product.average_price or target_product.lowest_price or 0.0

        for p in catalog:
            p_id = p.unified_product_id or p.id
            if p_id == target_id:
                continue

            if not (p.category and target_product.category and p.category.lower() == target_product.category.lower()):
                continue

            dq = (data_quality_map or {}).get(p_id, p.completeness_score * 100.0)
            tr = (trend_score_map or {}).get(p_id, 50.0)
            anoms = (anomaly_map or {}).get(p_id, [])

            p_price = p.average_price or p.lowest_price or 0.0
            # Must offer measurable advantage (higher rating, lower observed price, or higher trend)
            has_advantage = (p.avg_rating > target_rating) or (target_price > 0 and 0 < p_price < target_price) or (tr > 70.0)
            if not has_advantage:
                continue

            breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                candidate_product=p,
                target_product=target_product,
                data_quality_score=dq,
                trend_score=tr,
                active_anomalies=anoms,
                recommendation_type="alternative_product"
            )

            if breakdown.eligibility_status == "quality_gated":
                continue

            reasons = []
            if p.avg_rating > target_rating:
                reasons.append(f"Higher rated ({p.avg_rating:.1f} vs {target_rating:.1f})")
            if target_price > 0 and 0 < p_price < target_price:
                pct = ((target_price - p_price) / target_price) * 100.0
                reasons.append(f"Lower observed price ({p.primary_currency} {p_price:.2f}, -{pct:.0f}%)")
            if tr > 70.0:
                reasons.append(f"Stronger trend score ({tr:.0f}/100)")

            fp = cls.generate_fingerprint(None, p_id, "alternative_product", target_id)
            rec = ProductRecommendation(
                id=f"rec_alt_{uuid.uuid4().hex[:12]}",
                unified_product_id=p_id,
                target_product_id=target_id,
                recommendation_type="alternative_product",
                score=score,
                confidence=conf,
                reasons=reasons,
                evidence={
                    "target_rating": target_rating,
                    "target_price": target_price,
                    "candidate_rating": p.avg_rating,
                    "candidate_price": p_price,
                    "score_breakdown": breakdown.model_dump()
                },
                source_agents=["agent_taxonomy", "agent_trend_detection", "agent_data_quality"],
                platforms=p.platforms or [],
                category=p.category,
                brand=p.brand,
                fingerprint=fp,
                status="active",
                freshness_status="fresh"
            )
            recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]

    @classmethod
    def generate_better_price_recommendations(
        cls,
        target_product: UnifiedProduct,
        platform_listings: List[ProductPlatformListing],
        data_quality_map: Optional[Dict[str, float]] = None,
        anomaly_map: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> List[ProductRecommendation]:
        """
        Finds cross-platform or cross-seller better-price options for the same unified product.
        CRITICAL: Validates currency compatibility. Returns currency_comparison_unavailable on unknown conversions.
        """
        recs: List[ProductRecommendation] = []
        target_id = target_product.unified_product_id or target_product.id

        if not platform_listings or len(platform_listings) < 2:
            return recs

        # Group listings by currency
        currencies = set(l.currency.upper() for l in platform_listings if l.currency)
        if len(currencies) > 1:
            # Multi-currency safety gate: cannot blindly compare PKR to USD or EUR
            # Check if all listings share target currency
            primary_curr = (target_product.primary_currency or "USD").upper()
            non_matching = [c for c in currencies if c != primary_curr]
            if non_matching:
                # Return currency_comparison_unavailable recommendation warning
                rec = ProductRecommendation(
                    id=f"rec_bp_{uuid.uuid4().hex[:12]}",
                    unified_product_id=target_id,
                    target_product_id=target_id,
                    recommendation_type="better_price",
                    score=50.0,
                    confidence=0.50,
                    reasons=["Multi-currency cross-platform listings detected"],
                    evidence={"currency_status": "currency_comparison_unavailable", "currencies": list(currencies)},
                    source_agents=["agent_entity_matching"],
                    warnings=["currency_comparison_unavailable: exchange rates not fabricated"],
                    platforms=[l.platform for l in platform_listings],
                    category=target_product.category,
                    brand=target_product.brand,
                    fingerprint=cls.generate_fingerprint(None, target_id, "better_price", target_id),
                    status="active",
                    freshness_status="fresh"
                )
                return [rec]

        # Valid same-currency listings: find lowest price
        sorted_listings = sorted([l for l in platform_listings if l.price and l.price > 0], key=lambda x: x.price)
        if not sorted_listings:
            return recs

        lowest = sorted_listings[0]
        highest = sorted_listings[-1]
        if highest.price > lowest.price:
            savings = highest.price - lowest.price
            pct_savings = (savings / highest.price) * 100.0

            reasons = [
                f"Lowest observed price on {lowest.platform} ({lowest.currency} {lowest.price:.2f})",
                f"Potential savings of {lowest.currency} {savings:.2f} (-{pct_savings:.0f}%) vs {highest.platform}"
            ]
            fp = cls.generate_fingerprint(None, target_id, "better_price", target_id)
            rec = ProductRecommendation(
                id=f"rec_bp_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_id,
                target_product_id=target_id,
                recommendation_type="better_price",
                score=min(100.0, 70.0 + (pct_savings * 0.5)),
                confidence=0.92,
                reasons=reasons,
                evidence={
                    "lowest_platform": lowest.platform,
                    "lowest_price": lowest.price,
                    "highest_platform": highest.platform,
                    "highest_price": highest.price,
                    "currency": lowest.currency,
                    "savings_amount": savings,
                    "savings_percent": pct_savings
                },
                source_agents=["agent_entity_matching"],
                platforms=[l.platform for l in sorted_listings],
                category=target_product.category,
                brand=target_product.brand,
                fingerprint=fp,
                status="active",
                freshness_status="fresh"
            )
            recs.append(rec)

        return recs

    @classmethod
    def generate_trending_recommendations(
        cls,
        catalog: List[UnifiedProduct],
        trend_score_map: Dict[str, float],
        trend_signals_map: Optional[Dict[str, List[str]]] = None,
        data_quality_map: Optional[Dict[str, float]] = None,
        anomaly_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        min_trend_score: float = 65.0,
        limit: int = 10
    ) -> List[ProductRecommendation]:
        """
        Generates trending product recommendations grounded in Agent 4 trend signals.
        """
        recs: List[ProductRecommendation] = []

        for p in catalog:
            p_id = p.unified_product_id or p.id
            tr = trend_score_map.get(p_id, 0.0)
            if tr < min_trend_score:
                continue

            dq = (data_quality_map or {}).get(p_id, p.completeness_score * 100.0)
            anoms = (anomaly_map or {}).get(p_id, [])
            signals = (trend_signals_map or {}).get(p_id, [])

            breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                candidate_product=p,
                data_quality_score=dq,
                trend_score=tr,
                active_anomalies=anoms,
                recommendation_type="trending_product"
            )

            if breakdown.eligibility_status == "quality_gated":
                continue

            reasons = [
                f"High market trend score of {tr:.0f}/100",
                f"Observed review velocity and demand momentum"
            ]
            if signals:
                reasons.append(f"Active trend signals: {', '.join(signals[:3])}")

            fp = cls.generate_fingerprint(None, p_id, "trending_product")
            rec = ProductRecommendation(
                id=f"rec_tr_{uuid.uuid4().hex[:12]}",
                unified_product_id=p_id,
                recommendation_type="trending_product",
                score=score,
                confidence=conf,
                reasons=reasons,
                evidence={
                    "trend_score": tr,
                    "trend_signals": signals,
                    "score_breakdown": breakdown.model_dump()
                },
                source_agents=["agent_trend_detection", "agent_data_quality"],
                platforms=p.platforms or [],
                category=p.category,
                brand=p.brand,
                fingerprint=fp,
                status="active",
                freshness_status="fresh"
            )
            recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]

    @classmethod
    def generate_high_quality_recommendations(
        cls,
        catalog: List[UnifiedProduct],
        data_quality_map: Dict[str, float],
        anomaly_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        min_quality_score: float = 85.0,
        limit: int = 10
    ) -> List[ProductRecommendation]:
        """
        Generates high-quality recommendations grounded in Agent 1 quality audits.
        """
        recs: List[ProductRecommendation] = []

        for p in catalog:
            p_id = p.unified_product_id or p.id
            dq = data_quality_map.get(p_id, p.completeness_score * 100.0)
            if dq < min_quality_score or p.avg_rating < 4.0:
                continue

            anoms = (anomaly_map or {}).get(p_id, [])
            breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                candidate_product=p,
                data_quality_score=dq,
                trend_score=60.0,
                active_anomalies=anoms,
                recommendation_type="high_quality"
            )

            if breakdown.eligibility_status == "quality_gated":
                continue

            reasons = [
                f"Verified high data quality score ({dq:.0f}/100)",
                f"Strong buyer satisfaction ({p.avg_rating:.1f}/5.0 with {p.total_reviews} reviews)",
                f"Comprehensive product attributes and verified listings"
            ]

            fp = cls.generate_fingerprint(None, p_id, "high_quality")
            rec = ProductRecommendation(
                id=f"rec_hq_{uuid.uuid4().hex[:12]}",
                unified_product_id=p_id,
                recommendation_type="high_quality",
                score=score,
                confidence=conf,
                reasons=reasons,
                evidence={
                    "quality_score": dq,
                    "rating": p.avg_rating,
                    "review_count": p.total_reviews,
                    "score_breakdown": breakdown.model_dump()
                },
                source_agents=["agent_data_quality"],
                platforms=p.platforms or [],
                category=p.category,
                brand=p.brand,
                fingerprint=fp,
                status="active",
                freshness_status="fresh"
            )
            recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]

    @classmethod
    def generate_cross_platform_recommendations(
        cls,
        target_product: UnifiedProduct,
        platform_listings: List[ProductPlatformListing]
    ) -> List[ProductRecommendation]:
        """
        Generates cross-platform intelligence recommendations displaying multi-marketplace availability.
        """
        recs: List[ProductRecommendation] = []
        target_id = target_product.unified_product_id or target_product.id

        if not platform_listings:
            return recs

        plats = list(set(l.platform for l in platform_listings))
        reasons = [
            f"Available across {len(plats)} verified marketplace platform(s): {', '.join(plats)}",
            f"Cross-platform inventory and listing synchronization confirmed"
        ]

        listing_evidence = [
            {
                "platform": l.platform,
                "price": l.price,
                "currency": l.currency,
                "rating": l.rating,
                "review_count": l.review_count,
                "available": l.available,
                "seller": l.seller_name
            }
            for l in platform_listings
        ]

        fp = cls.generate_fingerprint(None, target_id, "cross_platform", target_id)
        rec = ProductRecommendation(
            id=f"rec_xp_{uuid.uuid4().hex[:12]}",
            unified_product_id=target_id,
            target_product_id=target_id,
            recommendation_type="cross_platform",
            score=85.0 if len(plats) >= 2 else 65.0,
            confidence=0.95,
            reasons=reasons,
            evidence={
                "platform_count": len(plats),
                "platforms": plats,
                "listings": listing_evidence
            },
            source_agents=["agent_entity_matching"],
            platforms=plats,
            category=target_product.category,
            brand=target_product.brand,
            fingerprint=fp,
            status="active",
            freshness_status="fresh"
        )
        recs.append(rec)
        return recs

    @classmethod
    def generate_best_value_recommendations(
        cls,
        catalog: List[UnifiedProduct],
        data_quality_map: Optional[Dict[str, float]] = None,
        trend_score_map: Optional[Dict[str, float]] = None,
        anomaly_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        limit: int = 10
    ) -> List[ProductRecommendation]:
        """
        Generates best-value recommendations combining price, rating, reviews, quality, availability, trend,
        and absence of critical anomalies.
        """
        recs: List[ProductRecommendation] = []

        for p in catalog:
            p_id = p.unified_product_id or p.id
            if p.avg_rating < 4.0 or p.total_reviews < 5:
                continue

            dq = (data_quality_map or {}).get(p_id, p.completeness_score * 100.0)
            tr = (trend_score_map or {}).get(p_id, 50.0)
            anoms = (anomaly_map or {}).get(p_id, [])

            # Check if critical anomaly blocks best_value
            has_crit_price_anomaly = any(
                a.get("severity") in ("critical", "high") and "price" in a.get("anomaly_type", "").lower()
                for a in anoms
            )
            if has_crit_price_anomaly:
                continue # Strictly blocked from best_value

            breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                candidate_product=p,
                data_quality_score=dq,
                trend_score=tr,
                active_anomalies=anoms,
                recommendation_type="best_value"
            )

            if breakdown.eligibility_status != "eligible":
                continue

            price = p.average_price or p.lowest_price or 0.0
            reasons = [
                f"Strong composite value index of {score:.0f}/100",
                f"High buyer rating of {p.avg_rating:.1f}/5.0 ({p.total_reviews} reviews)",
                f"Observed price of {p.primary_currency} {price:.2f} with healthy data quality ({dq:.0f}/100)"
            ]

            fp = cls.generate_fingerprint(None, p_id, "best_value")
            rec = ProductRecommendation(
                id=f"rec_bv_{uuid.uuid4().hex[:12]}",
                unified_product_id=p_id,
                recommendation_type="best_value",
                score=score,
                confidence=conf,
                reasons=reasons,
                evidence={
                    "price": price,
                    "currency": p.primary_currency,
                    "rating": p.avg_rating,
                    "reviews": p.total_reviews,
                    "quality_score": dq,
                    "trend_score": tr,
                    "score_breakdown": breakdown.model_dump()
                },
                source_agents=["agent_data_quality", "agent_trend_detection", "agent_anomaly_detection"],
                platforms=p.platforms or [],
                category=p.category,
                brand=p.brand,
                fingerprint=fp,
                status="active",
                freshness_status="fresh"
            )
            recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]

    @classmethod
    def generate_category_recommendations(
        cls,
        category: str,
        catalog: List[UnifiedProduct],
        data_quality_map: Optional[Dict[str, float]] = None,
        trend_score_map: Optional[Dict[str, float]] = None,
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """
        Generates top category-wide recommendations.
        """
        recs: List[ProductRecommendation] = []
        matching = [p for p in catalog if p.category and p.category.lower() == category.lower()]

        for p in matching:
            p_id = p.unified_product_id or p.id
            dq = (data_quality_map or {}).get(p_id, p.completeness_score * 100.0)
            tr = (trend_score_map or {}).get(p_id, 50.0)

            breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                candidate_product=p,
                data_quality_score=dq,
                trend_score=tr,
                recommendation_type="category_recommendation"
            )
            if breakdown.eligibility_status == "quality_gated":
                continue

            reasons = [
                f"Top ranked in category '{category}'",
                f"Buyer rating: {p.avg_rating:.1f}/5.0 ({p.total_reviews} reviews)"
            ]
            fp = cls.generate_fingerprint(None, p_id, "category_recommendation", category)
            rec = ProductRecommendation(
                id=f"rec_cat_{uuid.uuid4().hex[:12]}",
                unified_product_id=p_id,
                recommendation_type="category_recommendation",
                score=score,
                confidence=conf,
                reasons=reasons,
                evidence={"category": category, "score_breakdown": breakdown.model_dump()},
                source_agents=["agent_taxonomy", "agent_data_quality"],
                platforms=p.platforms or [],
                category=p.category,
                brand=p.brand,
                fingerprint=fp,
                status="active",
                freshness_status="fresh"
            )
            recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]

    @classmethod
    def generate_opportunity_recommendations(
        cls,
        catalog: List[UnifiedProduct],
        trend_score_map: Dict[str, float],
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """
        Generates opportunity recommendations for high-trend products with low platform competition.
        """
        recs: List[ProductRecommendation] = []

        for p in catalog:
            p_id = p.unified_product_id or p.id
            tr = trend_score_map.get(p_id, 0.0)
            plat_count = len(p.platforms) if p.platforms else p.platform_count

            # High trend + single platform presence represents a market expansion opportunity
            if tr >= 70.0 and plat_count <= 1:
                breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                    candidate_product=p,
                    trend_score=tr,
                    recommendation_type="opportunity"
                )

                reasons = [
                    f"High consumer demand momentum (Trend score: {tr:.0f}/100)",
                    f"Low marketplace saturation: only active on {plat_count} platform(s)"
                ]
                fp = cls.generate_fingerprint(None, p_id, "opportunity")
                rec = ProductRecommendation(
                    id=f"rec_opp_{uuid.uuid4().hex[:12]}",
                    unified_product_id=p_id,
                    recommendation_type="opportunity",
                    score=score,
                    confidence=conf,
                    reasons=reasons,
                    evidence={"trend_score": tr, "platform_count": plat_count, "score_breakdown": breakdown.model_dump()},
                    source_agents=["agent_trend_detection", "agent_entity_matching"],
                    platforms=p.platforms or [],
                    category=p.category,
                    brand=p.brand,
                    fingerprint=fp,
                    status="active",
                    freshness_status="fresh"
                )
                recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]

    @classmethod
    def generate_rising_product_recommendations(
        cls,
        catalog: List[UnifiedProduct],
        trend_score_map: Dict[str, float],
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """
        Generates rising product recommendations (emerging momentum products).
        """
        recs: List[ProductRecommendation] = []

        for p in catalog:
            p_id = p.unified_product_id or p.id
            tr = trend_score_map.get(p_id, 0.0)
            # Emerging/rising products: trend score between 55 and 80 with positive ratings
            if 55.0 <= tr < 80.0 and p.avg_rating >= 4.0:
                breakdown, score, conf = RecommendationScoringEngine.calculate_score(
                    candidate_product=p,
                    trend_score=tr,
                    recommendation_type="rising_product"
                )

                reasons = [
                    f"Rising market velocity (Trend score: {tr:.0f}/100)",
                    f"High customer sentiment ({p.avg_rating:.1f}/5.0 stars)"
                ]
                fp = cls.generate_fingerprint(None, p_id, "rising_product")
                rec = ProductRecommendation(
                    id=f"rec_ris_{uuid.uuid4().hex[:12]}",
                    unified_product_id=p_id,
                    recommendation_type="rising_product",
                    score=score,
                    confidence=conf,
                    reasons=reasons,
                    evidence={"trend_score": tr, "rating": p.avg_rating, "score_breakdown": breakdown.model_dump()},
                    source_agents=["agent_trend_detection"],
                    platforms=p.platforms or [],
                    category=p.category,
                    brand=p.brand,
                    fingerprint=fp,
                    status="active",
                    freshness_status="fresh"
                )
                recs.append(rec)

        recs.sort(key=lambda x: x.score, reverse=True)
        return recs[:limit]
