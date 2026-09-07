"""
Test Suite: Bug #9 - Header, Settings, and Authenticated Profile Global Synchronization

Validates that:
1. Authenticated user profile loads correctly from the backend layer.
2. Profile updates change full_name, role, and avatar_url in both UserRepository and SettingsRepository.
3. GET /api/v1/auth/me returns the authoritative updated profile.
4. GET /api/v1/settings returns the exact same synchronized profile fields.
5. Updating individual fields (e.g., full_name only) preserves all other profile and workspace settings.
6. Reload simulation (fresh API calls with authorization header) loads the persisted profile rather than old memory/cache.
7. Login/logout lifecycle simulation loads the updated persisted profile upon re-authentication.
8. Invalid profile updates (empty names, bad email format, oversized strings) are safely rejected with 422.
9. Passwords, token hashes, and sensitive secrets are never leaked in profile or settings payloads.
10. Default/demo identities are never used as authoritative runtime user state.
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
def auth_sync_context():
    user_repo = InMemoryUserRepository()
    settings_repo = InMemorySettingsRepository()
    
    raw_password = "Password123!"
    test_user = User(
        id="usr_sync_test_99",
        email="analyst@trendpulse.io",
        full_name="Original Name",
        hashed_password=get_password_hash(raw_password),
        is_active=True,
        is_verified=True,
        workspace_id="ws_sync_test_99",
        role="Intelligence Lead",
        avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
        created_at=datetime.now(timezone.utc)
    )
    user_repo.create(test_user)
    
    initial_settings = UserSettings(
        user_id=test_user.id,
        full_name=test_user.full_name,
        email=test_user.email,
        role=test_user.role,
        avatar_url=test_user.avatar_url,
        company_name="Vanguard Intelligence Group",
        currency="USD",
        timezone="America/New_York",
        dark_mode=True,
        ai_confidence_threshold=85
    )
    settings_repo.update(initial_settings)
    
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_settings_repository] = lambda: settings_repo
    
    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    
    yield {
        "user_repo": user_repo,
        "settings_repo": settings_repo,
        "user": test_user,
        "headers": headers,
        "raw_password": raw_password
    }
    
    app.dependency_overrides.pop(get_user_repository, None)
    app.dependency_overrides.pop(get_settings_repository, None)

def test_01_authenticated_profile_and_settings_initial_synchronization(auth_sync_context):
    headers = auth_sync_context["headers"]
    
    # 1. Check /auth/me
    res_auth = client.get("/api/v1/auth/me", headers=headers)
    assert res_auth.status_code == 200
    auth_data = res_auth.json()["data"]
    assert auth_data["full_name"] == "Original Name"
    assert auth_data["email"] == "analyst@trendpulse.io"
    assert auth_data["role"] == "Intelligence Lead"
    assert auth_data["avatar_url"] == "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
    
    # 2. Check /settings
    res_settings = client.get("/api/v1/settings", headers=headers)
    assert res_settings.status_code == 200
    settings_data = res_settings.json()["data"]
    assert settings_data["full_name"] == auth_data["full_name"]
    assert settings_data["email"] == auth_data["email"]
    assert settings_data["role"] == auth_data["role"]
    assert settings_data["avatar_url"] == auth_data["avatar_url"]
    assert settings_data["company_name"] == "Vanguard Intelligence Group"

def test_02_update_profile_via_settings_immediately_syncs_all_layers(auth_sync_context):
    headers = auth_sync_context["headers"]
    user_repo = auth_sync_context["user_repo"]
    settings_repo = auth_sync_context["settings_repo"]
    user = auth_sync_context["user"]
    
    update_payload = {
        "full_name": "Elena Rostova",
        "email": "elena.rostova@trendpulse.io",
        "role": "Principal Market Strategist",
        "avatar_url": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150",
        "company_name": "Horizon Alpha Labs",
        "currency": "EUR",
        "timezone": "Europe/London",
        "ai_confidence_threshold": 92
    }
    
    # 1. Update via PUT /settings
    res_put = client.put("/api/v1/settings", json=update_payload, headers=headers)
    assert res_put.status_code == 200
    put_data = res_put.json()["data"]
    assert put_data["full_name"] == "Elena Rostova"
    assert put_data["email"] == "elena.rostova@trendpulse.io"
    assert put_data["role"] == "Principal Market Strategist"
    assert put_data["avatar_url"] == "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150"
    
    # 2. Verify backend UserRepository was updated
    persisted_user = user_repo.get_by_id(user.id)
    assert persisted_user.full_name == "Elena Rostova"
    assert persisted_user.email == "elena.rostova@trendpulse.io"
    assert persisted_user.role == "Principal Market Strategist"
    assert persisted_user.avatar_url == "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150"
    
    # 3. Verify backend SettingsRepository was updated
    persisted_settings = settings_repo.get_by_user_id(user.id)
    assert persisted_settings.full_name == "Elena Rostova"
    assert persisted_settings.company_name == "Horizon Alpha Labs"
    assert persisted_settings.currency == "EUR"
    assert persisted_settings.ai_confidence_threshold == 92
    
    # 4. Verify /auth/me returns updated profile
    res_auth = client.get("/api/v1/auth/me", headers=headers)
    assert res_auth.status_code == 200
    auth_data = res_auth.json()["data"]
    assert auth_data["full_name"] == "Elena Rostova"
    assert auth_data["email"] == "elena.rostova@trendpulse.io"
    assert auth_data["role"] == "Principal Market Strategist"
    assert auth_data["avatar_url"] == "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150"

def test_03_update_profile_via_patch_auth_me_syncs_settings_repository(auth_sync_context):
    headers = auth_sync_context["headers"]
    settings_repo = auth_sync_context["settings_repo"]
    user = auth_sync_context["user"]
    
    patch_payload = {
        "full_name": "Marcus Aurelius Vance",
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
        "role": "Chief Intelligence Officer"
    }
    
    # 1. Update via PATCH /auth/me
    res_patch = client.patch("/api/v1/auth/me", json=patch_payload, headers=headers)
    assert res_patch.status_code == 200
    patch_data = res_patch.json()["data"]
    assert patch_data["full_name"] == "Marcus Aurelius Vance"
    assert patch_data["avatar_url"] == "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150"
    assert patch_data["role"] == "Chief Intelligence Officer"
    
    # 2. Verify /settings endpoint reflects the changes immediately
    res_settings = client.get("/api/v1/settings", headers=headers)
    assert res_settings.status_code == 200
    settings_data = res_settings.json()["data"]
    assert settings_data["full_name"] == "Marcus Aurelius Vance"
    assert settings_data["avatar_url"] == "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150"
    assert settings_data["role"] == "Chief Intelligence Officer"
    assert settings_data["company_name"] == "Vanguard Intelligence Group" # preserved

def test_04_partial_update_preserves_unmodified_fields(auth_sync_context):
    headers = auth_sync_context["headers"]
    
    # Update only full_name
    res = client.patch("/api/v1/settings", json={"full_name": "Sophia Lin"}, headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["full_name"] == "Sophia Lin"
    # Unmodified fields must be preserved
    assert data["email"] == "analyst@trendpulse.io"
    assert data["role"] == "Intelligence Lead"
    assert data["avatar_url"] == "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
    assert data["company_name"] == "Vanguard Intelligence Group"
    assert data["ai_confidence_threshold"] == 85

def test_05_relogin_loads_authoritative_persisted_profile(auth_sync_context):
    headers = auth_sync_context["headers"]
    raw_password = auth_sync_context["raw_password"]
    
    # 1. Change full name, role, and avatar
    client.put("/api/v1/settings", json={
        "full_name": "Dr. Aris Thorne",
        "role": "VP Predictive Analytics",
        "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"
    }, headers=headers)
    
    # 2. Simulate login request
    res_login = client.post("/api/v1/auth/login", json={
        "email": "analyst@trendpulse.io",
        "password": raw_password
    })
    assert res_login.status_code == 200
    login_data = res_login.json()["data"]
    assert login_data["full_name"] == "Dr. Aris Thorne"
    assert login_data["role"] == "VP Predictive Analytics"
    assert login_data["avatar_url"] == "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"

def test_06_invalid_profile_inputs_rejected(auth_sync_context):
    headers = auth_sync_context["headers"]
    
    # Empty full name
    res1 = client.put("/api/v1/settings", json={"full_name": "   "}, headers=headers)
    assert res1.status_code == 422
    
    # Invalid email
    res2 = client.put("/api/v1/settings", json={"email": "not-an-email"}, headers=headers)
    assert res2.status_code == 422
    
    # Oversized full name (>100 chars)
    res3 = client.put("/api/v1/settings", json={"full_name": "A" * 105}, headers=headers)
    assert res3.status_code == 422

def test_07_no_sensitive_secrets_or_hashes_exposed(auth_sync_context):
    headers = auth_sync_context["headers"]
    
    res_auth = client.get("/api/v1/auth/me", headers=headers)
    assert res_auth.status_code == 200
    content = res_auth.text
    assert "hashed_password" not in content
    assert "Password123!" not in content
    assert "token_hash" not in content
    assert "verification_token" not in content
    
    res_settings = client.get("/api/v1/settings", headers=headers)
    assert res_settings.status_code == 200
    content_st = res_settings.text
    assert "hashed_password" not in content_st
    assert "Password123!" not in content_st
