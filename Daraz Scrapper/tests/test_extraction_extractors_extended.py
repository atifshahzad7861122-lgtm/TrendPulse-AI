"""Extended unit tests for Title, Availability, Variant, and multi-source fallbacks."""

from bs4 import BeautifulSoup
import pytest

from app.extraction.extractors.availability import AvailabilityExtractor
from app.extraction.extractors.title import TitleExtractor
from app.extraction.extractors.variant import VariantExtractor
from app.extraction.confidence import ExtractionSource


def test_title_extractor_normalization():
    ext = TitleExtractor()
    raw = "  Apple&#39;s&nbsp;iPhone&nbsp;15&nbsp;Pro&nbsp;Max&amp;Case   "
    clean = ext.normalize_title(raw)
    assert clean == "Apple's iPhone 15 Pro Max&Case"


def test_title_extractor_jsonld():
    soup = BeautifulSoup("<html><body><h1>DOM Title</h1></body></html>", "html.parser")
    json_ld = {"name": "JSON-LD Title"}
    ext = TitleExtractor()
    title, source = ext.extract(soup, json_ld=json_ld)

    assert title == "JSON-LD Title"
    assert source == ExtractionSource.JSON_LD


def test_title_extractor_opengraph():
    html = """
    <html>
    <head>
        <meta property="og:title" content="OpenGraph Super Product" />
    </head>
    <body></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    ext = TitleExtractor()
    title, source = ext.extract(soup)

    assert title == "OpenGraph Super Product"
    assert source == ExtractionSource.OPENGRAPH


def test_availability_extractor_in_stock_and_out_of_stock():
    ext = AvailabilityExtractor()

    # Out of stock DOM
    html_out = "<html><body><button class='out-of-stock'>Sold Out</button></body></html>"
    soup_out = BeautifulSoup(html_out, "html.parser")
    is_in, status_str, _ = ext.extract(soup_out)
    assert is_in is False
    assert status_str == "out_of_stock"

    # In stock default
    html_in = "<html><body><button class='pdp-button_color_orange'>Buy Now</button></body></html>"
    soup_in = BeautifulSoup(html_in, "html.parser")
    is_in, status_str, _ = ext.extract(soup_in)
    assert is_in is True
    assert status_str == "in_stock"


def test_variant_extractor_structured():
    raw_json = {
        "fields": {
            "skuInfos": [
                {
                    "skuId": "sku_101",
                    "name": "Black 128GB",
                    "price": {"value": 50000},
                    "properties": {"color": "Black", "size": "128GB"},
                    "avail": True,
                },
                {
                    "skuId": "sku_102",
                    "name": "White 256GB",
                    "price": {"value": 60000},
                    "properties": {"color": "White", "size": "256GB"},
                    "avail": False,
                },
            ]
        }
    }
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    ext = VariantExtractor()
    variants, source = ext.extract(soup, raw_json=raw_json)

    assert len(variants) == 2
    assert variants[0].sku_id == "sku_101"
    assert variants[0].color == "Black"
    assert variants[0].available is True
    assert variants[1].sku_id == "sku_102"
    assert variants[1].available is False
    assert source == ExtractionSource.STRUCTURED_DATA
