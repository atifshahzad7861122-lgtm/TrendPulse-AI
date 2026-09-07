import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import verify_password
from backend.app.repositories.in_memory import (
    user_repo, workspace_repo, auth_persistence_repo, settings_repo
)
from backend.app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, VerifyEmailRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)

client = TestClient(app)

@pytest.fixture
def clean_auth_state():
    """Provides a fresh test user identifier."""
    test_email = "tester_persistent@trendpulse.ai"
    existing = user_repo.get_by_email(test_email)
    if existing:
        user_repo.delete(existing.id)
    return test_email

def test_auth_registration_full_persistence_pipeline(clean_auth_state):
    test_email = clean_auth_state
    reg_payload = {
        "email": test_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "full_name": "Jordan Peterson",
        "terms_accepted": True
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["email"] == test_email
    assert "user_id" in data
    assert "verification_token" not in data
    assert "dev_verification_url" not in data

    # Verify User record
    user = user_repo.get_by_email(test_email)
    assert user is not None
    assert user.full_name == "Jordan Peterson"
    assert user.is_verified is False
    assert user.is_active is True
    assert user.verification_token is not None
    assert verify_password("StrongPassword123!", user.hashed_password)

    # Verify Workspace & Member record
    ws = workspace_repo.get_by_id(user.workspace_id)
    assert ws is not None
    assert ws.owner_id == user.id
    members = workspace_repo.get_members(ws.id)
    assert len(members) >= 1
    assert any(m.user_id == user.id for m in members)

    # Verify User Settings record
    st = settings_repo.get_by_user_id(user.id)
    assert st is not None
    assert st.email == test_email

    # Verify Email Verification Record
    ev = auth_persistence_repo.get_email_verification(user.verification_token)
    assert ev is not None
    assert ev.user_id == user.id
    assert ev.used_at is None

def test_auth_registration_duplicate_email_rejection(clean_auth_state):
    test_email = clean_auth_state
    reg_payload = {
        "email": test_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "full_name": "Jordan Peterson",
        "terms_accepted": True
    }
    res1 = client.post("/api/v1/auth/register", json=reg_payload)
    assert res1.status_code == 200

    # Second registration with identical email must fail with 409
    res2 = client.post("/api/v1/auth/register", json=reg_payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]

def test_auth_registration_validation_guards():
    # Passwords do not match
    res = client.post("/api/v1/auth/register", json={
        "email": "mismatch@trendpulse.ai",
        "password": "Password123!",
        "confirm_password": "PasswordDifferent!",
        "full_name": "Mismatch User",
        "terms_accepted": True
    })
    assert res.status_code == 400
    assert "match" in res.json()["detail"]

    # Terms not accepted
    res_terms = client.post("/api/v1/auth/register", json={
        "email": "noterms@trendpulse.ai",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "full_name": "No Terms User",
        "terms_accepted": False
    })
    assert res_terms.status_code == 400
    assert "Terms" in res_terms.json()["detail"]

def test_auth_login_creates_session_and_events(clean_auth_state):
    test_email = clean_auth_state
    client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "full_name": "Session Tester",
        "terms_accepted": True
    })

    login_res = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "StrongPassword123!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()["data"]
    assert "access_token" in token_data

    # Audit events logged
    events = auth_persistence_repo.list_login_events(email=test_email)
    event_types = [e.event_type for e in events]
    assert "registered" in event_types
    assert "login_success" in event_types

def test_auth_login_invalid_credentials_and_inactive_account(clean_auth_state):
    test_email = clean_auth_state
    client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "full_name": "Inactive Tester",
        "terms_accepted": True
    })

    # Wrong password
    bad_res = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "WrongPassword!"
    })
    assert bad_res.status_code == 401

    # Deactivate user
    user = user_repo.get_by_email(test_email)
    user.is_active = False
    user_repo.update(user)

    inactive_res = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "StrongPassword123!"
    })
    assert inactive_res.status_code == 403
    assert "deactivated" in inactive_res.json()["detail"]

def test_auth_email_verification_lifecycle(clean_auth_state):
    test_email = clean_auth_state
    reg_res = client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "full_name": "Verification User",
        "terms_accepted": True
    })
    assert reg_res.status_code == 200
    assert "verification_token" not in reg_res.json()["data"]

    user = user_repo.get_by_email(test_email)
    assert user is not None
    token = user.verification_token
    assert token is not None

    # Verify email
    v_res = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert v_res.status_code == 200
    assert v_res.json()["data"]["is_verified"] is True

    # Check user record
    user = user_repo.get_by_email(test_email)
    assert user.is_verified is True

    # Re-using used token must fail
    v_res_used = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert v_res_used.status_code == 400

def test_auth_forgot_and_reset_password_lifecycle(clean_auth_state):
    test_email = clean_auth_state
    client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": "OldPassword123!",
        "confirm_password": "OldPassword123!",
        "full_name": "Reset User",
        "terms_accepted": True
    })

    # Forgot password for unknown email (anti-enumeration)
    f_res_unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent@trendpulse.ai"})
    assert f_res_unknown.status_code == 200

    # Forgot password for existing email
    f_res = client.post("/api/v1/auth/forgot-password", json={"email": test_email})
    assert f_res.status_code == 200
    reset_token = f_res.json()["data"]["reset_token"]
    assert reset_token is not None

    # Reset password
    r_res = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "BrandNewPassword123!",
        "confirm_password": "BrandNewPassword123!"
    })
    assert r_res.status_code == 200

    # Verify user can log in with new password
    login_new = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "BrandNewPassword123!"
    })
    assert login_new.status_code == 200

    # Reusing reset token must fail
    r_res_reuse = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "AnotherPassword123!",
        "confirm_password": "AnotherPassword123!"
    })
    assert r_res_reuse.status_code == 400

def test_auth_logout_and_me_endpoint(clean_auth_state):
    test_email = clean_auth_state
    client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "full_name": "Profile Tester",
        "terms_accepted": True
    })

    login_res = client.post("/api/v1/auth/login", json={
        "email": test_email,
        "password": "StrongPassword123!"
    })
    token = login_res.json()["data"]["access_token"]

    # /me endpoint
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    profile = me_res.json()["data"]
    assert profile["email"] == test_email
    assert profile["full_name"] == "Profile Tester"

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200
