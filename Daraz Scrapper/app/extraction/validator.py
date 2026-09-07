"""Product extraction validation and quality gate enforcement."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.product import Product


class ValidationStatus(str, Enum):
    """Validation classification for an extracted product record."""

    VALID = "valid"                  # All required fields present and within valid ranges
    WARNING = "warning"              # Non-fatal warnings (e.g. missing optional fields like description/specs)
    NEEDS_REVIEW = "needs_review"    # Low overall confidence or boundary anomalies
    REJECTED = "rejected"            # Fatal validation error (missing ID, missing price, invalid title)


class ValidationReport(BaseModel):
    """Detailed validation evaluation report."""

    status: ValidationStatus
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    passed_checks: List[str] = Field(default_factory=list)


class ProductExtractionValidator:
    """Validates extracted product fields against marketplace business rules and constraints."""

    @classmethod
    def validate_product(
        cls,
        product: Optional[Product],
        overall_confidence: float = 1.0,
        min_confidence_threshold: float = 0.60,
    ) -> ValidationReport:
        """Evaluate a product instance and generate a validation report."""
        if product is None:
            return ValidationReport(
                status=ValidationStatus.REJECTED,
                is_valid=False,
                errors=["Product object is None"],
            )

        errors: List[str] = []
        warnings: List[str] = []
        missing_fields: List[str] = []
        passed_checks: List[str] = []

        # 1. Product ID Validation
        if not product.product_id or not str(product.product_id).strip():
            errors.append("Missing required product_id")
            missing_fields.append("product_id")
        else:
            passed_checks.append("product_id")

        # 2. Title Validation
        if not product.title or not product.title.strip():
            errors.append("Missing required title")
            missing_fields.append("title")
        elif len(product.title.strip()) < 3:
            errors.append(f"Title is too short: '{product.title}'")
        else:
            passed_checks.append("title")

        # 3. URL Validation
        if not product.url or not product.url.strip():
            errors.append("Missing required url")
            missing_fields.append("url")
        elif "daraz" not in product.url.lower():
            warnings.append(f"URL does not contain 'daraz': {product.url}")
        else:
            passed_checks.append("url")

        # 4. Price Validation
        if product.price is None:
            errors.append("Missing required price")
            missing_fields.append("price")
        elif product.price < 0:
            errors.append(f"Price cannot be negative: {product.price}")
        elif product.price == 0:
            warnings.append("Price is 0 (may be out of stock or free item)")
        else:
            passed_checks.append("price")

        # 5. Original Price & Discount Validation
        if product.original_price is not None:
            if product.original_price < 0:
                warnings.append(f"Original price cannot be negative: {product.original_price}")
            elif product.price and product.original_price < product.price:
                warnings.append(f"Original price ({product.original_price}) is less than selling price ({product.price})")
            else:
                passed_checks.append("original_price")

        if product.discount is not None:
            if product.discount < 0 or product.discount > 100:
                warnings.append(f"Discount percentage out of normal range (0-100%): {product.discount}%")
            else:
                passed_checks.append("discount")

        # 6. Rating Validation
        if product.rating is not None:
            if product.rating < 0.0 or product.rating > 5.0:
                warnings.append(f"Rating out of bounds (0.0 - 5.0): {product.rating}")
            else:
                passed_checks.append("rating")

        # 7. Review Count & Sold Count Validation
        if product.review_count is not None:
            if product.review_count < 0:
                warnings.append(f"Review count cannot be negative: {product.review_count}")
            else:
                passed_checks.append("review_count")

        if product.sold_count is not None:
            if product.sold_count < 0:
                warnings.append(f"Sold count cannot be negative: {product.sold_count}")
            else:
                passed_checks.append("sold_count")

        # 8. Images Validation
        if not product.images or len(product.images) == 0:
            warnings.append("Product has no extracted images")
            missing_fields.append("images")
        else:
            passed_checks.append("images")

        # 9. Seller Validation
        if not product.seller_name or not str(product.seller_name).strip():
            warnings.append("Product has missing seller information")
            missing_fields.append("seller")
        else:
            passed_checks.append("seller")

        # Determine Final Status
        if errors:
            status = ValidationStatus.REJECTED
            is_valid = False
        elif overall_confidence < min_confidence_threshold:
            status = ValidationStatus.NEEDS_REVIEW
            is_valid = True
            warnings.append(f"Overall confidence ({overall_confidence}) is below threshold ({min_confidence_threshold})")
        elif warnings:
            status = ValidationStatus.WARNING
            is_valid = True
        else:
            status = ValidationStatus.VALID
            is_valid = True

        return ValidationReport(
            status=status,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
            passed_checks=passed_checks,
        )
