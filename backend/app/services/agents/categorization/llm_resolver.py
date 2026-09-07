import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.app.services.llm.provider import LLMProvider, LLMRequest, LLMException
from backend.app.repositories.base import LLMUsageRepository
from backend.app.models.domain import LLMUsageRecord

logger = logging.getLogger("trendpulse.categorization.llm_resolver")

CATEGORIZATION_SYSTEM_PROMPT = """You are the TrendPulse AI Product Categorization & Taxonomy Agent (Agent 2).
Your task is to classify marketplace products into the standardized TrendPulse taxonomy hierarchy.

Supported Top-Level Categories:
- Electronics
- Fashion
- Beauty & Personal Care
- Home & Living
- Health & Wellness
- Sports & Fitness
- Toys & Collectibles
- Automotive
- Groceries & Food
- Baby & Kids
- Books & Media
- Pet Supplies
- Jewelry & Accessories
- Tools & Hardware
- Office & Stationery
- Industrial & Business
- Other
- Unknown

Rules:
1. Never invent or hallucinate facts not supported by the product title, brand, or attributes.
2. If the product data is completely insufficient or gibberish, return category "Unknown", subcategory "Unknown", product_type "Unknown", confidence < 0.50, and needs_review true.
3. Extract clean manufacturer / brand name if identifiable.
4. Extract structured attributes (e.g. driver_size, storage, ram, battery_capacity, material, color, size, gender, connectivity).
5. Output STRICT JSON only conforming to the schema below.

JSON Schema:
{
  "category": string,
  "subcategory": string,
  "product_type": string,
  "taxonomy_path": [string],
  "brand": string or null,
  "attributes": object,
  "confidence": float (0.0 to 1.0),
  "classification_method": "llm",
  "needs_review": boolean
}"""

class LLMCategorizationOutput(BaseModel):
    category: str = "Unknown"
    subcategory: str = "Unknown"
    product_type: str = "Unknown"
    taxonomy_path: List[str] = Field(default_factory=lambda: ["Unknown"])
    brand: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    classification_method: str = "llm"
    needs_review: bool = False

class CategorizationLLMResolver:
    """
    Selective Gemini LLM Ambiguity Resolver for Agent 2.
    Invoked strictly for semantic classification, ambiguous categories,
    taxonomy conflicts, and deep attribute extraction.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        usage_repo: Optional[LLMUsageRepository] = None
    ):
        self.provider = provider
        self.usage_repo = usage_repo

    def resolve_classification(
        self,
        product_name: str,
        description: str = "",
        brand_raw: Optional[str] = None,
        original_category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        platform: Optional[str] = None,
        source_provider: Optional[str] = None,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executes selective LLM classification with sanitized context and token tracking.
        """
        if not self.provider:
            return None

        # Build sanitized prompt payload
        prompt = f"""Classify this marketplace product into the TrendPulse taxonomy:
- Product Title: {product_name}
- Raw Category: {original_category or 'None'}
- Declared Brand: {brand_raw or 'None'}
- Platform: {platform or 'Unknown'}
- Provider: {source_provider or 'direct'}
- Tags: {', '.join(tags) if tags else 'None'}
- Preliminary Attributes: {attributes or {}}
- Description Snippet: {description[:300] if description else 'None'}

Determine the primary Category, Subcategory, Product Type, Taxonomy Path, Brand, and structured Attributes.
"""

        req = LLMRequest(
            prompt=prompt,
            system_prompt=CATEGORIZATION_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=600,
            json_mode=True,
            timeout=2.0
        )

        start_time = time.time()
        try:
            resp = self.provider.generate(req)
            latency_ms = (time.time() - start_time) * 1000.0

            # Record token usage
            if self.usage_repo:
                try:
                    self.usage_repo.record_usage(LLMUsageRecord(
                        id=f"use_{uuid.uuid4().hex[:14]}",
                        user_id=user_id,
                        workspace_id=workspace_id,
                        provider=resp.provider,
                        model=resp.model,
                        request_type="product_categorization",
                        prompt_version="v2",
                        input_tokens=resp.input_tokens,
                        output_tokens=resp.output_tokens,
                        total_tokens=resp.total_tokens,
                        estimated_cost=getattr(resp, "estimated_cost", getattr(resp, "cost", 0.0)),
                        latency_ms=latency_ms,

                        status="success",
                        created_at=datetime.now(timezone.utc)
                    ))
                except Exception as ex:
                    logger.warning(f"Failed to record LLM usage: {ex}")

            if resp.parsed_json and isinstance(resp.parsed_json, dict):
                # Validate output via Pydantic
                parsed = LLMCategorizationOutput(**resp.parsed_json)
                return {
                    "category": parsed.category,
                    "subcategory": parsed.subcategory,
                    "product_type": parsed.product_type,
                    "taxonomy_path": parsed.taxonomy_path if parsed.taxonomy_path else [parsed.category, parsed.subcategory, parsed.product_type],
                    "brand": parsed.brand,
                    "attributes": parsed.attributes,
                    "confidence": parsed.confidence,
                    "classification_method": "llm",
                    "needs_review": parsed.needs_review or parsed.confidence < 0.50,
                    "tokens_used": resp.total_tokens,
                    "model": resp.model
                }

            return None

        except Exception as e:
            logger.error(f"Agent 2 LLM resolution failed: {e}")
            if self.usage_repo:
                try:
                    self.usage_repo.record_usage(LLMUsageRecord(
                        id=f"use_{uuid.uuid4().hex[:14]}",
                        user_id=user_id,
                        workspace_id=workspace_id,
                        provider="gemini",
                        model="gemini-2.0-flash",
                        request_type="product_categorization",
                        prompt_version="v2",
                        input_tokens=0,
                        output_tokens=0,
                        total_tokens=0,
                        estimated_cost=0.0,
                        latency_ms=(time.time() - start_time) * 1000.0,
                        status="failed",
                        created_at=datetime.now(timezone.utc)
                    ))
                except Exception:
                    pass
            return None
