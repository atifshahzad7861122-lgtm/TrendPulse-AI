from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field

from backend.app.schemas.daraz import (
    DarazProductItem,
    DarazProductDetails,
    DarazCategoryItem,
    DarazSearchResponse,
    DarazSellerProductsResponse
)

class DarazFetchResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    provider_name: str
    is_rate_limited: bool = False
    is_cached: bool = False

class DarazProvider(ABC):
    name: str = "base_daraz_provider"
    priority: int = 100

    @abstractmethod
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
        """Search products across Daraz marketplace."""
        ...

    @abstractmethod
    def get_product_details(
        self,
        item_id: str,
        url: Optional[str] = None
    ) -> DarazFetchResult:
        """Fetch detailed metadata for a single Daraz product."""
        ...

    @abstractmethod
    def get_categories(self) -> DarazFetchResult:
        """Retrieve available Daraz taxonomy category hierarchies."""
        ...

    @abstractmethod
    def get_seller_products(
        self,
        seller_id: str,
        page: int = 1
    ) -> DarazFetchResult:
        """Retrieve products for a specific Daraz seller or shop."""
        ...
