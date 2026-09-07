"""Image extraction, lazy-loading resolution, and deduplication."""

from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Tag

from app.intelligence.models.product import ImageRecord


class ImageExtractor:
    """
    Extracts, deduplicates, and normalizes gallery and variant product images.
    Resolves lazy-loaded attributes (data-src, data-origin-src, srcset).
    Preserves display order.
    """

    _LAZY_ATTRIBUTES = [
        "data-src",
        "data-origin-src",
        "data-lazy-src",
        "data-zoom-image",
        "data-old-hires",
        "data-hires",
        "data-original",
        "src",
    ]

    @classmethod
    def clean_image_url(cls, url: Optional[str]) -> Optional[str]:
        """Normalize URL scheme and remove thumbnail crop transformations where appropriate."""
        if not url or not isinstance(url, str):
            return None

        clean = url.strip()
        if not clean:
            return None

        if clean.startswith("//"):
            clean = f"https:{clean}"
        elif not clean.startswith(("http://", "https://")):
            return None

        # Filter out tiny icon data URLs, SVGs, or tracking beacons
        if clean.startswith("data:image") or ".svg" in clean.lower():
            return None

        return clean

    @classmethod
    def extract_from_img_tag(cls, tag: Tag) -> Optional[str]:
        """Extract best available resolution image URL from <img> tag."""
        # 1. Check lazy attributes first for high-res images
        for attr in cls._LAZY_ATTRIBUTES:
            val = tag.get(attr)
            if val and isinstance(val, str):
                cleaned = cls.clean_image_url(val)
                if cleaned:
                    return cleaned

        # 2. Check srcset (take the largest descriptor)
        srcset = tag.get("srcset")
        if srcset and isinstance(srcset, str):
            candidates = srcset.split(",")
            if candidates:
                last_candidate = candidates[-1].strip().split(" ")[0]
                cleaned = cls.clean_image_url(last_candidate)
                if cleaned:
                    return cleaned

        return None

    @classmethod
    def extract_gallery(
        cls,
        soup: BeautifulSoup,
        primary_selectors: Optional[List[str]] = None,
        gallery_selectors: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], List[ImageRecord]]:
        """
        Extract primary image URL and deduplicated list of ImageRecord instances.
        """
        seen_urls: Set[str] = set()
        image_records: List[ImageRecord] = []
        primary_url: Optional[str] = None

        default_primary_sel = [
            ".pdp-mod-common-image",
            "#landingImage",
            "#main-image",
            ".gallery-preview-panel__image img",
            ".product__media img",
            "[data-testid='main-image']",
        ]
        default_gallery_sel = [
            ".item-gallery img",
            ".altImages img",
            ".gallery-image",
            ".gallery-image img",
            ".product-gallery img",
            ".pdp-block img",
            ".gallery img",
            ".image-thumbnails img",
            ".thumbnails img",
        ]

        # 1. Primary image
        for sel in (primary_selectors or default_primary_sel):
            tag = soup.select_one(sel)
            if tag and isinstance(tag, Tag):
                url = cls.extract_from_img_tag(tag)
                if url:
                    primary_url = url
                    seen_urls.add(url)
                    image_records.append(
                        ImageRecord(url=url, position=0, is_primary=True, alt_text=tag.get("alt"))
                    )
                    break

        # 2. Gallery images
        for sel in (gallery_selectors or default_gallery_sel):
            for tag in soup.select(sel):
                if isinstance(tag, Tag):
                    url = cls.extract_from_img_tag(tag)
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        pos = len(image_records)
                        is_prim = (primary_url is None and pos == 0)
                        if is_prim:
                            primary_url = url
                        image_records.append(
                            ImageRecord(url=url, position=pos, is_primary=is_prim, alt_text=tag.get("alt"))
                        )

        # Fallback to any <img> tags if no gallery selectors matched
        if len(image_records) <= 1:
            for tag in soup.find_all("img"):
                if isinstance(tag, Tag):
                    url = cls.extract_from_img_tag(tag)
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        pos = len(image_records)
                        is_prim = (primary_url is None and pos == 0)
                        if is_prim:
                            primary_url = url
                        image_records.append(
                            ImageRecord(url=url, position=pos, is_primary=is_prim, alt_text=tag.get("alt"))
                        )

        return primary_url, image_records

    @classmethod
    def extract_from_json_list(cls, urls: List[str]) -> Tuple[Optional[str], List[ImageRecord]]:
        """Normalize and deduplicate an array of raw image URLs from JSON/JSON-LD state."""
        seen: Set[str] = set()
        records: List[ImageRecord] = []
        primary_url: Optional[str] = None

        for u in urls:
            clean = cls.clean_image_url(u)
            if clean and clean not in seen:
                seen.add(clean)
                pos = len(records)
                is_prim = (pos == 0)
                if is_prim:
                    primary_url = clean
                records.append(ImageRecord(url=clean, position=pos, is_primary=is_prim))

        return primary_url, records
