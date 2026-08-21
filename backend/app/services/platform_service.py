from typing import List, Optional
from backend.app.models.domain import PlatformMetrics
from backend.app.repositories.base import PlatformRepository, ProductRepository
from backend.app.domain.aggregation import AggregationEngine

PLATFORM_DEFINITIONS = [
    ("TikTok", "tiktok", "tiktok"),
    ("Daraz", "daraz", "shopping_bag"),
    ("Instagram", "instagram", "photo_camera"),
    ("YouTube", "youtube", "smart_display"),
    ("Facebook", "facebook", "group"),
]

class PlatformService:
    """
    Computes real-time platform telemetry, activity momentum,
    and channel distribution dynamically from signal data.
    """

    def __init__(self, platform_repo: PlatformRepository, product_repo: ProductRepository):
        self.platforms = platform_repo
        self.products = product_repo

    def list_platforms(self) -> List[PlatformMetrics]:
        all_products = self.products.list()
        results: List[PlatformMetrics] = []
        for name, slug, icon in PLATFORM_DEFINITIONS:
            # Check existing connected status if any
            existing = self.platforms.get_by_slug(slug)
            status = existing.status if existing else "Connected"
            metrics = AggregationEngine.aggregate_platform_metrics(
                platform_name=name,
                platform_slug=slug,
                icon=icon,
                products=all_products,
                status=status
            )
            results.append(metrics)
        return results

    def get_platform_by_slug(self, slug: str) -> Optional[PlatformMetrics]:
        platforms = self.list_platforms()
        for p in platforms:
            if p.slug == slug:
                return p
        return None
