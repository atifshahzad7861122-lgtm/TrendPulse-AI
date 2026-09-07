"""Tests for URL normalization and Product ID extraction."""

from app.discovery.normalizer import (
    extract_category_id_from_url,
    extract_product_id,
    normalize_url,
)


def test_normalize_url_strips_tracking_params():
    raw_url = "https://www.daraz.pk/products/item-i12345-s67890.html?spm=a2a0e.search.0.0.1234&clicktrack=xyz&scm=1007.123&wh_pid=999"
    clean = normalize_url(raw_url)
    assert "spm=" not in clean
    assert "clicktrack=" not in clean
    assert "scm=" not in clean
    assert "wh_pid=" not in clean
    assert clean == "https://www.daraz.pk/products/item-i12345-s67890.html"


def test_normalize_url_relative():
    rel = "/products/sample-i999.html"
    norm = normalize_url(rel, base_url="https://www.daraz.pk")
    assert norm == "https://www.daraz.pk/products/sample-i999.html"


def test_extract_product_id():
    url1 = "https://www.daraz.pk/products/redmi-note-13-8gb-256gb-i100101-s200201.html"
    assert extract_product_id(url1) == "100101"

    url2 = "https://www.daraz.pk/products/infinix-hot-40-pro-i987654321.html"
    assert extract_product_id(url2) == "987654321"

    url3 = "https://www.daraz.pk/catalog/?itemId=555444333"
    assert extract_product_id(url3) == "555444333"

    url4 = "https://www.daraz.pk/smartphones/"
    assert extract_product_id(url4) is None


def test_extract_category_id():
    url1 = "https://www.daraz.pk/smartphones/"
    assert extract_category_id_from_url(url1) == "smartphones"

    url2 = "https://www.daraz.pk/electronic-devices/laptops/"
    assert extract_category_id_from_url(url2) == "laptops"
