"""Field-level confidence scoring and diagnostics."""

from typing import Dict, Tuple

from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import FieldConfidence


class ConfidenceScorer:
    """
    Computes field-level and aggregate extraction confidence scores.
    Assigns qualitative labels (HIGH, MEDIUM, LOW, NONE).
    """

    # Field importance weights
    _WEIGHTS = {
        "title": 0.25,
        "price": 0.25,
        "images": 0.15,
        "rating": 0.10,
        "review_count": 0.10,
        "sold_count": 0.05,
        "seller": 0.05,
        "description": 0.05,
    }

    @classmethod
    def score(cls, product: ProductIntelligence) -> Tuple[Dict[str, float], Dict[str, FieldConfidence], float]:
        """
        Calculate (confidence_scores, confidence_levels, overall_confidence).
        """
        scores: Dict[str, float] = {}
        levels: Dict[str, FieldConfidence] = {}

        # 1. Title confidence
        if product.title and len(product.title) > 5:
            scores["title"] = 1.0
        elif product.title:
            scores["title"] = 0.5
        else:
            scores["title"] = 0.0

        # 2. Price confidence
        if product.price > 0.0:
            scores["price"] = 1.0
        else:
            scores["price"] = 0.0

        # 3. Images confidence
        if len(product.images) >= 2:
            scores["images"] = 1.0
        elif len(product.images) == 1:
            scores["images"] = 0.8
        else:
            scores["images"] = 0.0

        # 4. Rating confidence
        if product.rating is not None and 0.0 <= product.rating <= 5.0:
            scores["rating"] = 1.0
        else:
            scores["rating"] = 0.2  # missing rating is common for new products

        # 5. Review Count confidence
        scores["review_count"] = 1.0 if product.review_count >= 0 else 0.0

        # 6. Sales count confidence
        if product.sold_count is not None:
            scores["sold_count"] = 1.0
        elif product.raw_sold_text:
            scores["sold_count"] = 0.6
        else:
            scores["sold_count"] = 0.3  # optional field

        # 7. Seller confidence
        if product.seller_name and product.seller_id:
            scores["seller"] = 1.0
        elif product.seller_name:
            scores["seller"] = 0.8
        else:
            scores["seller"] = 0.3

        # 8. Description confidence
        if product.description_text and len(product.description_text) > 50:
            scores["description"] = 1.0
        elif product.description_text:
            scores["description"] = 0.6
        else:
            scores["description"] = 0.2

        # Convert scores to qualitative levels
        for field, s in scores.items():
            if s >= 0.85:
                levels[field] = FieldConfidence.HIGH
            elif s >= 0.5:
                levels[field] = FieldConfidence.MEDIUM
            elif s > 0.0:
                levels[field] = FieldConfidence.LOW
            else:
                levels[field] = FieldConfidence.NONE

        # Calculate overall weighted average
        weighted_sum = sum(scores.get(field, 0.0) * weight for field, weight in cls._WEIGHTS.items())
        overall = round(weighted_sum, 2)

        return scores, levels, overall
