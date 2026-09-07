import os
import json
import tempfile
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.domain import DarazAuthSession, MarketplaceProduct
from backend.app.repositories.in_memory import InMemoryMarketplaceProductRepository
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.daraz_service import DarazService
from backend.app.api.deps import get_daraz_service, get_marketplace_product_repository


def calculate_session_fingerprint(session_dict: dict) -> str:
    """Computes a SHA-256 fingerprint of non-secret session metadata."""
    keys = ["id", "account", "seller_id", "country", "status", "authorized_at", "expires_in"]
    normalized = {k: str(session_dict.get(k)) for k in keys}
    payload = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_oauth_fixture_isolation():
    """Verifies that mock OAuth sessions created in test memory never touch production storage."""
    test_repo = InMemoryMarketplaceProductRepository(storage_file=":memory:")
    mock_session = DarazAuthSession(
        id="daraz_sess_test_iso_1",
        account="seller_pk_01",
        seller_id="seller_pk_01",
        access_token="mock_access_token_abc",
        refresh_token="mock_refresh_token_xyz",
        expires_in=86400
    )
    test_repo.save_auth_session(mock_session)

    # In-memory retrieval works
    retrieved = test_repo.get_auth_session("seller_pk_01")
    assert retrieved is not None
    assert retrieved.id == "daraz_sess_test_iso_1"

    # Production store file path is untouched
    prod_store_path = os.path.join("backend", "app", "data", "marketplace_products_store.json")
    if os.path.exists(prod_store_path):
        with open(prod_store_path, "r", encoding="utf-8") as f:
            prod_data = json.load(f)
            for sess in prod_data.get("auth_sessions", []):
                assert sess.get("id") != "daraz_sess_test_iso_1"
                assert sess.get("access_token") != "mock_access_token_abc"


def test_production_auth_session_unchanged_after_tests():
    """Seeds a simulated production file with a sentinel session and asserts its fingerprint is unaltered."""
    temp_dir = tempfile.mkdtemp()
    prod_sim_file = os.path.join(temp_dir, "prod_marketplace_products_store.json")

    original_prod_session = {
        "id": "daraz_sess_real_prod_123",
        "account": "Real Daraz Official Seller",
        "seller_id": "real_seller_id_888",
        "user_id": "usr_999",
        "country": "pk",
        "access_token": "live_authentic_access_token_secret",
        "refresh_token": "live_authentic_refresh_token_secret",
        "expires_in": 2592000,
        "status": "authorized",
        "authorized_at": "2026-08-25T18:00:00Z",
        "created_at": "2026-08-25T18:00:00Z",
        "updated_at": "2026-08-25T18:00:00Z"
    }

    initial_payload = {
        "products": [],
        "snapshots": [],
        "auth_sessions": [original_prod_session],
        "sellers": [],
        "categories": [],
        "quotas": [],
        "training_dataset": []
    }
    with open(prod_sim_file, "w", encoding="utf-8") as f:
        json.dump(initial_payload, f, indent=2)

    initial_fingerprint = calculate_session_fingerprint(original_prod_session)

    # Instantiate repo on this simulated file and attempt to write mock sessions
    repo = InMemoryMarketplaceProductRepository(storage_file=prod_sim_file)
    mock_test_session = DarazAuthSession(
        id="mock_session_from_test_callback",
        account="seller_pk_01",
        seller_id="seller_pk_01",
        access_token="mock_access_token_999",
        expires_in=86400
    )
    repo.save_auth_session(mock_test_session)

    # Read back the underlying file from disk
    with open(prod_sim_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)

    disk_sessions = disk_data.get("auth_sessions", [])
    assert len(disk_sessions) == 1
    assert disk_sessions[0]["id"] == "daraz_sess_real_prod_123"
    after_fingerprint = calculate_session_fingerprint(disk_sessions[0])
    assert after_fingerprint == initial_fingerprint


def test_test_repository_isolation():
    """Verifies that in-memory repository with :memory: never writes to disk."""
    repo = InMemoryMarketplaceProductRepository(storage_file=":memory:")
    assert repo._storage_file == ":memory:"
    prod = MarketplaceProduct(
        id="daraz_iso_p1",
        platform="daraz",
        product_id="iso_p1",
        product_name="Iso Test Product",
        price=1000.0,
        currency="PKR"
    )
    repo.upsert_product(prod)
    sess = DarazAuthSession(
        id="daraz_sess_iso",
        account="test_account",
        access_token="test_token"
    )
    repo.save_auth_session(sess)

    assert repo.count_products(platform="daraz") == 1
    assert repo.get_auth_session("test_account") is not None


