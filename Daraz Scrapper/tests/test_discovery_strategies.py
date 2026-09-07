"""Tests for Category, Keyword, and Pagination discovery strategies in Module 2."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.discovery.client import DarazDiscoveryClient
from app.discovery.config import DarazDiscoveryConfig
from app.discovery.detector import ChallengeDetectionResult
from app.discovery.models import CategoryTarget, ProductTarget
from app.discovery.parser import DarazHTMLParser
from app.discovery.queue import ProductTargetQueue
from app.discovery.strategies.category import CategoryDiscoveryStrategy
from app.discovery.strategies.keyword import KeywordDiscoveryStrategy
from app.discovery.strategies.pagination import PaginationRunner, PaginationStrategy
from app.storage.repository import InMemoryStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


@pytest.fixture
def parser():
    return DarazHTMLParser()


@pytest.fixture
def storage():
    return InMemoryStorage()


@pytest.fixture
def queue(storage):
    return ProductTargetQueue(storage=storage)


@pytest.mark.asyncio
async def test_pagination_strategy_url_generation():
    strat = PaginationStrategy()
    url = "https://www.daraz.pk/catalog/?q=laptop"
    page2_url = strat.build_page_url(url, 2)
    assert "page=2" in page2_url
    assert "q=laptop" in page2_url

    page3_url = strat.build_page_url(page2_url, 3)
    assert "page=3" in page3_url


@pytest.mark.asyncio
async def test_pagination_runner_stops_on_empty_page(parser, queue):
    mock_client = MagicMock()
    # Page 1 has results, Page 2 is empty
    page1_html = (FIXTURES_DIR / "search_results.html").read_text(encoding="utf-8")
    page2_empty_html = "<html><body><div>No products found matching your search.</div></body></html>"

    mock_client.fetch_page = AsyncMock(
        side_effect=[
            (200, page1_html, "https://www.daraz.pk/catalog/?q=test&page=1", ChallengeDetectionResult()),
            (200, page2_empty_html, "https://www.daraz.pk/catalog/?q=test&page=2", ChallengeDetectionResult()),
        ]
    )

    runner = PaginationRunner(client=mock_client, parser=parser, queue=queue)
    stats = await runner.paginate(start_url="https://www.daraz.pk/catalog/?q=test", max_pages=5)

    assert stats.pages_processed == 2
    assert stats.total_targets_found == 3  # from page 1
    assert stats.stopped_reason == "empty_page"
    assert queue.total_unique() == 3


@pytest.mark.asyncio
async def test_pagination_runner_halts_on_challenge(parser, queue):
    mock_client = MagicMock()
    mock_client.fetch_page = AsyncMock(
        return_value=(
            403,
            "Access Denied",
            "https://www.daraz.pk/catalog/?q=test",
            ChallengeDetectionResult(is_challenge=True, is_blocked=True, reason="HTTP 403 Forbidden"),
        )
    )

    runner = PaginationRunner(client=mock_client, parser=parser, queue=queue)
    stats = await runner.paginate(start_url="https://www.daraz.pk/catalog/?q=test", max_pages=3)

    assert "challenge_detected" in stats.stopped_reason
    assert stats.pages_processed == 0
    assert stats.total_targets_found == 0


@pytest.mark.asyncio
async def test_category_discovery_strategy(parser, queue, storage):
    menu_html = (FIXTURES_DIR / "category_menu.html").read_text(encoding="utf-8")
    mock_client = MagicMock()
    mock_client.fetch_page = AsyncMock(
        return_value=(200, menu_html, "https://www.daraz.pk", ChallengeDetectionResult())
    )

    strat = CategoryDiscoveryStrategy(
        client=mock_client, parser=parser, queue=queue, storage=storage
    )
    categories = await strat.discover_category_tree(start_url="https://www.daraz.pk")

    assert len(categories) > 0
    top_level = [c for c in categories if c.level == 1]
    assert len(top_level) == 3
    assert any(c.name == "Electronic Devices" for c in top_level)

    sub_cats = [c for c in categories if c.level > 1]
    assert len(sub_cats) > 0


@pytest.mark.asyncio
async def test_keyword_discovery_strategy(parser, queue):
    search_html = (FIXTURES_DIR / "search_results.html").read_text(encoding="utf-8")
    mock_client = MagicMock()
    mock_client.fetch_page = AsyncMock(
        return_value=(200, search_html, "https://www.daraz.pk/catalog/?q=smartphones", ChallengeDetectionResult())
    )

    strat = KeywordDiscoveryStrategy(client=mock_client, parser=parser, queue=queue)
    search_url = strat.build_search_url("smartphones")
    assert "q=smartphones" in search_url

    stats = await strat.crawl_keyword("smartphones", max_pages=1)
    assert stats.pages_processed == 1
    assert stats.total_targets_found == 3
    assert queue.total_unique() == 3
