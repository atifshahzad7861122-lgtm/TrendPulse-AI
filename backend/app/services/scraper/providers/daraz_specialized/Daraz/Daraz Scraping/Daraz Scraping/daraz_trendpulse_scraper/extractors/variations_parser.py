import logging
from config import PROJECT_NAME

logger = logging.getLogger(PROJECT_NAME)

async def extract_variations(page) -> list:
    """Extracts available product variations, swatches, and sizing attributes."""
    variations = []
    swatch_elements = await page.query_selector_all(".sku-prop-content, .sku-variable-img-wrap, .sku-name")
    for elem in swatch_elements:
        title = await elem.get_attribute("title")
        text = (await elem.inner_text()).strip() if not title else title.strip()
        if text and text not in variations:
            variations.append(text)
    return variations
