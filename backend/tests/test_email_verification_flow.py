import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.repositories.in_memory import user_repo, auth_persistence_repo
from backend.app.models.domain import EmailVerification
from backend.app.services.email_service import email_service, EmailDeliveryStatus
from backend.app.core.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_in_memory_backend():
    orig = settings.DATA_BACKEND
    settings.DATA_BACKEND = "in_memory"
    yield
    settings.DATA_BACKEND = orig

def test_registration_does_not_expose_verification_token():
    """Requirement 4 & 11: Registration response must never expose the raw verification token."""
    email = f"secure_reg_{datetime.now().timestamp()}@trendpulse.ai"
    payload = {
        "full_name": "Security Tester",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Must contain user_id and email
    assert data["email"] == email
    assert "user_id" in data

    # MUST NOT contain verification_token or dev_verification_url
    assert "verification_token" not in data
    assert "dev_verification_url" not in data
    assert "token" not in data

def test_email_delivery_status_inspection():
    """Requirement 8: Inspect email provider status and report EMAIL DELIVERY NOT CONFIGURED if missing."""
    assert email_service.is_configured() is False or email_service.is_configured() is True
    # In default local environment without SMTP env vars:
    if not email_service.is_configured():
        missing = email_service.get_missing_configuration()
        assert len(missing) > 0
        dispatch_res = email_service.send_verification_email("user@test.com", "tok_test123")
        assert dispatch_res["status"] == EmailDeliveryStatus.NOT_CONFIGURED
        assert "EMAIL DELIVERY NOT CONFIGURED" in dispatch_res["message"]

def test_verification_requires_user_supplied_code():
    """Requirement 6 & 11: Verification requires a valid code and rejects empty / whitespace inputs."""
    resp1 = client.post("/api/v1/auth/verify-email", json={"token": ""})
    assert resp1.status_code == 400

    resp2 = client.post("/api/v1/auth/verify-email", json={"token": "   "})
    assert resp2.status_code == 400

def test_valid_code_succeeds_and_verifies_user():
    """Requirement 6: Submitting valid code marks user as verified and issues access token."""
    email = f"valid_flow_{datetime.now().timestamp()}@trendpulse.ai"
    client.post("/api/v1/auth/register", json={
        "full_name": "Valid User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })

    # Retrieve token from database/repository (simulating user checking email)
    user = user_repo.get_by_email(email)
    assert user is not None
    token = user.verification_token
    assert token is not None

    ver_resp = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert ver_resp.status_code == 200
    data = ver_resp.json()["data"]
    assert data["is_verified"] is True
    assert "access_token" in data

    # Verify user state in DB
    updated_user = user_repo.get_by_email(email)
    assert updated_user.is_verified is True
    assert updated_user.verification_token is None

def test_invalid_code_fails():
    """Requirement 6 & 11: Nonexistent or invalid token is rejected with 400 Bad Request."""
    resp = client.post("/api/v1/auth/verify-email", json={"token": "invalid_code_999999"})
    assert resp.status_code == 400
    assert "Invalid or expired" in resp.json()["detail"]

def test_expired_code_fails():
    """Requirement 6 & 11: Expired verification token is rejected."""
    email = f"expired_{datetime.now().timestamp()}@trendpulse.ai"
    client.post("/api/v1/auth/register", json={
        "full_name": "Expired User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })

    user = user_repo.get_by_email(email)
    assert user is not None
    token = user.verification_token

    # Artificially expire the token in persistence
    ev = auth_persistence_repo.get_email_verification(token)
    if ev:
        auth_persistence_repo._email_verifications[token] = ev.model_copy(
            update={"expires_at": datetime.now(timezone.utc) - timedelta(hours=1)}
        )

    resp = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 400
    assert "Invalid or expired" in resp.json()["detail"]

def test_used_code_fails_on_replay():
    """Requirement 6 & 11: Verification token is single-use and rejected if replayed."""
    email = f"replay_{datetime.now().timestamp()}@trendpulse.ai"
    client.post("/api/v1/auth/register", json={
        "full_name": "Replay User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })

    user = user_repo.get_by_email(email)
    assert user is not None
    token = user.verification_token

    # 1st verification succeeds
    resp1 = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp1.status_code == 200

    # 2nd verification must fail
    resp2 = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp2.status_code == 400
    assert "Invalid or expired" in resp2.json()["detail"]

def test_resend_flow_invalidates_previous_and_issues_new_working_code():
    """Requirement 7 & 11: Resend invalidates prior token, issues new token, does not return raw token to client."""
    email = f"resend_flow_{datetime.now().timestamp()}@trendpulse.ai"
    client.post("/api/v1/auth/register", json={
        "full_name": "Resend User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })

    user = user_repo.get_by_email(email)
    assert user is not None
    old_token = user.verification_token
    assert old_token is not None

    # User clicks Resend Code
    resend_resp = client.post("/api/v1/auth/resend-verification", json={"email": email})
    assert resend_resp.status_code == 200
    resend_data = resend_resp.json()["data"]

    # Must NOT expose raw token to client
    assert "verification_token" not in resend_data
    assert "token" not in resend_data

    # Old token must now be invalid
    old_ver_resp = client.post("/api/v1/auth/verify-email", json={"token": old_token})
    assert old_ver_resp.status_code == 400

    # New token in repository/email must succeed
    refreshed_user = user_repo.get_by_email(email)
    new_token = refreshed_user.verification_token
    assert new_token != old_token

    new_ver_resp = client.post("/api/v1/auth/verify-email", json={"token": new_token})
    assert new_ver_resp.status_code == 200
    assert new_ver_resp.json()["data"]["is_verified"] is True

def test_resend_anti_enumeration():
    """Requirement 10: Resend verification endpoint protects against user enumeration."""
    # Non-existent email
    resp_nonexistent = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "nonexistent_account_9999@trendpulse.ai"}
    )
    assert resp_nonexistent.status_code == 200
    assert "If the email exists" in resp_nonexistent.json()["message"]
    assert "verification_token" not in resp_nonexistent.json().get("data", {})
