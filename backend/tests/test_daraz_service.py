import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.daraz_service import (
    DarazService, DarazException, DarazAuthError, DarazRateLimitError
)
from backend.app.schemas.daraz import DarazProductItem, DarazProductDetails
from backend.app.core.config import settings

@pytest.fixture(autouse=True)
def ensure_in_memory_backend():
    original = settings.DATA_BACKEND
    settings.DATA_BACKEND = "in_memory"
    yield
    settings.DATA_BACKEND = original

from backend.app.api.deps import get_daraz_service, get_marketplace_product_repository
from backend.app.repositories.in_memory import InMemoryMarketplaceProductRepository

@pytest.fixture
def client():
    mock_repo = InMemoryMarketplaceProductRepository(storage_file=":memory:")
    svc = DarazService(marketplace_repo=mock_repo)
    app.dependency_overrides[get_marketplace_product_repository] = lambda: mock_repo
    app.dependency_overrides[get_daraz_service] = lambda: svc
    c = TestClient(app)
    yield c
    app.dependency_overrides.pop(get_marketplace_product_repository, None)
    app.dependency_overrides.pop(get_daraz_service, None)

@pytest.fixture
def mock_search_payload():
    return {
        "status": "success",
        "data": {
            "products": [
                {
                    "name": "Dell Inspiron 15 Core i7 12th Gen Laptop",
                    "nid": "837147106",
                    "itemId": "837147106",
                    "image": "https://pk-live-21.slatic.net/kf/S448bc8cb14e14b6bba2e702c28fd0e5dw.jpg",
                    "price": "118499.99",
                    "originalPrice": "180000",
                    "discount": "34% Off",
                    "ratingScore": "4.8",
                    "review": "25",
                    "location": "Punjab",
                    "sellerName": "TechStore PK",
                    "sellerId": "6005033052228",
                    "brandName": "Dell",
                    "categories": [57],
                    "inStock": True,
                    "itemSoldCntShow": "42 sold",
                    "sku": "DELL-15-837147106",
                    "itemUrl": "//www.daraz.pk/products/dell-inspiron-15-i837147106.html"
                }
            ]
        }
    }

@pytest.fixture
def mock_live_details_payload():
    return {
        "status": "success",
        "data": {
            "module": {
                "product": {
                    "title": "Petiwala – Pack of 10 Jet Black Retractable Ball Point Pen (Blue)",
                    "desc": "<ul><li>Ideal for your everyday writing needs</li></ul>",
                    "highlights": "<ul><li>Pack of 10 ball points (Blue)</li><li>Brass tip 0.8mm</li></ul>",
                    "link": "https://www.daraz.pk/products/petiwala-pack-of-10-i265958567.html",
                    "brand": {
                        "name": "No Brand"
                    },
                    "rating": {
                        "score": 4.9,
                        "total": 11
                    }
                },
                "seller": {
                    "sellerId": "1107783",
                    "name": "Petiwala Stationary Mart",
                    "url": "//www.daraz.pk/shop/petiwala-stationary-mart/",
                    "positiveSellerRating": {"value": "98%"},
                    "shipOnTime": {"value": "100%"},
                    "chatResponsiveRate": {"labelText": "99%"}
                },
                "skuInfos": {
                    "0": {
                        "price": {
                            "salePrice": {"value": 250, "text": "Rs. 250"},
                            "originalPrice": {"value": 300, "text": "Rs. 300"},
                            "discount": "-17%"
                        },
                        "image": "https://static-01.daraz.pk/p/77d62d9e.jpg"
                    }
                },
                "skuGalleries": {
                    "0": [
                        {"src": "//static-01.daraz.pk/p/e169b17d.jpg", "type": "img"},
                        {"src": "https://static-01.daraz.pk/p/77d62d9e.jpg", "type": "img"}
                    ]
                },
                "specifications": {
                    "1481857642": {
                        "boxContent": "1 X 10 Ball Point Pens",
                        "features": {
                            "Brand": "No Brand",
                            "Model": "M-910 BK",
                            "Number of Pieces in Set": "10"
                        }
                    }
                },
                "warranties": {
                    "1481857642": [
                        {"title": "14 days easy return", "type": "returnPolicy14"}
                    ]
                },
                "tracking": {
                    "pdt_name": "Petiwala Pen",
                    "pdt_price": "Rs. 250",
                    "pdt_category": ["Stationery & Craft", "Pens"]
                }
            }
        }
    }

def test_daraz_product_normalization(mock_search_payload):
    service = DarazService(api_key="pmx_test_key")
    raw_item = mock_search_payload["data"]["products"][0]
    normalized = service.normalize_search_product(raw_item)

    assert isinstance(normalized, DarazProductItem)
    assert normalized.platform == "daraz"
    assert normalized.product_id == "837147106"
    assert normalized.name == "Dell Inspiron 15 Core i7 12th Gen Laptop"
    assert normalized.price == 118499.99
    assert normalized.original_price == 180000.0
    assert normalized.discount == 34.0
    assert normalized.currency == "PKR"
    assert normalized.rating == 4.8
    assert normalized.review_count == 25
    assert normalized.seller_name == "TechStore PK"
    assert normalized.seller_id == "6005033052228"
    assert normalized.brand == "Dell"
    assert normalized.in_stock is True
    assert normalized.location == "Punjab"
    assert normalized.sold_count == 42
    assert normalized.source == "daraz.pk"
    assert normalized.product_url == "https://www.daraz.pk/products/dell-inspiron-15-i837147106.html"
    assert normalized.image_url.startswith("https://")

