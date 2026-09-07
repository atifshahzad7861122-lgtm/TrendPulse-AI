import json
import time
import requests
from typing import Optional, Dict, Any

from backend.app.services.llm.provider import (
    LLMProvider, LLMRequest, LLMResponse, LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMException, LLMInvalidResponseError
)

class OpenRouterProvider(LLMProvider):
    """
    OpenRouter API adapter providing multi-model unified routing across OpenAI, Anthropic, Meta, DeepSeek, and Mistral.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = "deepseek/deepseek-chat", base_url: Optional[str] = None):
        super().__init__(api_key=api_key, model=model, base_url=base_url or "https://openrouter.ai/api/v1")

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key or self.api_key.strip() in ["", "none", "null"]:
            raise LLMAuthError("OpenRouter API key is missing or not configured.")

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://trendpulse.ai",
            "X-Title": "TrendPulse AI",
            "Content-Type": "application/json"
        }

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=request.timeout)
        except requests.Timeout as e:
            raise LLMTimeoutError(f"OpenRouter request timed out after {request.timeout}s: {e}")
        except requests.RequestException as e:
            raise LLMException(f"OpenRouter connection error: {e}", status_code=502)

        latency = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code in [401, 403]:
            raise LLMAuthError(f"OpenRouter authentication rejected: {resp.text}")
        elif resp.status_code == 429:
            raise LLMRateLimitError(f"OpenRouter rate limit / credits exhausted: {resp.text}")
        elif resp.status_code >= 500:
            raise LLMException(f"OpenRouter server error (HTTP {resp.status_code}): {resp.text}", status_code=502)
        elif resp.status_code != 200:
            raise LLMException(f"OpenRouter error (HTTP {resp.status_code}): {resp.text}", status_code=resp.status_code)

        try:
            data = resp.json()
            choice = data["choices"][0]["message"]
            content = choice["content"].strip()
            usage = data.get("usage", {})
            in_tokens = usage.get("prompt_tokens", len(request.prompt.split()) * 2)
            out_tokens = usage.get("completion_tokens", len(content.split()) * 2)
            total_tokens = usage.get("total_tokens", in_tokens + out_tokens)
        except Exception as e:
            raise LLMInvalidResponseError(f"Malformed response envelope from OpenRouter: {e}")

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
                raise LLMInvalidResponseError(f"Failed to parse JSON content from OpenRouter output: {je}")

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
            provider="openrouter",
            raw_response=data
        )
