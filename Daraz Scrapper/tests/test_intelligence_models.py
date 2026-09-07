"""Unit tests for product intelligence data contracts and models."""

from datetime import datetime, timezone
import pytest

from app.crawling.models import MarketplaceType
from app.intelligence.models import (
    ExtractionStatus,
    FieldConfidence,
    HistoricalSnapshot,
    ImageRecord,
    IntelligenceExtractionResult,
    IntelligenceReview,
    ProductIntelligence,
    Specification,
    Variant,
)


def test_product_intelligence_model_instantiation():
    product = ProductIntelligence(
        product_id="123456",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://www.daraz.pk/products/laptop-i123456.html",
        canonical_url="https://www.daraz.pk/products/laptop-i123456.html",
        title="Gaming Laptop Pro 16GB",
        price=150000.0,
        original_price=180000.0,
        currency="PKR",
        rating=4.8,
        review_count=120,
        sold_count=500,
        raw_sold_text="500+ sold",
        seller_id="seller_99",
        seller_name="Official Tech Store",
        primary_image="https://img.daraz.pk/laptop.jpg",
        images=[
            ImageRecord(url="https://img.daraz.pk/laptop.jpg", is_primary=True),
            ImageRecord(url="https://img.daraz.pk/laptop_side.jpg", position=1),
        ],
        variants=[
            Variant(sku_id="sku_1", name="16GB / 512GB", price=150000.0),
        ],
        specifications=[
            Specification(key="RAM", value="16GB"),
            Specification(key="Storage", value="512GB SSD"),
        ],
    )

    assert product.product_id == "123456"
    assert product.marketplace == MarketplaceType.DARAZ
    assert product.price == 150000.0
    assert product.sold_count == 500
    assert len(product.images) == 2
    assert len(product.variants) == 1
    assert len(product.specifications) == 2


def test_intelligence_review_model():
    review = IntelligenceReview(
        product_id="B08N5WRWNW",
        marketplace=MarketplaceType.AMAZON,
        rating=5.0,
        review_title="Excellent headphones",
        review_text="Battery life is superb.",
        reviewer_name="Jane Doe",
        raw_date_str="Reviewed in the US on August 15, 2026",
    )

    assert review.product_id == "B08N5WRWNW"
    assert review.rating == 5.0
    assert review.verified_purchase is True
    assert review.is_negative is False


def test_historical_snapshot_model():
    snap = HistoricalSnapshot(
        product_id="B08N5WRWNW",
        marketplace=MarketplaceType.AMAZON,
        title="Noise Cancelling Headphones",
        price=299.99,
        rating=4.7,
        review_count=14500,
        sold_count=5000,
        raw_sold_text="5K+ bought in past month",
        availability=True,
        seller_name="Amazon.com",
        source_url="https://www.amazon.com/dp/B08N5WRWNW",
    )

    assert snap.product_id == "B08N5WRWNW"
    assert snap.price == 299.99
    assert snap.sold_count == 5000
    assert snap.observed_at is not None
