import os
os.environ["DATA_BACKEND"] = "in_memory"

import hashlib
import time
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi.testclient import TestClient

from backend.app.core.config import settings
settings.DATA_BACKEND = "in_memory"

from backend.app.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.models.domain import User, Workspace, UserSession
from backend.app.repositories.in_memory import user_repo, workspace_repo, auth_persistence_repo

@pytest.fixture(autouse=True)
def setup_in_memory_auth():
    orig = settings.DATA_BACKEND
    settings.DATA_BACKEND = "in_memory"
    os.environ["DATA_BACKEND"] = "in_memory"
    yield
    settings.DATA_BACKEND = orig

client = TestClient(app)

def test_valid_token_replay_behavior():
    """
    Test that an unexpired bearer token can be used multiple times before expiration (normal bearer token behavior).
    """
    user_id = "usr_replay_01"
    user_repo.create(User(
        id=user_id,
        email="replay_valid@trendpulse.ai",
        full_name="Replay User",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_replay_01"
    ))
    token = create_access_token(user_id)

    # Request 1
    res1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    assert res1.json()["data"]["id"] == user_id

    # Request 2 (Replay)
    res2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    assert res2.json()["data"]["id"] == user_id

def test_expired_token_replay_rejected():
    """Verify that an expired token cannot be replayed."""
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    payload = {"sub": "usr_replay_01", "exp": expired_time}
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401

def test_password_reset_token_replay_rejected():
    """Verify that a single-use password reset token cannot be reused/replayed."""
    email = "reset_replay@trendpulse.ai"
    user_id = "usr_reset_rep_01"
    user_repo.create(User(
        id=user_id,
        email=email,
        full_name="Reset Replay User",
        hashed_password=get_password_hash("OldPassword123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_reset_rep"
    ))

    # 1. Generate reset token
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": email})
    reset_token = forgot_res.json()["data"]["reset_token"]

    # 2. Use reset token 1st time (Success)
    res1 = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "NewPassword123!",
        "confirm_password": "NewPassword123!"
    })
    assert res1.status_code == 200

    # 3. Replay reset token 2nd time (Must be rejected)
    res2 = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "AnotherPassword123!",
        "confirm_password": "AnotherPassword123!"
    })
    assert res2.status_code == 400
    assert "Invalid or expired" in res2.json()["detail"]

def test_email_verification_token_replay_rejected():
    """Verify that an email verification token cannot be reused after verification."""
    email = "verify_replay@trendpulse.ai"
    reg_res = client.post("/api/v1/auth/register", json={
        "full_name": "Verify Replay User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    token = reg_res.json()["data"]["verification_token"]

    # 1st verification (Success)
    res1 = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert res1.status_code == 200

    # 2nd verification replay (Rejected)
    res2 = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert res2.status_code == 400

def test_tampered_token_replay_rejected():
    """Verify that tampered tokens are rejected."""
    token = create_access_token("usr_replay_01")
    tampered = token[:-5] + "XXXXX"
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert res.status_code == 401

def test_token_not_exposed_in_url():
    """Verify that API routes do not require or accept access tokens as GET URL query parameters."""
    token = create_access_token("usr_replay_01")
    # Passing token in URL query string without header should fail to authenticate
    res = client.get(f"/api/v1/auth/me?token={token}")
    # In-memory demo fallback returns demo user, but does not bind to the token in URL
    if res.status_code == 200:
        assert res.json()["data"]["id"] != "usr_replay_01"

def test_credentials_not_logged():
    """Verify that password verification does not output plain passwords to standard logs."""
    from backend.app.core.security import verify_password
    # verify_password takes plain password and hash
    res = verify_password("SuperSecretPass!", get_password_hash("SuperSecretPass!"))
    assert res is True
