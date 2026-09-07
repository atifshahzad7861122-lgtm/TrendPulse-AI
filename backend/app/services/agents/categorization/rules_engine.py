import re
from typing import Dict, Any, List, Optional, Tuple

from backend.app.domain.taxonomy import CENTRAL_TAXONOMY_TREE, INITIAL_TOP_LEVEL_CATEGORIES

# Known Brand Mappings & Default Categories
KNOWN_BRANDS: Dict[str, Dict[str, Any]] = {
    "apple": {
        "canonical": "Apple",
        "default_category": "Electronics",
        "default_subcategory": "Mobile Accessories",
        "regex": r"\b(apple|airpods|iphone|ipad|macbook|iwatch)\b"
    },
    "sony": {
        "canonical": "Sony",
        "default_category": "Electronics",
        "default_subcategory": "Audio",
        "regex": r"\b(sony|wh-1000xm|wf-1000xm|playstation|ps5|bravia)\b"
    },
    "samsung": {
        "canonical": "Samsung",
        "default_category": "Electronics",
        "default_subcategory": "Mobile Accessories",
        "regex": r"\b(samsung|galaxy|galaxy buds|exynos)\b"
    },
    "logitech": {
        "canonical": "Logitech",
        "default_category": "Electronics",
        "default_subcategory": "Computer Accessories",
        "regex": r"\b(logitech|logi|mx master|g pro|lightspeed)\b"
    },
    "anker": {
        "canonical": "Anker",
        "default_category": "Electronics",
        "default_subcategory": "Mobile Accessories",
        "regex": r"\b(anker|soundcore|eufy|powercore|powerdrive)\b"
    },
    "zero": {
        "canonical": "Zero",
        "default_category": "Electronics",
        "default_subcategory": "Audio",
        "regex": r"\b(zero lifestyle|zero earbuds|zero audio)\b"
    },
    "xiaomi": {
        "canonical": "Xiaomi",
        "default_category": "Electronics",
        "default_subcategory": "Mobile Accessories",
        "regex": r"\b(xiaomi|redmi|mi band|poco)\b"
    },
    "nike": {
        "canonical": "Nike",
        "default_category": "Fashion",
        "default_subcategory": "Footwear",
        "regex": r"\b(nike|air force|air max|dri-fit|jordan)\b"
    },
    "adidas": {
        "canonical": "Adidas",
        "default_category": "Fashion",
        "default_subcategory": "Footwear",
        "regex": r"\b(adidas|ultraboost|stan smith|yeezy|climalite)\b"
    },
    "titanflex": {
        "canonical": "TitanFlex",
        "default_category": "Sports & Fitness",
        "default_subcategory": "Running & Outdoor",
        "regex": r"\b(titanflex|titan flex)\b"
    },
    "ordinary": {
        "canonical": "The Ordinary",
        "default_category": "Beauty & Personal Care",
        "default_subcategory": "Skincare",
        "regex": r"\b(the ordinary|deciem)\b"
    },
    "cerave": {
        "canonical": "CeraVe",
        "default_category": "Beauty & Personal Care",
        "default_subcategory": "Skincare",
        "regex": r"\b(cerave|moisturizing cream)\b"
    },
    "cosrx": {
        "canonical": "COSRX",
        "default_category": "Beauty & Personal Care",
        "default_subcategory": "Skincare",
        "regex": r"\b(cosrx|snail mucin)\b"
    }
}

