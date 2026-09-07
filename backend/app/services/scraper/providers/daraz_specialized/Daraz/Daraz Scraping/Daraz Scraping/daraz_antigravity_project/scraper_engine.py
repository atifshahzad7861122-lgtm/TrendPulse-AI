import os
import re
import json
import logging
import asyncio
import urllib.parse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHROME_PROFILE_DIR = os.path.abspath("./chrome_recording_profile")

async def detect_and_handle_captcha(page):
    """
    Halts execution and opens human-in-the-loop prompt if an Alibaba/Daraz CAPTCHA appears.
    """
    captcha_selectors = [
        "#nc_1_n1z", "#nocaptcha", ".nc-container",
        "iframe[src*='captcha']", "#baxia-dialog-content", ".punish-dialog"
    ]
    for selector in captcha_selectors:
        element = await page.query_selector(selector)
        if element and await element.is_visible():
            print("\n" + "="*65)
            print("🚨 [HUMAN-IN-THE-LOOP TRIGGERED] CAPTCHA / Security Shield detected!")
            print("👉 Please solve the slider/verification directly in the browser.")
            print("="*65)
            await asyncio.to_thread(input, "Press [ENTER] in this terminal once solved...")
            print("CAPTCHA resolved. Continuing scraping process...\n")
            await asyncio.sleep(2)
            break

