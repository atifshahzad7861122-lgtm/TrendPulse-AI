"""Tests for ProductTargetQueue and global deduplication."""

import pytest
from app.discovery.models import ProductTarget
from app.discovery.queue import ProductTargetQueue
from app.storage.repository import InMemoryStorage


@pytest.mark.asyncio
async def test_queue_push_and_deduplication():
    storage = InMemoryStorage()
    queue = ProductTargetQueue(storage=storage)

    t1 = ProductTarget(product_id="101", url="https://www.daraz.pk/p101.html")
    t2 = ProductTarget(product_id="102", url="https://www.daraz.pk/p102.html")
    t1_duplicate = ProductTarget(product_id="101", url="https://www.daraz.pk/p101.html?source=dup")

    # Push first time
    assert await queue.push(t1) is True
    assert await queue.push(t2) is True

    # Duplicate should return False
    assert await queue.push(t1_duplicate) is False

    assert queue.total_unique() == 2
    assert queue.total_duplicates() == 1
    assert queue.size() == 2


@pytest.mark.asyncio
async def test_queue_push_many_and_drain():
    storage = InMemoryStorage()
    queue = ProductTargetQueue(storage=storage)

    targets = [
        ProductTarget(product_id="201", url="https://www.daraz.pk/p201.html"),
        ProductTarget(product_id="202", url="https://www.daraz.pk/p202.html"),
        ProductTarget(product_id="201", url="https://www.daraz.pk/p201.html"),  # duplicate
        ProductTarget(product_id="203", url="https://www.daraz.pk/p203.html"),
    ]

    enqueued, duplicates = await queue.push_many(targets)
    assert enqueued == 3
    assert duplicates == 1

    # Drain items
    drained = await queue.drain(max_items=2)
    assert len(drained) == 2
    assert queue.size() == 1

    # Storage should have received the items
    stored = await storage.get_product_targets()
    assert len(stored) == 3