def test_mock_session_never_persists_to_production():
    """Verifies that is_test_session correctly identifies test tokens and blocks disk writes."""
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "test_store.json")

    repo = InMemoryMarketplaceProductRepository(storage_file=temp_file)

    test_tokens = [
        "mock_access_token_123",
        "test_token_456",
        "fake_token_789",
        "sentinel_token_012"
    ]

    for tok in test_tokens:
        s = DarazAuthSession(
            id=f"sess_{tok}",
            account=f"acc_{tok}",
            access_token=tok,
            expires_in=3600
        )
        assert repo.is_test_session(s) is True
        repo.save_auth_session(s)

    # Disk file should either not exist or contain 0 auth sessions
    if os.path.exists(temp_file):
        with open(temp_file, "r", encoding="utf-8") as f:
            d = json.load(f)
            assert len(d.get("auth_sessions", [])) == 0


def test_testing_mode_blocks_production_auth_writes(monkeypatch):
    """Verifies that TESTING=true environment variable blocks all disk persistence."""
    monkeypatch.setenv("TESTING", "true")
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "test_store_env.json")

    repo = InMemoryMarketplaceProductRepository(storage_file=temp_file)
    assert repo.is_testing_environment() is True

    s = DarazAuthSession(
        id="sess_genuine_looking_id",
        account="Genuine Looking Account",
        access_token="genuine_format_access_token_xyz",
        expires_in=86400
    )
    repo.save_auth_session(s)

    if os.path.exists(temp_file):
        with open(temp_file, "r", encoding="utf-8") as f:
            d = json.load(f)
            assert len(d.get("auth_sessions", [])) == 0


def test_production_repository_not_used_by_oauth_tests():
    """Verifies that API dependency overrides prevent the app singleton from being used in tests."""
    mock_repo = InMemoryMarketplaceProductRepository(storage_file=":memory:")
    mock_svc = DarazService(marketplace_repo=mock_repo)

    app.dependency_overrides[get_marketplace_product_repository] = lambda: mock_repo
    app.dependency_overrides[get_daraz_service] = lambda: mock_svc

    client = TestClient(app)

    mock_token_data = {
        "access_token": "mock_token_override_test",
        "refresh_token": "mock_refresh_override_test",
        "seller_id": "seller_override_test",
        "account": "seller_override_test",
        "expires_in": 86400,
        "country": "pk"
    }

    with patch.object(DarazOfficialProvider, "exchange_code_for_token", return_value=(True, mock_token_data, None)):
        res = client.get("/api/v1/platforms/daraz/callback?code=test_code&state=test_state&account=seller_override_test")
        assert res.status_code == 200

    # The mock repo in memory received the session
    assert mock_repo.get_auth_session("seller_override_test") is not None

    # Clean up overrides
    app.dependency_overrides.pop(get_marketplace_product_repository, None)
    app.dependency_overrides.pop(get_daraz_service, None)


def test_live_session_remains_valid_after_test_suite():
    """Verifies that authentic production sessions are never evicted or overridden by test operations."""
    real_session_dict = {
        "id": "daraz_sess_prod_persistent_99",
        "account": "Authentic Live Store PK",
        "seller_id": "seller_live_pk_99",
        "user_id": "usr_real_99",
        "country": "pk",
        "access_token": "live_pk_access_token_real",
        "refresh_token": "live_pk_refresh_token_real",
        "expires_in": 2592000,
        "token_type": "Bearer",
        "status": "authorized",
        "authorized_at": "2026-08-25T18:00:00Z",
        "created_at": "2026-08-25T18:00:00Z",
        "updated_at": "2026-08-25T18:00:00Z"
    }

    temp_dir = tempfile.mkdtemp()
    store_file = os.path.join(temp_dir, "isolated_store.json")
    with open(store_file, "w", encoding="utf-8") as f:
        json.dump({
            "products": [],
            "snapshots": [],
            "auth_sessions": [real_session_dict],
            "sellers": [],
            "categories": [],
            "quotas": [],
            "training_dataset": []
        }, f, indent=2)

    repo = InMemoryMarketplaceProductRepository(storage_file=store_file)

    # Perform mock test session saves
    mock_session = DarazAuthSession(
        id="daraz_sess_mock_test",
        account="seller_pk_01",
        seller_id="seller_pk_01",
        access_token="mock_test_token"
    )
    repo.save_auth_session(mock_session)

    # Verify latest production session from disk
    disk_repo = InMemoryMarketplaceProductRepository(storage_file=store_file)
    active_prod = disk_repo.get_auth_session("seller_live_pk_99")
    assert active_prod is not None
    assert active_prod.id == "daraz_sess_prod_persistent_99"


def test_authenticated_products_request_after_tests():
    """Verifies that official provider get_active_token retrieves only valid non-mock sessions."""
    repo = InMemoryMarketplaceProductRepository(storage_file=":memory:")
    now = datetime.now(timezone.utc)
    valid_session = DarazAuthSession(
        id="daraz_sess_valid_active",
        account="Valid Seller",
        seller_id="valid_seller_1",
        access_token="valid_active_access_token_12345",
        expires_in=86400,
        authorized_at=now
    )
    repo.save_auth_session(valid_session)

    provider = DarazOfficialProvider(
        app_key="505830",
        app_secret="test_secret",
        marketplace_repo=repo
    )

    token, err = provider.get_active_token()
    assert err is None
    assert token == "valid_active_access_token_12345"
