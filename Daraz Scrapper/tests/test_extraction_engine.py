"""Integration tests for DarazProductExtractor engine orchestrator."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.discovery.models import ProductTarget
from app.extraction.engine import DarazProductExtractor
from app.storage.repository import InMemoryStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


@pytest.mark.asyncio
async def test_extractor_single_product_success():
    html = (FIXTURES_DIR / "product_page_standard.html").read_text(encoding="utf-8")
    storage = InMemoryStorage()

    extractor = DarazProductExtractor(storage=storage)
    extractor._fetch_browser = AsyncMock(return_value=(200, html))

    target = ProductTarget(
        product_id="100101",
        url="https://www.daraz.pk/products/redmi-note-13-i100101-s200201.html",
    )

    result = await extractor.extract_product(target, use_browser=True)

    assert result.success is True
    assert result.product is not None
    assert result.product.product_id == "100101"
    assert result.product.price == 45999.0
    assert result.product.rating == 4.7
    assert len(result.product.images) == 3

    # Check persistence in storage
    saved_prod = await storage.get_product("100101")
    assert saved_prod is not None
    assert saved_prod.title == result.product.title


@pytest.mark.asyncio
async def test_extractor_batch_extraction():
    html_standard = (FIXTURES_DIR / "product_page_standard.html").read_text(encoding="utf-8")
    html_minimal = (FIXTURES_DIR / "product_page_minimal.html").read_text(encoding="utf-8")

    storage = InMemoryStorage()
    extractor = DarazProductExtractor(storage=storage)

    async def mock_fetch(url: str):
        if "redmi" in url:
            return 200, html_standard
        return 200, html_minimal

    extractor._fetch_browser = AsyncMock(side_effect=mock_fetch)

    targets = [
        ProductTarget(product_id="100101", url="https://www.daraz.pk/products/redmi-note-13-i100101.html"),
        ProductTarget(product_id="200202", url="https://www.daraz.pk/products/cotton-tshirt-i200202.html"),
    ]

    results = await extractor.extract_batch(targets, use_browser=True, concurrency=2)

    assert len(results) == 2
    assert results[0].success is True
    assert results[0].product.product_id == "100101"
    assert results[1].success is True
    assert results[1].product.product_id == "200202"


@pytest.mark.asyncio
async def test_extractor_404_error_handling():
    storage = InMemoryStorage()
    extractor = DarazProductExtractor(storage=storage)
    extractor._fetch_browser = AsyncMock(return_value=(404, "<html><body>Not Found</body></html>"))

    target = ProductTarget(product_id="999999", url="https://www.daraz.pk/products/delisted-i999999.html")
    result = await extractor.extract_product(target, use_browser=True)

    assert result.success is False
    assert result.product is None
    assert any("404" in err for err in result.errors)


@pytest.mark.asyncio
async def test_extractor_captcha_detection_pause():
    captcha_html = (FIXTURES_DIR / "captcha_challenge.html").read_text(encoding="utf-8")
    storage = InMemoryStorage()

    extractor = DarazProductExtractor(storage=storage)
    extractor._fetch_browser = AsyncMock(return_value=(200, captcha_html))

    target = ProductTarget(product_id="888888", url="https://www.daraz.pk/products/challenge-i888888.html")
    result = await extractor.extract_product(target, use_browser=True)

    assert result.success is False
    assert result.product is None
    assert any("Challenge" in err or "challenge" in err.lower() for err in result.errors)
    assert extractor.intervention_manager.is_paused is True

    # Clean up paused state
    await extractor.intervention_manager.resolve_intervention()
    assert extractor.intervention_manager.is_paused is False
