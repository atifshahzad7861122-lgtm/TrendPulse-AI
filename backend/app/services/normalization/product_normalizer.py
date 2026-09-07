import re
import unicodedata
from typing import Dict, Any, List, Optional, Set

# Promotional words to strip from normalized titles
PROMOTIONAL_PATTERNS = [
    r"\b100%\s*(original|authentic|genuine)\b",
    r"\b(official|brand|company)\s*warranty\b",
    r"\b(free|fast)\s*(delivery|shipping)\b",
    r"\bhot\s*sale\b",
    r"\bbest\s*seller\b",
    r"\blimited\s*edition\b",
    r"\bdiscount\s*offer\b",
    r"\b(top|best)\s*quality\b",
    r"\b(matte\s*black\s*edition)\b",
    r"\[object\s*Object\]",
]

# Common brand dictionary for extraction
KNOWN_BRANDS = [
    "anker", "audionic", "apple", "samsung", "xiaomi", "redmi", "realme", "infinix", "tecno",
    "huawei", "oppo", "vivo", "sony", "logitech", "lenovo", "dell", "hp", "asus", "acer",
    "gymshark", "nike", "adidas", "puma", "under armour", "zara", "h&m", "levis", "gucci",
    "zero", "zero lifestyle", "dany", "ronin", "faster", "space", "joyroom", "baseus", "ugreen",
    "boat", "noise", "fire-boltt", "amazfit", "haylou", "soundpeats", "qcy", "mivi", "truke"
]

class ProductNormalizer:
    """
    Standardizes marketplace product metadata across Daraz, Shopify, and other platforms.
    Handles Unicode NFKC normalization, whitespace/punctuation cleaning, brand formatting,
    unit standardization (e.g. 10mm, 64gb, 5000mah), and model number extraction.
    """

    @classmethod
    def clean_unicode(cls, text: str) -> str:
        """Converts Unicode characters to NFKC canonical form and removes non-printable chars."""
        if not text:
            return ""
        norm_text = unicodedata.normalize("NFKC", text)
        # Remove registered trademarks, copyright, special decorative symbols
        norm_text = re.sub(r"[®™©★☆✓✔•|/\\#@!]", " ", norm_text)
        return norm_text

    @classmethod
    def clean_promotional_noise(cls, text: str) -> str:
        """Strips generic promotional fluff and badges."""
        cleaned = text
        for pattern in PROMOTIONAL_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        return cleaned

    @classmethod
    def standardize_units(cls, text: str) -> str:
        """Standardizes common physical & technical units into compact representations."""
        # e.g., "10 mm" -> "10mm", "64 gb" -> "64gb", "5000 mah" -> "5000mah", "100 ml" -> "100ml"
        patterns = [
            (r"(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|in|ft)\b", r"\1\2"),
            (r"(\d+(?:\.\d+)?)\s*(kb|mb|gb|tb)\b", r"\1\2"),
            (r"(\d+(?:\.\d+)?)\s*(mah|ah|w|v|hz|khz|mhz|ghz)\b", r"\1\2"),
            (r"(\d+(?:\.\d+)?)\s*(ml|l|oz|g|kg|lbs)\b", r"\1\2"),
        ]
        res = text
        for pat, repl in patterns:
            res = re.sub(pat, repl, res, flags=re.IGNORECASE)
        return res

    @classmethod
    def extract_brand(cls, title: str, vendor: Optional[str] = None, explicit_brand: Optional[str] = None) -> Optional[str]:
        """Extracts and formats canonical brand."""
        if explicit_brand and str(explicit_brand).lower().strip() not in ["generic", "unbranded", "none", ""]:
            return str(explicit_brand).strip().title()

        title_lower = str(title or "").lower()
        vendor_lower = str(vendor or "").lower()

        # Check known brands in title or vendor first
        for b in KNOWN_BRANDS:
            if re.search(r"\b" + re.escape(b) + r"\b", title_lower) or re.search(r"\b" + re.escape(b) + r"\b", vendor_lower):
                return b.title()

        if vendor and str(vendor).lower().strip() not in ["generic", "unbranded", "none", ""]:
            # Clean vendor if it contains store suffix
            v_clean = re.sub(r"\b(official|flagship|store|pk|global|shop|inc|co|ltd|audio|tech|technology|apparel)\b", "", str(vendor), flags=re.IGNORECASE).strip()
            if v_clean:
                return v_clean.title()
            return str(vendor).strip().title()

        return None

    @classmethod
    def extract_model_number(cls, text: str) -> Optional[str]:
        """Extracts candidate alphanumeric model numbers (e.g. M570, WH-1000XM4, A3951)."""
        # Patterns for typical tech/apparel model identifiers
        matches = re.findall(r"\b([A-Z0-9]{1,4}[-][A-Z0-9]{2,8}|[A-Z]{1,3}\d{2,5}[A-Z]{0,3}|[A-Z]\d{2,4})\b", text)
        if matches:
            # Return first non-unit match
            for m in matches:
                if not re.match(r"^\d+(mm|gb|mb|mah|kg|ml)$", m, re.IGNORECASE):
                    return m.upper()
        return None

    @classmethod
    def compute_completeness_score(cls, raw: Dict[str, Any]) -> float:
        """Calculates data quality & completeness score between 0.0 and 1.0."""
        score = 0.0
        if raw.get("title") or raw.get("name") or raw.get("product_name"):
            score += 0.35
        if raw.get("price") and float(raw.get("price") or 0) > 0:
            score += 0.25
        if raw.get("image_url") or raw.get("image") or raw.get("primary_image"):
            score += 0.15
        if raw.get("product_url") or raw.get("url"):
            score += 0.10
        if raw.get("brand") or raw.get("vendor") or raw.get("seller_name"):
            score += 0.10
        if raw.get("rating") is not None or raw.get("review_count") is not None:
            score += 0.05
        return round(min(1.0, score), 2)

    @classmethod
    def normalize_product(cls, raw: Dict[str, Any], platform: str = "generic") -> Dict[str, Any]:
        """Full normalization pipeline for a product entity."""
        raw_title = raw.get("title") or raw.get("name") or raw.get("product_name") or ""
        
        # Unicode NFKC & punctuation cleaning
        clean_text = cls.clean_unicode(raw_title)
        clean_text = cls.clean_promotional_noise(clean_text)
        clean_text = cls.standardize_units(clean_text)
        
        # Collapse multiple spaces
        clean_tokens = [t for t in re.split(r"[\s\-_,:;()\[\]{}]+", clean_text) if t]
        canonical_name = " ".join(clean_tokens)
        normalized_name = canonical_name.lower()

        brand = cls.extract_brand(
            title=raw_title,
            vendor=raw.get("vendor") or raw.get("seller_name"),
            explicit_brand=raw.get("brand")
        )
        model_number = cls.extract_model_number(raw_title)

        token_set = set(t.lower() for t in clean_tokens if len(t) > 1)

        completeness = cls.compute_completeness_score(raw)

        return {
            "canonical_name": canonical_name,
            "normalized_name": normalized_name,
            "brand": brand,
            "model_number": model_number,
            "tokens": token_set,
            "completeness_score": completeness,
            "platform": platform
        }
