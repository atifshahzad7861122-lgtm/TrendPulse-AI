import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.models.domain import ProductSignature, LLMUsageRecord
from backend.app.services.llm.provider import LLMProvider, LLMResponse
from backend.app.repositories.base import LLMUsageRepository

logger = logging.getLogger("trendpulse.agents.entity_matching.llm")

class EntityMatchingLLMResolver:
    """
    Selective Gemini LLM resolver for ambiguous product entity resolution (confidence 0.75 - 0.84).
    Enforces strict JSON schema output, response validation, caching, and token cost telemetry.
    """

    PROMPT_VERSION = "v1.0"

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        usage_repo: Optional[LLMUsageRepository] = None
    ):
        self.provider = provider
        self.usage_repo = usage_repo
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_cache_key(self, sig1: ProductSignature, sig2: ProductSignature) -> str:
        h1, h2 = sorted([sig1.signature_hash, sig2.signature_hash])
        return f"{h1}:{h2}:{self.PROMPT_VERSION}"

    def resolve_ambiguity(
        self,
        sig1: ProductSignature,
        sig2: ProductSignature,
        product_a_title: str,
        product_b_title: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], float, str, bool]:
        """
        Executes Gemini reasoning to resolve whether Product A and Product B represent the same real-world product.
        Returns: (parsed_data, confidence, match_method, success)
        """
        if not self.provider:
            return {}, 0.0, "llm_unavailable", False

        cache_key = self._get_cache_key(sig1, sig2)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return cached, cached.get("confidence", 0.85), "llm_gemini_cached", True

        system_instruction = (
            "You are an expert product entity resolution and deduplication AI for an e-commerce intelligence platform.\n"
            "Your task is to determine whether two product listings from different marketplaces represent the exact same real-world product.\n"
            "RULES:\n"
            "1. 'same_product': Identical base model, specifications, and brand.\n"
            "2. 'variant': Same base product, but differing by storage capacity, RAM, color, or size.\n"
            "3. 'related': Same brand/line, but different model tiers or generations (e.g. Pro vs standard, XM4 vs XM5).\n"
            "4. 'different': Completely distinct items.\n"
            "5. 'uncertain': Insufficient data to decide.\n\n"
            "OUTPUT FORMAT (STRICT JSON ONLY, NO MARKDOWN, NO EXPLANATION TEXT OUTSIDE JSON):\n"
            "{\n"
            '  "decision": "same_product" | "variant" | "related" | "different" | "uncertain",\n'
            '  "confidence": <float between 0.0 and 1.0>,\n'
            '  "reasons": ["<reason 1>", "<reason 2>"],\n'
            '  "conflicts": ["<conflict 1>"],\n'
            '  "variant_attributes": {"<key>": "<value>"}\n'
            "}"
        )

        user_content = json.dumps({
            "product_a": {
                "title": product_a_title,
                "brand": sig1.brand,
                "model": sig1.model,
                "category": sig1.category,
                "product_type": sig1.product_type,
                "attributes": sig1.key_attributes,
                "identifiers": sig1.identifiers
            },
            "product_b": {
                "title": product_b_title,
                "brand": sig2.brand,
                "model": sig2.model,
                "category": sig2.category,
                "product_type": sig2.product_type,
                "attributes": sig2.key_attributes,
                "identifiers": sig2.identifiers
            }
        }, indent=2)

        start_time = time.time()
        try:
            resp: LLMResponse = self.provider.generate(
                prompt=user_content,
                system_instruction=system_instruction,
                temperature=0.0
            )
            latency_ms = (time.time() - start_time) * 1000

            # Record telemetry
            if self.usage_repo and resp:
                rec = LLMUsageRecord(
                    id=f"llm_use_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    workspace_id=workspace_id,
                    provider="gemini",
                    model=getattr(resp, "model_name", "gemini-1.5-flash"),
                    request_type="entity_matching",
                    prompt_version=self.PROMPT_VERSION,
                    input_tokens=resp.prompt_tokens,
                    output_tokens=resp.completion_tokens,
                    total_tokens=resp.total_tokens,
                    estimated_cost=getattr(resp, "estimated_cost", getattr(resp, "cost", 0.0)),
                    latency_ms=latency_ms,
                    status="success"
                )
                self.usage_repo.record_usage(rec)

            raw_text = resp.content.strip()
            # Clean possible markdown block
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            confidence = float(parsed.get("confidence", 0.85))

            self._cache[cache_key] = parsed
            return parsed, confidence, "llm_gemini_resolver", True

        except Exception as e:
            logger.warning(f"Gemini entity matching resolution failed: {e}")
            if self.usage_repo:
                rec = LLMUsageRecord(
                    id=f"llm_err_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    workspace_id=workspace_id,
                    provider="gemini",
                    model="gemini-1.5-flash",
                    request_type="entity_matching",
                    prompt_version=self.PROMPT_VERSION,
                    status="failed",
                    error_code=500
                )
                self.usage_repo.record_usage(rec)
            return {}, 0.0, "llm_error_fallback", False
