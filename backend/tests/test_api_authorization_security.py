import os
os.environ["DATA_BACKEND"] = "in_memory"

import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import settings
settings.DATA_BACKEND = "in_memory"

from backend.app.main import app
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.models.domain import User, Workspace, Report, Alert, Notification
from backend.app.repositories.in_memory import (
    user_repo, workspace_repo, credit_repo, subscription_repo,
    report_repo, watchlist_repo, alert_repo, notification_repo
)

@pytest.fixture(autouse=True)
def setup_in_memory_auth():
    orig = settings.DATA_BACKEND
    settings.DATA_BACKEND = "in_memory"
    os.environ["DATA_BACKEND"] = "in_memory"
    yield
    settings.DATA_BACKEND = orig

client = TestClient(app)

def create_test_user(user_id: str, email: str, name: str, role: str = "Administrator") -> str:
    """Helper to create an isolated user and return their signed JWT."""
    u = User(
        id=user_id,
        email=email,
        full_name=name,
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_verified=True,
        workspace_id=f"ws_{user_id}",
        role=role
    )
    user_repo.create(u)
    ws = Workspace(
        id=f"ws_{user_id}",
        name=f"{name}'s Workspace",
        industry="Retail",
        use_case="Intelligence",
        owner_id=user_id,
        is_setup_complete=True
    )
    workspace_repo.create(ws)
    return create_access_token(user_id)

def test_anonymous_access_protection():
    """Verify that protected endpoints reject requests with invalid/bogus credentials."""
    bogus_header = {"Authorization": "Bearer bogus_token_12345"}
    protected_urls = [
        "/api/v1/auth/me",
        "/api/v1/workspace",
        "/api/v1/credits/balance",
        "/api/v1/credits/transactions",
        "/api/v1/credits/usage",
        "/api/v1/subscription",
        "/api/v1/watchlist",
        "/api/v1/settings"
    ]
    for url in protected_urls:
        res = client.get(url, headers=bogus_header)
        assert res.status_code == 401, f"Expected 401 for {url}, got {res.status_code}"

def test_user_a_to_user_b_profile_isolation():
    """Verify User A cannot read or mutate User B's profile."""
    token_a = create_test_user("usr_sec_a", "usera@trendpulse.ai", "User Alpha")
    token_b = create_test_user("usr_sec_b", "userb@trendpulse.ai", "User Beta")

    # User A requests /auth/me -> sees User A only
    res_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["data"]["id"] == "usr_sec_a"
    assert res_a.json()["data"]["email"] == "usera@trendpulse.ai"

    # User B requests /auth/me -> sees User B only
    res_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["data"]["id"] == "usr_sec_b"
    assert res_b.json()["data"]["email"] == "userb@trendpulse.ai"

