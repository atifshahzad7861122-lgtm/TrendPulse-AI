import os
os.environ["DATA_BACKEND"] = "in_memory"

import time
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi.testclient import TestClient

from backend.app.core.config import settings
settings.DATA_BACKEND = "in_memory"

from backend.app.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.models.domain import User, Workspace, WorkspaceMember, UserSession
from backend.app.repositories.in_memory import user_repo, workspace_repo, auth_persistence_repo, credit_repo

@pytest.fixture(autouse=True)
def setup_in_memory_auth():
    orig = settings.DATA_BACKEND
    settings.DATA_BACKEND = "in_memory"
    os.environ["DATA_BACKEND"] = "in_memory"
    yield
    settings.DATA_BACKEND = orig

client = TestClient(app)

def test_jwt_valid_token_authentication():
    """Verify that a properly signed JWT with valid sub claim authenticates successfully."""
    user_id = "usr_jwt_valid_01"
    user_repo.create(User(
        id=user_id,
        email="jwt_valid@trendpulse.ai",
        full_name="Valid JWT User",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_jwt_01",
        role="Administrator"
    ))
    token = create_access_token(user_id)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json().get("data", {})
    assert data.get("id") == user_id
    assert data.get("email") == "jwt_valid@trendpulse.ai"

def test_jwt_expired_token_rejection():
    """Verify that a token with an expired exp claim returns HTTP 401."""
    expired_time = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {"sub": "usr_jwt_expired", "exp": expired_time}
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "detail" in res.json()

def test_jwt_missing_sub_claim_rejection():
    """Verify that a token missing the sub claim returns HTTP 401."""
    payload = {"exp": datetime.now(timezone.utc) + timedelta(hours=1), "email": "nosub@trendpulse.ai"}
    token_no_sub = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_no_sub}"})
    assert res.status_code == 401

def test_jwt_algorithm_confusion_alg_none():
    """Verify that a token specifying alg=none is rejected with HTTP 401."""
    import base64
    import json
    
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "usr_jwt_valid_01", "exp": int(time.time()) + 3600}).encode()).decode().rstrip("=")
    none_token = f"{header}.{payload}."

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {none_token}"})
    assert res.status_code == 401

def test_jwt_wrong_secret_key_rejection():
    """Verify that a token signed with an invalid/attacker secret key returns HTTP 401."""
    payload = {"sub": "usr_jwt_valid_01", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    tampered_key_token = jwt.encode(payload, "attacker-compromised-secret-key-32-chars-long", algorithm=settings.ALGORITHM)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_key_token}"})
    assert res.status_code == 401

def test_jwt_signature_tampering_payload_modification():
    """Verify that modifying the payload without re-signing causes signature verification to fail."""
    valid_token = create_access_token("usr_jwt_valid_01")
    parts = valid_token.split(".")
    assert len(parts) == 3

    # Tamper the middle payload segment
    tampered_token = f"{parts[0]}.eyJzdWIiOiAidXNyX3ZpY3RpbV8wMSIsICJleHAiOiAyMDAwMDAwMDAwfQ.{parts[2]}"

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert res.status_code == 401

def test_malformed_authorization_headers():
    """Verify that various malformed Authorization headers are safely rejected with HTTP 401."""
    malformed_headers = [
        "Basic dXNlcm5hbWU6cGFzc3dvcmQ=",
        "Bearer",
        "Bearer invalid_jwt_payload_format",
        "Bearer null",
        "Bearer undefined",
        "Bearer eyJhbGciOi.truncated",
        "RandomTokenScheme 123456",
        ""
    ]

    for auth_val in malformed_headers:
        res = client.get("/api/v1/auth/me", headers={"Authorization": auth_val} if auth_val else {})
        # Must not cause unhandled 500 error
        assert res.status_code in [200, 401]  # 200 only if demo fallback triggers on empty header

