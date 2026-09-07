"""HTML and JSON parsing adapter for Daraz marketplace category trees, product cards, and pagination.

Adapted and adapted from reference implementations:
- sushil-rgb/Daraz-Global-WebScraper (selectors.yaml and safe text extraction)
- MuhammadAhmedSuhail/WebScraping-Ecommerce-Website (DOM structure analysis)
- regmiprabesh/daraz-scraper (daraz_spider.py item extraction)
"""

from dataclasses import dataclass
import json
import re
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from bs4 import BeautifulSoup, Tag

from app.core.exceptions import ParserError
from app.discovery.config import DarazDiscoveryConfig, default_discovery_config
from app.discovery.models import CategoryTarget, ProductTarget
from app.discovery.normalizer import (
    canonicalize_product_url,
    extract_category_id_from_url,
    extract_product_id,
    normalize_url,
)
from app.discovery.selectors import DarazSelectors


@dataclass
class PaginationResult:
    """Extracted pagination status and navigation links from a listing page."""

    current_page: int
    has_next_page: bool
    next_page_url: Optional[str] = None
    total_pages: Optional[int] = None
    is_empty_page: bool = False

    def __iter__(self) -> Iterator[Any]:
        """Support tuple unpacking: (current_page, total_pages, next_page_url)."""
        yield self.current_page
        yield self.total_pages
        yield self.next_page_url