def test_daraz_live_structure_normalization(mock_live_details_payload):
    service = DarazService(api_key="pmx_test_key")
    details = service.normalize_product_details(mock_live_details_payload, item_id="265958567")

    assert isinstance(details, DarazProductDetails)
    assert details.platform == "daraz"
    assert details.product_id == "265958567"
    assert "Petiwala" in details.name
    assert details.price == 250.0
    assert details.original_price == 300.0
    assert details.currency == "PKR"
    assert details.rating == 4.9
    assert details.review_count == 11
    assert details.main_image == "https://static-01.daraz.pk/p/e169b17d.jpg"
    assert len(details.images) == 2
    assert details.seller is not None
    assert details.seller.name == "Petiwala Stationary Mart"
    assert details.seller.positive_seller_rating == "98%"
    assert details.seller.seller_url == "https://www.daraz.pk/shop/petiwala-stationary-mart/"
    assert "14 days easy return" in (details.warranty or "")
    assert details.specifications.get("Box Content") == "1 X 10 Ball Point Pens"
    assert details.specifications.get("Model") == "M-910 BK"
    assert len(details.highlights) == 2
    assert "Pack of 10" in details.highlights[0]

def test_daraz_missing_price_and_image_fallbacks():
    service = DarazService(api_key="pmx_test_key")
    sparse_payload = {
        "status": "success",
        "data": {
            "module": {
                "title": "Sparse Product Item",
                "specifications": {
                    "color": "Red",
                    "nested": {"size": "Large"}
                }
            }
        }
    }
    details = service.normalize_product_details(sparse_payload, item_id="999")
    assert details.name == "Sparse Product Item"
    assert details.price == 0.0
    assert details.main_image is None
    assert len(details.images) == 0
    assert details.specifications.get("color") == "Red"
    assert details.specifications.get("size") == "Large"

def test_daraz_search_with_cache(mock_search_payload):
    service = DarazService(api_key="pmx_test_key")
    
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_search_payload
        mock_post.return_value = mock_resp

        # First call: hits network
        res1 = service.search_products(query="laptop", page=1)
        assert res1.total_products == 1
        assert mock_post.call_count == 1

        # Second call: hits in-memory TTL cache (no network)
        res2 = service.search_products(query="laptop", page=1)
        assert res2.total_products == 1
        assert mock_post.call_count == 1  # Still 1 because cached

def test_daraz_auth_error_handling():
    service = DarazService(api_key="pmx_invalid_key")
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        with pytest.raises(DarazAuthError):
            service.search_products(query="laptop")

def test_daraz_rate_limit_error_handling():
    service = DarazService(api_key="pmx_test_key", max_retries=2)
    with patch("requests.post") as mock_post, patch("time.sleep"):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limited"
        mock_post.return_value = mock_resp

        with pytest.raises(DarazRateLimitError):
            service.search_products(query="laptop")

def test_daraz_search_endpoint(client, mock_search_payload):
    from backend.app.api.deps import get_daraz_service
    test_service = DarazService()
    app.dependency_overrides[get_daraz_service] = lambda: test_service
    try:
        with patch.object(test_service, "_execute_request", return_value=mock_search_payload):
            resp = client.get("/api/v1/platforms/daraz/products/search?q=laptop")
            assert resp.status_code == 200
            json_data = resp.json()
            assert json_data["success"] is True
            assert "data" in json_data
            assert json_data["data"]["query"] == "laptop"
            assert len(json_data["data"]["products"]) == 1
            prod = json_data["data"]["products"][0]
            assert prod["platform"] == "daraz"
            assert prod["currency"] == "PKR"
            assert prod["price"] == 118499.99
    finally:
        app.dependency_overrides.clear()



def test_daraz_details_endpoint(client, mock_live_details_payload):
    from backend.app.api.deps import get_daraz_service
    test_service = DarazService()
    app.dependency_overrides[get_daraz_service] = lambda: test_service
    try:
        with patch.object(test_service, "_execute_request", return_value=mock_live_details_payload):
            resp = client.get("/api/v1/platforms/daraz/products/265958567")
            assert resp.status_code == 200
            json_data = resp.json()
            assert json_data["success"] is True
            assert json_data["data"]["product_id"] == "265958567"
            assert "Petiwala" in json_data["data"]["name"]
            assert json_data["data"]["price"] == 250.0
    finally:
        app.dependency_overrides.clear()

def test_daraz_categories_endpoint(client):
    from backend.app.api.deps import get_daraz_service
    mock_cat_payload = {
        "status": "success",
        "data": {
            "categories": [
                {
                    "id": "812485",
                    "categoryName": "Electronic Accessories",
                    "categoryIcon": "ic-cat-ElectronicAcc",
                    "level2TabList": [
                        {"categoryId": "9536", "categoryName": "Mobile Accessories"}
                    ]
                }
            ]
        }
    }
    test_service = DarazService()
    app.dependency_overrides[get_daraz_service] = lambda: test_service
    try:
        with patch.object(test_service, "_execute_request", return_value=mock_cat_payload):
            resp = client.get("/api/v1/platforms/daraz/categories")
            assert resp.status_code == 200
            json_data = resp.json()
            assert json_data["success"] is True
            assert len(json_data["data"]) == 1
            assert json_data["data"][0]["id"] == "812485"
            assert json_data["data"][0]["name"] == "Electronic Accessories"
            assert len(json_data["data"][0]["subcategories"]) == 1
    finally:
        app.dependency_overrides.clear()


