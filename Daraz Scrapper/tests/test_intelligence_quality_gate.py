"""Unit tests for DataQualityGate and ConfidenceScorer."""

import pytest

from app.crawling.models import MarketplaceType
from app.intelligence.models import (
    FieldConfidence,
    ImageRecord,
    ProductIntelligence,
)
from app.intelligence.validation import ConfidenceScorer, DataQualityGate


def test_quality_gate_valid_product():
    prod = ProductIntelligence(
        product_id="P1001",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://www.daraz.pk/p1001.html",
        canonical_url="https://www.daraz.pk/p1001.html",
        title="Wireless Bluetooth Earbuds",
        price=3500.0,
        rating=4.5,
        review_count=100,
        sold_count=500,
        seller_id="seller_42",
        seller_name="Audio Store",
        images=[ImageRecord(url="https://img.daraz.pk/1.jpg", is_primary=True)],
    )

    is_valid, errors, warnings = DataQualityGate.validate(prod)
    assert is_valid is True
    assert len(errors) == 0


def test_quality_gate_rejects_seller_id_matching_product_id():
    prod = ProductIntelligence(
        product_id="P1001",
        marketplace=MarketplaceType.DARAZ,
        source_url="https://www.daraz.pk/p1001.html",
        canonical_url="https://www.daraz.pk/p1001.html",
        title="Wireless Earbuds",
        price=3500.0,
        seller_id="P1001",  # Invalid: equals product_id
    )

    is_valid, errors, warnings = DataQualityGate.validate(prod)
    assert is_valid is False
    assert any("must not equal product_id" in e for e in errors)


def test_quality_gate_rejects_negative_price_and_invalid_rating():
    with pytest.raises(Exception):
        ProductIntelligence(
            product_id="P1001",
            marketplace=MarketplaceType.AMAZON,
            source_url="https://www.amazon.com/dp/B001",
            canonical_url="https://www.amazon.com/dp/B001",
            title="Test Item",
            price=-10.0,  # Negative
            rating=6.5,   # Outside [0, 5]
        )

    # Test short title validation in DataQualityGate
    prod = ProductIntelligence(
        product_id="P1001",
        marketplace=MarketplaceType.AMAZON,
        source_url="https://www.amazon.com/dp/B001",
        canonical_url="https://www.amazon.com/dp/B001",
        title="A",  # Too short
        price=10.0,
    )
    is_valid, errors, warnings = DataQualityGate.validate(prod)
    assert is_valid is False
    assert any("suspiciously short" in e for e in errors)


def test_confidence_scorer_levels():
    prod = ProductIntelligence(
        product_id="P1001",
        marketplace=MarketplaceType.AMAZON,
        source_url="https://www.amazon.com/dp/B001",
        canonical_url="https://www.amazon.com/dp/B001",
        title="Sony Wireless Headphones Noise Cancelling",
        price=299.99,
        rating=4.8,
        review_count=1000,
        sold_count=5000,
        seller_name="Sony Store",
        description_text="Long description text over 50 characters for high confidence calculation.",
        images=[
            ImageRecord(url="https://img.com/1.jpg", is_primary=True),
            ImageRecord(url="https://img.com/2.jpg", position=1),
        ],
    )

    scores, levels, overall = ConfidenceScorer.score(prod)
    assert levels["title"] == FieldConfidence.HIGH
    assert levels["price"] == FieldConfidence.HIGH
    assert levels["sold_count"] == FieldConfidence.HIGH
    assert overall >= 0.85
