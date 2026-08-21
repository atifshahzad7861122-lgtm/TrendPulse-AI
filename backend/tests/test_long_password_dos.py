import os
os.environ["DATA_BACKEND"] = "in_memory"

import time
import pytest
from unittest.mock import patch
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

VALID_LENGTHS = [8, 32, 64, 127, 128]
OVERSIZED_LENGTHS = [129, 256, 512, 1024, 2048, 4096, 8192]

def test_password_length_matrix_registration():
    """
    Test password lengths: 8, 32, 64, 127, 128 (pass schema validation)
    and 129, 256, 512, 1024, 2048, 4096, 8192 (HTTP 422 rejected).
    """
    # 1. Valid lengths
    for length in VALID_LENGTHS:
        pw = "A1!" + ("a" * (length - 3))
        res = client.post("/api/v1/auth/register", json={
            "full_name": "Valid Length User",
            "email": f"valid_pw_{length}@trendpulse.ai",
            "password": pw,
            "confirm_password": pw,
            "terms_accepted": True
        })
        assert res.status_code == 200, f"Expected 200 for length {length}, got {res.status_code}"

    # 2. Oversized lengths
    for length in OVERSIZED_LENGTHS:
        pw = "A1!" + ("a" * (length - 3))
        start = time.perf_counter()
        res = client.post("/api/v1/auth/register", json={
            "full_name": "Oversized User",
            "email": f"oversized_pw_{length}@trendpulse.ai",
            "password": pw,
            "confirm_password": pw,
            "terms_accepted": True
        })
        elapsed = time.perf_counter() - start
        assert res.status_code == 422, f"Expected 422 for length {length}, got {res.status_code}"
        assert elapsed < 0.2, f"Validation took too long ({elapsed:.4f}s) on length {length}"

def test_registration_bcrypt_hashpw_never_called_on_oversized():
    """
    Verify bcrypt.hashpw call count remains exactly 0 for all oversized registration attempts.
    """
    with patch("bcrypt.hashpw") as mock_hashpw:
        for length in OVERSIZED_LENGTHS:
            pw = "A" * length
            res = client.post("/api/v1/auth/register", json={
                "full_name": "Test User",
                "email": f"dos_reg_{length}@trendpulse.ai",
                "password": pw,
                "confirm_password": pw,
                "terms_accepted": True
            })
            assert res.status_code == 422
            mock_hashpw.assert_not_called()

def test_login_bcrypt_checkpw_never_called_on_oversized():
    """
    Verify bcrypt.checkpw call count remains exactly 0 for all oversized login attempts.
    """
    with patch("bcrypt.checkpw") as mock_checkpw:
        for length in OVERSIZED_LENGTHS:
            pw = "A" * length
            start = time.perf_counter()
            res = client.post("/api/v1/auth/login", json={
                "email": "victim@trendpulse.ai",
                "password": pw
            })
            elapsed = time.perf_counter() - start
            assert res.status_code == 422
            assert elapsed < 0.2, f"Login validation took {elapsed:.4f}s on {length} chars"
            mock_checkpw.assert_not_called()

def test_password_reset_bcrypt_never_called_on_oversized():
    """
    Verify bcrypt.hashpw is not called on oversized password reset attempts.
    """
    with patch("bcrypt.hashpw") as mock_hashpw:
        for length in OVERSIZED_LENGTHS:
            pw = "A" * length
            start = time.perf_counter()
            res = client.post("/api/v1/auth/reset-password", json={
                "token": "valid_mock_token_12345",
                "new_password": pw,
                "confirm_password": pw
            })
            elapsed = time.perf_counter() - start
            assert res.status_code == 422
            assert elapsed < 0.2, f"Reset validation took {elapsed:.4f}s on {length} chars"
            mock_hashpw.assert_not_called()

def test_confirm_password_boundary_bypass_prevention():
    """
    Verify that an attacker cannot bypass the limit by setting password <= 128 but confirm_password > 128.
    """
    valid_pw = "Password123!"
    for length in OVERSIZED_LENGTHS:
        long_confirm = "A" * length
        res = client.post("/api/v1/auth/register", json={
            "full_name": "Bypass Attacker",
            "email": f"bypass_{length}@trendpulse.ai",
            "password": valid_pw,
            "confirm_password": long_confirm,
            "terms_accepted": True
        })
        assert res.status_code == 422, f"Confirm password bypass not blocked on length {length}"
