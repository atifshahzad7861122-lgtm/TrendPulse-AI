"""
Test Suite: Bug #9 - Header Profile and Settings Profile Synchronization & Consistency

Covers mandatory Step 13 requirements:
1. /auth/me returns current user.
2. /settings returns the same identity.
3. Updating full_name through Settings updates UserRepository.
4. Updating full_name through /auth/me updates Settings.
5. GET /auth/me after update returns the new name.
6. GET /settings after update returns the new name.
7. Existing email remains intact when only name changes.
8. Existing role remains intact when only name changes.
9. Avatar synchronization works.
10. No password or secret fields are exposed.
11. Invalid profile values are rejected.
12. No demo profile is injected when user data is unavailable.
13. Profile state remains correct after simulated reload.
14. Two independent reads of the same authenticated user return consistent identity data.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from backend.app.main import app
from backend.app.models.domain import User, UserSettings
from backend.app.repositories.in_memory import InMemoryUserRepository, InMemorySettingsRepository
from backend.app.api.deps import get_user_repository, get_settings_repository
from backend.app.core.security import create_access_token, get_password_hash

client = TestClient(app)

@pytest.fixture
def auth_sync_env():
    user_repo = InMemoryUserRepository()
    settings_repo = InMemorySettingsRepository()

    raw_password = "SecretPassword123!"
    user = User(
        id="usr_consistency_909",
        email="operator.one@trendpulse.ai",
        full_name="Jordan Hayes",
        hashed_password=get_password_hash(raw_password),
        is_active=True,
        is_verified=True,
        workspace_id="ws_consistency_909",
        role="Senior Market Analyst",
        avatar_url="https://images.unsplash.com/photo-jordan.jpg",
        created_at=datetime.now(timezone.utc)
    )
    user_repo.create(user)

    settings = UserSettings(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        avatar_url=user.avatar_url,
        company_name="Apex Global Ventures",
        currency="USD",
        timezone="UTC",
        dark_mode=True,
        ai_confidence_threshold=82
    )
    settings_repo.update(settings)

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_settings_repository] = lambda: settings_repo

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    yield {
        "user_repo": user_repo,
        "settings_repo": settings_repo,
        "user": user,
        "token": token,
        "headers": headers,
        "raw_password": raw_password
    }

    app.dependency_overrides.pop(get_user_repository, None)
    app.dependency_overrides.pop(get_settings_repository, None)


def test_01_auth_me_returns_current_user(auth_sync_env):
    """1. /auth/me returns current user."""
    res = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"])
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == auth_sync_env["user"].id
    assert data["email"] == "operator.one@trendpulse.ai"
    assert data["full_name"] == "Jordan Hayes"
    assert data["role"] == "Senior Market Analyst"
    assert data["avatar_url"] == "https://images.unsplash.com/photo-jordan.jpg"


def test_02_settings_returns_same_identity(auth_sync_env):
    """2. /settings returns the same identity."""
    me_res = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"])
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]

    st_res = client.get("/api/v1/settings", headers=auth_sync_env["headers"])
    assert st_res.status_code == 200
    st_data = st_res.json()["data"]

    assert st_data["full_name"] == me_data["full_name"]
    assert st_data["email"] == me_data["email"]
    assert st_data["role"] == me_data["role"]
    assert st_data["avatar_url"] == me_data["avatar_url"]


def test_03_updating_full_name_through_settings_updates_user_repository(auth_sync_env):
    """3. Updating full_name through Settings updates UserRepository."""
    user_repo = auth_sync_env["user_repo"]
    user_id = auth_sync_env["user"].id

    update_payload = {
        "full_name": "Jordan Hayes-Chen",
        "company_name": "Frontier Analytics Inc",
        "currency": "EUR"
    }
    put_res = client.put("/api/v1/settings", json=update_payload, headers=auth_sync_env["headers"])
    assert put_res.status_code == 200

    # Direct persistence check in UserRepository
    persisted_user = user_repo.get_by_id(user_id)
    assert persisted_user is not None
    assert persisted_user.full_name == "Jordan Hayes-Chen"


def test_04_updating_full_name_through_auth_me_updates_settings(auth_sync_env):
    """4. Updating full_name through /auth/me updates Settings."""
    settings_repo = auth_sync_env["settings_repo"]
    user_id = auth_sync_env["user"].id

    patch_res = client.patch("/api/v1/auth/me", json={"full_name": "Jordan Vance Hayes"}, headers=auth_sync_env["headers"])
    assert patch_res.status_code == 200

    # Direct persistence check in SettingsRepository
    persisted_settings = settings_repo.get_by_user_id(user_id)
    assert persisted_settings is not None
    assert persisted_settings.full_name == "Jordan Vance Hayes"


def test_05_get_auth_me_after_update_returns_new_name(auth_sync_env):
    """5. GET /auth/me after update returns the new name."""
    put_res = client.put("/api/v1/settings", json={"full_name": "Dr. Jordan Hayes"}, headers=auth_sync_env["headers"])
    assert put_res.status_code == 200

    me_res = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"])
    assert me_res.status_code == 200
    assert me_res.json()["data"]["full_name"] == "Dr. Jordan Hayes"


def test_06_get_settings_after_update_returns_new_name(auth_sync_env):
    """6. GET /settings after update returns the new name."""
    patch_res = client.patch("/api/v1/auth/me", json={"full_name": "Professor Jordan Hayes"}, headers=auth_sync_env["headers"])
    assert patch_res.status_code == 200

    st_res = client.get("/api/v1/settings", headers=auth_sync_env["headers"])
    assert st_res.status_code == 200
    assert st_res.json()["data"]["full_name"] == "Professor Jordan Hayes"


def test_07_existing_email_remains_intact_when_only_name_changes(auth_sync_env):
    """7. Existing email remains intact when only name changes."""
    put_res = client.put("/api/v1/settings", json={"full_name": "Jordan Hayes Updated"}, headers=auth_sync_env["headers"])
    assert put_res.status_code == 200

    me_res = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"])
    assert me_res.json()["data"]["email"] == "operator.one@trendpulse.ai"

    st_res = client.get("/api/v1/settings", headers=auth_sync_env["headers"])
    assert st_res.json()["data"]["email"] == "operator.one@trendpulse.ai"


def test_08_existing_role_remains_intact_when_only_name_changes(auth_sync_env):
    """8. Existing role remains intact when only name changes."""
    put_res = client.put("/api/v1/settings", json={"full_name": "Jordan Hayes Renamed"}, headers=auth_sync_env["headers"])
    assert put_res.status_code == 200

    me_res = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"])
    assert me_res.json()["data"]["role"] == "Senior Market Analyst"

    st_res = client.get("/api/v1/settings", headers=auth_sync_env["headers"])
    assert st_res.json()["data"]["role"] == "Senior Market Analyst"


def test_09_avatar_synchronization_works(auth_sync_env):
    """9. Avatar synchronization works bi-directionally between /settings and /auth/me."""
    new_avatar = "https://cdn.trendpulse.ai/avatars/jordan_2026.png"

    # Update avatar via Settings
    put_res = client.put("/api/v1/settings", json={"avatar_url": new_avatar}, headers=auth_sync_env["headers"])
    assert put_res.status_code == 200
    assert put_res.json()["data"]["avatar_url"] == new_avatar

    # Verify reflected in /auth/me
    me_res = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"])
    assert me_res.status_code == 200
    assert me_res.json()["data"]["avatar_url"] == new_avatar

    # Update avatar via /auth/me
    second_avatar = "https://cdn.trendpulse.ai/avatars/jordan_alt.png"
    patch_res = client.patch("/api/v1/auth/me", json={"avatar_url": second_avatar}, headers=auth_sync_env["headers"])
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["avatar_url"] == second_avatar

    # Verify reflected in /settings
    st_res = client.get("/api/v1/settings", headers=auth_sync_env["headers"])
    assert st_res.status_code == 200
    assert st_res.json()["data"]["avatar_url"] == second_avatar


def test_10_no_password_or_secret_fields_are_exposed(auth_sync_env):
    """10. No password or secret fields are exposed in profile responses."""
    me_res = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"])
    me_data = me_res.json()["data"]

    st_res = client.get("/api/v1/settings", headers=auth_sync_env["headers"])
    st_data = st_res.json()["data"]

    for d in [me_data, st_data]:
        assert "password" not in d
        assert "hashed_password" not in d
        assert "verification_token" not in d
        assert "reset_token" not in d
        assert auth_sync_env["raw_password"] not in str(d)


def test_11_invalid_profile_values_are_rejected(auth_sync_env):
    """11. Invalid profile values are rejected."""
    # Empty full_name
    res_empty_settings = client.put("/api/v1/settings", json={"full_name": "   "}, headers=auth_sync_env["headers"])
    assert res_empty_settings.status_code == 422

    res_empty_auth = client.patch("/api/v1/auth/me", json={"full_name": "   "}, headers=auth_sync_env["headers"])
    assert res_empty_auth.status_code == 422

    # Oversized full_name (>100 characters)
    oversized = "A" * 105
    res_long_settings = client.put("/api/v1/settings", json={"full_name": oversized}, headers=auth_sync_env["headers"])
    assert res_long_settings.status_code == 422

    res_long_auth = client.patch("/api/v1/auth/me", json={"full_name": oversized}, headers=auth_sync_env["headers"])
    assert res_long_auth.status_code == 422

    # Malformed email
    res_bad_email = client.put("/api/v1/settings", json={"email": "not-a-valid-email"}, headers=auth_sync_env["headers"])
    assert res_bad_email.status_code == 422


def test_12_no_demo_profile_injected_when_user_data_unavailable():
    """12. No demo profile is injected when user data is unavailable."""
    # Anonymous call with no Authorization header must return 401 Unauthorized
    res_no_auth_me = client.get("/api/v1/auth/me")
    assert res_no_auth_me.status_code == 401

    res_no_auth_st = client.get("/api/v1/settings")
    assert res_no_auth_st.status_code == 401

    # Bogus credentials must return 401 Unauthorized
    bogus = {"Authorization": "Bearer non_existent_token_xyz"}
    res_bogus_me = client.get("/api/v1/auth/me", headers=bogus)
    assert res_bogus_me.status_code == 401

    res_bogus_st = client.get("/api/v1/settings", headers=bogus)
    assert res_bogus_st.status_code == 401


def test_13_profile_state_remains_correct_after_simulated_reload(auth_sync_env):
    """13. Profile state remains correct after simulated reload."""
    # Update profile
    client.put("/api/v1/settings", json={"full_name": "Jordan Reloaded"}, headers=auth_sync_env["headers"])

    # Simulate fresh client reload with fresh authorization header
    fresh_token = create_access_token(auth_sync_env["user"].id)
    fresh_headers = {"Authorization": f"Bearer {fresh_token}"}

    me_fresh = client.get("/api/v1/auth/me", headers=fresh_headers)
    assert me_fresh.status_code == 200
    assert me_fresh.json()["data"]["full_name"] == "Jordan Reloaded"

    st_fresh = client.get("/api/v1/settings", headers=fresh_headers)
    assert st_fresh.status_code == 200
    assert st_fresh.json()["data"]["full_name"] == "Jordan Reloaded"


def test_14_two_independent_reads_return_consistent_identity_data(auth_sync_env):
    """14. Two independent reads of the same authenticated user return consistent identity data."""
    read1 = client.get("/api/v1/auth/me", headers=auth_sync_env["headers"]).json()["data"]
    read2 = client.get("/api/v1/settings", headers=auth_sync_env["headers"]).json()["data"]

    for field in ["full_name", "email", "role", "avatar_url"]:
        assert read1[field] == read2[field], f"Mismatch in field {field}: {read1[field]} vs {read2[field]}"
