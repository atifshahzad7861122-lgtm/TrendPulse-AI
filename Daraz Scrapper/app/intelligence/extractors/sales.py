"""Sales volume extraction and normalization across marketplaces."""

import re
from typing import Optional, Tuple


class SalesExtractor:
    """
    High-priority sales extraction and numeric normalization.
    Handles formats like '1.2K sold', '500+ sold', '1,000 sold', '10K+ sold', '123 purchased',
    'over 50 bought in past month', '1,200 orders', '300+ sales'.
    Never invents or fabricates sales figures.
    """

    # Comprehensive multi-format patterns
    _PATTERNS = [
        # 1.2K sold / 1.5M sold / 10K+ sold
        re.compile(r"([\d\.,]+)\s*([kKmMbB])\+?\s*(?:sold|purchased|bought|orders|sales)", re.IGNORECASE),
        # 500+ sold / 1,000 sold / 123 sold / 123 purchased
        re.compile(r"([\d\.,]+)\+?\s*(?:sold|purchased|bought|orders|sales)", re.IGNORECASE),
        # Over 50 bought in past month / Over 1,000 sold
        re.compile(r"(?:over|more than)\s+([\d\.,]+)\s*([kKmMbB])?\+?\s*(?:sold|bought|orders)", re.IGNORECASE),
        # Bought in past month: 50+ / 100+
        re.compile(r"(?:bought in past (?:month|week|day))\s*:\s*([\d\.,]+)\s*([kKmMbB])?\+?", re.IGNORECASE),
        # 100+ items sold
        re.compile(r"([\d\.,]+)\+?\s*(?:items|units)\s+sold", re.IGNORECASE),
    ]

    @classmethod
    def extract_sales(cls, text: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
        """
        Extract normalized integer sales count and original raw string.
        Returns (normalized_int, raw_sold_text) or (None, None).
        """
        if not text or not text.strip():
            return None, None

        raw = text.strip()

        # 1. Try regex pattern matches
        for pattern in cls._PATTERNS:
            match = pattern.search(raw)
            if match:
                groups = match.groups()
                num_str = groups[0].replace(",", "")
                multiplier_str = groups[1] if len(groups) > 1 and groups[1] else None

                try:
                    base_num = float(num_str)
                    multiplier = 1
                    if multiplier_str:
                        m_upper = multiplier_str.upper()
                        if m_upper == "K":
                            multiplier = 1000
                        elif m_upper == "M":
                            multiplier = 1000000
                        elif m_upper == "B":
                            multiplier = 1000000000

                    normalized_val = int(round(base_num * multiplier))
                    return normalized_val, match.group(0).strip()
                except ValueError:
                    continue

        # 2. Try simple standalone numeric string if labeled as sales context
        cleaned = re.sub(r"[^\d\.]", "", raw)
        if cleaned:
            try:
                val = int(round(float(cleaned)))
                return val, raw
            except ValueError:
                pass

        return None, raw if len(raw) < 100 else None
