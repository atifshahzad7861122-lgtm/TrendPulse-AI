"""
Shopify Marketplace Search Provider.

Wraps the existing ShopifyService and Shopify discovery/failover architecture
behind the canonical MarketplaceSearchProvider interface. Acquires real Shopify
candidates, performs canonical normalization, and preserves provenance.
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
from backend.app.services.shopify.service import ShopifyService
from backend.app.services.shopify.providers.scout_provider import ShopifyScoutProvider
from backend.app.models.domain import ShopifyProduct

logger = logging.getLogger("trendpulse.marketplace_search.shopify")

# Default well-known public Shopify storefront domains for keyword discovery
DEFAULT_SHOPIFY_DISCOVERY_STORES = [
    "gymshark.com",
    "allbirds.com",
    "colourpop.com",
    "kith.com",
    "bulletproof.com"
]


class ShopifyMarketplaceSearchProvider(MarketplaceSearchProvider):
    """
    Canonical search provider for Shopify stores and catalog discovery.
    Uses existing ShopifyService and Shopify Scout provider.
    """

    def __init__(
        self,
        shopify_service: Optional[ShopifyService] = None,
        discovery_stores: Optional[List[str]] = None
    ):
        self.shopify_service = shopify_service
        self.scout_provider = ShopifyScoutProvider()
        self.discovery_stores = discovery_stores or DEFAULT_SHOPIFY_DISCOVERY_STORES
        self.provider_name = "shopify_scout"

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_supported_marketplaces(self) -> List[MarketplaceType]:
        return [MarketplaceType.SHOPIFY]

    def _product_to_candidate(
        self,
        p: ShopifyProduct,
        source_url: Optional[str] = None
    ) -> Optional[MarketplaceSearchCandidate]:
        """
        Maps a domain ShopifyProduct into canonical MarketplaceSearchCandidate.
        Ensures missing fields remain None without synthetic values.
        """
        if not p.title or not str(p.title).strip():
            return None

        # Price parsing
        price = round(float(p.price), 2) if p.price and p.price > 0 else None
        original_price = round(float(p.compare_at_price), 2) if p.compare_at_price and p.compare_at_price > 0 else None

        # Rating - only if present
        rating = round(float(p.rating), 1) if p.rating and 0.0 < p.rating <= 5.0 else None
        review_count = int(p.review_count) if p.review_count and p.review_count >= 0 else None

        # Seller / Vendor
        seller = p.vendor if p.vendor and str(p.vendor).strip() else p.store_domain

        # Brand
        brand = p.vendor if p.vendor and p.vendor.lower() not in ("shopify merchant", "general", "generic") else None

        # Category
        category = p.category or p.product_type
        category = str(category).strip() if category and str(category).strip() else None

        observed_at = p.last_synced_at or datetime.now(timezone.utc)

        raw_ref = p.raw_data if isinstance(p.raw_data, dict) else {}
        if not raw_ref:
            raw_ref = {
                "product_id": p.product_id,
                "store_domain": p.store_domain,
                "handle": p.handle,
                "vendor": p.vendor
            }

        return MarketplaceSearchCandidate(
            external_product_id=p.product_id,
            marketplace=MarketplaceType.SHOPIFY,
            title=p.title.strip(),
            url=p.product_url or f"https://{p.store_domain}/products/{p.handle or p.product_id}",
            image_url=p.image_url,
            price=price,
            currency=p.currency or "USD",
            original_price=original_price,
            seller=seller,
            brand=brand,
            category=category,
            rating=rating,
            review_count=review_count,
            availability=p.available,
            description=p.tags[0] if p.tags else None,
            source_provider=self.provider_name,
            source_url=source_url or p.product_url,
            observed_at=observed_at,
            raw_payload_reference=raw_ref
        )

    async def search(
        self,
        request: MarketplaceSearchRequest
    ) -> List[MarketplaceSearchCandidate]:
        """
        Execute search candidate acquisition across Shopify stores.
        Queries existing synced repository products and discovers matching products
        from connected Shopify storefronts.
        """
        logger.info(
            f"SHOPIFY_SEARCH_START keyword='{request.keyword}' "
            f"candidate_target={request.candidate_target}"
        )

        candidates: List[MarketplaceSearchCandidate] = []
        target_count = request.candidate_target
        seen_ids = set()

        # 1. Search existing synced repository records if ShopifyService is available
        if self.shopify_service:
            try:
                # Query matching products across pages
                page = 1
                limit = 50
                while len(candidates) < target_count:
                    resp = self.shopify_service.list_products(
                        search=request.keyword,
                        page=page,
                        limit=limit
                    )
                    if not resp.items:
                        break

                    for item in resp.items:
                        if item.product_id not in seen_ids:
                            seen_ids.add(item.product_id)
                            # Convert schema item to candidate
                            price = round(float(item.price), 2) if item.price and item.price > 0 else None
                            orig_price = round(float(item.compare_at_price), 2) if item.compare_at_price and item.compare_at_price > 0 else None
                            rating = round(float(item.rating), 1) if item.rating and 0.0 < item.rating <= 5.0 else None
                            review_count = int(item.review_count) if item.review_count and item.review_count >= 0 else None

                            cand = MarketplaceSearchCandidate(
                                external_product_id=item.product_id,
                                marketplace=MarketplaceType.SHOPIFY,
                                title=item.title.strip(),
                                url=item.product_url,
                                image_url=item.image_url,
                                price=price,
                                currency=item.currency or "USD",
                                original_price=orig_price,
                                seller=item.vendor or item.store_domain,
                                brand=item.vendor if item.vendor and item.vendor.lower() not in ("shopify merchant", "generic") else None,
                                category=item.category or item.product_type,
                                rating=rating,
                                review_count=review_count,
                                availability=item.available,
                                description=item.tags[0] if item.tags else None,
                                source_provider=self.provider_name,
                                source_url=item.product_url,
                                observed_at=item.last_synced_at or datetime.now(timezone.utc),
                                raw_payload_reference=item.raw_data
                            )
                            candidates.append(cand)
                            if len(candidates) >= target_count:
                                break

                    if len(resp.items) < limit:
                        break
                    page += 1
            except Exception as repo_err:
                logger.warning(f"Error querying Shopify repository: {repo_err}")

        # 2. If below candidate_target, query discovery stores using Shopify Scout
        if len(candidates) < target_count:
            kw_lower = request.keyword.lower().strip()
            kw_tokens = kw_lower.split()

            for store in self.discovery_stores:
                if len(candidates) >= target_count:
                    break
                try:
                    # Fetch from public storefront
                    fetch_res = self.scout_provider.fetch_products(
                        store_domain=store,
                        limit=50,
                        page=1
                    )
                    if fetch_res.success and fetch_res.products:
                        for prod in fetch_res.products:
                            if prod.product_id in seen_ids:
                                continue

                            # Check if keyword matches title, product_type, tags, or vendor
                            matches = False
                            p_text = f"{prod.title} {prod.product_type} {' '.join(prod.tags)} {prod.vendor}".lower()
                            if any(token in p_text for token in kw_tokens):
                                matches = True

                            if matches:
                                cand = self._product_to_candidate(prod)
                                if cand:
                                    seen_ids.add(prod.product_id)
                                    candidates.append(cand)
                                    if len(candidates) >= target_count:
                                        break
                except Exception as scout_err:
                    logger.debug(f"Error scouting store {store}: {scout_err}")

        logger.info(
            f"SHOPIFY_SEARCH_COMPLETE keyword='{request.keyword}' "
            f"candidates_acquired={len(candidates)}"
        )
        return candidates
