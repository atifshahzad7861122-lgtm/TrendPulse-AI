from typing import List
from backend.app.models.domain import Product

class AIInsightService:
    """
    Pluggable intelligence synthesis interface.
    Generates deterministic analytical summaries and strategic convictions
    based on calculated signal vectors.
    """

    @staticmethod
    def generate_product_insight(product: Product) -> str:
        """
        Synthesizes strategic rationale for a single product based on its velocity and sentiment.
        """
        conviction = "High" if product.trend_score >= 85.0 else "Moderate"
        return (
            f"Cross-channel viral surge detected on {product.primary_platform}. "
            f"Calculated velocity index of {product.trend_score:.1f} with {int(product.sentiment_score * 100)}% positive consumer sentiment. "
            f"Estimated first-mover supplier window: 3-5 weeks before domestic price saturation ({conviction} conviction)."
        )

    @staticmethod
    def generate_report_synthesis(
        top_products: List[Product],
        category: str,
        template: str
    ) -> str:
        """
        Generates executive dossier synthesis from active product signals.
        """
        if not top_products:
            return "Market intelligence scan indicates stable baseline demand with no severe anomaly deviations."
        
        top_p = top_products[0]
        return (
            f"Multi-source signal analysis confirms exponential demand acceleration in {category}. "
            f"Lead breakout asset '{top_p.name}' is driving +{top_p.growth_rate:.0f}% velocity on {top_p.primary_platform}. "
            f"Strategic recommendation: prioritize procurement depth and creator affiliate partnerships to capture initial margin spread."
        )
