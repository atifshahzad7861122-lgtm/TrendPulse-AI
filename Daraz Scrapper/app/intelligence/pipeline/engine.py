"""Universal Product Intelligence Extraction Engine orchestrator."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import uuid

from app.core.logging import logger
from app.crawling.challenge import UniversalChallengeDetector
from app.crawling.engine import UniversalCrawlingEngine
from app.crawling.models import CrawlContentType, CrawlRequest, CrawlResponse, MarketplaceType
from app.discovery.models import ProductTarget
from app.intelligence.history.snapshot_manager import HistoricalSnapshotManager
from app.intelligence.marketplaces import (
    AliExpressIntelligenceExtractor,
    AmazonIntelligenceExtractor,
    BaseMarketplaceExtractor,
    DarazIntelligenceExtractor,
    EbayIntelligenceExtractor,
    ShopifyIntelligenceExtractor,
)
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import ExtractionStatus, FieldConfidence, IntelligenceExtractionResult
from app.intelligence.pipeline.config import IntelligencePipelineConfig
from app.intelligence.validation.confidence import ConfidenceScorer
from app.intelligence.validation.quality_gate import DataQualityGate
from app.storage.base import BaseStorage
from app.storage.repository import InMemoryStorage


class ProductIntelligenceEngine:
    """
    High-level orchestrator for multi-marketplace product intelligence extraction.
    Takes discovered URLs / ProductTargets, crawls via UniversalCrawlingEngine,
    delegates to dedicated marketplace extractors, validates via DataQualityGate,
    computes field-level confidence, and records timestamped historical snapshots.
    """

    def __init__(
        self,
        config: Optional[IntelligencePipelineConfig] = None,
        crawler_engine: Optional[UniversalCrawlingEngine] = None,
        storage: Optional[BaseStorage] = None,
        snapshot_manager: Optional[HistoricalSnapshotManager] = None,
    ):
        self.config = config or IntelligencePipelineConfig()
        self.crawler = crawler_engine or UniversalCrawlingEngine()
        self.detector = UniversalChallengeDetector()
        self.storage = storage or InMemoryStorage()
        self.snapshot_manager = snapshot_manager or HistoricalSnapshotManager(
            storage=self.storage,
            snapshots_dir=self.config.snapshots_dir,
        )

        # Pluggable marketplace extractors
        self.extractors: Dict[MarketplaceType, BaseMarketplaceExtractor] = {
            MarketplaceType.DARAZ: DarazIntelligenceExtractor(),
            MarketplaceType.AMAZON: AmazonIntelligenceExtractor(),
            MarketplaceType.EBAY: EbayIntelligenceExtractor(),
            MarketplaceType.ALIEXPRESS: AliExpressIntelligenceExtractor(),
            MarketplaceType.SHOPIFY: ShopifyIntelligenceExtractor(),
        }

    def register_extractor(self, extractor: BaseMarketplaceExtractor) -> None:
        """Register custom marketplace extractor."""
        self.extractors[extractor.marketplace_type] = extractor

    def resolve_extractor(self, url: str, explicit_marketplace: Optional[MarketplaceType] = None) -> BaseMarketplaceExtractor:
        """Resolve suitable marketplace extractor."""
        if explicit_marketplace and explicit_marketplace in self.extractors:
            return self.extractors[explicit_marketplace]

        for extractor in self.extractors.values():
            if extractor.validate_url(url):
                return extractor

        # Fallback heuristic
        if "myshopify.com" in url.lower() or "/products/" in url.lower():
            return self.extractors[MarketplaceType.SHOPIFY]

        return self.extractors[MarketplaceType.DARAZ]

    async def extract_product(
        self,
        target: Union[str, ProductTarget],
        marketplace: Optional[MarketplaceType] = None,
        force_refresh: bool = False,
    ) -> IntelligenceExtractionResult:
        """
        Extract complete product intelligence for a single target.
        """
        url = target.url if isinstance(target, ProductTarget) else str(target)
        extractor = self.resolve_extractor(url, marketplace)
        prod_id = extractor.extract_product_id(url) or "unknown_id"
        extraction_id = f"ext_{uuid.uuid4().hex[:8]}"

        # 1. Crawl URL using Universal Crawling Engine
        crawl_req = CrawlRequest(
            url=url,
            marketplace=extractor.marketplace_type,
            content_type=CrawlContentType.PRODUCT,
            force_refresh=force_refresh,
        )
        crawl_resp = await self.crawler.crawler.crawl(crawl_req)

        # 2. Check for Network Failure / Target Unavailable
        if crawl_resp.status_code == 0:
            err_msg = crawl_resp.metadata.get("error", "Host resolution / DNS failure or network unreachable")
            logger.warning(f"Network / DNS failure reaching {url}: {err_msg}")
            return IntelligenceExtractionResult(
                extraction_id=extraction_id,
                product_id=prod_id,
                marketplace=extractor.marketplace_type,
                url=url,
                status=ExtractionStatus.FAILED,
                success=False,
                status_code=0,
                errors=[f"Target unavailable or network error: {err_msg}"],
            )

        # 3. Intercept Bot Challenge / Anti-Bot Block using UniversalChallengeDetector
        challenge_check = self.detector.detect(crawl_resp.status_code, crawl_resp.html, str(crawl_resp.url))
        if challenge_check.is_challenge or crawl_resp.status_code in (403, 429) or "challenge" in (crawl_resp.source_engine or ""):
            reason = challenge_check.reason or f"Blocked with status {crawl_resp.status_code}"
            logger.warning(f"Challenge encountered extracting {url}: {reason}. Pausing for manual intervention.")
            return IntelligenceExtractionResult(
                extraction_id=extraction_id,
                product_id=prod_id,
                marketplace=extractor.marketplace_type,
                url=url,
                status=ExtractionStatus.CHALLENGE,
                success=False,
                status_code=crawl_resp.status_code,
                errors=[f"Bot challenge detected: {reason}. Paused for manual intervention."],
                raw_payload=crawl_resp.html if self.config.preserve_raw_payloads else None,
            )

        # 3. Extract Intelligence via Marketplace Adapter
        try:
            result = extractor.extract_intelligence(crawl_resp)
        except Exception as e:
            logger.error(f"Extractor failed on {url}: {e}", exc_info=True)
            return IntelligenceExtractionResult(
                extraction_id=extraction_id,
                product_id=prod_id,
                marketplace=extractor.marketplace_type,
                url=url,
                status=ExtractionStatus.FAILED,
                success=False,
                status_code=crawl_resp.status_code,
                errors=[f"Extractor exception: {e}"],
            )

        if not result.success or not result.product:
            return result

        product = result.product

        # 4. Data Quality Gate Validation
        if self.config.enforce_quality_gate:
            is_valid, qg_errors, qg_warnings = DataQualityGate.validate(product)
            product.extraction_warnings.extend(qg_warnings)
            result.warnings.extend(qg_warnings)

            if not is_valid:
                result.errors.extend(qg_errors)
                result.status = ExtractionStatus.PARTIAL_SUCCESS if product.title and product.price > 0 else ExtractionStatus.FAILED
                result.success = (result.status == ExtractionStatus.PARTIAL_SUCCESS)

        # 5. Field-Level Confidence Scoring
        scores, levels, overall_confidence = ConfidenceScorer.score(product)
        product.extraction_confidence = scores
        product.overall_confidence = overall_confidence
        result.confidence_scores = scores
        result.confidence_levels = levels
        result.overall_confidence = overall_confidence

        # 6. Capture Point-in-Time Historical Snapshot
        if self.config.record_historical_snapshots and result.success:
            snapshot = self.snapshot_manager.create_snapshot(product)
            result.snapshot = snapshot
            await self.snapshot_manager.record_snapshot(snapshot)

        # 7. Preserve Raw Payload if configured
        if self.config.preserve_raw_payloads:
            product.raw_data = crawl_resp.html[:2000] if crawl_resp.html else None
            result.raw_payload = crawl_resp.html[:2000] if crawl_resp.html else None

        return result

    async def extract_batch(
        self,
        targets: List[Union[str, ProductTarget]],
        marketplace: Optional[MarketplaceType] = None,
        force_refresh: bool = False,
    ) -> List[IntelligenceExtractionResult]:
        """
        Extract batch of products concurrently with bounded semaphore.
        Isolated failures will never abort the full batch.
        """
        sem = asyncio.Semaphore(self.config.max_concurrency)

        async def _worker(t: Union[str, ProductTarget]) -> IntelligenceExtractionResult:
            async with sem:
                try:
                    return await self.extract_product(t, marketplace=marketplace, force_refresh=force_refresh)
                except Exception as e:
                    url_str = t.url if isinstance(t, ProductTarget) else str(t)
                    logger.error(f"Unhandled extraction error for {url_str}: {e}")
                    return IntelligenceExtractionResult(
                        extraction_id=f"ext_{uuid.uuid4().hex[:8]}",
                        product_id="error",
                        marketplace=marketplace or MarketplaceType.DARAZ,
                        url=url_str,
                        status=ExtractionStatus.FAILED,
                        success=False,
                        errors=[f"Unhandled pipeline failure: {e}"],
                    )

        tasks = [_worker(t) for t in targets]
        return await asyncio.gather(*tasks)
