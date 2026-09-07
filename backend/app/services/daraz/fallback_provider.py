import logging
from typing import Dict, Any, List, Optional
from backend.app.schemas.daraz import (
    DarazProductItem,
    DarazProductDetails,
    DarazCategoryItem,
    DarazSearchResponse,
    DarazSellerProductsResponse
)
from backend.app.services.daraz.base import DarazProvider, DarazFetchResult

logger = logging.getLogger(__name__)

class DarazDirectFallbackProvider(DarazProvider):
    """
    Direct Fallback Provider for Daraz Pakistan.
    Priority 3 (Tertiary fallback provider).
    """
    name: str = "daraz_direct_fallback"
    priority: int = 3

    def is_configured(self) -> bool:
        return True

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
        logger.info(f"Daraz Direct Fallback Provider querying '{query or category}'")
        return DarazFetchResult(
            success=False,
            error_code=503,
            error_message="Daraz Direct Fallback Provider offline.",
            provider_name=self.name
        )

    def get_product_details(self, item_id: str, url: Optional[str] = None) -> DarazFetchResult:
        return DarazFetchResult(
            success=False,
            error_code=503,
            error_message=f"Daraz Direct Fallback Provider offline for item {item_id}.",
            provider_name=self.name
        )

    def get_categories(self) -> DarazFetchResult:
        return DarazFetchResult(
            success=False,
            error_code=503,
            error_message="Daraz Direct Fallback Provider offline for categories.",
            provider_name=self.name
        )

    def get_seller_products(self, seller_id: str, page: int = 1) -> DarazFetchResult:
        return DarazFetchResult(
            success=False,
            error_code=503,
            error_message=f"Daraz Direct Fallback Provider offline for seller {seller_id}.",
            provider_name=self.name
        )
