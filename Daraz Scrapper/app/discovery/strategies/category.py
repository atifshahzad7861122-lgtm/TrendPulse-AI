"""Category hierarchy and catalog page discovery strategy for Daraz marketplace."""

from typing import List, Optional
from app.core.logging import logger
from app.discovery.client import DarazDiscoveryClient
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config
from app.discovery.models import CategoryTarget, DiscoveryRun, ProductTarget
from app.discovery.parser import DarazHTMLParser
from app.discovery.queue import ProductTargetQueue
from app.discovery.strategies.pagination import PaginationRunner, PaginationStats
from app.storage.base import BaseStorage


class CategoryDiscoveryStrategy:
    """Strategy for traversing multi-level marketplace category hierarchies and extracting product targets."""

    def __init__(
        self,
        client: DarazDiscoveryClient,
        parser: DarazHTMLParser,
        queue: ProductTargetQueue,
        storage: Optional[BaseStorage] = None,
        config: Optional[DarazDiscoveryConfig] = None,
    ):
        self.client = client
        self.parser = parser
        self.queue = queue
        self.storage = storage
        self.config = config or default_discovery_config
        self.pagination_runner = PaginationRunner(
            client=self.client,
            parser=self.parser,
            queue=self.queue,
            config=self.config,
        )

    async def discover_category_tree(
        self,
        start_url: Optional[str] = None,
        crawl_id: Optional[str] = None,
    ) -> List[CategoryTarget]:
        """Fetch marketplace navigation root and parse complete category and subcategory trees."""
        target_url = start_url or self.config.BASE_URL
        logger.info(f"Starting category tree discovery on {target_url}", extra={"crawl_id": crawl_id, "url": target_url})

        status_code, html, final_url, detection = await self.client.fetch_page(target_url, crawl_id=crawl_id)

        if detection.is_captcha or detection.is_blocked:
            logger.warning(
                f"Category tree discovery halted due to challenge: {detection.reason}",
                extra={"crawl_id": crawl_id, "reason": detection.reason},
            )
            return []

        categories = self.parser.parse_categories(html, base_url=self.config.BASE_URL)

        # Persist discovered categories to storage if available
        if self.storage and categories:
            for cat in categories:
                if hasattr(self.storage, "save_category_target"):
                    await self.storage.save_category_target(cat)

        top_level = [c for c in categories if c.level == 1]
        subs = [c for c in categories if c.level > 1]
        logger.info(
            f"Category discovery completed: {len(top_level)} top-level categories, {len(subs)} subcategories",
            extra={
                "crawl_id": crawl_id,
                "top_level": len(top_level),
                "subcategories": len(subs),
                "total": len(categories),
            },
        )
        return categories

    async def crawl_category_products(
        self,
        category: CategoryTarget,
        start_page: int = 1,
        max_pages: Optional[int] = None,
        crawl_id: Optional[str] = None,
    ) -> PaginationStats:
        """Paginate through a category's product listings and enqueue discovered targets."""
        limit_pages = max_pages or self.config.MAX_PAGES_PER_CATEGORY
        logger.info(
            f"Starting product discovery for category '{category.name}' ({category.url}) up to {limit_pages} pages",
            extra={"crawl_id": crawl_id, "category_id": category.category_id, "max_pages": limit_pages},
        )

        stats = await self.pagination_runner.paginate(
            start_url=category.url,
            start_page=start_page,
            max_pages=limit_pages,
            source_category=category.name,
            crawl_id=crawl_id,
        )

        return stats
