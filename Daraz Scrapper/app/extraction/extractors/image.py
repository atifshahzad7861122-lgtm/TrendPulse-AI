"""Image extraction, high-res resolution preference, and deduplication."""

import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from app.models.image import Image


class ImageExtractor:
    """Extracts, filters, deduplicates, and normalizes product gallery image URLs."""

    GALLERY_SELECTORS = [
        ".item-gallery__thumbnail-image",
        ".pdp-mod-common-image.gallery-preview-panel__image",
        ".pdp-gallery-thumbnail-img",
        ".gallery-preview-panel img",
        "#module_item_gallery img",
        "[data-qa-locator='product-image']",
        ".pdp-block__main-information img",
        ".pdp-gallery img",
    ]

    PRIMARY_IMAGE_SELECTORS = [
        ".gallery-preview-panel__image",
        ".pdp-mod-common-image.gallery-preview-panel__image",
        "img.pdp-mod-common-image",
        "meta[property='og:image']",
    ]

    @staticmethod
    def clean_image_url(url: str, prefer_high_res: bool = True) -> Optional[str]:
        """Normalize URL scheme, strip thumbnail resize patterns (e.g. _80x80.jpg), and deduplicate."""
        if not url or not url.strip():
            return None

        cleaned = url.strip()

        if cleaned.startswith("//"):
            cleaned = f"https:{cleaned}"

        if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
            return None

        if prefer_high_res:
            cleaned = re.sub(r"_\d+x\d+q?\d*\.(?:jpg|png|webp|jpeg)(?:_\.webp)?$", "", cleaned)
            cleaned = re.sub(r"_\d+x\d+\.(?:jpg|png|webp|jpeg)$", "", cleaned)
            cleaned = re.sub(r"_\.webp$", "", cleaned)

        return cleaned

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
        json_ld: Optional[Dict[str, Any]] = None,
        product_id: Optional[str] = None,
        prefer_high_res: bool = True,
        max_images: int = 20,
    ) -> List[Image]:
        """
        Extract list of deduplicated Image objects.
        """
        image_urls: List[str] = []
        seen_urls = set()

        def _add_image(img_url: Optional[str]):
            if not img_url:
                return
            clean = self.clean_image_url(img_url, prefer_high_res=prefer_high_res)
            if clean and clean not in seen_urls and len(image_urls) < max_images:
                if not any(icon in clean.lower() for icon in ["icon", "badge", "avatar", "logo"]):
                    seen_urls.add(clean)
                    image_urls.append(clean)

        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json)
            if isinstance(fields, dict):
                gallery_data = (
                    fields.get("productImages")
                    or fields.get("skuGalleries")
                    or fields.get("images")
                    or []
                )
                if isinstance(gallery_data, dict):
                    gallery_data = list(gallery_data.values())

                if isinstance(gallery_data, list):
                    for item in gallery_data:
                        if isinstance(item, str):
                            _add_image(item)
                        elif isinstance(item, dict):
                            _add_image(item.get("src") or item.get("url") or item.get("path"))

        # 2. JSON-LD
        if not image_urls and json_ld:
            j_images = json_ld.get("image")
            if isinstance(j_images, str):
                _add_image(j_images)
            elif isinstance(j_images, list):
                for img in j_images:
                    if isinstance(img, str):
                        _add_image(img)
                    elif isinstance(img, dict):
                        _add_image(img.get("url"))

        # 3. DOM Gallery Images
        for sel in self.GALLERY_SELECTORS:
            for el in soup.select(sel):
                src = (
                    el.get("data-origin-src")
                    or el.get("data-src")
                    or el.get("data-lazy-src")
                    or el.get("src")
                )
                _add_image(str(src) if src else None)

        # 4. OpenGraph and primary image selectors fallback
        if not image_urls:
            for sel in self.PRIMARY_IMAGE_SELECTORS:
                el = soup.select_one(sel)
                if el:
                    src = el.get("content") or el.get("src")
                    _add_image(str(src) if src else None)

        return [
            Image(
                product_id=product_id,
                url=u,
                position=idx,
                is_primary=(idx == 0),
            )
            for idx, u in enumerate(image_urls)
        ]
