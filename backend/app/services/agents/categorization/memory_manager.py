import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.models.domain import AIAgentMemory, AIAgentMemoryEvent, ProductTaxonomyAssignment
from backend.app.repositories.base import TaxonomyRepository

class CategorizationMemoryManager:
    """
    Manages persistent memory and auditing for Agent 2: Product Categorization & Taxonomy Agent.
    Stores and reuses learned category mappings, brand associations, and reliable classification patterns.
    """

    AGENT_ID = "agent_categorization"

    def __init__(self, repository: TaxonomyRepository):
        self.repository = repository

    def get_learned_mapping(self, memory_type: str, memory_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a learned memory pattern if confidence is high and memory exists.
        """
        key_norm = memory_key.strip().lower()
        mem = self.repository.get_memory(self.AGENT_ID, memory_type, key_norm)
        if mem and mem.confidence_score >= 0.85:
            return mem.memory_value
        return None

    def record_classification_memory(
        self,
        assignment: ProductTaxonomyAssignment,
        original_category: Optional[str] = None,
        brand: Optional[str] = None,
        run_id: Optional[str] = None
    ):
        """
        Records or reinforces persistent memory based on high-confidence classification results.
        """
        now = datetime.now(timezone.utc)

        # Only learn from confident, non-review classifications
        if assignment.needs_review or assignment.confidence < 0.85:
            # If ambiguous, record ambiguous pattern for tracking
            if assignment.needs_review and original_category:
                self._record_ambiguous_memory(original_category, assignment, run_id, now)
            return

        # 1. Learn Marketplace Category Mapping
        if original_category and original_category.strip() and original_category.lower() != "unknown":
            cat_key = original_category.strip().lower()
            existing = self.repository.get_memory(self.AGENT_ID, "marketplace_category_mapping", cat_key)
            new_val = {
                "category": assignment.category,
                "subcategory": assignment.subcategory,
                "product_type": assignment.product_type,
                "taxonomy_path": assignment.taxonomy_path,
                "source": assignment.classification_method,
                "last_verified_at": now.isoformat()
            }

            if existing:
                old_val = existing.memory_value
                updated = existing.model_copy(update={
                    "memory_value": new_val,
                    "occurrence_count": existing.occurrence_count + 1,
                    "confidence_score": min(1.0, existing.confidence_score + 0.02),
                    "last_observed_at": now,
                    "updated_at": now
                })
                self.repository.upsert_memory(updated)
                self.repository.record_memory_event(AIAgentMemoryEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    agent_id=self.AGENT_ID,
                    memory_id=existing.id,
                    event_type="reinforced",
                    old_value=old_val,
                    new_value=new_val,
                    reason=f"Reinforced marketplace category mapping '{cat_key}' -> {assignment.category}",
                    trigger_run_id=run_id,
                    created_at=now
                ))
            else:
                mem_id = f"mem_{uuid.uuid4().hex[:12]}"
                new_mem = AIAgentMemory(
                    id=mem_id,
                    agent_id=self.AGENT_ID,
                    memory_type="marketplace_category_mapping",
                    memory_key=cat_key,
                    memory_value=new_val,
                    confidence_score=assignment.confidence,
                    occurrence_count=1,
                    last_observed_at=now,
                    created_at=now,
                    updated_at=now
                )
                self.repository.upsert_memory(new_mem)
                self.repository.record_memory_event(AIAgentMemoryEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    agent_id=self.AGENT_ID,
                    memory_id=mem_id,
                    event_type="created",
                    old_value=None,
                    new_value=new_val,
                    reason=f"Learned new marketplace category mapping '{cat_key}' -> {assignment.category}",
                    trigger_run_id=run_id,
                    created_at=now
                ))

        # 2. Learn Brand -> Category Association
        if brand and brand.strip() and brand.lower() not in ["generic", "no brand", "none", "unknown"]:
            brand_key = brand.strip().lower()
            existing_b = self.repository.get_memory(self.AGENT_ID, "brand_category_pattern", brand_key)
            b_val = {
                "brand": brand,
                "category": assignment.category,
                "subcategory": assignment.subcategory,
                "taxonomy_path": assignment.taxonomy_path,
                "last_verified_at": now.isoformat()
            }

            if existing_b:
                old_b = existing_b.memory_value
                updated_b = existing_b.model_copy(update={
                    "memory_value": b_val,
                    "occurrence_count": existing_b.occurrence_count + 1,
                    "confidence_score": min(1.0, existing_b.confidence_score + 0.01),
                    "last_observed_at": now,
                    "updated_at": now
                })
                self.repository.upsert_memory(updated_b)
            else:
                mem_id = f"mem_{uuid.uuid4().hex[:12]}"
                new_b_mem = AIAgentMemory(
                    id=mem_id,
                    agent_id=self.AGENT_ID,
                    memory_type="brand_category_pattern",
                    memory_key=brand_key,
                    memory_value=b_val,
                    confidence_score=assignment.confidence,
                    occurrence_count=1,
                    last_observed_at=now,
                    created_at=now,
                    updated_at=now
                )
                self.repository.upsert_memory(new_b_mem)

    def _record_ambiguous_memory(
        self,
        raw_cat: str,
        assignment: ProductTaxonomyAssignment,
        run_id: Optional[str],
        now: datetime
    ):
        """
        Records an ambiguous category pattern to assist in batch offline reviews.
        """
        cat_key = raw_cat.strip().lower()
        existing = self.repository.get_memory(self.AGENT_ID, "ambiguous_classification_pattern", cat_key)
        val = {
            "raw_category": raw_cat,
            "assigned_category": assignment.category,
            "confidence": assignment.confidence,
            "last_observed_at": now.isoformat()
        }

        if existing:
            updated = existing.model_copy(update={
                "occurrence_count": existing.occurrence_count + 1,
                "last_observed_at": now,
                "updated_at": now
            })
            self.repository.upsert_memory(updated)
        else:
            mem_id = f"mem_{uuid.uuid4().hex[:12]}"
            new_mem = AIAgentMemory(
                id=mem_id,
                agent_id=self.AGENT_ID,
                memory_type="ambiguous_classification_pattern",
                memory_key=cat_key,
                memory_value=val,
                confidence_score=0.4,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            )
            self.repository.upsert_memory(new_mem)