class DarazHTMLParser:
    """Parses raw HTML from Daraz pages to extract category trees, product links, and pagination."""

    def __init__(self, config: Optional[DarazDiscoveryConfig] = None):
        self.config = config or default_discovery_config

    def parse_categories(self, html_content: str, base_url: Optional[str] = None) -> List[CategoryTarget]:
        """Extract multi-level category navigation hierarchy from homepage or category listing HTML."""
        if not html_content or not html_content.strip():
            return []

        base = base_url or self.config.BASE_URL
        categories: List[CategoryTarget] = []
        seen_category_ids: Set[str] = set()

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. Try parsing JSON-LD or embedded pageData if available
            embedded_cats = self._extract_embedded_category_data(soup, base)
            if embedded_cats:
                return embedded_cats

            # 2. Parse from standard category navigation menu structures
            # Level 1 Categories (Root items)
            root_items: List[Tag] = []
            for sel in DarazSelectors.CATEGORY_ROOT_ITEMS:
                root_items = soup.select(sel)
                if root_items:
                    break

            if not root_items:
                # Fallback: search for general category anchors in category lists
                cat_links = soup.select(", ".join(DarazSelectors.CATEGORY_LINKS_FALLBACK))
                for a in cat_links:
                    href = a.get("href", "")
                    name = a.get_text(strip=True)
                    if href and name:
                        norm_url = normalize_url(href, base_url=base)
                        cat_id = extract_category_id_from_url(norm_url)
                        if cat_id and cat_id not in seen_category_ids:
                            seen_category_ids.add(cat_id)
                            categories.append(
                                CategoryTarget(
                                    category_id=cat_id,
                                    name=name,
                                    parent_id=None,
                                    url=norm_url,
                                    level=1,
                                    is_leaf=True,
                                    source="navigation_link",
                                )
                            )
                return categories

            for root_li in root_items:
                root_anchor = root_li.select_one("a[href]") or root_li.select_one("span")
                if not root_anchor:
                    continue

                root_name = root_anchor.get_text(strip=True)
                root_href = root_anchor.get("href", "") if root_anchor.name == "a" else ""
                root_url = normalize_url(root_href, base_url=base) if root_href else ""
                root_id = extract_category_id_from_url(root_url) if root_url else f"cat_{len(categories) + 1}"

                if not root_name or root_id in seen_category_ids:
                    continue

                seen_category_ids.add(root_id)

                # Check for subcategories under this root
                sub_items: List[Tag] = []
                for sub_sel in DarazSelectors.CATEGORY_SUB_ITEMS:
                    sub_items = root_li.select(sub_sel)
                    if sub_items:
                        break

                filtered_sub_items = [
                    item for item in sub_items if item.name == "li" or not item.find_all("li")
                ]
                has_subs = len(filtered_sub_items) > 0

                categories.append(
                    CategoryTarget(
                        category_id=root_id,
                        name=root_name,
                        parent_id=None,
                        url=root_url or f"{base}/catalog/?category={root_id}",
                        level=1,
                        is_leaf=not has_subs,
                        source="catalog_tree",
                    )
                )

                # Parse Level 2 & Level 3 Subcategories
                for sub_li in filtered_sub_items:
                    sub_anchor = sub_li.select_one("a[href]")
                    if not sub_anchor:
                        continue

                    sub_name = sub_anchor.get_text(strip=True)
                    sub_href = sub_anchor.get("href", "")
                    sub_url = normalize_url(sub_href, base_url=base)
                    sub_id = extract_category_id_from_url(sub_url)

                    if not sub_name or not sub_id or sub_id in seen_category_ids:
                        continue

                    seen_category_ids.add(sub_id)

                    # Check for Level 3 items inside this sub_li
                    l3_items = sub_li.select("ul li, div.level-3 a, .grand-child a")
                    is_leaf = len(l3_items) == 0

                    categories.append(
                        CategoryTarget(
                            category_id=sub_id,
                            name=sub_name,
                            parent_id=root_id,
                            url=sub_url,
                            level=2,
                            is_leaf=is_leaf,
                            source="catalog_tree",
                        )
                    )

                    # Parse Level 3 grand-child items
                    for l3 in l3_items:
                        l3_a = l3 if l3.name == "a" else l3.select_one("a[href]")
                        if not l3_a:
                            continue
                        l3_name = l3_a.get_text(strip=True)
                        l3_href = l3_a.get("href", "")
                        l3_url = normalize_url(l3_href, base_url=base)
                        l3_id = extract_category_id_from_url(l3_url)

                        if l3_name and l3_id and l3_id not in seen_category_ids:
                            seen_category_ids.add(l3_id)
                            categories.append(
                                CategoryTarget(
                                    category_id=l3_id,
                                    name=l3_name,
                                    parent_id=sub_id,
                                    url=l3_url,
                                    level=3,
                                    is_leaf=True,
                                    source="catalog_tree",
                                )
                            )

            return categories

        except Exception as e:
            raise ParserError(f"Failed to parse category hierarchy: {e}") from e

    def _extract_embedded_category_data(self, soup: BeautifulSoup, base: str) -> List[CategoryTarget]:
        """Extract category hierarchy from embedded script variables if present."""
        scripts = soup.find_all("script")
        for script in scripts:
            text = script.string or script.get_text() or ""
            if "window.pageData" in text or "categoryTree" in text:
                match = re.search(r"window\.pageData\s*=\s*(\{.*?\});", text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        tree = data.get("categoryTree") or data.get("mods", {}).get("categoryTree", {}).get("data", [])
                        if tree:
                            return self._build_targets_from_tree(tree, base)
                    except Exception:
                        pass
        return []

    def _build_targets_from_tree(self, tree_data: Any, base: str) -> List[CategoryTarget]:
        """Recursively construct CategoryTarget models from structured JSON tree data."""
        results: List[CategoryTarget] = []
        if isinstance(tree_data, list):
            for item in tree_data:
                results.extend(self._parse_json_node(item, parent_id=None, level=1, base=base))
        elif isinstance(tree_data, dict):
            for key, item in tree_data.items():
                results.extend(self._parse_json_node(item, parent_id=None, level=1, base=base))
        return results

    def _parse_json_node(self, node: Dict[str, Any], parent_id: Optional[str], level: int, base: str) -> List[CategoryTarget]:
        """Helper to parse a single JSON category node and its children."""
        res: List[CategoryTarget] = []
        name = node.get("name") or node.get("title") or ""
        url = node.get("url") or node.get("href") or ""
        children = node.get("children") or node.get("subCategories") or []

        if name:
            norm_url = normalize_url(url, base_url=base) if url else ""
            cat_id = str(node.get("id") or extract_category_id_from_url(norm_url) or name.lower().replace(" ", "-"))
            is_leaf = len(children) == 0

            res.append(
                CategoryTarget(
                    category_id=cat_id,
                    name=name,
                    parent_id=parent_id,
                    url=norm_url or f"{base}/catalog/?category={cat_id}",
                    level=level,
                    is_leaf=is_leaf,
                    source="embedded_json",
                )
            )

            for child in children:
                if isinstance(child, dict):
                    res.extend(self._parse_json_node(child, parent_id=cat_id, level=level + 1, base=base))
        return res

    def parse_product_targets(
        self,
        html_content: str,
        base_url: Optional[str] = None,
        source_category: Optional[str] = None,
        source_query: Optional[str] = None,
    ) -> List[ProductTarget]:
        """Extract product targets from category catalog or keyword search listing HTML."""
        if not html_content or not html_content.strip():
            return []

        base = base_url or self.config.BASE_URL
        targets: List[ProductTarget] = []
        seen_product_ids: Set[str] = set()

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. First attempt: Structured product card elements
            card_elements: List[Tag] = []
            for selector in DarazSelectors.PRODUCT_CARDS:
                cards = soup.select(selector)
                if cards:
                    card_elements = cards
                    break

            for card in card_elements:
                # Find anchor inside card
                anchor: Optional[Tag] = None
                for link_sel in DarazSelectors.PRODUCT_LINKS:
                    anchor = card.select_one(link_sel)
                    if anchor:
                        break

                if not anchor:
                    anchor = card.find("a", href=True)

                if not anchor:
                    continue

                raw_href = anchor.get("href", "")
                norm_url = normalize_url(raw_href, base_url=base)
                pid = extract_product_id(norm_url) or extract_product_id(card.get("data-item-id", ""))

                if not pid or pid in seen_product_ids:
                    continue

                seen_product_ids.add(pid)
                canonical_url = canonicalize_product_url(norm_url, base_url=base)

                targets.append(
                    ProductTarget(
                        product_id=pid,
                        url=norm_url,
                        canonical_url=canonical_url,
                        source="keyword" if source_query else "category",
                        keyword=source_query,
                        source_query=source_query,
                        category_name=source_category,
                        source_category=source_category,
                    )
                )

            # 2. Fallback: Scan all anchors matching Daraz product patterns if no cards matched
            if not targets:
                all_anchors = soup.find_all("a", href=True)
                for a in all_anchors:
                    href = a.get("href", "")
                    if "-i" in href or "/products/" in href or "itemId=" in href:
                        norm_url = normalize_url(href, base_url=base)
                        pid = extract_product_id(norm_url)
                        if pid and pid not in seen_product_ids:
                            seen_product_ids.add(pid)
                            canonical = canonicalize_product_url(norm_url, base_url=base)
                            targets.append(
                                ProductTarget(
                                    product_id=pid,
                                    url=norm_url,
                                    canonical_url=canonical,
                                    source="keyword" if source_query else "category",
                                    keyword=source_query,
                                    source_query=source_query,
                                    category_name=source_category,
                                    source_category=source_category,
                                )
                            )

            return targets

        except Exception as e:
            raise ParserError(f"Failed to parse product targets from page: {e}") from e

    def parse_pagination(
        self,
        html_content: str,
        current_page: int = 1,
        base_url: Optional[str] = None,
    ) -> PaginationResult:
        """Inspect listing page HTML for next page availability, total pages, or empty state."""
        if not html_content or not html_content.strip():
            return PaginationResult(current_page=current_page, has_next_page=False, is_empty_page=True)

        base = base_url or self.config.BASE_URL
        soup = BeautifulSoup(html_content, "html.parser")

        # Check for empty catalog indicator texts
        empty_indicators = [
            "no products found",
            "did not match any products",
            "we couldn't find any results",
            "0 items found",
            "no results found",
        ]
        page_text = soup.get_text(separator=" ", strip=True).lower()
        for empty_text in empty_indicators:
            if empty_text in page_text and len(soup.select(", ".join(DarazSelectors.PRODUCT_CARDS))) == 0:
                return PaginationResult(
                    current_page=current_page,
                    has_next_page=False,
                    is_empty_page=True,
                )

        # Check max page numbers from pagination items
        total_pages: Optional[int] = None
        page_items = soup.select(", ".join(DarazSelectors.PAGINATION_ITEMS))
        page_nums = []
        for item in page_items:
            t = item.get_text(strip=True)
            if t.isdigit():
                page_nums.append(int(t))
        if page_nums:
            total_pages = max(page_nums)

        # Check next page button in DOM
        has_next = False
        next_url: Optional[str] = None

        next_elem = soup.select_one("li.ant-pagination-next, li[title='Next Page']")
        if next_elem:
            classes = next_elem.get("class", [])
            is_disabled = (
                "ant-pagination-disabled" in classes
                or "disabled" in classes
                or next_elem.get("aria-disabled") == "true"
            )
            if not is_disabled:
                a_tag = next_elem.find("a") if next_elem.name != "a" else next_elem
                if a_tag and a_tag.get("href"):
                    href = a_tag.get("href")
                    norm = normalize_url(href, base_url=base)
                    if norm and norm != base and norm != f"{base}/":
                        has_next = True
                        next_url = norm
                elif total_pages and current_page < total_pages:
                    has_next = True
                    next_url = f"{base}/catalog/?page={current_page + 1}"

        # If total_pages indicates we have reached or exceeded last page, force no next page
        if total_pages is not None and current_page >= total_pages:
            has_next = False
            next_url = None

        return PaginationResult(
            current_page=current_page,
            has_next_page=has_next,
            next_page_url=next_url,
            total_pages=total_pages,
            is_empty_page=False,
        )


# Default singleton parser instance
daraz_parser = DarazHTMLParser()
