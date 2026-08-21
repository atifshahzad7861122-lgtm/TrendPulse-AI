from typing import Dict, Any, List, Tuple, Optional
import re

TAXONOMY_HIERARCHY = [
    {
        "category": "Beauty & Personal Care",
        "subcategory": "Skincare & Cosmetics",
        "product_type": "Facial Serums & Lip Treatments",
        "keywords": ["serum", "lip", "gloss", "skincare", "cosmetic", "glow", "thermal", "sunscreen", "moisturizer", "makeup", "beauty", "dermatology", "collagen", "retinol"]
    },
    {
        "category": "Sports & Outdoor",
        "subcategory": "Athletic Gear & Hydration",
        "product_type": "Endurance Vests & Packs",
        "keywords": ["running", "vest", "hydration", "marathon", "fitness", "trail", "athletic", "gym", "workout", "titanflex", "endurance", "sport", "hiking", "flask"]
    },
    {
        "category": "Consumer Electronics",
        "subcategory": "Mobile Accessories & Charging",
        "product_type": "Wireless Chargers & Stands",
        "keywords": ["magsafe", "charger", "stand", "magsnap", "foldable", "wireless", "earbuds", "gadget", "phone", "iphone", "android", "electronics", "tech", "usbc", "dock"]
    },
    {
        "category": "Home & Kitchen",
        "subcategory": "Beverage Prep & Kitchenware",
        "product_type": "Ceremonial Tea & Coffee Accessories",
        "keywords": ["matcha", "whisk", "ceremonial", "tea", "coffee", "kitchen", "blender", "desk", "aesthetic", "home", "living", "organic", "cookware", "kettle"]
    },
    {
        "category": "Fashion & Apparel",
        "subcategory": "Functional Streetwear & Activewear",
        "product_type": "Performance Hoodies & Outerwear",
        "keywords": ["hoodie", "jacket", "activewear", "sneakers", "streetwear", "pants", "seamless", "leggings", "fashion", "apparel", "wear", "oversized", "fleece"]
    }
]

class CategoryClassificationResult:
    def __init__(
        self,
        category: str,
        subcategory: str,
        product_type: str,
        confidence: float,
        reason: str,
        tags: List[str],
        classification_version: str = "2.4.0"
    ):
        self.category = category
        self.subcategory = subcategory
        self.product_type = product_type
        self.confidence = confidence
        self.reason = reason
        self.tags = tags
        self.classification_version = classification_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "product_type": self.product_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "tags": self.tags,
            "classification_version": self.classification_version
        }

class CategoryClassificationService:
    """
    Intelligence Agent: Deterministically classifies product signals into
    a 3-tier hierarchical taxonomy (Category -> Subcategory -> Product Type)
    using rule-based scoring, semantic density, and confidence fallbacks.
    """

    CLASSIFICATION_VERSION = "2.4.0"

    @staticmethod
    def classify(text: str, current_category: str = "") -> CategoryClassificationResult:
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = set(cleaned_text.split())

        best_category = current_category or "Unclassified"
        best_sub = "General Products"
        best_type = "Standard Item"
        best_score = 0
        matched_tags: List[str] = []

        for rule in TAXONOMY_HIERARCHY:
            score = 0
            found_words = []
            for kw in rule["keywords"]:
                if kw in tokens:
                    score += 2
                    found_words.append(kw)
                elif kw in cleaned_text:
                    score += 1
                    found_words.append(kw)

            if score > best_score:
                best_score = score
                best_category = rule["category"]
                best_sub = rule["subcategory"]
                best_type = rule["product_type"]
                matched_tags = found_words

        # If keyword score is low, preserve current category if valid or mark Needs Review
        if best_score < 2:
            if current_category and current_category not in ["General", "Unclassified"]:
                confidence = 0.50
                reason = f"Preserved baseline category '{current_category}' (low keyword match)"
                best_category = current_category
            else:
                best_category = "Unclassified"
                best_sub = "Needs Review"
                best_type = "Unspecified Item"
                confidence = 0.20
                reason = "No domain keywords identified; flagged for review"
        else:
            confidence = round(min(max(best_score / 5.0, 0.55), 0.98), 2)
            reason = f"Classified via keyword matches: {', '.join(matched_tags[:3])}"

        return CategoryClassificationResult(
            category=best_category,
            subcategory=best_sub,
            product_type=best_type,
            confidence=confidence,
            reason=reason,
            tags=matched_tags,
            classification_version=CategoryClassificationService.CLASSIFICATION_VERSION
        )
