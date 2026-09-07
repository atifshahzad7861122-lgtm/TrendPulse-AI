"""Technical specifications key-value extraction."""

from typing import Any, Dict, Optional
from bs4 import BeautifulSoup


class SpecificationExtractor:
    """Extracts technical specifications and attributes into normalized key-value pairs."""

    SPEC_CONTAINER_SELECTORS = [
        ".pdp-mod-specification",
        "#module_product_specification",
        ".pdp-general-features",
        ".specification-keys",
    ]

    def extract(
        self,
        soup: BeautifulSoup,
        raw_json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Extract key-value specifications dictionary.
        """
        specs: Dict[str, str] = {}

        # 1. Structured Page Data
        if raw_json:
            fields = raw_json.get("fields", raw_json.get("specifications", {}))
            if isinstance(fields, dict):
                spec_data = fields.get("specifications") or fields.get("specData") or {}
                if isinstance(spec_data, dict):
                    for k, v in spec_data.items():
                        if k and v:
                            specs[str(k).strip()] = str(v).strip()
                elif isinstance(spec_data, list):
                    for item in spec_data:
                        if isinstance(item, dict):
                            k = item.get("name") or item.get("key") or item.get("title")
                            v = item.get("value") or item.get("val")
                            if k and v:
                                specs[str(k).strip()] = str(v).strip()

                if specs:
                    return specs

        # 2. DOM Selectors
        for sel in self.SPEC_CONTAINER_SELECTORS:
            container = soup.select_one(sel)
            if container:
                # Look for list items or table rows
                items = container.select("li, tr, .key-li, .specification-keys li")
                for it in items:
                    key_el = it.select_one(".key-title, th, .key, strong, span.title")
                    val_el = it.select_one(".key-value, td, .value, span.content")
                    if key_el and val_el:
                        k = key_el.get_text(strip=True).rstrip(":")
                        v = val_el.get_text(strip=True)
                        if k and v:
                            specs[k] = v
                    else:
                        txt = it.get_text(strip=True)
                        if ":" in txt:
                            parts = txt.split(":", 1)
                            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                                specs[parts[0].strip()] = parts[1].strip()

                if specs:
                    break

        return specs
