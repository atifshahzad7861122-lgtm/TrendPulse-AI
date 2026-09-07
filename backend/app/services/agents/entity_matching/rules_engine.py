import re
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.app.models.domain import ProductSignature, ProductMatchDecision

class DeterministicEntityMatcher:
    """
    7-Tier Deterministic Entity Resolution Engine with Variant Detection & False-Positive Guard.
    """

    # Incompatible product type pairs that should never merge
    INCOMPATIBLE_PRODUCT_TYPES = {
        ("keyboard", "mouse"),
        ("headphones", "earbuds"),
        ("laptop", "tablet"),
        ("t-shirt", "hoodie"),
        ("serum", "moisturizer"),
        ("smartwatch", "fitness tracker"),
        ("case", "phone"),
        ("charger", "cable"),
    }

    @classmethod
    def _jaccard_similarity(cls, tokens1: List[str], tokens2: List[str]) -> float:
        s1 = set(tokens1)
        s2 = set(tokens2)
        if not s1 or not s2:
            return 0.0
        intersection = len(s1.intersection(s2))
        union = len(s1.union(s2))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def _overlap_coefficient(cls, tokens1: List[str], tokens2: List[str]) -> float:
        s1 = set(tokens1)
        s2 = set(tokens2)
        if not s1 or not s2:
            return 0.0
        intersection = len(s1.intersection(s2))
        min_len = min(len(s1), len(s2))
        return intersection / min_len if min_len > 0 else 0.0

    @classmethod
    def check_hard_conflicts(
        cls,
        sig1: ProductSignature,
        sig2: ProductSignature
    ) -> Tuple[bool, List[str], str]:
        """
        Evaluates hard conflict rules to prevent false-positive merges.
        Returns: (has_hard_conflict, conflict_reasons, classification)
        """
        conflicts: List[str] = []

        # 1. Brand Hard Conflict
        b1 = (sig1.brand or "").strip().lower()
        b2 = (sig2.brand or "").strip().lower()
        if b1 and b2 and b1 != b2:
            conflicts.append(f"Conflicting brands: '{sig1.brand}' vs '{sig2.brand}'")
            return True, conflicts, "NO_MATCH"

        # 2. Global Identifier Conflict (e.g., different GTINs / ASINs)
        for id_key in ["gtin", "upc", "ean", "asin"]:
            v1 = sig1.identifiers.get(id_key)
            v2 = sig2.identifiers.get(id_key)
            if v1 and v2 and v1 != v2:
                conflicts.append(f"Conflicting {id_key.upper()} identifiers: '{v1}' vs '{v2}'")
                return True, conflicts, "NO_MATCH"

        # 3. Model Tier Hard Conflict (e.g., iPhone 16 vs iPhone 16 Pro, RTX 4070 vs RTX 4080)
        m1 = (sig1.model or "").strip().lower()
        m2 = (sig2.model or "").strip().lower()
        if m1 and m2 and m1 != m2:
            # Check if one is a 'Pro', 'Max', 'Ultra', 'Plus' upgrade of the other
            tier_suffixes = ["pro max", "pro", "max", "ultra", "plus", "+", "mini", "lite", "fe", "hero", "lightspeed"]
            is_tier_mismatch = any(
                (suffix in m1 and suffix not in m2) or (suffix in m2 and suffix not in m1)
                for suffix in tier_suffixes
            )
            # Check generation mismatch (e.g. XM4 vs XM5, Gen 2 vs Gen 3)
            gen_mismatch = False
            dig1 = re.findall(r"\d+", m1)
            dig2 = re.findall(r"\d+", m2)
            if dig1 and dig2 and dig1 != dig2:
                gen_mismatch = True

            if is_tier_mismatch or gen_mismatch:
                conflicts.append(f"Different product model/tier: '{sig1.model}' vs '{sig2.model}'")
                return True, conflicts, "RELATED_PRODUCT"

        # 4. Incompatible Product Types
        pt1 = (sig1.product_type or "").strip().lower()
        pt2 = (sig2.product_type or "").strip().lower()
        if pt1 and pt2 and pt1 != pt2:
            pair1 = (pt1, pt2)
            pair2 = (pt2, pt1)
            if pair1 in cls.INCOMPATIBLE_PRODUCT_TYPES or pair2 in cls.INCOMPATIBLE_PRODUCT_TYPES:
                conflicts.append(f"Incompatible product types: '{sig1.product_type}' vs '{sig2.product_type}'")
                return True, conflicts, "NO_MATCH"

        return False, [], ""

    @classmethod
    def evaluate_variant(
        cls,
        sig1: ProductSignature,
        sig2: ProductSignature
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Determines if two products are variants of the same base model (e.g. differing storage, RAM, or color).
        """
        # Base model or high name similarity must hold
        b1 = (sig1.brand or "").strip().lower()
        b2 = (sig2.brand or "").strip().lower()
        same_brand = (b1 and b2 and b1 == b2) or (not b1 and not b2)

        m1 = (sig1.model or "").strip().lower()
        m2 = (sig2.model or "").strip().lower()
        same_model = (m1 and m2 and m1 == m2)

        high_similarity = False
        if not same_model:
            toks1 = set(sig1.cleaned_tokens)
            toks2 = set(sig2.cleaned_tokens)
            if toks1 and toks2:
                overlap = len(toks1.intersection(toks2)) / max(1, min(len(toks1), len(toks2)))
                if overlap >= 0.65:
                    high_similarity = True

        if not (same_brand and (same_model or high_similarity)):
            return False, {}, []

        diff_attrs: Dict[str, Any] = {}
        reasons: List[str] = []

        # Check storage difference
        st1 = sig1.key_attributes.get("storage")
        st2 = sig2.key_attributes.get("storage")
        if st1 and st2 and st1.upper() != st2.upper():
            diff_attrs["storage"] = st2
            reasons.append(f"Storage variant: '{st1}' vs '{st2}'")


        # Check RAM difference
        ram1 = sig1.key_attributes.get("ram")
        ram2 = sig2.key_attributes.get("ram")
        if ram1 and ram2 and ram1.upper() != ram2.upper():
            diff_attrs["ram"] = ram2
            reasons.append(f"RAM variant: '{ram1}' vs '{ram2}'")

        # Check color difference
        col1 = sig1.key_attributes.get("color")
        col2 = sig2.key_attributes.get("color")
        if col1 and col2 and col1.lower() != col2.lower():
            diff_attrs["color"] = col2
            reasons.append(f"Color variant: '{col1}' vs '{col2}'")

        # Check size difference
        sz1 = sig1.key_attributes.get("size")
        sz2 = sig2.key_attributes.get("size")
        if sz1 and sz2 and sz1.upper() != sz2.upper():
            diff_attrs["size"] = sz2
            reasons.append(f"Size variant: '{sz1}' vs '{sz2}'")

        if diff_attrs:
            return True, diff_attrs, reasons

        return False, {}, []

    @classmethod
    def evaluate_pair(
        cls,
        sig1: ProductSignature,
        sig2: ProductSignature,
        product_a_id: str,
        product_b_id: str,
        platform_a: str = "unknown",
        platform_b: str = "unknown"
    ) -> ProductMatchDecision:
        """
        Executes full multi-tier deterministic matching evaluation.
        """
        # Step 0: Check Hard Conflicts (False-Positive Protection)
        has_conflict, conflicts, conflict_decision = cls.check_hard_conflicts(sig1, sig2)
        if has_conflict:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision=conflict_decision,
                confidence=0.10 if conflict_decision == "NO_MATCH" else 0.40,
                match_method="hard_conflict_guard",
                reasons=[],
                conflicts=conflicts,
                variant_attributes={}
            )

        # Step 1: Check Variant Detection
        is_variant, variant_attrs, variant_reasons = cls.evaluate_variant(sig1, sig2)
        if is_variant:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="VARIANT",
                confidence=0.96,
                match_method="variant_attribute_detection",
                reasons=[f"Same base product '{sig1.brand or ''} {sig1.model or ''}' with distinct variant attributes"] + variant_reasons,
                conflicts=[],
                variant_attributes=variant_attrs,
                base_product_id=product_b_id
            )

        # ----------------------------------------------------------------------
        # Tier 1: Exact SKU Match
        # ----------------------------------------------------------------------
        sku1 = sig1.identifiers.get("sku")
        sku2 = sig2.identifiers.get("sku")
        if sku1 and sku2 and sku1 == sku2:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="EXACT_MATCH",
                confidence=1.0,
                match_method="exact_sku",
                reasons=[f"Exact matching SKU identifier: '{sku1}'"]
            )

        # ----------------------------------------------------------------------
        # Tier 2: Exact GTIN / UPC / EAN Match
        # ----------------------------------------------------------------------
        for id_key in ["gtin", "upc", "ean", "mpn", "barcode"]:
            v1 = sig1.identifiers.get(id_key)
            v2 = sig2.identifiers.get(id_key)
            if v1 and v2 and v1 == v2:
                return ProductMatchDecision(
                    id=f"pmd_{product_a_id}_{product_b_id}",
                    product_a_id=product_a_id,
                    product_b_id=product_b_id,
                    platform_a=platform_a,
                    platform_b=platform_b,
                    decision="EXACT_MATCH",
                    confidence=1.0,
                    match_method=f"exact_{id_key}",
                    reasons=[f"Exact matching {id_key.upper()} barcode identifier: '{v1}'"]
                )

        # ----------------------------------------------------------------------
        # Tier 3: Exact ASIN Match
        # ----------------------------------------------------------------------
        asin1 = sig1.identifiers.get("asin")
        asin2 = sig2.identifiers.get("asin")
        if asin1 and asin2 and asin1 == asin2:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="EXACT_MATCH",
                confidence=1.0,
                match_method="exact_asin",
                reasons=[f"Exact matching ASIN identifier: '{asin1}'"]
            )

        # ----------------------------------------------------------------------
        # Tier 4: Exact Model Number + Brand Match
        # ----------------------------------------------------------------------
        b1 = (sig1.brand or "").strip().lower()
        b2 = (sig2.brand or "").strip().lower()
        m1 = (sig1.model or "").strip().lower()
        m2 = (sig2.model or "").strip().lower()

        if b1 and b2 and b1 == b2 and m1 and m2 and m1 == m2:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="HIGH_CONFIDENCE_MATCH",
                confidence=0.98,
                match_method="brand_model_exact",
                reasons=[f"Matching brand '{sig1.brand}' and model '{sig1.model}'"]
            )

        # ----------------------------------------------------------------------
        # Tier 5: Brand + High Title Similarity + Core Spec Match
        # ----------------------------------------------------------------------
        jaccard = cls._jaccard_similarity(sig1.cleaned_tokens, sig2.cleaned_tokens)
        overlap = cls._overlap_coefficient(sig1.cleaned_tokens, sig2.cleaned_tokens)
        composite_score = round(0.40 * jaccard + 0.60 * overlap, 3)

        brand_matched = (b1 and b2 and b1 == b2) or (not b1 and not b2)

        if brand_matched and b1:
            composite_score = min(0.98, composite_score + 0.15)

        # Attribute compatibility boost
        same_storage = sig1.key_attributes.get("storage") and sig1.key_attributes.get("storage") == sig2.key_attributes.get("storage")
        if same_storage:
            composite_score = min(0.98, composite_score + 0.05)

        # Decide based on thresholds
        if composite_score >= 0.95 and brand_matched:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="HIGH_CONFIDENCE_MATCH",
                confidence=composite_score,
                match_method="brand_title_spec_similarity",
                reasons=[
                    f"High token overlap ({round(overlap*100)}%) and Jaccard similarity ({round(jaccard*100)}%)",
                    f"Brand alignment: '{sig1.brand or 'N/A'}'"
                ]
            )
        elif composite_score >= 0.85 and brand_matched:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="PROBABLE_MATCH",
                confidence=composite_score,
                match_method="semantic_token_similarity",
                reasons=[f"Strong semantic token similarity ({round(composite_score*100)}%)"]
            )
        elif composite_score >= 0.75:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="NEEDS_REVIEW",
                confidence=composite_score,
                match_method="low_confidence_review_queue",
                reasons=[f"Moderate token similarity score ({round(composite_score*100)}%) requires review"]
            )
        else:
            return ProductMatchDecision(
                id=f"pmd_{product_a_id}_{product_b_id}",
                product_a_id=product_a_id,
                product_b_id=product_b_id,
                platform_a=platform_a,
                platform_b=platform_b,
                decision="NO_MATCH",
                confidence=composite_score,
                match_method="insufficient_similarity",
                reasons=[f"Low similarity score ({round(composite_score*100)}%) below match threshold"]
            )
