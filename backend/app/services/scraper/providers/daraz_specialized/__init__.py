"""Daraz Specialized Scraper Provider Package."""
from .engine import DarazSpecializedScraperEngine
from .challenge import detect_challenge, handle_challenge_if_present
from .extractors.catalog_parser import parse_page_data_json, extract_products_from_json, parse_dom_item
from .extractors.product_parser import extract_product_details
from .extractors.review_parser import extract_product_reviews
from .extractors.variations_parser import extract_variations

__all__ = [
    "DarazSpecializedScraperEngine",
    "detect_challenge",
    "handle_challenge_if_present",
    "parse_page_data_json",
    "extract_products_from_json",
    "parse_dom_item",
    "extract_product_details",
    "extract_product_reviews",
    "extract_variations",
]
