import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_01_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_02_registration_validation_and_success():
    # Test invalid registration (password mismatch)
    res_mismatch = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test_qa@trendpulse.ai",
            "password": "Password123!",
            "confirm_password": "MismatchPassword!",
            "terms_accepted": True
        }
    )
    assert res_mismatch.status_code == 400

    # Test invalid registration (terms not accepted)
    res_terms = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test_qa@trendpulse.ai",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": False
        }
    )
    assert res_terms.status_code == 400

    # Test valid registration
    res_valid = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "QA Operator",
            "email": "qa_operator@trendpulse.ai",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True
        }
    )
    assert res_valid.status_code == 200
    data = res_valid.json()["data"]
    assert data["email"] == "qa_operator@trendpulse.ai"
    assert "verification_token" in data

    # Test duplicate registration rejection
    res_dup = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "QA Operator Duplicate",
            "email": "qa_operator@trendpulse.ai",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True
        }
    )
    assert res_dup.status_code == 409

def test_03_email_verification():
    # Register a new user to verify
    res_reg = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Verify Me",
            "email": "verify_me@trendpulse.ai",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True
        }
    )
    token = res_reg.json()["data"]["verification_token"]

    # Verify with invalid token
    res_inv = client.post("/api/v1/auth/verify-email", json={"token": "invalid_token_123"})
    assert res_inv.status_code == 400

    # Verify with valid token
    res_ver = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert res_ver.status_code == 200
    assert res_ver.json()["data"]["is_verified"] is True
    assert "access_token" in res_ver.json()["data"]

def test_04_auth_login_and_session():
    # Login with bad credentials
    res_bad = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "WrongPassword!"}
    )
    assert res_bad.status_code == 401

    # Login with valid demo credentials
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    assert res_login.status_code == 200
    token = res_login.json()["data"]["access_token"]
    assert token is not None

    # Get /me with valid token
    headers = {"Authorization": f"Bearer {token}"}
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["data"]["email"] == "demo@trendpulse.ai"

    # Reject /me with invalid token
    res_unauth = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer badtoken"})
    assert res_unauth.status_code == 401

def test_05_workspace_setup_and_retrieval():
    # Login as demo
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get workspace
    res_ws = client.get("/api/v1/workspace", headers=headers)
    assert res_ws.status_code == 200
    assert "id" in res_ws.json()["data"]

    # Setup / update workspace
    res_setup = client.post(
        "/api/v1/workspace/setup",
        headers=headers,
        json={
            "name": "Apex Global Intelligence",
            "industry": "Consumer Tech",
            "use_case": "Trend Arbitrage",
            "currency": "USD",
            "default_dashboard": "signals",
            "data_sources": ["tiktok", "daraz", "instagram"]
        }
    )
    assert res_setup.status_code == 200
    assert res_setup.json()["data"]["name"] == "Apex Global Intelligence"

def test_06_dashboard_endpoints():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # Summary default
    res_sum = client.get("/api/v1/dashboard/summary", headers=headers)
    assert res_sum.status_code == 200
    data = res_sum.json()["data"]
    assert len(data["metrics"]) >= 4
    assert len(data["top_surging"]) >= 1
    assert len(data["live_signals"]) >= 1

    # Trends with filter
    res_trends = client.get(
        "/api/v1/dashboard/trends?time_range=7d&category=Beauty%20%26%20Personal%20Care",
        headers=headers
    )
    assert res_trends.status_code == 200
    assert len(res_trends.json()["data"]) >= 5

