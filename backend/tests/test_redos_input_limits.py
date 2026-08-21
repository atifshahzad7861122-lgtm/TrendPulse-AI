import os
os.environ["DATA_BACKEND"] = "in_memory"

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.core.config import settings
settings.DATA_BACKEND = "in_memory"

from backend.app.main import app

client = TestClient(app)

def get_auth_token(email="limit_tester@trendpulse.ai"):
    reg = client.post("/api/v1/auth/register", json={
        "full_name": "Limit Tester",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    token = reg.json().get("data", {}).get("verification_token")
    if token:
        client.post("/api/v1/auth/verify-email", json={"token": token})
    
    login = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    return login.json().get("data", {}).get("access_token")

# =========================================================================
# 1. PASSWORD BOUNDARY TESTS (127, 128, 129)
# =========================================================================
def test_password_length_boundary_registration():
    """Test 127 and 128 chars accepted, 129 chars rejected with 422."""
    # 127 characters
    p127 = "A1!" + ("a" * 124)
    res_127 = client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "pass127@example.com",
        "password": p127,
        "confirm_password": p127,
        "terms_accepted": True
    })
    assert res_127.status_code == 200, f"Expected 200 for 127-char password, got {res_127.status_code}"

    # 128 characters
    p128 = "A1!" + ("a" * 125)
    res_128 = client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "pass128@example.com",
        "password": p128,
        "confirm_password": p128,
        "terms_accepted": True
    })
    assert res_128.status_code == 200, f"Expected 200 for 128-char password, got {res_128.status_code}"

    # 129 characters -> 422 Unprocessable Entity
    p129 = "A1!" + ("a" * 126)
    res_129 = client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "pass129@example.com",
        "password": p129,
        "confirm_password": p129,
        "terms_accepted": True
    })
    assert res_129.status_code == 422, f"Expected 422 for 129-char password, got {res_129.status_code}"

def test_password_oversized_never_reaches_bcrypt():
    """Verify that a 129+ character password triggers 422 before bcrypt is ever called."""
    with patch("bcrypt.checkpw") as mock_checkpw, patch("bcrypt.hashpw") as mock_hashpw:
        p129 = "A1!" + ("a" * 126)
        
        # 1. Login with 129 chars
        res_login = client.post("/api/v1/auth/login", json={
            "email": "pass128@example.com",
            "password": p129
        })
        assert res_login.status_code == 422
        mock_checkpw.assert_not_called()

        # 2. Register with 129 chars
        res_reg = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "pass129_mock@example.com",
            "password": p129,
            "confirm_password": p129,
            "terms_accepted": True
        })
        assert res_reg.status_code == 422
        mock_hashpw.assert_not_called()

# =========================================================================
# 2. FULL NAME BOUNDARY TESTS (99, 100, 101)
# =========================================================================
def test_full_name_length_boundary():
    """Test 99 and 100 chars accepted, 101 chars rejected with 422."""
    n99 = "A" * 99
    res_99 = client.post("/api/v1/auth/register", json={
        "full_name": n99,
        "email": "name99@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    assert res_99.status_code == 200, f"Expected 200 for 99-char name, got {res_99.status_code}"

    n100 = "A" * 100
    res_100 = client.post("/api/v1/auth/register", json={
        "full_name": n100,
        "email": "name100@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    assert res_100.status_code == 200, f"Expected 200 for 100-char name, got {res_100.status_code}"

    n101 = "A" * 101
    res_101 = client.post("/api/v1/auth/register", json={
        "full_name": n101,
        "email": "name101@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    assert res_101.status_code == 422, f"Expected 422 for 101-char name, got {res_101.status_code}"

# =========================================================================
# 3. WORKSPACE NAME BOUNDARY TESTS (99, 100, 101)
# =========================================================================
def test_workspace_name_length_boundary():
    """Test 99 and 100 chars accepted, 101 chars rejected with 422."""
    token = get_auth_token("ws_tester@trendpulse.ai")
    headers = {"Authorization": f"Bearer {token}"}

    w99 = "W" * 99
    res_99 = client.post("/api/v1/workspace/setup", json={
        "name": w99,
        "industry": "Tech",
        "use_case": "Arbitrage",
        "currency": "USD"
    }, headers=headers)
    assert res_99.status_code == 200, f"Expected 200 for 99-char workspace, got {res_99.status_code}"

    w100 = "W" * 100
    res_100 = client.post("/api/v1/workspace/setup", json={
        "name": w100,
        "industry": "Tech",
        "use_case": "Arbitrage",
        "currency": "USD"
    }, headers=headers)
    assert res_100.status_code == 200, f"Expected 200 for 100-char workspace, got {res_100.status_code}"

    w101 = "W" * 101
    res_101 = client.post("/api/v1/workspace/setup", json={
        "name": w101,
        "industry": "Tech",
        "use_case": "Arbitrage",
        "currency": "USD"
    }, headers=headers)
    assert res_101.status_code == 422, f"Expected 422 for 101-char workspace, got {res_101.status_code}"

# =========================================================================
# 4. REPORT TITLE BOUNDARY TESTS (254, 255, 256)
# =========================================================================
def test_report_title_length_boundary():
    """Test 254 and 255 chars accepted, 256 chars rejected with 422."""
    token = get_auth_token("rep_tester@trendpulse.ai")
    headers = {"Authorization": f"Bearer {token}"}

    t254 = "R" * 254
    res_254 = client.post("/api/v1/reports/generate", json={
        "title": t254,
        "template": "Executive Briefing",
        "time_range": "30d"
    }, headers=headers)
    assert res_254.status_code == 200, f"Expected 200 for 254-char title, got {res_254.status_code}"

    t255 = "R" * 255
    res_255 = client.post("/api/v1/reports/generate", json={
        "title": t255,
        "template": "Executive Briefing",
        "time_range": "30d"
    }, headers=headers)
    assert res_255.status_code == 200, f"Expected 200 for 255-char title, got {res_255.status_code}"

    t256 = "R" * 256
    res_256 = client.post("/api/v1/reports/generate", json={
        "title": t256,
        "template": "Executive Briefing",
        "time_range": "30d"
    }, headers=headers)
    assert res_256.status_code == 422, f"Expected 422 for 256-char title, got {res_256.status_code}"

# =========================================================================
# 5. SEARCH QUERY BOUNDARY TESTS (199, 200, 201)
# =========================================================================
def test_search_query_length_boundary():
    """Test 199 and 200 chars accepted, 201 chars rejected with 422."""
    q199 = "s" * 199
    res_199 = client.get("/api/v1/search", params={"q": q199})
    assert res_199.status_code == 200, f"Expected 200 for 199-char search query, got {res_199.status_code}"

    q200 = "s" * 200
    res_200 = client.get("/api/v1/search", params={"q": q200})
    assert res_200.status_code == 200, f"Expected 200 for 200-char search query, got {res_200.status_code}"

    q201 = "s" * 201
    res_201 = client.get("/api/v1/search", params={"q": q201})
    assert res_201.status_code == 422, f"Expected 422 for 201-char search query, got {res_201.status_code}"
