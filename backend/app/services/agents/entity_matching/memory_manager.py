import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

from backend.app.models.domain import AIAgentMemory, AIAgentMemoryEvent, ProductSignature
from backend.app.repositories.base import TaxonomyRepository

logger = logging.getLogger("trendpulse.agents.entity_matching.memory")

class EntityMatchingMemoryManager:
    """
    Manages persistent memory patterns, human verification feedback,
    and audit trails for Agent 3 (Product Entity Matching & Deduplication).
    """

    AGENT_ID = "agent_entity_matching"

    def __init__(self, repository: TaxonomyRepository):
        self.repository = repository

    def _make_pair_key(self, sig1_hash: str, sig2_hash: str) -> str:
        h1, h2 = sorted([sig1_hash, sig2_hash])
        return f"{h1}:{h2}"

    def get_learned_pair(self, sig1_hash: str, sig2_hash: str) -> Optional[AIAgentMemory]:
        if not self.repository:
            return None
        pair_key = self._make_pair_key(sig1_hash, sig2_hash)
        # Check confirmed match
        mem = self.repository.get_memory(self.AGENT_ID, "confirmed_match_signature", pair_key)
        if mem:
            return mem
        # Check confirmed no-match
        return self.repository.get_memory(self.AGENT_ID, "confirmed_no_match_signature", pair_key)

    def record_confirmed_match(
        self,
        sig1: ProductSignature,
        sig2: ProductSignature,
        decision: str = "EXACT_MATCH",
        confidence: float = 0.98,
        reason: str = "Human confirmed match",
        run_id: Optional[str] = None
    ) -> AIAgentMemory:
        """
        Stores or reinforces a confirmed match signature pair in persistent memory.
        """
        if not self.repository:
            return None

        pair_key = self._make_pair_key(sig1.signature_hash, sig2.signature_hash)
        now = datetime.now(timezone.utc)
        existing = self.repository.get_memory(self.AGENT_ID, "confirmed_match_signature", pair_key)

        if existing:
            new_count = existing.occurrence_count + 1
            updated_mem = existing.model_copy(update={
                "confidence_score": min(1.0, existing.confidence_score + 0.02),
                "occurrence_count": new_count,
                "last_observed_at": now,
                "updated_at": now
            })
            saved = self.repository.upsert_memory(updated_mem)
            event = AIAgentMemoryEvent(
                id=f"evt_{uuid.uuid4().hex[:12]}",
                agent_id=self.AGENT_ID,
                memory_id=saved.id,
                event_type="reinforced",
                old_value={"occurrence_count": existing.occurrence_count},
                new_value={"occurrence_count": new_count, "decision": decision},
                reason=reason,
                trigger_run_id=run_id,
                created_at=now
            )
            self.repository.record_memory_event(event)
            return saved
        else:
            mem_id = f"mem_mat_{uuid.uuid4().hex[:12]}"
            new_mem = AIAgentMemory(
                id=mem_id,
                agent_id=self.AGENT_ID,
                memory_type="confirmed_match_signature",
                memory_key=pair_key,
                memory_value={
                    "brand": sig1.brand or sig2.brand,
                    "model": sig1.model or sig2.model,
                    "decision": decision,
                    "reason": reason
                },
                confidence_score=confidence,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            )
            saved = self.repository.upsert_memory(new_mem)
            event = AIAgentMemoryEvent(
                id=f"evt_{uuid.uuid4().hex[:12]}",
                agent_id=self.AGENT_ID,
                memory_id=mem_id,
                event_type="created",
                new_value={"decision": decision, "reason": reason},
                reason="Created new entity matching memory record",
                trigger_run_id=run_id,
                created_at=now
            )
            self.repository.record_memory_event(event)
            return saved

    def record_confirmed_no_match(
        self,
        sig1: ProductSignature,
        sig2: ProductSignature,
        reason: str = "Human confirmed no match",
        run_id: Optional[str] = None
    ) -> AIAgentMemory:
        """
        Stores a confirmed false-positive / no-match pair to prevent future auto-merges.
        """
        if not self.repository:
            return None

        pair_key = self._make_pair_key(sig1.signature_hash, sig2.signature_hash)
        now = datetime.now(timezone.utc)
        existing = self.repository.get_memory(self.AGENT_ID, "confirmed_no_match_signature", pair_key)

        if existing:
            new_count = existing.occurrence_count + 1
            updated = existing.model_copy(update={
                "occurrence_count": new_count,
                "last_observed_at": now,
                "updated_at": now
            })
            saved = self.repository.upsert_memory(updated)
            event = AIAgentMemoryEvent(
                id=f"evt_{uuid.uuid4().hex[:12]}",
                agent_id=self.AGENT_ID,
                memory_id=saved.id,
                event_type="reinforced",
                old_value={"occurrence_count": existing.occurrence_count},
                new_value={"occurrence_count": new_count},
                reason=reason,
                trigger_run_id=run_id,
                created_at=now
            )
            self.repository.record_memory_event(event)
            return saved
        else:
            mem_id = f"mem_nom_{uuid.uuid4().hex[:12]}"
            new_mem = AIAgentMemory(
                id=mem_id,
                agent_id=self.AGENT_ID,
                memory_type="confirmed_no_match_signature",
                memory_key=pair_key,
                memory_value={
                    "brand_a": sig1.brand,
                    "brand_b": sig2.brand,
                    "model_a": sig1.model,
                    "model_b": sig2.model,
                    "reason": reason
                },
                confidence_score=1.0,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            )
            saved = self.repository.upsert_memory(new_mem)
            event = AIAgentMemoryEvent(
                id=f"evt_{uuid.uuid4().hex[:12]}",
                agent_id=self.AGENT_ID,
                memory_id=mem_id,
                event_type="created",
                new_value={"reason": reason},
                reason="Recorded confirmed false positive pair in memory",
                trigger_run_id=run_id,
                created_at=now
            )
            self.repository.record_memory_event(event)
            return saved

    def list_memories(self, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        if not self.repository:
            return []
        return self.repository.list_memory(self.AGENT_ID, memory_type=memory_type)
