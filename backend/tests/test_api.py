import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_auth_flow():
    # 1. Register
    reg_payload = {
        "full_name": "Test Engineer",
        "email": "tester@trendpulse.ai",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()["data"]
    token = reg_data["verification_token"]
    assert token is not None

    # 2. Verify Email
    ver_resp = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert ver_resp.status_code == 200
    assert ver_resp.json()["data"]["is_verified"] is True

    # 3. Login
    login_resp = client.post("/api/v1/auth/login", json={"email": "tester@trendpulse.ai", "password": "Password123!"})
    assert login_resp.status_code == 200
    access_token = login_resp.json()["data"]["access_token"]
    assert access_token is not None

    # 4. Get Me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["email"] == "tester@trendpulse.ai"

def test_workspace_onboarding():
    login_resp = client.post("/api/v1/auth/login", json={"email": "demo@trendpulse.ai", "password": "Password123!"})
    access_token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    setup_payload = {
        "name": "Global Trend Labs",
        "industry": "Consumer Electronics",
        "use_case": "Dropshipping & Arbitrage",
        "currency": "USD",
        "default_dashboard": "signals",
        "data_sources": ["tiktok", "daraz"]
    }
    resp = client.post("/api/v1/workspace/setup", json=setup_payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Global Trend Labs"

def test_dashboard_and_products():
    login_resp = client.post("/api/v1/auth/login", json={"email": "demo@trendpulse.ai", "password": "Password123!"})
    access_token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Summary
    dash_resp = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dash_resp.status_code == 200
    assert len(dash_resp.json()["data"]["metrics"]) > 0

    # Trends
    trends_resp = client.get("/api/v1/dashboard/trends?time_range=7d", headers=headers)
    assert trends_resp.status_code == 200
    assert len(trends_resp.json()["data"]) > 0

    # Products List
    prods_resp = client.get("/api/v1/products", headers=headers)
    assert prods_resp.status_code == 200
    prods = prods_resp.json()["data"]
    assert len(prods) > 0
    first_id = prods[0]["id"]

    # Product Detail
    prod_resp = client.get(f"/api/v1/products/{first_id}", headers=headers)
    assert prod_resp.status_code == 200
    assert prod_resp.json()["data"]["id"] == first_id

    # Watchlist Add & Remove
    wl_add = client.post(f"/api/v1/watchlist/{first_id}", headers=headers)
    assert wl_add.status_code == 200
    wl_list = client.get("/api/v1/watchlist", headers=headers)
    assert wl_list.status_code == 200
    assert any(p["id"] == first_id for p in wl_list.json()["data"])

def test_reports_and_sources():
    login_resp = client.post("/api/v1/auth/login", json={"email": "demo@trendpulse.ai", "password": "Password123!"})
    access_token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Reports list
    rep_list = client.get("/api/v1/reports", headers=headers)
    assert rep_list.status_code == 200

    # Generate report
    gen_payload = {
        "title": "Beauty Market Peak Analysis",
        "template": "velocity_surge",
        "time_range": "7d",
        "category": "Beauty & Personal Care",
        "platforms": ["TikTok", "Instagram"]
    }
    gen_resp = client.post("/api/v1/reports/generate", json=gen_payload, headers=headers)
    assert gen_resp.status_code == 200
    rep_id = gen_resp.json()["data"]["id"]

    # Get Report Detail
    detail_resp = client.get(f"/api/v1/reports/{rep_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["id"] == rep_id

    # Data Sources
    ds_list = client.get("/api/v1/data-sources", headers=headers)
    assert ds_list.status_code == 200
    assert len(ds_list.json()["data"]) > 0

    # Connect YouTube
    conn_resp = client.post("/api/v1/data-sources/youtube/connect", headers=headers)
    assert conn_resp.status_code == 200
    assert conn_resp.json()["data"]["status"] == "Connected"

def test_settings_and_search():
    login_resp = client.post("/api/v1/auth/login", json={"email": "demo@trendpulse.ai", "password": "Password123!"})
    access_token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Search
    search_resp = client.get("/api/v1/search?q=hydro", headers=headers)
    assert search_resp.status_code == 200
    assert search_resp.json()["data"]["total_results"] >= 1

    # Settings get & update
    st_get = client.get("/api/v1/settings", headers=headers)
    assert st_get.status_code == 200
    st_data = st_get.json()["data"]
    st_data["company_name"] = "Apex Intelligence Labs V2"
    st_put = client.put("/api/v1/settings", json=st_data, headers=headers)
    assert st_put.status_code == 200
    assert st_put.json()["data"]["company_name"] == "Apex Intelligence Labs V2"
