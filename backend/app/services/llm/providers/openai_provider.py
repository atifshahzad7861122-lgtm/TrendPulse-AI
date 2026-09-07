import json
import time
import requests
from typing import Optional, Dict, Any

from backend.app.services.llm.provider import (
    LLMProvider, LLMRequest, LLMResponse, LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMException, LLMInvalidResponseError
)

class OpenAIProvider(LLMProvider):
    """
    OpenAI API adapter supporting GPT-4o, GPT-4o-mini, and compatible base URLs (e.g. vLLM, Ollama, Azure OpenAI).
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = "gpt-4o-mini", base_url: Optional[str] = None):
        super().__init__(api_key=api_key, model=model, base_url=base_url or "https://api.openai.com/v1")

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key or self.api_key.strip() in ["", "none", "null"]:
            raise LLMAuthError("OpenAI API key is missing or not configured.")

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
            raise LLMTimeoutError(f"OpenAI request timed out after {request.timeout}s: {e}")
        except requests.RequestException as e:
            raise LLMException(f"OpenAI connection error: {e}", status_code=502)

        latency = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code in [401, 403]:
            raise LLMAuthError(f"OpenAI authentication rejected: {resp.text}")
        elif resp.status_code == 429:
            raise LLMRateLimitError(f"OpenAI rate limit / quota exceeded: {resp.text}")
        elif resp.status_code >= 500:
            raise LLMException(f"OpenAI server error (HTTP {resp.status_code}): {resp.text}", status_code=502)
        elif resp.status_code != 200:
            raise LLMException(f"OpenAI error (HTTP {resp.status_code}): {resp.text}", status_code=resp.status_code)

        try:
            data = resp.json()
            choice = data["choices"][0]["message"]
            content = choice["content"].strip()
            usage = data.get("usage", {})
            in_tokens = usage.get("prompt_tokens", 0)
            out_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", in_tokens + out_tokens)
        except Exception as e:
            raise LLMInvalidResponseError(f"Malformed response envelope from OpenAI: {e}")

        parsed = None
        if request.json_mode:
            try:
                parsed = json.loads(content)
            except Exception:
                # Strip markdown json codeblock if present
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
                    raise LLMInvalidResponseError(f"Failed to parse JSON content from OpenAI output: {je}")

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
            provider="openai",
            raw_response=data
        )
