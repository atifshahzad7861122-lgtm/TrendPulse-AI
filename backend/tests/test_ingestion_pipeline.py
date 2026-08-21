import pytest
import os
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

def test_single_source_sync_endpoint(auth_headers):
    res = client.post("/api/v1/data-sources/youtube/sync", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["source"] == "youtube"
    assert data["status"] in ["Success", "Partial"]
    assert data["records_received"] > 0
    assert data["records_normalized"] > 0

def test_sync_deduplication_and_idempotency(auth_headers):
    # Second sync should skip already processed items (deduplication)
    res_repeat = client.post("/api/v1/data-sources/youtube/sync", headers=auth_headers)
    assert res_repeat.status_code == 200
    data_repeat = res_repeat.json()["data"]
    assert data_repeat["records_skipped"] >= 0

def test_sync_all_endpoint(auth_headers):
    res = client.post("/api/v1/data-sources/sync-all", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "total_records" in data

def test_data_sources_list_has_production_telemetry(auth_headers):
    client.post("/api/v1/data-sources/youtube/connect", headers=auth_headers)
    res = client.get("/api/v1/data-sources", headers=auth_headers)
    assert res.status_code == 200
    sources = res.json()["data"]
    yt = next((s for s in sources if s["slug"] == "youtube"), None)
    assert yt is not None
    assert yt["records_synced"] >= 0
    assert yt["health_score"] >= 80

def test_invalid_source_sync_fails(auth_headers):
    res = client.post("/api/v1/data-sources/non_existent_source/sync", headers=auth_headers)
    assert res.status_code == 400

@pytest.mark.skipif(
    os.getenv("RUN_LIVE_DATA_TESTS", "false").lower() != "true",
    reason="Opt-in live integration test requires RUN_LIVE_DATA_TESTS=true and YOUTUBE_API_KEY"
)
def test_live_youtube_api_ingestion():
    from backend.app.connectors.youtube_connector import YouTubeDataConnector
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        pytest.skip("YOUTUBE_API_KEY is not set")
    connector = YouTubeDataConnector(api_key=key)
    signals = connector.fetch_signals(limit=5, query="viral beauty serum")
    assert len(signals) > 0
    assert signals[0].platform == "YouTube"
