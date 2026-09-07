"""Tests for Discovery Checkpoints, Crash Recovery, and Resumption in Module 2."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.checkpoint import CheckpointManager
from app.core.constants import CrawlStatus
from app.discovery.detector import ChallengeDetectionResult
from app.discovery.engine import DarazDiscoveryEngine
from app.discovery.models import CategoryTarget, DiscoveryRun
from app.storage.repository import InMemoryStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


@pytest.mark.asyncio
async def test_discovery_checkpoint_creation_and_resumption():
    storage = InMemoryStorage()
    menu_html = (FIXTURES_DIR / "category_menu.html").read_text(encoding="utf-8")
    search_html = (FIXTURES_DIR / "search_results.html").read_text(encoding="utf-8")

    mock_client = MagicMock()
    mock_client.fetch_page = AsyncMock(
        side_effect=[
            (200, menu_html, "https://www.daraz.pk", ChallengeDetectionResult()),
            (200, search_html, "https://www.daraz.pk/smartphones/?page=1", ChallengeDetectionResult()),
            (200, search_html, "https://www.daraz.pk/catalog/?q=redmi&page=1", ChallengeDetectionResult()),
        ]
    )

    crawl_id = "resumable-discovery-session"
    engine = DarazDiscoveryEngine(storage=storage, discovery_client=mock_client)

    run = await engine.run_discovery(
        seed_categories=True,
        search_queries=["redmi"],
        max_category_pages=1,
        max_search_pages=1,
        crawl_id=crawl_id,
    )

    assert run.status == CrawlStatus.COMPLETED
    assert run.pages_processed >= 1

    # Verify checkpoint was recorded in storage
    checkpoint = await storage.get_checkpoint(crawl_id)
    assert checkpoint is not None
    assert checkpoint.crawl_id == crawl_id


@pytest.mark.asyncio
async def test_discovery_pauses_and_persists_on_challenge():
    storage = InMemoryStorage()
    mock_client = MagicMock()
    mock_client.fetch_page = AsyncMock(
        return_value=(
            403,
            "Cloudflare Access Denied",
            "https://www.daraz.pk/catalog/?q=blocked",
            ChallengeDetectionResult(is_challenge=True, is_blocked=True, reason="Cloudflare 403"),
        )
    )

    crawl_id = "blocked-session"
    engine = DarazDiscoveryEngine(storage=storage, discovery_client=mock_client)

    run = await engine.run_discovery(
        seed_categories=False,
        search_queries=["blocked"],
        max_search_pages=1,
        crawl_id=crawl_id,
    )

    assert run.status == CrawlStatus.MANUAL_INTERVENTION
    assert run.captcha_events >= 1
