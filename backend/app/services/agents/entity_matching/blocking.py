from typing import List, Dict, Any, Set, Optional, Tuple
from backend.app.models.domain import ProductSignature, UnifiedProduct

class CandidateBlocker:
    """
    High-performance candidate blocking indexer for entity resolution.
    Generates deterministic partition keys to restrict comparison space from O(N^2) to O(k).
    """

    @classmethod
    def get_blocking_keys(cls, sig: ProductSignature) -> Set[str]:
        """
        Extracts multi-tier blocking keys from a product signature.
        """
        keys: Set[str] = set()

        # 1. Global Identifier Blocking Keys
        for id_type, id_val in sig.identifiers.items():
            if id_val and len(id_val) >= 4:
                keys.add(f"id:{id_type.lower()}:{id_val.upper()}")

        # 2. Brand + Model Blocking Key
        if sig.brand and sig.model:
            b = sig.brand.strip().lower()
            m = sig.model.strip().lower()
            keys.add(f"bm:{b}:{m}")

        # 3. Brand + Product Type Key
        if sig.brand and sig.product_type:
            b = sig.brand.strip().lower()
            pt = sig.product_type.strip().lower()
            keys.add(f"bpt:{b}:{pt}")

        # 4. Brand + Core Tokens
        if sig.brand and sig.cleaned_tokens:
            b = sig.brand.strip().lower()
            # Top 3 most informative tokens (length > 3, excluding brand)
            meaningful_tokens = [t for t in sig.cleaned_tokens if len(t) >= 3 and t != b][:3]
            for tok in meaningful_tokens:
                keys.add(f"bt:{b}:{tok}")

        # 5. Fallback: Core token pairs
        if len(sig.cleaned_tokens) >= 2:
            meaningful = [t for t in sig.cleaned_tokens if len(t) >= 4][:3]
            if len(meaningful) >= 2:
                pair = f"tp:{meaningful[0]}:{meaningful[1]}"
                keys.add(pair)

        return keys

    @classmethod
    def score_candidate_relevance(
        cls,
        target_sig: ProductSignature,
        candidate: Any
    ) -> float:
        """
        Computes a fast heuristic relevance score (0.0 to 1.0) between target signature and candidate.
        """
        score = 0.0
        cand_ids = getattr(candidate, "identifiers", {}) if not isinstance(candidate, dict) else candidate.get("identifiers", {})
        cand_brand = getattr(candidate, "brand", None) if not isinstance(candidate, dict) else candidate.get("brand")
        cand_name = getattr(candidate, "canonical_name", "") if not isinstance(candidate, dict) else candidate.get("canonical_name", "")

        # 1. Global Identifier Direct Hit
        for k in ["sku", "gtin", "upc", "ean", "asin", "mpn", "model_number"]:
            t_id = target_sig.identifiers.get(k)
            c_id = str(cand_ids.get(k) or "").strip().upper()
            if t_id and c_id and t_id == c_id:
                return 1.0

        # 2. Brand Match
        b1 = (target_sig.brand or "").strip().lower()
        b2 = (cand_brand or "").strip().lower()
        if b1 and b2:
            if b1 == b2:
                score += 0.40
            else:
                # Brand mismatch penalty
                return 0.0

        # 3. Model Match
        m1 = (target_sig.model or "").strip().lower()
        m2 = str(cand_ids.get("model_number") or "").strip().lower()
        if m1 and m2 and m1 == m2:
            score += 0.40

        # 4. Token Overlap
        cand_tokens = set(cand_name.lower().split())
        target_tokens = set(target_sig.cleaned_tokens)
        if target_tokens and cand_tokens:
            overlap = len(target_tokens.intersection(cand_tokens)) / max(1, min(len(target_tokens), len(cand_tokens)))
            score += 0.20 * overlap

        return min(1.0, score)

    @classmethod
    def filter_candidates(
        cls,
        target_sig: ProductSignature,
        candidate_pool: List[Any],
        max_candidates: int = 50
    ) -> List[Any]:
        """
        Filters and ranks candidate UnifiedProducts from the catalog.
        """
        if not candidate_pool:
            return []

        scored_candidates: List[Tuple[float, Any]] = []

        for cand in candidate_pool:
            # Check brand compatibility
            b_target = str(target_sig.brand or "").strip().lower()
            raw_b = getattr(cand, "brand", None) if not isinstance(cand, dict) else cand.get("brand")
            b_cand = str(raw_b or "").strip().lower()
            if b_target and b_cand and b_target != b_cand:
                # Different brands never share entity
                continue

            rel_score = cls.score_candidate_relevance(target_sig, cand)
            if rel_score > 0.15:
                scored_candidates.append((rel_score, cand))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_candidates[:max_candidates]]
