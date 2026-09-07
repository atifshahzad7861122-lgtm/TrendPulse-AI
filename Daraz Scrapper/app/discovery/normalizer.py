"""URL normalization and unique identifier extraction utilities for Daraz marketplace entities.

Adapted and adapted from reference implementations:
- regmiprabesh/daraz-scraper (daraz_spider.py remove_query_params)
- BrenoFariasdaSilva/E-Commerces-WebScraper (urls_utils.py, product_utils.py)
"""

import re
from typing import Optional, Set
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from app.discovery.config import default_discovery_config

# Regex patterns for Daraz product ID extraction across different URL formats
DARAZ_ID_URL_REGEX = re.compile(r"-i(\d+)(?:-s\d+)?(?:\.html|\?|$)", re.IGNORECASE)
DARAZ_ITEM_QUERY_REGEX = re.compile(r"[?&](?:itemId|pId|item_id|productId)=(\d+)", re.IGNORECASE)
DARAZ_NUMERIC_ID_REGEX = re.compile(r"/products/.*?(\d{6,})", re.IGNORECASE)
DARAZ_PLAIN_DIGITS_REGEX = re.compile(r"^(\d{6,})$")


def normalize_url(
    url: str,
    base_url: str = default_discovery_config.BASE_URL,
    strip_params: Optional[Set[str]] = None,
) -> str:
    """Normalize a raw or relative URL by canonicalizing domain, scheme, and stripping tracking parameters."""
    if not url or not str(url).strip():
        return ""

    url = str(url).strip()

    # Handle protocol-relative URLs (//www.daraz.pk/...)
    if url.startswith("//"):
        url = f"https:{url}"
    elif not url.startswith("http://") and not url.startswith("https://"):
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    # Force HTTPS scheme and lowercase host
    scheme = "https"
    netloc = parsed.netloc.lower()

    # Strip noisy tracking query parameters
    params_to_strip = strip_params if strip_params is not None else default_discovery_config.STRIP_QUERY_PARAMS
    query_tuples = parse_qsl(parsed.query, keep_blank_values=False)
    filtered_query = [(k, v) for k, v in query_tuples if k not in params_to_strip]

    # Reconstruct query string alphabetically sorted for consistency
    filtered_query.sort(key=lambda x: x[0])
    new_query = urlencode(filtered_query)

    # Clean path (strip duplicate slashes)
    clean_path = re.sub(r"/+", "/", parsed.path)

    # Reconstruct URL without fragment
    normalized = urlunparse((scheme, netloc, clean_path, parsed.params, new_query, ""))
    return normalized


def canonicalize_product_url(url: str, base_url: str = default_discovery_config.BASE_URL) -> str:
    """Produce a canonical clean product URL with all tracking parameters and fragments stripped."""
    if not url:
        return ""
    normalized = normalize_url(url, base_url=base_url)
    parsed = urlparse(normalized)
    # Strip any remaining query string for canonical PDP URLs
    canonical = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return canonical


def extract_product_id(url_or_text: str) -> Optional[str]:
    """Extract a stable numeric Daraz product ID from a product URL or metadata string."""
    if not url_or_text:
        return None

    url_str = str(url_or_text).strip()

    # 1. Plain numeric ID
    if DARAZ_PLAIN_DIGITS_REGEX.match(url_str):
        return url_str

    # 2. Try primary URL regex: -i<digits> (e.g. apple-iphone-15-pro-max-i438927492-s2049281.html)
    match = DARAZ_ID_URL_REGEX.search(url_str)
    if match:
        return match.group(1)

    # 3. Try query parameters: itemId=<digits>
    match = DARAZ_ITEM_QUERY_REGEX.search(url_str)
    if match:
        return match.group(1)

    # 4. Fallback to numeric segment in /products/ path
    match = DARAZ_NUMERIC_ID_REGEX.search(url_str)
    if match:
        return match.group(1)

    return None


def extract_category_id_from_url(url: str) -> str:
    """Extract a canonical category ID or slug from a category URL."""
    if not url:
        return ""
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    path_segments = [s for s in parsed.path.strip("/").split("/") if s]
    if path_segments:
        # e.g. /smartphones/ -> 'smartphones' or /category/audio -> 'audio'
        return path_segments[-1]
    return "root"


def normalize_search_keyword(keyword: str) -> str:
    """Clean and standardize a search query keyword."""
    if not keyword:
        return ""
    cleaned = re.sub(r"\s+", " ", keyword.strip().lower())
    return cleaned
