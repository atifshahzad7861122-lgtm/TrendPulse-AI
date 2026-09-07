import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.domain import User, UserSettings
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.repositories.in_memory import InMemoryUserRepository, InMemorySettingsRepository
from backend.app.api.deps import get_user_repository, get_settings_repository

client = TestClient(app)

@pytest.fixture
def clean_repos():
    user_repo = InMemoryUserRepository()
    settings_repo = InMemorySettingsRepository()
    
    # Create test user
    test_user = User(
        id="usr_settings_test_01",
        email="operator@trendpulse.ai",
        full_name="Alex Vance",
        hashed_password=get_password_hash("Password123!"),
        is_verified=True,
        workspace_id="ws_settings_test_01",
        role="Lead Market Strategist",
        avatar_url="https://example.com/avatar.jpg"
    )
    user_repo.create(test_user)
    
    test_settings = UserSettings(
        user_id=test_user.id,
        full_name=test_user.full_name,
        email=test_user.email,
        role=test_user.role,
        avatar_url=test_user.avatar_url,
        company_name="Apex Intelligence Labs",
        timezone="UTC",
        currency="USD",
        email_notifications=True,
        alert_critical_only=False,
        weekly_digest=True,
        ai_model_preference="Qwen 2.5 Max (Simulated)",
        ai_confidence_threshold=85,
        auto_generate_reports=True,
        dark_mode=True,
        table_dense_view=False,
        live_ticker_enabled=True
    )
    settings_repo.update(test_settings)
    
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_settings_repository] = lambda: settings_repo
    
    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    
    yield {"user_repo": user_repo, "settings_repo": settings_repo, "user": test_user, "headers": headers}
    
    app.dependency_overrides.clear()


