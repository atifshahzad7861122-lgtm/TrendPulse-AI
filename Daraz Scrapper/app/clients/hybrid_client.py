"""Unified Hybrid Scraping Client supporting HTTP, Browser, and Hybrid fallback strategies."""

import asyncio
from typing import Any, Callable, Dict, Optional, Tuple, Union
import httpx
from playwright.async_api import Page

from app.clients.browser_client import AsyncBrowserClient
from app.clients.http_client import AsyncHttpClient
from app.core.challenge_detector import ChallengeDetector
from app.core.config import Settings, get_settings
from app.core.constants import ScrapingMode
from app.core.exceptions import ChallengeDetectedError, NetworkError, ScraperError
from app.core.logging import logger
from app.core.session import SessionManager, SessionState


class HybridClient:
    """Unified client orchestrating HTTP requests with seamless Browser automation fallback."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[AsyncHttpClient] = None,
        browser_client: Optional[AsyncBrowserClient] = None,
        session_manager: Optional[SessionManager] = None,
        default_mode: ScrapingMode = ScrapingMode.HYBRID,
    ):
        self.settings = settings or get_settings()
        self.http_client = http_client or AsyncHttpClient(settings=self.settings)
        self.browser_client = browser_client or AsyncBrowserClient(settings=self.settings)
        self.session_manager = session_manager or SessionManager()
        self.default_mode = default_mode
        self._is_closed = False

    async def fetch(
        self,
        url: str,
        mode: Optional[ScrapingMode] = None,
        session_id: Optional[str] = None,
        is_content_valid: Optional[Callable[[str], bool]] = None,
        wait_selector: Optional[str] = None,
        scroll_count: int = 0,
    ) -> Tuple[str, str]:
        """
        Fetch URL content using selected ScrapingMode.
        Returns Tuple of (content: str, used_mode: str).
        """
        effective_mode = mode or self.default_mode
        session: Optional[SessionState] = None
        if session_id:
            session = await self.session_manager.get_or_create_session(session_id)

        # 1. Direct HTTP Mode
        if effective_mode == ScrapingMode.HTTP:
            resp = await self.http_client.get(url)
            return resp.text, "http"

        # 2. Direct Browser Mode
        if effective_mode == ScrapingMode.BROWSER:
            return await self._fetch_browser(
                url=url,
                session=session,
                wait_selector=wait_selector,
                scroll_count=scroll_count,
            )

        # 3. Hybrid Mode: HTTP-first, fallback to browser
        try:
            resp = await self.http_client.get(url, inspect_challenges=True)
            html = resp.text

            # If validator passed and content is deemed complete, return HTTP result
            if is_content_valid is None or is_content_valid(html):
                return html, "http"

            logger.info(
                f"HTTP content validation check indicated incomplete dynamic data for {url}. Falling back to Browser.",
                extra={"event": "hybrid_fallback_to_browser", "url": url},
            )
        except ChallengeDetectedError as e:
            logger.warning(
                f"HTTP request encountered challenge on {url}. Escalating to Browser for verification.",
                extra={"event": "challenge_escalate_to_browser", "url": url, "challenge_type": e.challenge_type},
            )
        except (NetworkError, Exception) as e:
            logger.warning(
                f"HTTP request failed on {url} ({e}). Attempting Browser fallback.",
                extra={"event": "http_failed_fallback_to_browser", "url": url, "error": str(e)},
            )

        # Fallback to browser execution
        return await self._fetch_browser(
            url=url,
            session=session,
            wait_selector=wait_selector,
            scroll_count=scroll_count,
        )

    async def _fetch_browser(
        self,
        url: str,
        session: Optional[SessionState] = None,
        wait_selector: Optional[str] = None,
        scroll_count: int = 0,
    ) -> Tuple[str, str]:
        """Internal browser page fetcher with session management and scrolling."""
        storage_state = session.storage_state if session else None
        context = await self.browser_client.new_context(
            user_agent=self.settings.SCRAPER_USER_AGENT,
            storage_state=storage_state,
        )
        page = await self.browser_client.new_page(context=context)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.settings.BROWSER_TIMEOUT * 1000)

            # Check for bot challenge immediately
            await self.browser_client.inspect_page_challenges(page)

            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    pass

            if scroll_count > 0:
                await self.browser_client.scroll_page(page, scroll_count=scroll_count)

            # Update session state cookies
            if session:
                cookies = await context.cookies()
                await self.session_manager.update_cookies(session.session_id, cookies)

            content = await page.content()
            return content, "browser"

        finally:
            await page.close()

    async def close(self):
        """Shut down underlying HTTP and Browser clients."""
        if not self._is_closed:
            await self.http_client.aclose()
            await self.browser_client.close()
            self._is_closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
