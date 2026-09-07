"""Anti-Bot and Challenge Detection for Daraz."""
import asyncio
import logging
from typing import Any, Tuple

logger = logging.getLogger("trendpulse.scraper.daraz.challenge")

CHALLENGE_SELECTORS = [
    "#nc_1_n1z",
    "#nocaptcha",
    ".nc-container",
    "iframe[src*='captcha']",
    "iframe[src*='baxia']",
    "#baxia-dialog-content",
    ".punish-dialog",
    "#punish_dialog",
    ".baxia-dialog"
]


async def detect_challenge(page: Any) -> Tuple[bool, str]:
    """
    Checks if a Daraz / Alibaba security challenge or CAPTCHA dialog is visible.
    Returns (is_challenged, reason).
    """
    try:
        for selector in CHALLENGE_SELECTORS:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                reason = f"Security verification slider detected: {selector}"
                logger.warning(f"🚨 [DARAZ ANTI-BOT CHALLENGE DETECTED]: {reason}")
                return True, reason
    except Exception as e:
        logger.debug(f"Error checking challenge selectors: {e}")

    return False, ""


async def handle_challenge_if_present(page: Any, interactive: bool = False) -> bool:
    """
    Checks for challenge. If interactive=True, gives time for manual solve.
    Returns True if challenged.
    """
    is_challenged, reason = await detect_challenge(page)
    if is_challenged:
        if interactive:
            logger.warning("👉 Interactive mode: Waiting 10s for manual challenge completion...")
            await asyncio.sleep(10)
            still_challenged, _ = await detect_challenge(page)
            return still_challenged
        return True
    return False
