import asyncio
import re
from captcha_handler import handle_captcha_if_present
from extractors.variations_parser import extract_variations
from logger import logger

async def extract_product_details(page, url: str) -> dict:
    """Extracts full product overview, galleries, prices, specs, and seller performance."""
    logger.info(f"Extracting product information: {url}")
    await handle_captcha_if_present(page)

    # 1. Title & Pricing
    title_el = await page.query_selector(".pdp-mod-product-badge-title, h1")
    title = (await title_el.inner_text()).strip() if title_el else "N/A"

    price_el = await page.query_selector(".pdp-price_type_normal, .pdp-price")
    current_price = (await price_el.inner_text()).strip() if price_el else "N/A"

    orig_price_el = await page.query_selector(".pdp-price_type_deleted")
    original_price = (await orig_price_el.inner_text()).strip() if orig_price_el else current_price

    disc_el = await page.query_selector(".pdp-product-price__discount")
    discount = (await disc_el.inner_text()).strip() if disc_el else "0%"

    currency = "PKR" if ("Rs." in current_price or "PKR" in current_price) else "PKR"

    brand_el = await page.query_selector(".pdp-link_theme_blue, .pdp-product-brand__brand-link")
    brand = (await brand_el.inner_text()).strip() if brand_el else "No Brand"

    # 2. Ratings & Review/Sold Counts
    rating_el = await page.query_selector(".score .score-average, .pdp-review-summary__score")
    rating = (await rating_el.inner_text()).strip() if rating_el else "N/A"

    review_count_el = await page.query_selector(".pdp-review-summary__link, .count")
    total_reviews = (await review_count_el.inner_text()).strip() if review_count_el else "0"

    sold_count_el = await page.query_selector(".pdp-mod-product-badge-sub, [class*='sold']")
    sold_count = (await sold_count_el.inner_text()).strip() if sold_count_el else "Not Available"

    # 3. Product Description & Highlights
    desc_el = await page.query_selector(".pdp-product-highlights, .pdp-product-desc, .html-content")
    description = (await desc_el.inner_text()).strip() if desc_el else "No description provided."

    # 4. Image Gallery Extraction
    image_gallery = []
    img_elements = await page.query_selector_all(".item-gallery__thumbnail-image, .pdp-mod-common-image, .gallery-preview-panel img")
    for img in img_elements:
        src = await img.get_attribute("src")
        if src:
            clean_url = re.sub(r'_\d+x\d+.*$', '', src)
            clean_url = f"https:{clean_url}" if clean_url.startswith("//") else clean_url
            if clean_url not in image_gallery:
                image_gallery.append(clean_url)

    # 5. Breadcrumbs / Categories
    categories = []
    crumbs = await page.query_selector_all(".breadcrumb_item, .lzd-breadcrumb li")
    for c in crumbs:
        text = (await c.inner_text()).strip()
        if text and text != "/":
            categories.append(text)
    category = " > ".join(categories) if categories else "General"

    # 6. Seller Metrics & ID
    seller_el = await page.query_selector(".seller-name__detail-name")
    seller_name = (await seller_el.inner_text()).strip() if seller_el else "N/A"

    seller_link_el = await page.query_selector(".seller-name__detail a")
    seller_href = await seller_link_el.get_attribute("href") if seller_link_el else ""
    seller_id = seller_href.rstrip("/").split("/")[-1] if seller_href else "N/A"

    seller_metrics = {}
    v_nodes = await page.query_selector_all(".seller-info-value")
    t_nodes = await page.query_selector_all(".seller-info-title")
    for t, v in zip(t_nodes, v_nodes):
        seller_metrics[(await t.inner_text()).strip()] = (await v.inner_text()).strip()

    # 7. Product ID & SKU Extraction
    product_id = "N/A"
    if "-i" in url:
        try:
            product_id = url.split("-i")[-1].split(".html")[0].split("-")[0]
        except Exception:
            pass

    sku_el = await page.query_selector(".pdp-sku-property-item, [data-sku-id]")
    sku = (await sku_el.get_attribute("data-sku-id")) if sku_el else f"SKU-{product_id}"

    # 8. Specifications
    await page.evaluate("window.scrollBy({ top: 800, behavior: 'smooth' })")
    await asyncio.sleep(1.5)
    await handle_captcha_if_present(page)

    specs = {}
    spec_items = await page.query_selector_all(".specification-keys li")
    for item in spec_items:
        k_node = await item.query_selector(".key-title")
        v_node = await item.query_selector(".key-value")
        if k_node and v_node:
            specs[(await k_node.inner_text()).strip()] = (await v_node.inner_text()).strip()

    # 9. Variations
    variations = await extract_variations(page)

    return {
        "product_id": product_id,
        "sku": sku,
        "url": url,
        "title": title,
        "description": description,
        "current_price": current_price,
        "original_price": original_price,
        "discount": discount,
        "currency": currency,
        "brand": brand,
        "category": category,
        "rating": rating,
        "total_reviews": total_reviews,
        "sold_count": sold_count,
        "seller_name": seller_name,
        "seller_id": seller_id,
        "seller_metrics": seller_metrics,
        "image_gallery": image_gallery,
        "variations": variations,
        "specifications": specs
    }
