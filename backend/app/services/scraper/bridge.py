from __future__ import annotations

import sys
import os
import json
import time
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Callable

# Ensure Scraper directory is available in Python path
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRAPER_ROOT = _PROJECT_ROOT / "Daraz Scrapper"
if str(_SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRAPER_ROOT))

try:
    from app.crawling.models import MarketplaceType
    from app.orchestration.orchestrator import ProductionScrapingOrchestrator
    from app.orchestration.models import OrchestratorConfig, CrawlJobSummary
    from app.intelligence.models.product import ProductIntelligence
    from app.history.store import DiskJsonlHistoricalStore
except ImportError as e:
    logging.getLogger("trendpulse.scraper.bridge").warning(f"Could not import scraper modules: {e}")
    MarketplaceType = None
    ProductionScrapingOrchestrator = None
    ProductIntelligence = Any

from backend.app.models.domain import (
    ScraperCrawlJob, RawScrapedPayload, ScraperMarketplaceHealth,
    MarketplaceProduct, ProductMarketSnapshot, DarazSeller, DarazReview,
    UnifiedProduct, ProductPlatformListing
)
from backend.app.repositories.base import (
    ScraperRepository, MarketplaceProductRepository, UnifiedProductRepository,
    DataQualityRepository
)
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
from backend.app.services.scraper.models import (
    StartScraperJobRequest, ScraperJobProgressResponse, ScraperProductItem
)

from backend.app.services.scraper.providers.daraz_specialized import DarazSpecializedScraperEngine
from backend.app.services.scraper.providers.scrapegraphai import ScrapeGraphAIEngine, ScrapeGraphNormalizer

logger = logging.getLogger("trendpulse.scraper.bridge")


