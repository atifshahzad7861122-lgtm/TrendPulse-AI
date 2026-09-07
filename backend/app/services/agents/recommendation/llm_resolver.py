import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.models.domain import ProductRecommendation, UnifiedProduct


class RecommendationLLMInterpretationOutput(BaseModel):
    summary: str = Field(..., description="Human-readable synthesis explaining why this recommendation is valuable.")
    reasons: List[str] = Field(default_factory=list, description="Top evidence-grounded reasons supporting the recommendation.")
    confidence: float = Field(default=0.85, description="LLM confidence in interpretation from 0.0 to 1.0.")
    warnings: List[str] = Field(default_factory=list, description="Any detected cautions or potential discrepancies.")


class RecommendationLLMResolver:
    """
    Selective Gemini LLM resolver for Agent 06.
    Enriches ambiguous product comparisons, multi-signal evidence, and generates
    human-readable rationales.
    Never calculates the final numerical recommendation score.
    """

    @classmethod
    def should_invoke_llm(
        cls,
        recommendations: List[ProductRecommendation],
        is_complex_comparison: bool = False
    ) -> bool:
        """
        Determines if Gemini should be selectively invoked:
        - When comparing multiple diverse alternatives (3+ items)
        - When ambiguous similarity or cross-platform differences exist
        - When explicitly requested for complex narrative synthesis
        """
        if is_complex_comparison and len(recommendations) >= 2:
            return True
        # If any recommendation has warnings or conflicting multi-agent signals
        if any(len(r.warnings) > 0 for r in recommendations):
            return True
        return False

    @classmethod
    async def interpret_recommendation_with_gemini(
        cls,
        target_product: UnifiedProduct,
        recommendation: ProductRecommendation,
        gemini_provider: Optional[Any] = None
    ) -> RecommendationLLMInterpretationOutput:
        """
        Calls Gemini to generate a rich narrative explanation with structured JSON validation.
        Falls back safely to deterministic signals on errors or timeouts.
        """
        # Default fallback output
        fallback_output = RecommendationLLMInterpretationOutput(
            summary=f"Recommended based on {recommendation.recommendation_type.replace('_', ' ')} with score {recommendation.score:.0f}/100.",
            reasons=recommendation.reasons or [
                f"Observed data in category {target_product.category or 'General'}",
                f"Verified marketplace intelligence score: {recommendation.score:.0f}/100"
            ],
            confidence=recommendation.confidence,
            warnings=recommendation.warnings or []
        )

        if not gemini_provider:
            return fallback_output

        prompt = f"""You are the Recommendation & Product Intelligence Agent for TrendPulse AI.
Analyze the following verified marketplace product recommendation and produce an evidence-grounded interpretation in JSON format.

TARGET PRODUCT:
- Title: {target_product.canonical_name}
- Category: {target_product.category}
- Brand: {target_product.brand or 'N/A'}
- Price: {target_product.primary_currency} {target_product.average_price or target_product.lowest_price}
- Rating: {target_product.avg_rating} ({target_product.total_reviews} reviews)

RECOMMENDATION:
- Type: {recommendation.recommendation_type}
- Score: {recommendation.score}/100
- Initial Reasons: {', '.join(recommendation.reasons)}
- Evidence: {json.dumps(recommendation.evidence)}
- Warnings: {', '.join(recommendation.warnings)}

OUTPUT REQUIREMENTS:
Output ONLY valid JSON matching this schema:
{{
  "summary": "<Concise 1-2 sentence evidence-grounded explanation>",
  "reasons": ["<Specific grounded point 1>", "<Specific grounded point 2>"],
  "confidence": <Float between 0.0 and 1.0>,
  "warnings": ["<Any caveats or empty list>"]
}}
Do NOT fabricate unavailable metrics or user purchase data."""

        try:
            raw_response = await gemini_provider.generate_text(
                prompt=prompt,
                temperature=0.2,
                max_tokens=400
            )

            if not raw_response or not isinstance(raw_response, str):
                return fallback_output

            clean_json = raw_response.strip()
            if "```json" in clean_json:
                match = re.search(r"```json\s*(.*?)\s*```", clean_json, re.DOTALL)
                if match:
                    clean_json = match.group(1).strip()
            elif "```" in clean_json:
                match = re.search(r"```\s*(.*?)\s*```", clean_json, re.DOTALL)
                if match:
                    clean_json = match.group(1).strip()

            parsed = json.loads(clean_json)
            return RecommendationLLMInterpretationOutput(**parsed)

        except Exception:
            # Safe deterministic fallback
            return fallback_output
