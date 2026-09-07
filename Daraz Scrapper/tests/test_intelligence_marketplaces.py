"""Unit tests for all 5 marketplace intelligence extractors."""

import pytest

from app.crawling.models import CrawlResponse, MarketplaceType
from app.intelligence.marketplaces import (
    AliExpressIntelligenceExtractor,
    AmazonIntelligenceExtractor,
    DarazIntelligenceExtractor,
    EbayIntelligenceExtractor,
    ShopifyIntelligenceExtractor,
)
from app.intelligence.models import ExtractionStatus


def test_daraz_intelligence_extractor():
    extractor = DarazIntelligenceExtractor()
    url = "https://www.daraz.pk/products/laptop-stand-i100200-s300400.html"
    assert extractor.validate_url(url) is True

    html = """
    <html>
        <head><title>Foldable Laptop Stand</title></head>
        <body>
            <h1 class="pdp-mod-product-badge-title">Ergonomic Foldable Laptop Stand Aluminum</h1>
            <span class="pdp-price">Rs. 2,499</span>
            <span class="pdp-price_type_deleted">Rs. 3,500</span>
            <div class="score"><span class="score-average">4.7</span></div>
            <span class="count">850 Ratings</span>
            <span class="sold-count">1.5K sold</span>
            <div class="seller-name__detail"><a href="/shop/ergotech-official">ErgoTech Official</a></div>
            <img class="pdp-mod-common-image" src="https://img.daraz.pk/stand_main.jpg" />
            <div class="pdp-product-desc"><p>Heavy duty aluminum alloy stand.</p></div>
        </body>
    </html>
    """
    resp = CrawlResponse(url=url, status_code=200, html=html)
    res = extractor.extract_intelligence(resp)

    assert res.success is True
    assert res.status == ExtractionStatus.SUCCESS
    assert res.product.title == "Ergonomic Foldable Laptop Stand Aluminum"
    assert res.product.price == 2499.0
    assert res.product.original_price == 3500.0
    assert res.product.rating == 4.7
    assert res.product.review_count == 850
    assert res.product.sold_count == 1500
    assert res.product.seller_name == "ErgoTech Official"
    assert res.product.primary_image == "https://img.daraz.pk/stand_main.jpg"


def test_amazon_intelligence_extractor():
    extractor = AmazonIntelligenceExtractor()
    url = "https://www.amazon.com/dp/B08N5WRWNW"
    assert extractor.validate_url(url) is True
    assert extractor.extract_product_id(url) == "B08N5WRWNW"

    html = """
    <html>
        <body>
            <span id="productTitle">Sony WH-1000XM4 Wireless Premium Noise Canceling Headphones</span>
            <span class="a-price"><span class="a-offscreen">$278.00</span></span>
            <span class="a-text-price"><span class="a-offscreen">$348.00</span></span>
            <span id="acrPopover"><span class="a-icon-alt">4.7 out of 5 stars</span></span>
            <span id="acrCustomerReviewText">52,430 ratings</span>
            <span id="social-proofing-faceout-title-tk_bought">5K+ bought in past month</span>
            <a id="bylineInfo">Sony</a>
            <img id="landingImage" src="https://m.media-amazon.com/images/I/71o8Q5XJS5L.jpg" />
            <div id="feature-bullets">
                <ul>
                    <li><span class="a-list-item">Industry-leading noise canceling</span></li>
                </ul>
            </div>
        </body>
    </html>
    """
    resp = CrawlResponse(url=url, status_code=200, html=html)
    res = extractor.extract_intelligence(resp)

    assert res.success is True
    assert res.product.product_id == "B08N5WRWNW"
    assert "Sony WH-1000XM4" in res.product.title
    assert res.product.price == 278.0
    assert res.product.original_price == 348.0
    assert res.product.rating == 4.7
    assert res.product.review_count == 52430
    assert res.product.sold_count == 5000
    assert res.product.brand == "Sony"


def test_ebay_intelligence_extractor():
    extractor = EbayIntelligenceExtractor()
    url = "https://www.ebay.com/itm/123456789012"
    assert extractor.validate_url(url) is True
    assert extractor.extract_product_id(url) == "123456789012"

    html = """
    <html>
        <body>
            <h1 class="x-item-title"><span class="ux-textspans">Apple iPhone 13 128GB Unlocked Good Condition</span></h1>
            <div class="x-price-primary"><span class="ux-textspans">US $429.99</span></div>
            <div class="x-quantity__availability"><span class="ux-textspans--BOLD">1,420 sold</span></div>
            <div class="x-sellercard-atf__info__about-seller"><a href="https://www.ebay.com/usr/techdealz">techdealz</a></div>
            <img class="pdp-mod-common-image" src="https://i.ebayimg.com/images/g/iphone13.jpg" />
        </body>
    </html>
    """
    resp = CrawlResponse(url=url, status_code=200, html=html)
    res = extractor.extract_intelligence(resp)

    assert res.success is True
    assert res.product.product_id == "123456789012"
    assert res.product.price == 429.99
    assert res.product.sold_count == 1420
    assert res.product.seller_name == "techdealz"


def test_aliexpress_intelligence_extractor():
    extractor = AliExpressIntelligenceExtractor()
    url = "https://www.aliexpress.com/item/1005005566778899.html"
    assert extractor.validate_url(url) is True
    assert extractor.extract_product_id(url) == "1005005566778899"

    html = """
    <html>
        <body>
            <h1 class="product-title-text">Smart Fitness Tracker Watch IP68 Waterproof</h1>
            <span class="product-price-current">US $18.50</span>
            <span class="overview-rating-average">4.8</span>
            <span class="reviewer-info-reviews">620 reviews</span>
            <span class="reviewer-info-sold">3,000+ sold</span>
            <img class="pdp-mod-common-image" src="https://ae01.alicdn.com/kf/watch.jpg" />
        </body>
    </html>
    """
    resp = CrawlResponse(url=url, status_code=200, html=html)
    res = extractor.extract_intelligence(resp)

    assert res.success is True
    assert res.product.product_id == "1005005566778899"
    assert res.product.price == 18.50
    assert res.product.rating == 4.8
    assert res.product.review_count == 620
    assert res.product.sold_count == 3000


def test_shopify_intelligence_extractor():
    extractor = ShopifyIntelligenceExtractor()
    url = "https://shop.gymshark.com/products/seamless-t-shirt"
    assert extractor.validate_url(url) is True

    json_payload = """
    {
        "product": {
            "id": 99887766,
            "title": "Vital Seamless 2.0 T-Shirt",
            "vendor": "Gymshark",
            "body_html": "<p>Form-fitting breathable workout top.</p>",
            "variants": [
                {"id": 1, "title": "Black / S", "price": "40.00", "available": true},
                {"id": 2, "title": "Black / M", "price": "40.00", "available": true}
            ],
            "images": [
                {"src": "https://cdn.shopify.com/s/files/shirt_black.jpg"}
            ]
        }
    }
    """
    resp = CrawlResponse(url=url, status_code=200, html=json_payload)
    res = extractor.extract_intelligence(resp)

    assert res.success is True
    assert res.product.product_id == "99887766"
    assert res.product.title == "Vital Seamless 2.0 T-Shirt"
    assert res.product.price == 40.0
    assert res.product.seller_name == "Gymshark"
    assert len(res.product.variants) == 2
