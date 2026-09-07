"""
Daraz Specialized Marketplace Search Provider.

Wraps the existing DarazSpecializedScraperEngine behind the canonical
MarketplaceSearchProvider interface. Implements multi-page candidate acquisition,
canonical MarketplaceSearchCandidate normalization, and provenance preservation.
"""

import logging
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
from backend.app.services.scraper.providers.daraz_specialized.engine import DarazSpecializedScraperEngine

logger = logging.getLogger("trendpulse.marketplace_search.daraz")


class DarazMarketplaceSearchProvider(MarketplaceSearchProvider):
    """
    Canonical search provider for Daraz ecommerce platform.
    Uses DarazSpecializedScraperEngine for candidate acquisition.
    """

    def __init__(self, engine: Optional[DarazSpecializedScraperEngine] = None):
        self.engine = engine or DarazSpecializedScraperEngine(headless=True)
        self.provider_name = SearchProviderName.DARAZ_SPECIALIZED.value

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_supported_marketplaces(self) -> List[MarketplaceType]:
        return [MarketplaceType.DARAZ]

    def _normalize_candidate(
        self,
        raw_item: Dict[str, Any],
        keyword: str,
        page_url: Optional[str] = None
    ) -> Optional[MarketplaceSearchCandidate]:
        """
        Converts a raw Daraz extracted product dict into a canonical candidate.
        Strictly preserves factual data; missing attributes remain None.
        """
        title = raw_item.get("title") or raw_item.get("name")
        if not title or not str(title).strip():
            return None

        product_url = raw_item.get("product_url") or raw_item.get("url")
        if not product_url or not str(product_url).strip():
            return None

        product_id = raw_item.get("product_id") or raw_item.get("itemId")
        ext_id = str(product_id).strip() if product_id else None

        # Price parsing - never invent price
        price = None
        raw_price = raw_item.get("price")
        if raw_price is not None:
            try:
                p_val = float(raw_price)
                if p_val > 0:
                    price = round(p_val, 2)
            except (ValueError, TypeError):
                price = None

        # Original price if available
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
        currency = raw_item.get("currency") or "PKR"

        # Rating - only if real (never fabricate)
        rating = None
        raw_rating = raw_item.get("rating") or raw_item.get("ratingScore")
        if raw_rating is not None:
            try:
                r_val = float(raw_rating)
                if 0.0 < r_val <= 5.0:
                    rating = round(r_val, 1)
            except (ValueError, TypeError):
                rating = None

        # Review count - only if real
        review_count = None
        raw_revs = raw_item.get("review_count") or raw_item.get("review")
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
        brand = raw_item.get("brand") or raw_item.get("brandName")
        brand = str(brand).strip() if brand and str(brand).strip() and str(brand).lower() != "generic" else None

        # Category
        category = raw_item.get("category") or raw_item.get("categoryName")
        category = str(category).strip() if category and str(category).strip() else None

        # Image URL
        image_url = raw_item.get("image_url") or raw_item.get("image")
        image_url = str(image_url).strip() if image_url and str(image_url).strip().startswith("http") else None

        # Availability
        availability = raw_item.get("in_stock", True) if "in_stock" in raw_item else True

        # Observed timestamp
        observed_at = datetime.now(timezone.utc)

        return MarketplaceSearchCandidate(
            external_product_id=ext_id,
            marketplace=MarketplaceType.DARAZ,
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
            description=raw_item.get("description"),
            source_provider=self.provider_name,
            source_url=page_url or f"https://www.daraz.pk/catalog/?q={keyword}",
            observed_at=observed_at,
            raw_payload_reference=raw_item
        )

    async def search(
        self,
        request: MarketplaceSearchRequest
    ) -> List[MarketplaceSearchCandidate]:
        """
        Execute real search candidate acquisition on Daraz.
        Paginates until candidate_target is reached or catalog is exhausted.
        """
        logger.info(
            f"DARAZ_SEARCH_START keyword='{request.keyword}' "
            f"candidate_target={request.candidate_target} desired_results={request.desired_results}"
        )

        target_count = request.candidate_target
        # Daraz returns ~40 products per page; calculate needed pages (bounded to 15 max)
        pages_needed = max(1, min((target_count + 39) // 40, 15))

        try:
            raw_products, is_challenged, challenge_reason = await self.engine.crawl_keyword_search(
                keyword=request.keyword,
                max_pages=pages_needed,
                max_products=target_count
            )
        except Exception as err:
            logger.error(f"DARAZ_SEARCH_ERROR keyword='{request.keyword}' error={err}")
            return []

        if is_challenged:
            logger.warning(
                f"DARAZ_SEARCH_CHALLENGE keyword='{request.keyword}' reason='{challenge_reason}' "
                f"products_collected={len(raw_products)}"
            )

        candidates: List[MarketplaceSearchCandidate] = []
        for item in raw_products:
            cand = self._normalize_candidate(item, keyword=request.keyword)
            if cand:
                candidates.append(cand)
                if len(candidates) >= target_count:
                    break

        logger.info(
            f"DARAZ_SEARCH_COMPLETE keyword='{request.keyword}' "
            f"raw_extracted={len(raw_products)} candidates_normalized={len(candidates)}"
        )
        return candidates
