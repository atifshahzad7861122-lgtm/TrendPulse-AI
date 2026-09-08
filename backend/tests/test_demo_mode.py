import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings

@pytest.fixture
def client():
    return TestClient(app)

def test_demo_session_creation(client):
    # Test acquiring demo session
    settings.DEMO_MODE = True
    response = client.post("/api/v1/auth/demo-session")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["role"] == "demo"
    assert data["data"]["email"] == settings.DEMO_USER_EMAIL

def test_demo_user_read_access(client):
    settings.DEMO_MODE = True
    # Get demo token
    token_resp = client.post("/api/v1/auth/demo-session")
    token = token_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify GET /auth/me returns demo profile
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200, me_resp.text
    me_data = me_resp.json()["data"]
    assert me_data["role"] == "demo"
    assert me_data["email"] == settings.DEMO_USER_EMAIL

    # Verify GET /dashboard/summary works
    dash_resp = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dash_resp.status_code == 200, dash_resp.text

    # Verify GET /products works
    prod_resp = client.get("/api/v1/products", headers=headers)
    assert prod_resp.status_code == 200, prod_resp.text

    # Verify GET /market-intelligence/overview works
    intel_resp = client.get("/api/v1/market-intelligence/overview", headers=headers)
    assert intel_resp.status_code == 200, intel_resp.text

def test_demo_user_mutation_blocked_with_403(client):
    settings.DEMO_MODE = True
    token_resp = client.post("/api/v1/auth/demo-session")
    token = token_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try mutating settings -> 403 Forbidden
    put_resp = client.put("/api/v1/settings", json={"theme": "light"}, headers=headers)
    assert put_resp.status_code == 403, put_resp.text
    assert "Demo mode is read-only" in put_resp.json()["detail"]

    # Try starting scraper job -> 403 Forbidden
    job_resp = client.post("/api/v1/scraper/jobs/start", json={"marketplace": "daraz", "keyword": "test"}, headers=headers)
    assert job_resp.status_code == 403, job_resp.text
    assert "Demo mode is read-only" in job_resp.json()["detail"]

    # Try generating report -> 403 Forbidden
    rep_resp = client.post("/api/v1/reports/generate", json={"type": "market_summary"}, headers=headers)
    assert rep_resp.status_code == 403, rep_resp.text
    assert "Demo mode is read-only" in rep_resp.json()["detail"]

    # Try mutating user profile -> 403 Forbidden
    patch_resp = client.patch("/api/v1/auth/me", json={"full_name": "Hacked"}, headers=headers)
    assert patch_resp.status_code == 403, patch_resp.text
    assert "Demo mode is read-only" in patch_resp.json()["detail"]

def test_demo_mode_disabled_behavior(client):
    # When DEMO_MODE is False
    settings.DEMO_MODE = False
    try:
        # demo-session endpoint disabled
        resp = client.post("/api/v1/auth/demo-session")
        assert resp.status_code == 403

        # existing demo token is rejected
        settings.DEMO_MODE = True
        token_resp = client.post("/api/v1/auth/demo-session")
        token = token_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        settings.DEMO_MODE = False
        me_resp = client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 401
    finally:
        # Restore DEMO_MODE = True for hackathon
        settings.DEMO_MODE = True
