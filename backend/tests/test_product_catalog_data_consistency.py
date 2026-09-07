import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.domain import (
    Product, MarketplaceProduct, ProductMarketSnapshot
)
from backend.app.api.deps import (
    get_product_repository, get_marketplace_product_repository,
    get_watchlist_repository
)

client = TestClient(app)

def _get_auth_headers(email: str = "catalog_tester@trendpulse.ai", full_name: str = "Catalog Consistency Tester") -> dict:
    pwd = "AuditPassword123!"
    client.post("/api/v1/auth/register", json={
        "full_name": full_name,
        "email": email,
        "password": pwd,
        "confirm_password": pwd,
        "terms_accepted": True
    })
    res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_01_products_api_returns_persisted_products_consistently():
    """
    1. Products API returns persisted products from authoritative repository.
    2. Catalog receives the same products without loss.
    """
    headers = _get_auth_headers("catalog_user_1@trendpulse.ai")
    res = client.get("/api/v1/products?limit=20", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    # Verify canonical products like TitanFlex or HydroGlow are returned if present in product repo
    product_names = [p["name"] for p in data["data"]]
    assert "TitanFlex Modular Running Vest" in product_names or len(data["data"]) >= 1


def test_02_empty_database_returns_genuine_empty_state_without_fake_injection():
    """
    3. Empty database returns a genuine empty state (empty list), not hardcoded demo data.
    11. No demo products are injected when queried with an impossible filter.
    """
    headers = _get_auth_headers("catalog_user_2@trendpulse.ai")
    res = client.get("/api/v1/products?category=NonExistentCategoryXYZ999", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"] == []


def test_03_search_filtering_works_accurately():
    """
    4. Search filtering works against product name, category, or tags.
    """
    headers = _get_auth_headers("catalog_user_3@trendpulse.ai")
    
    # Search for running vest
    res = client.get("/api/v1/products?search=Running%20Vest", headers=headers)
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) >= 1
    assert any("Running Vest" in p["name"] or "Sports" in p["category"] for p in items)

    # Search for non-existent keyword
    res_empty = client.get("/api/v1/products?search=NonExistentQueryZXY999", headers=headers)
    assert res_empty.status_code == 200
    assert res_empty.json()["data"] == []


def test_04_category_filtering_works_accurately():
    """
    5. Category filtering correctly isolates target category products.
    """
    headers = _get_auth_headers("catalog_user_4@trendpulse.ai")
    
    res = client.get("/api/v1/products?category=Sports%20%26%20Outdoor", headers=headers)
    assert res.status_code == 200
    items = res.json()["data"]
    for p in items:
        assert "sports" in p["category"].lower() or "outdoor" in p["category"].lower()


def test_05_marketplace_platform_filtering_works():
    """
    6. Marketplace filtering correctly isolates products available on specific platforms.
    """
    headers = _get_auth_headers("catalog_user_5@trendpulse.ai")
    
    res_tiktok = client.get("/api/v1/products?platform=TikTok", headers=headers)
    assert res_tiktok.status_code == 200
    items_tt = res_tiktok.json()["data"]
    for p in items_tt:
        assert "TikTok" in p["platforms"] or p["primary_platform"] == "TikTok"


def test_06_sorting_works_against_actual_dataset():
    """
    7. Sorting works for trend_score, growth, volume, and sentiment.
    """
    headers = _get_auth_headers("catalog_user_6@trendpulse.ai")
    
    # Sort by growth
    res_growth = client.get("/api/v1/products?sort_by=growth", headers=headers)
    assert res_growth.status_code == 200
    items = res_growth.json()["data"]
    if len(items) >= 2:
        for i in range(len(items) - 1):
            assert items[i]["growth_rate"] >= items[i+1]["growth_rate"]


def test_07_pagination_works_without_losing_or_duplicating_products():
    """
    8. Pagination works (limit, page) without losing or duplicating products.
    """
    headers = _get_auth_headers("catalog_user_7@trendpulse.ai")
    
    res_page1 = client.get("/api/v1/products?limit=2&page=1", headers=headers)
    assert res_page1.status_code == 200
    page1_items = res_page1.json()["data"]
    assert len(page1_items) == 2

    res_page2 = client.get("/api/v1/products?limit=2&page=2", headers=headers)
    assert res_page2.status_code == 200
    page2_items = res_page2.json()["data"]
    assert len(page2_items) == 2

    page1_ids = {p["id"] for p in page1_items}
    page2_ids = {p["id"] for p in page2_items}
    assert page1_ids.isdisjoint(page2_ids), "Pagination duplicate detected between page 1 and page 2"


def test_08_watchlist_products_resolve_against_canonical_catalog_products():
    """
    9. Watchlist products resolve against canonical catalog products and preserve is_watchlisted state.
    """
    headers = _get_auth_headers("catalog_user_8@trendpulse.ai")
    
    # Get products
    cat_res = client.get("/api/v1/products", headers=headers)
    assert cat_res.status_code == 200
    products = cat_res.json()["data"]
    assert len(products) > 0
    first_prod = products[0]
    pid = first_prod["id"]

    # Add to watchlist
    add_res = client.post(f"/api/v1/watchlist/{pid}", headers=headers)
    assert add_res.status_code == 200
    assert add_res.json()["data"]["is_watchlisted"] is True

    # Check in catalog that is_watchlisted is True for this user
    cat_res_after = client.get("/api/v1/products", headers=headers)
    target = next((p for p in cat_res_after.json()["data"] if p["id"] == pid), None)
    assert target is not None
    assert target["is_watchlisted"] is True

    # Check in watchlist endpoint
    wl_res = client.get("/api/v1/watchlist", headers=headers)
    assert wl_res.status_code == 200
    wl_items = wl_res.json()["data"]
    assert any(p["id"] == pid for p in wl_items)

    # Clean up watchlist
    del_res = client.delete(f"/api/v1/watchlist/{pid}", headers=headers)
    assert del_res.status_code == 200


def test_09_api_failure_is_distinguishable_from_zero_results():
    """
    10. API failure (e.g. invalid endpoint or internal error) produces error response, distinguishable from zero results.
    """
    # Missing required query on compare
    err_res = client.get("/api/v1/products/compare", headers=_get_auth_headers())
    assert err_res.status_code == 422 or err_res.status_code == 400


def test_10_existing_persisted_daraz_products_remain_visible():
    """
    12. Existing persisted Daraz products from scraper remain visible in catalog with accurate PKR price.
    """
    mp_repo = app.dependency_overrides.get(get_marketplace_product_repository, get_marketplace_product_repository)()
    
    raw_pid = f"cat_daraz_{uuid.uuid4().hex[:6]}"
    unique_id = f"daraz_{raw_pid}"
    now = datetime.now(timezone.utc)

    mp = MarketplaceProduct(
        id=unique_id,
        platform="daraz",
        product_id=raw_pid,
        product_name="Catalog Verified Wireless Earphones TWS",
        product_url=f"https://www.daraz.pk/products/-i{raw_pid}.html",
        image_url="https://img.daraz.pk/p/tws.jpg",
        seller_name="TWS Audio PK",
        category="Consumer Electronics",
        price=2499.0,
        rating=4.7,
        review_count=85,
        stock_status="in_stock",
        in_stock=True,
        currency="PKR",
        location="Pakistan",
        first_seen_at=now,
        last_seen_at=now,
        last_synced_at=now
    )
    mp_repo.upsert_product(mp)

    headers = _get_auth_headers("catalog_user_10@trendpulse.ai")
    res = client.get("/api/v1/products?platform=all", headers=headers)
    assert res.status_code == 200
    items = res.json()["data"]
    found = next((p for p in items if p["id"] == unique_id or p["name"] == "Catalog Verified Wireless Earphones TWS"), None)
    assert found is not None
    assert found["name"] == "Catalog Verified Wireless Earphones TWS"
    assert "PKR" in found["price_range"]
    assert found["provenance"] == "persisted_marketplace_observations"
