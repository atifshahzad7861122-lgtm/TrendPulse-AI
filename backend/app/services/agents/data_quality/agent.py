import time
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.models.domain import (
    AIAgent, AIAgentRun, AIAgentMemory, AIAgentMemoryEvent,
    DataQualityRuleViolation, DataQualityValidationResult
)
from backend.app.repositories.base import DataQualityRepository
from backend.app.services.llm.provider import LLMProvider
from backend.app.services.agents.data_quality.rules_engine import DataQualityRulesEngine
from backend.app.services.agents.data_quality.scorer import DataQualityScorer
from backend.app.services.agents.data_quality.llm_resolver import DataQualityLLMResolver
from backend.app.services.agents.data_quality.memory_manager import DataQualityMemoryManager

class DataQualityAgent:
    """
    Agent 1: Production Data Quality & Validation Agent for TrendPulse AI.
    Autonomously evaluates raw & normalized product listings across Daraz, Shopify, and all future platforms.
    Enforces deterministic validation gates, impossible value detection, staleness checks,
    selective Gemini LLM resolution, persistent pattern learning, and run auditing.
    """

    AGENT_ID = "agent_data_quality"

    def __init__(
        self,
        repository: DataQualityRepository,
        llm_provider: Optional[LLMProvider] = None,
        staleness_days: int = 30
    ):
        self.repository = repository
        self.rules_engine = DataQualityRulesEngine(staleness_days=staleness_days)
        self.scorer = DataQualityScorer()
        self.llm_resolver = DataQualityLLMResolver(provider=llm_provider)
        self.memory_manager = DataQualityMemoryManager(repository=repository)

    def _hash_payload(self, payload: Dict[str, Any]) -> str:
        try:
            raw_str = json.dumps(payload, sort_keys=True, default=str)
            return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
        except Exception:
            return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()

    def validate_product(
        self,
        payload: Dict[str, Any],
        platform: Optional[str] = None,
        source_provider: Optional[str] = None,
        allow_llm: bool = True,
        workspace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        save_result: bool = True,
        existing_catalog: Optional[List[Dict[str, Any]]] = None
    ) -> DataQualityValidationResult:
        """
        Evaluates a single product payload through the validation pipeline.
        """
        plat = str(platform or payload.get("platform") or "unknown").lower()
        prov = str(source_provider or payload.get("source_provider") or "direct").lower()
        p_id = str(payload.get("product_id") or payload.get("id") or payload.get("platform_product_id") or "").strip()
        title = str(payload.get("title") or payload.get("product_name") or payload.get("name") or "").strip()
        now = datetime.now(timezone.utc)
        res_id = f"dqr_{uuid.uuid4().hex[:14]}"

        # 1. Deterministic Rule Evaluation
        issues, warnings, field_scores, needs_llm, llm_context = self.rules_engine.evaluate(
            payload=payload,
            existing_catalog=existing_catalog
        )

        # 2. Selective LLM Ambiguity Resolution
        used_llm = False
        llm_resolution: Optional[Dict[str, Any]] = None

        if allow_llm and needs_llm and self.llm_resolver.provider is not None:
            # We only invoke LLM for ambiguous items (not completely broken items)
            critical_missing = any(iss.rule_name in ["mandatory_product_id", "mandatory_price", "impossible_negative_or_zero_price"] for iss in issues)
            if not critical_missing and title:
                resolution = self.llm_resolver.resolve_ambiguity(
                    product_title=title,
                    platform=plat,
                    category_raw=str(payload.get("category") or ""),
                    brand_raw=str(payload.get("brand") or ""),
                    price=float(payload.get("price")) if payload.get("price") is not None else None,
                    currency=str(payload.get("currency") or ""),
                    context_hints=llm_context
                )
                if resolution:
                    used_llm = True
                    llm_resolution = resolution

                    # Apply LLM insights to enhance quality or flag spam
                    if resolution.get("is_spam"):
                        issues.append(DataQualityRuleViolation(
                            field="title",
                            rule_name="llm_detected_spam_title",
                            severity="critical",
                            message=f"LLM identified title as spam / abusive keywords: {resolution.get('quality_assessment')}",
                            observed_value=title[:80],
                            penalty_score=40.0
                        ))
                    if resolution.get("extracted_brand") and not payload.get("brand"):
                        # Brand recovered by LLM; reduce warning penalty
                        warnings = [w for w in warnings if w.rule_name != "missing_or_generic_brand"]
                        field_scores["brand"] = 0.9
                    if resolution.get("mapped_category") and (not payload.get("category") or str(payload.get("category")).isdigit()):
                        # Category recovered by LLM; reduce warning penalty
                        warnings = [w for w in warnings if w.rule_name not in ["missing_or_generic_category", "numeric_raw_category_id"]]
                        field_scores["category"] = 0.95

        # 3. Deterministic Scoring
        score, classification, is_trusted = self.scorer.calculate_score(
            issues=issues,
            warnings=warnings,
            field_scores=field_scores
        )

        # 4. Extract Category and Field Breakdowns for Public Read Model
        raw_cat = payload.get("category") or payload.get("category_name") or payload.get("raw_category")
        original_category = str(raw_cat).strip() if raw_cat is not None and str(raw_cat).strip() else None
        
        # Category normalization: never invent a category. If missing, set to "Unknown"
        if llm_resolution and llm_resolution.get("mapped_category"):
            normalized_category = str(llm_resolution["mapped_category"]).strip()
        elif original_category:
            normalized_category = original_category
        else:
            normalized_category = "Unknown"

        # Explicit Data Quality Category for rejected products
        data_quality_category = "Data Quality Issues" if classification == "rejected" else ""

        # Segregate issues into structured arrays for public auditability
        rejection_reasons = [iss.message for iss in issues] if classification == "rejected" else []
        missing_fields = [iss.field for iss in issues if "missing" in iss.rule_name or "mandatory" in iss.rule_name] + \
                         [w.field for w in warnings if "missing" in w.rule_name or "empty" in w.rule_name]
        invalid_fields = [iss.field for iss in issues if "impossible" in iss.rule_name or "invalid" in iss.rule_name or "negative" in iss.rule_name] + \
                         [w.field for w in warnings if "invalid" in w.rule_name or "stale" in w.rule_name]
        suspicious_fields = [iss.field for iss in issues if "spam" in iss.rule_name or "suspicious" in iss.rule_name] + \
                            [w.field for w in warnings if "spam" in w.rule_name or "suspicious" in w.rule_name]

        # Extract numeric & scalar fields
        raw_price = payload.get("price")
        parsed_price: Optional[float] = None
        if raw_price is not None:
            try:
                parsed_price = float(raw_price)
            except (ValueError, TypeError):
                parsed_price = None

        raw_rating = payload.get("rating")
        parsed_rating: Optional[float] = None
        if raw_rating is not None:
            try:
                parsed_rating = float(raw_rating)
            except (ValueError, TypeError):
                parsed_rating = None

        raw_reviews = payload.get("review_count") or payload.get("reviews") or 0
        try:
            parsed_reviews = int(raw_reviews)
        except (ValueError, TypeError):
            parsed_reviews = 0

        raw_avail = payload.get("available")
        if raw_avail is None:
            raw_avail = payload.get("in_stock", True)
        parsed_avail = bool(raw_avail)

        product_url = str(payload.get("product_url") or payload.get("url") or "") or None
        image_url = str(payload.get("image_url") or payload.get("image") or payload.get("primary_image") or "") or None
        currency_code = str(payload.get("currency") or "PKR").upper()

        result = DataQualityValidationResult(
            id=res_id,
            agent_id=self.AGENT_ID,
            run_id=run_id,
            workspace_id=workspace_id,
            platform=plat,
            source_provider=prov,
            platform_product_id=p_id,
            unified_product_id=payload.get("unified_product_id"),
            product_title=title or "Untitled Product",
            product_name=title or "Untitled Product",
            original_category=original_category,
            normalized_category=normalized_category,
            data_quality_category=data_quality_category,
            product_url=product_url,
            image_url=image_url,
            price=parsed_price,
            currency=currency_code,
            rating=parsed_rating,
            review_count=parsed_reviews,
            availability=parsed_avail,
            overall_score=score,
            quality_score=score,
            classification=classification,
            is_trusted=is_trusted,
            issues=issues,
            warnings=warnings,
            rejection_reasons=rejection_reasons,
            missing_fields=list(set(missing_fields)),
            invalid_fields=list(set(invalid_fields)),
            suspicious_fields=list(set(suspicious_fields)),
            field_scores=field_scores,
            raw_payload_hash=self._hash_payload(payload),
            used_llm=used_llm,
            llm_used=used_llm,
            llm_provider="gemini" if used_llm else None,
            llm_resolution=llm_resolution,
            raw_payload=payload,
            validated_at=now,
            created_at=now,
            updated_at=now
        )

        # 5. Save validation record & update memory
        if save_result:
            self.repository.save_validation_result(result)
            self.memory_manager.record_validation_memory(result, run_id=run_id)

        return result


    def validate_batch(
        self,
        products: List[Dict[str, Any]],
        platform: Optional[str] = None,
        source_provider: Optional[str] = None,
        allow_llm: bool = True,
        workspace_id: Optional[str] = None,
        trigger_source: str = "manual"
    ) -> Tuple[AIAgentRun, List[DataQualityValidationResult]]:
        """
        Processes a batch of products within an audited AIAgentRun.
        """
        start_time = time.time()
        now = datetime.now(timezone.utc)
        run_id = f"run_{uuid.uuid4().hex[:14]}"

        # Initialize run record
        agent_run = AIAgentRun(
            id=run_id,
            agent_id=self.AGENT_ID,
            workspace_id=workspace_id,
            run_type="ad_hoc_batch" if trigger_source == "manual" else "ingestion_stream",
            status="running",
            trigger_source=trigger_source,
            items_processed=0,
            items_valid=0,
            items_warning=0,
            items_needs_review=0,
            items_rejected=0,
            avg_quality_score=0.0,
            gemini_calls_count=0,
            execution_time_ms=0.0,
            started_at=now,
            created_at=now
        )
        self.repository.create_agent_run(agent_run)

        results: List[DataQualityValidationResult] = []
        gemini_calls = 0
        score_sum = 0.0

        for prod in products:
            res = self.validate_product(
                payload=prod,
                platform=platform,
                source_provider=source_provider,
                allow_llm=allow_llm,
                workspace_id=workspace_id,
                run_id=run_id,
                save_result=True,
                existing_catalog=products
            )
            results.append(res)
            score_sum += res.overall_score
            if res.used_llm:
                gemini_calls += 1

        total = len(results)
        valid_cnt = len([r for r in results if r.classification == "valid"])
        warn_cnt = len([r for r in results if r.classification == "valid_with_warnings"])
        review_cnt = len([r for r in results if r.classification == "needs_review"])
        rej_cnt = len([r for r in results if r.classification == "rejected"])
        avg_score = round(score_sum / max(1, total), 1) if total else 100.0
        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)
        completed_now = datetime.now(timezone.utc)

        # Finalize run record
        agent_run = agent_run.model_copy(update={
            "status": "completed",
            "items_processed": total,
            "items_valid": valid_cnt,
            "items_warning": warn_cnt,
            "items_needs_review": review_cnt,
            "items_rejected": rej_cnt,
            "avg_quality_score": avg_score,
            "gemini_calls_count": gemini_calls,
            "execution_time_ms": elapsed_ms,
            "completed_at": completed_now
        })
        self.repository.update_agent_run(agent_run)

        return agent_run, results

    def get_status(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns comprehensive status, memory stats, and reliability breakdown."""
        agent = self.repository.get_agent(self.AGENT_ID)
        summary = self.repository.get_quality_summary(workspace_id=workspace_id)
        return {
            "agent_id": self.AGENT_ID,
            "agent_name": agent.name if agent else "Data Quality & Validation Agent",
            "status": agent.status if agent else "active",
            "version": agent.version if agent else "1.0.0",
            "capabilities": agent.capabilities if agent else [],
            **summary
        }
