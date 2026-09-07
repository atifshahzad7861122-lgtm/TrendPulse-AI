"""Automated regression and hardening test suite for Module 7."""

from datetime import datetime, timezone
import pytest
from bs4 import BeautifulSoup

from app.crawling.models import MarketplaceType
from app.intelligence.extractors.images import ImageExtractor
from app.intelligence.models.product import ImageRecord, ProductIntelligence
from app.intelligence.models.result import ExtractionStatus, IntelligenceExtractionResult
from app.intelligence.models.review import IntelligenceReview
from app.intelligence.validation.completeness import (
    CompletenessLevel,
    ProductCompletenessReport,
    ProductCompletenessValidator,
)


# =========================================================================
# 1. Product Completeness Validator Tests
# =========================================================================

def test_completeness_validator_complete_product():
    p = ProductIntelligence(
        product_id="prod_complete_01",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://www.daraz.pk/products/item1.html",
        canonical_url="https://www.daraz.pk/products/item1.html",
        title="Gaming Mechanical Keyboard RGB Backlit",
        price=4500.0,
        currency="PKR",
        primary_image="https://img.daraz.pk/p/1.jpg",
        description_text="High quality mechanical switches with RGB lighting and wrist rest.",
        seller_name="TechStore Official",
        category_path="Computers & Laptops > Keyboards",
        rating=4.8,
        review_count=120,
    )
    report = ProductCompletenessValidator.evaluate(p)
    assert report.level == CompletenessLevel.COMPLETE
    assert report.is_usable is True
    assert report.completeness_score >= 0.8
    assert len(report.missing_critical_fields) == 0


def test_completeness_validator_partial_product():
    # Has title, url, price and image, but lacks seller and description
    p = ProductIntelligence(
        product_id="prod_partial_01",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://www.daraz.pk/products/item2.html",
        canonical_url="https://www.daraz.pk/products/item2.html",
        title="Simple USB Cable",
        price=150.0,
        currency="PKR",
        primary_image="https://img.daraz.pk/p/2.jpg",
    )
    report = ProductCompletenessValidator.evaluate(p)
    assert report.level == CompletenessLevel.PARTIAL
    assert report.is_usable is True
    assert "seller" in report.missing_optional_fields


def test_completeness_validator_invalid_product():
    # 1. Product is None
    report_none = ProductCompletenessValidator.evaluate(None)
    assert report_none.level == CompletenessLevel.INVALID
    assert report_none.is_usable is False
    assert "all" in report_none.missing_critical_fields

    # 2. Product has short/invalid title and missing currency
    p = ProductIntelligence(
        product_id="prod_invalid_01",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://daraz.pk/p/1.html",
        canonical_url="",
        title="AB", # Length < 3
        price=0.0,
        currency="",
    )
    report = ProductCompletenessValidator.evaluate(p)
    assert report.level == CompletenessLevel.INVALID
    assert report.is_usable is False
    assert "title" in report.missing_critical_fields


def test_completeness_validator_challenge_and_not_found():
    res_chal = IntelligenceExtractionResult(
        extraction_id="ext_c",
        product_id="P1",
        marketplace=MarketplaceType.AMAZON,
        url="https://amazon.com/dp/B001",
        status=ExtractionStatus.CHALLENGE,
        errors=["Robot Check CAPTCHA detected"],
    )
    rep_chal = ProductCompletenessValidator.evaluate(None, res_chal)
    assert rep_chal.level == CompletenessLevel.CHALLENGE
    assert rep_chal.is_usable is False

    res_404 = IntelligenceExtractionResult(
        extraction_id="ext_4",
        product_id="P2",
        marketplace=MarketplaceType.DARAZ,
        url="https://daraz.pk/products/deleted.html",
        status_code=404,
        status=ExtractionStatus.FAILED,
        errors=["Listing not found"],
    )
    rep_404 = ProductCompletenessValidator.evaluate(None, res_404)
    assert rep_404.level == CompletenessLevel.NOT_FOUND
    assert rep_404.is_usable is False


# =========================================================================
# 2. Image Extraction & Lazy Loading Tests
# =========================================================================

def test_image_extractor_lazy_attributes_and_json_list():
    html = """
    <div class="gallery">
        <img class="pdp-mod-common-image" data-origin-src="//img.lazcdn.com/static/pk/p/main_hi.jpg" src="//img.lazcdn.com/static/pk/p/placeholder.jpg" />
        <img class="gallery-image" data-lazy-src="https://img.lazcdn.com/static/pk/p/thumb2.jpg" />
        <img class="gallery-image" data-src="https://img.lazcdn.com/static/pk/p/thumb3.jpg" />
        <img class="gallery-image" src="data:image/png;base64,iVBORw0KGgo" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    prim, records = ImageExtractor.extract_gallery(soup)
    assert prim == "https://img.lazcdn.com/static/pk/p/main_hi.jpg"
    assert len(records) == 3
    assert records[0].is_primary is True
    assert records[1].url == "https://img.lazcdn.com/static/pk/p/thumb2.jpg"
    assert records[2].url == "https://img.lazcdn.com/static/pk/p/thumb3.jpg"

    # Test JSON list extraction
    urls = [
        "//img.lazcdn.com/p/1.jpg",
        "https://img.lazcdn.com/p/2.jpg",
        "https://img.lazcdn.com/p/1.jpg", # Duplicate
        "data:image/svg+xml;utf8,<svg></svg>", # Invalid data url
    ]
    p_url, j_records = ImageExtractor.extract_from_json_list(urls)
    assert p_url == "https://img.lazcdn.com/p/1.jpg"
    assert len(j_records) == 2
    assert j_records[0].position == 0
    assert j_records[1].position == 1


# =========================================================================
# 3. Review Fingerprint Deduplication Tests
# =========================================================================

def test_review_fingerprint_deterministic_and_unique():
    r1 = IntelligenceReview(
        product_id="prod_100",
        marketplace=MarketplaceType.DARAZ,
        rating=5.0,
        reviewer_name="Ali Khan",
        review_text="Excellent mouse, works great!",
    )
    r2 = IntelligenceReview(
        product_id="prod_100",
        marketplace=MarketplaceType.DARAZ,
        rating=5.0,
        reviewer_name="Ali Khan",
        review_text="Excellent mouse, works great!",
    )
    r3 = IntelligenceReview(
        product_id="prod_100",
        marketplace=MarketplaceType.DARAZ,
        rating=4.0, # Different rating
        reviewer_name="Ali Khan",
        review_text="Excellent mouse, works great!",
    )

    fp1 = r1.compute_fingerprint()
    fp2 = r2.compute_fingerprint()
    fp3 = r3.compute_fingerprint()

    assert fp1 == fp2
    assert fp1 != fp3
    assert len(fp1) == 64 # SHA-256


# =========================================================================
# 4. Realistic Malformed HTML Fault Tolerance Tests
# =========================================================================

def test_malformed_html_graceful_handling():
    # Incomplete tags, unclosed spans, broken attributes
    malformed_html = "<html><head><title>Test Item (Broken)</title></head><body><div class='price'>Rs. 1,200</span><p unclosed attr><img src='//img.com/a.jpg'></div>"
    soup = BeautifulSoup(malformed_html, "html.parser")
    prim, images = ImageExtractor.extract_gallery(soup)
    assert len(images) >= 1
    assert prim == "https://img.com/a.jpg"
