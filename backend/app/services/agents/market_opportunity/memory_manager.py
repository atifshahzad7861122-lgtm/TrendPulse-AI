import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from backend.app.models.domain import AIAgentMemory, AIAgentMemoryEvent, MarketOpportunity
from backend.app.repositories.base import MarketOpportunityRepository


class MarketOpportunityMemoryManager:
    """
    Persistent memory manager for Agent 07 (Market Opportunity Intelligence Agent).
    Stores confirmed opportunity rules, category opportunity patterns, and false-positive criteria
    in ai_agent_memory with full audit logging in ai_agent_memory_events.
    """

    AGENT_ID = "agent_market_opportunity_intelligence"
    GLOBAL_RULE_KEY = "mem_market_opportunity_rules"

    @classmethod
    def record_opportunity_pattern(
        cls,
        opp_repo: MarketOpportunityRepository,
        opportunity: MarketOpportunity,
        category: Optional[str] = None,
        trigger_run_id: Optional[str] = None
    ) -> AIAgentMemory:
        """
        Stores or reinforces a confirmed opportunity pattern.
        """
        cat_key = category or opportunity.category or "General"
        mem_key = f"opp_pattern:{opportunity.opportunity_type}:{cat_key}"
        mem_type = "opportunity_pattern"

        existing = opp_repo.get_memory(cls.AGENT_ID, mem_type, mem_key)
        now = datetime.now(timezone.utc)

        if existing:
            # Reinforce memory
            new_count = existing.occurrence_count + 1
            new_conf = min(0.99, existing.confidence_score + 0.03)
            old_val = dict(existing.memory_value)
            new_val = {
                "occurrence_count": new_count,
                "last_observed_score": opportunity.score,
                "last_opportunity_id": opportunity.id,
                "opportunity_type": opportunity.opportunity_type,
                "category": cat_key
            }

            updated = opp_repo.upsert_memory(AIAgentMemory(
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
            opp_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=existing.id,
                event_type="reinforced",
                old_value=old_val,
                new_value=new_val,
                reason=f"Reinforced opportunity pattern {opportunity.opportunity_type} in {cat_key}",
                trigger_run_id=trigger_run_id,
                created_at=now
            ))
            return updated
        else:
            # Create new memory
            mem_id = f"omem_{uuid.uuid4().hex[:12]}"
            new_val = {
                "occurrence_count": 1,
                "last_observed_score": opportunity.score,
                "last_opportunity_id": opportunity.id,
                "opportunity_type": opportunity.opportunity_type,
                "category": cat_key
            }

            new_mem = opp_repo.upsert_memory(AIAgentMemory(
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
            opp_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=mem_id,
                event_type="created",
                old_value={},
                new_value=new_val,
                reason=f"Recorded new opportunity pattern for {opportunity.opportunity_type} in {cat_key}",
                trigger_run_id=trigger_run_id,
                created_at=now
            ))
            return new_mem

    @classmethod
    def record_global_rule_memory(
        cls,
        opp_repo: MarketOpportunityRepository,
        rule_name: str,
        rule_definition: Dict[str, Any]
    ) -> AIAgentMemory:
        """
        Maintains global opportunity rules under the key 'mem_market_opportunity_rules'.
        """
        mem_key = cls.GLOBAL_RULE_KEY
        mem_type = "opportunity_rules"

        existing = opp_repo.get_memory(cls.AGENT_ID, mem_type, mem_key)
        now = datetime.now(timezone.utc)

        if existing:
            old_val = dict(existing.memory_value)
            new_val = dict(existing.memory_value)
            new_val[rule_name] = rule_definition
            new_val["last_updated_at"] = now.isoformat()

            updated = opp_repo.upsert_memory(AIAgentMemory(
                id=existing.id,
                agent_id=cls.AGENT_ID,
                memory_type=mem_type,
                memory_key=mem_key,
                memory_value=new_val,
                confidence_score=0.95,
                occurrence_count=existing.occurrence_count + 1,
                last_observed_at=now,
                created_at=existing.created_at,
                updated_at=now
            ))

            opp_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=existing.id,
                event_type="updated",
                old_value=old_val,
                new_value=new_val,
                reason=f"Updated global opportunity rule '{rule_name}'",
                created_at=now
            ))
            return updated
        else:
            mem_id = f"omem_{uuid.uuid4().hex[:12]}"
            new_val = {
                rule_name: rule_definition,
                "created_at": now.isoformat(),
                "last_updated_at": now.isoformat()
            }

            new_mem = opp_repo.upsert_memory(AIAgentMemory(
                id=mem_id,
                agent_id=cls.AGENT_ID,
                memory_type=mem_type,
                memory_key=mem_key,
                memory_value=new_val,
                confidence_score=0.95,
                occurrence_count=1,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            ))

            opp_repo.record_memory_event(AIAgentMemoryEvent(
                id=f"mevt_{uuid.uuid4().hex[:12]}",
                agent_id=cls.AGENT_ID,
                memory_id=mem_id,
                event_type="created",
                old_value={},
                new_value=new_val,
                reason="Initialized global opportunity rules memory",
                created_at=now
            ))
            return new_mem
