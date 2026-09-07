"""Export crawler abstractions."""

from app.crawler.base import BaseCrawler
from app.crawler.job import CrawlJob

__all__ = [
    "BaseCrawler",
    "CrawlJob",
]
