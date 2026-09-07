"""Unit tests for ProductParser across multiple DOM and dynamic JSON layouts."""

from pathlib import Path
import pytest

from app.core.exceptions import ParserError
from app.extraction.parser import ProductParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "daraz"


@pytest.fixture
def parser():
    return ProductParser()


def test_parse_standard_product_page(parser: ProductParser):
    html = (FIXTURES_DIR / "product_page_standard.html").read_text(encoding="utf-8")
    url = "https://www.daraz.pk/products/redmi-note-13-8gb-256gb-i100101-s200201.html"

    product, fields_extracted, fields_missing, warnings = parser.parse(html, url=url)

    assert product.product_id == "100101"
    assert "Redmi Note 13" in product.title
    assert product.price == 45999.0
    assert product.original_price == 54999.0
    assert product.discount == 16.0
    assert product.brand == "Xiaomi"
    assert product.rating == 4.7
    assert product.review_count == 245
    assert product.sold_count == 1500
    assert product.seller_name == "Xiaomi Flagship Store"
    assert product.seller_id == "xiaomi-official-store"
    assert product.availability is True
    assert len(product.images) == 3  # Duplicate deduplicated
    assert product.images[0].is_primary is True
    assert "Snapdragon 685" in product.specifications.get("Processor", "")
    assert "108MP" in product.description

    assert "product_id" in fields_extracted
    assert "price" in fields_extracted
    assert "images" in fields_extracted


def test_parse_minimal_product_page(parser: ProductParser):
    html = (FIXTURES_DIR / "product_page_minimal.html").read_text(encoding="utf-8")
    url = "https://www.daraz.pk/products/cotton-tshirt-i200202.html"

    product, fields_extracted, fields_missing, warnings = parser.parse(html, url=url)

    assert product.product_id == "200202"
    assert "Cotton T-Shirt" in product.title
    assert product.price == 899.0
    assert product.original_price is None
    assert product.rating is None
    assert product.review_count == 0
    assert product.sold_count is None
    assert len(product.images) == 1

    assert "rating" in fields_missing
    assert "sold_count" in fields_missing


def test_parse_out_of_stock_product_page(parser: ProductParser):
    html = (FIXTURES_DIR / "product_page_out_of_stock.html").read_text(encoding="utf-8")
    url = "https://www.daraz.pk/products/keyboard-i300303.html"

    product, _, _, _ = parser.parse(html, url=url)
    assert product.product_id == "300303"
    assert product.availability is False


def test_parse_dynamic_json_product_page(parser: ProductParser):
    html = (FIXTURES_DIR / "product_page_dynamic_json.html").read_text(encoding="utf-8")
    url = "https://www.daraz.pk/products/sony-wh1000xm5-i400404.html"

    product, fields_extracted, fields_missing, warnings = parser.parse(html, url=url)

    assert product.product_id == "400404"
    assert "Sony WH-1000XM5" in product.title
    assert product.brand == "Sony"
    assert product.price == 78999.0
    assert product.original_price == 95000.0
    assert product.discount == 16.8
    assert product.rating == 4.9
    assert product.review_count == 312
    assert product.sold_count == 420
    assert product.seller_name == "Sony Official Flagship Store"
    assert len(product.images) == 2
    assert "Audio > Over-Ear Headphones" in product.category_name
    assert "Battery Life" in product.specifications


def test_parse_missing_title_raises_parser_error(parser: ProductParser):
    html = "<html><body><div>No product here</div></body></html>"
    url = "https://www.daraz.pk/products/invalid-item-i999999.html"

    with pytest.raises(ParserError):
        parser.parse(html, url=url)