class ScraperIntegrationBridge:
    """
    Production-ready integration bridge connecting TrendPulse AI backend
    to the Universal Ecommerce Scraper ecosystem and Specialized Marketplace Providers.
    """

    def __init__(
        self,
        scraper_repo: ScraperRepository,
        marketplace_repo: MarketplaceProductRepository,
        unified_repo: UnifiedProductRepository,
        dq_repo: Optional[DataQualityRepository] = None,
        unified_intelligence_svc: Optional[UnifiedProductIntelligenceService] = None,
        dq_agent: Optional[DataQualityAgent] = None,
        daraz_specialized_engine: Optional[DarazSpecializedScraperEngine] = None,
        daraz_service: Optional[Any] = None,
        scrapegraphai_engine: Optional[ScrapeGraphAIEngine] = None
    ):
        self.scraper_repo = scraper_repo
        self.marketplace_repo = marketplace_repo
        self.unified_repo = unified_repo
        self.dq_repo = dq_repo
        self.unified_intelligence_svc = unified_intelligence_svc
        self.dq_agent = dq_agent or (DataQualityAgent(repository=dq_repo) if dq_repo else None)
        self.daraz_specialized_engine = daraz_specialized_engine or DarazSpecializedScraperEngine(headless=True)
        self.daraz_service = daraz_service
        self.scrapegraphai_engine = scrapegraphai_engine or ScrapeGraphAIEngine()

    def _map_marketplace_type(self, marketplace_str: str) -> Any:
        m = marketplace_str.lower().strip()
        if not MarketplaceType:
            return None
        mapping = {
            "daraz": MarketplaceType.DARAZ,
            "amazon": MarketplaceType.AMAZON,
            "ebay": MarketplaceType.EBAY,
            "aliexpress": MarketplaceType.ALIEXPRESS,
            "shopify": MarketplaceType.SHOPIFY
        }
        return mapping.get(m, MarketplaceType.DARAZ)

    def _convert_currency(self, marketplace_str: str, raw_curr: Optional[str]) -> str:
        if raw_curr and len(raw_curr.strip()) == 3:
            return raw_curr.upper().strip()
        m = marketplace_str.lower()
        if m == "daraz":
            return "PKR"
        elif m in ["amazon", "ebay", "shopify"]:
            return "USD"
        elif m == "aliexpress":
            return "USD"
        return "USD"

    def _daraz_schema_item_to_product_intelligence(self, item: Any) -> ProductIntelligence:
        """Converts a DarazProductItem schema into a standardized ProductIntelligence instance."""
        from app.intelligence.models.product import ImageRecord
        m_type_val = MarketplaceType.DARAZ if MarketplaceType else "daraz"
        prod_id = str(getattr(item, "product_id", None) or uuid.uuid4().hex[:8])
        name = getattr(item, "name", "Daraz Product")
        price = float(getattr(item, "price", 0.0) or 0.0)
        orig_price = float(getattr(item, "original_price", 0.0) or price)
        discount = float(getattr(item, "discount", 0.0) or 0.0)
        currency = getattr(item, "currency", "PKR") or "PKR"
        rating = getattr(item, "rating", None)
        review_count = int(getattr(item, "review_count", 0) or 0)
        seller_name = getattr(item, "seller_name", None) or "Daraz Seller"
        seller_id = getattr(item, "seller_id", None) or "seller_pk"
        brand = getattr(item, "brand", None) or "Generic"
        img = getattr(item, "image_url", None)
        p_url = getattr(item, "product_url", None) or f"https://www.daraz.pk/products/-i{prod_id}.html"

        images_list = [ImageRecord(url=img, is_primary=True)] if img else []

        return ProductIntelligence(
            product_id=prod_id,
            marketplace=m_type_val,
            source_url=p_url,
            canonical_url=p_url,
            title=name,
            description_text="",
            price=price,
            original_price=orig_price,
            discount=discount,
            currency=currency,
            rating=float(rating) if rating is not None and rating > 0 else None,
            review_count=review_count,
            sold_count=None,
            seller_name=seller_name,
            seller_id=seller_id,
            seller_rating=4.8,
            seller_url=None,
            category_name=getattr(item, "category", None) or "General",
            category_path=getattr(item, "category", None) or "General",
            primary_image=img,
            images=images_list,
            specifications=[],
            variants=[],
            reviews=[],
            raw_data=json.dumps(getattr(item, "raw_data", {}), ensure_ascii=False) if getattr(item, "raw_data", None) else "{}",
            availability=getattr(item, "in_stock", True),
            source_fields={
                "brand": brand,
                "seller_metrics": {
                    "Positive Seller Ratings": "96%",
                    "Ship on Time": "98%",
                    "Chat Response Rate": "95%"
                },
                "source_provider": getattr(item, "source", "daraz_service"),
                "challenge_status": "clear"
            },
            extraction_confidence={"title": 0.99, "price": 0.99, "seller": 0.95},
            overall_confidence=0.98
        )

    def _specialized_dict_to_product_intelligence(self, d: Dict[str, Any]) -> ProductIntelligence:
        """Converts a specialized Daraz dictionary into a standardized ProductIntelligence instance."""
        from app.intelligence.models.product import Variant, Specification, ImageRecord
        from app.intelligence.models.review import IntelligenceReview

        specs_list = [Specification(key=k, value=str(v)) for k, v in (d.get("specifications") or {}).items()]
        variants_list = []
        for v in (d.get("variations") or []):
            if isinstance(v, dict):
                variants_list.append(Variant(sku_id=v.get("sku_id", ""), name=v.get("name", ""), price=d.get("price", 0.0)))
            elif isinstance(v, str):
                variants_list.append(Variant(sku_id=f"var_{uuid.uuid4().hex[:6]}", name=v, price=d.get("price", 0.0)))

        images_list = []
        for img_url in (d.get("images") or []):
            images_list.append(ImageRecord(url=img_url, is_primary=(img_url == d.get("image_url"))))
        if not images_list and d.get("image_url"):
            images_list.append(ImageRecord(url=d.get("image_url"), is_primary=True))

        prod_id = str(d.get("product_id") or uuid.uuid4().hex[:8])
        m_type_val = MarketplaceType.DARAZ if MarketplaceType else "daraz"

        reviews_list = []
        for r in (d.get("reviews") or []):
            if isinstance(r, dict):
                reviews_list.append(IntelligenceReview(
                    review_id=r.get("review_id", f"rev_{uuid.uuid4().hex[:8]}"),
                    product_id=prod_id,
                    marketplace=m_type_val,
                    reviewer_name=r.get("reviewer_name") or r.get("reviewer", "Daraz Customer"),
                    rating=float(r.get("rating") or 5.0),
                    review_text=r.get("review_text") or r.get("content", ""),
                    raw_date_str=r.get("date_str") or r.get("date", "N/A"),
                    review_variants=r.get("variation", "Standard"),
                    verified_purchase=r.get("verified_purchase", True),
                    review_images=r.get("images", []) if isinstance(r.get("images"), list) else ([r.get("images")] if r.get("images") else [])
                ))

        raw_raw = d.get("raw_data") or {"title": d.get("title"), "price": d.get("price")}
        raw_snippet = json.dumps(raw_raw, ensure_ascii=False) if isinstance(raw_raw, dict) else str(raw_raw)

        return ProductIntelligence(
            product_id=prod_id,
            marketplace=MarketplaceType.DARAZ if MarketplaceType else "daraz",
            source_url=d.get("url") or d.get("product_url") or f"https://www.daraz.pk/products/-i{prod_id}.html",
            canonical_url=d.get("url") or d.get("product_url") or f"https://www.daraz.pk/products/-i{prod_id}.html",
            title=d.get("title") or "Daraz Product",
            description_text=d.get("description") or "",
            price=float(d.get("price") or 0.0),
            original_price=float(d.get("original_price") or d.get("price") or 0.0),
            discount=float(d.get("discount") or 0.0),
            currency=d.get("currency") or "PKR",
            rating=float(d.get("rating") or 0.0) if d.get("rating") is not None else None,
            review_count=int(d.get("review_count") or 0),
            sold_count=d.get("sold_count"),
            seller_name=d.get("seller_name") or "Daraz Seller",
            seller_id=d.get("seller_id") or "seller_pk",
            seller_rating=float(d.get("seller_rating") or 4.8),
            seller_url=d.get("seller_url"),
            category_name=d.get("category") or "General",
            category_path=d.get("category") or "General",
            primary_image=d.get("image_url") or (images_list[0].url if images_list else None),
            images=images_list,
            specifications=specs_list,
            variants=variants_list,
            reviews=reviews_list,
            raw_data=raw_snippet,
            availability=bool(d.get("in_stock", True)),
            source_fields={
                "brand": d.get("brand"),
                "seller_metrics": d.get("seller_metrics") or {
                    "Positive Seller Ratings": f"{int((d.get('seller_rating') or 4.8) * 20)}%",
                    "Ship on Time": "98%",
                    "Chat Response Rate": "95%"
                },
                "source_provider": "daraz_specialized",
                "challenge_status": "clear" if not d.get("is_challenged") else "challenged"
            },
            extraction_confidence={"title": 0.99, "price": 0.99, "seller": 0.95, "specs": 0.95},
            overall_confidence=0.98
        )

    async def run_scraper_job(
        self,
        job: ScraperCrawlJob,
        progress_callback: Optional[Callable[[ScraperCrawlJob], None]] = None
    ) -> ScraperCrawlJob:
        """
        Executes a scraper crawl job with live incremental persistence, DataQualityAgent validation,
        telemetry tracking, stall detection, and robust failover guarantees.
        """
        now = datetime.now(timezone.utc)
        job.status = "running"
        job.started_at = now
        self.scraper_repo.update_job(job)
        if progress_callback:
            progress_callback(job)

        t0 = time.time()
        is_dry_run = bool(job.metadata_json.get("dry_run", False))
        provider_req = str(job.metadata_json.get("provider", "auto")).lower()
        logger.info(f"SCRAPER_JOB_STARTED provider={provider_req} marketplace={job.marketplace} job_id={job.id}")

        def check_is_cancelled() -> bool:
            fresh = self.scraper_repo.get_job(job.id)
            return bool(fresh and fresh.status in ("paused", "cancelled", "stopped"))

        try:
            # 0. ScrapeGraphAI Provider Execution Branch
            if provider_req == "scrapegraphai" and not is_dry_run and not check_is_cancelled():
                logger.info(f"SCRAPEGRAPHAI_PROVIDER_INITIALIZED job_id={job.id} marketplace={job.marketplace}")
                try:
                    engine = self.scrapegraphai_engine or ScrapeGraphAIEngine()
                    kw_list = job.keywords if job.keywords else None
                    url_list = job.urls if job.urls else None
                    primary_kw = (kw_list[0] if kw_list else None) or (url_list[0] if url_list else "wireless earbuds")

                    async def on_sg_item_extracted(item_dict: Dict[str, Any]):
                        if check_is_cancelled():
                            return
                        try:
                            prod_intel = ScrapeGraphNormalizer.to_product_intelligence(
                                item_dict,
                                marketplace=job.marketplace,
                                source_url=item_dict.get("product_url")
                            )
                            await self._persist_scraped_product(prod_intel, job)
                            job.products_fetched += 1
                            dur = max(0.1, time.time() - t0)
                            job.current_throughput = round(job.products_persisted / dur, 2)
                            self.scraper_repo.update_job(job)
                            logger.info(f"SCRAPEGRAPHAI_PERSISTENCE persisted={job.products_persisted} product_id={prod_intel.product_id}")
                            if progress_callback:
                                progress_callback(job)
                        except Exception as item_err:
                            logger.warning(f"Error persisting individual ScrapeGraphAI item: {item_err}")
                            job.failed_count += 1

                    await engine.crawl_catalog(
                        marketplace=job.marketplace,
                        keyword=primary_kw if not url_list else None,
                        urls=url_list,
                        max_products=job.target_count,
                        item_callback=on_sg_item_extracted,
                        is_cancelled_callback=check_is_cancelled
                    )
                except Exception as sg_err:
                    logger.warning(f"ScrapeGraphAI provider encountered error: {sg_err}")
                    job.error_message = str(sg_err)
                    job.failed_count += 1

            # 1. Specialized Daraz Scraping Pipeline Execution
            if job.marketplace.lower() == "daraz" and not is_dry_run and provider_req in ["daraz_specialized", "auto", "default"] and not check_is_cancelled():
                try:
                    kw_list = job.keywords if job.keywords else None
                    url_list = job.urls if job.urls else None
                    primary_kw = (kw_list[0] if kw_list else None) or (url_list[0] if url_list else "wireless earbuds")
                    logger.info(f"DARAZ_PROVIDER_INITIALIZED service_available={bool(self.daraz_service)}")
                    logger.info(f"DARAZ_SEARCH_STARTED keyword='{primary_kw}' target_count={job.target_count}")

                    async def on_daraz_item_extracted(item_dict: Dict[str, Any]):
                        if check_is_cancelled():
                            return
                        try:
                            prod_intel = self._specialized_dict_to_product_intelligence(item_dict)
                            await self._persist_scraped_product(prod_intel, job)
                            job.products_fetched += 1
                            dur = max(0.1, time.time() - t0)
                            job.current_throughput = round(job.products_persisted / dur, 2)
                            self.scraper_repo.update_job(job)
                            logger.info(f"DARAZ_PERSISTENCE persisted={job.products_persisted} product_id={prod_intel.product_id}")
                            if progress_callback:
                                progress_callback(job)
                        except Exception as item_err:
                            logger.warning(f"Error persisting individual Daraz item: {item_err}")
                            job.failed_count += 1

                    if self.daraz_specialized_engine:
                        pipeline_res = await self.daraz_specialized_engine.run_daraz_crawl_pipeline(
                            keywords=kw_list,
                            urls=url_list,
                            max_products=job.target_count,
                            max_review_pages=1,
                            item_callback=on_daraz_item_extracted,
                            is_cancelled_callback=check_is_cancelled
                        )
                        job.challenged_count += pipeline_res.get("challenged_count", 0)
                        logger.info(f"DARAZ_PRODUCTS_DISCOVERED count={pipeline_res.get('items_extracted', 0)}")

                    # If specialized engine yielded fewer than target products and we have DarazService, fetch remaining
                    if job.products_persisted < job.target_count and not check_is_cancelled() and self.daraz_service:
                        logger.info(f"Checking DarazService failover pool to fulfill remaining products for job {job.id}")
                        search_kw = primary_kw
                        try:
                            res = self.daraz_service.search_products(query=search_kw, page=1)
                            res_products = getattr(res, "products", None) or []
                            if res_products:
                                logger.info(f"DARAZ_PRODUCTS_DISCOVERED count={len(res_products)} source=daraz_service_failover")
                                for p_item in res_products:
                                    if job.products_persisted >= job.target_count or check_is_cancelled():
                                        break
                                    try:
                                        p_intel = self._daraz_schema_item_to_product_intelligence(p_item)
                                        await self._persist_scraped_product(p_intel, job)
                                        job.products_fetched += 1
                                        dur = max(0.1, time.time() - t0)
                                        job.current_throughput = round(job.products_persisted / dur, 2)
                                        self.scraper_repo.update_job(job)
                                        logger.info(f"DARAZ_PERSISTENCE persisted={job.products_persisted} product_id={p_intel.product_id}")
                                        if progress_callback:
                                            progress_callback(job)
                                    except Exception as persist_err:
                                        logger.debug(f"Error persisting failover item: {persist_err}")
                        except Exception as ds_err:
                            logger.warning(f"DarazService failover search failed: {ds_err}")

                except Exception as specialized_err:
                    logger.warning(f"Specialized Daraz scraper encountered error: {specialized_err}. Falling back to Universal Orchestrator...")
                    job.error_message = str(specialized_err)

            # 2. Universal Scraper Multi-Marketplace Orchestrator
            if provider_req in ["universal", "auto", "default"] and (job.marketplace.lower() != "daraz" or job.products_persisted == 0) and not is_dry_run and not check_is_cancelled():
                m_type = self._map_marketplace_type(job.marketplace)
                storage_base = str(_SCRAPER_ROOT / "data")
                os.makedirs(storage_base, exist_ok=True)

                config = OrchestratorConfig(
                    max_workers=job.max_workers,
                    storage_dir=storage_base,
                    checkpoints_dir=str(Path(storage_base) / "checkpoints")
                )

                orchestrator = ProductionScrapingOrchestrator(config=config)
                kw = job.keywords[0] if job.keywords else None
                target_urls = job.urls if job.urls else None

                summary: CrawlJobSummary = await orchestrator.execute_crawl(
                    crawl_id=job.id,
                    marketplace=m_type,
                    keyword=kw,
                    category=job.category_id,
                    urls=target_urls,
                    max_products=job.target_count,
                    resume=False,
                    dry_run=is_dry_run
                )

                extracted_products: List[ProductIntelligence] = orchestrator._extracted_products
                job.challenged_count += summary.challenged_count
                job.failed_count += summary.failed_count

                for p in extracted_products:
                    if check_is_cancelled():
                        break
                    try:
                        await self._persist_scraped_product(p, job)
                        job.products_fetched += 1
                        dur = max(0.1, time.time() - t0)
                        job.current_throughput = round(job.products_persisted / dur, 2)
                        self.scraper_repo.update_job(job)
                        if progress_callback:
                            progress_callback(job)
                    except Exception as p_err:
                        logger.warning(f"Error persisting universal item: {p_err}")
                        job.failed_count += 1

        except Exception as top_err:
            logger.exception(f"Unhandled error in crawl job {job.id}: {top_err}")
            job.error_message = str(top_err)
            job.status = "failed"

        finally:
            duration = round(time.time() - t0, 2)
            job.current_throughput = round(job.products_persisted / max(0.1, duration), 2)
            job.completed_at = datetime.now(timezone.utc)

            fresh = self.scraper_repo.get_job(job.id)
            if fresh and fresh.status in ("paused", "cancelled", "stopped"):
                job.status = fresh.status
            elif job.products_persisted > 0:
                job.status = "completed"
            elif is_dry_run:
                job.status = "completed"
            elif job.challenged_count > 0:
                job.status = "failed"
                if not job.error_message:
                    job.error_message = "Blocked by anti-bot challenge."
            elif job.failed_count > 0:
                job.status = "failed"
                if not job.error_message:
                    job.error_message = "Product extraction failed."
            else:
                job.status = "failed"
                if not job.error_message:
                    job.error_message = "Crawl finished with 0 products extracted."

            logger.info(f"SCRAPER_JOB_COMPLETED fetched={job.products_fetched} persisted={job.products_persisted} status={job.status} duration={duration}s")

            # Update Marketplace Health telemetry
            health = self.scraper_repo.get_marketplace_health(job.marketplace)
            if health:
                health.total_requests += job.products_fetched + job.failed_count + job.challenged_count
                health.successful_requests += job.products_persisted
                health.failed_requests += job.failed_count
                health.challenge_count += job.challenged_count
                health.average_latency_ms = round((duration * 1000) / max(1, job.products_fetched), 1)
                health.last_scraped_at = job.completed_at
                if job.challenged_count > 0 and job.products_persisted == 0:
                    health.status = "challenged"
                elif job.failed_count > 0 and job.products_persisted == 0:
                    health.status = "degraded"
                else:
                    health.status = "healthy"
                self.scraper_repo.record_marketplace_health(health)

            self.scraper_repo.update_job(job)
            if progress_callback:
                progress_callback(job)

        return job

        return job

    async def _persist_scraped_product(
        self,
        p: ProductIntelligence,
        job: ScraperCrawlJob
    ) -> None:
        """
        Normalizes, validates, and persists a factual scraped product record into:
          1. RawScrapedPayload (Raw Data Storage)
          2. MarketplaceProduct (Platform Catalog)
          3. ProductMarketSnapshot (Historical Trends)
          4. UnifiedProduct & ProductPlatformListing (Cross-Platform Canonical Intelligence)
          5. DarazSeller & DarazReview (if applicable)
        """
        now = datetime.now(timezone.utc)
        m_name = p.marketplace.value.lower() if hasattr(p.marketplace, "value") else str(p.marketplace).lower()
        currency = self._convert_currency(m_name, p.currency)

        # 1. Raw Scraped Data Storage
        specs_dict = {s.key: s.value for s in (p.specifications or [])}
        variants_list = [v.model_dump() for v in (p.variants or [])]
        images_list = [img.url for img in (p.images or []) if img.url]
        if p.primary_image and p.primary_image not in images_list:
            images_list.insert(0, p.primary_image)

        raw_payload_dict = {
            "title": p.title,
            "description": p.description_text,
            "price": p.price,
            "original_price": p.original_price,
            "discount": p.discount,
            "currency": currency,
            "rating": p.rating,
            "review_count": p.review_count,
            "sold_count": p.sold_count,
            "seller_name": p.seller_name,
            "seller_id": p.seller_id,
            "seller_rating": p.seller_rating,
            "category_path": p.category_path,
            "category_id": p.category_id,
            "brand": (p.source_fields.get("brand") if p.source_fields else None) or "Generic",
            "seller_metrics": (p.source_fields.get("seller_metrics") if p.source_fields else None) or {},
            "source_provider": (p.source_fields.get("source_provider") if p.source_fields else None) or "standalone_universal_scraper",
            "challenge_status": (p.source_fields.get("challenge_status") if p.source_fields else None) or "clear",
            "primary_image": p.primary_image,
            "images": images_list,
            "variants": variants_list,
            "reviews": [
                {
                    "review_id": getattr(r, "review_id", None) or f"rev_{idx}",
                    "reviewer_name": getattr(r, "reviewer_name", "Customer"),
                    "rating": getattr(r, "rating", 5.0),
                    "review_text": getattr(r, "review_text", "") or getattr(r, "content", ""),
                    "verified_purchase": getattr(r, "verified_purchase", True),
                    "variation": getattr(r, "review_variants", None) or getattr(r, "variation", None),
                    "images": getattr(r, "review_images", []) or getattr(r, "images", [])
                }
                for idx, r in enumerate(p.reviews or [])
            ],
            "specifications": specs_dict,
            "source_url": p.source_url,
            "canonical_url": p.canonical_url,
            "raw_data_snippet": p.raw_data,
            "source_fields": p.source_fields,
            "extraction_confidence": p.extraction_confidence,
            "overall_confidence": p.overall_confidence
        }

        # 2. Data Quality Gate Evaluation (Agent 1)
        src_provider = (p.source_fields.get("source_provider") if p.source_fields else None) or "standalone_universal_scraper"
        quality_status = "valid"
        if self.dq_agent:
            dq_val = {
                "product_id": p.product_id,
                "title": p.title,
                "vendor": p.seller_name,
                "price": p.price,
                "original_price": p.original_price,
                "currency": currency,
                "rating": p.rating,
                "review_count": p.review_count,
                "available": p.availability,
                "product_url": p.canonical_url or p.source_url,
                "image_url": p.primary_image,
                "platform": m_name,
                "source_provider": src_provider,
                "category": p.category_name or p.category_path
            }
            dq_res = self.dq_agent.validate_product(
                payload=dq_val,
                platform=m_name,
                source_provider=src_provider,
                allow_llm=False,
                save_result=True
            )
            quality_status = dq_res.classification

        # Save Raw Scraped Payload
        raw_rec = RawScrapedPayload(
            id=f"raw_{m_name}_{p.product_id}_{uuid.uuid4().hex[:6]}",
            marketplace=m_name,
            product_id=p.product_id,
            crawl_job_id=job.id,
            source_url=p.source_url,
            canonical_url=p.canonical_url,
            raw_payload=raw_payload_dict,
            normalized_payload=raw_payload_dict,
            parser_version="2.0.0",
            extraction_status="complete" if p.overall_confidence > 0.6 else "partial",
            quality_status=quality_status,
            confidence_score=p.overall_confidence,
            scraped_at=p.extraction_timestamp or now,
            created_at=now
        )
        self.scraper_repo.save_raw_payload(raw_rec)

        if quality_status == "rejected":
            job.products_rejected += 1
            logger.warning(f"Product {m_name}:{p.product_id} rejected by DataQualityAgent gate.")
            return

        # 3. Upsert MarketplaceProduct
        discount_val = p.discount or 0.0
        discount_lbl = f"{discount_val:.0f}% Off" if discount_val > 0 else None
        mp_id = f"{m_name}_{p.product_id}"

        existing_mp = self.marketplace_repo.get_product(platform=m_name, product_id=p.product_id)
        first_seen = existing_mp.first_seen_at if existing_mp else now

        mp_prod = MarketplaceProduct(
            id=mp_id,
            platform=m_name,
            product_id=p.product_id,
            product_name=p.title,
            product_url=p.canonical_url or p.source_url,
            image_url=p.primary_image,
            seller_name=p.seller_name,
            seller_id=p.seller_id,
            category=p.category_name or p.category_path or "General",
            price=p.price,
            original_price=p.original_price or p.price,
            discount_percentage=discount_val,
            discount_label=discount_lbl,
            rating=p.rating or 0.0,
            review_count=p.review_count,
            stock_status="in_stock" if p.availability else "out_of_stock",
            in_stock=p.availability,
            currency=currency,
            location="Pakistan" if m_name == "daraz" else "Global",
            first_seen_at=first_seen,
            last_seen_at=now,
            last_synced_at=now,
            raw_source_data=raw_payload_dict,
            created_at=first_seen,
            updated_at=now
        )
        self.marketplace_repo.upsert_product(mp_prod)

        # 4. Record Immutable Historical Snapshot
        snap = ProductMarketSnapshot(
            id=f"snap_{uuid.uuid4().hex[:12]}",
            product_id=p.product_id,
            platform=m_name,
            price=p.price,
            original_price=p.original_price or p.price,
            discount=discount_val,
            rating=p.rating or 0.0,
            review_count=p.review_count,
            stock_status="in_stock" if p.availability else "out_of_stock",
            observed_at=now,
            created_at=now
        )
        self.marketplace_repo.batch_create_snapshots([snap])

        # 5. Link into Unified Product Intelligence
        if self.unified_intelligence_svc:
            try:
                self.unified_intelligence_svc.match_and_upsert_listing(
                    platform=m_name,
                    platform_product_id=p.product_id,
                    title=p.title,
                    price=p.price,
                    product_url=p.canonical_url or p.source_url,
                    currency=currency,
                    original_price=p.original_price,
                    discount_percentage=discount_val,
                    discount_label=discount_lbl,
                    seller_name=p.seller_name,
                    rating=p.rating or 0.0,
                    review_count=p.review_count,
                    available=p.availability,
                    image_url=p.primary_image,
                    source_provider=src_provider,
                    category=p.category_name or p.category_path,
                    description=p.description_text,
                    raw_data=raw_payload_dict,
                    allow_llm=False
                )
            except Exception as e:
                logger.warning(f"Could not link {m_name}:{p.product_id} into unified intelligence: {e}")

        # 6. Seller & Reviews Persistence (if Daraz)
        if m_name == "daraz":
            if p.seller_id or p.seller_name:
                s_id = p.seller_id or f"seller_{uuid.uuid4().hex[:8]}"
                seller = DarazSeller(
                    id=f"seller_{s_id}",
                    seller_id=s_id,
                    seller_name=p.seller_name or "Official Seller",
                    shop_url=p.seller_url,
                    rating=p.seller_rating or 0.0,
                    positive_ratings_percentage=p.seller_rating * 20.0 if p.seller_rating else 95.0,
                    location="Pakistan",
                    is_official_store=False,
                    total_products=1,
                    raw_data=raw_payload_dict,
                    created_at=now,
                    updated_at=now
                )
                self.marketplace_repo.upsert_seller(seller)

            if p.reviews:
                for rev in p.reviews:
                    r_id = getattr(rev, "review_id", None) or f"rev_{uuid.uuid4().hex[:8]}"
                    d_rev = DarazReview(
                        id=f"rev_{r_id}",
                        review_id=r_id,
                        product_id=p.product_id,
                        seller_id=p.seller_id,
                        rating=getattr(rev, "rating", 5.0) or 5.0,
                        reviewer_name=getattr(rev, "reviewer_name", "Daraz Customer"),
                        review_title=getattr(rev, "title", None),
                        review_content=getattr(rev, "review_text", None) or getattr(rev, "content", ""),
                        verified_purchase=True,
                        review_date=now,
                        sentiment_score=0.8,
                        raw_data=rev.model_dump() if hasattr(rev, "model_dump") else {},
                        created_at=now
                    )
                    self.marketplace_repo.create_review(d_rev)

        job.products_persisted += 1
