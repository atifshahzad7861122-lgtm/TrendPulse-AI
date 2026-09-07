from backend.app.services.scraper.bridge import ScraperIntegrationBridge
from backend.app.services.scraper.service import ScraperService
from backend.app.services.scraper.models import (
    StartScraperJobRequest, ScraperJobProgressResponse, ScraperJobListResponse,
    ScraperProductItem, ScraperProductListResponse, RawScrapedDataResponse,
    ScraperHistoricalSnapshotItem, ScraperProductHistoryResponse
)

__all__ = [
    "ScraperIntegrationBridge",
    "ScraperService",
    "StartScraperJobRequest",
    "ScraperJobProgressResponse",
    "ScraperJobListResponse",
    "ScraperProductItem",
    "ScraperProductListResponse",
    "RawScrapedDataResponse",
    "ScraperHistoricalSnapshotItem",
    "ScraperProductHistoryResponse"
]
