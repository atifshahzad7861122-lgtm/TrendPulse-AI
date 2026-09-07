from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from backend.app.models.domain import ShopifyProduct

@dataclass
class ShopifyFetchResult:
    success: bool
    products: List[ShopifyProduct] = field(default_factory=list)
    total_count: int = 0
    has_next: bool = False
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    is_rate_limited: bool = False
    is_timeout: bool = False
    is_empty_valid: bool = False
    raw_response: Optional[Any] = None

class ShopifyProvider(ABC):
    name: str = "base"
    priority: int = 1
    display_name: str = "Base Provider"

    @abstractmethod
    def validate_store(self, store_domain: str) -> bool:
        """Check if store domain is accessible and valid Shopify store."""
        ...

    @abstractmethod
    def fetch_products(
        self,
        store_domain: str,
        limit: int = 50,
        page: int = 1,
        collection: Optional[str] = None
    ) -> ShopifyFetchResult:
        """Fetch products for the given store domain."""
        ...

    @abstractmethod
    def fetch_product(
        self,
        store_domain: str,
        product_id_or_handle: str
    ) -> Optional[ShopifyProduct]:
        """Fetch single product details."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Self-test provider readiness/connectivity."""
        ...
