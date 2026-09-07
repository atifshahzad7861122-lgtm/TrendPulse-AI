import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.app.main import app
from backend.app.api.deps import get_user_repository
from backend.app.services.email_service import email_service

client = TestClient(app)

def test_demo_email_verification_flow():
    """Verify demo verification mechanism when email delivery is not configured."""
    user_repo = get_user_repository()
    test_email = "demo_verifier_test@trendpulse.ai"

    # 1. Register a test user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Demo Verifier",
            "email": test_email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True
        }
    )
    assert reg_resp.status_code == 200

    # Ensure email_service is unconfigured
    with patch.object(email_service, "is_configured", return_value=False):
        # A. Random code without email should be rejected (400)
        res_fail = client.post("/api/v1/auth/verify-email", json={"token": "random_fake_code_999"})
        assert res_fail.status_code == 400

        # B. Any code WITH registered email should verify successfully in demo mode
        res_ok = client.post("/api/v1/auth/verify-email", json={"token": "123456", "email": test_email})
        assert res_ok.status_code == 200
        data = res_ok.json()["data"]
        assert data["is_verified"] is True
        assert "access_token" in data

    # Verify user state in repository
    user = user_repo.get_by_email(test_email)
    assert user is not None
    assert user.is_verified is True


def test_production_email_verification_strictness():
    """Verify that when email_service IS configured, only real valid tokens are accepted."""
    test_email = "strict_prod_test@trendpulse.ai"

    # Register user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Strict Prod Verifier",
            "email": test_email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True
        }
    )
    assert reg_resp.status_code == 200

    user_repo = get_user_repository()
    user = user_repo.get_by_email(test_email)
    real_token = user.verification_token
    assert real_token is not None

    # Simulate configured production email provider
    with patch.object(email_service, "is_configured", return_value=True):
        # A. Arbitrary code with email must be REJECTED in production mode
        res_rejected = client.post("/api/v1/auth/verify-email", json={"token": "123456", "email": test_email})
        assert res_rejected.status_code == 400

        # B. Real token must SUCCEED in production mode
        res_success = client.post("/api/v1/auth/verify-email", json={"token": real_token})
        assert res_success.status_code == 200
        assert res_success.json()["data"]["is_verified"] is True


def test_registration_hackathon_demo_mode():
    """Verify that when EMAIL_VERIFICATION_ENABLED=False, registration directly issues access_token and marks user verified."""
    from backend.app.core.config import settings

    test_email = "hackathon_demo_direct@trendpulse.ai"

    with patch.object(settings, "EMAIL_VERIFICATION_ENABLED", False):
        reg_resp = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Demo Direct User",
                "email": test_email,
                "password": "Password123!",
                "confirm_password": "Password123!",
                "terms_accepted": True
            }
        )
        assert reg_resp.status_code == 200
        data = reg_resp.json()["data"]

        # Direct onboarding payload returned
        assert data["is_verified"] is True
        assert "access_token" in data
        assert len(data["access_token"]) > 20
        assert data["workspace_id"] is not None
        assert data["email_verification_enabled"] is False

        # Verify database record
        user_repo = get_user_repository()
        user = user_repo.get_by_email(test_email)
        assert user is not None
        assert user.is_verified is True
        # Architecture intact: verification_token is still created for future auditing/records
        assert user.verification_token is not None


def test_registration_production_mode_verification_required():
    """Verify that when EMAIL_VERIFICATION_ENABLED=True, registration requires email verification."""
    from backend.app.core.config import settings

    test_email = "production_strict_user@trendpulse.ai"

    with patch.object(settings, "EMAIL_VERIFICATION_ENABLED", True):
        reg_resp = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Production Strict User",
                "email": test_email,
                "password": "Password123!",
                "confirm_password": "Password123!",
                "terms_accepted": True
            }
        )
        assert reg_resp.status_code == 200
        data = reg_resp.json()["data"]

        # Verification required payload
        assert data["is_verified"] is False
        assert "access_token" not in data
        assert data["email_verification_enabled"] is True

        # Verify database record
        user_repo = get_user_repository()
        user = user_repo.get_by_email(test_email)
        assert user is not None
        assert user.is_verified is False
        assert user.verification_token is not None

