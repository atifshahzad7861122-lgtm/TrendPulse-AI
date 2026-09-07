"""Resumable pagination runner for category catalog and keyword search listings."""

from dataclasses import dataclass, field
from typing import Callable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.core.logging import logger
from app.discovery.client import DarazDiscoveryClient
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config
from app.discovery.models import ProductTarget
from app.discovery.parser import DarazHTMLParser, PaginationResult
from app.discovery.queue import ProductTargetQueue


@dataclass
class PaginationStats:
    """Statistics recorded during a paginated crawl run."""

    pages_processed: int = 0
    pages_failed: int = 0
    total_targets_found: int = 0
    stopped_reason: str = "completed"
    collected_targets: List[ProductTarget] = field(default_factory=list)


class PaginationStrategy:
    """Handles page URL construction, pagination parsing, and empty/duplicate page termination."""

    def __init__(self, config: Optional[DarazDiscoveryConfig] = None):
        self.config = config or default_discovery_config

    def build_page_url(self, base_url: str, page_number: int) -> str:
        """Construct a paginated URL with updated page query parameter."""
        parsed = urlparse(base_url)
        query_dict = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_dict[self.config.PAGE_PARAM] = str(page_number)
        new_query = urlencode(query_dict)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))


class PaginationRunner:
    """Executes a sequential or bounded paginated harvest across multiple listing pages."""

    def __init__(
        self,
        client: DarazDiscoveryClient,
        parser: DarazHTMLParser,
        queue: ProductTargetQueue,
        config: Optional[DarazDiscoveryConfig] = None,
        strategy: Optional[PaginationStrategy] = None,
    ):
        self.client = client
        self.parser = parser
        self.queue = queue
        self.config = config or default_discovery_config
        self.strategy = strategy or PaginationStrategy(config=self.config)

    async def paginate(
        self,
        start_url: str,
        start_page: int = 1,
        max_pages: int = 10,
        source_category: Optional[str] = None,
        source_query: Optional[str] = None,
        crawl_id: Optional[str] = None,
        on_page_completed: Optional[Callable[[int, List[ProductTarget]], None]] = None,
    ) -> PaginationStats:
        """Iterate through pages, extracting and enqueueing unique product targets."""
        stats = PaginationStats()
        current_page = start_page
        consecutive_empty_pages = 0

        while current_page <= (start_page + max_pages - 1):
            page_url = self.strategy.build_page_url(start_url, current_page)
            logger.debug(
                f"Fetching page {current_page}: {page_url}",
                extra={"crawl_id": crawl_id, "page": current_page, "url": page_url},
            )

            status_code, html, final_url, detection = await self.client.fetch_page(
                page_url, crawl_id=crawl_id
            )

            if detection.is_captcha or detection.is_blocked:
                stats.stopped_reason = f"challenge_detected: {detection.reason}"
                logger.warning(
                    f"Pagination halted on page {current_page} due to anti-bot challenge: {detection.reason}",
                    extra={"crawl_id": crawl_id, "page": current_page, "reason": detection.reason},
                )
                break

            if status_code != 200:
                stats.pages_failed += 1
                logger.warning(
                    f"Page {current_page} returned HTTP {status_code}",
                    extra={"crawl_id": crawl_id, "page": current_page, "status": status_code},
                )
                if status_code in (404, 410):
                    stats.stopped_reason = f"http_{status_code}"
                    break
                current_page += 1
                continue

            # Parse product targets on this page
            targets = self.parser.parse_product_targets(
                html_content=html,
                base_url=self.config.BASE_URL,
                source_category=source_category,
                source_query=source_query,
            )

            stats.pages_processed += 1
            stats.total_targets_found += len(targets)
            stats.collected_targets.extend(targets)

            # Check pagination indicators
            pagination = self.parser.parse_pagination(
                html_content=html,
                current_page=current_page,
                base_url=self.config.BASE_URL,
            )

            # Enqueue discovered targets
            if targets:
                await self.queue.enqueue_batch(targets)
                consecutive_empty_pages = 0
            else:
                consecutive_empty_pages += 1

            if on_page_completed:
                try:
                    on_page_completed(current_page, targets)
                except Exception as e:
                    logger.error(f"Error in on_page_completed callback: {e}")

            # Check termination conditions
            if pagination.is_empty_page or (not targets and consecutive_empty_pages >= 2):
                stats.stopped_reason = "empty_page"
                logger.info(f"Empty page detected at page {current_page}. Terminating pagination.")
                break

            if not pagination.has_next_page and (pagination.total_pages and current_page >= pagination.total_pages):
                stats.stopped_reason = "last_page_reached"
                logger.info(f"Reached final page {current_page}/{pagination.total_pages}.")
                break

            current_page += 1

        return stats
