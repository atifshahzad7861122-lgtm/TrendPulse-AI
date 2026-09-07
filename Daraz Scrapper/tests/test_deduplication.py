"""Tests for ProductDeduplicator, ReviewDeduplicator, URL canonicalization, and title sanitization."""

from app.core.deduplication import (
    ProductDeduplicator,
    ReviewDeduplicator,
    canonicalize_url,
    normalize_product_title,
)


def test_canonicalize_url_strips_tracking_parameters():
    raw_url = "https://www.daraz.pk/products/item-i12345.html?spm=a2a0e.home.flashSale.1&scm=1007.123&click=true&valid_param=keep"
    clean = canonicalize_url(raw_url, keep_params={"valid_param"})
    assert "spm" not in clean
    assert "scm" not in clean
    assert "click" not in clean
    assert "valid_param=keep" in clean
    assert clean.startswith("https://www.daraz.pk/products/item-i12345.html")


def test_normalize_product_title():
    raw = "  Apple\u00a0\u00a0iPhone   15 Pro   Max  - 256GB   "
    clean = normalize_product_title(raw, max_length=30)
    assert clean == "Apple iPhone 15 Pro Max - 256G"


def test_product_deduplicator():
    dedup = ProductDeduplicator()

    assert dedup.is_duplicate(product_id="P1", url="https://daraz.pk/p1?spm=1") is False
    assert dedup.duplicates_prevented == 0

    # Same ID -> duplicate
    assert dedup.is_duplicate(product_id="P1", url="https://daraz.pk/p1-diff") is True
    assert dedup.duplicates_prevented == 1

    # Same canonical URL -> duplicate
    assert dedup.is_duplicate(product_id="P2", url="https://daraz.pk/p1?spm=999") is True
    assert dedup.duplicates_prevented == 2

    # New item -> unique
    assert dedup.is_duplicate(product_id="P3", url="https://daraz.pk/p3") is False
    assert dedup.duplicates_prevented == 2


def test_review_deduplicator_with_fingerprinting():
    dedup = ReviewDeduplicator()

    # Distinct reviews
    assert dedup.is_duplicate(
        product_id="P100",
        reviewer="Ali",
        rating=5.0,
        date_str="2026-01-01",
        text="Excellent quality product!",
    ) is False
    assert dedup.duplicates_prevented == 0

    # Duplicate review content
    assert dedup.is_duplicate(
        product_id="P100",
        reviewer="ali",
        rating=5.0,
        date_str="2026-01-01",
        text="Excellent quality product!",
    ) is True
    assert dedup.duplicates_prevented == 1

    # Different product or rating is not duplicate
    assert dedup.is_duplicate(
        product_id="P101",
        reviewer="Ali",
        rating=5.0,
        date_str="2026-01-01",
        text="Excellent quality product!",
    ) is False
    assert dedup.duplicates_prevented == 1
