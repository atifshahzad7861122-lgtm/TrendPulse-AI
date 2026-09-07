from typing import List, Optional
from datetime import datetime, timezone
from backend.app.models.domain import DataSource
from backend.app.repositories.base import DataSourceRepository, MarketplaceProductRepository, ProductRepository

class DataSourceService:
    """
    Manages data source connector lifecycle and telemetry health scores.
    """

    def __init__(
        self,
        data_source_repo: DataSourceRepository,
        marketplace_repo: Optional[MarketplaceProductRepository] = None,
        product_repo: Optional[ProductRepository] = None
    ):
        self.sources = data_source_repo
        self.marketplace_repo = marketplace_repo
        self.product_repo = product_repo

    def list_sources(self) -> List[DataSource]:
        raw_sources = self.sources.list()
        # Dynamically sync real counts
        for s in raw_sources:
            if s.slug == "daraz" and self.marketplace_repo:
                try:
                    count = self.marketplace_repo.count_products(platform="daraz") if hasattr(self.marketplace_repo, "count_products") else len(self.marketplace_repo.list_products(platform="daraz"))
                    s.records_synced = count
                except Exception:
                    pass
            elif s.slug in ("tiktok", "instagram", "facebook"):
                s.records_synced = 0
                s.status = "Coming Soon"
                s.sync_frequency = "Not Connected"
        return raw_sources

    def connect_source(self, slug: str) -> Optional[DataSource]:
        src = self.sources.update_status(slug, "Connected")
        if src:
            src.last_sync = datetime.now(timezone.utc)
            src.health_score = 98
        return src

    def disconnect_source(self, slug: str) -> Optional[DataSource]:
        return self.sources.update_status(slug, "Disconnected")

