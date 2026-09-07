"""Tests for core data models and schema validation contracts."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.core.constants import CrawlStatus, CrawlType, SentimentType
from app.models import Category, CrawlRun, CrawlStats, Image, Product, Review, Seller


def test_product_model_valid():
    product = Product(
        product_id="PK-1001",
        title="Wireless Bluetooth Headphones",
        description="High fidelity audio with noise cancellation.",
        url="https://www.daraz.pk/products/wireless-headphones-i1001.html",
        price=3500.0,
        original_price=5000.0,
        discount=30.0,
        currency="PKR",
        rating=4.5,
        review_count=128,
        sold_count=450,
        brand="SoundCore",
        seller_id="SELLER-88",
        seller_name="Official Audio Store",
        category_id="CAT-AUDIO-1",
        category_name="Audio > Headphones",
        availability=True,
        images=[
            Image(url="https://img.daraz.pk/1.jpg", is_primary=True, position=0),
            Image(url="https://img.daraz.pk/2.jpg", is_primary=False, position=1),
        ],
        variants=[{"sku": "BLK-01", "color": "Black", "stock": 50}],
        specifications={"Bluetooth": "5.3", "Battery": "40h"},
        source="daraz",
    )

    assert product.product_id == "PK-1001"
    assert product.price == 3500.0
    assert len(product.images) == 2
    assert product.images[0].is_primary is True
    assert product.variants[0]["color"] == "Black"
    assert product.specifications["Bluetooth"] == "5.3"
    assert isinstance(product.first_seen_at, datetime)
    assert isinstance(product.last_seen_at, datetime)


def test_product_model_validation_errors():
    # Negative price should fail
    with pytest.raises(ValidationError):
        Product(
            product_id="P1",
            title="Item",
            url="https://example.com/p1",
            price=-10.0,
        )

    # Empty title should fail
    with pytest.raises(ValidationError):
        Product(
            product_id="P1",
            title="",
            url="https://example.com/p1",
            price=100.0,
        )


def test_review_model():
    review = Review(
        product_id="PK-1001",
        rating=5.0,
        text="Excellent build quality and bass!",
        sentiment=SentimentType.POSITIVE,
        sentiment_score=0.92,
        is_negative=False,
    )
    assert review.rating == 5.0
    assert review.sentiment == SentimentType.POSITIVE
    assert review.is_negative is False
    assert len(review.review_id) > 0

    # Rating > 5 should fail
    with pytest.raises(ValidationError):
        Review(product_id="PK-1001", rating=6.0)

    # Rating < 1 should fail
    with pytest.raises(ValidationError):
        Review(product_id="PK-1001", rating=0.5)


def test_category_model():
    cat = Category(
        category_id="CAT-AUDIO",
        parent_id="CAT-ELECTRONICS",
        name="Audio & Headphones",
        level=2,
        is_leaf=True,
    )
    assert cat.category_id == "CAT-AUDIO"
    assert cat.level == 2
    assert cat.is_leaf is True


def test_seller_model():
    seller = Seller(
        seller_id="S-123",
        seller_name="Tech Hub",
        rating=4.8,
        positive_seller_ratings=95.5,
        ship_on_time_rate=98.0,
        response_rate=90.0,
    )
    assert seller.seller_id == "S-123"
    assert seller.positive_seller_ratings == 95.5


def test_crawl_model_and_stats():
    crawl = CrawlRun(
        crawl_type=CrawlType.CATEGORY,
        status=CrawlStatus.RUNNING,
        items_discovered=100,
        items_processed=85,
        items_failed=2,
        error_count=2,
    )
    assert crawl.status == CrawlStatus.RUNNING
    assert crawl.items_processed == 85

    stats = CrawlStats(
        crawl_id=crawl.crawl_id,
        duration_seconds=120.0,
        items_per_minute=42.5,
        success_rate_percentage=97.7,
    )
    assert stats.items_per_minute == 42.5
    assert stats.success_rate_percentage == 97.7
