"""Core system constants, enumerations, and version specifications."""

from enum import Enum
import re
from typing import Dict, List, Set

# System & Data Versioning
SCHEMA_VERSION = "1.0.0"
PARSER_VERSION = "1.0.0"
SCRAPER_VERSION = "1.0.0"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class CrawlStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    MANUAL_INTERVENTION = "manual_intervention"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlType(str, Enum):
    FULL = "full"
    CATEGORY = "category"
    PRODUCT = "product"
    SEARCH = "search"
    PRICE_UPDATE = "price_update"


class ScrapingMode(str, Enum):
    HTTP = "http"
    BROWSER = "browser"
    HYBRID = "hybrid"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ur;q=0.8",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Supported Daraz marketplace regional domains
DARAZ_DOMAINS: Dict[str, Dict[str, str]] = {
    "pk": {"country": "Pakistan", "currency": "PKR", "base_url": "https://www.daraz.pk"},
    "np": {"country": "Nepal", "currency": "NPR", "base_url": "https://www.daraz.com.np"},
    "bd": {"country": "Bangladesh", "currency": "BDT", "base_url": "https://www.daraz.com.bd"},
    "lk": {"country": "Sri Lanka", "currency": "LKR", "base_url": "https://www.daraz.lk"},
    "mm": {"country": "Myanmar", "currency": "MMK", "base_url": "https://www.shop.com.mm"},
}

DARAZ_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?daraz\.(pk|com\.np|com\.bd|lk)|^https?://(?:www\.)?shop\.com\.mm",
    re.IGNORECASE,
)

# Anti-Bot Signatures and Challenge Keywords
CHALLENGE_KEYWORDS: List[str] = [
    "verify you are human",
    "security verification",
    "please slide to verify",
    "captcha",
    "challenge-running",
    "cf-browser-verification",
    "akamai-bm",
    "punish page",
    "access denied",
    "attention required! | cloudflare",
    "waf verification",
    "robot check",
    "datadome",
    "shield.daraz",
]

CHALLENGE_STATUS_CODES: Set[int] = {403, 429}
