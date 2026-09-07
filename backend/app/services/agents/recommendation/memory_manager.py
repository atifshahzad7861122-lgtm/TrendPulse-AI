import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from backend.app.models.domain import AIAgentMemory, AIAgentMemoryEvent, ProductRecommendation
from backend.app.repositories.base import RecommendationRepository


class RecommendationMemoryManager:
    """
    Persistent memory manager for Agent 06 (Recommendation & Product Intelligence Agent).
    Stores successful recommendation patterns, confirmed operator outcomes, category affinities,
    and ranking calibrations in ai_agent_memory with full audit logging in ai_agent_memory_events.
    """

    AGENT_ID = "agent_recommendation_engine"

    @classmethod
    def record_recommendation_pattern(
        cls,
        rec_repo: RecommendationRepository,
        recommendation: ProductRecommendation,
        category: str,
        trigger_run_id: Optional[str] = None
    ) -> AIAgentMemory:
        """
        Stores or reinforces a confirmed recommendation pattern.
        """
        mem_key = f"rec_pattern:{recommendation.recommendation_type}:{category}"
        mem_type = "recommendation_pattern"

        existing = rec_repo.get_memory(cls.AGENT_ID, mem_type, mem_key)
        now = datetime.now(timezone.utc)

        if existing:
            # Reinforce memory
            new_count = existing.occurrence_count + 1
            new_conf = min(0.99, existing.confidence_score + 0.03)
            old_val = dict(existing.memory_value)
            new_val = {
                "occurrence_count": new_count,
                "last_observed_score": recommendation.score,
                "last_recommendation_id": recommendation.id
            }

            updated = rec_repo.upsert_memory(AIAgentMemory(
                id=existing.id,
                agent_id=cls.AGENT_ID,
                memory_type=mem_type,
                memory_key=mem_key,
                memory_value=new_val,
                confidence_score=new_conf,
                occurrence_count=new_count,
                last_observed_at=now,
                created_at=existing.created_at,
                updated_at=now
            ))

            # Audit event
            rec_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=existing.id,
                event_type="reinforced",
                old_value=old_val,
                new_value=new_val,
                reason=f"Reinforced recommendation pattern {recommendation.recommendation_type} for {category}",
                trigger_run_id=trigger_run_id,
                created_at=now
            ))
            return updated
        else:
            # Create new memory
            mem_id = f"rmem_{uuid.uuid4().hex[:12]}"
            new_val = {
                "occurrence_count": 1,
                "last_observed_score": recommendation.score,
                "last_recommendation_id": recommendation.id
            }

            new_mem = rec_repo.upsert_memory(AIAgentMemory(
                id=mem_id,
                agent_id=cls.AGENT_ID,
                memory_type=mem_type,
                memory_key=mem_key,
                memory_value=new_val,
                confidence_score=0.85,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            ))

            # Audit event
            rec_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=mem_id,
                event_type="created",
                old_value={},
                new_value=new_val,
                reason=f"Learned new recommendation pattern for {recommendation.recommendation_type} in {category}",
                trigger_run_id=trigger_run_id,
                created_at=now
            ))
            return new_mem

    @classmethod
    def record_user_preference_memory(
        cls,
        rec_repo: RecommendationRepository,
        user_id: str,
        preferred_category: str,
        interaction_type: str
    ) -> AIAgentMemory:
        """
        Stores user category preference from real interaction events.
        """
        mem_key = f"user_pref:{user_id}:{preferred_category}"
        mem_type = "user_preference"

        existing = rec_repo.get_memory(cls.AGENT_ID, mem_type, mem_key)
        now = datetime.now(timezone.utc)

        if existing:
            new_count = existing.occurrence_count + 1
            new_conf = min(0.99, existing.confidence_score + 0.05)
            old_val = dict(existing.memory_value)
            new_val = {
                "user_id": user_id,
                "category": preferred_category,
                "interactions_count": new_count,
                "last_interaction": interaction_type
            }

            updated = rec_repo.upsert_memory(AIAgentMemory(
                id=existing.id,
                agent_id=cls.AGENT_ID,
                memory_type=mem_type,
                memory_key=mem_key,
                memory_value=new_val,
                confidence_score=new_conf,
                occurrence_count=new_count,
                last_observed_at=now,
                created_at=existing.created_at,
                updated_at=now
            ))

            rec_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=existing.id,
                event_type="reinforced",
                old_value=old_val,
                new_value=new_val,
                reason=f"Updated user category affinity via {interaction_type}",
                created_at=now
            ))
            return updated
        else:
            mem_id = f"rmem_{uuid.uuid4().hex[:12]}"
            new_val = {
                "user_id": user_id,
                "category": preferred_category,
                "interactions_count": 1,
                "last_interaction": interaction_type
            }

            new_mem = rec_repo.upsert_memory(AIAgentMemory(
                id=mem_id,
                agent_id=cls.AGENT_ID,
                memory_type=mem_type,
                memory_key=mem_key,
                memory_value=new_val,
                confidence_score=0.80,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            ))

            rec_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=mem_id,
                event_type="created",
                old_value={},
                new_value=new_val,
                reason=f"Recorded new category affinity for user {user_id}",
                created_at=now
            ))
            return new_mem
