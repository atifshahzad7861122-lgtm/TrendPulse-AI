import logging
from typing import Dict, Any, List, Optional
from backend.app.schemas.daraz import (
    DarazProductItem,
    DarazProductDetails,
    DarazCategoryItem,
    DarazSearchResponse,
    DarazSellerProductsResponse
)
from backend.app.models.domain import MarketplaceProduct
from backend.app.repositories.base import MarketplaceProductRepository
from backend.app.services.daraz.base import DarazProvider, DarazFetchResult

logger = logging.getLogger(__name__)

class DarazDatabaseCacheProvider(DarazProvider):
    """
    Database Cache Provider for Daraz Products.
    Priority 4 (Last-resort fallback serving previously synchronized data).
    """
    name: str = "database_cache"
    priority: int = 4

    def __init__(self, repository: Optional[MarketplaceProductRepository] = None):
        self.repository = repository

    def is_configured(self) -> bool:
        return self.repository is not None

    def search_products(
        self,
        query: str,
        page: int = 1,
        category: Optional[str] = None,
        min_rating: Optional[float] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: Optional[str] = None
    ) -> DarazFetchResult:
        if not self.repository:
            return DarazFetchResult(
                success=False,
                error_code=500,
                error_message="Marketplace product repository is not available.",
                provider_name=self.name
            )

        limit = 20
        offset = (page - 1) * limit
        prods = self.repository.list_products(
            platform="daraz",
            category=category,
            search=query,
            limit=limit,
            offset=offset
        )

        if not prods:
            return DarazFetchResult(
                success=False,
                error_code=404,
                error_message=f"No cached Daraz products found for '{query or category}'",
                provider_name=self.name,
                is_cached=True
            )

        parsed_items: List[DarazProductItem] = []
        for p in prods:
            item = DarazProductItem(
                platform="daraz",
                product_id=p.product_id,
                name=p.product_name,
                price=p.price,
                original_price=p.original_price,
                discount=p.discount_percentage,
                discount_label=p.discount_label,
                currency=p.currency or "PKR",
                rating=p.rating,
                review_count=p.review_count,
                seller_name=p.seller_name,
                seller_id=p.seller_id,
                brand=None,
                category=p.category,
                image_url=p.image_url,
                product_url=p.product_url,
                sku=None,
                in_stock=p.in_stock,
                source="daraz.pk",
                raw_data=p.raw_source_data
            )
            parsed_items.append(item)

        total = self.repository.count_products(platform="daraz", category=category)
        search_res = DarazSearchResponse(
            query=query or category or "daraz",
            page=page,
            total_products=total or len(parsed_items),
            has_next=(offset + len(parsed_items) < total),
            source="daraz.pk",
            products=parsed_items
        )

        return DarazFetchResult(
            success=True,
            data=search_res,
            provider_name=self.name,
            is_cached=True
        )

    def get_product_details(self, item_id: str, url: Optional[str] = None) -> DarazFetchResult:
        if not self.repository:
            return DarazFetchResult(
                success=False,
                error_code=500,
                error_message="Marketplace product repository is not available.",
                provider_name=self.name
            )

        p = self.repository.get_product("daraz", item_id)
        if not p:
            return DarazFetchResult(
                success=False,
                error_code=404,
                error_message=f"Product {item_id} not found in database cache.",
                provider_name=self.name,
                is_cached=True
            )

        details = DarazProductDetails(
            platform="daraz",
            product_id=p.product_id,
            name=p.product_name,
            price=p.price,
            original_price=p.original_price,
            discount=p.discount_percentage,
            discount_label=p.discount_label,
            currency=p.currency or "PKR",
            rating=p.rating,
            review_count=p.review_count,
            in_stock=p.in_stock,
            brand=None,
            category=p.category,
            description="",
            highlights=[],
            specifications={},
            warranty=None,
            images=[p.image_url] if p.image_url else [],
            main_image=p.image_url,
            product_url=p.product_url,
            source="daraz.pk",
            raw_module=p.raw_source_data
        )

        return DarazFetchResult(
            success=True,
            data=details,
            provider_name=self.name,
            is_cached=True
        )

    def get_categories(self) -> DarazFetchResult:
        return DarazFetchResult(
            success=True,
            data=[],
            provider_name=self.name,
            is_cached=True
        )

    def get_seller_products(self, seller_id: str, page: int = 1) -> DarazFetchResult:
        return self.search_products(query="", page=page)
