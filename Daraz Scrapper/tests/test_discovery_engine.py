"""Tests for DarazDiscoveryEngine end-to-end flows, pagination, checkpoints, and manual intervention."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.constants import CrawlStatus
from app.discovery.detector import ChallengeDetectionResult
from app.discovery.engine import DarazDiscoveryEngine
from app.discovery.manual_intervention import ManualInterventionManager
from app.discovery.models import CategoryTarget, DiscoveryRun
from app.storage.repository import InMemoryStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


@pytest.mark.asyncio
async def test_engine_discover_categories():
    menu_html = (FIXTURES_DIR / "category_menu.html").read_text(encoding="utf-8")
    storage = InMemoryStorage()

    mock_client = MagicMock()
    mock_client.fetch_page = AsyncMock(
        return_value=(200, menu_html, "https://www.daraz.pk", ChallengeDetectionResult())
    )

    engine = DarazDiscoveryEngine(storage=storage, discovery_client=mock_client)
    run = DiscoveryRun()
    categories = await engine.discover_categories(run_record=run)

    assert len(categories) > 0
    assert run.categories_discovered == 3
    assert run.subcategories_discovered >= 5
    assert run.pages_processed == 1

    stored_categories = await storage.get_category_targets()
    assert len(stored_categories) == len(categories)


@pytest.mark.asyncio
async def test_engine_discover_category_products_paginated():
    page1_html = (FIXTURES_DIR / "search_results.html").read_text(encoding="utf-8")
    page2_html = (FIXTURES_DIR / "search_results_page2.html").read_text(encoding="utf-8")

    storage = InMemoryStorage()
    mock_client = MagicMock()

    # Simulate 2 pages response
    mock_client.fetch_page = AsyncMock(
        side_effect=[
            (200, page1_html, "https://www.daraz.pk/smartphones/?page=1", ChallengeDetectionResult()),
            (200, page2_html, "https://www.daraz.pk/smartphones/?page=2", ChallengeDetectionResult()),
        ]
    )

    engine = DarazDiscoveryEngine(storage=storage, discovery_client=mock_client)
    run = DiscoveryRun()

    cat_target = CategoryTarget(
        category_id="smartphones",
        name="Smartphones",
        url="https://www.daraz.pk/smartphones/",
    )

    targets = await engine.discover_category_products(
        category_target=cat_target, max_pages=2, run_record=run
    )

    # Page 1 had items 100101, 100102, 100103. Page 2 had 100104 and repeat of 100101.
    assert len(targets) == 5  # raw discovered
    assert run.unique_products_discovered == 4  # 100101, 100102, 100103, 100104
    assert run.duplicates_removed == 1  # repeated 100101 removed
    assert run.pages_processed == 2


@pytest.mark.asyncio
async def test_engine_captcha_triggers_manual_intervention():
    captcha_html = (FIXTURES_DIR / "captcha_challenge.html").read_text(encoding="utf-8")
    storage = InMemoryStorage()
    intervention_mgr = ManualInterventionManager()

    mock_client = MagicMock()
    mock_client.fetch_page = AsyncMock(
        return_value=(
            200,
            captcha_html,
            "https://www.daraz.pk/punish?...",
            ChallengeDetectionResult(is_challenge=True, is_captcha=True, reason="CAPTCHA detected"),
        )
    )

    engine = DarazDiscoveryEngine(
        storage=storage, discovery_client=mock_client, intervention_manager=intervention_mgr
    )
    run = DiscoveryRun(crawl_id="test-captcha-crawl")

    # Attempt category exploration
    await engine.discover_categories(crawl_id="test-captcha-crawl", run_record=run)

    # Should detect captcha and enter manual intervention state
    assert run.captcha_events == 1
    assert run.status == CrawlStatus.MANUAL_INTERVENTION


@pytest.mark.asyncio
async def test_engine_full_discovery_orchestration():
    menu_html = (FIXTURES_DIR / "category_menu.html").read_text(encoding="utf-8")
    search_html = (FIXTURES_DIR / "search_results.html").read_text(encoding="utf-8")

    storage = InMemoryStorage()
    mock_client = MagicMock()

    async def mock_fetch(url: str, **kwargs):
        if "category" in url or "daraz.pk/" == url or url == "https://www.daraz.pk":
            return 200, menu_html, url, ChallengeDetectionResult()
        return 200, search_html, url, ChallengeDetectionResult()

    mock_client.fetch_page = AsyncMock(side_effect=mock_fetch)

    engine = DarazDiscoveryEngine(storage=storage, discovery_client=mock_client)

    run = await engine.run_discovery(
        seed_categories=True,
        search_queries=["redmi"],
        max_category_pages=1,
        max_search_pages=1,
    )

    assert run.status == CrawlStatus.COMPLETED
    assert run.categories_discovered > 0
    assert run.product_urls_discovered > 0
    assert run.unique_products_discovered > 0

    # Ensure saved in storage
    saved_run = await storage.get_discovery_run(run.crawl_id)
    assert saved_run is not None
    assert saved_run.status == CrawlStatus.COMPLETED