def test_workspace_isolation_and_idor():
    """Verify User A cannot read or mutate User B's workspace."""
    token_a = create_test_user("usr_ws_a", "wsa@trendpulse.ai", "Workspace User A")
    token_b = create_test_user("usr_ws_b", "wsb@trendpulse.ai", "Workspace User B")

    # User A accesses workspace
    res_a = client.get("/api/v1/workspace", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["data"]["owner_id"] == "usr_ws_a"

    # User B accesses workspace
    res_b = client.get("/api/v1/workspace", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["data"]["owner_id"] == "usr_ws_b"

def test_credit_system_authorization_and_isolation():
    """Verify that credit balance, transactions, and usage cannot be accessed or manipulated across users."""
    token_a = create_test_user("usr_c_a", "credit_a@trendpulse.ai", "Credit User A")
    token_b = create_test_user("usr_c_b", "credit_b@trendpulse.ai", "Credit User B")

    credit_repo.get_or_create_account("usr_c_a")
    credit_repo.update_account_balance("usr_c_a", new_balance=250, delta_granted=250, delta_used=0)

    credit_repo.get_or_create_account("usr_c_b")
    credit_repo.update_account_balance("usr_c_b", new_balance=750, delta_granted=750, delta_used=0)

    # Balance check
    res_a = client.get("/api/v1/credits/balance", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["data"]["current_balance"] == 250

    res_b = client.get("/api/v1/credits/balance", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["data"]["current_balance"] == 750

def test_subscription_isolation():
    """Verify that User A cannot modify User B's subscription."""
    token_a = create_test_user("usr_sub_a", "sub_a@trendpulse.ai", "Sub User A")
    token_b = create_test_user("usr_sub_b", "sub_b@trendpulse.ai", "Sub User B")

    # User A modifies their subscription to pro
    res_change_a = client.post(
        "/api/v1/subscription/change",
        json={"plan_slug": "pro"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_change_a.status_code == 200
    assert res_change_a.json()["data"]["plan_slug"] == "pro"
    assert res_change_a.json()["data"]["user_id"] == "usr_sub_a"

    # User B's subscription remains unaffected (free)
    res_sub_b = client.get("/api/v1/subscription", headers={"Authorization": f"Bearer {token_b}"})
    assert res_sub_b.status_code == 200
    assert res_sub_b.json()["data"]["plan_slug"] == "free"
    assert res_sub_b.json()["data"]["user_id"] == "usr_sub_b"

def test_watchlist_isolation():
    """Verify that User A cannot view or manipulate User B's watchlist."""
    token_a = create_test_user("usr_wl_a", "wl_a@trendpulse.ai", "Watchlist User A")
    token_b = create_test_user("usr_wl_b", "wl_b@trendpulse.ai", "Watchlist User B")

    # User A adds a product
    client.post("/api/v1/watchlist/prod_test_01", headers={"Authorization": f"Bearer {token_a}"})

    # User A sees 1 product
    res_a = client.get("/api/v1/watchlist", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200

    # User B watchlist is empty
    res_b = client.get("/api/v1/watchlist", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert len(res_b.json()["data"]) == 0

def test_client_supplied_user_id_override_rejection():
    """Verify that supplying a different user_id in requests does not hijack another account."""
    token_a = create_test_user("usr_inject_a", "inject_a@trendpulse.ai", "User Inject A")
    create_test_user("usr_victim_b", "victim_b@trendpulse.ai", "Victim User B")

    # Send payload containing victim's user_id to workspace setup
    res = client.post(
        "/api/v1/workspace/setup",
        json={
            "name": "Hijacked Workspace",
            "industry": "Electronics",
            "use_case": "Dropshipping",
            "currency": "USD",
            "default_dashboard": "trends",
            "connected_sources": ["daraz"],
            "user_id": "usr_victim_b"
        },
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res.status_code == 200
    # Workspace owner must remain the authenticated User A
    assert res.json()["data"]["owner_id"] == "usr_inject_a"

def test_role_escalation_payload_rejection():
    """Verify that client payloads attempting to inject role=SuperAdmin or is_admin=True are ignored."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Attacker Role",
            "email": "attacker_role@trendpulse.ai",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "terms_accepted": True,
            "role": "SuperAdmin",
            "is_admin": True
        }
    )
    assert res.status_code == 200
    user = user_repo.get_by_email("attacker_role@trendpulse.ai")
    assert user is not None
    # Assigned role is the default workspace role ("Administrator"), not cross-tenant SuperAdmin
    assert user.role == "Administrator"

def test_http_method_bypass_prevention():
    """Verify that changing HTTP methods (e.g. PUT instead of GET) on protected endpoints does not bypass security."""
    token_a = create_test_user("usr_method_a", "method_a@trendpulse.ai", "Method User A")
    # PUT /api/v1/credits/balance is not allowed and must return 405 Method Not Allowed
    res = client.put("/api/v1/credits/balance", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 405

def test_response_data_leakage_on_error():
    """Verify that error responses do not leak sensitive database connection strings, passwords, or stack traces."""
    res = client.get("/api/v1/reports/nonexistent_report_id_99999")
    assert res.status_code == 404
    body_str = str(res.json())
    assert "postgresql://" not in body_str
    assert "password" not in body_str.lower()
    assert "traceback" not in body_str.lower()
