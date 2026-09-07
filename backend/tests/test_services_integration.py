import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_headers():
    # Login as demo user
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_dynamic_dashboard_summary(auth_headers):
    # 7d
    res_7d = client.get("/api/v1/dashboard/summary?time_range=7d", headers=auth_headers)
    assert res_7d.status_code == 200
    data_7d = res_7d.json()["data"]
    assert len(data_7d["metrics"]) == 4
    assert len(data_7d["live_signals"]) > 0

    # 30d
    res_30d = client.get("/api/v1/dashboard/summary?time_range=30d", headers=auth_headers)
    assert res_30d.status_code == 200
    data_30d = res_30d.json()["data"]
    assert len(data_30d["metrics"][0]["subtext"]) > 0

def test_dynamic_dashboard_trends(auth_headers):
    res = client.get("/api/v1/dashboard/trends?time_range=7d", headers=auth_headers)
    assert res.status_code == 200
    points = res.json()["data"]
    assert len(points) == 8  # 7 days + today

def test_product_intelligence_listing(auth_headers):
    res = client.get("/api/v1/products?sort_by=trend_score", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) > 0
    # Verified that trend_score is dynamically computed
    assert items[0]["trend_score"] >= 80.0
    assert items[0]["velocity_label"] in ["Explosive", "Breakout", "Surging", "Steady"]

def test_product_comparison_service(auth_headers):
    res = client.get("/api/v1/products/compare?ids=prod_01,prod_02", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) == 2
    assert items[0]["id"] == "prod_01"
    assert items[1]["id"] == "prod_02"

def test_dynamic_categories_service(auth_headers):
    res = client.get("/api/v1/categories", headers=auth_headers)
    assert res.status_code == 200
    cats = res.json()["data"]
    assert len(cats) >= 4
    # Check that product count is dynamically aggregated
    beauty = next((c for c in cats if "Beauty" in c["name"]), None)
    assert beauty is not None
    assert beauty["product_count"] > 0
    assert beauty["avg_trend_score"] > 0

def test_dynamic_platforms_service(auth_headers):
    res = client.get("/api/v1/platforms", headers=auth_headers)
    assert res.status_code == 200
    platforms = res.json()["data"]
    assert len(platforms) >= 4
    tiktok = next((p for p in platforms if p["name"] == "TikTok"), None)
    assert tiktok is not None
    assert tiktok["total_signals"] >= 0

def test_report_generation_and_export(auth_headers):
    gen_payload = {
        "title": "Q3 Consumer Intelligence Dossier",
        "template": "executive",
        "time_range": "30d",
        "category": "Beauty & Personal Care",
        "platforms": ["TikTok", "Instagram"]
    }
    gen_res = client.post("/api/v1/reports/generate", json=gen_payload, headers=auth_headers)
    assert gen_res.status_code == 200
    rep = gen_res.json()["data"]
    assert rep["title"] == "Q3 Consumer Intelligence Dossier"
    assert len(rep["key_findings"]) >= 2

    # Test JSON export
    export_json = client.get(f"/api/v1/reports/{rep['id']}/export?format=json")
    assert export_json.status_code == 200
    assert export_json.json()["report_id"] == rep["id"]

    # Test CSV export
    export_csv = client.get(f"/api/v1/reports/{rep['id']}/export?format=csv")
    assert export_csv.status_code == 200
    assert "Report ID,Title" in export_csv.text
    assert rep["id"] in export_csv.text

def test_global_search_service(auth_headers):
    res = client.get("/api/v1/search?q=HydroGlow", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_results"] > 0
    assert any(r["title"] == "HydroGlow Thermal Lip Serum" for r in data["results"])

def test_watchlist_service_lifecycle(auth_headers):
    # Add product 04 to watchlist
    add_res = client.post("/api/v1/watchlist/prod_04", headers=auth_headers)
    assert add_res.status_code == 200
    assert add_res.json()["data"]["is_watchlisted"] is True

    # Check watchlist list
    wl_res = client.get("/api/v1/watchlist", headers=auth_headers)
    assert wl_res.status_code == 200
    items = wl_res.json()["data"]
    assert any(p["id"] == "prod_04" for p in items)

    # Remove product 04 from watchlist
    del_res = client.delete("/api/v1/watchlist/prod_04", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["data"]["is_watchlisted"] is False

def test_data_sources_sync_all(auth_headers):
    res = client.post("/api/v1/data-sources/sync-all", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "total_records" in data
    assert data["total_records"] >= 0
