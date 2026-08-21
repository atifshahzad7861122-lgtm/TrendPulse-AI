from typing import List, Optional
from datetime import datetime, timezone
from backend.app.models.domain import DataSource
from backend.app.repositories.base import DataSourceRepository

class DataSourceService:
    """
    Manages data source connector lifecycle and telemetry health scores.
    """

    def __init__(self, data_source_repo: DataSourceRepository):
        self.sources = data_source_repo

    def list_sources(self) -> List[DataSource]:
        return self.sources.list()

    def connect_source(self, slug: str) -> Optional[DataSource]:
        src = self.sources.update_status(slug, "Connected")
        if src:
            src.last_sync = datetime.now(timezone.utc)
            src.health_score = 98
        return src

    def disconnect_source(self, slug: str) -> Optional[DataSource]:
        return self.sources.update_status(slug, "Disconnected")
