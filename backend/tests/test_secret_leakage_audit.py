import os
os.environ["DATA_BACKEND"] = "in_memory"

import re
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.core.config import settings
settings.DATA_BACKEND = "in_memory"

from backend.app.main import app

@pytest.fixture(autouse=True)
def setup_in_memory():
    orig = settings.DATA_BACKEND
    settings.DATA_BACKEND = "in_memory"
    os.environ["DATA_BACKEND"] = "in_memory"
    yield
    settings.DATA_BACKEND = orig

client = TestClient(app)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_SRC = ROOT_DIR / "frontend" / "src"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

SENSITIVE_PATTERNS = [
    (r"postgresql(\+asyncpg)?://\w+:[^@]+@", "PostgreSQL URL with Password"),
    (r"postgres://\w+:[^@]+@", "Postgres URL with Password"),
    (r"SUPABASE_SERVICE_ROLE_KEY\s*=\s*['\"][^'\"]+['\"]", "Supabase Service Role Key Assignment"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google/YouTube API Key Pattern"),
    (r"ghp_[0-9a-zA-Z]{36}", "GitHub Personal Access Token Pattern"),
    (r"github_pat_[0-9a-zA-Z_]{80,}", "GitHub Fine-Grained PAT Pattern"),
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private Key Header"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI/Anthropic Secret Key Pattern")
]

def test_frontend_src_free_of_secrets():
    """Verify that no sensitive credential patterns appear anywhere in frontend/src/."""
    assert FRONTEND_SRC.exists(), "frontend/src directory must exist"
    
    scanned_count = 0
    for root, _, files in os.walk(FRONTEND_SRC):
        for file in files:
            if file.endswith((".ts", ".tsx", ".js", ".jsx", ".json", ".html", ".css")):
                file_path = Path(root) / file
                scanned_count += 1
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                for pattern, name in SENSITIVE_PATTERNS:
                    match = re.search(pattern, content)
                    assert not match, f"Secret pattern '{name}' detected in {file_path.relative_to(ROOT_DIR)}"

    assert scanned_count > 0, "Expected to scan frontend source files"

def test_frontend_dist_bundle_free_of_secrets():
    """Verify that no sensitive credential patterns appear in built production assets (dist/)."""
    if not FRONTEND_DIST.exists():
        pytest.skip("frontend/dist not built yet; run npm run build first")

    scanned_count = 0
    for root, _, files in os.walk(FRONTEND_DIST):
        for file in files:
            if file.endswith((".js", ".css", ".html")):
                file_path = Path(root) / file
                scanned_count += 1
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                for pattern, name in SENSITIVE_PATTERNS:
                    match = re.search(pattern, content)
                    assert not match, f"Secret pattern '{name}' detected in production build {file_path.relative_to(ROOT_DIR)}"

    assert scanned_count > 0, "Expected to scan dist build files"

def test_api_responses_do_not_leak_password_hashes():
    """Verify that auth and user endpoints do not leak password hashes or internal secret keys."""
    # 1. Register test user
    email = "secret_audit_user@trendpulse.ai"
    reg_res = client.post("/api/v1/auth/register", json={
        "full_name": "Audit User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "terms_accepted": True
    })
    token = reg_res.json().get("data", {}).get("verification_token")
    if token:
        client.post("/api/v1/auth/verify-email", json={"token": token})

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    access_token = login_res.json().get("data", {}).get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}

    # Verify /auth/me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data_str = str(me_res.json()).lower()
    assert "password" not in me_res.json().get("data", {})
    assert "hashed_password" not in me_data_str
    assert "password_hash" not in me_data_str
    assert "$2b$" not in me_data_str  # bcrypt prefix

    # Verify /data-sources
    ds_res = client.get("/api/v1/data-sources", headers=headers)
    assert ds_res.status_code == 200
    ds_data_str = str(ds_res.json()).lower()
    assert "api_key" not in ds_data_str
    assert "secret" not in ds_data_str
    assert "token" not in ds_data_str or ds_data_str.count("token") <= 1

    # Verify /health/database
    h_res = client.get("/api/v1/health/database")
    assert h_res.status_code == 200
    h_data_str = str(h_res.json())
    assert "postgresql://" not in h_data_str
    assert "@" not in h_data_str