# Exact Marketplace Category Normalization Lookup
EXACT_MARKETPLACE_CATEGORY_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # Daraz Category Paths
    "mobiles & tablets > mobile accessories > headphones": {
        "category": "Electronics",
        "subcategory": "Audio",
        "product_type": "Wireless Earbuds",
        "taxonomy_path": ["Electronics", "Audio", "Headphones & Earbuds", "Wireless Earbuds"]
    },
    "audio > headphones & headsets > wireless earbuds": {
        "category": "Electronics",
        "subcategory": "Audio",
        "product_type": "Wireless Earbuds",
        "taxonomy_path": ["Electronics", "Audio", "Headphones & Earbuds", "Wireless Earbuds"]
    },
    "computers & laptops > computer accessories > keyboards": {
        "category": "Electronics",
        "subcategory": "Computer Accessories",
        "product_type": "Gaming Keyboard",
        "taxonomy_path": ["Electronics", "Computer Accessories", "Keyboards & Mice", "Gaming Keyboard"]
    },
    "men's fashion > clothing > t-shirts": {
        "category": "Fashion",
        "subcategory": "Men's Clothing",
        "product_type": "T-Shirts",
        "taxonomy_path": ["Fashion", "Men's Clothing", "Tops", "T-Shirts"]
    },
    "women's fashion > clothing > dresses": {
        "category": "Fashion",
        "subcategory": "Women's Clothing",
        "product_type": "Dresses",
        "taxonomy_path": ["Fashion", "Women's Clothing", "Dresses & Suits", "Dresses"]
    },
    "beauty & personal care > skin care > face serums": {
        "category": "Beauty & Personal Care",
        "subcategory": "Skincare",
        "product_type": "Face Serum",
        "taxonomy_path": ["Beauty & Personal Care", "Skincare", "Face Treatments", "Face Serum"]
    },
    "sports & outdoors > running > hydration packs": {
        "category": "Sports & Fitness",
        "subcategory": "Running & Outdoor",
        "product_type": "Hydration Vests & Packs",
        "taxonomy_path": ["Sports & Fitness", "Running & Outdoor", "Packs & Hydration", "Hydration Vests & Packs"]
    },
    "kitchen & dining > coffee & tea > matcha tools": {
        "category": "Home & Living",
        "subcategory": "Kitchen & Dining",
        "product_type": "Tea & Coffee Accessories",
        "taxonomy_path": ["Home & Living", "Kitchen & Dining", "Beverage Prep", "Tea & Coffee Accessories"]
    },

    # Shopify Product Types / Collections
    "electronics / audio": {
        "category": "Electronics",
        "subcategory": "Audio",
        "product_type": "Wireless Earbuds",
        "taxonomy_path": ["Electronics", "Audio", "Headphones & Earbuds", "Wireless Earbuds"]
    },
    "apparel / streetwear": {
        "category": "Fashion",
        "subcategory": "Men's Clothing",
        "product_type": "Hoodies & Sweatshirts",
        "taxonomy_path": ["Fashion", "Men's Clothing", "Outerwear", "Hoodies & Sweatshirts"]
    },
    "skincare / serums": {
        "category": "Beauty & Personal Care",
        "subcategory": "Skincare",
        "product_type": "Face Serum",
        "taxonomy_path": ["Beauty & Personal Care", "Skincare", "Face Treatments", "Face Serum"]
    },
    "fitness / gear": {
        "category": "Sports & Fitness",
        "subcategory": "Running & Outdoor",
        "product_type": "Hydration Vests & Packs",
        "taxonomy_path": ["Sports & Fitness", "Running & Outdoor", "Packs & Hydration", "Hydration Vests & Packs"]
    },
    "home / kitchenware": {
        "category": "Home & Living",
        "subcategory": "Kitchen & Dining",
        "product_type": "Tea & Coffee Accessories",
        "taxonomy_path": ["Home & Living", "Kitchen & Dining", "Beverage Prep", "Tea & Coffee Accessories"]
    }
}

