import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, ProductMatchDecision,
    ProductMatchCandidate, ProductMatchAudit, ProductSignature
)
from backend.app.repositories.base import UnifiedProductRepository, TaxonomyRepository, LLMUsageRepository
from backend.app.services.llm.provider import LLMProvider
from backend.app.services.agents.entity_matching.signature import ProductSignatureBuilder
from backend.app.services.agents.entity_matching.blocking import CandidateBlocker
from backend.app.services.agents.entity_matching.rules_engine import DeterministicEntityMatcher
from backend.app.services.agents.entity_matching.memory_manager import EntityMatchingMemoryManager
from backend.app.services.agents.entity_matching.llm_resolver import EntityMatchingLLMResolver

logger = logging.getLogger("trendpulse.agents.entity_matching")

class ProductEntityMatchingAgent:
    """
    Agent 3: Product Entity Matching & Deduplication Agent for TrendPulse AI.
    Executes cross-platform product entity resolution, multi-tier deterministic identifier matching,
    candidate blocking, variant detection, false-positive protection, selective Gemini reasoning,
    review queue orchestration, and persistent memory learning.
    """

    AGENT_ID = "agent_entity_matching"

    def __init__(
        self,
        unified_repo: UnifiedProductRepository,
        taxonomy_repo: Optional[TaxonomyRepository] = None,
        llm_provider: Optional[LLMProvider] = None,
        llm_usage_repo: Optional[LLMUsageRepository] = None,
        exact_threshold: float = 0.99,
        high_threshold: float = 0.95,
        probable_threshold: float = 0.85,
        review_threshold: float = 0.75
    ):
        self.unified_repo = unified_repo
        if taxonomy_repo is None:
            from backend.app.repositories.in_memory import InMemoryTaxonomyRepository
            self.taxonomy_repo = InMemoryTaxonomyRepository()
        else:
            self.taxonomy_repo = taxonomy_repo
        self.signature_builder = ProductSignatureBuilder
        self.blocker = CandidateBlocker
        self.rules_engine = DeterministicEntityMatcher
        self.memory_manager = EntityMatchingMemoryManager(repository=self.taxonomy_repo)
        self.llm_resolver = EntityMatchingLLMResolver(
            provider=llm_provider,
            usage_repo=llm_usage_repo
        )
        self.exact_threshold = exact_threshold
        self.high_threshold = high_threshold
        self.probable_threshold = probable_threshold
        self.review_threshold = review_threshold

    def match_listing(
        self,
        payload: Dict[str, Any],
        candidate_pool: Optional[List[UnifiedProduct]] = None,
        allow_llm: bool = True,
        force_rematch: bool = False,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> Tuple[ProductMatchDecision, Optional[UnifiedProduct]]:
        """
        Main entrypoint: matches an incoming marketplace listing against the Unified Product catalog.
        """
        now = datetime.now(timezone.utc)
        platform = str(payload.get("platform") or "unknown").strip()
        platform_product_id = str(payload.get("platform_product_id") or payload.get("id") or f"prod_{uuid.uuid4().hex[:8]}").strip()
        store_domain = payload.get("store_domain")

        # Step 0: Check if exact same listing already exists on this platform
        if not force_rematch and self.unified_repo:
            existing_listing = self.unified_repo.get_platform_listing(
                platform=platform,
                platform_product_id=platform_product_id,
                store_domain=store_domain
            )
            if existing_listing:
                existing_u_prod = self.unified_repo.get_unified_product(existing_listing.unified_product_id)
                if existing_u_prod:
                    decision = ProductMatchDecision(
                        id=f"pmd_{uuid.uuid4().hex[:12]}",
                        product_a_id=platform_product_id,
                        product_b_id=existing_u_prod.unified_product_id,
                        unified_product_id=existing_u_prod.unified_product_id,
                        platform_a=platform,
                        platform_b=platform,
                        decision="EXACT_MATCH",
                        confidence=1.0,
                        match_method="existing_platform_listing_resync",
                        reasons=[f"Existing listing matched on platform '{platform}' with ID '{platform_product_id}'"],
                        agent_id=self.AGENT_ID,
                        agent_run_id=run_id,
                        created_at=now,
                        updated_at=now
                    )
                    self.unified_repo.record_match_decision(decision)
                    return decision, existing_u_prod

        # Step 1: Build target product signature
        target_sig = self.signature_builder.build_signature(payload)
        raw_title = str(payload.get("product_name") or payload.get("title") or payload.get("name") or "").strip()

        # Step 2: Fetch candidate pool and apply candidate blocking
        if candidate_pool is None:
            candidate_pool = self.unified_repo.list_unified_products(limit=500) if self.unified_repo else []

        filtered_candidates = self.blocker.filter_candidates(target_sig, candidate_pool, max_candidates=50)

        best_decision: Optional[ProductMatchDecision] = None
        best_candidate: Optional[UnifiedProduct] = None

        # Step 3: Evaluate candidates through tiered matching hierarchy
        for candidate in filtered_candidates:
            cand_name = getattr(candidate, "canonical_name", "") if not isinstance(candidate, dict) else candidate.get("canonical_name", "")
            cand_brand = getattr(candidate, "brand", None) if not isinstance(candidate, dict) else candidate.get("brand")
            cand_cat = getattr(candidate, "category", None) if not isinstance(candidate, dict) else candidate.get("category")
            cand_subcat = getattr(candidate, "subcategory", None) if not isinstance(candidate, dict) else candidate.get("subcategory")
            cand_ptype = getattr(candidate, "product_type", None) if not isinstance(candidate, dict) else candidate.get("product_type")
            cand_desc = getattr(candidate, "description", "") if not isinstance(candidate, dict) else candidate.get("description", "")
            cand_ids = getattr(candidate, "identifiers", {}) if not isinstance(candidate, dict) else candidate.get("identifiers", {})
            cand_unf_id = getattr(candidate, "unified_product_id", "") if not isinstance(candidate, dict) else candidate.get("unified_product_id", "")

            cand_payload = {
                "title": cand_name,
                "canonical_name": cand_name,
                "brand": cand_brand,
                "category": cand_cat,
                "subcategory": cand_subcat,
                "product_type": cand_ptype,
                "description": cand_desc or "",
                "identifiers": cand_ids or {},
                "model_number": (cand_ids or {}).get("model_number")
            }
            cand_sig = self.signature_builder.build_signature(cand_payload)

            # 3A. Check Persistent Agent Memory
            if self.memory_manager:
                learned_mem = self.memory_manager.get_learned_pair(target_sig.signature_hash, cand_sig.signature_hash)
                if learned_mem:
                    if learned_mem.memory_type == "confirmed_no_match_signature":
                        # Known false positive -> skip candidate
                        continue
                    elif learned_mem.memory_type == "confirmed_match_signature":
                        decision = ProductMatchDecision(
                            id=f"pmd_{uuid.uuid4().hex[:12]}",
                            product_a_id=platform_product_id,
                            product_b_id=cand_unf_id,
                            unified_product_id=cand_unf_id,
                            platform_a=platform,
                            platform_b="unified",
                            decision=learned_mem.memory_value.get("decision", "EXACT_MATCH"),
                            confidence=learned_mem.confidence_score,
                            match_method="persistent_agent_memory",
                            reasons=["Matched via Agent 3 persistent memory pattern"],
                            agent_id=self.AGENT_ID,
                            agent_run_id=run_id,
                            created_at=now,
                            updated_at=now
                        )
                        best_decision = decision
                        best_candidate = candidate
                        break

            # 3B. Evaluate Deterministic Tiers (1-6)
            decision = self.rules_engine.evaluate_pair(
                sig1=target_sig,
                sig2=cand_sig,
                product_a_id=platform_product_id,
                product_b_id=cand_unf_id,
                platform_a=platform,
                platform_b="unified"
            )

            # 3C. Selective Gemini LLM Resolution for Ambiguous Candidates (Tier 7)
            if decision.decision == "NEEDS_REVIEW" and allow_llm:
                llm_data, llm_conf, llm_method, llm_ok = self.llm_resolver.resolve_ambiguity(
                    sig1=target_sig,
                    sig2=cand_sig,
                    product_a_title=raw_title,
                    product_b_title=cand_name,
                    user_id=user_id,
                    workspace_id=workspace_id
                )
                if llm_ok:
                    llm_dec = llm_data.get("decision", "").lower()
                    if llm_dec == "same_product" and llm_conf >= self.probable_threshold:
                        decision.decision = "PROBABLE_MATCH"
                        decision.confidence = llm_conf
                        decision.match_method = llm_method
                        decision.reasons = llm_data.get("reasons", ["Gemini confirmed same product"])
                        decision.llm_used = True
                        decision.llm_provider = "gemini"
                        decision.llm_model = "gemini-1.5-flash"
                    elif llm_dec == "variant":
                        decision.decision = "VARIANT"
                        decision.confidence = llm_conf
                        decision.match_method = llm_method
                        decision.variant_attributes = llm_data.get("variant_attributes", {})
                        decision.reasons = llm_data.get("reasons", ["Gemini identified product variant"])
                        decision.llm_used = True
                        decision.llm_provider = "gemini"
                        decision.llm_model = "gemini-1.5-flash"
                    elif llm_dec in ["related", "different"]:
                        decision.decision = "NO_MATCH" if llm_dec == "different" else "RELATED_PRODUCT"
                        decision.confidence = 0.20
                        decision.match_method = llm_method
                        decision.conflicts = llm_data.get("conflicts", ["Gemini confirmed different products"])
                        decision.llm_used = True

            # Track best match
            if decision.decision in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH", "PROBABLE_MATCH", "VARIANT"]:
                if best_decision is None or decision.confidence > best_decision.confidence:
                    best_decision = decision
                    best_candidate = candidate
                    decision.unified_product_id = cand_unf_id
            elif decision.decision == "NEEDS_REVIEW":
                if best_decision is None or best_decision.decision not in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH"]:
                    best_decision = decision
                    best_candidate = candidate
                    decision.unified_product_id = cand_unf_id

        # Step 4: Finalize Decision & Link Unified Product
        matched_unified: Optional[UnifiedProduct] = None

        if best_decision and best_decision.decision in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH", "PROBABLE_MATCH", "VARIANT"] and best_candidate:
            if isinstance(best_candidate, dict):
                matched_unified = UnifiedProduct(**best_candidate)
            else:
                matched_unified = best_candidate
            best_decision.unified_product_id = matched_unified.unified_product_id

            # Update UnifiedProduct metadata if richer
            if self.unified_repo:
                update_fields: Dict[str, Any] = {"last_seen_at": now}
                if not matched_unified.brand and target_sig.brand:
                    update_fields["brand"] = target_sig.brand
                if not matched_unified.category and target_sig.category:
                    update_fields["category"] = target_sig.category
                if not matched_unified.product_type and target_sig.product_type:
                    update_fields["product_type"] = target_sig.product_type
                if target_sig.identifiers:
                    combined_ids = {**(matched_unified.identifiers or {}), **target_sig.identifiers}
                    update_fields["identifiers"] = combined_ids

                matched_unified = matched_unified.model_copy(update=update_fields)
                self.unified_repo.upsert_unified_product(matched_unified)

            # Learn in memory if high confidence
            if self.memory_manager and best_decision.confidence >= self.high_threshold:
                cand_dict = best_candidate.model_dump() if hasattr(best_candidate, "model_dump") else best_candidate
                self.memory_manager.record_confirmed_match(
                    sig1=target_sig,
                    sig2=ProductSignatureBuilder.build_signature(cand_dict),
                    decision=best_decision.decision,
                    confidence=best_decision.confidence,
                    reason=best_decision.match_method,
                    run_id=run_id
                )

        elif best_decision and best_decision.decision == "NEEDS_REVIEW" and best_candidate:
            # Record in Match Candidates Review Queue
            if self.unified_repo:
                cand_record = ProductMatchCandidate(
                    id=f"cand_{uuid.uuid4().hex[:12]}",
                    unified_product_id=best_candidate.unified_product_id,
                    candidate_unified_id=best_candidate.unified_product_id,
                    platform=platform,
                    platform_product_id=platform_product_id,
                    confidence_score=best_decision.confidence,
                    method=best_decision.match_method,
                    status="needs_review",
                    reasons=best_decision.reasons,
                    created_at=now
                )
                self.unified_repo.record_match_candidate(cand_record)

            # Create separate entity for now to avoid false-positive merge
            new_id = f"unf_{uuid.uuid4().hex[:12]}"
            matched_unified = UnifiedProduct(
                id=new_id,
                unified_product_id=new_id,
                canonical_name=raw_title,
                normalized_name=target_sig.normalized_title,
                brand=target_sig.brand,
                category=target_sig.category or "Unknown",
                subcategory=target_sig.subcategory or "Unknown",
                product_type=target_sig.product_type or "Unknown",
                description=str(payload.get("description") or ""),
                primary_image=payload.get("image_url"),
                identifiers=target_sig.identifiers,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now
            )
            if self.unified_repo:
                self.unified_repo.upsert_unified_product(matched_unified)
            best_decision.unified_product_id = new_id

        else:
            # NO_MATCH -> Create New Canonical Unified Product
            new_id = f"unf_{uuid.uuid4().hex[:12]}"
            matched_unified = UnifiedProduct(
                id=new_id,
                unified_product_id=new_id,
                canonical_name=raw_title,
                normalized_name=target_sig.normalized_title,
                brand=target_sig.brand,
                category=target_sig.category or "Unknown",
                subcategory=target_sig.subcategory or "Unknown",
                product_type=target_sig.product_type or "Unknown",
                description=str(payload.get("description") or ""),
                primary_image=payload.get("image_url"),
                identifiers=target_sig.identifiers,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now
            )
            if self.unified_repo:
                self.unified_repo.upsert_unified_product(matched_unified)

            best_decision = ProductMatchDecision(
                id=f"pmd_{uuid.uuid4().hex[:12]}",
                product_a_id=platform_product_id,
                product_b_id=None,
                unified_product_id=new_id,
                platform_a=platform,
                platform_b=None,
                decision="NO_MATCH",
                confidence=1.0,
                match_method="new_canonical_product",
                reasons=["Created new canonical unified product"],
                agent_id=self.AGENT_ID,
                agent_run_id=run_id,
                created_at=now,
                updated_at=now
            )

        # Record decision & audit
        if self.unified_repo:
            self.unified_repo.record_match_decision(best_decision)
            if matched_unified:
                audit = ProductMatchAudit(
                    id=f"audit_{uuid.uuid4().hex[:12]}",
                    unified_product_id=matched_unified.unified_product_id,
                    platform=platform,
                    platform_product_id=platform_product_id,
                    matching_method=best_decision.match_method,
                    matching_confidence=best_decision.confidence,
                    matched_at=now,
                    details={
                        "decision": best_decision.decision,
                        "reasons": best_decision.reasons,
                        "conflicts": best_decision.conflicts,
                        "variant_attributes": best_decision.variant_attributes,
                        "llm_used": best_decision.llm_used
                    },
                    created_at=now
                )
                self.unified_repo.record_match_audit(audit)

        return best_decision, matched_unified

    def compare_products(
        self,
        product_a: Dict[str, Any],
        product_b: Dict[str, Any],
        allow_llm: bool = True
    ) -> ProductMatchDecision:
        """
        Directly evaluates matching between two specified product payloads.
        """
        sig1 = self.signature_builder.build_signature(product_a)
        sig2 = self.signature_builder.build_signature(product_b)

        p_a_id = str(product_a.get("id") or product_a.get("product_id") or "prod_a")
        p_b_id = str(product_b.get("id") or product_b.get("product_id") or "prod_b")

        # 1. Memory check
        if self.memory_manager:
            learned = self.memory_manager.get_learned_pair(sig1.signature_hash, sig2.signature_hash)
            if learned:
                if learned.memory_type == "confirmed_no_match_signature":
                    return ProductMatchDecision(
                        id=f"pmd_{p_a_id}_{p_b_id}",
                        product_a_id=p_a_id,
                        product_b_id=p_b_id,
                        platform_a=product_a.get("platform", "unknown"),
                        platform_b=product_b.get("platform", "unknown"),
                        decision="NO_MATCH",
                        confidence=1.0,
                        match_method="persistent_agent_memory",
                        reasons=["Confirmed no-match in persistent memory"],
                        conflicts=["Known false positive pair"]
                    )
                elif learned.memory_type == "confirmed_match_signature":
                    self.memory_manager.record_confirmed_match(sig1, sig2, learned.memory_value.get("decision", "EXACT_MATCH"), learned.confidence_score)
                    return ProductMatchDecision(
                        id=f"pmd_{p_a_id}_{p_b_id}",
                        product_a_id=p_a_id,
                        product_b_id=p_b_id,
                        platform_a=product_a.get("platform", "unknown"),
                        platform_b=product_b.get("platform", "unknown"),
                        decision=learned.memory_value.get("decision", "EXACT_MATCH"),
                        confidence=learned.confidence_score,
                        match_method="persistent_agent_memory",
                        reasons=["Matched via Agent 3 persistent memory pattern"]
                    )

        # 2. Deterministic tiers
        decision = self.rules_engine.evaluate_pair(
            sig1=sig1,
            sig2=sig2,
            product_a_id=p_a_id,
            product_b_id=p_b_id,
            platform_a=product_a.get("platform", "unknown"),
            platform_b=product_b.get("platform", "unknown")
        )

        # 3. LLM if in ambiguous zone
        if decision.decision == "NEEDS_REVIEW" and allow_llm:
            title_a = str(product_a.get("product_name") or product_a.get("title") or "")
            title_b = str(product_b.get("product_name") or product_b.get("title") or "")
            llm_data, llm_conf, llm_method, llm_ok = self.llm_resolver.resolve_ambiguity(
                sig1=sig1,
                sig2=sig2,
                product_a_title=title_a,
                product_b_title=title_b
            )
            if llm_ok:
                llm_dec = llm_data.get("decision", "").lower()
                if llm_dec == "same_product" and llm_conf >= self.probable_threshold:
                    decision.decision = "PROBABLE_MATCH"
                    decision.confidence = llm_conf
                    decision.match_method = llm_method
                    decision.reasons = llm_data.get("reasons", [])
                    decision.llm_used = True
                elif llm_dec == "variant":
                    decision.decision = "VARIANT"
                    decision.confidence = llm_conf
                    decision.match_method = llm_method
                    decision.variant_attributes = llm_data.get("variant_attributes", {})
                    decision.reasons = llm_data.get("reasons", [])
                    decision.llm_used = True
                elif llm_dec in ["related", "different"]:
                    decision.decision = "NO_MATCH" if llm_dec == "different" else "RELATED_PRODUCT"
                    decision.confidence = 0.20
        if decision.decision in ["EXACT_MATCH", "HIGH_CONFIDENCE_MATCH"] and self.memory_manager:
            self.memory_manager.record_confirmed_match(sig1, sig2, decision.decision, decision.confidence)

        if self.unified_repo:
            self.unified_repo.record_match_decision(decision)

        return decision

    def resolve_review_candidate(
        self,
        candidate_id: str,
        action: str,  # 'confirm_match', 'confirm_variant', 'reject_match'
        variant_attributes: Optional[Dict[str, Any]] = None,
        notes: str = "",
        user_id: Optional[str] = None
    ) -> Optional[ProductMatchCandidate]:
        """
        Resolves a review queue candidate based on human admin confirmation,
        and learns the confirmed pattern into Agent 3 memory.
        """
        if not self.unified_repo:
            return None

        cand = self.unified_repo.get_match_candidate(candidate_id)
        if not cand:
            return None

        now = datetime.now(timezone.utc)
        u_prod = self.unified_repo.get_unified_product(cand.unified_product_id)

        if action == "confirm_match":
            cand.status = "confirmed_match"
            cand.reasons.append(f"Confirmed match by user: {notes or 'verified'}")
            if self.memory_manager and u_prod:
                sig1 = self.signature_builder.build_signature({"title": cand.platform_product_id, "platform": cand.platform})
                sig2 = self.signature_builder.build_signature(u_prod.model_dump())
                self.memory_manager.record_confirmed_match(sig1, sig2, decision="EXACT_MATCH", reason=notes or "Human confirmed match")

        elif action == "confirm_variant":
            cand.status = "confirmed_variant"
            cand.reasons.append(f"Confirmed variant by user: {notes or 'verified'}")
            if self.memory_manager and u_prod:
                sig1 = self.signature_builder.build_signature({"title": cand.platform_product_id, "platform": cand.platform})
                sig2 = self.signature_builder.build_signature(u_prod.model_dump())
                self.memory_manager.record_confirmed_match(sig1, sig2, decision="VARIANT", reason=notes or "Human confirmed variant")

        elif action == "reject_match":
            cand.status = "rejected"
            cand.reasons.append(f"Rejected match by user: {notes or 'false positive'}")
            if self.memory_manager and u_prod:
                sig1 = self.signature_builder.build_signature({"title": cand.platform_product_id, "platform": cand.platform})
                sig2 = self.signature_builder.build_signature(u_prod.model_dump())
                self.memory_manager.record_confirmed_no_match(sig1, sig2, reason=notes or "Human confirmed false positive")

        self.unified_repo.update_match_candidate(cand)
        return cand

    def get_stats(self) -> Dict[str, Any]:
        """
        Calculates telemetry performance stats for Agent 3.
        """
        if not self.unified_repo:
            return {}

        decisions = self.unified_repo.list_match_decisions(limit=1000)
        candidates = self.unified_repo.list_match_candidates(status="needs_review", limit=1000)
        total = len(decisions)

        exact_count = sum(1 for d in decisions if d.decision == "EXACT_MATCH")
        high_count = sum(1 for d in decisions if d.decision == "HIGH_CONFIDENCE_MATCH")
        probable_count = sum(1 for d in decisions if d.decision == "PROBABLE_MATCH")
        variant_count = sum(1 for d in decisions if d.decision == "VARIANT")
        related_count = sum(1 for d in decisions if d.decision == "RELATED_PRODUCT")
        no_match_count = sum(1 for d in decisions if d.decision == "NO_MATCH")

        llm_count = sum(1 for d in decisions if d.llm_used)
        mem_count = sum(1 for d in decisions if "memory" in d.match_method)
        avg_conf = round(sum(d.confidence for d in decisions) / total, 2) if total > 0 else 0.0

        return {
            "total_evaluations": total,
            "exact_matches": exact_count,
            "high_confidence_matches": high_count,
            "probable_matches": probable_count,
            "variants_detected": variant_count,
            "related_products": related_count,
            "no_matches": no_match_count,
            "review_queue_count": len(candidates),
            "deterministic_match_rate": round((total - llm_count) / max(1, total), 2),
            "llm_match_rate": round(llm_count / max(1, total), 2),
            "memory_hit_count": mem_count,
            "average_confidence": avg_conf
        }
