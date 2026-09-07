import uuid
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.models.domain import (
    AIAgent, AIAgentRun, AIAgentMemory, AIAgentMemoryEvent,
    ProductTaxonomyAssignment, ProductTaxonomyCandidate
)
from backend.app.repositories.base import TaxonomyRepository, LLMUsageRepository
from backend.app.services.llm.provider import LLMProvider
from backend.app.services.agents.categorization.rules_engine import DeterministicTaxonomyEngine
from backend.app.services.agents.categorization.memory_manager import CategorizationMemoryManager
from backend.app.services.agents.categorization.llm_resolver import CategorizationLLMResolver

logger = logging.getLogger("trendpulse.agents.categorization")

class ProductCategorizationAgent:
    """
    Agent 2: Product Categorization & Taxonomy Agent for TrendPulse AI.
    Classifies validated marketplace products into the standardized TrendPulse taxonomy hierarchy.
    Enforces deterministic brand rules, exact marketplace maps, memory pattern reuse,
    selective Gemini semantic resolution, candidate creation for ambiguous products,
    and memory auditing.
    """

    AGENT_ID = "agent_categorization"

    def __init__(
        self,
        repository: TaxonomyRepository,
        llm_provider: Optional[LLMProvider] = None,
        llm_usage_repo: Optional[LLMUsageRepository] = None,
        high_confidence_threshold: float = 0.90,
        med_confidence_threshold: float = 0.75,
        review_threshold: float = 0.50
    ):
        self.repository = repository
        self.rules_engine = DeterministicTaxonomyEngine()
        self.memory_manager = CategorizationMemoryManager(repository=repository)
        self.llm_resolver = CategorizationLLMResolver(
            provider=llm_provider,
            usage_repo=llm_usage_repo
        )
        self.high_threshold = high_confidence_threshold
        self.med_threshold = med_confidence_threshold
        self.review_threshold = review_threshold

    def _compute_payload_hash(self, title: str, brand: Optional[str], original_category: Optional[str]) -> str:
        s = f"{title.strip().lower()}:{str(brand).strip().lower()}:{str(original_category).strip().lower()}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def classify_product(
        self,
        payload: Dict[str, Any],
        unified_product_id: Optional[str] = None,
        allow_llm: bool = True,
        force_reclassify: bool = False,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None,
        save_result: bool = True
    ) -> ProductTaxonomyAssignment:
        """
        Classifies a product into the standardized TrendPulse taxonomy hierarchy.
        """
        u_id = unified_product_id or str(payload.get("unified_product_id") or payload.get("id") or f"unf_{uuid.uuid4().hex[:14]}")
        p_id = str(payload.get("product_id") or payload.get("platform_product_id") or u_id)
        title = str(payload.get("product_name") or payload.get("title") or payload.get("name") or "").strip()
        description = str(payload.get("description") or "")
        orig_cat = payload.get("original_category") or payload.get("category")
        raw_brand = payload.get("brand") or payload.get("vendor")
        tags = payload.get("tags") or []
        input_attrs = payload.get("attributes") or {}
        platform = str(payload.get("platform") or "unknown").lower()
        provider = str(payload.get("source_provider") or payload.get("provider") or "direct").lower()
        now = datetime.now(timezone.utc)

        # 0. Check Cache / Existing Assignment
        if not force_reclassify and self.repository:
            existing = self.repository.get_assignment_by_unified_product_id(u_id)
            if existing:
                # If cached assignment exists and confidence is high, return it
                if existing.confidence >= self.med_threshold:
                    return existing

        # 1. Deterministic Rule Evaluation
        det_result, det_confidence, det_method = self.rules_engine.classify_deterministic(
            product_name=title,
            description=description,
            original_category=orig_cat,
            brand_raw=raw_brand,
            tags=tags
        )

        extracted_brand = self.rules_engine.extract_brand(title, raw_brand)
        extracted_attrs = self.rules_engine.extract_attributes(f"{title} {description}")
        combined_attrs = {**extracted_attrs, **input_attrs}

        final_category = det_result.get("category") if det_result else None
        final_subcategory = det_result.get("subcategory") if det_result else None
        final_product_type = det_result.get("product_type") if det_result else None
        final_path = det_result.get("taxonomy_path") if det_result else None
        final_confidence = det_confidence
        final_method = det_method
        used_llm = False

        # 2. Check Persistent Agent Memory if deterministic confidence is moderate or unknown
        if final_confidence < self.med_threshold and orig_cat:
            mem_mapping = self.memory_manager.get_learned_mapping("marketplace_category_mapping", orig_cat)
            if mem_mapping:
                final_category = mem_mapping.get("category")
                final_subcategory = mem_mapping.get("subcategory", "Unknown")
                final_product_type = mem_mapping.get("product_type", "Unknown")
                final_path = mem_mapping.get("taxonomy_path", [final_category, final_subcategory, final_product_type])
                final_confidence = 0.90
                final_method = "memory"

        # 3. Selective Gemini LLM Resolution
        needs_llm = (final_confidence < self.med_threshold or not final_category or final_category == "Unknown")
        if allow_llm and needs_llm and title and self.llm_resolver.provider is not None:
            llm_res = self.llm_resolver.resolve_classification(
                product_name=title,
                description=description,
                brand_raw=raw_brand or extracted_brand,
                original_category=orig_cat,
                tags=tags,
                attributes=combined_attrs,
                platform=platform,
                source_provider=provider,
                user_id=user_id,
                workspace_id=workspace_id
            )
            if llm_res:
                used_llm = True
                final_category = llm_res.get("category") or final_category or "Unknown"
                final_subcategory = llm_res.get("subcategory") or final_subcategory or "Unknown"
                final_product_type = llm_res.get("product_type") or final_product_type or "Unknown"
                final_path = llm_res.get("taxonomy_path") or [final_category, final_subcategory, final_product_type]
                final_confidence = float(llm_res.get("confidence", 0.85))
                final_method = "llm"
                if llm_res.get("brand"):
                    extracted_brand = llm_res.get("brand")
                if llm_res.get("attributes"):
                    combined_attrs.update(llm_res.get("attributes"))

        # 4. Fallback Handling & Candidate Creation for Insufficient Data
        if not final_category or final_confidence < self.review_threshold or not title:
            final_category = "Unknown"
            final_subcategory = "Unknown"
            final_product_type = "Unknown"
            final_path = ["Unknown", "Unknown", "Unknown"]
            final_confidence = min(final_confidence, 0.45)
            final_method = "unknown"
            needs_review = True

            if save_result and self.repository:
                self.repository.create_candidate(ProductTaxonomyCandidate(
                    id=f"ptc_{uuid.uuid4().hex[:12]}",
                    product_id=p_id,
                    unified_product_id=u_id,
                    candidate_category=det_result.get("category", "Unknown") if det_result else "Unknown",
                    candidate_subcategory=det_result.get("subcategory", "Unknown") if det_result else "Unknown",
                    candidate_product_type=det_result.get("product_type", "Unknown") if det_result else "Unknown",
                    confidence=final_confidence,
                    reason=f"Classification confidence {final_confidence:.2f} below threshold {self.review_threshold}",
                    created_at=now
                ))
        else:
            needs_review = (final_confidence < self.med_threshold)

        # Ensure taxonomy path is a clean list of non-empty strings
        if not final_path or not isinstance(final_path, list) or len(final_path) == 0:
            final_path = [final_category, final_subcategory, final_product_type]

        assignment = ProductTaxonomyAssignment(
            id=f"pta_{uuid.uuid4().hex[:14]}",
            unified_product_id=u_id,
            category=final_category,
            subcategory=final_subcategory,
            product_type=final_product_type,
            taxonomy_path=final_path,
            brand=extracted_brand,
            attributes=combined_attrs,
            confidence=round(final_confidence, 2),
            classification_method=final_method,
            needs_review=needs_review,
            agent_id=self.AGENT_ID,
            agent_run_id=run_id,
            created_at=now,
            updated_at=now
        )

        # 5. Persist Assignment & Update Learned Memory
        if save_result and self.repository:
            self.repository.upsert_assignment(assignment)
            self.memory_manager.record_classification_memory(
                assignment=assignment,
                original_category=orig_cat,
                brand=extracted_brand,
                run_id=run_id
            )

        return assignment