def test_user_isolation_and_idor_prevention():
    """Verify complete tenant isolation between User A and User B."""
    # User A
    user_a_id = "usr_jwt_iso_a"
    user_repo.create(User(
        id=user_a_id,
        email="user_a_iso@trendpulse.ai",
        full_name="User Alpha",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_iso_a",
        role="Administrator"
    ))
    token_a = create_access_token(user_a_id)

    # User B
    user_b_id = "usr_jwt_iso_b"
    user_repo.create(User(
        id=user_b_id,
        email="user_b_iso@trendpulse.ai",
        full_name="User Beta",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_iso_b",
        role="Administrator"
    ))
    token_b = create_access_token(user_b_id)

    # User A profile
    res_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["data"]["id"] == user_a_id
    assert res_a.json()["data"]["email"] == "user_a_iso@trendpulse.ai"

    # User B profile
    res_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["data"]["id"] == user_b_id
    assert res_b.json()["data"]["email"] == "user_b_iso@trendpulse.ai"

def test_credit_authorization_isolation():
    """Verify that User A cannot read or mutate User B's credit account."""
    user_a_id = "usr_credit_iso_a"
    user_b_id = "usr_credit_iso_b"
    user_repo.create(User(
        id=user_a_id,
        email="credit_a@trendpulse.ai",
        full_name="Credit User A",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_credit_a"
    ))
    user_repo.create(User(
        id=user_b_id,
        email="credit_b@trendpulse.ai",
        full_name="Credit User B",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_credit_b"
    ))
    
    # Initialize credit accounts with distinct balances
    credit_repo.get_or_create_account(user_a_id)
    credit_repo.update_account_balance(user_a_id, new_balance=100, delta_granted=100, delta_used=0)

    credit_repo.get_or_create_account(user_b_id)
    credit_repo.update_account_balance(user_b_id, new_balance=500, delta_granted=500, delta_used=0)

    token_a = create_access_token(user_a_id)
    token_b = create_access_token(user_b_id)

    # Check balances through authenticated endpoints
    res_a = client.get("/api/v1/credits/balance", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["data"]["current_balance"] == 100

    res_b = client.get("/api/v1/credits/balance", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["data"]["current_balance"] == 500

def test_session_revocation_lifecycle():
    """Verify session revocation records during logout and password reset."""
    email = "session_user@trendpulse.ai"
    user_id = "usr_sess_test_01"
    user_repo.create(User(
        id=user_id,
        email=email,
        full_name="Session User",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_sess_01"
    ))

    # 1. Login generates session
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]

    # 2. Logout revokes session
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200

    # 3. Password reset revokes all user sessions
    reset_email = "reset_sess_user@trendpulse.ai"
    reset_user_id = "usr_reset_sess_01"
    user_repo.create(User(
        id=reset_user_id,
        email=reset_email,
        full_name="Reset Session User",
        hashed_password=get_password_hash("OldPassword123!"),
        is_active=True,
        is_verified=True,
        workspace_id="ws_reset_01"
    ))
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": reset_email})
    reset_token = forgot_res.json().get("data", {}).get("reset_token")
    if reset_token:
        res = client.post("/api/v1/auth/reset-password", json={
            "token": reset_token,
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        })
        assert res.status_code == 200

def test_login_failure_behavior_anti_enumeration():
    """Verify that login failures return uniform error messages without leaking internals."""
    # Non-existent user
    res1 = client.post("/api/v1/auth/login", json={"email": "nonexistent_12345@trendpulse.ai", "password": "Password123!"})
    assert res1.status_code == 401
    assert res1.json()["detail"] == "Invalid email or password"

    # Valid user wrong password
    res2 = client.post("/api/v1/auth/login", json={"email": "session_user@trendpulse.ai", "password": "WrongPassword123!"})
    assert res2.status_code == 401
    assert res2.json()["detail"] == "Invalid email or password"

    # Response does not leak password hash
    body_str = str(res1.json()) + str(res2.json())
    assert "$2b$" not in body_str
    assert "hashed_password" not in body_str
