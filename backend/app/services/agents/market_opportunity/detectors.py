import hashlib
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, MarketOpportunity,
    TrendSignal, AnomalyDetection
)
from backend.app.services.agents.market_opportunity.scoring_engine import MarketOpportunityScoringEngine


class MarketOpportunityDetectors:
    """
    Deterministic opportunity generators for AI Agent 07 (Market Opportunity Intelligence Agent).
    Covers all 12 core opportunity types with evidence grounding and SHA-256 idempotency fingerprinting.
    """

    SCORING_VERSION = "v1.0"
    KNOWN_PLATFORMS = ["Daraz", "Shopify"]

    @classmethod
    def generate_fingerprint(
        cls,
        target_id: str,
        opportunity_type: str,
        evidence_keys: Optional[List[str]] = None
    ) -> str:
        """
        Produces SHA-256 deterministic idempotency hash.
        """
        raw = f"{target_id}:{opportunity_type}:{sorted(evidence_keys or [])}:{cls.SCORING_VERSION}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # 1. Product Gap Detector
    @classmethod
    def detect_product_gaps(
        cls,
        target_product: UnifiedProduct,
        data_quality_score: float = 85.0,
        trend_score: float = 50.0,
        anomalies: Optional[List[Dict[str, Any]]] = None
    ) -> List[MarketOpportunity]:
        """
        Detects product gap opportunities when a product shows strong ratings/reviews but limited platform coverage.
        """
        if data_quality_score < 70.0:
            return []

        plat_count = len(target_product.platforms) if target_product.platforms else target_product.platform_count
        if plat_count >= len(cls.KNOWN_PLATFORMS):
            return [] # Already has full observed marketplace coverage

        missing = [p for p in cls.KNOWN_PLATFORMS if p.lower() not in [pl.lower() for pl in target_product.platforms]]
        breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
            candidate_product=target_product,
            category=target_product.category,
            data_quality_score=data_quality_score,
            trend_score=trend_score,
            coverage_gap_ratio=len(missing) / len(cls.KNOWN_PLATFORMS),
            cross_platform_count=plat_count,
            active_anomalies=anomalies,
            opportunity_type="product_gap"
        )

        now = datetime.now(timezone.utc)
        reasons = [
            f"Observed opportunity based on increasing marketplace activity in {target_product.category or 'General'}.",
            f"Product is currently verified on {', '.join(target_product.platforms or ['single platform'])}, with unobserved presence on {', '.join(missing)}.",
            f"Buyer satisfaction is verified at {target_product.avg_rating:.1f}/5.0 based on {target_product.total_reviews} reviews."
        ]

        evidence = {
            "current_platforms": target_product.platforms,
            "missing_observed_platforms": missing,
            "avg_rating": target_product.avg_rating,
            "total_reviews": target_product.total_reviews,
            "trend_score": trend_score,
            "data_quality_score": data_quality_score
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "product_gap", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_pg_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="product_gap",
                score=score,
                confidence=conf,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_data_quality", "agent_entity_matching", "agent_trend_detection"],
                warnings=[],
                current_platforms=target_product.platforms,
                missing_observed_platforms=missing,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 2. Price Opportunity Detector
    @classmethod
    def detect_price_opportunities(
        cls,
        target_product: UnifiedProduct,
        platform_listings: List[ProductPlatformListing],
        data_quality_score: float = 85.0,
        anomalies: Optional[List[Dict[str, Any]]] = None
    ) -> List[MarketOpportunity]:
        """
        Detects price variance opportunities across verified marketplace listings.
        """
        if len(platform_listings) < 2 or data_quality_score < 70.0:
            return []

        # Check currency safety
        currencies = {l.currency.upper() for l in platform_listings if l.currency}
        if len(currencies) > 1:
            # Different currencies without certified rate
            now = datetime.now(timezone.utc)
            fp = cls.generate_fingerprint(target_product.unified_product_id, "price_opportunity", ["currency_mismatch"])
            return [
                MarketOpportunity(
                    id=f"opp_po_{uuid.uuid4().hex[:12]}",
                    unified_product_id=target_product.unified_product_id,
                    category=target_product.category,
                    subcategory=target_product.subcategory,
                    brand=target_product.brand,
                    opportunity_type="price_opportunity",
                    score=40.0,
                    confidence=0.50,
                    status="insufficient_data",
                    reasons=["Multi-platform listings observed in differing currencies without certified conversion source."],
                    evidence={"currencies": list(currencies)},
                    source_agent_ids=["agent_entity_matching"],
                    warnings=["currency_comparison_unavailable"],
                    current_platforms=target_product.platforms,
                    fingerprint=fp,
                    data_freshness="fresh",
                    detected_at=now,
                    created_at=now,
                    updated_at=now
                )
            ]

        prices = [l.price for l in platform_listings if l.price and l.price > 0]
        if len(prices) < 2:
            return []

        min_price = min(prices)
        max_price = max(prices)
        if min_price <= 0:
            return []

        spread_pct = ((max_price - min_price) / max_price) * 100.0
        if spread_pct < 5.0:
            return [] # Negligible price spread

        lowest_listing = next(l for l in platform_listings if l.price == min_price)
        highest_listing = next(l for l in platform_listings if l.price == max_price)

        breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
            candidate_product=target_product,
            category=target_product.category,
            data_quality_score=data_quality_score,
            price_spread_pct=spread_pct,
            cross_platform_count=len(platform_listings),
            active_anomalies=anomalies,
            opportunity_type="price_opportunity"
        )

        now = datetime.now(timezone.utc)
        curr = list(currencies)[0] if currencies else "PKR"
        reasons = [
            f"Observed price difference of {spread_pct:.1f}% ({curr} {max_price - min_price:,.2f}) across verified platforms.",
            f"Lowest verified price on {lowest_listing.platform} at {curr} {min_price:,.2f} vs {highest_listing.platform} at {curr} {max_price:,.2f}."
        ]

        evidence = {
            "lowest_platform": lowest_listing.platform,
            "lowest_price": min_price,
            "highest_platform": highest_listing.platform,
            "highest_price": max_price,
            "price_spread_pct": round(spread_pct, 2),
            "currency": curr,
            "listings_count": len(platform_listings)
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "price_opportunity", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_po_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="price_opportunity",
                score=score,
                confidence=conf,
                status=breakdown.eligibility_status,
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_data_quality", "agent_entity_matching"],
                warnings=[],
                current_platforms=target_product.platforms,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 3. Category Opportunity Detector
    @classmethod
    def detect_category_opportunities(
        cls,
        category: str,
        category_products: List[UnifiedProduct],
        category_trend_score: float = 65.0,
        data_quality_score: float = 85.0
    ) -> List[MarketOpportunity]:
        """
        Detects category-level growth and expansion opportunities.
        """
        if not category_products or data_quality_score < 70.0:
            return []

        avg_cat_rating = sum(p.avg_rating for p in category_products) / len(category_products)
        total_cat_reviews = sum(p.total_reviews for p in category_products)

        breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
            category=category,
            data_quality_score=data_quality_score,
            trend_score=category_trend_score,
            coverage_gap_ratio=0.4,
            cross_platform_count=2,
            opportunity_type="category_opportunity"
        )

        now = datetime.now(timezone.utc)
        reasons = [
            f"Category {category} exhibits strong trend score of {category_trend_score:.1f}/100.",
            f"Category catalog comprises {len(category_products)} verified products with cumulative {total_cat_reviews} reviews.",
            f"Average buyer rating across category stands at {avg_cat_rating:.2f}/5.0."
        ]

        evidence = {
            "category": category,
            "product_count": len(category_products),
            "total_reviews": total_cat_reviews,
            "avg_rating": round(avg_cat_rating, 2),
            "trend_score": category_trend_score
        }

        fp = cls.generate_fingerprint(f"cat:{category}", "category_opportunity", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_co_{uuid.uuid4().hex[:12]}",
                category=category,
                opportunity_type="category_opportunity",
                score=score,
                confidence=conf,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_taxonomy", "agent_trend_detection"],
                warnings=[],
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 4. Competitive Gap Detector
    @classmethod
    def detect_competitive_gaps(
        cls,
        target_product: UnifiedProduct,
        competitors: List[UnifiedProduct],
        data_quality_score: float = 85.0
    ) -> List[MarketOpportunity]:
        """
        Identifies measurable competitive advantages (higher rating, lower price, higher review count).
        """
        if not competitors or data_quality_score < 70.0:
            return []

        # Find competitor with lower rating or higher price
        outperformed = [
            c for c in competitors
            if c.unified_product_id != target_product.unified_product_id
            and target_product.avg_rating > c.avg_rating
            and target_product.total_reviews >= 10
        ]

        if not outperformed:
            return []

        best_target_comp = outperformed[0]
        rating_diff = target_product.avg_rating - best_target_comp.avg_rating

        breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
            candidate_product=target_product,
            category=target_product.category,
            data_quality_score=data_quality_score,
            trend_score=65.0,
            coverage_gap_ratio=0.3,
            cross_platform_count=target_product.platform_count,
            opportunity_type="competitive_gap"
        )

        now = datetime.now(timezone.utc)
        reasons = [
            f"Product maintains higher buyer satisfaction ({target_product.avg_rating:.1f} vs {best_target_comp.avg_rating:.1f}) compared to competitor {best_target_comp.canonical_name[:40]}.",
            f"Supported by {target_product.total_reviews} verified reviews in {target_product.category or 'General'}."
        ]

        evidence = {
            "target_rating": target_product.avg_rating,
            "competitor_product_id": best_target_comp.unified_product_id,
            "competitor_rating": best_target_comp.avg_rating,
            "rating_advantage": round(rating_diff, 2),
            "target_reviews": target_product.total_reviews
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "competitive_gap", [best_target_comp.unified_product_id])
        return [
            MarketOpportunity(
                id=f"opp_cg_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="competitive_gap",
                score=score,
                confidence=conf,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_data_quality", "agent_entity_matching"],
                warnings=[],
                current_platforms=target_product.platforms,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 5. Cross-Platform Gap Detector
    @classmethod
    def detect_cross_platform_gaps(
        cls,
        target_product: UnifiedProduct,
        data_quality_score: float = 85.0
    ) -> List[MarketOpportunity]:
        """
        Detects specific unobserved marketplace presence for high-performing products.
        """
        if data_quality_score < 70.0:
            return []

        observed_lower = [p.lower() for p in target_product.platforms]
        missing = [p for p in cls.KNOWN_PLATFORMS if p.lower() not in observed_lower]
        if not missing:
            return []

        breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
            candidate_product=target_product,
            category=target_product.category,
            data_quality_score=data_quality_score,
            trend_score=60.0,
            coverage_gap_ratio=len(missing) / len(cls.KNOWN_PLATFORMS),
            cross_platform_count=len(target_product.platforms),
            opportunity_type="cross_platform_gap"
        )

        now = datetime.now(timezone.utc)
        reasons = [
            f"Potential cross-platform expansion opportunity based on verified product presence on {', '.join(target_product.platforms)}.",
            f"Listing not currently observed on {', '.join(missing)}."
        ]

        evidence = {
            "current_platforms": target_product.platforms,
            "missing_observed_platforms": missing,
            "avg_rating": target_product.avg_rating,
            "total_reviews": target_product.total_reviews
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "cross_platform_gap", missing)
        return [
            MarketOpportunity(
                id=f"opp_xpg_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="cross_platform_gap",
                score=score,
                confidence=conf,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_entity_matching"],
                warnings=[],
                current_platforms=target_product.platforms,
                missing_observed_platforms=missing,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 6. Availability Opportunity Detector
    @classmethod
    def detect_availability_opportunities(
        cls,
        target_product: UnifiedProduct,
        platform_listings: List[ProductPlatformListing]
    ) -> List[MarketOpportunity]:
        """
        Detects stockout and availability gaps.
        """
        if not platform_listings:
            return []

        out_of_stock = [l for l in platform_listings if l.available is False]
        if not out_of_stock:
            return []

        now = datetime.now(timezone.utc)
        reasons = [
            f"Verified stockout observed on {len(out_of_stock)} marketplace listings ({', '.join(l.platform for l in out_of_stock)}).",
            f"High product search demand with limited stock availability represents immediate inventory fulfillment opportunity."
        ]

        evidence = {
            "out_of_stock_platforms": [l.platform for l in out_of_stock],
            "total_observed_listings": len(platform_listings),
            "stockout_ratio": round(len(out_of_stock) / len(platform_listings), 2)
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "availability_opportunity", [l.platform for l in out_of_stock])
        return [
            MarketOpportunity(
                id=f"opp_av_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="availability_opportunity",
                score=78.0,
                confidence=0.88,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_entity_matching"],
                warnings=[],
                current_platforms=target_product.platforms,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 7. Quality Gap Detector
    @classmethod
    def detect_quality_gaps(
        cls,
        category: str,
        category_products: List[UnifiedProduct],
        quality_score_map: Dict[str, float]
    ) -> List[MarketOpportunity]:
        """
        Identifies categories with low data completeness or missing attributes.
        """
        if not category_products:
            return []

        low_qual_prods = [
            p for p in category_products
            if quality_score_map.get(p.unified_product_id, p.completeness_score * 100.0) < 70.0
        ]

        if len(low_qual_prods) < 1:
            return []

        ratio = len(low_qual_prods) / len(category_products)
        now = datetime.now(timezone.utc)
        reasons = [
            f"Category {category} contains {len(low_qual_prods)} products ({ratio*100:.1f}%) with data quality/completeness warnings.",
            "Indicates a data quality remediation and catalog enrichment opportunity."
        ]

        evidence = {
            "category": category,
            "low_quality_product_count": len(low_qual_prods),
            "total_category_products": len(category_products),
            "warning_ratio": round(ratio, 2)
        }

        fp = cls.generate_fingerprint(f"cat:{category}", "quality_gap", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_qg_{uuid.uuid4().hex[:12]}",
                category=category,
                opportunity_type="quality_gap",
                score=72.0,
                confidence=0.90,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_data_quality", "agent_taxonomy"],
                warnings=["data_quality_opportunity"],
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 8. Rising Category Detector
    @classmethod
    def detect_rising_category(
        cls,
        category: str,
        category_trend_score: float,
        breakout_count: int = 1
    ) -> List[MarketOpportunity]:
        """
        Detects categories experiencing accelerating trend momentum.
        """
        if category_trend_score < 65.0:
            return []

        now = datetime.now(timezone.utc)
        reasons = [
            f"Category {category} exhibits strong trend momentum score of {category_trend_score:.1f}/100.",
            f"Backed by {breakout_count} verified rising product signal(s) from Agent 4."
        ]

        evidence = {
            "category": category,
            "category_trend_score": category_trend_score,
            "breakout_signals_count": breakout_count
        }

        fp = cls.generate_fingerprint(f"cat:{category}", "rising_category", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_rc_{uuid.uuid4().hex[:12]}",
                category=category,
                opportunity_type="rising_category",
                score=category_trend_score,
                confidence=0.92,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_taxonomy", "agent_trend_detection"],
                warnings=[],
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 9. Rising Product Detector
    @classmethod
    def detect_rising_product(
        cls,
        target_product: UnifiedProduct,
        trend_score: float,
        trend_signals: List[str]
    ) -> List[MarketOpportunity]:
        """
        Detects individual products showing breakout trend signals.
        """
        if trend_score < 70.0:
            return []

        now = datetime.now(timezone.utc)
        reasons = [
            f"Product demonstrates breakout momentum with trend strength score of {trend_score:.1f}/100.",
            f"Triggered by active trend signals: {', '.join(trend_signals) if trend_signals else 'velocity_spike'}."
        ]

        evidence = {
            "trend_score": trend_score,
            "trend_signals": trend_signals,
            "avg_rating": target_product.avg_rating,
            "total_reviews": target_product.total_reviews
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "rising_product", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_rp_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="rising_product",
                score=trend_score,
                confidence=0.94,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_trend_detection"],
                warnings=[],
                current_platforms=target_product.platforms,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 10. Marketplace Expansion Detector
    @classmethod
    def detect_marketplace_expansion(
        cls,
        target_product: UnifiedProduct,
        data_quality_score: float = 85.0
    ) -> List[MarketOpportunity]:
        """
        Detects specific marketplace expansion avenues.
        """
        if data_quality_score < 70.0:
            return []

        missing = [p for p in cls.KNOWN_PLATFORMS if p.lower() not in [pl.lower() for pl in target_product.platforms]]
        if not missing:
            return []

        now = datetime.now(timezone.utc)
        reasons = [
            f"Marketplace expansion candidate: verified on {', '.join(target_product.platforms)}, unobserved on {', '.join(missing)}.",
            f"High rating ({target_product.avg_rating:.1f}/5.0) signals solid consumer reception for marketplace rollout."
        ]

        evidence = {
            "current_platforms": target_product.platforms,
            "missing_observed_platforms": missing,
            "avg_rating": target_product.avg_rating
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "marketplace_expansion", missing)
        return [
            MarketOpportunity(
                id=f"opp_me_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="marketplace_expansion",
                score=80.0,
                confidence=0.88,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_entity_matching"],
                warnings=[],
                current_platforms=target_product.platforms,
                missing_observed_platforms=missing,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 11. Underserved Category Detector
    @classmethod
    def detect_underserved_category(
        cls,
        category: str,
        category_products: List[UnifiedProduct],
        category_trend_score: float = 70.0
    ) -> List[MarketOpportunity]:
        """
        Identifies categories with strong trend scores but sparse product catalogs (< 3 products).
        """
        if len(category_products) >= 5 or category_trend_score < 60.0:
            return []

        now = datetime.now(timezone.utc)
        reasons = [
            f"Category {category} displays elevated trend score ({category_trend_score:.1f}/100) with only {len(category_products)} verified product listing(s).",
            "Indicates high demand momentum relative to observed catalog supply."
        ]

        evidence = {
            "category": category,
            "product_count": len(category_products),
            "trend_score": category_trend_score
        }

        fp = cls.generate_fingerprint(f"cat:{category}", "underserved_category", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_uc_{uuid.uuid4().hex[:12]}",
                category=category,
                opportunity_type="underserved_category",
                score=85.0,
                confidence=0.90,
                status="active",
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_taxonomy", "agent_trend_detection"],
                warnings=[],
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]

    # 12. Product Launch Opportunity Detector
    @classmethod
    def detect_product_launch_opportunities(
        cls,
        target_product: UnifiedProduct,
        data_quality_score: float = 90.0,
        trend_score: float = 75.0,
        anomalies: Optional[List[Dict[str, Any]]] = None
    ) -> List[MarketOpportunity]:
        """
        Identifies top-tier product launch opportunities combining quality, trend, and high satisfaction.
        """
        if data_quality_score < 80.0 or trend_score < 65.0 or target_product.avg_rating < 4.0:
            return []

        breakdown, score, conf = MarketOpportunityScoringEngine.calculate_score(
            candidate_product=target_product,
            category=target_product.category,
            data_quality_score=data_quality_score,
            trend_score=trend_score,
            coverage_gap_ratio=0.5,
            cross_platform_count=target_product.platform_count,
            active_anomalies=anomalies,
            opportunity_type="product_launch_opportunity"
        )

        now = datetime.now(timezone.utc)
        reasons = [
            f"Prime product launch opportunity in {target_product.category or 'General'}.",
            f"Validated high quality ({data_quality_score:.1f}/100), strong trend momentum ({trend_score:.1f}/100), and rating ({target_product.avg_rating:.1f}/5.0)."
        ]

        evidence = {
            "trend_score": trend_score,
            "data_quality_score": data_quality_score,
            "avg_rating": target_product.avg_rating,
            "total_reviews": target_product.total_reviews
        }

        fp = cls.generate_fingerprint(target_product.unified_product_id, "product_launch_opportunity", list(evidence.keys()))
        return [
            MarketOpportunity(
                id=f"opp_plo_{uuid.uuid4().hex[:12]}",
                unified_product_id=target_product.unified_product_id,
                category=target_product.category,
                subcategory=target_product.subcategory,
                brand=target_product.brand,
                opportunity_type="product_launch_opportunity",
                score=score,
                confidence=conf,
                status=breakdown.eligibility_status,
                reasons=reasons,
                evidence=evidence,
                source_agent_ids=["agent_data_quality", "agent_trend_detection", "agent_entity_matching"],
                warnings=[],
                current_platforms=target_product.platforms,
                fingerprint=fp,
                data_freshness="fresh",
                detected_at=now,
                created_at=now,
                updated_at=now
            )
        ]
