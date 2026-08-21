import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_headers():
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_dev_reset_endpoint(auth_headers):
    # First check data source status config
    cfg_res = client.get("/api/v1/data-sources/config/status", headers=auth_headers)
    assert cfg_res.status_code == 200
    cfg = cfg_res.json()["data"]
    assert "youtube" in cfg
    assert "mode" in cfg["youtube"]

    # Now call dev reset
    reset_res = client.post("/api/v1/dev/reset-data", headers=auth_headers)
    assert reset_res.status_code == 200
    assert reset_res.json()["data"]["reset"] is True
