"""Rating and review count extraction."""

import re
from typing import Any, Dict, Optional, Tuple
from bs4 import BeautifulSoup


class RatingExtractor:
    """Extracts average rating and total review count from JSON-LD, structured data, or DOM."""

    RATING_SELECTORS = [
        ".score .score-average",
        ".pdp-review-summary__stars",
        ".pdp-mod-review .score-average",
        "span.ratig-num--KNake",
        ".rating-score",
        "[data-qa-locator='rating-score']",
    ]

    REVIEW_COUNT_SELECTORS = [
        ".pdp-review-summary__link",
        ".count",
        ".pdp-mod-review .summary",
        "div.rating__review--ygkUy a",
        ".review-count",
        "[data-qa-locator='review-count']",
    ]

    @staticmethod
    def parse_float(text: str) -> Optional[float]:
        """Extract float between 0.0 and 5.0 from text."""
        if not text:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            try:
                val = float(match.group(1))
                if 0.0 <= val <= 5.0:
                    return val
            except ValueError:
                return None
        return None

    @staticmethod
    def parse_int(text: str) -> Optional[int]:
        """Extract integer from string like '1,420 Ratings' or '(45)'."""
        if not text:
            return None
        cleaned = text.replace(",", "")
        match = re.search(r"(\d+)", cleaned)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
        json_ld: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[float], Optional[int]]:
        """
        Extract (rating, review_count).
        """
        rating: Optional[float] = None
        review_count: Optional[int] = None

        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json)
            if isinstance(fields, dict):
                score_data = (
                    fields.get("review")
                    or fields.get("ratings")
                    or fields.get("reviewScore")
                    or fields.get("scores", {})
                )
                if isinstance(score_data, dict):
                    r_val = score_data.get("ratings") or score_data.get("average") or score_data.get("score")
                    c_val = score_data.get("reviews") or score_data.get("rateCount") or score_data.get("reviewCount")
                    if r_val is not None:
                        rating = self.parse_float(str(r_val))
                    if c_val is not None:
                        review_count = self.parse_int(str(c_val))
                elif score_data is not None and not isinstance(score_data, (list, dict)):
                    rating = self.parse_float(str(score_data))

        # 2. JSON-LD aggregateRating
        if rating is None and json_ld:
            agg = json_ld.get("aggregateRating")
            if isinstance(agg, dict):
                r_val = agg.get("ratingValue")
                c_val = agg.get("reviewCount") or agg.get("ratingCount")
                if r_val is not None:
                    rating = self.parse_float(str(r_val))
                if c_val is not None:
                    review_count = self.parse_int(str(c_val))

        # 3. DOM Selectors
        if rating is None:
            for sel in self.RATING_SELECTORS:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    rating = self.parse_float(el.get_text(strip=True))
                    if rating is not None:
                        break

        if review_count is None:
            for sel in self.REVIEW_COUNT_SELECTORS:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    review_count = self.parse_int(el.get_text(strip=True))
                    if review_count is not None:
                        break

        return rating, review_count
