import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.models.domain import MarketOpportunity, UnifiedProduct

logger = logging.getLogger(__name__)


class MarketOpportunityLLMOutput(BaseModel):
    summary: str = Field(..., description="High-level synthesis of the market opportunity")
    reasons: List[str] = Field(default_factory=list, description="Specific supporting evidence bullet points")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence in this interpretation")
    warnings: List[str] = Field(default_factory=list, description="Any risk or data quality warnings")


class MarketOpportunityLLMResolver:
    """
    Selective LLM Resolver for AI Agent 07 (Market Opportunity Intelligence Agent).
    Provides structured strategic synthesis for complex cross-platform gaps, competitive comparisons,
    or warning explanations while keeping scoring and eligibility 100% deterministic.
    """

    @classmethod
    def should_invoke_llm(
        cls,
        opportunities: List[MarketOpportunity],
        is_complex_strategy: bool = False
    ) -> bool:
        """
        Invokes LLM only when there are multiple opportunities with warnings, or complex multi-marketplace comparisons.
        """
        if is_complex_strategy:
            return True
        if any(len(o.warnings) > 0 for o in opportunities):
            return True
        if len(opportunities) >= 3:
            return True
        return False

    @classmethod
    async def interpret_opportunity_with_gemini(
        cls,
        target_product: Optional[UnifiedProduct],
        opportunity: MarketOpportunity,
        gemini_provider: Optional[Any] = None
    ) -> MarketOpportunityLLMOutput:
        """
        Uses Gemini to generate explainable opportunity analysis with strict Pydantic JSON validation and deterministic fallbacks.
        """
        # Deterministic default fallback
        fallback = MarketOpportunityLLMOutput(
            summary=f"Opportunity {opportunity.opportunity_type.replace('_', ' ').title()} identified based on verified marketplace observations.",
            reasons=opportunity.reasons if opportunity.reasons else [f"Verified score of {opportunity.score:.1f}/100 in {opportunity.category or 'General'}."],
            confidence=opportunity.confidence,
            warnings=opportunity.warnings
        )

        if not gemini_provider:
            return fallback

        prompt = f"""
You are the AI Market Opportunity Analyst for TrendPulse AI.
Analyze the following verified marketplace data and provide a concise, factual explanation for the detected opportunity.
Do not invent sales figures, revenue, customer demand, or unobserved metrics.

Opportunity Type: {opportunity.opportunity_type}
Product ID: {opportunity.unified_product_id or 'Category-Level'}
Category: {opportunity.category or 'N/A'}
Current Platforms: {', '.join(opportunity.current_platforms) if opportunity.current_platforms else 'Single Platform'}
Missing Platforms: {', '.join(opportunity.missing_observed_platforms) if opportunity.missing_observed_platforms else 'None'}
Score: {opportunity.score}/100
Confidence: {opportunity.confidence}
Evidence: {json.dumps(opportunity.evidence)}
Existing Reasons: {json.dumps(opportunity.reasons)}
Existing Warnings: {json.dumps(opportunity.warnings)}

Respond ONLY with a valid JSON object matching this schema:
{{
  "summary": "Concise summary of the opportunity grounded only in the facts above",
  "reasons": ["Factual reason 1", "Factual reason 2"],
  "confidence": {opportunity.confidence},
  "warnings": []
}}
"""

        try:
            raw_response = await gemini_provider.generate_text(prompt)
            clean_text = raw_response.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            parsed = json.loads(clean_text)
            validated = MarketOpportunityLLMOutput(**parsed)
            return validated
        except Exception as err:
            logger.warning("Gemini opportunity interpretation failed, using deterministic fallback: %s", err)
            return fallback
