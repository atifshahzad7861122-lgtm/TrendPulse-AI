"""Tests for Daraz category hierarchy, product card, and pagination parsing."""

from pathlib import Path
import pytest
from app.discovery.parser import DarazHTMLParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


@pytest.fixture
def parser():
    return DarazHTMLParser()


def test_parse_categories_from_menu_fixture(parser: DarazHTMLParser):
    html = (FIXTURES_DIR / "category_menu.html").read_text(encoding="utf-8")
    categories = parser.parse_categories(html)

    assert len(categories) > 0
    # Level 1 check
    level1 = [c for c in categories if c.level == 1]
    assert len(level1) == 3
    assert any(c.name == "Electronic Devices" for c in level1)
    assert any(c.name == "Health & Beauty" for c in level1)
    assert any(c.name == "Fashion" for c in level1)

    # Level 2 check
    level2 = [c for c in categories if c.level == 2]
    assert len(level2) >= 3
    assert any(c.name == "Smartphones" and c.parent_id == "electronic-devices" for c in level2)

    # Level 3 check
    level3 = [c for c in categories if c.level == 3]
    assert len(level3) >= 2
    assert any(c.name == "Android Phones" and c.is_leaf is True for c in level3)


def test_parse_product_targets_from_search_fixture(parser: DarazHTMLParser):
    html = (FIXTURES_DIR / "search_results.html").read_text(encoding="utf-8")
    targets = parser.parse_product_targets(html, source_query="smartphones")

    assert len(targets) == 3
    assert targets[0].product_id == "100101"
    assert "https://www.daraz.pk/products/redmi-note-13-8gb-256gb-i100101-s200201.html" in targets[0].url
    assert "spm=" not in targets[0].url  # Verify tracking query removed
    assert targets[0].source_query == "smartphones"

    assert targets[1].product_id == "100102"
    assert targets[2].product_id == "100103"


def test_parse_pagination(parser: DarazHTMLParser):
    html_page1 = (FIXTURES_DIR / "search_results.html").read_text(encoding="utf-8")
    current_page, total_pages, next_page = parser.parse_pagination(html_page1, current_page=1)

    assert current_page == 1
    assert total_pages == 3
    assert next_page is not None
    assert "page=2" in next_page

    html_page2 = (FIXTURES_DIR / "search_results_page2.html").read_text(encoding="utf-8")
    current_page, total_pages, next_page = parser.parse_pagination(html_page2, current_page=2)
    assert current_page == 2
    assert total_pages == 2
    # Next page is disabled in page 2 fixture
    assert next_page is None
