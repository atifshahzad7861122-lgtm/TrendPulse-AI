"""Regression test suite for Module 5 Scraper Hardening."""

import json
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

from app.crawling.challenge import UniversalChallengeDetector
from app.crawling.models import CrawlResponse, MarketplaceType
from app.intelligence.marketplaces.aliexpress import AliExpressIntelligenceExtractor
from app.intelligence.marketplaces.amazon import AmazonIntelligenceExtractor
from app.intelligence.marketplaces.daraz import DarazIntelligenceExtractor
from app.intelligence.marketplaces.ebay import EbayIntelligenceExtractor
from app.intelligence.marketplaces.shopify import ShopifyIntelligenceExtractor
from app.intelligence.models.product import ProductIntelligence
from app.intelligence.models.result import ExtractionStatus
from app.intelligence.models.review import IntelligenceReview
from app.storage.export import DataExporter


# ==========================================
# 1. Challenge & Anti-Bot Detection Tests
# ==========================================

def test_amazon_robot_check_detection():
    detector = UniversalChallengeDetector()
    robot_html = """
    <html>
        <head><title>Robot Check</title></head>
        <body>
            <p>Sorry, we just need to make sure you're not a robot.</p>
            <form action="/errors/validateCaptcha"></form>
        </body>
    </html>
    """
    res = detector.detect(200, robot_html, "https://www.amazon.com/dp/B08N5WRWNW")
    assert res.is_challenge is True
    assert res.is_blocked is True
    assert "Robot Check" in res.reason or "Amazon" in res.waf_provider


def test_ebay_akamai_403_detection():
    detector = UniversalChallengeDetector()
    akamai_html = """
    <html>
        <head><title>Access Denied</title></head>
        <body>
            <h1>Pardon Our Interruption</h1>
            <p>Reference #18.12345678.1690000000.abc1234</p>
        </body>
    </html>
    """
    res = detector.detect(403, akamai_html, "https://www.ebay.com/itm/1234567890")
    assert res.is_challenge is True
    assert res.is_blocked is True


def test_amazon_extractor_flags_challenge():
    extractor = AmazonIntelligenceExtractor()
    resp = CrawlResponse(
        url="https://www.amazon.com/dp/B08N5WRWNW",
        status_code=200,
        html="<html><head><title>Robot Check</title></head><body><form action='/errors/validateCaptcha'></form></body></html>",
    )
    result = extractor.extract_intelligence(resp)
    assert result.status == ExtractionStatus.CHALLENGE
    assert result.success is False


def test_ebay_extractor_flags_challenge():
    extractor = EbayIntelligenceExtractor()
    resp = CrawlResponse(
        url="https://www.ebay.com/itm/1234567890",
        status_code=403,
        html="<html><body><h1>Pardon Our Interruption</h1></body></html>",
    )
    result = extractor.extract_intelligence(resp)
    assert result.status == ExtractionStatus.CHALLENGE
    assert result.success is False


# ==========================================
# 2. AliExpress Price & Stub Rejection Tests
# ==========================================

def test_aliexpress_runparams_price_extraction():
    extractor = AliExpressIntelligenceExtractor()
    run_params_payload = {
        "data": {
            "productInfoComponent": {
                "subject": "Wireless RGB Gaming Mouse 16000 DPI"
            },
            "priceComponent": {
                "origPrice": {"minAmount": {"value": 29.99}},
                "discountPrice": {"minAmount": {"value": 14.99}}
            },
            "feedbackComponent": {
                "evarageStar": "4.8",
                "totalValidNum": 350
            },
            "tradeComponent": {
                "formatTradeCount": "1,200+ sold"
            }
        }
    }
    html = f"""
    <html>
        <head><title>Wireless Gaming Mouse</title></head>
        <body>
            <script>window.runParams = {json.dumps(run_params_payload)};</script>
        </body>
    </html>
    """
    resp = CrawlResponse(
        url="https://www.aliexpress.com/item/100500111222333.html",
        status_code=200,
        html=html,
    )
    result = extractor.extract_intelligence(resp)
    assert result.success is True
    assert result.product is not None
    assert result.product.title == "Wireless RGB Gaming Mouse 16000 DPI"
    assert result.product.price == 14.99
    assert result.product.original_price == 29.99
    assert result.product.rating == 4.8
    assert result.product.review_count == 350
    assert result.product.sold_count == 1200


