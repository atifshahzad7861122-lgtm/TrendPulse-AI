"""Data quality gate and validation rules for extracted product intelligence."""

from typing import List, Tuple
from urllib.parse import urlparse

from app.intelligence.models.product import ProductIntelligence


class DataQualityGate:
    """
    Validates product intelligence data against integrity rules before persistence.
    Rejects or cleanses invalid mappings.
    """

    @classmethod
    def validate(cls, product: ProductIntelligence) -> Tuple[bool, List[str], List[str]]:
        """
        Validate product intelligence.
        Returns: (is_valid, list_of_errors, list_of_warnings).
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Product ID & Title Validation
        if not product.product_id or not str(product.product_id).strip():
            errors.append("Mandatory product_id is missing or empty")

        if not product.title or len(product.title.strip()) < 2:
            errors.append("Product title is missing or suspiciously short (< 2 chars)")

        # 2. Canonical URL Validation
        if not product.canonical_url or not product.canonical_url.startswith(("http://", "https://")):
            errors.append("Invalid canonical_url format")

        # 3. Price Validation
        if product.price < 0.0:
            errors.append(f"Price cannot be negative: {product.price}")
        elif product.price == 0.0:
            warnings.append("Product price is reported as 0.0 (may be out-of-stock or free)")

        if product.original_price is not None and product.original_price < 0.0:
            errors.append(f"Original price cannot be negative: {product.original_price}")

        # 4. Rating Validation
        if product.rating is not None:
            if not (0.0 <= product.rating <= 5.0):
                errors.append(f"Rating {product.rating} is outside valid [0.0, 5.0] range")

        # 5. Review & Rating Counts
        if product.review_count < 0:
            errors.append("review_count cannot be negative")

        if product.rating_count is not None and product.rating_count < 0:
            errors.append("rating_count cannot be negative")

        # 6. Sales Volume Integrity
        if product.sold_count is not None:
            if not isinstance(product.sold_count, int) or product.sold_count < 0:
                errors.append("sold_count must be a non-negative integer")

        # 7. Seller Identity & Mappings Validation (Critical Rule)
        if product.seller_id:
            s_id_clean = product.seller_id.strip()
            # seller_id must NOT equal product_id
            if s_id_clean.lower() == product.product_id.strip().lower():
                errors.append(f"seller_id '{product.seller_id}' must not equal product_id")

            # seller_id must NOT contain itemId parameter query leaks
            if "itemid=" in s_id_clean.lower() or "productid=" in s_id_clean.lower():
                errors.append(f"seller_id '{product.seller_id}' contains invalid itemId URL parameter")

        # 8. Image Deduplication Validation
        seen_img_urls = set()
        for idx, img in enumerate(product.images):
            if img.url in seen_img_urls:
                warnings.append(f"Duplicate image found at index {idx}: {img.url}")
            seen_img_urls.add(img.url)

        is_valid = len(errors) == 0
        return is_valid, errors, warnings