def test_01_existing_profile_loads_correctly(clean_repos):
    """Verify that existing profile and settings load accurately for the authenticated user."""
    headers = clean_repos["headers"]
    
    # 1. GET /api/v1/settings
    res = client.get("/api/v1/settings", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["full_name"] == "Alex Vance"
    assert body["data"]["email"] == "operator@trendpulse.ai"
    assert body["data"]["company_name"] == "Apex Intelligence Labs"
    
    # 2. GET /api/v1/auth/me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_body = me_res.json()
    assert me_body["data"]["full_name"] == "Alex Vance"
    assert me_body["data"]["email"] == "operator@trendpulse.ai"


def test_02_update_full_name_persists_in_both_repositories(clean_repos):
    """Verify that updating Full Name persists in both SettingsRepository and UserRepository."""
    headers = clean_repos["headers"]
    user_repo = clean_repos["user_repo"]
    settings_repo = clean_repos["settings_repo"]
    user_id = clean_repos["user"].id
    
    # Update settings with a new Full Name
    update_payload = {
        "full_name": "Dr. Elena Rostova",
        "company_name": "Nova Frontier Tech",
        "currency": "EUR"
    }
    
    put_res = client.put("/api/v1/settings", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    put_body = put_res.json()
    assert put_body["success"] is True
    assert put_body["data"]["full_name"] == "Dr. Elena Rostova"
    assert put_body["data"]["company_name"] == "Nova Frontier Tech"
    assert put_body["data"]["currency"] == "EUR"
    
    # Direct backend repository verification:
    saved_settings = settings_repo.get_by_user_id(user_id)
    assert saved_settings is not None
    assert saved_settings.full_name == "Dr. Elena Rostova"
    assert saved_settings.company_name == "Nova Frontier Tech"
    
    saved_user = user_repo.get_by_id(user_id)
    assert saved_user is not None
    assert saved_user.full_name == "Dr. Elena Rostova"


def test_03_get_after_update_and_reload_simulation(clean_repos):
    """Verify GET after update and subsequent simulated browser reloads return the persisted updated value."""
    headers = clean_repos["headers"]
    
    # Step 1: Update name
    update_payload = {"full_name": "Sarah Connor"}
    put_res = client.put("/api/v1/settings", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    
    # Step 2: Fresh GET request (simulating reopening Settings page)
    get_res = client.get("/api/v1/settings", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["full_name"] == "Sarah Connor"
    
    # Step 3: Fresh GET /auth/me (simulating AuthContext reload on browser refresh)
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["full_name"] == "Sarah Connor"


def test_04_patch_profile_via_auth_me_endpoint(clean_repos):
    """Verify updating profile directly via PATCH /auth/me synchronizes both User and Settings."""
    headers = clean_repos["headers"]
    user_repo = clean_repos["user_repo"]
    settings_repo = clean_repos["settings_repo"]
    user_id = clean_repos["user"].id
    
    patch_res = client.patch("/api/v1/auth/me", json={"full_name": "Marcus Wright", "role": "Principal Analyst"}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["full_name"] == "Marcus Wright"
    assert patch_res.json()["data"]["role"] == "Principal Analyst"
    
    # Check UserRepository
    u = user_repo.get_by_id(user_id)
    assert u.full_name == "Marcus Wright"
    assert u.role == "Principal Analyst"
    
    # Check SettingsRepository
    s = settings_repo.get_by_user_id(user_id)
    assert s.full_name == "Marcus Wright"
    assert s.role == "Principal Analyst"


def test_05_invalid_profile_data_is_rejected(clean_repos):
    """Verify invalid profile inputs (empty name, whitespace-only, overlong name) are rejected with 422."""
    headers = clean_repos["headers"]
    
    # Empty string
    res1 = client.put("/api/v1/settings", json={"full_name": ""}, headers=headers)
    assert res1.status_code == 422
    assert "Full name cannot be empty" in res1.json()["detail"]
    
    # Whitespace only
    res2 = client.put("/api/v1/settings", json={"full_name": "   "}, headers=headers)
    assert res2.status_code == 422
    assert "Full name cannot be empty" in res2.json()["detail"]
    
    # Overlong name (>100 chars)
    long_name = "A" * 105
    res3 = client.put("/api/v1/settings", json={"full_name": long_name}, headers=headers)
    assert res3.status_code == 422
    assert "cannot exceed 100 characters" in res3.json()["detail"]


def test_06_secrets_and_passwords_never_exposed(clean_repos):
    """Verify secrets, hashed passwords, verification tokens are never leaked in settings or error responses."""
    headers = clean_repos["headers"]
    
    res = client.get("/api/v1/settings", headers=headers)
    data = res.json()["data"]
    assert "password" not in data
    assert "hashed_password" not in data
    assert "verification_token" not in data
    assert "reset_token" not in data
    
    # In error response
    err_res = client.put("/api/v1/settings", json={"full_name": ""}, headers=headers)
    err_text = err_res.text
    assert "password" not in err_text.lower()
    assert "secret" not in err_text.lower()


def test_07_existing_fields_remain_intact_when_only_full_name_changes(clean_repos):
    """Verify updating only full_name preserves email, company_name, currency, timezone, dark_mode."""
    headers = clean_repos["headers"]
    
    # Initial settings check
    initial_res = client.get("/api/v1/settings", headers=headers)
    initial_data = initial_res.json()["data"]
    assert initial_data["company_name"] == "Apex Intelligence Labs"
    assert initial_data["dark_mode"] is True
    assert initial_data["currency"] == "USD"
    
    # Update only full_name
    update_res = client.put("/api/v1/settings", json={"full_name": "Kyle Reese"}, headers=headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    
    assert updated_data["full_name"] == "Kyle Reese"
    # Preserved fields:
    assert updated_data["company_name"] == "Apex Intelligence Labs"
    assert updated_data["dark_mode"] is True
    assert updated_data["currency"] == "USD"
    assert updated_data["email_notifications"] is True
    assert updated_data["ai_confidence_threshold"] == 85