def test_07_products_catalog_detail_and_comparison():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # List products
    res_list = client.get("/api/v1/products", headers=headers)
    assert res_list.status_code == 200
    products = res_list.json()["data"]
    assert len(products) >= 4

    # Search products
    res_search = client.get("/api/v1/products?search=Serum", headers=headers)
    assert res_search.status_code == 200
    assert any("Serum" in p["name"] for p in res_search.json()["data"])

    # Single product detail
    prod_id = products[0]["id"]
    res_detail = client.get(f"/api/v1/products/{prod_id}", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["data"]["id"] == prod_id

    # 404 for invalid product
    res_404 = client.get("/api/v1/products/non_existent_id", headers=headers)
    assert res_404.status_code == 404

    # Compare 2 products
    prod_ids = f"{products[0]['id']},{products[1]['id']}"
    res_comp = client.get(f"/api/v1/products/compare?ids={prod_ids}", headers=headers)
    assert res_comp.status_code == 200
    assert len(res_comp.json()["data"]) == 2

def test_08_watchlist_mutations():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # Get all products
    prods = client.get("/api/v1/products", headers=headers).json()["data"]
    target_id = prods[2]["id"]

    # Add to watchlist
    res_add = client.post(f"/api/v1/watchlist/{target_id}", headers=headers)
    assert res_add.status_code == 200

    # Verify present in watchlist
    res_wl = client.get("/api/v1/watchlist", headers=headers)
    assert res_wl.status_code == 200
    assert any(p["id"] == target_id for p in res_wl.json()["data"])

    # Remove from watchlist
    res_rem = client.delete(f"/api/v1/watchlist/{target_id}", headers=headers)
    assert res_rem.status_code == 200

    # Verify removed
    res_wl2 = client.get("/api/v1/watchlist", headers=headers)
    assert not any(p["id"] == target_id for p in res_wl2.json()["data"])

def test_09_categories_and_platforms():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # Categories
    res_cats = client.get("/api/v1/categories", headers=headers)
    assert res_cats.status_code == 200
    assert len(res_cats.json()["data"]) >= 4

    # Platforms
    res_plats = client.get("/api/v1/platforms", headers=headers)
    assert res_plats.status_code == 200
    assert len(res_plats.json()["data"]) >= 4

def test_10_alerts_and_notifications():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # Alerts list
    res_alerts = client.get("/api/v1/alerts", headers=headers)
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()["data"]
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    # Mark alert read
    res_read = client.post(f"/api/v1/alerts/{alert_id}/read", headers=headers)
    assert res_read.status_code == 200
    assert res_read.json()["data"]["is_read"] is True

    # Resolve alert
    res_res = client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=headers)
    assert res_res.status_code == 200
    assert res_res.json()["data"]["is_resolved"] is True

    # Notifications list
    res_notes = client.get("/api/v1/notifications", headers=headers)
    assert res_notes.status_code == 200
    notes = res_notes.json()["data"]
    assert len(notes) >= 1

    # Mark all read
    res_all_read = client.post("/api/v1/notifications/read-all", headers=headers)
    assert res_all_read.status_code == 200

def test_11_reports_and_generation():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # Generate report
    res_gen = client.post(
        "/api/v1/reports/generate",
        headers=headers,
        json={
            "title": "Automated QA Velocity Dossier",
            "template": "executive",
            "time_range": "30d",
            "category": "Beauty & Personal Care",
            "platforms": ["TikTok", "Daraz"],
            "sections": ["Executive Summary", "Key Findings"]
        }
    )
    assert res_gen.status_code == 200
    rep_id = res_gen.json()["data"]["id"]
    assert "Automated QA" in res_gen.json()["data"]["title"]

    # Retrieve report by ID
    res_rep = client.get(f"/api/v1/reports/{rep_id}", headers=headers)
    assert res_rep.status_code == 200
    assert res_rep.json()["data"]["id"] == rep_id

    # 404 for invalid report
    res_404 = client.get("/api/v1/reports/invalid_rep_999", headers=headers)
    assert res_404.status_code == 404

def test_12_data_sources_and_search():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # Data sources list
    res_ds = client.get("/api/v1/data-sources", headers=headers)
    assert res_ds.status_code == 200
    sources = res_ds.json()["data"]
    assert len(sources) >= 4

    # Disconnect & Reconnect
    res_disc = client.post("/api/v1/data-sources/youtube/disconnect", headers=headers)
    assert res_disc.status_code == 200
    assert res_disc.json()["data"]["status"] == "Disconnected"

    res_conn = client.post("/api/v1/data-sources/youtube/connect", headers=headers)
    assert res_conn.status_code == 200
    assert res_conn.json()["data"]["status"] == "Connected"

    # Global search
    res_search = client.get("/api/v1/search?q=Serum", headers=headers)
    assert res_search.status_code == 200
    assert len(res_search.json()["data"]["results"]) >= 1

def test_13_settings_management():
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    headers = {"Authorization": f"Bearer {res_login.json()['data']['access_token']}"}

    # Get settings
    res_set = client.get("/api/v1/settings", headers=headers)
    assert res_set.status_code == 200
    current_settings = res_set.json()["data"]

    # Update settings
    current_settings["company_name"] = "TrendPulse Global Labs"
    current_settings["ai_confidence_threshold"] = 88
    res_upd = client.put("/api/v1/settings", headers=headers, json=current_settings)
    assert res_upd.status_code == 200
    assert res_upd.json()["data"]["company_name"] == "TrendPulse Global Labs"
    assert res_upd.json()["data"]["ai_confidence_threshold"] == 88

def test_14_forgot_and_reset_password_flow():
    # Register dedicated user for reset flow
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Reset Test User",
            "email": "reset_user@trendpulse.ai",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True
        }
    )

    # Request reset token
    res_forgot = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset_user@trendpulse.ai"}
    )
    assert res_forgot.status_code == 200
    reset_token = res_forgot.json()["data"]["reset_token"]
    assert reset_token is not None

    # Reset with invalid token
    res_bad_reset = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "invalid_reset_token",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }
    )
    assert res_bad_reset.status_code == 400

    # Reset with valid token
    res_reset = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }
    )
    assert res_reset.status_code == 200

    # Verify login with new password
    res_new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset_user@trendpulse.ai", "password": "NewSecurePassword123!"}
    )
    assert res_new_login.status_code == 200
    assert "access_token" in res_new_login.json()["data"]
