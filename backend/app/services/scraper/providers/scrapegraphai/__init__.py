"""
ScrapeGraphAI Provider for TrendPulse AI.

Provides AI-driven graph extraction using ScrapeGraphAI while maintaining
complete compatibility with TrendPulse AI's canonical data pipeline,
DataQualityAgent, and persistence layers.
"""

from backend.app.services.scraper.providers.scrapegraphai.config import ScrapeGraphAIConfig
from backend.app.services.scraper.providers.scrapegraphai.schema import (
    ScrapeGraphProductItem, ScrapeGraphProductList,
    ScrapeGraphVariantItem, ScrapeGraphReviewItem
)
from backend.app.services.scraper.providers.scrapegraphai.normalizer import ScrapeGraphNormalizer
from backend.app.services.scraper.providers.scrapegraphai.engine import ScrapeGraphAIEngine

__all__ = [
    "ScrapeGraphAIConfig",
    "ScrapeGraphProductItem",
    "ScrapeGraphProductList",
    "ScrapeGraphVariantItem",
    "ScrapeGraphReviewItem",
    "ScrapeGraphNormalizer",
    "ScrapeGraphAIEngine",
]
