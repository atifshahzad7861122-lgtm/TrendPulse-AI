"""Rating score and review count normalization."""

import re
from typing import Optional, Tuple


class RatingReviewExtractor:
    """
    Normalizes rating scores (0.0 to 5.0) and review counts (1.2K, 500+, 1,234).
    Correctly distinguishes between star ratings (e.g. 4.7 out of 5) and review counts (e.g. 1,420 reviews).
    """

    @classmethod
    def extract_rating(cls, val: Optional[any]) -> Optional[float]:
        """Normalize rating into float between 0.0 and 5.0."""
        if val is None:
            return None

        if isinstance(val, (int, float)):
            score = float(val)
            return round(score, 2) if 0.0 <= score <= 5.0 else None

        text = str(val).strip()
        if not text:
            return None

        # Pattern: "4.7 out of 5 stars", "4.7 / 5", "Rating: 4.5", "4.8"
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:out of|\/|\s*stars?)?\s*(?:5)?", text, re.IGNORECASE)
        if m:
            try:
                score = float(m.group(1))
                if 0.0 <= score <= 5.0:
                    return round(score, 2)
            except ValueError:
                pass

        return None

    @classmethod
    def extract_count(cls, val: Optional[any]) -> int:
        """Normalize review / rating count into positive integer."""
        if val is None:
            return 0

        if isinstance(val, (int, float)):
            return max(0, int(val))

        text = str(val).strip()
        if not text:
            return 0

        # Pattern: 1.2K reviews, 500+ ratings, (1,234), 10K+
        m = re.search(r"([\d\.,]+)\s*([kKmMbB])?\+?", text)
        if m:
            num_str = m.group(1).replace(",", "")
            multiplier_str = m.group(2)
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
                return max(0, int(round(base_num * multiplier)))
            except ValueError:
                pass

        return 0
