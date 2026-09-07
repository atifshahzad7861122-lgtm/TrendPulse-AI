"""Tests for RawDataRecord preservation and batch storage."""

import pytest
from app.models.raw_data import RawDataRecord
from app.storage.repository import InMemoryStorage


@pytest.mark.asyncio
async def test_raw_data_preservation_and_batch():
    storage = InMemoryStorage()

    rec1 = RawDataRecord(
        source_url="https://www.daraz.pk/products/item1.html",
        content_type="html",
        payload="<html><body>Product 1 HTML</body></html>",
        response_status=200,
    )
    rec2 = RawDataRecord(
        source_url="https://www.daraz.pk/api/item2.json",
        content_type="json",
        payload={"product_id": "P2", "price": 1500},
        response_status=200,
    )

    # Save single
    await storage.save_raw_data(rec1)
    retrieved = await storage.get_raw_data(rec1.raw_id)
    assert retrieved is not None
    assert retrieved.source_url == rec1.source_url
    assert "Product 1 HTML" in retrieved.payload
    assert retrieved.parser_version == "1.0.0"

    # Save batch
    count = await storage.save_raw_data_batch([rec2])
    assert count == 1
    retrieved2 = await storage.get_raw_data(rec2.raw_id)
    assert retrieved2.content_type == "json"
    assert retrieved2.payload["product_id"] == "P2"
