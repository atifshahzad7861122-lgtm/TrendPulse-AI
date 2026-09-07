"""Configuration for the Daraz Specialized Scraper."""
import os

DEFAULT_DOMAIN = "daraz.pk"
DEFAULT_HEADLESS = True
DEFAULT_SLOW_MO = 100
DEFAULT_TIMEOUT_MS = 45000
DEFAULT_MAX_REVIEW_PAGES = 3

BROWSER_ARGS = [
    "--start-maximized",
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-sandbox",
    "--disable-dev-shm-usage"
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

VIEWPORT = {"width": 1280, "height": 800}
