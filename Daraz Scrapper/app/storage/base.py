"""Abstract base storage interface defining the persistence contract."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.models.category import Category
from app.models.checkpoint import CrawlCheckpoint
from app.models.crawl import CrawlRun
from app.models.image import Image
from app.models.product import Product
from app.models.raw_data import RawDataRecord
from app.models.review import Review
from app.models.seller import Seller


class BaseStorage(ABC):
    """Abstract storage interface completely decoupled from crawling and parsing logic."""

    # --- Product Operations ---
    @abstractmethod
    async def save_product(self, product: Product) -> None:
        """Persist or update a single product."""
        pass

    @abstractmethod
    async def save_products(self, products: List[Product]) -> int:
        """Bulk persist or update a collection of products. Returns count saved."""
        pass

    @abstractmethod
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Retrieve a product by its unique product_id."""
        pass

    # --- Review Operations ---
    @abstractmethod
    async def save_review(self, review: Review) -> None:
        """Persist a single customer review."""
        pass

    @abstractmethod
    async def save_reviews(self, reviews: List[Review]) -> int:
        """Bulk persist customer reviews. Returns count saved."""
        pass

    # --- Classification & Entity Operations ---
    @abstractmethod
    async def save_category(self, category: Category) -> None:
        """Persist or update category classification."""
        pass

    @abstractmethod
    async def save_seller(self, seller: Seller) -> None:
        """Persist or update seller details."""
        pass

    @abstractmethod
    async def save_image(self, image: Image) -> None:
        """Persist product image asset record."""
        pass

    @abstractmethod
    async def save_images(self, images: List[Image]) -> int:
        """Bulk persist product image records. Returns count saved."""
        pass

    # --- Raw Data Preservation ---
    @abstractmethod
    async def save_raw_data(self, record: RawDataRecord) -> None:
        """Persist a single raw HTML/JSON response record."""
        pass

    @abstractmethod
    async def save_raw_data_batch(self, records: List[RawDataRecord]) -> int:
        """Bulk persist raw response records."""
        pass

    @abstractmethod
    async def get_raw_data(self, raw_id: str) -> Optional[RawDataRecord]:
        """Retrieve raw payload record by raw_id."""
        pass

    @abstractmethod
    async def save_snapshot(self, entity_id: str, data: Dict[str, Any], entity_type: str = "product") -> None:
        """Store point-in-time raw snapshot data."""
        pass

    # --- Checkpoints & Session Runs ---
    @abstractmethod
    async def save_checkpoint(self, checkpoint: CrawlCheckpoint) -> None:
        """Persist or update a crawl progress checkpoint."""
        pass

    @abstractmethod
    async def get_checkpoint(self, crawl_id: str) -> Optional[CrawlCheckpoint]:
        """Retrieve latest checkpoint for a crawl_id."""
        pass

    @abstractmethod
    async def create_crawl_run(self, crawl: CrawlRun) -> CrawlRun:
        """Initialize and persist a new crawl session record."""
        pass

    @abstractmethod
    async def update_crawl_run(self, crawl_id: str, **updates: Any) -> Optional[CrawlRun]:
        """Update existing crawl session status, metrics, or metadata."""
        pass

    @abstractmethod
    async def get_crawl_run(self, crawl_id: str) -> Optional[CrawlRun]:
        """Retrieve a crawl session by its crawl_id."""
        pass

    # --- Discovery Engine Methods ---
    @abstractmethod
    async def save_category_target(self, target: Any) -> None:
        """Persist a discovered category target."""
        pass

    @abstractmethod
    async def get_category_targets(self) -> List[Any]:
        """Retrieve all discovered category targets."""
        pass

    @abstractmethod
    async def save_product_target(self, target: Any) -> None:
        """Persist a discovered product target."""
        pass

    @abstractmethod
    async def save_product_targets(self, targets: List[Any]) -> int:
        """Bulk persist discovered product targets. Returns count saved."""
        pass

    @abstractmethod
    async def get_product_targets(self) -> List[Any]:
        """Retrieve all queued product targets."""
        pass

    @abstractmethod
    async def save_discovery_run(self, run: Any) -> Any:
        """Persist or update a discovery crawl run."""
        pass

    @abstractmethod
    async def get_discovery_run(self, crawl_id: str) -> Optional[Any]:
        """Retrieve discovery run by crawl_id."""
        pass

    @abstractmethod
    async def update_discovery_run(self, crawl_id: str, **updates: Any) -> Optional[Any]:
        """Update discovery run fields."""
        pass

    @abstractmethod
    async def save_snapshot(self, snapshot: Any) -> None:
        """Persist a historical product snapshot observation."""
        pass

    @abstractmethod
    async def get_snapshots(self, product_id: Optional[str] = None) -> List[Any]:
        """Retrieve historical product snapshots."""
        pass
