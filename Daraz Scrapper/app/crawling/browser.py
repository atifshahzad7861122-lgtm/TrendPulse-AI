"""Browser lifecycle manager for headless Playwright execution and state recycling."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.crawling.config import UniversalCrawlerConfig
from app.crawling.models import CrawlRequest, CrawlResponse
from app.core.logging import logger


class BrowserLifecycleManager:
    """
    Manages Playwright browser instances, context recycling, smooth lazy scrolling,
    and resource filtering.
    """

    SCROLL_SCRIPT = """
    async () => {
        await new Promise((resolve) => {
            let totalHeight = 0;
            const distance = 400;
            const timer = setInterval(() => {
                const scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;
                if (totalHeight >= scrollHeight || totalHeight >= 4000) {
                    clearInterval(timer);
                    resolve();
                }
            }, 100);
        });
    }
    """

    def __init__(self, config: Optional[UniversalCrawlerConfig] = None):
        self.config = config or UniversalCrawlerConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _get_browser(self) -> Browser:
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self._playwright.chromium.launch(
                    headless=self.config.headless_browser,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
            return self._browser

    async def fetch(self, request: CrawlRequest, storage_state: Optional[Dict[str, Any]] = None) -> CrawlResponse:
        """Render page in a lightweight browser context."""
        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent=self.config.default_user_agent,
            viewport={"width": 1280, "height": 800},
            storage_state=storage_state,
        )

        page = await context.new_page()
        start_time = time.perf_counter()
        try:
            # Navigate using domcontentloaded
            response = await page.goto(
                request.url,
                wait_until="domcontentloaded",
                timeout=int(self.config.browser_timeout_seconds * 1000),
            )
            status_code = response.status if response else 200

            # Wait for specific selector if specified
            if request.wait_selector:
                try:
                    await page.wait_for_selector(request.wait_selector, timeout=5000)
                except Exception:
                    pass

            # Execute custom JS or scroll script if enabled
            if request.js_code:
                try:
                    await page.evaluate(request.js_code)
                except Exception as e:
                    logger.warning(f"Error executing custom js: {e}")

            if self.config.scroll_page_on_browser:
                try:
                    await page.evaluate(self.SCROLL_SCRIPT)
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

            html = await page.content()
            final_url = page.url
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return CrawlResponse(
                url=final_url,
                status_code=status_code,
                html=html,
                headers=dict(response.headers) if response else {},
                source_engine="browser",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(f"Browser rendering failed for {request.url}: {e}")
            return CrawlResponse(
                url=request.url,
                status_code=0,
                html="",
                headers={},
                source_engine="browser",
                duration_ms=duration_ms,
                metadata={"error": str(e)},
            )
        finally:
            await page.close()
            await context.close()

    async def close(self) -> None:
        """Close browser and terminate Playwright."""
        async with self._lock:
            if self._browser and self._browser.is_connected():
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
