"""Product extraction engine orchestrating HTTP-first retrieval, browser fallback, deduplication, and batch persistence."""

import asyncio
from typing import List, Optional, Set, Tuple, Union
from playwright.async_api import BrowserContext, Page

from app.clients.browser_client import AsyncBrowserClient
from app.clients.http_client import AsyncHttpClient
from app.core.config import Settings, get_settings
from app.core.exceptions import ChallengeDetectedError, NetworkError, ParserError
from app.core.logging import logger
from app.core.rate_limiter import AsyncRateLimiter
from app.discovery.detector import ChallengeDetector, challenge_detector
from app.discovery.manual_intervention import ManualInterventionManager, manual_intervention_manager
from app.discovery.models import ProductTarget
from app.discovery.normalizer import extract_product_id, normalize_url
from app.extraction.config import DarazExtractionConfig, default_extraction_config
from app.extraction.models import ExtractionResult
from app.extraction.parser import ProductParser
from app.extraction.validator import ValidationStatus
from app.core.checkpoint import CheckpointManager
from app.core.deduplication import ProductDeduplicator
from app.storage.base import BaseStorage


class DarazProductExtractionEngine:
    """Production extraction engine orchestrating multi-source product data harvesting and persistence."""

    SCROLLING_SCRIPT_PRODUCT = """
    async () => {
        const distance = 400;
        const delay = 200;
        while (document.scrollingElement.scrollTop + window.innerHeight < document.scrollingElement.scrollHeight) {
            document.scrollingElement.scrollBy(0, distance);
            await new Promise((resolve) => setTimeout(resolve, delay));
        }
    }
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        config: Optional[DarazExtractionConfig] = None,
        http_client: Optional[AsyncHttpClient] = None,
        browser_client: Optional[AsyncBrowserClient] = None,
        parser: Optional[ProductParser] = None,
        storage: Optional[BaseStorage] = None,
        deduplicator: Optional[ProductDeduplicator] = None,
        detector: Optional[ChallengeDetector] = None,
        intervention_manager: Optional[ManualInterventionManager] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        self.settings = settings or get_settings()
        self.config = config or default_extraction_config
        self.http_client = http_client or AsyncHttpClient(settings=self.settings)
        self.browser_client = browser_client or AsyncBrowserClient(settings=self.settings)
        self.parser = parser or ProductParser(config=self.config)
        self.storage = storage
        self.deduplicator = deduplicator or ProductDeduplicator()
        self.detector = detector or challenge_detector
        self.intervention_manager = intervention_manager or manual_intervention_manager
        self.checkpoint_manager = checkpoint_manager

        self.rate_limiter = AsyncRateLimiter(settings=self.settings)
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        self._shared_context: Optional[BrowserContext] = None

        # Statistics
        self.total_processed = 0
        self.http_success_count = 0
        self.browser_fallback_count = 0
        self.duplicates_prevented = 0
        self.validation_passed_count = 0
        self.validation_warning_count = 0
        self.validation_rejected_count = 0

    async def _fetch_http(self, url: str) -> Tuple[int, str]:
        """Fetch product page using fast async HTTP client."""
        try:
            await self.rate_limiter.acquire(url=url)
            response = await self.http_client.get(url)
            return response.status_code, response.text
        except ChallengeDetectedError as e:
            return e.status_code or 403, ""
        except NetworkError as e:
            return e.status_code or 500, ""
        except Exception:
            return 500, ""

    async def _fetch_browser(self, url: str, crawl_id: Optional[str] = None) -> Tuple[int, str]:
        """Fetch product page using headless Playwright browser with scrolling for lazy content."""
        if not self._shared_context:
            self._shared_context = await self.browser_client.new_context()

        page: Page = await self.browser_client.new_page(context=self._shared_context)
        try:
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=int(self.config.browser_timeout_seconds * 1000),
            )
            status_code = response.status if response else 200

            # Wait briefly for dynamic elements or initial hydration
            try:
                await page.wait_for_selector(".pdp-price, .pdp-mod-product-badge-title, h1", timeout=5000)
            except Exception:
                pass

            # Execute smooth scrolling to trigger lazy images and review modules
            if self.config.scroll_pages_for_lazy_loading:
                try:
                    await page.evaluate(self.SCROLLING_SCRIPT_PRODUCT)
                    await asyncio.sleep(self.config.scroll_delay_ms / 1000.0)
                except Exception:
                    pass

            html_content = await page.content()
            return status_code, html_content
        finally:
            await page.close()

    async def extract_product(
        self,
        target: Union[str, ProductTarget],
        use_browser: bool = False,
        crawl_id: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract complete product information for a target URL or ProductTarget instance.
        Executes HTTP-first retrieval with automatic Playwright fallback on dynamic/incomplete markup.
        """
        url = target.url if isinstance(target, ProductTarget) else str(target)
        product_id = target.product_id if isinstance(target, ProductTarget) else extract_product_id(url)
        canonical_url = normalize_url(url)

        # Check pause on manual intervention
        if self.intervention_manager.is_paused:
            resumed = await self.intervention_manager.wait_until_resumed(timeout=5.0)
            if not resumed:
                logger.warning("Manual intervention wait timed out (5.0s) in extraction engine.")

        async with self._semaphore:
            status_code = 200
            html_content = ""
            source_engine = "browser" if use_browser else "http"

            if use_browser:
                fetch_res = await self._fetch_browser(canonical_url)
                status_code, html_content = fetch_res[0], fetch_res[1]
                source_engine = "browser"
                self.browser_fallback_count += 1
            else:
                # 1. Attempt HTTP-first extraction
                if self.config.enable_http_first:
                    fetch_res = await self._fetch_http(canonical_url)
                    status_code, html_content = fetch_res[0], fetch_res[1]

                # Initial parse to inspect data completeness
                init_result = None
                if status_code == 200 and html_content:
                    try:
                        init_result = self.parser.parse(
                            html_content=html_content,
                            url=canonical_url,
                            product_id=product_id,
                            source_engine="http",
                        )
                    except Exception:
                        init_result = None

                is_csr_stub = (
                    '"renderMode":"CSR"' in html_content
                    and not any(k in html_content for k in ["pdp-mod-product-badge-title", "pdp-price", "pdp-product-detail"])
                )
                is_incomplete = (
                    init_result is None
                    or not init_result.product
                    or init_result.product.price == 0.0
                    or init_result.overall_confidence < self.config.min_overall_confidence
                )

                needs_browser = (
                    self.config.auto_browser_fallback
                    and (
                        not html_content
                        or status_code != 200
                        or is_csr_stub
                        or is_incomplete
                    )
                    and self.settings.ENVIRONMENT != "testing"
                )

                if needs_browser:
                    logger.info(f"Triggering browser fallback for {canonical_url} (incomplete HTTP extraction)", extra={"url": canonical_url})
                    try:
                        fetch_res = await self._fetch_browser(canonical_url)
                        status_code, html_content = fetch_res[0], fetch_res[1]
                        source_engine = "browser"
                        self.browser_fallback_count += 1
                    except Exception as e:
                        logger.warning(f"Browser fallback failed for {canonical_url}: {e}")
                else:
                    self.http_success_count += 1

            self.total_processed += 1

            # Check 404 or client error status codes
            if status_code == 404:
                return ExtractionResult(
                    product=None,
                    success=False,
                    validation_status=ValidationStatus.REJECTED,
                    errors=[f"Product URL returned 404 Not Found: {canonical_url}"],
                    source_engine=source_engine,
                )

            # Check challenge detection
            detection = self.detector.detect(status_code, html_content, current_url=canonical_url)
            if detection.is_captcha or detection.is_blocked:
                await self.intervention_manager.trigger_intervention(
                    reason=detection.reason or "Challenge detected during product extraction",
                    crawl_id=crawl_id,
                    url=canonical_url,
                )
                return ExtractionResult(
                    product=None,
                    success=False,
                    validation_status=ValidationStatus.REJECTED,
                    errors=[f"Anti-bot Challenge detected: {detection.reason}"],
                    source_engine=source_engine,
                )

            # Parse extracted HTML
            try:
                result = self.parser.parse(
                    html_content=html_content or "<html><body></body></html>",
                    url=canonical_url,
                    product_id=product_id,
                    source_engine=source_engine,
                )
            except ParserError as e:
                return ExtractionResult(
                    product=None,
                    success=False,
                    validation_status=ValidationStatus.REJECTED,
                    errors=[f"Parser error: {e}"],
                    source_engine=source_engine,
                )

            # Update validation statistics
            if result.validation_status == ValidationStatus.VALID:
                self.validation_passed_count += 1
            elif result.validation_status in (ValidationStatus.WARNING, ValidationStatus.NEEDS_REVIEW):
                self.validation_warning_count += 1
            else:
                self.validation_rejected_count += 1

            # Immediate single persistence if storage provided
            if self.storage and result.success and result.product:
                try:
                    await self.storage.save_product(result.product)
                except Exception as e:
                    logger.error(f"Failed to persist single product to storage: {e}")

            return result

    async def extract_batch(
        self,
        targets: List[Union[str, ProductTarget]],
        use_browser: bool = False,
        concurrency: Optional[int] = None,
        crawl_id: Optional[str] = None,
    ) -> List[ExtractionResult]:
        """
        Extract a batch of product targets concurrently with bounded workers, deduplication,
        checkpoint state updates, and batch database/file persistence.
        """
        results: List[ExtractionResult] = []
        valid_products_to_persist = []
        seen_batch_ids: Set[str] = set()

        unique_targets = []
        for t in targets:
            pid = t.product_id if isinstance(t, ProductTarget) else extract_product_id(str(t))
            purl = t.url if isinstance(t, ProductTarget) else str(t)

            if self.deduplicator.is_duplicate(product_id=pid, url=purl):
                self.duplicates_prevented += 1
                continue

            if pid and pid in seen_batch_ids:
                self.duplicates_prevented += 1
                continue

            if pid:
                seen_batch_ids.add(pid)
            unique_targets.append(t)

        semaphore = asyncio.Semaphore(concurrency or self.config.max_concurrency)

        async def _worker(tgt):
            async with semaphore:
                return await self.extract_product(target=tgt, use_browser=use_browser, crawl_id=crawl_id)

        tasks = [_worker(t) for t in unique_targets]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in batch_results:
            if isinstance(res, Exception):
                logger.error(f"Batch worker exception during extraction: {res}")
                continue
            if isinstance(res, ExtractionResult):
                results.append(res)
                if res.success and res.product:
                    valid_products_to_persist.append(res.product)

                    if self.checkpoint_manager:
                        self.checkpoint_manager.record_product_extracted(res.product.product_id)

        # Batch Persistence to Storage
        if self.storage and valid_products_to_persist:
            try:
                for chunk_idx in range(0, len(valid_products_to_persist), self.config.batch_size):
                    chunk = valid_products_to_persist[chunk_idx : chunk_idx + self.config.batch_size]
                    await self.storage.save_products(chunk)
                logger.info(f"Persisted {len(valid_products_to_persist)} extracted products to storage.")
            except Exception as e:
                logger.error(f"Error persisting batch products to storage: {e}")

        # Checkpoint commit
        if self.checkpoint_manager:
            self.checkpoint_manager.save_checkpoint()

        return results

    async def close(self):
        """Cleanly release all HTTP and browser sessions."""
        if self._shared_context:
            try:
                await self._shared_context.close()
            except Exception:
                pass
            self._shared_context = None

        await self.http_client.aclose()
        await self.browser_client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Backward compatible alias
DarazProductExtractor = DarazProductExtractionEngine
