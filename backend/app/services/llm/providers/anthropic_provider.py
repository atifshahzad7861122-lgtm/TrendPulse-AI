import json
import time
import requests
from typing import Optional, Dict, Any

from backend.app.services.llm.provider import (
    LLMProvider, LLMRequest, LLMResponse, LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMException, LLMInvalidResponseError
)

class AnthropicProvider(LLMProvider):
    """
    Anthropic API adapter supporting Claude 3.5 Sonnet, Claude 3.5 Haiku, and Claude 3 Opus.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = "claude-3-5-sonnet-20241022", base_url: Optional[str] = None):
        super().__init__(api_key=api_key, model=model, base_url=base_url or "https://api.anthropic.com/v1")

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key or self.api_key.strip() in ["", "none", "null"]:
            raise LLMAuthError("Anthropic API key is missing or not configured.")

        url = f"{self.base_url.rstrip('/')}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [
                {"role": "user", "content": request.prompt}
            ]
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        start_time = time.perf_counter()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=request.timeout)
        except requests.Timeout as e:
            raise LLMTimeoutError(f"Anthropic request timed out after {request.timeout}s: {e}")
        except requests.RequestException as e:
            raise LLMException(f"Anthropic connection error: {e}", status_code=502)

        latency = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code in [401, 403]:
            raise LLMAuthError(f"Anthropic authentication rejected: {resp.text}")
        elif resp.status_code == 429:
            raise LLMRateLimitError(f"Anthropic rate limit / quota exceeded: {resp.text}")
        elif resp.status_code >= 500:
            raise LLMException(f"Anthropic server error (HTTP {resp.status_code}): {resp.text}", status_code=502)
        elif resp.status_code != 200:
            raise LLMException(f"Anthropic error (HTTP {resp.status_code}): {resp.text}", status_code=resp.status_code)

        try:
            data = resp.json()
            content_blocks = data.get("content", [])
            content = "".join([b.get("text", "") for b in content_blocks if b.get("type") == "text"]).strip()
            usage = data.get("usage", {})
            in_tokens = usage.get("input_tokens", 0)
            out_tokens = usage.get("output_tokens", 0)
            total_tokens = in_tokens + out_tokens
        except Exception as e:
            raise LLMInvalidResponseError(f"Malformed response envelope from Anthropic: {e}")

        parsed = None
        if request.json_mode:
            clean = content.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean = "\n".join(lines).strip()
            try:
                parsed = json.loads(clean)
            except Exception as je:
                raise LLMInvalidResponseError(f"Failed to parse JSON content from Anthropic output: {je}")

        cost = self.calculate_cost(self.model, in_tokens, out_tokens)

        return LLMResponse(
            content=content,
            parsed_json=parsed,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost,
            latency_ms=round(latency, 2),
            model=self.model,
            provider="anthropic",
            raw_response=data
        )
