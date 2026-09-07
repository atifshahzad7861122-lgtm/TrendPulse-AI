"""Manual intervention manager for CAPTCHA challenges and human verification."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from playwright.async_api import BrowserContext, Page

from app.core.constants import CrawlStatus
from app.core.logging import logger


class ManualInterventionManager:
    """Coordinates manual verification workflows, preserving browser contexts and handling resume signals."""

    def __init__(self):
        self._is_paused = False
        self._resume_event = asyncio.Event()
        self._resume_event.set()  # Default: not paused
        self._active_challenge_info: Optional[Dict[str, Any]] = None
        self._preserved_context: Optional[BrowserContext] = None
        self._preserved_page: Optional[Page] = None
        self._lock = asyncio.Lock()

    @property
    def is_paused(self) -> bool:
        """Return True if an unresolved manual intervention challenge is active."""
        return self._is_paused

    @property
    def challenge_info(self) -> Optional[Dict[str, Any]]:
        """Return metadata about the current active security challenge."""
        return self._active_challenge_info

    async def trigger_intervention(
        self,
        reason: str,
        crawl_id: Optional[str] = None,
        context: Optional[BrowserContext] = None,
        page: Optional[Page] = None,
        url: Optional[str] = None,
    ) -> None:
        """
        Pause discovery execution, preserve the browser session, and enter MANUAL_INTERVENTION state.
        DO NOT attempt automated bypass or solving.
        """
        async with self._lock:
            self._is_paused = True
            self._resume_event.clear()
            self._preserved_context = context
            self._preserved_page = page

            self._active_challenge_info = {
                "crawl_id": crawl_id,
                "reason": reason,
                "url": url,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
                "status": CrawlStatus.MANUAL_INTERVENTION,
            }

            logger.warning(
                f"MANUAL INTERVENTION REQUIRED: {reason} on {url}. Crawl {crawl_id} paused.",
                extra={
                    "event": "manual_intervention_triggered",
                    "crawl_id": crawl_id,
                    "url": url,
                    "reason": reason,
                    "status": CrawlStatus.MANUAL_INTERVENTION,
                },
            )

    async def resolve_intervention(self, note: str = "Resolved manually") -> None:
        """Signal that human verification has been completed in the browser, unpausing the crawl."""
        async with self._lock:
            self._is_paused = False
            self._active_challenge_info = None
            self._preserved_context = None
            self._preserved_page = None
            self._resume_event.set()

            logger.info(
                f"Manual intervention resolved: {note}. Resuming crawl execution.",
                extra={"event": "manual_intervention_resolved", "note": note},
            )

    async def wait_until_resumed(self, timeout: Optional[float] = None) -> bool:
        """Wait until manual intervention has been resolved or timeout occurs."""
        try:
            await asyncio.wait_for(self._resume_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


# Shared global manual intervention coordinator
manual_intervention_manager = ManualInterventionManager()
