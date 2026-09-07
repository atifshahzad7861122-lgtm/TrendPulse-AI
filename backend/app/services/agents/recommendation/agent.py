import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, ProductRecommendation,
    RecommendationCandidate, RecommendationInteraction, RecommendationAudit,
    RecommendationScoreBreakdown, ProductRecommendationSummary, AgentRecommendationStats
)
from backend.app.repositories.base import (
    UnifiedProductRepository, DataQualityRepository,
    TrendDetectionRepository, AnomalyDetectionRepository,
    RecommendationRepository
)
from backend.app.services.agents.recommendation.scoring_engine import RecommendationScoringEngine
from backend.app.services.agents.recommendation.generators import RecommendationGenerators
from backend.app.services.agents.recommendation.llm_resolver import RecommendationLLMResolver
from backend.app.services.agents.recommendation.memory_manager import RecommendationMemoryManager


class ProductRecommendationAgent:
    """
    Master orchestrator for AI Agent 06: Recommendation & Product Intelligence Agent.
    Converts verified marketplace intelligence into explainable, evidence-grounded recommendations.
    """

    def __init__(
        self,
        recommendation_repo: RecommendationRepository,
        unified_product_repo: UnifiedProductRepository,
        data_quality_repo: Optional[DataQualityRepository] = None,
        trend_repo: Optional[TrendDetectionRepository] = None,
        anomaly_repo: Optional[AnomalyDetectionRepository] = None,
        gemini_provider: Optional[Any] = None
    ):
        self.recommendation_repo = recommendation_repo
        self.unified_product_repo = unified_product_repo
        self.data_quality_repo = data_quality_repo
        self.trend_repo = trend_repo
        self.anomaly_repo = anomaly_repo
        self.gemini_provider = gemini_provider

    async def analyze_product_recommendations(
        self,
        unified_product_id: str,
        user_id: Optional[str] = None,
        include_similar: bool = True,
        include_alternatives: bool = True,
        include_better_price: bool = True,
        include_cross_platform: bool = True,
        include_best_value: bool = True,
        limit_per_type: int = 5
    ) -> ProductRecommendationSummary:
        """
        Generates grounded recommendations for a specific unified product.
        """
        run_id = f"run_rec_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # 1. Fetch Target Product
        target = None
        if hasattr(self.unified_product_repo, "get_unified_product"):
            target = self.unified_product_repo.get_unified_product(unified_product_id)
        if not target and hasattr(self.unified_product_repo, "get_by_id"):
            target = self.unified_product_repo.get_by_id(unified_product_id)

        if not target:
            return ProductRecommendationSummary(
                unified_product_id=unified_product_id,
                canonical_name="Unknown Product",
                status="insufficient_data",
                confidence=0.0,
                freshness_status="insufficient_data",
                warnings=["Target unified product not found in repository"]
            )

        # 2. Fetch Catalog for Similarity & Alternatives
        catalog = self.unified_product_repo.list_unified_products(limit=200)

        # 3. Fetch Upstream Agent Signals
        dq_map: Dict[str, float] = {}
        trend_score_map: Dict[str, float] = {}
        trend_signals_map: Dict[str, List[str]] = {}
        anomaly_map: Dict[str, List[Dict[str, Any]]] = {}

        if self.trend_repo:
            all_signals = self.trend_repo.list_signals(status="active", limit=200)
            for s in all_signals:
                p_id = s.unified_product_id
                trend_score_map[p_id] = max(trend_score_map.get(p_id, 0.0), s.strength * 100.0)
                if p_id not in trend_signals_map:
                    trend_signals_map[p_id] = []
                trend_signals_map[p_id].append(s.signal_type)

        if self.anomaly_repo:
            all_anoms = self.anomaly_repo.list_anomalies(status="active", limit=200)
            for a in all_anoms:
                p_id = a.unified_product_id
                if p_id not in anomaly_map:
                    anomaly_map[p_id] = []
                anomaly_map[p_id].append(a.model_dump())

        # 4. Target Product Listings
        if hasattr(self.unified_product_repo, "list_listings_for_product"):
            listings = self.unified_product_repo.list_listings_for_product(unified_product_id)
        elif hasattr(self.unified_product_repo, "list_platform_listings"):
            listings = self.unified_product_repo.list_platform_listings(unified_product_id)
        else:
            listings = []

        # 5. Check Target Quality Gate
        target_dq = dq_map.get(unified_product_id, target.completeness_score * 100.0)
        target_anoms = anomaly_map.get(unified_product_id, [])

        breakdown, overall_score, overall_conf = RecommendationScoringEngine.calculate_score(
            candidate_product=target,
            data_quality_score=target_dq,
            trend_score=trend_score_map.get(unified_product_id, 50.0),
            active_anomalies=target_anoms,
            recommendation_type="best_value"
        )

        all_generated_recs: List[ProductRecommendation] = []

        # A. Similar Products
        if include_similar:
            sims = RecommendationGenerators.generate_similar_products(
                target_product=target,
                catalog=catalog,
                data_quality_map=dq_map,
                trend_score_map=trend_score_map,
                anomaly_map=anomaly_map,
                limit=limit_per_type
            )
            all_generated_recs.extend(sims)

        # B. Alternative Products
        if include_alternatives:
            alts = RecommendationGenerators.generate_alternative_products(
                target_product=target,
                catalog=catalog,
                data_quality_map=dq_map,
                trend_score_map=trend_score_map,
                anomaly_map=anomaly_map,
                limit=limit_per_type
            )
            all_generated_recs.extend(alts)

        # C. Better Price
        if include_better_price:
            bps = RecommendationGenerators.generate_better_price_recommendations(
                target_product=target,
                platform_listings=listings,
                data_quality_map=dq_map,
                anomaly_map=anomaly_map
            )
            all_generated_recs.extend(bps)

        # D. Cross Platform
        if include_cross_platform:
            xps = RecommendationGenerators.generate_cross_platform_recommendations(
                target_product=target,
                platform_listings=listings
            )
            all_generated_recs.extend(xps)

        # E. Best Value
        if include_best_value:
            bvs = RecommendationGenerators.generate_best_value_recommendations(
                catalog=catalog,
                data_quality_map=dq_map,
                trend_score_map=trend_score_map,
                anomaly_map=anomaly_map,
                limit=limit_per_type
            )
            all_generated_recs.extend(bvs)

        # 6. Save Recommendations and Audits
        saved_recs: List[ProductRecommendation] = []
        for r in all_generated_recs:
            saved = self.recommendation_repo.save_recommendation(r)
            saved_recs.append(saved)

            # Record audit
            self.recommendation_repo.record_audit(RecommendationAudit(
                id=f"raud_{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                recommendation_id=saved.id,
                product_id=saved.unified_product_id,
                decision="generated",
                score=saved.score,
                confidence=saved.confidence,
                evidence=saved.evidence,
                source_agents=saved.source_agents,
                llm_used=False,
                created_at=now
            ))

            # If confidence is borderline, queue into candidate review
            if saved.confidence < 0.75 or len(saved.warnings) > 0:
                self.recommendation_repo.create_candidate(RecommendationCandidate(
                    id=f"rcand_{uuid.uuid4().hex[:12]}",
                    unified_product_id=saved.unified_product_id,
                    target_product_id=saved.target_product_id,
                    candidate_type=saved.recommendation_type,
                    composite_score=saved.score,
                    confidence=saved.confidence,
                    status="pending",
                    reasons=saved.reasons,
                    evidence=saved.evidence,
                    source_agents=saved.source_agents,
                    metadata={"run_id": run_id, "warnings": saved.warnings},
                    created_at=now,
                    updated_at=now
                ))

            # Record Memory Pattern
            if saved.category:
                RecommendationMemoryManager.record_recommendation_pattern(
                    self.recommendation_repo, saved, saved.category, trigger_run_id=run_id
                )

        status_label = "ready"
        if breakdown.eligibility_status == "quality_gated":
            status_label = "quality_gated"
        elif breakdown.eligibility_status == "anomaly_blocked":
            status_label = "anomaly_blocked"

        return ProductRecommendationSummary(
            unified_product_id=unified_product_id,
            canonical_name=target.canonical_name,
            brand=target.brand,
            category=target.category or "Unknown",
            platforms=target.platforms or [],
            recommendation_score=overall_score,
            status=status_label,
            confidence=overall_conf,
            freshness_status="fresh",
            recommendations=saved_recs,
            score_breakdown=breakdown,
            warnings=breakdown.eligibility_status != "eligible" and [f"Target product {breakdown.eligibility_status}"] or [],
            last_generated_at=now
        )

    async def generate_catalog_recommendations(
        self,
        recommendation_type: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        min_score: float = 50.0,
        limit: int = 20
    ) -> List[ProductRecommendation]:
        """
        Generates catalog-wide recommendations for discovery feeds or personalized user recommendations.
        """
        catalog = self.unified_product_repo.list_unified_products(limit=200)
        if not catalog:
            return []

        # Upstream signals
        trend_score_map: Dict[str, float] = {}
        trend_signals_map: Dict[str, List[str]] = {}
        anomaly_map: Dict[str, List[Dict[str, Any]]] = {}

        if self.trend_repo:
            all_signals = self.trend_repo.list_signals(status="active", limit=200)
            for s in all_signals:
                p_id = s.unified_product_id
                trend_score_map[p_id] = max(trend_score_map.get(p_id, 0.0), s.strength * 100.0)
                if p_id not in trend_signals_map:
                    trend_signals_map[p_id] = []
                trend_signals_map[p_id].append(s.signal_type)

        if self.anomaly_repo:
            all_anoms = self.anomaly_repo.list_anomalies(status="active", limit=200)
            for a in all_anoms:
                p_id = a.unified_product_id
                if p_id not in anomaly_map:
                    anomaly_map[p_id] = []
                anomaly_map[p_id].append(a.model_dump())

        # Check user personalization
        preferred_categories = []
        if user_id:
            interactions = self.recommendation_repo.list_interactions(user_id=user_id, limit=50)
            if interactions:
                cat_counts: Dict[str, int] = {}
                for inter in interactions:
                    cat = inter.metadata.get("category")
                    if cat:
                        cat_counts[cat] = cat_counts.get(cat, 0) + 1
                preferred_categories = sorted(cat_counts.keys(), key=lambda k: cat_counts[k], reverse=True)

        generated: List[ProductRecommendation] = []

        # Category recommendations
        if category:
            generated.extend(RecommendationGenerators.generate_category_recommendations(
                category=category,
                catalog=catalog,
                trend_score_map=trend_score_map,
                limit=limit
            ))
        else:
            # Trending
            if not recommendation_type or recommendation_type == "trending_product":
                generated.extend(RecommendationGenerators.generate_trending_recommendations(
                    catalog=catalog,
                    trend_score_map=trend_score_map,
                    trend_signals_map=trend_signals_map,
                    anomaly_map=anomaly_map,
                    limit=limit
                ))

            # Best Value
            if not recommendation_type or recommendation_type == "best_value":
                generated.extend(RecommendationGenerators.generate_best_value_recommendations(
                    catalog=catalog,
                    trend_score_map=trend_score_map,
                    anomaly_map=anomaly_map,
                    limit=limit
                ))

            # High Quality
            if not recommendation_type or recommendation_type == "high_quality":
                generated.extend(RecommendationGenerators.generate_high_quality_recommendations(
                    catalog=catalog,
                    data_quality_map={},
                    anomaly_map=anomaly_map,
                    limit=limit
                ))

            # Opportunities
            if not recommendation_type or recommendation_type == "opportunity":
                generated.extend(RecommendationGenerators.generate_opportunity_recommendations(
                    catalog=catalog,
                    trend_score_map=trend_score_map,
                    limit=limit
                ))

            # Rising
            if not recommendation_type or recommendation_type == "rising_product":
                generated.extend(RecommendationGenerators.generate_rising_product_recommendations(
                    catalog=catalog,
                    trend_score_map=trend_score_map,
                    limit=limit
                ))

        # Personalization affinity boost
        if preferred_categories:
            for r in generated:
                if r.category and r.category in preferred_categories:
                    r.score = min(100.0, r.score + 5.0)

        # Batch save
        saved = self.recommendation_repo.batch_save_recommendations(generated)
        filtered = [r for r in saved if r.score >= min_score]
        filtered.sort(key=lambda x: x.score, reverse=True)
        return filtered[:limit]

    def record_user_interaction(
        self,
        interaction: RecommendationInteraction
    ) -> RecommendationInteraction:
        """
        Records a real user interaction event and updates memory if applicable.
        """
        saved = self.recommendation_repo.record_interaction(interaction)
        if interaction.user_id and interaction.metadata.get("category"):
            RecommendationMemoryManager.record_user_preference_memory(
                rec_repo=self.recommendation_repo,
                user_id=interaction.user_id,
                preferred_category=interaction.metadata["category"],
                interaction_type=interaction.interaction_type
            )
        return saved
