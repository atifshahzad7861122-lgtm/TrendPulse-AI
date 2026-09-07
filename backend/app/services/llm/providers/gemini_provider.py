import json
import time
import re
import requests
from typing import Optional, Dict, Any

from backend.app.services.llm.provider import (
    LLMProvider, LLMRequest, LLMResponse, LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMException, LLMInvalidResponseError
)

class GeminiProvider(LLMProvider):
    """
    Google Gemini REST API adapter supporting Gemini 1.5 Flash, 1.5 Pro, and 2.0 Flash.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = "gemini-1.5-flash", base_url: Optional[str] = None):
        super().__init__(api_key=api_key, model=model or "gemini-1.5-flash", base_url=base_url or "https://generativelanguage.googleapis.com/v1beta")

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key or self.api_key.strip() in ["", "none", "null"]:
            raise LLMAuthError("Google Gemini API key is missing or not configured.")

        clean_model = self.model
        if not clean_model.startswith("models/"):
            clean_model = f"models/{clean_model}"

        # Use header authentication to avoid exposing API key in URLs or query strings
        url = f"{self.base_url.rstrip('/')}/{clean_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": request.prompt}]
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            }
        }

        if request.system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": request.system_prompt}]
            }

        if request.json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        start_time = time.perf_counter()
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=request.timeout)
        except requests.Timeout as e:
            raise LLMTimeoutError(f"Gemini request timed out after {request.timeout}s: {e}")
        except requests.RequestException as e:
            raise LLMException(f"Gemini connection error: {e}", status_code=502)

        latency = (time.perf_counter() - start_time) * 1000.0

        # Sanitize error message to never leak API key
        safe_resp_text = resp.text.replace(self.api_key, "[REDACTED_API_KEY]") if self.api_key else resp.text

        if resp.status_code in [400, 401, 403] and any(x in safe_resp_text for x in ["API_KEY_INVALID", "API key not valid", "PERMISSION_DENIED"]):
            raise LLMAuthError(f"Gemini API key rejected or invalid: {safe_resp_text}")
        elif resp.status_code == 429 or "RESOURCE_EXHAUSTED" in safe_resp_text:
            raise LLMRateLimitError(f"Gemini quota / rate limit exceeded: {safe_resp_text}")
        elif resp.status_code >= 500:
            raise LLMException(f"Gemini server error (HTTP {resp.status_code}): {safe_resp_text}", status_code=502)
        elif resp.status_code != 200:
            raise LLMException(f"Gemini error (HTTP {resp.status_code}): {safe_resp_text}", status_code=resp.status_code)

        try:
            data = resp.json()
            candidate = data["candidates"][0]["content"]["parts"][0]
            content = candidate["text"].strip()
            usage = data.get("usageMetadata", {})
            in_tokens = usage.get("promptTokenCount", max(1, len(request.prompt.split()) * 2))
            out_tokens = usage.get("candidatesTokenCount", max(1, len(content.split()) * 2))
            total_tokens = usage.get("totalTokenCount", in_tokens + out_tokens)
        except Exception as e:
            raise LLMInvalidResponseError(f"Malformed response envelope from Gemini: {e}")

        parsed = None
        if request.json_mode:
            clean = content.strip()
            if "```" in clean:
                extracted = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
                if extracted:
                    clean = extracted[0].strip()
                else:
                    lines = clean.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    clean = "\n".join(lines).strip()
            try:
                parsed = json.loads(clean)
            except Exception:
                # Fallback: extract JSON brackets
                match = re.search(r"(\{[\s\S]*\})", clean)
                if match:
                    try:
                        parsed = json.loads(match.group(1).strip())
                    except Exception as je:
                        raise LLMInvalidResponseError(f"Failed to parse JSON content from Gemini output: {je}")
                else:
                    raise LLMInvalidResponseError("Failed to parse JSON content from Gemini output.")

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
            provider="gemini",
            raw_response=data
        )
