"""Tests for storage interface and repository implementations."""

import pytest
from app.core.constants import CrawlStatus, CrawlType, SentimentType
from app.models import Category, CrawlRun, Image, Product, Review
from app.storage.repository import InMemoryStorage


@pytest.mark.asyncio
async def test_storage_product_crud(storage: InMemoryStorage):
    product = Product(
        product_id="P-TEST-1",
        title="Sample Product",
        url="https://example.com/p1",
        price=1500.0,
    )

    await storage.save_product(product)
    retrieved = await storage.get_product("P-TEST-1")
    assert retrieved is not None
    assert retrieved.title == "Sample Product"
    assert retrieved.price == 1500.0

    # Test bulk save
    products = [
        Product(product_id="P-TEST-2", title="P2", url="https://example.com/p2", price=200.0),
        Product(product_id="P-TEST-3", title="P3", url="https://example.com/p3", price=300.0),
    ]
    saved_count = await storage.save_products(products)
    assert saved_count == 2
    assert (await storage.get_product("P-TEST-2")) is not None


@pytest.mark.asyncio
async def test_storage_review_crud(storage: InMemoryStorage):
    review = Review(
        product_id="P-TEST-1",
        rating=4.0,
        text="Very good product",
        sentiment=SentimentType.POSITIVE,
    )
    await storage.save_review(review)
    assert len(storage._reviews) == 1

    bulk_reviews = [
        Review(product_id="P-TEST-1", rating=5.0, text="Amazing!"),
        Review(product_id="P-TEST-2", rating=2.0, text="Poor quality", is_negative=True),
    ]
    saved = await storage.save_reviews(bulk_reviews)
    assert saved == 2
    assert len(storage._reviews) == 3


@pytest.mark.asyncio
async def test_storage_crawl_run_crud(storage: InMemoryStorage):
    crawl = CrawlRun(
        crawl_id="CRAWL-101",
        crawl_type=CrawlType.FULL,
        status=CrawlStatus.RUNNING,
    )
    await storage.create_crawl_run(crawl)

    retrieved = await storage.get_crawl_run("CRAWL-101")
    assert retrieved is not None
    assert retrieved.status == CrawlStatus.RUNNING

    # Test update crawl run
    updated = await storage.update_crawl_run(
        "CRAWL-101",
        status=CrawlStatus.COMPLETED,
        items_processed=150,
    )
    assert updated is not None
    assert updated.status == CrawlStatus.COMPLETED
    assert updated.items_processed == 150