def test_aliexpress_empty_stub_rejection():
    extractor = AliExpressIntelligenceExtractor()
    html = """
    <html>
        <head><title>Aliexpress</title></head>
        <body>
            <div id="root"></div>
        </body>
    </html>
    """
    resp = CrawlResponse(
        url="https://www.aliexpress.com/item/999999999.html",
        status_code=200,
        html=html,
    )
    result = extractor.extract_intelligence(resp)
    assert result.success is False
    assert result.status == ExtractionStatus.FAILED


# ==========================================
# 3. Daraz Multi-Tier Fallback Tests
# ==========================================

def test_daraz_jsonld_fallback():
    extractor = DarazIntelligenceExtractor()
    jsonld_payload = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "M10 TWS Wireless Earbuds Bluetooth 5.1",
        "image": "https://pk-live.slatic.net/kf/S12345.jpg",
        "description": "High quality TWS Bluetooth earphones with LED display",
        "offers": {
            "@type": "Offer",
            "price": "950",
            "priceCurrency": "PKR"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.6",
            "reviewCount": "120"
        }
    }
    html = f"""
    <html>
        <head>
            <script type="application/ld+json">{json.dumps(jsonld_payload)}</script>
        </head>
        <body>
            <h1 class="pdp-mod-product-badge-title">M10 TWS Wireless Earbuds Bluetooth 5.1</h1>
        </body>
    </html>
    """
    resp = CrawlResponse(
        url="https://www.daraz.pk/products/m10-earbuds-i12345-s67890.html",
        status_code=200,
        html=html,
    )
    result = extractor.extract_intelligence(resp)
    assert result.success is True
    assert result.product is not None
    assert result.product.title == "M10 TWS Wireless Earbuds Bluetooth 5.1"
    assert result.product.price == 950.0
    assert result.product.currency == "PKR"
    assert result.product.rating == 4.6
    assert result.product.review_count == 120


# ==========================================
# 4. Shopify Multi-Source Generic Tests
# ==========================================

def test_shopify_json_endpoint_extraction():
    extractor = ShopifyIntelligenceExtractor()
    shopify_json = {
        "product": {
            "id": 1234567890,
            "title": "Classic Wool Runners",
            "vendor": "Allbirds",
            "body_html": "<p>Super soft merino wool running shoes</p>",
            "variants": [
                {"id": 987654321, "title": "Size 10", "price": "110.00", "compare_at_price": "130.00", "available": True}
            ],
            "images": [
                {"src": "https://cdn.shopify.com/s/files/1/001/wool_runner.jpg"}
            ]
        }
    }
    resp = CrawlResponse(
        url="https://www.allbirds.com/products/mens-wool-runners.json",
        status_code=200,
        html=json.dumps(shopify_json),
    )
    result = extractor.extract_intelligence(resp)
    assert result.success is True
    assert result.product is not None
    assert result.product.title == "Classic Wool Runners"
    assert result.product.price == 110.0
    assert result.product.original_price == 130.0
    assert result.product.seller_name == "Allbirds"
    assert len(result.product.images) == 1


# ==========================================
# 5. Data Export Tests (JSON, JSONL, CSV)
# ==========================================

def test_data_exporter_all_formats(tmp_path: Path):
    products = [
        ProductIntelligence(
            product_id="P001",
            marketplace=MarketplaceType.DARAZ,
            source_url="https://www.daraz.pk/products/p1.html",
            canonical_url="https://www.daraz.pk/products/p1.html",
            title="Wireless Mouse",
            price=1500.0,
            currency="PKR",
            rating=4.5,
            review_count=50,
        ),
        ProductIntelligence(
            product_id="P002",
            marketplace=MarketplaceType.AMAZON,
            source_url="https://www.amazon.com/dp/B000000000",
            canonical_url="https://www.amazon.com/dp/B000000000",
            title="USB-C Hub",
            price=29.99,
            currency="USD",
            rating=4.8,
            review_count=1200,
        )
    ]

    # JSON export
    json_path = tmp_path / "products.json"
    out_json = DataExporter.export_products(products, json_path, "json")
    assert out_json.exists()
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 2
    assert loaded[0]["product_id"] == "P001"

    # JSONL export
    jsonl_path = tmp_path / "products.jsonl"
    out_jsonl = DataExporter.export_products(products, jsonl_path, "jsonl")
    assert out_jsonl.exists()
    lines = out_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    # CSV export
    csv_path = tmp_path / "products.csv"
    out_csv = DataExporter.export_products(products, csv_path, "csv")
    assert out_csv.exists()
    csv_text = out_csv.read_text(encoding="utf-8")
    assert "product_id" in csv_text
    assert "Wireless Mouse" in csv_text
    assert "USB-C Hub" in csv_text
