import re
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.app.models.domain import ProductSignature

class ProductSignatureBuilder:
    """
    Constructs deterministic, noise-free product signatures for high-precision entity resolution.
    Strips promotional fluff, normalizes brand & model tokens, and extracts key physical specs.
    """

    PROMOTIONAL_NOISE_TERMS: List[str] = [
        "free shipping", "100% original", "100% genuine", "official store", "official",
        "best seller", "bestseller", "limited edition", "new arrival", "flash sale",
        "top rated", "authentic", "genuine", "promo", "daraz", "shopify", "super deal",
        "cod", "cash on delivery", "discount", "sale", "special offer", "hot sale",
        "original", "free delivery", "best price", "high quality", "premium quality",
        "fast delivery", "warranty", "brand new", "ready stock", "hot selling", "clearance"
    ]

    BRAND_ALIASES: Dict[str, str] = {
        "zero lifestyle": "zero",
        "zero-lifestyle": "zero",
        "apple inc": "apple",
        "apple inc.": "apple",
        "samsung electronics": "samsung",
        "sony corp": "sony",
        "sony corporation": "sony",
        "logitech g": "logitech",
        "anker innovations": "anker",
        "soundcore by anker": "soundcore",
        "xiaomi mi": "xiaomi",
        "redmi by xiaomi": "redmi",
        "nike sportswear": "nike",
        "adidas originals": "adidas",
        "the ordinary co": "the ordinary",
        "cerave skincare": "cerave",
        "l'oreal paris": "l'oreal",
        "loreal": "l'oreal",
    }

    COLOR_TERMS: Set[str] = {
        "black", "white", "midnight blue", "midnight", "space gray", "space grey",
        "silver", "gold", "rose gold", "titanium", "natural titanium", "desert titanium",
        "red", "blue", "green", "purple", "pink", "yellow", "orange", "grey", "gray",
        "matte black", "glossy black", "navy blue", "cyan", "beige", "brown"
    }

    @classmethod
    def clean_title(cls, title: str) -> str:
        """Removes promotional noise, emojis, and extraneous punctuation from title."""
        if not title:
            return ""
        t = title.strip()
        t_lower = t.lower()

        # Remove promo phrases
        for term in cls.PROMOTIONAL_NOISE_TERMS:
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            t = pattern.sub(" ", t)

        # Remove common brackets/tags like [Brand New] or (Free Gift)
        t = re.sub(r"\[.*?\]|\(.*?\)", " ", t)

        # Remove special noise characters except hyphens and dots in numbers
        t = re.sub(r"[^\w\s\-\.\/\+]", " ", t)

        # Collapse whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @classmethod
    def normalize_brand(cls, brand_raw: Optional[str], title: Optional[str] = "") -> Optional[str]:
        """Normalizes brand string and resolves common marketplace aliases."""
        if brand_raw and str(brand_raw).strip() and str(brand_raw).strip().lower() not in ["generic", "no brand", "unknown", "n/a", "none"]:
            b_norm = str(brand_raw).strip().lower()
            if b_norm in cls.BRAND_ALIASES:
                return cls.BRAND_ALIASES[b_norm].title()
            return str(brand_raw).strip().title()

        # Try to infer brand from the beginning of the title
        t_words = str(title or "").strip().split()
        if t_words:
            first_two = " ".join(t_words[:2]).lower()
            first_one = t_words[0].lower()
            if first_two in cls.BRAND_ALIASES:
                return cls.BRAND_ALIASES[first_two].title()
            if first_one in cls.BRAND_ALIASES:
                return cls.BRAND_ALIASES[first_one].title()

        return str(brand_raw).strip().title() if brand_raw and str(brand_raw).strip() else None

    @classmethod
    def extract_attributes(cls, text: str) -> Dict[str, Any]:
        """Extracts structured key attributes (storage, ram, color, battery, connectivity, size)."""
        attrs: Dict[str, Any] = {}
        t_low = text.lower()

        # Storage (e.g. 128GB, 256GB, 512GB, 1TB)
        storage_match = re.search(r"\b(\d+)\s*(?:gb|tb)\s*(?:ssd|storage|rom|nvme)?\b(?!\s*ram)", t_low)
        if storage_match:
            val = storage_match.group(1)
            unit = "TB" if "tb" in storage_match.group(0).lower() else "GB"
            attrs["storage"] = f"{val}{unit}"

        # RAM (e.g. 8GB RAM, 16GB RAM, 8GB/256GB)
        ram_match = re.search(r"\b(\d+)\s*(?:gb|tb)\s*ram\b", t_low)
        if ram_match:
            attrs["ram"] = f"{ram_match.group(1)}GB"
        else:
            # Check pattern like 8GB/128GB or 8+128GB
            dual_match = re.search(r"\b(\d+)\s*gb\s*[\/\+]\s*(\d+)\s*(?:gb|tb)\b", t_low)
            if dual_match:
                attrs["ram"] = f"{dual_match.group(1)}GB"
                attrs["storage"] = f"{dual_match.group(2)}GB"

        # Battery (e.g. 5000mAh, 4500 mAh)
        bat_match = re.search(r"\b(\d+)\s*mah\b", t_low)
        if bat_match:
            attrs["battery"] = f"{bat_match.group(1)}mAh"

        # Colors
        for color in sorted(cls.COLOR_TERMS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(color)}\b", t_low):
                attrs["color"] = color.title()
                break

        # Connectivity
        if "wireless" in t_low or "bluetooth" in t_low or "tws" in t_low:
            attrs["connectivity"] = "Wireless"
        elif "wired" in t_low:
            attrs["connectivity"] = "Wired"

        # Size (e.g. S, M, L, XL, XXL)
        size_match = re.search(r"\b(?:size\s*[:\-]?\s*|(?<=\s))(xxl|xl|l|m|s|xs)\b", t_low)
        if size_match:
            attrs["size"] = size_match.group(1).upper()

        return attrs

    @classmethod
    def extract_model(cls, title: str, brand: Optional[str] = None) -> Optional[str]:
        """Extracts product model series/code (e.g., 'WH-1000XM5', 'AirPods Pro 2', 'iPhone 16 Pro Max', 'G502 Hero')."""
        t = cls.clean_title(title)
        if not t:
            return None

        # Regex for common electronic model patterns (letters + digits + hyphens, e.g. WH-1000XM5, RTX-4070, SM-G998B, Z-Buds)
        model_code_match = re.search(r"\b([A-Za-z]{1,4}[\-_]?\d{2,5}[A-Za-z0-9\-_]*)\b", t)
        if model_code_match:
            cand = model_code_match.group(1).strip("-").strip("_")
            if len(cand) >= 3 and not cand.lower().endswith("mah") and not cand.lower().endswith("gb") and not cand.lower().endswith("tb"):
                return cand.upper()

        # Specific known product line patterns
        patterns = [
            r"\b(airpods\s+pro\s*(?:2|gen\s*2|2nd\s*gen)?)\b",
            r"\b(airpods\s*(?:3|4|max|pro)?)\b",
            r"\b(iphone\s*\d{1,2}\s*(?:pro\s*max|pro|plus|mini)?)\b",
            r"\b(galaxy\s*s\d{2}\s*(?:ultra|plus|\+)?)\b",
            r"\b(galaxy\s*z\s*(?:fold|flip)\s*\d?)\b",
            r"\b(pixel\s*\d\s*(?:pro|a)?)\b",
            r"\b(wh-?1000xm[45])\b",
            r"\b(wf-?1000xm[45])\b",
            r"\b(g\d{3}\s*(?:hero|lightspeed|x)?)\b",
            r"\b(evo\s*(?:pro|plus)?)\b",
            r"\b(z-?buds\s*(?:pro)?)\b"
        ]

        for p in patterns:
            m = re.search(p, t, re.IGNORECASE)
            if m:
                return m.group(1).title()

        return None

    @classmethod
    def build_signature(cls, item: Dict[str, Any]) -> ProductSignature:
        """
        Builds a structured, deterministic ProductSignature for matching.
        """
        raw_title = str(item.get("product_name") or item.get("title") or item.get("canonical_name") or item.get("name") or "").strip()
        cleaned_title = cls.clean_title(raw_title)
        raw_brand = item.get("brand") or item.get("vendor")
        brand = cls.normalize_brand(raw_brand, raw_title)

        raw_ids = item.get("identifiers") or {}
        model = str(item.get("model_number") or raw_ids.get("model_number") or item.get("model") or "").strip() or cls.extract_model(raw_title, brand)
        product_type = item.get("product_type") or item.get("normalized_product_type")
        category = item.get("category")
        subcategory = item.get("subcategory")

        # Extract attributes from title + description + passed attributes
        desc = str(item.get("description") or "")
        extracted_attrs = cls.extract_attributes(f"{raw_title} {desc}")
        passed_attrs = item.get("attributes") or {}
        combined_attrs = {**extracted_attrs, **passed_attrs}

        # Collect global identifiers
        raw_ids = item.get("identifiers") or {}
        ids: Dict[str, str] = {}
        for k in ["sku", "gtin", "upc", "ean", "asin", "mpn", "barcode", "model_number"]:
            val = str(item.get(k) or raw_ids.get(k) or "").strip().upper()
            if val and val not in ["NONE", "NULL", "UNKNOWN", "N/A", "0"]:
                ids[k] = val

        # Clean tokens
        tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", cleaned_title) if len(t) > 1]

        # Signature hash
        sig_str = f"{brand or ''}|{model or ''}|{product_type or ''}|{' '.join(sorted(tokens[:8]))}|{combined_attrs.get('storage', '')}|{combined_attrs.get('ram', '')}"
        sig_hash = hashlib.sha256(sig_str.encode("utf-8")).hexdigest()

        return ProductSignature(
            brand=brand,
            model=model,
            product_type=product_type,
            category=category,
            subcategory=subcategory,
            currency=item.get("currency"),
            normalized_title=cleaned_title,
            cleaned_tokens=tokens,
            key_attributes=combined_attrs,
            identifiers=ids,
            signature_hash=sig_hash
        )
