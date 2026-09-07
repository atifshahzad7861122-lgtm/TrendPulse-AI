import logging
from typing import Dict, Any, Optional

from backend.app.services.llm.provider import (
    LLMProvider, LLMRequest, LLMException
)

logger = logging.getLogger("trendpulse.data_quality.llm_resolver")

DATA_QUALITY_RESOLVER_SYSTEM_PROMPT = """You are the TrendPulse AI Data Quality & Validation Resolver.
Your job is to resolve ambiguous marketplace metadata strictly based on the provided product attributes.

Rules:
1. Never invent or assume facts not present in the input.
2. If brand is unidentifiable or generic, return null for extracted_brand.
3. If category cannot be confidently mapped from title, return null for mapped_category.
4. Output STRICT JSON format only.

Output JSON Schema:
{
  "extracted_brand": string or null,
  "mapped_category": string or null,
  "is_spam": boolean,
  "is_duplicate": boolean,
  "quality_assessment": string,
  "confidence": float (0.0 to 1.0)
}"""

class DataQualityLLMResolver:
    """
    Selective LLM Ambiguity Resolver using the configured LLMProvider (Gemini, etc.).
    Invoked only for ambiguous brand extraction, numeric/vague taxonomy mapping,
    spam title classification, or conflicting candidate attributes.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider

    def resolve_ambiguity(
        self,
        product_title: str,
        platform: str,
        category_raw: Optional[str] = None,
        brand_raw: Optional[str] = None,
        price: Optional[float] = None,
        currency: Optional[str] = None,
        context_hints: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executes selective LLM ambiguity resolution for difficult records.
        """
        if not self.provider:
            return None

        prompt = f"""Evaluate this marketplace product for ambiguity resolution:
- Platform: {platform}
- Title: {product_title}
- Source Brand: {brand_raw or 'None'}
- Source Category: {category_raw or 'None'}
- Price: {price} {currency or ''}
- Context Hints: {context_hints or {}}

Resolve:
1. Extract true manufacturer/brand name if clearly evident in title (otherwise null).
2. Map to a clean, human-readable e-commerce category name if identifiable (otherwise null).
3. Determine if title is spam / abusive keyword stuffing (true/false).
4. Provide a brief 1-sentence quality assessment and confidence score.
"""

        req = LLMRequest(
            prompt=prompt,
            system_prompt=DATA_QUALITY_RESOLVER_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=512,
            json_mode=True,
            timeout=2.5
        )

        try:
            resp = self.provider.generate(req)
            if resp.parsed_json and isinstance(resp.parsed_json, dict):
                return {
                    "extracted_brand": resp.parsed_json.get("extracted_brand"),
                    "mapped_category": resp.parsed_json.get("mapped_category"),
                    "is_spam": bool(resp.parsed_json.get("is_spam", False)),
                    "is_duplicate": bool(resp.parsed_json.get("is_duplicate", False)),
                    "quality_assessment": resp.parsed_json.get("quality_assessment", "LLM validation complete."),
                    "confidence": float(resp.parsed_json.get("confidence", 0.9)),
                    "tokens_used": resp.total_tokens,
                    "provider": resp.provider,
                    "model": resp.model
                }
            elif resp.content:
                return {
                    "extracted_brand": None,
                    "mapped_category": None,
                    "is_spam": False,
                    "is_duplicate": False,
                    "quality_assessment": resp.content[:150],
                    "confidence": 0.8,
                    "tokens_used": resp.total_tokens,
                    "provider": resp.provider,
                    "model": resp.model
                }
        except LLMException as e:
            logger.warning(f"DataQualityLLMResolver encountered error (falling back gracefully): {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error in DataQualityLLMResolver: {e}")
            return None

        return None
