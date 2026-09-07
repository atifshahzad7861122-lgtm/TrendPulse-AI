"""Variations and SKU Options Parser for Daraz."""
import logging
from typing import List, Dict, Any

logger = logging.getLogger("trendpulse.scraper.daraz.variations")


async def extract_variations(page: Any) -> List[Dict[str, Any]]:
    """
    Extracts available product variations, swatches, and sizing attributes.
    Returns structured list of variation dictionaries.
    """
    variations = []
    try:
        swatch_elements = await page.query_selector_all(".sku-prop-content, .sku-variable-img-wrap, .sku-name, .sku-item")
        for elem in swatch_elements:
            title = await elem.get_attribute("title")
            text = (await elem.inner_text()).strip() if not title else title.strip()
            sku_id = await elem.get_attribute("data-sku-id") or ""
            img_el = await elem.query_selector("img")
            img_src = await img_el.get_attribute("src") if img_el else None
            if img_src and img_src.startswith("//"):
                img_src = "https:" + img_src

            if text and not any(v.get("name") == text for v in variations):
                variations.append({
                    "sku_id": sku_id or f"sku_{len(variations)+1}",
                    "name": text,
                    "image": img_src,
                    "in_stock": True
                })
    except Exception as e:
        logger.debug(f"Error extracting variations: {e}")

    return variations
