"""Tests for Module 2 data contracts and discovery models."""

from datetime import datetime
import pytest
from pydantic import ValidationError

from app.core.constants import CrawlStatus
from app.discovery.models import CategoryTarget, DiscoveryRun, ProductTarget


def test_category_target_model():
    cat = CategoryTarget(
        category_id="smartphones",
        name="Smartphones",
        parent_id="electronic-devices",
        url="https://www.daraz.pk/smartphones/",
        level=2,
        is_leaf=False,
    )
    assert cat.category_id == "smartphones"
    assert cat.level == 2
    assert cat.is_leaf is False
    assert isinstance(cat.discovered_at, datetime)


def test_product_target_model():
    target = ProductTarget(
        product_id="100101",
        url="https://www.daraz.pk/products/item-i100101.html",
        source_category="Smartphones",
        source_query="Redmi",
    )
    assert target.product_id == "100101"
    assert "https://www.daraz.pk/products/item-i100101.html" in target.url
    assert target.source_category == "Smartphones"
    assert target.source_query == "Redmi"


def test_discovery_run_model():
    run = DiscoveryRun(
        status=CrawlStatus.RUNNING,
        categories_discovered=10,
        subcategories_discovered=25,
        product_urls_discovered=100,
        unique_products_discovered=80,
        duplicates_removed=20,
    )
    assert run.status == CrawlStatus.RUNNING
    assert run.unique_products_discovered == 80
    assert run.duplicates_removed == 20
    assert run.pages_failed == 0
