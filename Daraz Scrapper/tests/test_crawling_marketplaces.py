"""Unit tests for marketplace adapters: Daraz, Amazon, eBay, AliExpress, Shopify."""

import pytest
from app.crawling.marketplaces import (
    AliExpressAdapter,
    AmazonAdapter,
    DarazAdapter,
    EbayAdapter,
    ShopifyAdapter,
)
from app.crawling.models import CrawlContentType, CrawlResponse, MarketplaceType


def test_amazon_adapter_url_and_parsing():
    adapter = AmazonAdapter()
    url = "https://www.amazon.com/Apple-iPhone-15-128GB-Black/dp/B0CHX1W1XY?ref_=ast_sto_dp"
    
    assert adapter.validate_url(url) is True
    assert adapter.detect_content_type(url) == CrawlContentType.PRODUCT
    assert adapter.extract_product_id(url) == "B0CHX1W1XY"

    html = """
    <html>
    <body>
        <h1 id="productTitle">Apple iPhone 15, 128GB, Black</h1>
        <span class="a-price"><span class="a-offscreen">$799.99</span></span>
        <div id="landingImage" src="https://m.media-amazon.com/images/I/71d7rfSl0wL.jpg"></div>
        <span data-hook="rating-out-of-text">4.6 out of 5</span>
        <span id="acrCustomerReviewText">1,250 ratings</span>
    </body>
    </html>
    """
    resp = CrawlResponse(url=url, status_code=200, html=html)
    result = adapter.parse_response(resp, CrawlContentType.PRODUCT)

    assert result.success is True
    assert result.product is not None
    assert result.product.product_id == "B0CHX1W1XY"
    assert result.product.title == "Apple iPhone 15, 128GB, Black"
    assert result.product.price == 799.99
    assert result.product.currency == "USD"
    assert result.product.rating == 4.6
    assert result.product.review_count == 1250


def test_ebay_adapter_url_and_parsing():
    adapter = EbayAdapter()
    url = "https://www.ebay.com/itm/123456789012?hash=item1c"
    
    assert adapter.validate_url(url) is True
    assert adapter.detect_content_type(url) == CrawlContentType.PRODUCT
    assert adapter.extract_product_id(url) == "123456789012"

    html = """
    <html>
    <body>
        <h1 class="x-item-title__mainTitle">Sony WH-1000XM5 Wireless Headphones</h1>
        <div class="x-price-primary"><span>US $348.00</span></div>
        <div class="x-sellercard-atf__info__about-seller"><a href="#">AudioProStore</a></div>
    </body>
    </html>
    """
    resp = CrawlResponse(url=url, status_code=200, html=html)
    result = adapter.parse_response(resp, CrawlContentType.PRODUCT)

    assert result.success is True
    assert result.product.product_id == "123456789012"
    assert result.product.title == "Sony WH-1000XM5 Wireless Headphones"
    assert result.product.price == 348.0
    assert result.product.seller_name == "AudioProStore"


def test_shopify_adapter_json_and_html():
    adapter = ShopifyAdapter()
    url = "https://store.myshopify.com/products/leather-jacket"
    
    assert adapter.validate_url(url) is True
    assert adapter.detect_content_type(url) == CrawlContentType.PRODUCT
    assert adapter.extract_product_id(url) == "leather-jacket"

    # JSON endpoint response
    json_payload = """
    {
        "product": {
            "id": 888999,
            "title": "Vintage Leather Jacket",
            "vendor": "Urban Outfitters",
            "body_html": "<p>Premium leather jacket.</p>",
            "variants": [
                {"id": 101, "title": "Medium", "price": "199.50", "available": true}
            ],
            "images": [
                {"src": "https://cdn.shopify.com/s/files/jacket.jpg"}
            ]
        }
    }
    """
    resp = CrawlResponse(url=url, status_code=200, html=json_payload)
    result = adapter.parse_response(resp, CrawlContentType.PRODUCT)

    assert result.success is True
    assert result.product.title == "Vintage Leather Jacket"
    assert result.product.price == 199.50
    assert len(result.product.variants) == 1
    assert result.product.variants[0]["sku_id"] == "101"
