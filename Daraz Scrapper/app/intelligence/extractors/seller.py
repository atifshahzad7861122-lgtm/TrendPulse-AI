"""Seller and merchant extraction with integrity validation."""

import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup


class SellerExtractor:
    """
    Extracts merchant identity, seller ratings, and shop profiles.
    Strictly prevents mapping product IDs or itemId parameters as seller IDs.
    """

    @classmethod
    def clean_seller_id(cls, raw_id: Optional[str], product_id: Optional[str] = None) -> Optional[str]:
        """
        Validate and sanitize seller_id.
        Rejects values matching product_id or itemId URL parameters.
        """
        if not raw_id:
            return None

        clean = str(raw_id).strip()

        # Reject if identical to product_id
        if product_id and clean.lower() == str(product_id).strip().lower():
            return None

        # Reject if looks like an itemId URL param query string
        if "itemid=" in clean.lower() or "productid=" in clean.lower():
            return None

        # Reject generic placeholder text
        if clean.lower() in ("unknown", "null", "none", "seller", "seller_id", "undefined"):
            return None

        return clean if len(clean) < 100 else None

    @classmethod
    def extract_seller_from_dom(
        cls,
        soup: BeautifulSoup,
        product_id: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
        """
        Extract (seller_id, seller_name, seller_rating, seller_url) from DOM.
        """
        seller_id: Optional[str] = None
        seller_name: Optional[str] = None
        seller_rating: Optional[float] = None
        seller_url: Optional[str] = None

        # 1. Daraz Seller Selectors
        seller_link = soup.select_one(".seller-name__detail a, .seller-link, #sellerProfileTriggerId")
        if seller_link:
            seller_name = seller_link.get_text(strip=True)
            href = seller_link.get("href")
            if href:
                seller_url = href if href.startswith("http") else f"https:{href}"
                # Extract seller id from shop URL
                m = re.search(r"/shop/([^/?]+)", href)
                if m:
                    seller_id = cls.clean_seller_id(m.group(1), product_id)

        # 2. Amazon "Sold by" or "Brand"
        if not seller_name:
            merchant_tag = soup.select_one("#sellerProfileTriggerId, #merchant-info, [data-feature-name='merchant-info']")
            if merchant_tag:
                text = merchant_tag.get_text(strip=True)
                m = re.search(r"(?:Sold by|Dispatched from and sold by|Ships from and sold by)\s+([^,.]+)", text, re.IGNORECASE)
                if m:
                    seller_name = m.group(1).strip()
                elif text:
                    seller_name = text.strip()

        # 3. eBay Seller
        if not seller_name:
            ebay_seller_tag = soup.select_one(".x-sellercard-atf__info__about-seller a, .mbg-nw, .seller-persona")
            if ebay_seller_tag:
                seller_name = ebay_seller_tag.get_text(strip=True)
                seller_id = cls.clean_seller_id(seller_name, product_id)

        # 4. Rating extraction from seller section
        rating_tag = soup.select_one(".seller-info-rating, .seller-rating__percentage, .x-sellercard-atf__data-item")
        if rating_tag:
            m_rating = re.search(r"(\d+(?:\.\d+)?)\s*%", rating_tag.get_text(strip=True))
            if m_rating:
                try:
                    seller_rating = float(m_rating.group(1))
                except ValueError:
                    pass

        return seller_id, seller_name, seller_rating, seller_url
