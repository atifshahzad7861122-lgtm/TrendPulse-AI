import os
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.app.services.llm.provider import (
    LLMRequest, LLMResponse, LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMException, LLMInvalidResponseError
)
from backend.app.services.llm.providers.gemini_provider import GeminiProvider
from backend.app.core.config import settings

def test_gemini_provider_init_defaults():
    provider = GeminiProvider(api_key="test-gemini-key")
    assert provider.model == "gemini-1.5-flash"
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta"
    assert provider.api_key == "test-gemini-key"

def test_gemini_provider_missing_key():
    provider = GeminiProvider(api_key=None)
    with pytest.raises(LLMAuthError) as exc_info:
        provider.generate(LLMRequest(prompt="Hello Gemini"))
    assert "missing or not configured" in str(exc_info.value)

def test_gemini_provider_request_envelope():
    provider = GeminiProvider(api_key="test-key", model="gemini-1.5-flash")
    req = LLMRequest(
        prompt="Analyze product data",
        system_prompt="You are a strict data analyst.",
        temperature=0.2,
        max_tokens=1024,
        json_mode=True
    )

    mock_gemini_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"summary": "Top product", "confidence": 0.95}'}]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 250,
            "candidatesTokenCount": 80,
            "totalTokenCount": 330
        }
    }

    with patch("requests.post") as mock_post:
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 200
        mock_http_resp.ok = True
        mock_http_resp.json.return_value = mock_gemini_resp
        mock_post.return_value = mock_http_resp

        res = provider.generate(req)

        # Verify endpoint and headers
        assert mock_post.call_count == 1
        args, kwargs = mock_post.call_args
        url = args[0]
        assert "models/gemini-1.5-flash:generateContent" in url
        headers = kwargs["headers"]
        assert headers["x-goog-api-key"] == "test-key"
        assert headers["Content-Type"] == "application/json"

        # Verify payload structure
        payload = kwargs["json"]
        assert "systemInstruction" in payload
        assert payload["systemInstruction"]["parts"][0]["text"] == "You are a strict data analyst."
        assert payload["contents"][0]["role"] == "user"
        assert payload["contents"][0]["parts"][0]["text"] == "Analyze product data"
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["temperature"] == 0.2
        assert payload["generationConfig"]["maxOutputTokens"] == 1024

        # Verify parsed response
        assert res.provider == "gemini"
        assert res.model == "gemini-1.5-flash"
        assert res.input_tokens == 250
        assert res.output_tokens == 80
        assert res.total_tokens == 330
        assert res.parsed_json["summary"] == "Top product"
        assert res.parsed_json["confidence"] == 0.95
        assert res.estimated_cost > 0.0

def test_gemini_provider_json_markdown_fence_stripping():
    provider = GeminiProvider(api_key="test-key", model="gemini-1.5-flash")
    req = LLMRequest(prompt="Output json", json_mode=True)

    mock_gemini_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '```json\n{\n  "recommendation": "Buy now"\n}\n```'}]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 20, "totalTokenCount": 70}
    }

    with patch("requests.post") as mock_post:
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 200
        mock_http_resp.json.return_value = mock_gemini_resp
        mock_post.return_value = mock_http_resp

        res = provider.generate(req)
        assert res.parsed_json == {"recommendation": "Buy now"}

def test_gemini_provider_auth_error_handling():
    provider = GeminiProvider(api_key="invalid-gemini-key")
    with patch("requests.post") as mock_post:
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 400
        mock_http_resp.text = '{"error": {"code": 400, "message": "API_KEY_INVALID", "status": "INVALID_ARGUMENT"}}'
        mock_post.return_value = mock_http_resp

        with pytest.raises(LLMAuthError) as exc_info:
            provider.generate(LLMRequest(prompt="Test"))
        assert "API key rejected or invalid" in str(exc_info.value)
        # Verify raw secret was not exposed
        assert "invalid-gemini-key" not in str(exc_info.value)

def test_gemini_provider_rate_limit_error_handling():
    provider = GeminiProvider(api_key="test-key")
    with patch("requests.post") as mock_post:
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 429
        mock_http_resp.text = '{"error": {"code": 429, "message": "RESOURCE_EXHAUSTED", "status": "RESOURCE_EXHAUSTED"}}'
        mock_post.return_value = mock_http_resp

        with pytest.raises(LLMRateLimitError) as exc_info:
            provider.generate(LLMRequest(prompt="Test"))
        assert "quota / rate limit exceeded" in str(exc_info.value)

def test_gemini_cost_calculation():
    provider = GeminiProvider(api_key="test-key")
    # Flash: $0.075 / 1M input, $0.30 / 1M output
    cost_flash = provider.calculate_cost("gemini-1.5-flash", 10000, 2000)
    expected_flash = round((10000 * 0.000000075) + (2000 * 0.0000003), 6)
    assert cost_flash == expected_flash

    # Pro: $1.25 / 1M input, $5.00 / 1M output
    cost_pro = provider.calculate_cost("gemini-1.5-pro", 10000, 2000)
    expected_pro = round((10000 * 0.00000125) + (2000 * 0.000005), 6)
    assert cost_pro == expected_pro
