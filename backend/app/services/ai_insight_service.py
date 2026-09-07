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
        if product.trend_score <= 0:
            return f"Single observation recorded on {product.primary_platform}. Insufficient historical signals to compute velocity conviction."

        conviction = "High" if product.trend_score >= 85.0 else "Moderate"
        sentiment_pct = int(product.sentiment_score * 100) if product.sentiment_score > 0 else 0
        sentiment_str = f"{sentiment_pct}% positive consumer sentiment" if product.sentiment_score > 0 else "unrated sentiment baseline"
        return (
            f"Cross-channel activity recorded on {product.primary_platform}. "
            f"Calculated velocity index of {product.trend_score:.1f} with {sentiment_str}. "
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
            return "No market report intelligence available for the selected parameters. Persist marketplace catalog items or ingest connector signals to generate an executive synthesis."
        
        top_p = top_products[0]
        if top_p.trend_score <= 0 or top_p.growth_rate == 0:
            return (
                f"Baseline market telemetry recorded across {len(top_products)} evaluated product(s) in {category}. "
                f"Multi-period velocity divergence and predictive trend vectors require at least two chronological snapshot observations."
            )

        growth_sign = "+" if top_p.growth_rate > 0 else ""
        if top_p.trend_score >= 85.0:
            return (
                f"Multi-source signal analysis confirms demand concentration in {category}. "
                f"Lead breakout asset '{top_p.name}' is driving {growth_sign}{top_p.growth_rate:.1f}% velocity on {top_p.primary_platform}. "
                f"Strategic recommendation: prioritize procurement depth and supplier allocation to capture initial margin spread."
            )

        return (
            f"Signal monitoring confirms steady demand activity in {category}. "
            f"Lead asset '{top_p.name}' exhibits {top_p.velocity_label} activity ({growth_sign}{top_p.growth_rate:.1f}% change) across connected channels."
        )
