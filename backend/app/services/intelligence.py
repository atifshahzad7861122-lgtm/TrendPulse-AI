from typing import List, Optional, Dict, Any
from backend.app.models.domain import Product
from backend.app.repositories.base import ProductRepository
from backend.app.domain.scoring import TrendScoringEngine
from backend.app.domain.demand import DemandSignalEngine
from backend.app.domain.viral import ViralPotentialEngine
from backend.app.domain.prediction import TrendPredictionService
from backend.app.domain.classification import CategoryClassificationService

class ProductIntelligenceEngine:
    """
    Coordinates analytical calculations for products, including dynamic score
    computation, explainable component breakdowns, demand classification,
    viral potential, and statistical trajectory forecasting.
    """

    def __init__(self, product_repo: ProductRepository):
        self.products = product_repo

    def get_product_intelligence(self, product_id: str) -> Optional[Product]:
        product = self.products.get_by_id(product_id)
        if not product:
            return None
        return self._enrich_product(product)

    def list_products(
        self,
        category: Optional[str] = "all",
        platform: Optional[str] = "all",
        search: Optional[str] = None,
        sort_by: Optional[str] = "trend_score"
    ) -> List[Product]:
        items = self.products.list(category=category, platform=platform, search=search, sort_by=sort_by)
        return [self._enrich_product(p) for p in items]

    def compare_products(self, product_ids: List[str]) -> List[Product]:
        all_prods = {p.id: self._enrich_product(p) for p in self.products.list()}
        return [all_prods[pid] for pid in product_ids if pid in all_prods]

    def _enrich_product(self, product: Product) -> Product:
        """
        Dynamically calculates analytical attributes and explainable breakdowns for the product.
        """
        hist_scores = [h.get("score", 50.0) for h in product.historical_scores] if product.historical_scores else []
        
        # 1. Explainable Trend Scoring
        scoring_detail = TrendScoringEngine.calculate_explainable_trend_score(
            growth_rate=product.growth_rate,
            volume=product.volume,
            sentiment_score=product.sentiment_score,
            platform_count=len(product.platforms),
            historical_trend=hist_scores
        )
        product.trend_score = scoring_detail.trend_score
        product.velocity_label = scoring_detail.velocity_label

        # 2. Calibrated Demand Analysis
        demand_detail = DemandSignalEngine.evaluate_demand_detailed(
            volume=product.volume,
            sentiment_score=product.sentiment_score,
            growth_rate=product.growth_rate
        )

        # 3. Calibrated Viral Potential Analysis
        viral_detail = ViralPotentialEngine.evaluate_virality_detailed(
            growth_rate=product.growth_rate,
            platforms=product.platforms,
            platform_shares=product.platform_shares or {},
            velocity_label=product.velocity_label
        )

        # 4. Statistical Trajectory Prediction (insufficient history safe)
        prediction_result = TrendPredictionService.predict_product_trajectory(product)

        # 5. Hierarchical Category Classification
        classification_result = CategoryClassificationService.classify(
            text=f"{product.name} {product.category}",
            current_category=product.category
        )

        # 6. Attach structured metadata
        if not hasattr(product, "raw_data") or not isinstance(product.raw_data, dict):
            product.raw_data = {}

        product.raw_data.update({
            "scoring_detail": scoring_detail.to_dict(),
            "demand_detail": demand_detail.to_dict(),
            "viral_detail": viral_detail.to_dict(),
            "prediction": prediction_result.to_dict(),
            "classification": classification_result.to_dict(),
            "intelligence_calibrated": True,
            "version_metadata": {
                "scoring_version": TrendScoringEngine.SCORING_VERSION,
                "demand_version": DemandSignalEngine.ENGINE_VERSION,
                "viral_version": ViralPotentialEngine.ENGINE_VERSION,
                "prediction_version": TrendPredictionService.PREDICTION_VERSION,
                "classification_version": CategoryClassificationService.CLASSIFICATION_VERSION
            }
        })

        return product
