from typing import List, Optional, Tuple, Dict, Any
import re
from backend.app.models.domain import Product

STOP_WORDS = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of", "is", "it", "my", "your", "best", "top", "new", "2026", "review", "test"}

KNOWN_ALIASES: Dict[str, str] = {}

class MatchResult:
    def __init__(
        self,
        product: Optional[Product],
        confidence: float,
        match_type: str,  # "matched", "unmatched", "ambiguous"
        reason: str,
        matching_version: str = "2.4.0"
    ):
        self.product = product
        self.confidence = confidence
        self.match_type = match_type
        self.reason = reason
        self.matching_version = matching_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product.id if self.product else None,
            "product_name": self.product.name if self.product else None,
            "confidence": self.confidence,
            "match_type": self.match_type,
            "reason": self.reason,
            "matching_version": self.matching_version
        }

class ProductMatchingEngine:
    """
    Intelligence Agent: Deterministically matches external raw content (titles, tags, descriptions)
    to canonical catalog products using alias mapping, n-gram token overlap, tag intersection,
    and calibrated confidence gating.
    """

    MATCHING_VERSION = "2.4.0"

    @staticmethod
    def match_content_detailed(
        text: str,
        catalog_products: List[Product]
    ) -> MatchResult:
        if not text or not text.strip():
            return MatchResult(
                product=None,
                confidence=0.0,
                match_type="unmatched",
                reason="Empty input text."
            )

        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        raw_tokens = cleaned_text.split()
        meaningful_tokens = set(w for w in raw_tokens if w not in STOP_WORDS and len(w) > 1)

        # 1. Check for SKU or External ID exact matches
        for p in catalog_products:
            p_id_str = getattr(p, "id", "") or ""
            ext_id = getattr(p, "external_product_id", "") or ""
            if p_id_str and len(p_id_str) > 4 and p_id_str.lower() in cleaned_text:
                return MatchResult(
                    product=p,
                    confidence=0.99,
                    match_type="matched",
                    reason=f"Exact product identifier match for '{p_id_str}'"
                )
            if ext_id and len(ext_id) > 4 and ext_id.lower() in cleaned_text:
                return MatchResult(
                    product=p,
                    confidence=0.99,
                    match_type="matched",
                    reason=f"Exact external product ID match for '{ext_id}'"
                )

        # 2. Iterate catalog and calculate dynamic similarity weights
        candidate_scores: List[Tuple[Product, float, List[str]]] = []

        for p in catalog_products:
            score = 0.0
            reasons = []

            p_name = getattr(p, "name", None) or getattr(p, "title", "") or ""
            p_name_clean = re.sub(r'[^\w\s]', ' ', p_name.lower())
            
            # Exact full name substring
            if p_name_clean and len(p_name_clean) > 3 and p_name_clean in cleaned_text:
                return MatchResult(
                    product=p,
                    confidence=0.99,
                    match_type="matched",
                    reason=f"Exact canonical title match for '{p_name}'"
                )

            # Name token overlap
            p_tokens = set(w for w in p_name_clean.split() if w not in STOP_WORDS and len(w) > 1)
            overlap = p_tokens.intersection(meaningful_tokens)
            if overlap:
                overlap_ratio = len(overlap) / max(len(p_tokens), 1)
                score += overlap_ratio * 40.0
                reasons.append(f"Name tokens matched: {', '.join(overlap)}")
                
                # Multi-word continuous n-gram match
                if len(overlap) >= 2 and overlap_ratio >= 0.5:
                    score += 25.0
                    reasons.append(f"High multi-token correlation ({overlap_ratio * 100:.0f}%)")

            # Brand extraction and matching
            brand = getattr(p, "brand", None) or (p_name.split()[0] if p_name else None)
            if brand and len(brand) > 2:
                brand_clean = brand.lower().strip()
                if brand_clean not in STOP_WORDS and brand_clean in cleaned_text:
                    score += 20.0
                    reasons.append(f"Brand matched: '{brand}'")

            # Tags intersection
            p_tags = getattr(p, "tags", []) or []
            matched_tags = []
            for tag in p_tags:
                tag_clean = re.sub(r'[^\w\s]', ' ', tag.lower())
                tag_words = set(tag_clean.split())
                if tag_words.intersection(meaningful_tokens):
                    matched_tags.append(tag)
                    score += 15.0
            if matched_tags:
                reasons.append(f"Tags matched: {', '.join(matched_tags[:2])}")

            if score >= 30.0:
                candidate_scores.append((p, score, reasons))

        if not candidate_scores:
            return MatchResult(
                product=None,
                confidence=0.0,
                match_type="unmatched",
                reason="No candidate reached minimum confidence threshold (30.0)"
            )

        # Sort candidates by score descending
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        top_product, top_score, top_reasons = candidate_scores[0]
        confidence = round(min(top_score / 70.0, 0.96), 2)

        # Multi-candidate ambiguity detection
        if len(candidate_scores) > 1:
            second_product, second_score, _ = candidate_scores[1]
            if (top_score - second_score) < 15.0 and confidence < 0.80:
                return MatchResult(
                    product=top_product,
                    confidence=0.60,
                    match_type="ambiguous",
                    reason=f"Ambiguous match between '{top_product.name}' ({top_score:.0f}) and '{second_product.name}' ({second_score:.0f})"
                )

        # Calibrated Thresholds:
        # >= 0.75: matched
        # 0.50 - 0.74: ambiguous
        # < 0.50: unmatched
        if confidence >= 0.75:
            return MatchResult(
                product=top_product,
                confidence=confidence,
                match_type="matched",
                reason="; ".join(top_reasons)
            )
        elif confidence >= 0.50:
            return MatchResult(
                product=top_product,
                confidence=confidence,
                match_type="ambiguous",
                reason=f"Moderate match confidence ({confidence:.2f}): {'; '.join(top_reasons)}"
            )
        else:
            return MatchResult(
                product=None,
                confidence=confidence,
                match_type="unmatched",
                reason=f"Low confidence ({confidence:.2f}); rejected to prevent catalog contamination"
            )

    @staticmethod
    def match_content_to_product(
        text: str,
        catalog_products: List[Product]
    ) -> Optional[Product]:
        """Convenience method preserving backward compatibility."""
        result = ProductMatchingEngine.match_content_detailed(text, catalog_products)
        return result.product