class DeterministicTaxonomyEngine:
    """
    Deterministic rule and pattern matching engine for Agent 2.
    Evaluates brand identity, marketplace categories, token keyword sets,
    and regex patterns to classify products with high confidence before Gemini.
    """

    def __init__(self):
        self.taxonomy_tree = CENTRAL_TAXONOMY_TREE

    def extract_brand(self, title: str, raw_brand: Optional[str] = None) -> Optional[str]:
        """
        Identifies and normalizes brand name from title or source payload.
        """
        if raw_brand and raw_brand.strip().lower() not in ["", "generic", "no brand", "none", "unknown", "n/a", "other"]:
            raw_clean = raw_brand.strip()
            # Normalize known brands
            for k, meta in KNOWN_BRANDS.items():
                if k in raw_clean.lower():
                    return meta["canonical"]
            return raw_clean

        title_lower = title.lower()
        for k, meta in KNOWN_BRANDS.items():
            if re.search(meta["regex"], title_lower):
                return meta["canonical"]

        # Regex heuristic: extract leading capitalized word (e.g. "Anker 20W Charger" -> "Anker")
        match = re.match(r"^([A-Z][a-zA-Z0-9\+\-]+)\s+", title)
        if match:
            candidate = match.group(1)
            if candidate.lower() not in ["new", "best", "hot", "top", "mini", "smart", "pro", "ultra", "super", "wireless", "portable", "men", "women"]:
                return candidate

        return None

    def extract_attributes(self, text: str) -> Dict[str, Any]:
        """
        Extracts structured product specifications & attributes via deterministic regex.
        """
        attrs: Dict[str, Any] = {}
        t_low = text.lower()

        # Driver Size (e.g., 10mm, 12mm, 14.2mm)
        driver_match = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*(?:driver|dynamic|speaker)?", t_low)
        if driver_match and "driver" in t_low:
            attrs["driver_size"] = f"{driver_match.group(1)}mm"

        # Battery / Battery Capacity (e.g., 5000mAh, 10000mAh, 400mAh)
        battery_match = re.search(r"(\d+)\s*mah", t_low)
        if battery_match:
            attrs["battery_capacity"] = f"{battery_match.group(1)}mAh"

        # Storage / RAM (e.g., 128GB, 256GB, 8GB RAM, 16GB)
        ram_match = re.search(r"\b(\d+)\s*(?:gb|tb)\s*ram\b", t_low)
        if ram_match:
            attrs["ram"] = f"{ram_match.group(1)}GB"

        storage_match = re.search(r"\b(\d+)\s*(?:gb|tb)\s*(?:ssd|hdd|rom|storage|nvme)\b", t_low)
        if storage_match:
            unit = "TB" if "tb" in storage_match.group(0) else "GB"
            attrs["storage"] = f"{storage_match.group(1)}{unit}"
        elif not ram_match:
            gen_storage = re.search(r"\b(\d+)\s*(gb|tb)\b", t_low)
            if gen_storage:
                attrs["storage"] = f"{gen_storage.group(1)}{gen_storage.group(2).upper()}"

        # Connectivity (e.g., Bluetooth 5.3, 2.4G, Type-C, USB-C, MagSafe)
        if "bluetooth" in t_low or "bt 5." in t_low:
            bt_match = re.search(r"(?:bluetooth|bt)\s*(\d+(?:\.\d+)?)", t_low)
            attrs["connectivity"] = f"Bluetooth {bt_match.group(1)}" if bt_match else "Bluetooth"
        elif "2.4g" in t_low:
            attrs["connectivity"] = "2.4GHz Wireless"
        elif "usb-c" in t_low or "type-c" in t_low:
            attrs["interface"] = "USB-C"

        # Color extraction: multi-word phrases first
        colors = ["matte black", "rose gold", "space grey", "space gray", "midnight blue", "black", "white", "blue", "red", "green", "silver", "gold", "pink", "purple", "grey", "gray"]
        for c in colors:
            if re.search(rf"\b{c}\b", t_low):
                attrs["color"] = c.title()
                break


        # Size extraction (e.g., XS, S, M, L, XL, XXL)
        size_match = re.search(r"\b(size\s*:?\s*)?(xs|s|m|l|xl|xxl|xxxl)\b", t_low)
        if size_match:
            attrs["size"] = size_match.group(2).upper()

        # Material extraction
        materials = ["cotton", "fleece", "leather", "silicone", "denim", "stainless steel", "titanium", "aluminum", "nylon", "ceramic"]
        for m in materials:
            if re.search(rf"\b{m}\b", t_low):
                attrs["material"] = m.title()
                break

        # Gender / Target Audience
        if re.search(r"\b(men|man|male|gentlemen)\b", t_low):
            attrs["gender"] = "Men"
        elif re.search(r"\b(women|woman|female|ladies)\b", t_low):
            attrs["gender"] = "Women"
        elif re.search(r"\b(unisex|all genders)\b", t_low):
            attrs["gender"] = "Unisex"
        elif re.search(r"\b(kids|baby|toddler|children)\b", t_low):
            attrs["age_group"] = "Kids"

        return attrs

    def classify_deterministic(
        self,
        product_name: str,
        description: str = "",
        original_category: Optional[str] = None,
        brand_raw: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[Optional[Dict[str, Any]], float, str]:
        """
        Executes strict deterministic classification.
        Returns:
            (classification_dict, confidence, method_name)
        """
        combined_text = f"{product_name} {description} {' '.join(tags or [])}".strip()
        cleaned_text = re.sub(r"[^\w\s-]", " ", combined_text.lower())
        tokens = set(cleaned_text.split())

        # 1. Exact Marketplace Category Mapping
        if original_category:
            norm_cat_key = original_category.strip().lower().replace(" / ", " > ").replace(" /", " > ").replace("/ ", " > ")
            norm_cat_key_std = original_category.strip().lower()
            if norm_cat_key in EXACT_MARKETPLACE_CATEGORY_MAPPINGS:
                m = EXACT_MARKETPLACE_CATEGORY_MAPPINGS[norm_cat_key]
                return m, 0.98, "exact_marketplace_map"
            if norm_cat_key_std in EXACT_MARKETPLACE_CATEGORY_MAPPINGS:
                m = EXACT_MARKETPLACE_CATEGORY_MAPPINGS[norm_cat_key_std]
                return m, 0.98, "exact_marketplace_map"

        # 2. Keyword & Token Scoring across Central Taxonomy Tree
        best_candidate: Optional[Dict[str, Any]] = None
        best_score = 0
        second_best_score = 0

        for cat_node in self.taxonomy_tree:
            cat_name = cat_node["name"]
            if cat_name in ["Other", "Unknown"]:
                continue

            for sub_node in cat_node.get("subcategories", []):
                sub_name = sub_node["name"]
                for p_type in sub_node.get("product_types", []):
                    pt_name = p_type["name"]
                    keywords = p_type.get("keywords", [])
                    score = 0

                    for kw in keywords:
                        kw_lower = kw.lower()
                        if " " in kw_lower:
                            if kw_lower in cleaned_text:
                                score += 3  # Multi-word exact match
                        else:
                            if kw_lower in tokens:
                                score += 2  # Single token exact match
                            elif kw_lower in cleaned_text:
                                score += 1

                    if score > best_score:
                        second_best_score = best_score
                        best_score = score
                        best_candidate = {
                            "category": cat_name,
                            "subcategory": sub_name,
                            "product_type": pt_name,
                            "taxonomy_path": p_type.get("path", [cat_name, sub_name, pt_name])
                        }
                    elif score > second_best_score:
                        second_best_score = score

        # 3. Known Brand Fallback
        extracted_brand = self.extract_brand(product_name, brand_raw)
        if best_candidate and best_score >= 3:
            # High confidence deterministic match
            confidence = 0.95 if best_score >= 5 else 0.85
            return best_candidate, confidence, "keyword_rule"

        if extracted_brand:
            for k, meta in KNOWN_BRANDS.items():
                if meta["canonical"].lower() == extracted_brand.lower():
                    if best_candidate and best_score >= 2:
                        return best_candidate, 0.88, "brand_rule"
                    # Default category from brand
                    return {
                        "category": meta["default_category"],
                        "subcategory": meta["default_subcategory"],
                        "product_type": best_candidate["product_type"] if best_candidate else "Standard Product",
                        "taxonomy_path": [meta["default_category"], meta["default_subcategory"]]
                    }, 0.76, "brand_rule"

        if best_candidate and best_score >= 2:
            return best_candidate, 0.70, "keyword_rule"

        return None, 0.0, "unknown"
