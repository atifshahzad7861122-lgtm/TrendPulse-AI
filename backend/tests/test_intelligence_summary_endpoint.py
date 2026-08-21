import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_intelligence_summary_endpoint():
    # Login as demo user
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@trendpulse.ai", "password": "Password123!"}
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/dev/intelligence/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["environment"] == "development"
    assert data["total_products"] > 0
    assert "metrics_summary" in data
    assert "trend_score" in data["metrics_summary"]
    assert "percentiles" in data["metrics_summary"]["trend_score"]
    assert "p50" in data["metrics_summary"]["trend_score"]["percentiles"]
    assert "prediction_intelligence" in data
    assert data["version_metadata"]["scoring_version"] == "2.4.0"
    assert data["version_metadata"]["calibration_status"] == "CALIBRATED_PHASE_2D"
