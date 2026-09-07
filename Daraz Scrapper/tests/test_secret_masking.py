"""Tests for logging secret masking and redaction."""

from app.core.logging import mask_secrets


def test_mask_secrets_api_keys_and_passwords():
    raw_log = "Request failed: api_key=secret_12345&password=SuperSecretPassword123"
    masked = mask_secrets(raw_log)
    assert "secret_12345" not in masked
    assert "SuperSecretPassword123" not in masked
    assert "***REDACTED***" in masked


def test_mask_secrets_bearer_tokens():
    raw_log = "Authorization header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    masked = mask_secrets(raw_log)
    assert "eyJhbGci" not in masked
    assert "***REDACTED***" in masked


def test_mask_secrets_cookies():
    raw_log = "Cookie: session=sess_token_abcdef987; user=john"
    masked = mask_secrets(raw_log)
    assert "sess_token_abcdef987" not in masked
    assert "***REDACTED***" in masked
