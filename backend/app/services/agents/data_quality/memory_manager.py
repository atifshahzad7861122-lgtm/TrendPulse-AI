import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.app.models.domain import AIAgentMemory, AIAgentMemoryEvent, DataQualityValidationResult
from backend.app.repositories.base import DataQualityRepository

class DataQualityMemoryManager:
    """
    Manages persistent memory and event auditing for DataQualityAgent.
    Learns provider reliability profiles, frequently missing fields, and recurring data quality patterns.
    """

    AGENT_ID = "agent_data_quality"

    def __init__(self, repository: DataQualityRepository):
        self.repository = repository

    def record_validation_memory(self, result: DataQualityValidationResult, run_id: Optional[str] = None):
        """
        Updates persistent memory based on validation outcomes for a single item.
        """
        provider = (result.source_provider or "direct").lower()
        platform = (result.platform or "unknown").lower()
        now = datetime.now(timezone.utc)

        # 1. Update Missing Fields Pattern
        missing_fields = [iss.field for iss in result.issues + result.warnings if "missing" in iss.rule_name.lower()]
        if missing_fields:
            mem_key = f"missing_fields:{platform}:{provider}"
            existing = self.repository.get_memory(self.AGENT_ID, "missing_fields_pattern", mem_key)
            if existing:
                field_counts = existing.memory_value.get("field_counts", {})
                for f in missing_fields:
                    field_counts[f] = field_counts.get(f, 0) + 1
                new_val = {
                    "platform": platform,
                    "provider": provider,
                    "field_counts": field_counts,
                    "total_samples": existing.memory_value.get("total_samples", 1) + 1
                }
                old_val = existing.memory_value
                updated_mem = existing.model_copy(update={
                    "memory_value": new_val,
                    "occurrence_count": existing.occurrence_count + 1,
                    "last_observed_at": now
                })
                self.repository.upsert_memory(updated_mem)
                self.repository.record_memory_event(AIAgentMemoryEvent(
                    id=f"evt_{uuid.uuid4().hex[:12]}",
                    agent_id=self.AGENT_ID,
                    memory_id=existing.id,
                    event_type="reinforced",
                    old_value=old_val,
                    new_value=new_val,
                    reason=f"Recorded missing fields {missing_fields} for provider {provider}",
                    trigger_run_id=run_id,
                    created_at=now
                ))
            else:
                mem_id = f"mem_{uuid.uuid4().hex[:12]}"
                field_counts = {f: 1 for f in missing_fields}
                new_val = {
                    "platform": platform,
                    "provider": provider,
                    "field_counts": field_counts,
                    "total_samples": 1
                }
                new_mem = AIAgentMemory(
                    id=mem_id,
                    agent_id=self.AGENT_ID,
                    memory_type="missing_fields_pattern",
                    memory_key=mem_key,
                    memory_value=new_val,
                    confidence_score=0.9,
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
                    reason=f"Initial discovery of missing fields pattern for provider {provider}",
                    trigger_run_id=run_id,
                    created_at=now
                ))

        # 2. Update Provider Reliability Profile
        rel_key = f"reliability:{platform}:{provider}"
        existing_rel = self.repository.get_memory(self.AGENT_ID, "reliability_score", rel_key)
        is_valid = result.classification == "valid"
        is_warn = result.classification == "valid_with_warnings"
        is_rej = result.classification == "rejected"

        if existing_rel:
            v_count = existing_rel.memory_value.get("valid_count", 0) + (1 if is_valid else 0)
            w_count = existing_rel.memory_value.get("warning_count", 0) + (1 if is_warn else 0)
            r_count = existing_rel.memory_value.get("rejected_count", 0) + (1 if is_rej else 0)
            total = existing_rel.memory_value.get("total_evaluated", 0) + 1
            scores_sum = existing_rel.memory_value.get("scores_sum", 100.0) + result.overall_score
            avg_score = round(scores_sum / max(1, total), 1)

            new_val = {
                "platform": platform,
                "provider": provider,
                "total_evaluated": total,
                "valid_count": v_count,
                "warning_count": w_count,
                "rejected_count": r_count,
                "scores_sum": scores_sum,
                "average_score": avg_score,
                "reliability_index": round((v_count + 0.5 * w_count) / max(1, total), 2)
            }
            updated_mem = existing_rel.model_copy(update={
                "memory_value": new_val,
                "occurrence_count": total,
                "last_observed_at": now
            })
            self.repository.upsert_memory(updated_mem)
        else:
            mem_id = f"mem_{uuid.uuid4().hex[:12]}"
            new_val = {
                "platform": platform,
                "provider": provider,
                "total_evaluated": 1,
                "valid_count": 1 if is_valid else 0,
                "warning_count": 1 if is_warn else 0,
                "rejected_count": 1 if is_rej else 0,
                "scores_sum": result.overall_score,
                "average_score": result.overall_score,
                "reliability_index": 1.0 if is_valid else (0.5 if is_warn else 0.0)
            }
            new_mem = AIAgentMemory(
                id=mem_id,
                agent_id=self.AGENT_ID,
                memory_type="reliability_score",
                memory_key=rel_key,
                memory_value=new_val,
                confidence_score=0.95,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            )
            self.repository.upsert_memory(new_mem)

    def get_learned_patterns(self) -> List[AIAgentMemory]:
        """Retrieves all memory items for DataQualityAgent."""
        return self.repository.list_memories(self.AGENT_ID)
