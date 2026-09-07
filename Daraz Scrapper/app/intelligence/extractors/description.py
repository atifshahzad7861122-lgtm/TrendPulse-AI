"""Description extraction, HTML sanitization, and text normalization."""

import re
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, Comment, Tag


class DescriptionExtractor:
    """
    Extracts, sanitizes, and normalizes product descriptions.
    Strips scripts, styles, iframes, trackers, and malicious attributes while preserving formatting.
    Returns both description_html and description_text.
    """

    _DANGEROUS_TAGS = [
        "script",
        "style",
        "iframe",
        "embed",
        "object",
        "noscript",
        "svg",
        "form",
        "input",
        "button",
        "link",
        "meta",
    ]

    _ALLOWED_TAGS = {
        "p", "br", "ul", "ol", "li", "b", "strong", "i", "em", "u",
        "h1", "h2", "h3", "h4", "h5", "h6", "table", "thead", "tbody",
        "tr", "th", "td", "span", "div", "blockquote", "hr"
    }

    _ALLOWED_ATTRS = {"class", "id", "title"}

    @classmethod
    def sanitize_html(cls, html_content: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Sanitize HTML snippet and extract clean plain text.
        Returns (clean_html, clean_text).
        """
        if not html_content or not html_content.strip():
            return None, None

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Remove dangerous tags and comments
        for element in soup.find_all(string=lambda s: isinstance(s, Comment)):
            element.extract()

        for tag_name in cls._DANGEROUS_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 2. Clean attributes and remove non-allowed tags
        for tag in soup.find_all(True):
            if tag.name not in cls._ALLOWED_TAGS:
                tag.unwrap()
            else:
                # Remove event handlers (onclick, onload, etc.) and style attributes
                attrs_to_remove = [k for k in tag.attrs if k.startswith("on") or k not in cls._ALLOWED_ATTRS]
                for k in attrs_to_remove:
                    del tag.attrs[k]

        clean_html = str(soup).strip()
        clean_text = soup.get_text(separator=" ", strip=True)

        # Normalize excess whitespace in text
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

        if not clean_text or len(clean_text) < 5:
            return None, None

        return clean_html if clean_html else None, clean_text
