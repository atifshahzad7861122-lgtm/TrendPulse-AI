import asyncio
import logging
from backend.app.services.scraper.providers.daraz_specialized.engine import DarazSpecializedScraperEngine

logging.basicConfig(level=logging.INFO)

# Deterministic HTML response fixtures representing real Daraz catalog and product detail responses
CATALOG_SEARCH_HTML = """<!DOCTYPE html>
<html>
<head><title>Daraz Search Results</title></head>
<body>
    <div data-qa-locator="product-item" class="gridItem">
        <div class="RfADt">
            <a title="Wireless Bluetooth Earbuds Stereo Sound" href="//www.daraz.pk/products/wireless-earbuds-i123456.html">
                Wireless Bluetooth Earbuds Stereo Sound
            </a>
        </div>
        <div class="ooOxS">Rs. 3,499</div>
        <div class="IcOsH">-30% Off</div>
        <div class="qzqFw">(48)</div>
        <img src="//img.daraz.pk/p/earbuds.jpg" />
    </div>
    <script>
    window.pageData = {
        "mods": {
            "listItems": [
                {
                    "name": "Wireless Bluetooth Earbuds Stereo Sound",
                    "priceShow": "Rs. 3,499",
                    "originalPrice": "Rs. 4,999",
                    "discount": "-30%",
                    "ratingScore": "4.8",
                    "review": "48",
                    "location": "Karachi",
                    "brandName": "SoundPulse",
                    "productUrl": "//www.daraz.pk/products/wireless-earbuds-i123456.html",
                    "image": "//img.daraz.pk/p/earbuds.jpg",
                    "itemId": "123456"
                }
            ]
        }
    };
    </script>
</body>
</html>"""

PRODUCT_DETAIL_HTML = """<!DOCTYPE html>
<html>
<head><title>Wireless Bluetooth Earbuds Stereo Sound - Daraz.pk</title></head>
<body>
    <div class="pdp-block">
        <h1 class="pdp-mod-product-badge-title">Wireless Bluetooth Earbuds Stereo Sound</h1>
        <a class="pdp-product-brand__brand-link">SoundPulse</a>
        <div class="pdp-sku-property-item" data-sku-id="SKU-123456">SKU-123456</div>
        
        <div class="pdp-price_type_normal">Rs. 3,499</div>
        <del class="pdp-price_type_deleted">Rs. 4,999</del>
        <span class="pdp-product-price__discount">-30%</span>
        
        <div class="score"><span class="score-average">4.8</span></div>
        <div class="pdp-review-summary__link"><span class="count">(48)</span></div>
        <div class="pdp-mod-product-badge-sub">120 sold</div>

        <div class="pdp-product-highlights">
            <p>Active Noise Cancellation</p>
            <p>30-hour battery life</p>
        </div>

        <div class="gallery-preview-panel">
            <img src="//img.daraz.pk/p/earbuds_front.jpg" class="pdp-mod-common-image" />
            <img src="//img.daraz.pk/p/earbuds_case.jpg" class="pdp-mod-common-image" />
        </div>

        <div class="breadcrumb_item">Electronics</div>
        <div class="breadcrumb_item">Audio</div>
        <div class="breadcrumb_item">Earphones</div>

        <div class="seller-name__detail-name">AudioTech Official</div>
        <div class="seller-name__detail"><a href="//www.daraz.pk/shop/audiotech-official">Shop</a></div>
        <div class="seller-info-title">Positive Seller Ratings</div>
        <div class="seller-info-value">94%</div>
        <div class="seller-info-title">Ship on Time</div>
        <div class="seller-info-value">99%</div>

        <button class="buy-now">Buy Now</button>

        <div class="mod-reviews">
            <div class="item">
                <div class="user-name">Kamran A.</div>
                <div class="date">12 Aug 2024</div>
                <div class="content">Excellent sound quality and fast delivery. Very satisfied!</div>
                <div class="star star-filled" style="color: rgb(255, 200, 60);">★</div>
                <div class="star star-filled" style="color: rgb(255, 200, 60);">★</div>
                <div class="star star-filled" style="color: rgb(255, 200, 60);">★</div>
                <div class="star star-filled" style="color: rgb(255, 200, 60);">★</div>
                <div class="star star-filled" style="color: rgb(255, 200, 60);">★</div>
            </div>
        </div>
    </div>
</body>
</html>"""


async def _async_test_direct_engine():
    engine = DarazSpecializedScraperEngine(headless=True)

    # Isolate external network boundary at Playwright browser context level
    # so test runs deterministically without external DNS or live network flakiness.
    orig_create_context = engine._create_context

    async def _mocked_create_context(p):
        ctx = await orig_create_context(p)

        async def _route_handler(route):
            request_url = route.request.url
            if "/catalog" in request_url:
                await route.fulfill(
                    status=200,
                    content_type="text/html; charset=utf-8",
                    body=CATALOG_SEARCH_HTML
                )
            elif "/products" in request_url:
                await route.fulfill(
                    status=200,
                    content_type="text/html; charset=utf-8",
                    body=PRODUCT_DETAIL_HTML
                )
            else:
                await route.fulfill(
                    status=200,
                    content_type="text/html; charset=utf-8",
                    body="<!DOCTYPE html><html><body></body></html>"
                )

        await ctx.route("**/*", _route_handler)
        return ctx

    engine._create_context = _mocked_create_context

    print("=== STEP 1: Search Test (wireless earbuds, max_products=3) ===")
    prods, is_chal, reason = await engine.crawl_keyword_search("wireless earbuds", max_pages=1, max_products=3)
    print(f"Search result count: {len(prods)}")
    print(f"Challenge status: is_challenged={is_chal}, reason='{reason}'")
    for i, p in enumerate(prods):
        print(f"  [{i+1}] Title: {p.get('title')}")
        print(f"      Price: {p.get('price')} | Orig: {p.get('original_price')} | Discount: {p.get('discount')}%")
        print(f"      URL: {p.get('product_url')}")
    
    assert len(prods) > 0, "No products discovered in search test!"

    target_url = prods[0].get("product_url")
    print(f"\n=== STEP 2: Detail Extraction Test on Discovered URL ===")
    print(f"Target URL: {target_url}")
    p_data, reviews, p_chal, p_reason = await engine.crawl_product_detail(target_url, max_review_pages=1)
    
    print(f"Detail product_data is not None? {p_data is not None}")
    if p_data:
        print(f"  Title: {p_data.get('title')}")
        print(f"  Product URL: {p_data.get('product_url') or target_url}")
        print(f"  Price: {p_data.get('price')} {p_data.get('currency')}")
        print(f"  Original Price: {p_data.get('original_price')}")
        print(f"  Discount: {p_data.get('discount')}%")
        print(f"  Brand: {p_data.get('brand')}")
        print(f"  Rating: {p_data.get('rating')}")
        print(f"  Seller: {p_data.get('seller_name')}")
        print(f"  Reviews Extracted: {len(reviews)} (Challenge on PDP: {p_chal})")
        if reviews:
            print(f"  Sample Review: {reviews[0]}")
    
    assert p_data is not None, "Product detail extraction returned None!"
    assert bool(p_data.get("title")), "Product title is missing!"
    assert p_data.get("title") == "Wireless Bluetooth Earbuds Stereo Sound"
    assert p_data.get("price") == 3499.0
    assert p_data.get("seller_name") == "AudioTech Official"
    assert len(reviews) > 0
    print("\n>>> Direct Engine Tests: PASSED SUCCESSFUL <<<\n")


def test_direct_engine():
    asyncio.run(_async_test_direct_engine())


if __name__ == "__main__":
    test_direct_engine()
