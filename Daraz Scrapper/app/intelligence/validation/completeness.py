"""Product Completeness Validator assessing field integrity and data usability."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult


class CompletenessLevel(str, Enum):
    """Normalized data completeness classification."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INVALID = "INVALID"
    CHALLENGE = "CHALLENGE"
    NOT_FOUND = "NOT_FOUND"
    TARGET_UNAVAILABLE = "TARGET_UNAVAILABLE"


class ProductCompletenessReport(BaseModel):
    """Structured evaluation report for product data completeness."""
    level: CompletenessLevel
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Completeness score (0.0 - 1.0)")
    is_usable: bool = Field(default=True, description="Whether product record is usable for downstream consumption")
    missing_critical_fields: List[str] = Field(default_factory=list)
    missing_optional_fields: List[str] = Field(default_factory=list)
    diagnostic_notes: List[str] = Field(default_factory=list)


class ProductCompletenessValidator:
    """
    Evaluates extracted product intelligence against strict production standards.
    Distinguishes complete records from partial observations without fabricating missing data.
    """

    CRITICAL_FIELDS = ["product_id", "title", "canonical_url", "currency"]
    KEY_CATALOG_FIELDS = ["price", "images", "description_text", "seller_name", "category_path", "rating"]

    @classmethod
    def evaluate(
        cls,
        product: Optional[ProductIntelligence],
        extraction_result: Optional[IntelligenceExtractionResult] = None,
    ) -> ProductCompletenessReport:
        """Evaluate a product record or raw extraction result for completeness."""
        # 1. Handle Pre-Extraction Status Failures
        if extraction_result:
            if extraction_result.status == ExtractionStatus.CHALLENGE:
                return ProductCompletenessReport(
                    level=CompletenessLevel.CHALLENGE,
                    completeness_score=0.0,
                    is_usable=False,
                    diagnostic_notes=["Encountered anti-bot verification or CAPTCHA"],
                )
            if extraction_result.status_code == 404 or extraction_result.status == ExtractionStatus.FAILED and "not found" in " ".join(extraction_result.errors).lower():
                return ProductCompletenessReport(
                    level=CompletenessLevel.NOT_FOUND,
                    completeness_score=0.0,
                    is_usable=False,
                    diagnostic_notes=["Listing target not found (HTTP 404)"],
                )
            if extraction_result.status_code in {500, 502, 503, 504} or extraction_result.status_code == 0:
                if not product:
                    return ProductCompletenessReport(
                        level=CompletenessLevel.TARGET_UNAVAILABLE,
                        completeness_score=0.0,
                        is_usable=False,
                        diagnostic_notes=[f"Target server or network unavailable (Status {extraction_result.status_code})"],
                    )

        if not product:
            return ProductCompletenessReport(
                level=CompletenessLevel.INVALID,
                completeness_score=0.0,
                is_usable=False,
                missing_critical_fields=["all"],
                diagnostic_notes=["Product object is None"],
            )

        # 2. Check Critical Fields
        missing_crit: List[str] = []
        if not product.product_id or str(product.product_id).strip() == "":
            missing_crit.append("product_id")
        if not product.title or len(product.title.strip()) < 3:
            missing_crit.append("title")
        if not (product.canonical_url or product.source_url):
            missing_crit.append("canonical_url")
        if not product.currency:
            missing_crit.append("currency")

        if missing_crit:
            return ProductCompletenessReport(
                level=CompletenessLevel.INVALID,
                completeness_score=0.0,
                is_usable=False,
                missing_critical_fields=missing_crit,
                diagnostic_notes=[f"Missing mandatory critical fields: {', '.join(missing_crit)}"],
            )

        # 3. Check Key Catalog Fields & Compute Score
        missing_opt: List[str] = []
        notes: List[str] = []
        present_count = len(cls.CRITICAL_FIELDS)

        # Price check
        if product.price is None or product.price < 0:
            missing_opt.append("price")
            notes.append("Price is missing or invalid")
        else:
            present_count += 1

        # Images check
        if not product.images and not product.primary_image:
            missing_opt.append("images")
            notes.append("No product images found")
        else:
            present_count += 1

        # Description check
        if not product.description_text or len(product.description_text.strip()) < 10:
            missing_opt.append("description_text")
        else:
            present_count += 1

        # Seller check
        if not product.seller_name and not product.seller_id:
            missing_opt.append("seller")
        else:
            present_count += 1

        # Category check
        if not product.category_path and not product.category_name:
            missing_opt.append("category")
        else:
            present_count += 1

        # Rating / Reviews check
        if product.rating is None:
            missing_opt.append("rating")
        else:
            present_count += 1

        total_tracked = len(cls.CRITICAL_FIELDS) + len(cls.KEY_CATALOG_FIELDS)
        score = round(present_count / total_tracked, 2)

        # 4. Determine Completeness Level
        if len(missing_opt) <= 1:
            level = CompletenessLevel.COMPLETE
            is_usable = True
        elif "price" not in missing_opt and ("images" not in missing_opt or "description_text" not in missing_opt):
            level = CompletenessLevel.PARTIAL
            is_usable = True
        else:
            level = CompletenessLevel.PARTIAL
            is_usable = True

        return ProductCompletenessReport(
            level=level,
            completeness_score=score,
            is_usable=is_usable,
            missing_critical_fields=missing_crit,
            missing_optional_fields=missing_opt,
            diagnostic_notes=notes,
        )
