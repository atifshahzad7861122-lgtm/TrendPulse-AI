"""Discovery client bridging HTTP and Playwright engines with integrated challenge detection."""

from typing import Dict, Optional, Tuple
import httpx
from playwright.async_api import BrowserContext, Page

from app.clients.browser_client import AsyncBrowserClient
from app.clients.http_client import AsyncHttpClient
from app.core.config import Settings, get_settings
from app.core.exceptions import BrowserError, ChallengeDetectedError, NetworkError
from app.core.logging import logger
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config
from app.discovery.detector import ChallengeDetectionResult, ChallengeDetector, challenge_detector
from app.discovery.manual_intervention import ManualInterventionManager, manual_intervention_manager


class DarazDiscoveryClient:
    """Specialized discovery client for Daraz marketplace navigation."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        discovery_config: Optional[DarazDiscoveryConfig] = None,
        http_client: Optional[AsyncHttpClient] = None,
        browser_client: Optional[AsyncBrowserClient] = None,
        detector: Optional[ChallengeDetector] = None,
        intervention_manager: Optional[ManualInterventionManager] = None,
    ):
        self.settings = settings or get_settings()
        self.discovery_config = discovery_config or default_discovery_config
        self.http_client = http_client or AsyncHttpClient(settings=self.settings)
        self.browser_client = browser_client or AsyncBrowserClient(settings=self.settings)
        self.detector = detector or challenge_detector
        self.intervention_manager = intervention_manager or manual_intervention_manager

        self._shared_context: Optional[BrowserContext] = None

    async def fetch_page(
        self,
        url: str,
        use_browser: bool = False,
        headers: Optional[Dict[str, str]] = None,
        crawl_id: Optional[str] = None,
    ) -> Tuple[int, str, str, ChallengeDetectionResult]:
        """
        Fetch HTML content for a catalog or search page via HTTP or Headless Browser.
        Automatically falls back to browser if an HTTP response is empty or CSR-only.
        Returns (status_code, html_content, final_url, challenge_result).
        """
        # If crawl is currently in manual intervention state, wait before requesting
        if self.intervention_manager.is_paused:
            logger.info("Discovery client waiting for manual intervention resolution...")
            resumed = await self.intervention_manager.wait_until_resumed(timeout=5.0)
            if not resumed:
                logger.warning("Manual intervention wait timed out (5.0s). Proceeding with challenge result.")
                return 403, "", url, ChallengeDetectionResult(is_blocked=True, reason="Manual intervention timed out")

        if use_browser:
            return await self._fetch_browser(url, crawl_id=crawl_id)

        # Try fast async HTTP first
        status_code, html_content, final_url, detection = await self._fetch_http(url, headers=headers, crawl_id=crawl_id)

        # If HTTP response is CSR-only and missing DOM product cards, trigger browser fallback if not in test env
        is_csr_empty = (
            status_code == 200
            and '"renderMode":"CSR"' in html_content
            and not any(k in html_content for k in ["data-qa-locator", "gridItem", "box--ujueT", "c2prKC"])
        )

        if is_csr_empty and self.settings.ENVIRONMENT != "testing":
            logger.info(f"HTTP response for {url} is CSR-rendered. Falling back to browser engine.", extra={"url": url})
            return await self._fetch_browser(url, crawl_id=crawl_id)

        return status_code, html_content, final_url, detection

    async def _fetch_http(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        crawl_id: Optional[str] = None,
    ) -> Tuple[int, str, str, ChallengeDetectionResult]:
        """Execute request using async HTTP client."""
        try:
            response = await self.http_client.get(url, headers=headers)
            status_code = response.status_code
            html_content = response.text
            final_url = str(response.url)
        except ChallengeDetectedError as e:
            status_code = e.status_code or 403
            html_content = ""
            final_url = url
        except NetworkError as e:
            status_code = e.status_code or 500
            html_content = ""
            final_url = url
        except Exception as e:
            status_code = 500
            html_content = ""
            final_url = url

        detection = self.detector.detect(status_code, html_content, current_url=final_url)

        if detection.is_captcha or detection.is_blocked:
            await self.intervention_manager.trigger_intervention(
                reason=detection.reason or "Anti-bot challenge detected via HTTP",
                crawl_id=crawl_id,
                url=final_url,
            )

        return status_code, html_content, final_url, detection

    async def _fetch_browser(
        self,
        url: str,
        crawl_id: Optional[str] = None,
    ) -> Tuple[int, str, str, ChallengeDetectionResult]:
        """Execute request using Playwright browser client."""
        try:
            if not self._shared_context:
                self._shared_context = await self.browser_client.new_context()

            page: Page = await self.browser_client.new_page(context=self._shared_context)

            try:
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                status_code = response.status if response else 200
                html_content = await page.content()
                final_url = page.url
            except Exception as e:
                await page.close()
                raise BrowserError(f"Browser navigation failed for {url}: {e}") from e

            detection = self.detector.detect(status_code, html_content, current_url=final_url)

            if detection.is_captcha or detection.is_blocked:
                # Keep page & context alive for manual intervention
                await self.intervention_manager.trigger_intervention(
                    reason=detection.reason or "CAPTCHA/challenge detected in browser",
                    crawl_id=crawl_id,
                    context=self._shared_context,
                    page=page,
                    url=final_url,
                )
            else:
                await page.close()

            return status_code, html_content, final_url, detection

        except Exception as e:
            raise BrowserError(f"Browser execution failed: {e}") from e

    async def close(self):
        """Cleanly terminate HTTP and browser sessions."""
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
