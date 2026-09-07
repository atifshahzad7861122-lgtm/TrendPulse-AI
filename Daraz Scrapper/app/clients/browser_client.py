"""Playwright browser automation abstraction with context management, anti-detection, and session preservation."""

import asyncio
from typing import Any, Dict, List, Optional
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Route,
    async_playwright,
)

from app.core.challenge_detector import ChallengeDetector
from app.core.config import Settings, get_settings
from app.core.exceptions import BrowserError, ChallengeDetectedError
from app.core.logging import logger
from app.core.proxy import ProxyProvider
from app.core.runtime import runtime_metrics


class AsyncBrowserClient:
    """Manages the lifecycle of Playwright browsers, contexts, pages, and interactive sessions."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        headless: Optional[bool] = None,
        proxy_provider: Optional[ProxyProvider] = None,
        abort_media: bool = False,
    ):
        self.settings = settings or get_settings()
        self.headless = headless if headless is not None else self.settings.BROWSER_HEADLESS
        self.proxy_provider = proxy_provider or ProxyProvider(enabled=self.settings.PROXY_ENABLED)
        self.abort_media = abort_media

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._contexts: List[BrowserContext] = []
        self._is_started = False
        self._lock = asyncio.Lock()

    async def start(self):
        """Initialize the Playwright engine and launch browser instance."""
        async with self._lock:
            if self._is_started:
                return

            try:
                self._playwright = await async_playwright().start()

                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                ]

                proxy_cfg = await self.proxy_provider.get_next_proxy() if self.proxy_provider else None
                playwright_proxy = self.proxy_provider.get_playwright_proxy(proxy_cfg) if proxy_cfg else None

                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=launch_args,
                    proxy=playwright_proxy,
                    timeout=self.settings.BROWSER_TIMEOUT * 1000,
                )
                self._is_started = True
                logger.info(
                    "Browser client initialized successfully",
                    extra={"event": "browser_started", "headless": self.headless},
                )
            except Exception as exc:
                await self._close_internal()
                raise BrowserError(f"Failed to launch browser: {exc}") from exc

    async def new_context(
        self,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        locale: str = "en-US",
        timezone_id: str = "Asia/Karachi",
        extra_http_headers: Optional[Dict[str, str]] = None,
        cookies: Optional[List[Dict[str, Any]]] = None,
        storage_state: Optional[Dict[str, Any]] = None,
    ) -> BrowserContext:
        """Create an isolated browser context with fingerprint evasion defaults."""
        if not self._is_started or not self._browser:
            await self.start()

        try:
            assert self._browser is not None
            context_kwargs: Dict[str, Any] = {
                "user_agent": user_agent or self.settings.SCRAPER_USER_AGENT,
                "viewport": viewport or {"width": 1920, "height": 1080},
                "locale": locale,
                "timezone_id": timezone_id,
                "extra_http_headers": extra_http_headers,
                "ignore_https_errors": True,
            }
            if storage_state:
                context_kwargs["storage_state"] = storage_state

            context = await self._browser.new_context(**context_kwargs)

            if cookies and not storage_state:
                await context.add_cookies(cookies)

            if self.abort_media:
                async def _route_handler(route: Route):
                    if route.request.resource_type in ["image", "media", "font"]:
                        await route.abort()
                    else:
                        await route.continue_()
                await context.route("**/*", _route_handler)

            self._contexts.append(context)
            return context
        except Exception as exc:
            raise BrowserError(f"Failed to create browser context: {exc}") from exc

    async def new_page(
        self,
        context: Optional[BrowserContext] = None,
    ) -> Page:
        """Create a new page within a context and apply anti-automation evasions."""
        ctx = context or (await self.new_context())
        try:
            page = await ctx.new_page()
            page.set_default_timeout(self.settings.BROWSER_TIMEOUT * 1000)

            # Evade basic navigator.webdriver detection
            await page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                """
            )
            return page
        except Exception as exc:
            raise BrowserError(f"Failed to create new browser page: {exc}") from exc

    async def scroll_page(
        self,
        page: Page,
        scroll_count: int = 5,
        delay_seconds: float = 0.5,
    ) -> None:
        """Gradually scroll down the page to trigger dynamic AJAX and lazy-loaded items."""
        for _ in range(scroll_count):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(delay_seconds)

    async def inspect_page_challenges(self, page: Page) -> None:
        """Check if active page contains CAPTCHA or challenge barriers."""
        content = await page.content()
        url = page.url
        res = ChallengeDetector.inspect_response(status_code=200, body=content, url=url)
        if res.is_challenge:
            await runtime_metrics.record_challenge(res.challenge_type or "unknown")
            raise ChallengeDetectedError(
                message=f"Browser encountered challenge: {res.reason}",
                url=url,
                challenge_type=res.challenge_type,
            )

    async def capture_screenshot(self, page: Page, path: str) -> None:
        """Save a screenshot of current page state for debugging or manual intervention."""
        try:
            await page.screenshot(path=path, full_page=True)
        except Exception as e:
            logger.warning(f"Failed to capture page screenshot to {path}: {e}")

    async def _close_internal(self):
        for ctx in self._contexts:
            try:
                await ctx.close()
            except Exception:
                pass
        self._contexts.clear()

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        self._is_started = False

    async def close(self):
        """Cleanly close contexts, browser, and stop the Playwright daemon."""
        async with self._lock:
            await self._close_internal()
            logger.info("Browser client closed", extra={"event": "browser_closed"})

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
