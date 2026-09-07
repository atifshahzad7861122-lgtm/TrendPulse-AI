"""Category classification and breadcrumb extraction."""

from typing import List, Optional, Tuple
from bs4 import BeautifulSoup


class CategoryExtractor:
    """
    Extracts structured multi-level category hierarchies and breadcrumbs from HTML or JSON.
    """

    @classmethod
    def extract_from_breadcrumbs(
        cls,
        soup: BeautifulSoup,
        selectors: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Extract (category_name, category_path, breadcrumbs) from DOM.
        """
        default_selectors = [
            ".breadcrumb li",
            "#wayfinding-breadcrumbs_feature_div li",
            ".pdp-breadcrumb li",
            "nav.breadcrumbs ol li",
            ".ebay-breadcrumb li",
        ]

        crumbs: List[str] = []
        for sel in (selectors or default_selectors):
            elements = soup.select(sel)
            if elements:
                for el in elements:
                    text = el.get_text(strip=True).rstrip(">/")
                    if text and text.lower() not in ("home", "back to search", "all categories"):
                        crumbs.append(text)
                if crumbs:
                    break

        if not crumbs:
            return None, None, []

        cat_name = crumbs[-1]
        cat_path = " > ".join(crumbs)
        return cat_name, cat_path, crumbs
