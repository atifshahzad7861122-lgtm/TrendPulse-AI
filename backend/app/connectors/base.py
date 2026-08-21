from abc import ABC, abstractmethod
from typing import List
from backend.app.domain.signals import PlatformSignal

class DataSourceConnector(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the platform, e.g., TikTok, Daraz."""
        ...

    @property
    @abstractmethod
    def platform_slug(self) -> str:
        """Slug identifier, e.g., tiktok, daraz."""
        ...

    @abstractmethod
    def fetch_signals(self, limit: int = 50) -> List[PlatformSignal]:
        """Fetch and return normalized signals from the platform."""
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify connector health and connectivity."""
        ...
