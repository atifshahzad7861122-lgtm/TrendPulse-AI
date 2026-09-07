"""Product Detail, Specs, Gallery, and Seller Parser for Daraz."""
import asyncio
import re
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from .variations_parser import extract_variations

logger = logging.getLogger("trendpulse.scraper.daraz.product")


def _clean_price_digits(price_str: str) -> float:
    if not price_str:
        return 0.0
    s = str(price_str).replace(',', '')
    match = re.search(r'(\d+(?:\.\d+)?)', s)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return 0.0
    return 0.0


async def extract_product_details(page: Any, url: str, challenge_detector: Any = None) -> Dict[str, Any]:
    """
    Extracts full product overview, specifications, high-resolution galleries,
    pricing, discounts, seller performance metrics, and variations from a loaded Playwright Page.
    Uses BeautifulSoup on page.content() for high-performance, zero-latency extraction.
    """
    logger.info(f"Extracting product information from {url}")
    if challenge_detector:
        await challenge_detector(page)

    # 1. Product ID & SKU Extraction
    product_id = "N/A"
    if "-i" in url:
        try:
            product_id = url.split("-i")[-1].split(".html")[0].split("-")[0]
        except Exception:
            pass

    # Grab DOM snapshot once
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    # SKU
    sku_el = soup.select_one(".pdp-sku-property-item, [data-sku-id]")
    sku = sku_el.get("data-sku-id") if (sku_el and sku_el.get("data-sku-id")) else f"SKU-{product_id}"

    # 2. Title & Brand
    title_el = soup.select_one(".pdp-mod-product-badge-title, h1, .pdp-mod-product-title, .pdp-product-title, .pdp-title, [class*='product-title']")
    title = title_el.get_text(strip=True) if title_el else ""
    if "\n" in title:
        title = title.split("\n")[0].strip()

    brand_el = soup.select_one(".pdp-product-brand__brand-link, .pdp-link-brand, .brand, .pdp-link_theme_blue")
    brand = brand_el.get_text(strip=True) if brand_el else ""
    if "rating" in brand.lower() or "review" in brand.lower():
        brand = "Generic"

    # 3. Pricing, Discounts & Currency
    price_el = soup.select_one(".pdp-price_type_normal, .pdp-price, .pdp-product-price, .notranslate.pdp-price, [class*='price_type_normal'], [class*='pdp-price'], .pdp-mod-product-price, [class*='product-price']")
    current_price_str = price_el.get_text(strip=True) if price_el else ""
    if "\n" in current_price_str:
        current_price_str = current_price_str.split("\n")[0].strip()
    price = _clean_price_digits(current_price_str)

    if price <= 0:
        try:
            eval_price = await page.evaluate("""() => {
                const el = document.querySelector('.pdp-price_type_normal, .pdp-price, .pdp-product-price, [class*="price_type_normal"], [class*="pdp-price"]');
                return el ? el.innerText : '';
            }""")
            if eval_price:
                price = _clean_price_digits(eval_price)
        except Exception:
            pass

    orig_price_el = soup.select_one(".pdp-price_type_deleted, del, [class*='price_type_deleted'], [class*='original-price']")
    orig_price_str = orig_price_el.get_text(strip=True) if orig_price_el else current_price_str
    if "\n" in orig_price_str:
        orig_price_str = orig_price_str.split("\n")[0].strip()
    original_price = _clean_price_digits(orig_price_str)
    if original_price <= 0:
        original_price = price

    disc_el = soup.select_one(".pdp-product-price__discount, .pdp-price__discount, [class*='discount']")
    discount_str = disc_el.get_text(strip=True) if disc_el else ""
    discount = _clean_price_digits(discount_str)
    if discount <= 0 and original_price > price and original_price > 0:
        discount = round(((original_price - price) / original_price) * 100.0, 1)

    # JSON-LD and pageData fallback if DOM is not fully hydrated
    if not title or price <= 0:
        for script in soup.find_all("script"):
            s_text = script.string or script.text or ""
            if 'type="application/ld+json"' in str(script.attrs) or "application/ld+json" in str(script.get("type", "")):
                try:
                    import json
                    ld_data = json.loads(s_text)
                    if isinstance(ld_data, dict):
                        if not title and ld_data.get("name"):
                            title = ld_data["name"]
                        if not brand and isinstance(ld_data.get("brand"), dict):
                            brand = ld_data["brand"].get("name", "Generic")
                        offers = ld_data.get("offers")
                        if isinstance(offers, dict) and price <= 0:
                            price = float(offers.get("price") or 0.0)
                            if original_price <= 0:
                                original_price = price
                except Exception:
                    pass

    if not title:
        title = "Daraz Product"
    if not brand:
        brand = "Generic"

    currency = "PKR"

    # 4. Ratings, Review & Sold Counts
    rating_el = soup.select_one(".score .score-average, .pdp-review-summary__score")
    rating_str = rating_el.get_text(strip=True) if rating_el else "0.0"
    try:
        rating = float(re.sub(r'[^\d.]', '', rating_str)) if rating_str else 0.0
    except Exception:
        rating = 0.0

    review_count_el = soup.select_one(".pdp-review-summary__link, .count")
    review_count_str = review_count_el.get_text(strip=True) if review_count_el else "0"
    try:
        review_count = int(re.sub(r'[^\d]', '', review_count_str)) if review_count_str else 0
    except Exception:
        review_count = 0

    sold_count_el = soup.select_one(".pdp-mod-product-badge-sub, [class*='sold']")
    sold_count_str = sold_count_el.get_text(strip=True) if sold_count_el else ""
    sold_count = None
    if sold_count_str:
        digits = re.sub(r'[^\d]', '', sold_count_str)
        if digits:
            sold_count = int(digits)

    # 5. Product Description & Highlights
    desc_el = soup.select_one(".pdp-product-highlights, .pdp-product-desc, .html-content, .detail-desc")
    description = desc_el.get_text(separator="\n", strip=True) if desc_el else "No description provided."

    # 6. High-Resolution Image Gallery
    image_gallery: List[str] = []
    img_elements = soup.select(".item-gallery__thumbnail-image, .pdp-mod-common-image, .gallery-preview-panel img, .item-gallery img")
    for img in img_elements:
        src = img.get("src") or img.get("data-src")
        if src:
            clean_url = re.sub(r'_\d+x\d+.*$', '', src)
            clean_url = f"https:{clean_url}" if clean_url.startswith("//") else clean_url
            if clean_url not in image_gallery:
                image_gallery.append(clean_url)

    primary_image = image_gallery[0] if image_gallery else None

    # 7. Category Breadcrumbs Hierarchy
    categories = []
    crumbs = soup.select(".breadcrumb_item, .lzd-breadcrumb li, .breadcrumb li")
    for c in crumbs:
        text = c.get_text(strip=True)
        if text and text != "/":
            categories.append(text)
    category = " > ".join(categories) if categories else "General"

    # 8. Seller Name, ID, URL & Metrics
    seller_el = soup.select_one(".seller-name__detail-name, .seller-name__detail")
    seller_name = seller_el.get_text(strip=True) if seller_el else "Daraz Seller"

    seller_link_el = soup.select_one(".seller-name__detail a, .seller-name a")
    seller_href = seller_link_el.get("href") if (seller_link_el and seller_link_el.get("href")) else ""
    if seller_href and seller_href.startswith("//"):
        seller_href = "https:" + seller_href
    seller_id = seller_href.rstrip("/").split("/")[-1] if seller_href else "seller_01"

    seller_metrics: Dict[str, str] = {}
    v_nodes = soup.select(".seller-info-value")
    t_nodes = soup.select(".seller-info-title")
    for t, v in zip(t_nodes, v_nodes):
        k_str = t.get_text(strip=True)
        v_str = v.get_text(strip=True)
        if k_str and v_str:
            seller_metrics[k_str] = v_str

    # 9. Specifications Table
    specs: Dict[str, str] = {}
    spec_items = soup.select(".specification-keys li, .pdp-mod-specification li.key-li")
    for item in spec_items:
        k_node = item.select_one(".key-title")
        v_node = item.select_one(".key-value")
        if k_node and v_node:
            specs[k_node.get_text(strip=True)] = v_node.get_text(strip=True)
        else:
            text = item.get_text(strip=True)
            parts = re.split(r'\s{2,}', text)
            if len(parts) >= 2:
                specs[parts[0].strip()] = parts[1].strip()

    # 10. Variations & Swatches
    variations = await extract_variations(page)

    # 11. Availability
    in_stock = True
    buy_now_btn = soup.select_one(".buy-now, .pdp-button_theme_orange, .add-to-cart-buy-now-btn")
    if not buy_now_btn:
        out_of_stock_el = soup.select_one(".out-of-stock, [class*='outOfStock']")
        if out_of_stock_el:
            in_stock = False

    return {
        "product_id": product_id,
        "sku": sku,
        "url": url,
        "title": title,
        "description": description,
        "price": price,
        "original_price": original_price,
        "discount": discount,
        "discount_label": discount_str or (f"{int(discount)}% Off" if discount > 0 else None),
        "currency": currency,
        "brand": brand,
        "category": category,
        "rating": rating,
        "review_count": review_count,
        "sold_count": sold_count,
        "in_stock": in_stock,
        "seller_name": seller_name,
        "seller_id": seller_id,
        "seller_url": seller_href,
        "seller_metrics": seller_metrics,
        "image_url": primary_image,
        "images": image_gallery,
        "variations": variations,
        "specifications": specs,
        "raw_data": {
            "title": title,
            "price": price,
            "original_price": original_price,
            "seller_metrics": seller_metrics,
            "specs": specs
        }
    }
