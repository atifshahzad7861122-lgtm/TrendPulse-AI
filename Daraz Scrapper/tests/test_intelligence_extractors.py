"""Unit tests for specialized intelligence extractors."""

from bs4 import BeautifulSoup
import pytest

from app.intelligence.extractors import (
    CategoryExtractor,
    DescriptionExtractor,
    ImageExtractor,
    RatingReviewExtractor,
    SalesExtractor,
    SellerExtractor,
    SpecificationExtractor,
    VariantExtractor,
)


def test_sales_extractor_patterns():
    # 1. 1.2K sold
    count, raw = SalesExtractor.extract_sales("1.2K sold")
    assert count == 1200
    assert "1.2K sold" in raw

    # 2. 500+ sold
    count, raw = SalesExtractor.extract_sales("500+ sold")
    assert count == 500

    # 3. 1,000 sold
    count, raw = SalesExtractor.extract_sales("1,000 sold")
    assert count == 1000

    # 4. 10K+ sold
    count, raw = SalesExtractor.extract_sales("10K+ sold")
    assert count == 10000

    # 5. 123 purchased / 123 sold
    count, raw = SalesExtractor.extract_sales("123 sold")
    assert count == 123

    # 6. Over 50 bought in past month
    count, raw = SalesExtractor.extract_sales("Over 50 bought in past month")
    assert count == 50

    # 7. Invalid/empty
    count, raw = SalesExtractor.extract_sales(None)
    assert count is None
    assert raw is None


def test_rating_and_review_extractor():
    assert RatingReviewExtractor.extract_rating("4.7 out of 5 stars") == 4.7
    assert RatingReviewExtractor.extract_rating("4.5 / 5") == 4.5
    assert RatingReviewExtractor.extract_rating("3.9") == 3.9
    assert RatingReviewExtractor.extract_rating("6.0") is None  # invalid > 5

    assert RatingReviewExtractor.extract_count("1.2K reviews") == 1200
    assert RatingReviewExtractor.extract_count("500+ ratings") == 500
    assert RatingReviewExtractor.extract_count("1,234") == 1234


def test_image_extractor_dedup_and_lazy():
    html = """
    <div class="gallery">
        <img class="pdp-mod-common-image" src="https://example.com/thumb.jpg" data-zoom-image="https://example.com/highres.jpg" alt="Hero"/>
        <div class="item-gallery">
            <img src="https://example.com/highres.jpg" />
            <img data-src="https://example.com/pic2.jpg" />
            <img src="//example.com/pic3.jpg" />
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    primary_url, images = ImageExtractor.extract_gallery(soup)

    assert primary_url == "https://example.com/highres.jpg"
    assert len(images) == 3  # Deduped highres.jpg
    assert images[0].is_primary is True
    assert images[2].url == "https://example.com/pic3.jpg"


def test_description_extractor_sanitization():
    unsafe_html = """
    <div class="product-desc">
        <script>alert('xss')</script>
        <p>Premium <b>Noise Cancelling</b> headphones.</p>
        <iframe src="http://tracker.com"></iframe>
        <span onclick="doSomething()">Click me</span>
    </div>
    """
    clean_html, clean_text = DescriptionExtractor.sanitize_html(unsafe_html)

    assert "<script>" not in clean_html
    assert "<iframe>" not in clean_html
    assert "onclick" not in clean_html
    assert "<b>Noise Cancelling</b>" in clean_html
    assert "Premium Noise Cancelling headphones." in clean_text


def test_seller_extractor_integrity():
    # Valid seller
    s_id = SellerExtractor.clean_seller_id("Official Store", product_id="12345")
    assert s_id == "Official Store"

    # Reject when seller_id equals product_id
    assert SellerExtractor.clean_seller_id("12345", product_id="12345") is None

    # Reject when seller_id contains itemId leak
    assert SellerExtractor.clean_seller_id("itemId=998877&vendor=xyz", product_id="12345") is None
