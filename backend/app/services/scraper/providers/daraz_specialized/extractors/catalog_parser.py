"""Catalog and Search Results Parser for Daraz."""
import re
import json
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger("trendpulse.scraper.daraz.catalog")


def parse_page_data_json(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Search for window.pageData or __INITIAL_STATE__ JSON object within script tags.
    """
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup.find_all('script'):
        content = script.string or script.text or ""
        if not content:
            continue
        if 'window.pageData=' in content:
            try:
                json_str = content.split('window.pageData=')[1]
                json_str = json_str.split(';')[0].strip()
                return json.loads(json_str)
            except Exception as e:
                logger.debug(f"Error parsing script pageData JSON: {e}")
        elif 'pageData=' in content:
            match = re.search(r'pageData\s*=\s*(\{.*?\});', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
    return None


def extract_products_from_json(page_data: Dict[str, Any], domain: str = "daraz.pk") -> List[Dict[str, Any]]:
    """
    Extracts structured product list from window.pageData JSON structure.
    """
    products = []
    if not isinstance(page_data, dict):
        return products

    list_items = (
        page_data.get('mods', {}).get('listItems')
        or page_data.get('mainInfo', {}).get('listItems')
        or page_data.get('globalData', {}).get('listItems')
        or page_data.get('fields', {}).get('listItems')
    )

    if not list_items or not isinstance(list_items, list):
        return products

    for item in list_items:
        if not isinstance(item, dict):
            continue

        raw_id = str(item.get('itemId') or item.get('nid') or item.get('id') or '')
        product_url = item.get('productUrl', '') or item.get('itemUrl', '')
        if product_url.startswith('//'):
            product_url = 'https:' + product_url
        elif product_url.startswith('/'):
            product_url = f'https://www.{domain}' + product_url
        elif product_url and not product_url.startswith('http'):
            product_url = f'https://www.{domain}/products/' + product_url

        if not raw_id and product_url and '-i' in product_url:
            try:
                raw_id = product_url.split('-i')[-1].split('.html')[0].split('-')[0]
            except Exception:
                pass

        image_url = item.get('image', '') or item.get('imageUrl', '')
        if image_url.startswith('//'):
            image_url = 'https:' + image_url

        price_show = item.get('priceShow', item.get('price', '0'))
        original_price = item.get('originalPrice', '')
        discount = item.get('discount', '')

        # Parse rating
        rating_raw = item.get('ratingScore', item.get('rating', '0'))
        try:
            rating = float(rating_raw)
        except (ValueError, TypeError):
            rating = 0.0

        # Parse reviews
        reviews_raw = item.get('review', item.get('reviewCount', '0'))
        try:
            review_count = int(reviews_raw)
        except (ValueError, TypeError):
            review_count = 0

        # Parse numeric price
        try:
            s_price = str(price_show).replace(',', '')
            m_price = re.search(r'(\d+(?:\.\d+)?)', s_price)
            price_val = float(m_price.group(1)) if m_price else 0.0
        except Exception:
            price_val = 0.0

        try:
            s_orig = str(original_price).replace(',', '')
            m_orig = re.search(r'(\d+(?:\.\d+)?)', s_orig)
            orig_val = float(m_orig.group(1)) if m_orig else price_val
        except Exception:
            orig_val = price_val

        try:
            s_disc = str(discount).replace(',', '')
            m_disc = re.search(r'(\d+(?:\.\d+)?)', s_disc)
            disc_val = float(m_disc.group(1)) if m_disc else 0.0
        except Exception:
            disc_val = 0.0

        product = {
            'product_id': raw_id or f"daraz_{len(products)+1}",
            'title': item.get('name', '') or item.get('title', ''),
            'price': price_val,
            'price_raw': str(price_show),
            'original_price': orig_val if orig_val > 0 else price_val,
            'original_price_raw': str(original_price),
            'discount': disc_val,
            'discount_label': str(discount) if discount else (f"{int(disc_val)}% Off" if disc_val > 0 else None),
            'currency': 'PKR',
            'rating': rating,
            'review_count': review_count,
            'seller_name': item.get('sellerName', ''),
            'seller_id': str(item.get('sellerId', '') or ''),
            'location': item.get('location', 'Pakistan'),
            'brand': item.get('brandName', item.get('brand', 'Generic')),
            'product_url': product_url,
            'image_url': image_url,
            'images': [image_url] if image_url else [],
            'in_stock': True,
            'category': item.get('categoryName', ''),
            'raw_data': item
        }
        products.append(product)

    return products


def parse_dom_item(item: Any, domain: str = "daraz.pk", idx: int = 0) -> Dict[str, Any]:
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

    product_id = ""
    if '-i' in link:
        try:
            product_id = link.split('-i')[-1].split('.html')[0].split('-')[0]
        except Exception:
            pass

    price_str = ""
    price_el = item.select_one('.ooOxS')
    if price_el:
        price_str = price_el.text.strip()
    else:
        for span in item.find_all('span'):
            text = span.text.strip()
            if any(symbol in text for symbol in ['Rs.', 'Tk.', 'NPR', 'LKR', 'Rs']):
                price_str = text
                break

    discount_str = ""
    discount_el = item.select_one('.IcOsH')
    if discount_el:
        discount_str = discount_el.text.strip()
    else:
        for span in item.find_all('span'):
            text = span.text.strip()
            if '%' in text and any(w in text.lower() for w in ['off', '-']):
                discount_str = text
                break

    # Calculate numeric price and original price
    price_val = 0.0
    if price_str:
        s_price = price_str.replace(',', '')
        m_price = re.search(r'(\d+(?:\.\d+)?)', s_price)
        if m_price:
            try:
                price_val = float(m_price.group(1))
            except Exception:
                price_val = 0.0

    disc_val = 0.0
    if discount_str:
        s_disc = discount_str.replace(',', '')
        m_disc = re.search(r'(\d+(?:\.\d+)?)', s_disc)
        if m_disc:
            try:
                disc_val = float(m_disc.group(1))
            except Exception:
                disc_val = 0.0

    orig_val = price_val
    if price_val > 0 and disc_val > 0 and disc_val < 100:
        orig_val = round(price_val / (1.0 - (disc_val / 100.0)), 2)

    # Stars
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
        rating = float(full_stars) + (0.5 if has_fraction else 0.0)
    else:
        stars = item.select('i[class*="star"]')
        if stars:
            rating = float(len([s for s in stars if 'filled' in str(s.get('class', []))]))

    # Reviews
    review_count = 0
    reviews_el = item.select_one('.qzqFw') or item.select_one('[class*="review"]')
    if reviews_el:
        digits = re.sub(r'[^\d]', '', reviews_el.text.strip())
        if digits:
            review_count = int(digits)
    else:
        for span in item.find_all('span'):
            text = span.text.strip()
            if re.match(r'^\(\d+\)$', text):
                review_count = int(re.sub(r'[^\d]', '', text))
                break

    location = "Pakistan"
    location_el = item.select_one('.oa6ri') or item.select_one('[class*="location"]')
    if location_el:
        location = location_el.get('title', location_el.text.strip()) or "Pakistan"

    img_url = ""
    img_el = item.select_one('img')
    if img_el:
        img_url = img_el.get('src', img_el.get('data-src', ''))
        if img_url.startswith('//'):
            img_url = 'https:' + img_url

    return {
        'product_id': product_id or f"daraz_{idx}",
        'title': title,
        'price': price_val,
        'price_raw': price_str,
        'original_price': orig_val,
        'original_price_raw': f"Rs. {orig_val:.0f}" if orig_val > 0 else price_str,
        'discount': disc_val,
        'discount_label': discount_str or (f"{int(disc_val)}% Off" if disc_val > 0 else None),
        'currency': 'PKR',
        'rating': rating,
        'review_count': review_count,
        'seller_name': '',
        'seller_id': '',
        'location': location,
        'brand': 'Generic',
        'product_url': link,
        'image_url': img_url,
        'images': [img_url] if img_url else [],
        'in_stock': True,
        'category': '',
        'raw_data': {}
    }
