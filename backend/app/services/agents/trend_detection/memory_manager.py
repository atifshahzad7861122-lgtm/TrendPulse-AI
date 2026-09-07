import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from backend.app.models.domain import AIAgentMemory, AIAgentMemoryEvent
from backend.app.repositories.base import TaxonomyRepository

class TrendDetectionMemoryManager:
    """
    Persistent memory manager for Agent 4 (Trend Detection & Signal Discovery).
    Learns reliable signal patterns, category thresholds, and suppresses false positives.
    """

    AGENT_ID = "agent_trend_detection"

    def __init__(self, repository: TaxonomyRepository):
        self.repository = repository

    def get_learned_threshold(self, category: str, platform: str) -> Optional[AIAgentMemory]:
        """Retrieves learned sensitivity thresholds for a given category and platform."""
        key = f"{category.strip().lower()}:{platform.strip().lower()}"
        return self.repository.get_memory(self.AGENT_ID, "trend_threshold_calibration", key)

    def record_breakout_pattern(
        self,
        category: str,
        platform: str,
        signal_types: List[str],
        confidence: float,
        run_id: Optional[str] = None
    ) -> Optional[AIAgentMemory]:
        """
        Learns and reinforces multi-signal breakout patterns across categories and platforms.
        """
        key = f"{category.strip().lower()}:{platform.strip().lower()}:{'+'.join(sorted(signal_types))}"
        now = datetime.now(timezone.utc)
        existing = self.repository.get_memory(self.AGENT_ID, "breakout_signal_pattern", key)

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
                id=f"evt_trd_{uuid.uuid4().hex[:12]}",
                agent_id=self.AGENT_ID,
                memory_id=saved.id,
                event_type="reinforced",
                old_value={"occurrence_count": existing.occurrence_count},
                new_value={"occurrence_count": new_count, "confidence": saved.confidence_score},
                reason=f"Breakout pattern observed for {category} on {platform}",
                trigger_run_id=run_id,
                created_at=now
            )
            self.repository.record_memory_event(event)
            return saved
        else:
            mem_id = f"mem_trd_{uuid.uuid4().hex[:12]}"
            new_mem = AIAgentMemory(
                id=mem_id,
                agent_id=self.AGENT_ID,
                memory_type="breakout_signal_pattern",
                memory_key=key,
                memory_value={
                    "category": category,
                    "platform": platform,
                    "signal_types": signal_types
                },
                confidence_score=confidence,
                occurrence_count=1,
                source="signal_discovery_engine",
                last_observed_at=now,
                created_at=now,
                updated_at=now
            )
            saved = self.repository.upsert_memory(new_mem)
            event = AIAgentMemoryEvent(
                id=f"evt_trd_{uuid.uuid4().hex[:12]}",
                agent_id=self.AGENT_ID,
                memory_id=saved.id,
                event_type="created",
                old_value={},
                new_value=new_mem.memory_value,
                reason=f"Initial breakout signal pattern registered for {category}",
                trigger_run_id=run_id,
                created_at=now
            )
            self.repository.record_memory_event(event)
            return saved

    def list_memories(self, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        return self.repository.list_memory(self.AGENT_ID, memory_type)

    def get_events(self, limit: int = 50) -> List[AIAgentMemoryEvent]:
        return self.repository.get_memory_events(self.AGENT_ID, limit=limit)
