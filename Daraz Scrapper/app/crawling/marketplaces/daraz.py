"""Daraz Marketplace Adapter supporting regional domains (.pk, .lk, .com.bd, .com.np, .com.mm)."""

import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from app.crawling.marketplaces.base import BaseMarketplaceAdapter
from app.crawling.models import (
    CrawlContentType,
    CrawlResponse,
    CrawlStatus,
    MarketplaceType,
    UniversalCrawlResult,
)
from app.extraction.parser import ProductParser
from app.models.category import Category
from app.models.product import Product


class DarazAdapter(BaseMarketplaceAdapter):
    """
    Marketplace adapter for Daraz e-commerce platforms.
    """

    DOMAINS = ["daraz.pk", "daraz.lk", "daraz.com.bd", "daraz.com.np", "shop.com.mm"]

    def __init__(self):
        self.parser = ProductParser()

    @property
    def marketplace_type(self) -> MarketplaceType:
        return MarketplaceType.DARAZ

    @property
    def supported_domains(self) -> List[str]:
        return self.DOMAINS

    def validate_url(self, url: str) -> bool:
        if not url:
            return False
        return any(d in url.lower() for d in self.DOMAINS)

    def detect_content_type(self, url: str) -> CrawlContentType:
        canonical = self.canonicalize_url(url).lower()
        if re.search(r"-i\d+", canonical) or "/products/" in canonical:
            return CrawlContentType.PRODUCT
        elif "/catalog/" in canonical or "/catalog?" in canonical or "q=" in canonical or "/search" in canonical:
            return CrawlContentType.SEARCH
        elif any(c in canonical for c in ["/audio-", "/phones-", "/laptops-", "/category/"]):
            return CrawlContentType.CATEGORY
        return CrawlContentType.GENERIC

    def extract_product_id(self, url: str) -> Optional[str]:
        match = re.search(r"-i(\d+)", url)
        if match:
            return match.group(1)
        match_p = re.search(r"/products/[^/]+-(\d+)\.html", url)
        return match_p.group(1) if match_p else None

    def build_search_url(self, keyword: str, page: int = 1) -> str:
        safe_kw = keyword.strip().replace(" ", "+")
        if page > 1:
            return f"https://www.daraz.pk/catalog/?q={safe_kw}&page={page}"
        return f"https://www.daraz.pk/catalog/?q={safe_kw}"

    def parse_response(self, response: CrawlResponse, content_type: CrawlContentType) -> UniversalCrawlResult:
        canonical_url = self.canonicalize_url(response.url)
        
        if content_type == CrawlContentType.PRODUCT:
            product_id = self.extract_product_id(canonical_url) or "unknown"
            try:
                extraction_res = self.parser.parse(
                    html_content=response.html,
                    url=canonical_url,
                    product_id=product_id,
                    source_engine=response.source_engine,
                )
                return UniversalCrawlResult(
                    crawl_id=f"daraz_{product_id}",
                    url=canonical_url,
                    marketplace=MarketplaceType.DARAZ,
                    content_type=content_type,
                    status=CrawlStatus.COMPLETED if extraction_res.success else CrawlStatus.FAILED,
                    success=extraction_res.success,
                    status_code=response.status_code,
                    source_engine=response.source_engine,
                    duration_ms=response.duration_ms,
                    product=extraction_res.product,
                    raw_html=response.html,
                    errors=extraction_res.errors,
                    warnings=extraction_res.warnings,
                )
            except Exception as e:
                return UniversalCrawlResult(
                    crawl_id=f"daraz_{product_id}",
                    url=canonical_url,
                    marketplace=MarketplaceType.DARAZ,
                    content_type=content_type,
                    status=CrawlStatus.FAILED,
                    success=False,
                    status_code=response.status_code,
                    errors=[f"Daraz product parser error: {e}"],
                )

        # Search / Category parsing
        soup = BeautifulSoup(response.html, "html.parser")
        discovered_urls: List[str] = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.startswith("//"):
                href = f"https:{href}"
            if self.validate_url(href) and self.detect_content_type(href) == CrawlContentType.PRODUCT:
                clean = self.canonicalize_url(href)
                if clean not in discovered_urls:
                    discovered_urls.append(clean)

        return UniversalCrawlResult(
            crawl_id="daraz_discovery",
            url=canonical_url,
            marketplace=MarketplaceType.DARAZ,
            content_type=content_type,
            status=CrawlStatus.COMPLETED,
            success=True,
            status_code=response.status_code,
            discovered_urls=discovered_urls,
            raw_html=response.html,
        )
