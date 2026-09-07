import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.models.domain import AIAgentMemory, AIAgentMemoryEvent, AnomalyDetection

class AnomalyDetectionMemoryManager:
    """
    Persistent memory manager for Agent 05: Anomaly Detection.
    Stores and reinforces learned normal ranges, false-positive suppressions,
    and provider error patterns.
    """

    AGENT_ID = "agent_anomaly_detection"

    @classmethod
    def record_anomaly_pattern(
        cls,
        memory_store: Any,
        anomaly: AnomalyDetection,
        category: Optional[str] = None
    ) -> AIAgentMemory:
        """
        Records or reinforces an observed anomaly pattern in persistent agent memory.
        """
        memory_key = f"anomaly_pattern:{anomaly.anomaly_type}:{category or 'global'}"
        now = datetime.now(timezone.utc)
        existing = None
        if hasattr(memory_store, "get_memory"):
            existing = memory_store.get_memory(cls.AGENT_ID, "anomaly_threshold_calibration", memory_key)
        elif hasattr(memory_store, "get_memory_by_key"):
            existing = memory_store.get_memory_by_key(cls.AGENT_ID, memory_key)

        if existing:
            new_count = existing.occurrence_count + 1
            new_val = dict(existing.memory_value)
            new_val["occurrence_count"] = new_count
            new_val["last_observed_severity"] = anomaly.severity
            new_val["last_deviation_percent"] = anomaly.deviation_percent

            updated = existing.model_copy(update={
                "confidence_score": min(0.99, existing.confidence_score + 0.02),
                "occurrence_count": new_count,
                "memory_value": new_val,
                "last_observed_at": now,
                "updated_at": now
            })
            if hasattr(memory_store, "upsert_memory"):
                memory_store.upsert_memory(updated)

            # Record event
            if hasattr(memory_store, "record_memory_event"):
                event = AIAgentMemoryEvent(
                    id=f"aevt_{uuid.uuid4().hex[:12]}",
                    agent_id=cls.AGENT_ID,
                    memory_id=existing.id,
                    event_type="reinforced",
                    old_value={"occurrence_count": existing.occurrence_count},
                    new_value={"occurrence_count": new_count, "confidence": updated.confidence_score},
                    reason=f"Reinforced {anomaly.anomaly_type} pattern for category '{category or 'global'}'",
                    created_at=now
                )
                memory_store.record_memory_event(event)

            return updated
        else:
            mem_id = f"amem_{uuid.uuid4().hex[:12]}"
            mem_val = {
                "anomaly_type": anomaly.anomaly_type,
                "category": category or "global",
                "occurrence_count": 1,
                "initial_severity": anomaly.severity,
                "initial_deviation_percent": anomaly.deviation_percent,
                "platforms": anomaly.platforms
            }
            new_mem = AIAgentMemory(
                id=mem_id,
                agent_id=cls.AGENT_ID,
                memory_type="anomaly_threshold_calibration",
                memory_key=memory_key,
                memory_value=mem_val,
                confidence_score=0.85,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            )
            if hasattr(memory_store, "upsert_memory"):
                memory_store.upsert_memory(new_mem)

            if hasattr(memory_store, "record_memory_event"):
                event = AIAgentMemoryEvent(
                    id=f"aevt_{uuid.uuid4().hex[:12]}",
                    agent_id=cls.AGENT_ID,
                    memory_id=mem_id,
                    event_type="created",
                    old_value={},
                    new_value=mem_val,
                    reason=f"Created {anomaly.anomaly_type} pattern memory for '{category or 'global'}'",
                    created_at=now
                )
                memory_store.record_memory_event(event)

            return new_mem

    @classmethod
    def record_false_positive_suppression(
        cls,
        memory_store: Any,
        anomaly_type: str,
        category: Optional[str] = None,
        reason: str = "Operator marked as normal promotion"
    ) -> AIAgentMemory:
        """
        Records a false-positive pattern to suppress false alarms in future analyses.
        """
        memory_key = f"false_positive_suppression:{anomaly_type}:{category or 'global'}"
        now = datetime.now(timezone.utc)
        mem_id = f"amem_fp_{uuid.uuid4().hex[:12]}"
        mem_val = {
            "anomaly_type": anomaly_type,
            "category": category or "global",
            "suppression_reason": reason
        }

        new_mem = AIAgentMemory(
            id=mem_id,
            agent_id=cls.AGENT_ID,
            memory_type="false_positive_pattern",
            memory_key=memory_key,
            memory_value=mem_val,
            confidence_score=0.92,
            occurrence_count=1,
            last_observed_at=now,
            created_at=now,
            updated_at=now
        )
        if hasattr(memory_store, "upsert_memory"):
            memory_store.upsert_memory(new_mem)

        if hasattr(memory_store, "record_memory_event"):
            event = AIAgentMemoryEvent(
                id=f"aevt_fp_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=mem_id,
                event_type="created",
                old_value={},
                new_value=mem_val,
                reason=reason,
                created_at=now
            )
            memory_store.record_memory_event(event)

        return new_mem

