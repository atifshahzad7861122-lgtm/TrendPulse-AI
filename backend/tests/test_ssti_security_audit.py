import os
os.environ["DATA_BACKEND"] = "in_memory"

import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import settings
settings.DATA_BACKEND = "in_memory"

from backend.app.main import app

client = TestClient(app)

PAYLOADS = [
    "{{7*7}}",
    "${7*7}",
    "<%= 7*7 %>",
    "#{7*7}",
    "{{config}}",
    "{{self}}",
    "{7*7}",
    "*{7*7}"
]

def register_verify_login(email: str, full_name: str):
    reg = client.post("/api/v1/auth/register", json={
        "full_name": full_name,
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
    access_token = login.json().get("data", {}).get("access_token")
    return {"Authorization": f"Bearer {access_token}"} if access_token else {}

def test_ssti_registration_and_auth_endpoints():
    """Verify that SSTI payloads in registration full_name are strictly treated as literal data."""
    for i, payload in enumerate(PAYLOADS):
        email = f"ssti_user_{i}@example.com"
        headers = register_verify_login(email, f"TestUser {payload}")
        assert "Authorization" in headers
        
        me_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        user_name = me_res.json().get("data", {}).get("full_name", "")
        # Must remain literal string, never evaluated to 49
        assert "49" not in user_name
        assert payload in user_name

def test_ssti_search_endpoint():
    """Verify that SSTI payloads in global search queries are never evaluated."""
    for payload in PAYLOADS:
        res = client.get("/api/v1/search", params={"q": payload})
        assert res.status_code == 200
        data = res.json()
        assert data.get("success") is True
        msg = data.get("message", "")
        assert payload in msg
        assert "49" not in msg

def test_ssti_report_generation():
    """Verify that SSTI payloads in report generation titles, categories, and templates are not evaluated."""
    headers = register_verify_login("ssti_report_user@example.com", "SSTI Reporter")
    for payload in PAYLOADS:
        rep_req = {
            "title": f"Report Title {payload}",
            "template": "Executive Briefing",
            "time_range": "30d",
            "category": f"Category {payload}",
            "platforms": ["YouTube", "TikTok"],
            "sections": ["Executive Summary", "Key Findings"]
        }
        res = client.post("/api/v1/reports/generate", json=rep_req, headers=headers)
        assert res.status_code == 200
        data = res.json()
        report_data = data.get("data", {})
        # Title must preserve literal string and never evaluate 7*7 -> 49
        assert payload in report_data.get("title", "")
        assert "49" not in report_data.get("title", "")

def test_ssti_workspace_setup():
    """Verify that SSTI payloads in workspace naming are literal."""
    headers = register_verify_login("ssti_workspace_user@example.com", "SSTI Workspace User")
    for payload in PAYLOADS:
        ws_req = {
            "name": f"Workspace {payload}",
            "industry": f"Industry {payload}",
            "use_case": f"UseCase {payload}",
            "currency": "USD",
            "default_dashboard": "signals",
            "data_sources": ["YouTube"]
        }
        res = client.post("/api/v1/workspace/setup", json=ws_req, headers=headers)
        assert res.status_code == 200
        data = res.json().get("data", {})
        assert payload in data.get("name", "")
        assert "49" not in data.get("name", "")
