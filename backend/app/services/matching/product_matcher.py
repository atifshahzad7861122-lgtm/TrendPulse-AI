from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

class MatchDecision(BaseModel):
    """Result of deterministic product matching evaluation."""
    is_match: bool = Field(..., description="Whether the products are considered the same entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence score")
    method: str = Field(..., description="Matching rule/algorithm utilized")
    status: str = Field(..., description="matched, probable, or rejected")
    candidate_id: Optional[str] = None
    reasons: List[str] = Field(default_factory=list, description="Audit explanations for the decision")

class ProductMatcher:
    """
    Deterministic matching engine executing tiered cross-platform product entity resolution:
      1. Exact SKU/UPC/EAN/GTIN/ASIN Match -> Confidence = 1.0 (Auto-match)
      2. Brand + Model exact match -> Confidence >= 0.95 (Auto-match)
      3. Brand exact match + High Token Similarity (Jaccard + Token Overlap >= 0.85) -> Confidence 0.85-0.95
      4. Moderate Token Similarity (0.80 - 0.94) -> Probable candidate
      5. Low similarity (< 0.80) or mismatched brands -> Separate entity
    """

    @classmethod
    def _jaccard_similarity(cls, tokens1: Set[str], tokens2: Set[str]) -> float:
        if not tokens1 or not tokens2:
            return 0.0
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def _overlap_coefficient(cls, tokens1: Set[str], tokens2: Set[str]) -> float:
        if not tokens1 or not tokens2:
            return 0.0
        intersection = len(tokens1.intersection(tokens2))
        min_len = min(len(tokens1), len(tokens2))
        return intersection / min_len if min_len > 0 else 0.0

    @classmethod
    def evaluate_match(
        cls,
        item_norm: Dict[str, Any],
        candidate_norm: Dict[str, Any],
        item_identifiers: Optional[Dict[str, Any]] = None,
        candidate_identifiers: Optional[Dict[str, Any]] = None
    ) -> MatchDecision:
        item_ids = item_identifiers or {}
        cand_ids = candidate_identifiers or {}

        # ----------------------------------------------------------------------
        # Tier 1: Exact Unique Global Identifiers (SKU, UPC, EAN, GTIN, MPN, ASIN)
        # ----------------------------------------------------------------------
        identifier_keys = ["sku", "upc", "ean", "gtin", "mpn", "asin", "barcode"]
        for k in identifier_keys:
            v1 = str(item_ids.get(k) or "").strip().upper()
            v2 = str(cand_ids.get(k) or "").strip().upper()
            if v1 and v2 and v1 == v2:
                return MatchDecision(
                    is_match=True,
                    confidence=1.0,
                    method=f"{k}_exact",
                    status="matched",
                    reasons=[f"Exact matching {k.upper()} identifier: '{v1}'"]
                )

        # ----------------------------------------------------------------------
        # Tier 2: Brand + Model Number Exact Match
        # ----------------------------------------------------------------------
        b1 = str(item_norm.get("brand") or "").strip().lower()
        b2 = str(candidate_norm.get("brand") or "").strip().lower()
        m1 = str(item_norm.get("model_number") or "").strip().upper()
        m2 = str(candidate_norm.get("model_number") or "").strip().upper()

        if b1 and b2 and b1 == b2 and m1 and m2 and m1 == m2:
            return MatchDecision(
                is_match=True,
                confidence=0.98,
                method="brand_model_exact",
                status="matched",
                reasons=[f"Matching brand '{b1.title()}' and model number '{m1}'"]
            )

        # If brands are explicitly known and conflicting, reject immediately
        if b1 and b2 and b1 != b2:
            return MatchDecision(
                is_match=False,
                confidence=0.10,
                method="brand_mismatch",
                status="rejected",
                reasons=[f"Conflicting brands: '{b1.title()}' vs '{b2.title()}'"]
            )

        # ----------------------------------------------------------------------
        # Tier 3: Token Similarity & Overlap Analysis
        # ----------------------------------------------------------------------
        tokens1 = item_norm.get("tokens", set())
        tokens2 = candidate_norm.get("tokens", set())

        jaccard = cls._jaccard_similarity(tokens1, tokens2)
        overlap = cls._overlap_coefficient(tokens1, tokens2)
        composite_score = round(0.5 * jaccard + 0.5 * overlap, 3)

        # Brand match bonus
        brand_matched = (b1 and b2 and b1 == b2) or (not b1 and not b2)
        if brand_matched and b1:
            composite_score = min(1.0, composite_score + 0.15)

        # Match Decision based on thresholds
        if composite_score >= 0.85 and brand_matched:
            return MatchDecision(
                is_match=True,
                confidence=composite_score,
                method="normalized_token_similarity",
                status="matched" if composite_score >= 0.95 else "probable",
                reasons=[
                    f"High token overlap ({round(overlap*100)}%) and Jaccard similarity ({round(jaccard*100)}%)",
                    f"Brand alignment: '{b1.title() if b1 else 'N/A'}'"
                ]
            )
        elif composite_score >= 0.75:
            return MatchDecision(
                is_match=False,
                confidence=composite_score,
                method="probable_token_overlap",
                status="probable",
                reasons=[f"Moderate token similarity score ({round(composite_score*100)}%)"]
            )
        else:
            return MatchDecision(
                is_match=False,
                confidence=composite_score,
                method="low_token_similarity",
                status="rejected",
                reasons=[f"Low similarity score ({round(composite_score*100)}%) below auto-match threshold"]
            )
