import json
import time
from typing import Dict, Any, Optional

from backend.app.services.llm.provider import (
    LLMProvider, LLMRequest, LLMResponse, LLMAuthError, LLMRateLimitError, LLMTimeoutError
)

class MockLLMProvider(LLMProvider):
    """
    Offline, deterministic mock provider for testing, sandbox environments,
    and local validation without incurring API costs.
    """

    def __init__(
        self,
        api_key: Optional[str] = "mock-key",
        model: Optional[str] = "mock-model-v1",
        base_url: Optional[str] = None,
        simulate_error: Optional[str] = None
    ):
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self.simulate_error = simulate_error

    def generate(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()

        if self.simulate_error == "auth":
            raise LLMAuthError("Mock authentication failure: invalid mock API key.")
        elif self.simulate_error == "rate_limit":
            raise LLMRateLimitError("Mock rate limit exceeded (HTTP 429).")
        elif self.simulate_error == "timeout":
            raise LLMTimeoutError("Mock execution timed out after 30s.")

        prompt_lower = request.prompt.lower()

        # Generate structured payload based on request content
        if "category_analysis" in prompt_lower or "market_overview" in prompt_lower:
            payload = {
                "category": "Electronics",
                "market_overview": "The market demonstrates solid demand with verified listings across Daraz and Shopify.",
                "demand_state": "High Steady Demand",
                "price_range_summary": "Prices range from PKR 2,500 to PKR 15,000 depending on variant specifications.",
                "growth_drivers": [
                    "High consumer interest in wireless convenience",
                    "Expansion of multi-channel seller distribution"
                ],
                "threats_and_challenges": [
                    "Price sensitivity across competitive budget segments",
                    "Rapid product iteration cycles"
                ],
                "strategic_advice": [
                    "Maintain competitive pricing near median market range",
                    "Emphasize verified seller warranty in marketing"
                ]
            }
        elif "market_comparison" in prompt_lower or "price_arbitrage" in prompt_lower:
            payload = {
                "cross_platform_overview": "Cross-platform analysis reveals significant price variance between direct-to-consumer Shopify stores and marketplace listings.",
                "price_arbitrage_analysis": "Daraz listings average PKR 3,200 while international Shopify stores price at approximately $29.99.",
                "seller_and_vendor_landscape": "Multiple verified sellers present with consistent positive rating profiles above 4.5 stars.",
                "platform_comparison_breakdown": [
                    {
                        "platform": "Daraz",
                        "competitive_strength": "Local stock, fast nationwide shipping, cash on delivery.",
                        "risk_factor": "Intense price competition among reseller tiers."
                    },
                    {
                        "platform": "Shopify",
                        "competitive_strength": "Direct brand experience and official bundling.",
                        "risk_factor": "Currency conversion friction for non-USD buyers."
                    }
                ],
                "recommendations": [
                    "Monitor competitor pricing on Daraz weekly for promotional drops.",
                    "Optimize listing imagery to match official Shopify brand aesthetics."
                ]
            }
        elif "trend_analysis" in prompt_lower or "trend_trajectory" in prompt_lower:
            payload = {
                "trend_trajectory": "Rising Momentum",
                "velocity_assessment": "Listing volume and customer engagement metrics indicate sustained upward velocity.",
                "volatility_risk": "Low",
                "historical_price_action": "Stable pricing pattern observed over recent snapshots with minimal discounting.",
                "predictive_outlook_30d": "Demand projected to remain buoyant over the next 30 days based on consistent review volume."
            }
        elif "executive_summary" in prompt_lower or "product_summary" in prompt_lower:
            payload = {
                "executive_summary": "Top-performing consumer product verified across multiple marketplace channels with strong customer satisfaction.",
                "key_takeaways": [
                    "Consistently high ratings across verified customer reviews",
                    "Competitive price point in the mid-tier category",
                    "High data completeness score across marketplace feeds"
                ],
                "target_audience": "Tech-savvy consumers seeking reliable performance at accessible pricing.",
                "competitive_edge": "Strong brand recognition and reliable stock availability across major platforms."
            }
        else:
            # Default Product Analysis
            payload = {
                "summary": "Verified canonical product demonstrating strong multi-platform presence and positive customer sentiment.",
                "category": "Consumer Tech",
                "confidence_score": 0.94,
                "key_signals": [
                    "Multi-platform presence confirmed on Daraz and Shopify",
                    "Average rating exceeds 4.5 stars across platforms",
                    "High data quality and completeness score"
                ],
                "opportunities": [
                    "Cross-channel promotional synergy between marketplace and DTC store",
                    "Bundle packaging to improve average order value"
                ],
                "risks": [
                    "Potential price erosion if competitors offer aggressive promotional discounts",
                    "Stockout risk during high-velocity holiday events"
                ],
                "recommendations": [
                    "Maintain automated price monitoring alerts",
                    "Benchmark listing content against top-rated competitors"
                ],
                "pricing_analysis": {
                    "price_tier": "Mid-Market",
                    "arbitrage_potential": "Moderate",
                    "discount_depth": "Healthy"
                }
            }

        content_str = json.dumps(payload, indent=2)
        latency = (time.perf_counter() - start_time) * 1000.0

        in_toks = len(request.prompt.split()) * 2
        out_toks = len(content_str.split()) * 2
        cost = self.calculate_cost(self.model, in_toks, out_toks)

        return LLMResponse(
            content=content_str,
            parsed_json=payload,
            input_tokens=in_toks,
            output_tokens=out_toks,
            total_tokens=in_toks + out_toks,
            estimated_cost=cost,
            latency_ms=round(latency, 2),
            model=self.model,
            provider="mock",
            raw_response={"mock": True, "status": "ok"}
        )
