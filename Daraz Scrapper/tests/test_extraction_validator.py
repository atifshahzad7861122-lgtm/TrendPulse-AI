"""Unit tests for ProductExtractionValidator and quality gate classifications."""

from datetime import datetime, timezone
import pytest

from app.extraction.validator import ProductExtractionValidator, ValidationStatus
from app.models.image import Image
from app.models.product import Product


def test_validator_valid_product():
    product = Product(
        product_id="12345",
        title="Wireless Ergonomic Mouse",
        url="https://www.daraz.pk/products/mouse-i12345.html",
        price=1500.0,
        original_price=2000.0,
        discount=25.0,
        rating=4.5,
        review_count=50,
        sold_count=200,
        seller_name="Logitech Official Store",
        category_name="Computer Accessories > Mice",
        images=[Image(product_id="12345", url="https://img.daraz.pk/p/mouse.jpg", is_primary=True)],
    )

    report = ProductExtractionValidator.validate_product(product, overall_confidence=0.95)
    assert report.is_valid is True
    assert report.status == ValidationStatus.VALID
    assert len(report.errors) == 0
    assert "product_id" in report.passed_checks
    assert "title" in report.passed_checks
    assert "price" in report.passed_checks


def test_validator_warning_on_missing_optional_fields():
    product = Product(
        product_id="12345",
        title="Basic Mouse",
        url="https://www.daraz.pk/products/mouse-i12345.html",
        price=500.0,
        images=[],
    )

    report = ProductExtractionValidator.validate_product(product, overall_confidence=0.80)
    assert report.is_valid is True
    assert report.status == ValidationStatus.WARNING
    assert any("images" in w for w in report.warnings)


def test_validator_needs_review_on_low_confidence():
    product = Product(
        product_id="12345",
        title="Basic Mouse",
        url="https://www.daraz.pk/products/mouse-i12345.html",
        price=500.0,
        seller_name="Generic Seller",
        images=[Image(product_id="12345", url="https://img.daraz.pk/p/mouse.jpg", is_primary=True)],
    )

    report = ProductExtractionValidator.validate_product(
        product, overall_confidence=0.45, min_confidence_threshold=0.60
    )
    assert report.is_valid is True
    assert report.status == ValidationStatus.NEEDS_REVIEW


def test_validator_rejected_on_missing_required_fields():
    # Empty title or None product
    report = ProductExtractionValidator.validate_product(None)
    assert report.is_valid is False
    assert report.status == ValidationStatus.REJECTED
    assert "Product object is None" in report.errors

    # Invalid title
    product = Product(
        product_id="12345",
        title="A",  # Too short
        url="https://www.daraz.pk/products/mouse-i12345.html",
        price=500.0,
    )
    report = ProductExtractionValidator.validate_product(product, overall_confidence=0.9)
    assert report.is_valid is False
    assert report.status == ValidationStatus.REJECTED
