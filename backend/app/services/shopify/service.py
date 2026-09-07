from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from backend.app.models.domain import ShopifyProduct
from backend.app.repositories.base import ShopifyRepository
from backend.app.services.shopify.failover_pool import ShopifyFailoverPool
from backend.app.schemas.shopify import (
    ShopifyProductItem,
    ShopifyProductListResponse,
    ShopifySyncResponse,
    ShopifyStatusResponse,
    ShopifyProviderHealthItem
)

class ShopifyService:
    def __init__(self, repository: ShopifyRepository, failover_pool: Optional[ShopifyFailoverPool] = None):
        self.repository = repository
        self.failover_pool = failover_pool or ShopifyFailoverPool(repository=repository)

    def _to_schema(self, p: ShopifyProduct) -> ShopifyProductItem:
        price_fmt = f"${p.price:,.2f}" if p.currency == "USD" else f"{p.currency} {p.price:,.2f}"
        comp_fmt = None
        if p.compare_at_price and p.compare_at_price > 0:
            comp_fmt = f"${p.compare_at_price:,.2f}" if p.currency == "USD" else f"{p.currency} {p.compare_at_price:,.2f}"

        return ShopifyProductItem(
            id=p.id,
            store_domain=p.store_domain,
            product_id=p.product_id,
            title=p.title,
            handle=p.handle,
            product_url=p.product_url,
            image_url=p.image_url,
            images=p.images,
            vendor=p.vendor,
            product_type=p.product_type,
            category=p.category,
            tags=p.tags,
            price=p.price,
            price_formatted=price_fmt,
            compare_at_price=p.compare_at_price,
            compare_at_price_formatted=comp_fmt,
            discount_percentage=p.discount_percentage,
            discount_label=p.discount_label,
            currency=p.currency,
            available=p.available,
            rating=p.rating,
            review_count=p.review_count,
            source_provider=p.source_provider,
            variants_count=p.variants_count,
            first_seen_at=p.first_seen_at,
            last_seen_at=p.last_seen_at,
            last_synced_at=p.last_synced_at,
            raw_data=p.raw_data or {}
        )

    def list_products(
        self,
        store_domain: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> ShopifyProductListResponse:
        offset = (page - 1) * limit
        products = self.repository.list_products(
            store_domain=store_domain,
            category=category,
            search=search,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )
        total = self.repository.count_products(
            store_domain=store_domain,
            category=category,
            search=search
        )
        meta = self.repository.get_latest_sync_metadata(store_domain=store_domain)

        items = [self._to_schema(p) for p in products]
        msg = None
        if not items and total == 0:
            msg = "No Shopify products found. Sync a store to populate catalog."
        elif not meta.get("is_live"):
            msg = "Showing synchronized database records."

        return ShopifyProductListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            store_domain=store_domain,
            source_platform="Shopify",
            source_provider=meta.get("data_source", "database_cache"),
            is_live=meta.get("is_live", False),
            last_synced_at=meta.get("last_synced_at"),
            data_age_seconds=meta.get("data_age_seconds"),
            message=msg
        )

    def get_product(self, product_id: str) -> Optional[ShopifyProductItem]:
        p = self.repository.get_product_by_id(product_id)
        return self._to_schema(p) if p else None

    def sync_store(
        self,
        store_domain: str,
        limit: int = 50,
        page: int = 1,
        collection: Optional[str] = None,
        force_live: bool = False
    ) -> ShopifySyncResponse:
        products, source_provider, is_live, status, attempts, sync_run = self.failover_pool.execute_sync(
            store_domain=store_domain,
            limit=limit,
            page=page,
            collection=collection,
            force_live=force_live
        )

        items = [self._to_schema(p) for p in products]
        now = datetime.now(timezone.utc)
        meta = self.repository.get_latest_sync_metadata(store_domain=store_domain)

        if status == "success":
            msg = f"Successfully synced {len(items)} products from {store_domain} via {source_provider}."
            succ = True
        elif status == "cached":
            msg = "Live Shopify providers are temporarily unavailable. Showing previously synchronized data."
            succ = True
        else:
            msg = f"All Shopify providers failed and no cache available for {store_domain}."
            succ = False

        return ShopifySyncResponse(
            success=succ,
            store_domain=store_domain,
            source_platform="Shopify",
            source_provider=source_provider,
            is_live=is_live,
            status=status,
            products_fetched=sync_run.products_fetched,
            products_inserted=sync_run.products_inserted,
            products_updated=sync_run.products_updated,
            snapshots_created=sync_run.snapshots_created,
            last_synced_at=sync_run.completed_at,
            data_age_seconds=meta.get("data_age_seconds"),
            provider_attempts=attempts,
            products=items,
            message=msg
        )

    def get_status(self) -> ShopifyStatusResponse:
        pool_status = self.failover_pool.get_pool_status()
        sync_runs = self.repository.list_sync_runs(limit=10)
        meta = self.repository.get_latest_sync_metadata()
        total_prods = self.repository.count_products()
        
        # Calculate total snapshots
        # In repository, total products stored
        recent_runs = [r.model_dump(mode="json") for r in sync_runs]

        provider_items = [
            ShopifyProviderHealthItem.model_validate(p)
            for p in pool_status["providers"]
        ]

        return ShopifyStatusResponse(
            overall_status=pool_status["overall_status"],
            preferred_provider=pool_status["preferred_provider"],
            active_providers_count=pool_status["active_providers_count"],
            total_products_stored=total_prods,
            total_snapshots_stored=sum(r.snapshots_created for r in sync_runs) if sync_runs else 0,
            last_synced_at=meta.get("last_synced_at"),
            data_age_seconds=meta.get("data_age_seconds"),
            providers=provider_items,
            recent_sync_runs=recent_runs
        )
