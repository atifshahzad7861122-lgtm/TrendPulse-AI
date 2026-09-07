"""Centralized deduplication, fingerprinting, and URL canonicalization utilities."""

import hashlib
import re
from typing import Optional, Set
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def canonicalize_url(url: str, keep_params: Optional[Set[str]] = None) -> str:
    """Normalize and canonicalize ecommerce URLs to strip ephemeral tracking tokens."""
    if not url:
        return ""

    parsed = urlparse(url.strip())
    # Force lowercase host and scheme
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    # Query param normalization
    query_tuples = parse_qsl(parsed.query, keep_blank_values=False)
    if keep_params:
        filtered_query = [(k, v) for k, v in query_tuples if k in keep_params]
    else:
        # Strip tracking query params by default (spm, scm, pdp_npi, click, etc.)
        tracking_keys = {"spm", "scm", "pdp_npi", "click", "from", "tracker", "ref", "tag", "source"}
        filtered_query = [(k, v) for k, v in query_tuples if k.lower() not in tracking_keys]

    sorted_query = sorted(filtered_query, key=lambda x: x[0])
    new_query = urlencode(sorted_query)

    # Clean path (strip trailing slash if length > 1)
    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse((scheme, netloc, path, "", new_query, ""))


def normalize_product_title(title: str, max_length: int = 120) -> str:
    """Clean and sanitize product titles with deterministic length bounds."""
    if not title:
        return ""
    # Normalize unicode spaces and collapsed whitespace
    clean = title.replace("\u00a0", " ").strip()
    clean = re.sub(r"\s+", " ", clean)
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip()
    return clean


class ProductDeduplicator:
    """In-memory thread-safe tracker for product uniqueness by ID and canonical URL."""

    def __init__(self):
        self._seen_ids: Set[str] = set()
        self._seen_urls: Set[str] = set()
        self.duplicates_prevented: int = 0

    def is_duplicate(self, product_id: Optional[str], url: Optional[str]) -> bool:
        """Check if a product has already been processed and record duplicate metrics."""
        is_dup = False
        canon_url = canonicalize_url(url) if url else ""

        if product_id and product_id in self._seen_ids:
            is_dup = True
        elif canon_url and canon_url in self._seen_urls:
            is_dup = True

        if is_dup:
            self.duplicates_prevented += 1
            return True

        # Register as seen
        if product_id:
            self._seen_ids.add(product_id)
        if canon_url:
            self._seen_urls.add(canon_url)

        return False

    def clear(self) -> None:
        """Reset deduplication state."""
        self._seen_ids.clear()
        self._seen_urls.clear()
        self.duplicates_prevented = 0


class ReviewDeduplicator:
    """In-memory tracker for review uniqueness using IDs and deterministic SHA256 fingerprints."""

    def __init__(self):
        self._seen_fingerprints: Set[str] = set()
        self.duplicates_prevented: int = 0

    @staticmethod
    def generate_fingerprint(
        product_id: str,
        reviewer: Optional[str] = None,
        rating: Optional[float] = None,
        date_str: Optional[str] = None,
        text: Optional[str] = None,
        review_id: Optional[str] = None,
    ) -> str:
        """Generate a deterministic fingerprint hash for a review."""
        if review_id:
            return hashlib.sha256(f"id:{product_id}:{review_id}".encode("utf-8")).hexdigest()

        # Deterministic combination of core stable attributes
        norm_reviewer = (reviewer or "").strip().lower()
        norm_rating = str(rating or 0.0)
        norm_date = (date_str or "").strip()
        norm_text = (text or "").strip().lower()[:100]  # First 100 chars of review text

        raw_str = f"fp:{product_id}:{norm_reviewer}:{norm_rating}:{norm_date}:{norm_text}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def is_duplicate(
        self,
        product_id: str,
        review_id: Optional[str] = None,
        reviewer: Optional[str] = None,
        rating: Optional[float] = None,
        date_str: Optional[str] = None,
        text: Optional[str] = None,
    ) -> bool:
        """Check whether review has been seen and record duplicate metric."""
        fp = self.generate_fingerprint(
            product_id=product_id,
            reviewer=reviewer,
            rating=rating,
            date_str=date_str,
            text=text,
            review_id=review_id,
        )
        if fp in self._seen_fingerprints:
            self.duplicates_prevented += 1
            return True

        self._seen_fingerprints.add(fp)
        return False

    def clear(self) -> None:
        self._seen_fingerprints.clear()
        self.duplicates_prevented = 0
