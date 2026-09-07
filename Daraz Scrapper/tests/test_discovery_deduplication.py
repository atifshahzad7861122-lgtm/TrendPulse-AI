"""Tests for cross-category and cross-keyword global product deduplication in Module 2."""

import pytest
from app.discovery.models import ProductTarget
from app.discovery.normalizer import canonicalize_product_url, extract_product_id, normalize_url
from app.discovery.queue import ProductTargetQueue
from app.storage.repository import InMemoryStorage


@pytest.mark.asyncio
async def test_cross_category_and_keyword_deduplication():
    storage = InMemoryStorage()
    queue = ProductTargetQueue(storage=storage)

    # Product discovered under category "Smartphones"
    t1 = ProductTarget(
        product_id="990011",
        url="https://www.daraz.pk/products/xiaomi-redmi-note-13-i990011-s123.html?spm=a2a0e.category.1",
        canonical_url="https://www.daraz.pk/products/xiaomi-redmi-note-13-i990011-s123.html",
        category_name="Smartphones",
    )

    # Same product discovered under keyword search "redmi"
    t2 = ProductTarget(
        product_id="990011",
        url="https://www.daraz.pk/products/xiaomi-redmi-note-13-i990011-s123.html?q=redmi&scm=search.1",
        canonical_url="https://www.daraz.pk/products/xiaomi-redmi-note-13-i990011-s123.html",
        keyword="redmi",
    )

    # Same product discovered under category "Mobile Phones" with alternate tracking params
    t3 = ProductTarget(
        product_id="990011",
        url="https://www.daraz.pk/products/xiaomi-redmi-note-13-i990011-s123.html?wh_pid=banner",
        canonical_url="https://www.daraz.pk/products/xiaomi-redmi-note-13-i990011-s123.html",
        category_name="Mobile Phones",
    )

    # Different product
    t4 = ProductTarget(
        product_id="990022",
        url="https://www.daraz.pk/products/samsung-galaxy-s24-i990022-s456.html",
        canonical_url="https://www.daraz.pk/products/samsung-galaxy-s24-i990022-s456.html",
        category_name="Smartphones",
    )

    # Push all targets
    res1 = await queue.push(t1)
    res2 = await queue.push(t2)
    res3 = await queue.push(t3)
    res4 = await queue.push(t4)

    assert res1 is True
    assert res2 is False  # duplicate prevented
    assert res3 is False  # duplicate prevented
    assert res4 is True

    assert queue.total_unique() == 2
    assert queue.total_duplicates() == 2
    assert queue.products_discovered == 4


def test_url_canonicalization_and_product_id_formats():
    # Test format 1: -i{digits}-s{digits}.html
    url1 = "https://www.daraz.pk/products/apple-iphone-15-pro-max-i438927492-s2049281.html?spm=a2a0e.search.0.0.380a"
    assert extract_product_id(url1) == "438927492"
    canon1 = canonicalize_product_url(url1)
    assert canon1 == "https://www.daraz.pk/products/apple-iphone-15-pro-max-i438927492-s2049281.html"

    # Test format 2: -i{digits}.html
    url2 = "https://www.daraz.pk/products/case-for-iphone-i55443322.html?clicktrack=abc"
    assert extract_product_id(url2) == "55443322"
    assert canonicalize_product_url(url2) == "https://www.daraz.pk/products/case-for-iphone-i55443322.html"

    # Test format 3: query parameter itemId
    url3 = "https://www.daraz.pk/item.htm?itemId=88776655&wh_pid=promo"
    assert extract_product_id(url3) == "88776655"
