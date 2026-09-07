"""Technical and catalog specification extraction."""

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag

from app.intelligence.models.product import Specification


class SpecificationExtractor:
    """
    Extracts key-value technical specifications from product tables, definition lists, or JSON.
    Preserves original keys and values.
    """

    @classmethod
    def extract_from_dict(cls, data: Dict[str, Any], group: str = "General") -> List[Specification]:
        """Convert specification dictionary into list of Specification objects."""
        specs: List[Specification] = []
        for k, v in data.items():
            if v is not None and str(v).strip():
                specs.append(Specification(
                    key=str(k).strip(),
                    value=str(v).strip(),
                    group=group,
                ))
        return specs

    @classmethod
    def extract_from_dom(cls, soup: BeautifulSoup) -> List[Specification]:
        """Extract specifications from HTML tables or list elements."""
        specs: List[Specification] = []
        seen_keys = set()

        # 1. Look for definition lists (<dl><dt>Key</dt><dd>Value</dd></dl>)
        for dl in soup.select("dl, .prod-specifications, .pdp-mod-specification"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                k = dt.get_text(strip=True).rstrip(":")
                v = dd.get_text(strip=True)
                if k and v and k not in seen_keys:
                    seen_keys.add(k)
                    specs.append(Specification(key=k, value=v))

        # 2. Look for two-column tables
        for table in soup.select("table.prod-params, table#productDetails_techSpec_section_1, table.technical-specifications, .spec-table"):
            for row in table.find_all("tr"):
                cols = row.find_all(["th", "td"])
                if len(cols) >= 2:
                    k = cols[0].get_text(strip=True).rstrip(":")
                    v = cols[1].get_text(strip=True)
                    if k and v and k not in seen_keys and len(k) < 50:
                        seen_keys.add(k)
                        specs.append(Specification(key=k, value=v))

        # 3. Look for list items with bold keys (<li><b>Brand:</b> Apple</li>)
        for li in soup.select(".specification-keys li, .tech-specs li, #feature-bullets li"):
            b_tag = li.find(["b", "strong"])
            if b_tag:
                k = b_tag.get_text(strip=True).rstrip(":")
                full_text = li.get_text(strip=True)
                v = full_text.replace(b_tag.get_text(strip=True), "").lstrip(": -").strip()
                if k and v and k not in seen_keys and len(k) < 50:
                    seen_keys.add(k)
                    specs.append(Specification(key=k, value=v))

        return specs