def parse_page_data_json(html_content):
    """
    Search for window.pageData JSON object within the script tags.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup.find_all('script'):
        if script.string and 'window.pageData=' in script.string:
            try:
                json_str = script.string.split('window.pageData=')[1]
                json_str = json_str.split(';')[0].strip()
                return json.loads(json_str)
            except Exception as e:
                logger.error(f"Error parsing script pageData JSON: {e}")
    return None

def extract_products_from_json(page_data, domain):
    """
    Extracts structured product list from window.pageData structure.
    """
    products = []
    
    list_items = None
    if isinstance(page_data, dict):
        list_items = page_data.get('mods', {}).get('listItems')
        if not list_items:
            list_items = page_data.get('mainInfo', {}).get('listItems')
        if not list_items:
            list_items = page_data.get('globalData', {}).get('listItems')
            
    if not list_items:
        return products

    for item in list_items:
        product_url = item.get('productUrl', '')
        if product_url.startswith('//'):
            product_url = 'https:' + product_url
        elif product_url.startswith('/'):
            product_url = f'https://www.{domain}' + product_url
        elif not product_url.startswith('http'):
            product_url = f'https://www.{domain}/products/' + product_url

        image_url = item.get('image', '')
        if image_url.startswith('//'):
            image_url = 'https:' + image_url

        price_show = item.get('priceShow', item.get('price', ''))
        original_price = item.get('originalPrice', '')
        discount = item.get('discount', '')
        
        rating = item.get('ratingScore', item.get('rating', '0'))
        try:
            rating = float(rating)
        except ValueError:
            rating = 0.0

        reviews = item.get('review', item.get('reviewCount', '0'))
        try:
            reviews = int(reviews)
        except ValueError:
            reviews = 0

        product = {
            'Title': item.get('name', ''),
            'Price': price_show,
            'Original Price': original_price,
            'Discount': discount,
            'Rating': rating,
            'Reviews': reviews,
            'Location': item.get('location', ''),
            'Brand': item.get('brandName', item.get('brand', 'Generic')),
            'URL': product_url,
            'Image URL': image_url
        }
        products.append(product)
        
    return products

def parse_dom_item(item, domain, idx):
    """
    Extracts product data from a BeautifulSoup DOM element representing a product card.
    """
    title = ""
    link = ""
    title_el = item.select_one('div.RfADt a') or item.select_one('a[title]')
    if title_el:
        title = title_el.get('title', title_el.text.strip())
        link = title_el.get('href', '')
    
    if not title:
        fallback_title_el = item.select_one('[class*="title"]') or item.select_one('[class*="name"]')
        title = fallback_title_el.text.strip() if fallback_title_el else f"Product {idx}"
        
    if not link:
        url_el = item.select_one('a')
        link = url_el.get('href', '') if url_el else ''

    if link.startswith('//'):
        link = 'https:' + link
    elif link.startswith('/'):
        link = f'https://www.{domain}' + link

    price = ""
    price_el = item.select_one('.ooOxS')
    if price_el:
        price = price_el.text.strip()
    else:
        for span in item.find_all('span'):
            text = span.text.strip()
            if any(symbol in text for symbol in ['Rs.', 'Tk.', 'NPR', 'LKR', 'Rs']):
                price = text
                break

    discount = ""
    discount_el = item.select_one('.IcOsH')
    if discount_el:
        discount = discount_el.text.strip()
    else:
        for span in item.find_all('span'):
            text = span.text.strip()
            if '%' in text and ('Off' in text or 'OFF' in text or 'off' in text):
                discount = text
                break

    original_price = ""
    if price and discount:
        try:
            price_num_str = re.sub(r'[^\d]', '', price)
            discount_num_str = re.sub(r'[^\d]', '', discount)
            if price_num_str and discount_num_str:
                price_num = float(price_num_str)
                discount_num = float(discount_num_str)
                if 0 < discount_num < 100:
                    orig_num = price_num / (1.0 - (discount_num / 100.0))
                    prefix_match = re.match(r'^([^\d]+)', price)
                    prefix = prefix_match.group(1).strip() if prefix_match else "Rs."
                    original_price = f"{prefix} {int(round(orig_num)):,}"
        except Exception as calc_err:
            logger.debug(f"Could not calculate original price: {calc_err}")

    rating = 0.0
    rating_container = item.select_one('.mdmmT') or item.select_one('[class*="rating"]')
    if rating_container:
        stars = rating_container.find_all('i')
        full_stars = 0
        has_fraction = False
        for star in stars:
            classes = star.get('class', [])
            if 'Dy1nx' in classes or any('star-filled' in c for c in classes):
                full_stars += 1
            elif any(c not in ['_9-ogB', 'star-empty'] for c in classes):
                has_fraction = True
        
        rating = float(full_stars)
        if has_fraction:
            rating += 0.5
    else:
        stars = item.select('i[class*="star"]')
        if stars:
            rating = float(len([s for s in stars if 'filled' in str(s.get('class', []))]))

    reviews = 0
    reviews_el = item.select_one('.qzqFw') or item.select_one('[class*="review"]')
    if reviews_el:
        reviews_text = reviews_el.text.strip()
        digits = re.sub(r'[^\d]', '', reviews_text)
        if digits:
            reviews = int(digits)
    else:
        for span in item.find_all('span'):
            text = span.text.strip()
            if re.match(r'^\(\d+\)$', text):
                reviews = int(re.sub(r'[^\d]', '', text))
                break

    location = ""
    location_el = item.select_one('.oa6ri') or item.select_one('[class*="location"]')
    if location_el:
        location = location_el.get('title', location_el.text.strip())
    else:
        for span in item.find_all('span'):
            if span.get('title'):
                location = span['title']
                break

    img_url = ""
    img_el = item.select_one('img')
    if img_el:
        img_url = img_el.get('src', img_el.get('data-src', ''))
        if img_url.startswith('//'):
            img_url = 'https:' + img_url

    return {
        'Title': title,
        'Price': price,
        'Original Price': original_price,
        'Discount': discount,
        'Rating': rating,
        'Reviews': reviews,
        'Location': location,
        'Brand': 'Generic',
        'URL': link,
        'Image URL': img_url
    }

async def run_daraz_scraper(url: str, max_review_pages: int = 3):
    """
    Executes the Playwright session in a dedicated persistent Chrome profile.
    Scrapes single product detail, specs, and reviews.
    """
    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE_DIR,
                channel="chrome",
                headless=False,
                slow_mo=400,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run"
                ],
                ignore_default_args=["--enable-automation"]
            )
        except Exception as e:
            logger.warning(f"Failed to launch with persistent Chrome context: {e}. Retrying with default chromium...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE_DIR,
                headless=False,
                slow_mo=400,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run"
                ],
                ignore_default_args=["--enable-automation"]
            )

        page = context.pages[0] if context.pages else await context.new_page()

        logger.info(f"Navigating to product URL: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        await detect_and_handle_captcha(page)

        # 1. Product Core Details
        title_el = await page.query_selector(".pdp-mod-product-badge-title, h1, .pdp-mod-product-title")
        price_el = await page.query_selector(".pdp-price_type_normal, .pdp-price, .pdp-product-price")
        orig_price_el = await page.query_selector(".pdp-price_type_deleted, del")
        # Ensure brand element targets specific brand tags before generic blue links
        brand_el = await page.query_selector(".pdp-product-brand__brand-link, .pdp-link-brand, .brand, .pdp-link_theme_blue")
        seller_el = await page.query_selector(".seller-name__detail-name, .seller-name__detail")

        # Strip newline/extra details from elements
        title_text = (await title_el.inner_text()).strip() if title_el else "N/A"
        
        price_text = "N/A"
        if price_el:
            price_text = (await price_el.inner_text()).strip()
            if "\n" in price_text:
                price_text = price_text.split("\n")[0].strip()
                
        orig_price_text = "N/A"
        if orig_price_el:
            orig_price_text = (await orig_price_el.inner_text()).strip()
            if "\n" in orig_price_text:
                orig_price_text = orig_price_text.split("\n")[0].strip()

        brand_text = (await brand_el.inner_text()).strip() if brand_el else "No Brand"
        if "rating" in brand_text.lower() or "review" in brand_text.lower():
            brand_text = "No Brand" # Fallback if it matches rating elements

        product_data = {
            "title": title_text,
            "price": price_text,
            "original_price": orig_price_text,
            "brand": brand_text,
            "seller_name": (await seller_el.inner_text()).strip() if seller_el else "N/A",
            "url": url,
            "seller_metrics": {}
        }

        # Seller Metrics
        val_nodes = await page.query_selector_all(".seller-info-value")
        title_nodes = await page.query_selector_all(".seller-info-title")
        for t, v in zip(title_nodes, val_nodes):
            product_data["seller_metrics"][(await t.inner_text()).strip()] = (await v.inner_text()).strip()

        # 2. Specifications
        await page.evaluate("window.scrollBy({ top: 800, behavior: 'smooth' })")
        await asyncio.sleep(1.5)
        await detect_and_handle_captcha(page)

        specs = {}
        spec_items = await page.query_selector_all(".specification-keys li, .pdp-mod-specification li.key-li")
        for item in spec_items:
            k_node = await item.query_selector(".key-title")
            v_node = await item.query_selector(".key-value")
            if k_node and v_node:
                specs[(await k_node.inner_text()).strip()] = (await v_node.inner_text()).strip()
            else:
                text = (await item.inner_text()).strip()
                parts = re.split(r'\s{2,}', text)
                if len(parts) >= 2:
                    specs[parts[0].strip()] = parts[1].strip()

        # 3. Reviews Extraction & Pagination
        for _ in range(3):
            await page.evaluate("window.scrollBy({ top: 900, behavior: 'smooth' })")
            await asyncio.sleep(1)

        reviews = []
        current_rev_page = 1

        while current_rev_page <= max_review_pages:
            await detect_and_handle_captcha(page)
            try:
                await page.wait_for_selector(".mod-reviews .item, .pdp-mod-review .item", timeout=6000)
                items = await page.query_selector_all(".mod-reviews .item, .pdp-mod-review .item")
            except Exception:
                logger.info(f"No more reviews found on page {current_rev_page}.")
                break

            for rev in items:
                u_el = await rev.query_selector(".user-name, .middle")
                d_el = await rev.query_selector(".title.right, .date")
                c_el = await rev.query_selector(".content, .review-content")
                s_el = await rev.query_selector(".skuInfo, [class*='sku']")
                stars = await rev.query_selector_all(".star, .i-rate-star")

                img_nodes = await rev.query_selector_all(".review-image img, .image-item img")
                images = [await img.get_attribute("src") for img in img_nodes if await img.get_attribute("src")]

                rating = len(stars) if stars else 5
                if stars:
                    calc_rating = 0
                    for star in stars:
                        star_html = await star.inner_html()
                        if 'rgb(255, 200, 60)' in star_html:
                            calc_rating += 1
                    if calc_rating > 0:
                        rating = calc_rating

                reviews.append({
                    "page": current_rev_page,
                    "reviewer": (await u_el.inner_text()).strip() if u_el else "Anonymous",
                    "date": (await d_el.inner_text()).strip() if d_el else "N/A",
                    "rating": rating,
                    "variation": (await s_el.inner_text()).strip() if s_el else "N/A",
                    "content": (await c_el.inner_text()).strip() if c_el else "No written text",
                    "images": ", ".join([("https:" + img if img.startswith("//") else img) for img in images])
                })

            # Next button handling
            next_btn = await page.query_selector(".next-btn, .ant-pagination-next, button[class*='next']")
            if not next_btn:
                break
            is_disabled = await next_btn.get_attribute("aria-disabled")
            btn_class = await next_btn.get_attribute("class") or ""
            if is_disabled == "true" or "disabled" in btn_class.lower():
                break

            await next_btn.scroll_into_view_if_needed()
            await next_btn.click()
            current_rev_page += 1
            await asyncio.sleep(2)

        await context.close()
        return product_data, specs, reviews

async def async_scrape_daraz_search(query, domain="daraz.pk", max_pages=1):
    """
    Asynchronously crawls product search result catalogs using Playwright.
    """
    all_products = []
    
    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE_DIR,
                channel="chrome",
                headless=False,
                slow_mo=400,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run"
                ],
                ignore_default_args=["--enable-automation"]
            )
        except Exception as e:
            logger.warning(f"Failed to launch persistent Chrome context: {e}. Retrying with default chromium...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=CHROME_PROFILE_DIR,
                headless=False,
                slow_mo=400,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run"
                ],
                ignore_default_args=["--enable-automation"]
            )
            
        page = context.pages[0] if context.pages else await context.new_page()
        
        for current_page in range(1, max_pages + 1):
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.{domain}/catalog/?q={encoded_query}&page={current_page}"
            logger.info(f"Navigating to page {current_page}: {url}")
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                await detect_and_handle_captcha(page)
                
                # Fetch DOM content and parse
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                page_data = parse_page_data_json(html_content)
                if not page_data:
                    try:
                        page_data = await page.evaluate("() => window.pageData")
                    except Exception:
                        page_data = None
                        
                if page_data:
                    products = extract_products_from_json(page_data, domain)
                    logger.info(f"Extracted {len(products)} products from pageData JSON.")
                    all_products.extend(products)
                else:
                    items = soup.select('div[data-qa-locator="product-item"]')
                    if not items:
                        items = soup.select('.gridItem') or soup.select('[class*="product-item"]')
                        
                    logger.info(f"Found {len(items)} product elements via DOM selector.")
                    page_products = []
                    for idx, item in enumerate(items):
                        try:
                            product = parse_dom_item(item, domain, idx)
                            page_products.append(product)
                        except Exception as parse_err:
                            logger.error(f"Error parsing DOM item {idx}: {parse_err}")
                    all_products.extend(page_products)
                    
            except Exception as page_err:
                logger.error(f"Error loading or scraping search page {current_page}: {page_err}")
                
        await context.close()
        
    return all_products
