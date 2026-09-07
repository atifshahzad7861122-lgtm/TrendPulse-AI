"""
ScrapeGraphAI Marketplace Search Provider for Amazon and eBay.

Performs real structured candidate acquisition from Amazon and eBay catalog pages
using ScrapeGraphAI's extraction graphs. Preserves factual marketplace attributes,
supports multi-page pagination, and strictly prohibits synthetic fallback data.
"""

import logging
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from backend.app.services.scraper.marketplace_search.enums import (
    MarketplaceType,
    SearchProviderName
)
from backend.app.services.scraper.marketplace_search.models import (
    MarketplaceSearchRequest,
    MarketplaceSearchCandidate
)
from backend.app.services.scraper.marketplace_search.provider import MarketplaceSearchProvider
from backend.app.services.scraper.providers.scrapegraphai.engine import ScrapeGraphAIEngine

logger = logging.getLogger("trendpulse.marketplace_search.scrapegraphai")


class ScrapeGraphAIMarketplaceSearchProvider(MarketplaceSearchProvider):
    """
    MarketplaceSearchProvider implementation powered by ScrapeGraphAI.
    Supports Amazon and eBay search catalog extraction.
    """

    def __init__(
        self,
        engine: Optional[ScrapeGraphAIEngine] = None,
        supported_marketplaces: Optional[List[MarketplaceType]] = None
    ):
        self.engine = engine or ScrapeGraphAIEngine()
        self.provider_name = SearchProviderName.SCRAPEGRAPHAI.value
        self._supported_marketplaces = supported_marketplaces or [
            MarketplaceType.AMAZON,
            MarketplaceType.EBAY
        ]

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_supported_marketplaces(self) -> List[MarketplaceType]:
        return self._supported_marketplaces

    def _build_page_urls(self, marketplace: MarketplaceType, keyword: str, max_pages: int) -> List[str]:
        """
        Constructs deterministic search catalog page URLs for pagination.
        """
        kw_enc = urllib.parse.quote_plus(keyword)
        urls: List[str] = []

        if marketplace == MarketplaceType.AMAZON:
            for p in range(1, max_pages + 1):
                if p == 1:
                    urls.append(f"https://www.amazon.com/s?k={kw_enc}")
                else:
                    urls.append(f"https://www.amazon.com/s?k={kw_enc}&page={p}")
        elif marketplace == MarketplaceType.EBAY:
            for p in range(1, max_pages + 1):
                if p == 1:
                    urls.append(f"https://www.ebay.com/sch/i.html?_nkw={kw_enc}")
                else:
                    urls.append(f"https://www.ebay.com/sch/i.html?_nkw={kw_enc}&_pgn={p}")
        else:
            urls.append(f"https://www.google.com/search?q={marketplace.value}+{kw_enc}")

        return urls

    def _normalize_candidate(
        self,
        raw_item: Dict[str, Any],
        marketplace: MarketplaceType,
        source_page_url: Optional[str] = None
    ) -> Optional[MarketplaceSearchCandidate]:
        """
        Maps a ScrapeGraphAI product extraction dictionary into MarketplaceSearchCandidate.
        Ensures missing fields remain None without inventing synthetic data.
        """
        title = raw_item.get("title") or raw_item.get("name")
        if not title or not str(title).strip():
            return None

        product_url = raw_item.get("product_url") or raw_item.get("url")
        if not product_url or not str(product_url).strip():
            return None

        product_id = raw_item.get("product_id") or raw_item.get("asin") or raw_item.get("item_id")
        ext_id = str(product_id).strip() if product_id else None

        # Price parsing
        price = None
        raw_price = raw_item.get("price")
        if raw_price is not None:
            try:
                p_val = float(raw_price)
                if p_val > 0:
                    price = round(p_val, 2)
            except (ValueError, TypeError):
                price = None

        # Original price
        original_price = None
        raw_orig = raw_item.get("original_price")
        if raw_orig is not None:
            try:
                op_val = float(raw_orig)
                if op_val > 0 and (price is None or op_val >= price):
                    original_price = round(op_val, 2)
            except (ValueError, TypeError):
                original_price = None

        # Currency
        currency = raw_item.get("currency")
        if not currency or str(currency).strip() == "":
            currency = "USD"
        else:
            currency = str(currency).strip().upper()

        # Rating - only if present and non-zero
        rating = None
        raw_rating = raw_item.get("rating")
        if raw_rating is not None:
            try:
                r_val = float(raw_rating)
                if 0.0 < r_val <= 5.0:
                    rating = round(r_val, 1)
            except (ValueError, TypeError):
                rating = None

        # Review count - only if present and non-negative
        review_count = None
        raw_revs = raw_item.get("review_count")
        if raw_revs is not None:
            try:
                rc_val = int(raw_revs)
                if rc_val >= 0:
                    review_count = rc_val
            except (ValueError, TypeError):
                review_count = None

        # Seller
        seller = raw_item.get("seller_name") or raw_item.get("seller")
        seller = str(seller).strip() if seller and str(seller).strip() else None

        # Brand
        brand = raw_item.get("brand")
        brand = str(brand).strip() if brand and str(brand).strip() and str(brand).lower() != "generic" else None

        # Category
        category = raw_item.get("category")
        category = str(category).strip() if category and str(category).strip() else None

        # Image URL
        image_url = raw_item.get("image_url") or raw_item.get("image")
        if not image_url and raw_item.get("images") and isinstance(raw_item["images"], list) and raw_item["images"]:
            image_url = raw_item["images"][0]
        image_url = str(image_url).strip() if image_url and str(image_url).strip().startswith("http") else None

        # Availability
        availability = raw_item.get("availability")
        if availability is not None:
            availability = bool(availability)

        # Description
        description = raw_item.get("description")
        description = str(description).strip() if description and str(description).strip() else None

        observed_at = datetime.now(timezone.utc)

        return MarketplaceSearchCandidate(
            external_product_id=ext_id,
            marketplace=marketplace,
            title=str(title).strip(),
            url=str(product_url).strip(),
            image_url=image_url,
            price=price,
            currency=currency,
            original_price=original_price,
            seller=seller,
            brand=brand,
            category=category,
            rating=rating,
            review_count=review_count,
            availability=availability,
            description=description,
            source_provider=self.provider_name,
            source_url=source_page_url or product_url,
            observed_at=observed_at,
            raw_payload_reference=raw_item
        )

    async def search(
        self,
        request: MarketplaceSearchRequest
    ) -> List[MarketplaceSearchCandidate]:
        """
        Execute real structured extraction on Amazon or eBay using ScrapeGraphAI.
        Paginates search catalog URLs until candidate_target is reached or exhausted.
        """
        logger.info(
            f"SCRAPEGRAPHAI_SEARCH_START marketplace={request.marketplace.value} "
            f"keyword='{request.keyword}' candidate_target={request.candidate_target}"
        )

        target_count = request.candidate_target

        # Determine estimated pages needed: ~20 items per page for Amazon, ~40 for eBay, max 15
        items_per_page = 20 if request.marketplace == MarketplaceType.AMAZON else 40
        max_pages = max(1, min((target_count + items_per_page - 1) // items_per_page, 15))

        page_urls = self._build_page_urls(
            marketplace=request.marketplace,
            keyword=request.keyword,
            max_pages=max_pages
        )

        try:
            crawl_res = await self.engine.crawl_catalog(
                marketplace=request.marketplace.value,
                urls=page_urls,
                max_products=target_count
            )
            raw_products = crawl_res.get("products", [])
        except Exception as err:
            logger.error(
                f"SCRAPEGRAPHAI_SEARCH_ERROR marketplace={request.marketplace.value} "
                f"keyword='{request.keyword}' error={err}"
            )
            return []

        candidates: List[MarketplaceSearchCandidate] = []
        for item in raw_products:
            if isinstance(item, dict):
                cand = self._normalize_candidate(
                    raw_item=item,
                    marketplace=request.marketplace
                )
                if cand:
                    candidates.append(cand)
                    if len(candidates) >= target_count:
                        break

        logger.info(
            f"SCRAPEGRAPHAI_SEARCH_COMPLETE marketplace={request.marketplace.value} "
            f"keyword='{request.keyword}' raw_extracted={len(raw_products)} "
            f"candidates_normalized={len(candidates)}"
        )
        return candidates
