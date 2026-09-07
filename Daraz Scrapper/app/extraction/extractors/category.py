"""Category hierarchy and breadcrumb extraction."""

import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup


class CategoryExtractor:
    """Extracts category path and names from breadcrumbs or structured metadata."""

    BREADCRUMB_SELECTORS = [
        "ul.breadcrumb li.breadcrumb_item",
        ".pdp-breadcrumb .breadcrumb-item",
        "#module_breadcrumb li",
        "[data-qa-locator='breadcrumb-item']",
        "ul.breadcrumb li",
    ]

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract (category_id, category_name_or_path).
        """
        breadcrumbs: List[str] = []
        category_id: Optional[str] = None

        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("category", {}))
            if isinstance(fields, dict):
                cat_data = fields.get("categories") or fields.get("breadcrumb") or []
                if isinstance(cat_data, list):
                    for item in cat_data:
                        if isinstance(item, str):
                            if item.strip() and item.strip().lower() != "home":
                                breadcrumbs.append(item.strip())
                        elif isinstance(item, dict):
                            name = item.get("name") or item.get("title")
                            if name and str(name).strip().lower() != "home":
                                breadcrumbs.append(str(name).strip())
                            if item.get("id"):
                                category_id = str(item.get("id"))

        # 2. DOM Selectors
        if not breadcrumbs:
            for sel in self.BREADCRUMB_SELECTORS:
                items = soup.select(sel)
                if items:
                    for item in items:
                        txt = item.get_text(strip=True)
                        if txt and txt not in (">", "/") and txt.lower() != "home":
                            breadcrumbs.append(txt)

                        # Extract category ID from the last link with slug
                        a_tag = item.find("a")
                        if a_tag and a_tag.get("href"):
                            href = str(a_tag.get("href")).strip()
                            if href and href != "/":
                                m = re.search(r"/([a-zA-Z0-9_-]+)/?$", href)
                                if m:
                                    category_id = m.group(1)
                    if breadcrumbs:
                        break

        if not breadcrumbs:
            return None, None

        cat_path = " > ".join(breadcrumbs)
        return category_id, cat_path
