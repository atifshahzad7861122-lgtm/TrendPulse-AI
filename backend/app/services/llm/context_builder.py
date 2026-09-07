import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.app.models.domain import UnifiedProduct, ProductPlatformListing, ProductMarketSnapshot
from backend.app.schemas.llm import DataFreshnessMeta

class ContextBuilder:
    """
    Constructs high-signal, token-budgeted, strictly grounded JSON context
    from Unified Product Intelligence domain models.
    """

    MAX_DESCRIPTION_LENGTH = 500
    MAX_HISTORICAL_SNAPSHOTS = 10
    MAX_CATEGORY_PRODUCTS = 15

    @classmethod
    def calculate_data_freshness(cls, listings: List[ProductPlatformListing]) -> DataFreshnessMeta:
        if not listings:
            return DataFreshnessMeta(
                source_platforms=[],
                source_providers=[],
                last_synced_at=None,
                data_age_seconds=0,
                data_status="cached"
            )

        platforms = list(dict.fromkeys(l.platform for l in listings if l.platform))
        providers = list(dict.fromkeys(l.source_provider for l in listings if l.source_provider))

        # Find most recent sync timestamp
        synced_dates = [l.last_synced_at for l in listings if l.last_synced_at]
        if synced_dates:
            most_recent = max(synced_dates)
            now = datetime.now(timezone.utc)
            if most_recent.tzinfo is None:
                most_recent = most_recent.replace(tzinfo=timezone.utc)
            age_seconds = max(0, int((now - most_recent).total_seconds()))
            status = "live" if age_seconds < 900 else "cached"  # 15 minutes threshold
            last_synced_str = most_recent.isoformat()
        else:
            age_seconds = 0
            status = "cached"
            last_synced_str = None

        return DataFreshnessMeta(
            source_platforms=platforms,
            source_providers=providers,
            last_synced_at=last_synced_str,
            data_age_seconds=age_seconds,
            data_status=status
        )

    @classmethod
    def build_product_context(
        cls,
        product: UnifiedProduct,
        listings: List[ProductPlatformListing],
        history: Optional[List[ProductMarketSnapshot]] = None
    ) -> Dict[str, Any]:
        """Constructs sanitized structured context for a single unified product."""
        # Truncate description safely
        desc = (product.description or "").strip()
        if len(desc) > cls.MAX_DESCRIPTION_LENGTH:
            desc = desc[:cls.MAX_DESCRIPTION_LENGTH] + "... [truncated]"

        # Platform listings summary
        formatted_listings = []
        for l in listings:
            formatted_listings.append({
                "platform": l.platform,
                "store_domain": l.store_domain,
                "price": l.price,
                "original_price": l.original_price,
                "currency": l.currency,
                "discount_percentage": l.discount_percentage,
                "rating": l.rating,
                "review_count": l.review_count,
                "available": l.available,
                "seller_or_vendor": l.vendor or l.seller_name,
                "completeness_score": l.completeness_score,
                "last_synced_at": l.last_synced_at.isoformat() if l.last_synced_at else None
            })

        # History timeline (latest N snapshots)
        formatted_history = []
        if history:
            sorted_history = sorted(
                history,
                key=lambda x: x.observed_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )[:cls.MAX_HISTORICAL_SNAPSHOTS]
            for h in sorted_history:
                formatted_history.append({
                    "platform": h.platform,
                    "price": h.price,
                    "rating": h.rating,
                    "review_count": h.review_count,
                    "stock_status": h.stock_status,
                    "observed_at": h.observed_at.isoformat() if h.observed_at else None
                })

        freshness = cls.calculate_data_freshness(listings)

        return {
            "unified_product_id": product.unified_product_id,
            "canonical_name": product.canonical_name,
            "brand": product.brand or "Unbranded / Independent",
            "category": product.category or "General",
            "subcategory": product.subcategory,
            "product_type": product.product_type,
            "description": desc if desc else "Data unavailable",
            "identifiers": product.identifiers or {},
            "active_listings_count": len(listings),
            "platform_listings": formatted_listings,
            "recent_snapshot_history": formatted_history,
            "data_freshness": freshness.model_dump()
        }

    @classmethod
    def build_category_context(
        cls,
        category: str,
        products_with_listings: List[tuple[UnifiedProduct, List[ProductPlatformListing]]]
    ) -> Dict[str, Any]:
        """Constructs sanitized structured context for a marketplace category."""
        sample_items = []
        all_prices: List[float] = []
        all_listings: List[ProductPlatformListing] = []

        for prod, listings in products_with_listings[:cls.MAX_CATEGORY_PRODUCTS]:
            all_listings.extend(listings)
            item_prices = [l.price for l in listings if l.price > 0]
            if item_prices:
                all_prices.extend(item_prices)

            sample_items.append({
                "canonical_name": prod.canonical_name,
                "brand": prod.brand,
                "platforms": [l.platform for l in listings],
                "price_range": f"{min(item_prices)} - {max(item_prices)}" if item_prices else "Data unavailable",
                "avg_rating": round(sum(l.rating for l in listings) / max(1, len(listings)), 1)
            })

        freshness = cls.calculate_data_freshness(all_listings)

        price_stats = {}
        if all_prices:
            price_stats = {
                "min_price": min(all_prices),
                "max_price": max(all_prices),
                "avg_price": round(sum(all_prices) / len(all_prices), 2),
                "sample_size": len(all_prices)
            }

        return {
            "category": category,
            "analyzed_products_count": len(sample_items),
            "price_statistics": price_stats if price_stats else "Data unavailable",
            "sample_products": sample_items,
            "data_freshness": freshness.model_dump()
        }
