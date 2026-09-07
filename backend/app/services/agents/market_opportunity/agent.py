import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, MarketOpportunity,
    MarketOpportunityCandidate, MarketOpportunityAudit, MarketOpportunityScoreBreakdown,
    MarketOpportunitySummary, AgentMarketOpportunityStats
)
from backend.app.repositories.base import (
    MarketOpportunityRepository, UnifiedProductRepository, DataQualityRepository,
    TaxonomyRepository, TrendDetectionRepository, AnomalyDetectionRepository,
    RecommendationRepository
)
from backend.app.services.agents.market_opportunity.scoring_engine import MarketOpportunityScoringEngine
from backend.app.services.agents.market_opportunity.detectors import MarketOpportunityDetectors
from backend.app.services.agents.market_opportunity.llm_resolver import MarketOpportunityLLMResolver
from backend.app.services.agents.market_opportunity.memory_manager import MarketOpportunityMemoryManager

logger = logging.getLogger(__name__)


class MarketOpportunityIntelligenceAgent:
    """
    AI Agent 07: Market Opportunity Intelligence Agent for TrendPulse AI.
    Integrates upstream signals from Agents 1–6 to identify evidence-grounded
    product gaps, price opportunities, category gaps, cross-platform expansion,
    availability issues, and high-potential launch opportunities without fabricating metrics.
    """

    AGENT_ID = "agent_market_opportunity_intelligence"

    def __init__(
        self,
        opp_repo: MarketOpportunityRepository,
        unified_product_repo: UnifiedProductRepository,
        data_quality_repo: Optional[DataQualityRepository] = None,
        taxonomy_repo: Optional[TaxonomyRepository] = None,
        trend_repo: Optional[TrendDetectionRepository] = None,
        anomaly_repo: Optional[AnomalyDetectionRepository] = None,
        recommendation_repo: Optional[RecommendationRepository] = None,
        gemini_provider: Optional[Any] = None
    ):
        self.opp_repo = opp_repo
        self.unified_product_repo = unified_product_repo
        self.data_quality_repo = data_quality_repo
        self.taxonomy_repo = taxonomy_repo
        self.trend_repo = trend_repo
        self.anomaly_repo = anomaly_repo
        self.recommendation_repo = recommendation_repo
        self.gemini_provider = gemini_provider

    async def analyze_product_opportunities(
        self,
        unified_product_id: str,
        is_complex_strategy: bool = False
    ) -> MarketOpportunitySummary:
        """
        Analyzes opportunities specifically for a given unified product.
        """
        run_id = f"run_opp_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # 1. Fetch Target Product
        target = None
        if hasattr(self.unified_product_repo, "get_unified_product"):
            target = self.unified_product_repo.get_unified_product(unified_product_id)
        if not target and hasattr(self.unified_product_repo, "get_by_id"):
            target = self.unified_product_repo.get_by_id(unified_product_id)

        if not target:
            return MarketOpportunitySummary(
                target_id=unified_product_id,
                target_type="product",
                name="Unknown Product",
                status="insufficient_data",
                confidence=0.0,
                data_freshness="insufficient_data",
                warnings=["Target product not found in repository"],
                analyzed_at=now
            )

        # 2. Fetch Listings
        listings: List[ProductPlatformListing] = []
        if hasattr(self.unified_product_repo, "list_listings_for_product"):
            listings = self.unified_product_repo.list_listings_for_product(unified_product_id)
        elif hasattr(self.unified_product_repo, "list_platform_listings"):
            listings = self.unified_product_repo.list_platform_listings(unified_product_id)

        # 3. Fetch Category Competitors
        catalog = self.unified_product_repo.list_unified_products(
            category=target.category if target.category else None,
            limit=50
        )

        # 4. Fetch Upstream Agent Signals
        dq_score = target.completeness_score * 100.0
        if self.data_quality_repo and hasattr(self.data_quality_repo, "list_validation_results"):
            val_res = self.data_quality_repo.list_validation_results(limit=100)
            target_vals = [
                v for v in val_res
                if getattr(v, "unified_product_id", None) == unified_product_id
                or any(getattr(l, "platform_product_id", None) == getattr(v, "platform_product_id", None) for l in listings)
            ]
            if target_vals:
                dq_score = sum(v.quality_score for v in target_vals) / len(target_vals)

        trend_score = 50.0
        trend_signals: List[str] = []
        if self.trend_repo:
            sigs = self.trend_repo.list_signals(limit=200)
            product_sigs = [s for s in sigs if s.unified_product_id == unified_product_id]
            if product_sigs:
                trend_score = max(s.strength * 100.0 for s in product_sigs)
                trend_signals = [s.signal_type for s in product_sigs]

        anomalies: List[Dict[str, Any]] = []
        if self.anomaly_repo:
            anom_list = self.anomaly_repo.list_anomalies(limit=200)
            product_anoms = [a for a in anom_list if a.unified_product_id == unified_product_id and a.status == "active"]
            anomalies = [a.model_dump() for a in product_anoms]

        # 5. Execute Detectors
        all_opps: List[MarketOpportunity] = []

        # Product Gap
        all_opps.extend(MarketOpportunityDetectors.detect_product_gaps(
            target_product=target,
            data_quality_score=dq_score,
            trend_score=trend_score,
            anomalies=anomalies
        ))

        # Price Opportunity
        all_opps.extend(MarketOpportunityDetectors.detect_price_opportunities(
            target_product=target,
            platform_listings=listings,
            data_quality_score=dq_score,
            anomalies=anomalies
        ))

        # Competitive Gap
        all_opps.extend(MarketOpportunityDetectors.detect_competitive_gaps(
            target_product=target,
            competitors=catalog,
            data_quality_score=dq_score
        ))

        # Cross Platform Gap
        all_opps.extend(MarketOpportunityDetectors.detect_cross_platform_gaps(
            target_product=target,
            data_quality_score=dq_score
        ))

        # Availability Opportunity
        all_opps.extend(MarketOpportunityDetectors.detect_availability_opportunities(
            target_product=target,
            platform_listings=listings
        ))

        # Rising Product
        all_opps.extend(MarketOpportunityDetectors.detect_rising_product(
            target_product=target,
            trend_score=trend_score,
            trend_signals=trend_signals
        ))

        # Marketplace Expansion
        all_opps.extend(MarketOpportunityDetectors.detect_marketplace_expansion(
            target_product=target,
            data_quality_score=dq_score
        ))

        # Product Launch Opportunity
        all_opps.extend(MarketOpportunityDetectors.detect_product_launch_opportunities(
            target_product=target,
            data_quality_score=dq_score,
            trend_score=trend_score,
            anomalies=anomalies
        ))

        # 6. Save Opportunities & Record Audits
        saved_opps: List[MarketOpportunity] = []
        for opp in all_opps:
            saved = self.opp_repo.save_opportunity(opp)
            saved_opps.append(saved)

            # Record audit
            self.opp_repo.record_audit(MarketOpportunityAudit(
                id=f"oaud_{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                opportunity_id=saved.id,
                rule_name=f"detect_{saved.opportunity_type}",
                decision="generated",
                score=saved.score,
                confidence=saved.confidence,
                evidence=saved.evidence,
                source_agent_ids=saved.source_agent_ids,
                llm_used=False,
                created_at=now
            ))

            # If confidence is borderline or warnings exist, queue into candidate review
            if saved.confidence < 0.75 or len(saved.warnings) > 0:
                self.opp_repo.create_candidate(MarketOpportunityCandidate(
                    id=f"ocand_{uuid.uuid4().hex[:12]}",
                    unified_product_id=saved.unified_product_id,
                    category=saved.category,
                    candidate_type=saved.opportunity_type,
                    composite_score=saved.score,
                    confidence=saved.confidence,
                    status="pending",
                    reasons=saved.reasons,
                    evidence=saved.evidence,
                    source_agent_ids=saved.source_agent_ids,
                    metadata={"run_id": run_id, "warnings": saved.warnings},
                    created_at=now,
                    updated_at=now
                ))

            # Record memory pattern
            MarketOpportunityMemoryManager.record_opportunity_pattern(
                self.opp_repo, saved, saved.category, trigger_run_id=run_id
            )

        # 7. Summary Scoring
        breakdown, overall_score, overall_conf = MarketOpportunityScoringEngine.calculate_score(
            candidate_product=target,
            category=target.category,
            data_quality_score=dq_score,
            trend_score=trend_score,
            cross_platform_count=target.platform_count,
            active_anomalies=anomalies,
            opportunity_type="product_gap"
        )

        # 8. Selective Gemini interpretation
        if self.gemini_provider and MarketOpportunityLLMResolver.should_invoke_llm(saved_opps, is_complex_strategy):
            for sopp in saved_opps:
                llm_out = await MarketOpportunityLLMResolver.interpret_opportunity_with_gemini(
                    target_product=target,
                    opportunity=sopp,
                    gemini_provider=self.gemini_provider
                )
                if llm_out.summary:
                    sopp.reasons = llm_out.reasons or sopp.reasons

        status_label = "ready"
        if dq_score < 70.0:
            status_label = "quality_gated"
        elif any(a.get("severity") == "critical" for a in anomalies):
            status_label = "anomaly_blocked"

        return MarketOpportunitySummary(
            target_id=target.unified_product_id,
            target_type="product",
            name=target.canonical_name,
            category=target.category,
            status=status_label,
            opportunity_score=overall_score,
            confidence=overall_conf,
            data_freshness="fresh",
            opportunities=saved_opps,
            score_breakdown=breakdown,
            warnings=[w for o in saved_opps for w in o.warnings],
            analyzed_at=now
        )

    async def analyze_category_opportunities(
        self,
        category: str
    ) -> MarketOpportunitySummary:
        """
        Analyzes macro opportunities for a whole category (rising category, quality gaps, underserved catalog).
        """
        run_id = f"run_opp_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        category_products = self.unified_product_repo.list_unified_products(category=category, limit=200)
        if not category_products:
            return MarketOpportunitySummary(
                target_id=f"cat:{category}",
                target_type="category",
                name=category,
                category=category,
                status="insufficient_data",
                confidence=0.0,
                data_freshness="insufficient_data",
                warnings=[f"No verified products found for category '{category}'"],
                analyzed_at=now
            )

        # Average trend score
        trend_score = 65.0
        if self.trend_repo:
            active_signals = self.trend_repo.list_signals(category=category, status="active", limit=50)
            if active_signals:
                trend_score = sum(s.strength * 100.0 for s in active_signals) / len(active_signals)

        dq_map = {p.unified_product_id: p.completeness_score * 100.0 for p in category_products}

        all_opps: List[MarketOpportunity] = []

        # Category Opportunity
        all_opps.extend(MarketOpportunityDetectors.detect_category_opportunities(
            category=category,
            category_products=category_products,
            category_trend_score=trend_score
        ))

        # Quality Gap
        all_opps.extend(MarketOpportunityDetectors.detect_quality_gaps(
            category=category,
            category_products=category_products,
            quality_score_map=dq_map
        ))

        # Rising Category
        all_opps.extend(MarketOpportunityDetectors.detect_rising_category(
            category=category,
            category_trend_score=trend_score
        ))

        # Underserved Category
        all_opps.extend(MarketOpportunityDetectors.detect_underserved_category(
            category=category,
            category_products=category_products,
            category_trend_score=trend_score
        ))

        # Save
        saved_opps: List[MarketOpportunity] = []
        for opp in all_opps:
            saved = self.opp_repo.save_opportunity(opp)
            saved_opps.append(saved)

            self.opp_repo.record_audit(MarketOpportunityAudit(
                id=f"oaud_{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                opportunity_id=saved.id,
                rule_name=f"detect_{saved.opportunity_type}",
                decision="generated",
                score=saved.score,
                confidence=saved.confidence,
                evidence=saved.evidence,
                source_agent_ids=saved.source_agent_ids,
                llm_used=False,
                created_at=now
            ))

            MarketOpportunityMemoryManager.record_opportunity_pattern(
                self.opp_repo, saved, category, trigger_run_id=run_id
            )

        breakdown, overall_score, overall_conf = MarketOpportunityScoringEngine.calculate_score(
            category=category,
            trend_score=trend_score,
            coverage_gap_ratio=0.3,
            cross_platform_count=2,
            opportunity_type="category_opportunity"
        )

        return MarketOpportunitySummary(
            target_id=f"cat:{category}",
            target_type="category",
            name=category,
            category=category,
            status="ready",
            opportunity_score=overall_score,
            confidence=overall_conf,
            data_freshness="fresh",
            opportunities=saved_opps,
            score_breakdown=breakdown,
            warnings=[w for o in saved_opps for w in o.warnings],
            analyzed_at=now
        )

    async def run_market_opportunity_pipeline(
        self,
        category: Optional[str] = None,
        min_score: float = 50.0,
        limit: int = 50
    ) -> List[MarketOpportunity]:
        """
        Executes full market opportunity discovery across unified catalog.
        """
        products = self.unified_product_repo.list_unified_products(category=category, limit=limit)
        results: List[MarketOpportunity] = []

        for p in products:
            summary = await self.analyze_product_opportunities(p.unified_product_id)
            for opp in summary.opportunities:
                if opp.score >= min_score:
                    results.append(opp)

        return results
