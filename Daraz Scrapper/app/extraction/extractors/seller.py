"""Seller profile and rating extraction."""

import re
from typing import Any, Dict, Optional, Tuple
from bs4 import BeautifulSoup


class SellerExtractor:
    """Extracts seller profile attributes including seller_id, seller_name, seller_rating."""

    SELLER_NAME_SELECTORS = [
        ".seller-name__detail-name",
        ".seller-name__detail a",
        ".seller-name a",
        ".seller-name",
        "[data-qa-locator='seller-name']",
        ".pdp-seller-info__name",
        ".pdp-seller-name a",
    ]

    SELLER_RATING_SELECTORS = [
        ".seller-info-value.rating-positive",
        ".seller-info-value",
        ".pdp-seller-info__rate",
        "[data-qa-locator='seller-rating']",
    ]

    @staticmethod
    def _parse_percentage(text: str) -> Optional[float]:
        if not text:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[float]]:
        """
        Extract (seller_id, seller_name, seller_rating).
        """
        name: Optional[str] = None
        seller_id: Optional[str] = None
        seller_rating: Optional[float] = None

        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("seller", {}))
            if isinstance(fields, dict):
                seller_data = fields.get("seller") or fields.get("sellerInfo")
                if isinstance(seller_data, dict):
                    name = seller_data.get("name")
                    seller_id = str(seller_data.get("sellerId") or seller_data.get("id") or "") or None
                    score_val = seller_data.get("rating") or seller_data.get("positiveRate")
                    if score_val is not None:
                        seller_rating = self._parse_percentage(str(score_val))

        # 2. DOM Selectors
        if not name:
            for sel in self.SELLER_NAME_SELECTORS:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    name = el.get_text(strip=True)
                    if el.get("href"):
                        href = str(el.get("href"))
                        id_match = re.search(r"/(?:shop|seller)/([a-zA-Z0-9_-]+)", href)
                        if id_match:
                            seller_id = id_match.group(1)
                    break

        if seller_rating is None:
            for sel in self.SELLER_RATING_SELECTORS:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    seller_rating = self._parse_percentage(el.get_text(strip=True))
                    if seller_rating is not None:
                        break

        return seller_id, name, seller_rating
