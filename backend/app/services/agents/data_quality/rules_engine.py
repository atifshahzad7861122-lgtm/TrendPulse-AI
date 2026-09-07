import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional

from backend.app.models.domain import DataQualityRuleViolation

RECOGNIZED_CURRENCIES = {
    "USD", "PKR", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "INR", "AED", "SAR",
    "SGD", "NZD", "CHF", "HKD", "SEK", "NOK", "KRW", "TRY", "RUB", "BRL", "ZAR", "RS", "RS."
}

GENERIC_PLACEHOLDERS = {
    "null", "none", "undefined", "n/a", "na", "test", "test product", "sample",
    "sample product", "placeholder", "no title", "untitled", "unknown"
}

GENERIC_BRANDS = {
    "generic", "no brand", "nobrand", "oem", "unbranded", "unknown", "n/a", "none", "null"
}

class DataQualityRulesEngine:
    """
    Deterministic validation engine evaluating marketplace product payloads
    for completeness, sanity, impossible values, formatting, freshness, and anomalies.
    """

    def __init__(self, staleness_days: int = 30):
        self.staleness_days = staleness_days

    def _is_valid_url(self, url: Optional[str]) -> bool:
        if not url or not isinstance(url, str):
            return False
        clean = url.strip()
        if not (clean.startswith("http://") or clean.startswith("https://") or clean.startswith("//")):
            return False
        try:
            result = urllib.parse.urlparse(clean if not clean.startswith("//") else f"https:{clean}")
            return bool(result.netloc)
        except Exception:
            return False

    def _detect_title_spam(self, title: str) -> bool:
        """Detects keyword stuffing or suspicious spam patterns in titles."""
        if not title:
            return False
        words = [w.lower() for w in re.findall(r"\b\w+\b", title) if len(w) > 2]
        if not words:
            return False
        # Repeated word frequency > 5 times
        counts = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
            if counts[w] >= 5:
                return True
        # Excessive consecutive punctuation / special characters
        if re.search(r"[!@#$%^&*()_+=\[\]{};':\"\\|<>\/?~`]{4,}", title):
            return True
        return False

    def evaluate(self, payload: Dict[str, Any], existing_catalog: Optional[List[Dict[str, Any]]] = None) -> Tuple[
        List[DataQualityRuleViolation],
        List[DataQualityRuleViolation],
        Dict[str, float],
        bool,
        Dict[str, Any]
    ]:
        """
        Executes all deterministic rules against a product payload.
        Returns:
            issues (critical violations)
            warnings (non-critical violations)
            field_scores (per-field quality rating 0.0 - 1.0)
            needs_llm (flag if ambiguous attributes require LLM resolution)
            llm_context (minimal context payload if LLM is needed)
        """
        issues: List[DataQualityRuleViolation] = []
        warnings: List[DataQualityRuleViolation] = []
        field_scores: Dict[str, float] = {
            "product_id": 1.0,
            "title": 1.0,
            "brand": 1.0,
            "price": 1.0,
            "currency": 1.0,
            "rating": 1.0,
            "reviews": 1.0,
            "urls": 1.0,
            "category": 1.0,
            "freshness": 1.0,
            "inventory": 1.0,
            "uniqueness": 1.0
        }
        needs_llm = False
        llm_context: Dict[str, Any] = {}

        # ----------------------------------------------------------------------
        # 1. Product Identifier Validation
        # ----------------------------------------------------------------------
        p_id = str(payload.get("product_id") or payload.get("id") or payload.get("item_id") or "").strip()
        if not p_id or p_id.lower() in GENERIC_PLACEHOLDERS:
            issues.append(DataQualityRuleViolation(
                field="product_id",
                rule_name="mandatory_product_id",
                severity="critical",
                message="Product identifier is missing or is an invalid generic placeholder.",
                observed_value=p_id,
                penalty_score=35.0
            ))
            field_scores["product_id"] = 0.0

        # ----------------------------------------------------------------------
        # 2. Product Name / Title Validation
        # ----------------------------------------------------------------------
        title = str(payload.get("title") or payload.get("product_name") or payload.get("name") or "").strip()
        if not title:
            issues.append(DataQualityRuleViolation(
                field="title",
                rule_name="mandatory_title",
                severity="critical",
                message="Product title is missing or empty.",
                observed_value=title,
                penalty_score=35.0
            ))
            field_scores["title"] = 0.0
        elif len(title) < 3:
            issues.append(DataQualityRuleViolation(
                field="title",
                rule_name="title_min_length",
                severity="critical",
                message=f"Product title '{title}' is too short (minimum 3 characters required).",
                observed_value=title,
                penalty_score=25.0
            ))
            field_scores["title"] = 0.3
        elif title.lower() in GENERIC_PLACEHOLDERS:
            issues.append(DataQualityRuleViolation(
                field="title",
                rule_name="title_generic_placeholder",
                severity="critical",
                message=f"Product title '{title}' is a placeholder name.",
                observed_value=title,
                penalty_score=30.0
            ))
            field_scores["title"] = 0.0
        else:
            if self._detect_title_spam(title):
                warnings.append(DataQualityRuleViolation(
                    field="title",
                    rule_name="title_spam_patterns",
                    severity="warning",
                    message="Product title contains repetitive keywords or excessive symbols.",
                    observed_value=title[:80],
                    penalty_score=10.0
                ))
                field_scores["title"] = 0.7
                needs_llm = True
                llm_context["suspicious_title"] = title

        # ----------------------------------------------------------------------
        # 3. Brand Validation & Ambiguity Flag
        # ----------------------------------------------------------------------
        brand = payload.get("brand")
        brand_str = str(brand).strip() if brand is not None else ""
        if not brand_str or brand_str.lower() in GENERIC_BRANDS:
            warnings.append(DataQualityRuleViolation(
                field="brand",
                rule_name="missing_or_generic_brand",
                severity="warning",
                message="Brand is unassigned, generic, or OEM.",
                observed_value=brand_str or "null",
                penalty_score=8.0
            ))
            field_scores["brand"] = 0.6
            # If title is rich, we can attempt LLM brand extraction if enabled
            if title and len(title.split()) >= 3:
                needs_llm = True
                llm_context["extract_brand_from_title"] = title

        # ----------------------------------------------------------------------
        # 4. Price & Currency Sanity
        # ----------------------------------------------------------------------
        raw_price = payload.get("price")
        price_val = None
        try:
            if raw_price is not None:
                price_val = float(raw_price)
        except (ValueError, TypeError):
            pass

        if price_val is None:
            issues.append(DataQualityRuleViolation(
                field="price",
                rule_name="mandatory_price",
                severity="critical",
                message="Price is missing or non-numeric.",
                observed_value=raw_price,
                penalty_score=40.0
            ))
            field_scores["price"] = 0.0
        elif price_val <= 0.0:
            issues.append(DataQualityRuleViolation(
                field="price",
                rule_name="impossible_negative_or_zero_price",
                severity="critical",
                message=f"Impossible price value: {price_val} (must be > 0.0).",
                observed_value=price_val,
                penalty_score=40.0
            ))
            field_scores["price"] = 0.0
        elif price_val > 1000000.0:
            warnings.append(DataQualityRuleViolation(
                field="price",
                rule_name="price_extreme_outlier",
                severity="warning",
                message=f"Unusually high price value: {price_val}.",
                observed_value=price_val,
                penalty_score=10.0
            ))
            field_scores["price"] = 0.7

        # Original price sanity
        raw_orig_price = payload.get("original_price")
        if raw_orig_price is not None:
            try:
                orig_val = float(raw_orig_price)
                if orig_val < 0.0:
                    warnings.append(DataQualityRuleViolation(
                        field="original_price",
                        rule_name="impossible_negative_original_price",
                        severity="warning",
                        message=f"Negative original price: {orig_val}.",
                        observed_value=orig_val,
                        penalty_score=10.0
                    ))
                elif price_val is not None and orig_val > 0 and orig_val < price_val:
                    warnings.append(DataQualityRuleViolation(
                        field="original_price",
                        rule_name="original_price_lower_than_current",
                        severity="warning",
                        message=f"Original price ({orig_val}) is lower than current price ({price_val}).",
                        observed_value=orig_val,
                        penalty_score=5.0
                    ))
            except (ValueError, TypeError):
                pass

        # Currency
        curr = str(payload.get("currency") or "").strip().upper()
        if not curr:
            warnings.append(DataQualityRuleViolation(
                field="currency",
                rule_name="missing_currency",
                severity="warning",
                message="Currency is missing; defaulted to platform standard.",
                observed_value=curr,
                penalty_score=5.0
            ))
            field_scores["currency"] = 0.8
        elif curr not in RECOGNIZED_CURRENCIES:
            issues.append(DataQualityRuleViolation(
                field="currency",
                rule_name="invalid_currency_code",
                severity="critical",
                message=f"Unrecognized currency code: '{curr}'.",
                observed_value=curr,
                penalty_score=20.0
            ))
            field_scores["currency"] = 0.0

        # ----------------------------------------------------------------------
        # 5. Rating & Reviews Sanity
        # ----------------------------------------------------------------------
        raw_rating = payload.get("rating", 0.0)
        rating_val = 0.0
        try:
            if raw_rating is not None:
                rating_val = float(raw_rating)
        except (ValueError, TypeError):
            issues.append(DataQualityRuleViolation(
                field="rating",
                rule_name="malformed_rating",
                severity="critical",
                message="Rating value is not a valid number.",
                observed_value=raw_rating,
                penalty_score=20.0
            ))
            field_scores["rating"] = 0.0

        if rating_val < 0.0 or rating_val > 5.0:
            issues.append(DataQualityRuleViolation(
                field="rating",
                rule_name="impossible_rating_range",
                severity="critical",
                message=f"Rating {rating_val} is out of valid range [0.0, 5.0].",
                observed_value=rating_val,
                penalty_score=35.0
            ))
            field_scores["rating"] = 0.0

        raw_reviews = payload.get("review_count", 0)
        review_val = 0
        try:
            if raw_reviews is not None:
                review_val = int(raw_reviews)
        except (ValueError, TypeError):
            issues.append(DataQualityRuleViolation(
                field="review_count",
                rule_name="malformed_review_count",
                severity="critical",
                message="Review count is not a valid integer.",
                observed_value=raw_reviews,
                penalty_score=20.0
            ))
            field_scores["reviews"] = 0.0

        if review_val < 0:
            issues.append(DataQualityRuleViolation(
                field="review_count",
                rule_name="impossible_negative_review_count",
                severity="critical",
                message=f"Negative review count: {review_val}.",
                observed_value=review_val,
                penalty_score=30.0
            ))
            field_scores["reviews"] = 0.0

        # ----------------------------------------------------------------------
        # 6. URLs Validation
        # ----------------------------------------------------------------------
        p_url = payload.get("product_url") or payload.get("url")
        if p_url and not self._is_valid_url(str(p_url)):
            issues.append(DataQualityRuleViolation(
                field="product_url",
                rule_name="malformed_product_url",
                severity="critical",
                message=f"Invalid product URL: '{p_url}'.",
                observed_value=p_url,
                penalty_score=25.0
            ))
            field_scores["urls"] = min(field_scores["urls"], 0.4)

        img_url = payload.get("image_url") or payload.get("primary_image") or payload.get("main_image")
        if not img_url:
            warnings.append(DataQualityRuleViolation(
                field="image_url",
                rule_name="missing_image_url",
                severity="warning",
                message="Product image URL is missing.",
                observed_value="null",
                penalty_score=8.0
            ))
            field_scores["urls"] = min(field_scores["urls"], 0.7)
        elif not self._is_valid_url(str(img_url)):
            warnings.append(DataQualityRuleViolation(
                field="image_url",
                rule_name="malformed_image_url",
                severity="warning",
                message=f"Malformed image URL: '{img_url}'.",
                observed_value=img_url,
                penalty_score=8.0
            ))
            field_scores["urls"] = min(field_scores["urls"], 0.7)

        # ----------------------------------------------------------------------
        # 7. Category Validation & Ambiguity Flag
        # ----------------------------------------------------------------------
        cat = payload.get("category")
        cat_str = str(cat).strip() if cat is not None else ""
        if not cat_str or cat_str.lower() in GENERIC_PLACEHOLDERS:
            warnings.append(DataQualityRuleViolation(
                field="category",
                rule_name="missing_or_generic_category",
                severity="warning",
                message="Category is missing or generic.",
                observed_value=cat_str or "null",
                penalty_score=6.0
            ))
            field_scores["category"] = 0.5
            needs_llm = True
            llm_context["resolve_category_for_title"] = title
        elif cat_str.isdigit():
            # Numeric raw taxonomy ID like Daraz "9067"
            warnings.append(DataQualityRuleViolation(
                field="category",
                rule_name="numeric_raw_category_id",
                severity="warning",
                message=f"Category is an unmapped numeric taxonomy ID: '{cat_str}'.",
                observed_value=cat_str,
                penalty_score=5.0
            ))
            field_scores["category"] = 0.7
            needs_llm = True
            llm_context["map_numeric_category"] = {"category_id": cat_str, "title": title}

        # ----------------------------------------------------------------------
        # 8. Availability & Inventory Consistency
        # ----------------------------------------------------------------------
        avail = payload.get("available")
        stock = payload.get("inventory") or payload.get("stock")
        if avail is True and stock is not None:
            try:
                stock_int = int(stock)
                if stock_int == 0:
                    warnings.append(DataQualityRuleViolation(
                        field="availability",
                        rule_name="inconsistent_stock_state",
                        severity="warning",
                        message="Product marked available but stock quantity is 0.",
                        observed_value={"available": True, "stock": 0},
                        penalty_score=6.0
                    ))
                    field_scores["inventory"] = 0.6
            except (ValueError, TypeError):
                pass

        # ----------------------------------------------------------------------
        # 9. Freshness & Staleness Rules
        # ----------------------------------------------------------------------
        obs_time = payload.get("observed_at") or payload.get("last_synced_at") or payload.get("updated_at")
        now = datetime.now(timezone.utc)
        if obs_time:
            try:
                if isinstance(obs_time, str):
                    dt = datetime.fromisoformat(obs_time.replace("Z", "+00:00"))
                elif isinstance(obs_time, datetime):
                    dt = obs_time if obs_time.tzinfo else obs_time.replace(tzinfo=timezone.utc)
                else:
                    dt = now

                age_days = (now - dt).total_seconds() / 86400.0
                if age_days > self.staleness_days:
                    warnings.append(DataQualityRuleViolation(
                        field="freshness",
                        rule_name="stale_marketplace_data",
                        severity="warning",
                        message=f"Data snapshot is {age_days:.1f} days old (threshold: {self.staleness_days} days).",
                        observed_value=str(obs_time),
                        penalty_score=10.0
                    ))
                    field_scores["freshness"] = max(0.2, 1.0 - (age_days / 100.0))
                elif age_days < -1.0:
                    warnings.append(DataQualityRuleViolation(
                        field="freshness",
                        rule_name="future_timestamp_detected",
                        severity="warning",
                        message=f"Snapshot has future timestamp ({obs_time}).",
                        observed_value=str(obs_time),
                        penalty_score=5.0
                    ))
            except Exception:
                pass

        # ----------------------------------------------------------------------
        # 10. Duplicate / Collision Detection
        # ----------------------------------------------------------------------
        if existing_catalog and p_id:
            platform = str(payload.get("platform") or "").lower()
            for ex in existing_catalog:
                ex_id = str(ex.get("platform_product_id") or ex.get("product_id") or ex.get("id") or "").strip()
                ex_plat = str(ex.get("platform") or "").lower()
                ex_title = str(ex.get("title") or ex.get("product_name") or "").strip()
                ex_url = str(ex.get("product_url") or "").strip()

                if platform == ex_plat:
                    # Same ID collision
                    if ex_id == p_id and ex.get("id") != payload.get("id"):
                        warnings.append(DataQualityRuleViolation(
                            field="uniqueness",
                            rule_name="duplicate_product_identifier",
                            severity="warning",
                            message=f"Identical product identifier '{p_id}' already registered on platform '{platform}'.",
                            observed_value=p_id,
                            penalty_score=15.0
                        ))
                        field_scores["uniqueness"] = 0.5
                        break
                    # Exact URL collision
                    elif p_url and ex_url and p_url.lower() == ex_url.lower() and ex_id != p_id:
                        warnings.append(DataQualityRuleViolation(
                            field="uniqueness",
                            rule_name="duplicate_product_url",
                            severity="warning",
                            message="Exact product URL match found for different product ID.",
                            observed_value=p_url,
                            penalty_score=15.0
                        ))
                        field_scores["uniqueness"] = 0.5
                        break

        return issues, warnings, field_scores, needs_llm, llm_context
