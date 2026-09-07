"""Unit tests for specialized domain extractors in the product extraction layer."""

from bs4 import BeautifulSoup
import pytest

from app.extraction.extractors import (
    CategoryExtractor,
    DescriptionExtractor,
    ImageExtractor,
    PriceExtractor,
    RatingExtractor,
    SalesExtractor,
    SellerExtractor,
    SpecificationExtractor,
    VariantExtractor,
)


def test_price_extractor_clean_number():
    ext = PriceExtractor()
    assert ext.clean_number("Rs. 45,999") == 45999.0
    assert ext.clean_number("PKR 1,250.50") == 1250.50
    assert ext.clean_number("-25%") == 25.0
    assert ext.clean_number("Free") is None


def test_price_extractor_dom():
    html = """
    <div class="pdp-product-price">
        <span class="pdp-price pdp-price_type_normal">Rs. 1,999</span>
        <span class="pdp-price_type_deleted">Rs. 2,999</span>
        <span class="pdp-product-price__discount">-33%</span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = PriceExtractor()
    price, orig_price, discount, currency = ext.extract(soup)

    assert price == 1999.0
    assert orig_price == 2999.0
    assert discount == 33.0
    assert currency == "PKR"


def test_image_extractor_dedup_and_lazy():
    html = """
    <div class="pdp-gallery">
        <img src="//img.daraz.pk/p/item1_80x80.jpg" data-origin-src="//img.daraz.pk/p/item1.jpg" />
        <img data-lazy-src="https://img.daraz.pk/p/item2.jpg" />
        <img src="https://img.daraz.pk/p/item1.jpg" /> <!-- Duplicate -->
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = ImageExtractor()
    images = ext.extract(soup, product_id="P100")

    assert len(images) == 2
    assert images[0].url == "https://img.daraz.pk/p/item1.jpg"
    assert images[0].is_primary is True
    assert images[1].url == "https://img.daraz.pk/p/item2.jpg"
    assert images[1].is_primary is False


def test_rating_extractor():
    html = """
    <div class="pdp-review-summary">
        <div class="score"><span class="score-average">4.6</span> / 5</div>
        <div class="count">1,520 Ratings</div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = RatingExtractor()
    rating, review_count = ext.extract(soup)

    assert rating == 4.6
    assert review_count == 1520


def test_sales_extractor_formats():
    ext = SalesExtractor()
    assert ext.parse_sold_string("1.2K sold") == 1200
    assert ext.parse_sold_string("500+ sold") == 500
    assert ext.parse_sold_string("1,000 sold") == 1000
    assert ext.parse_sold_string("2.5M sold") == 2500000
    assert ext.parse_sold_string("42 sold") == 42
    assert ext.parse_sold_string("No sales yet") is None


def test_seller_extractor():
    html = """
    <div class="seller-name">
        <a class="seller-name__detail-name" href="https://www.daraz.pk/shop/official-tech-pk">Tech Store</a>
    </div>
    <div class="seller-info-value rating-positive">97.5%</div>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = SellerExtractor()
    seller_id, seller_name, seller_rating = ext.extract(soup)

    assert seller_name == "Tech Store"
    assert seller_id == "official-tech-pk"
    assert seller_rating == 97.5


def test_category_extractor():
    html = """
    <ul class="breadcrumb">
        <li><a href="/">Home</a></li>
        <li><a href="/electronics/">Electronics</a></li>
        <li><a href="/audio-headphones/">Headphones</a></li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = CategoryExtractor()
    cat_id, cat_name = ext.extract(soup)

    assert cat_id == "audio-headphones"
    assert cat_name == "Electronics > Headphones"


def test_specification_extractor():
    html = """
    <ul class="pdp-general-features">
        <li><span class="key-title">Bluetooth:</span><span class="key-value">v5.3</span></li>
        <li><span class="key-title">Battery:</span><span class="key-value">30 Hours</span></li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = SpecificationExtractor()
    specs = ext.extract(soup)

    assert specs.get("Bluetooth") == "v5.3"
    assert specs.get("Battery") == "30 Hours"


def test_description_extractor():
    html = """
    <div class="pdp-product-desc">
        <p>Premium wireless noise canceling headphones.</p>
        <script>var x = 10;</script>
        <div class="ads">Banner ad</div>
        <p>Comfortable memory foam ear cushions.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = DescriptionExtractor()
    desc = ext.extract(soup)

    assert "Premium wireless" in desc
    assert "Memory foam" in desc or "memory foam" in desc
    assert "var x = 10" not in desc
    assert "Banner ad" not in desc
