from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field, ConfigDict

class LLMException(Exception):
    """Base exception for LLM provider errors."""
    def __init__(self, message: str, status_code: int = 500, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

class LLMAuthError(LLMException):
    """Authentication or credential failure (401/403). Permanent, should not be retried."""
    def __init__(self, message: str = "Invalid or missing LLM API credentials"):
        super().__init__(message, status_code=401, error_code="LLM_AUTH_ERROR")

class LLMRateLimitError(LLMException):
    """Rate limit or quota exceeded (429). Transient, eligible for exponential backoff."""
    def __init__(self, message: str = "LLM provider rate limit exceeded"):
        super().__init__(message, status_code=429, error_code="LLM_RATE_LIMIT")

class LLMTimeoutError(LLMException):
    """Network or execution timeout. Transient, eligible for retry."""
    def __init__(self, message: str = "LLM request timed out"):
        super().__init__(message, status_code=504, error_code="LLM_TIMEOUT")

class LLMInvalidResponseError(LLMException):
    """Output could not be parsed into expected JSON structure."""
    def __init__(self, message: str = "Invalid or unparseable JSON returned by LLM"):
        super().__init__(message, status_code=502, error_code="LLM_INVALID_RESPONSE")


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout: float = 30.0
    json_mode: bool = True
    schema_model: Optional[Type[BaseModel]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)



class LLMResponse(BaseModel):
    content: str
    parsed_json: Optional[Dict[str, Any]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0
    model: str
    provider: str
    raw_response: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract interface for pluggable LLM backends."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model or "default"
        self.base_url = base_url

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Executes a single generation call against the LLM provider."""
        ...

    def analyze(self, request: LLMRequest) -> LLMResponse:
        """Specialized analysis call enforcing structured JSON output."""
        request.json_mode = True
        return self.generate(request)

    def summarize(self, request: LLMRequest) -> LLMResponse:
        """Specialized executive summary call."""
        request.json_mode = True
        return self.generate(request)

    def classify(self, request: LLMRequest) -> LLMResponse:
        """Specialized classification call."""
        request.json_mode = True
        return self.generate(request)

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimates USD cost based on token counts for known models."""
        m = (model or "").lower()
        if "gpt-4o-mini" in m:
            # $0.15 / 1M input, $0.60 / 1M output
            return round((input_tokens * 0.00000015) + (output_tokens * 0.0000006), 6)
        elif "gpt-4o" in m:
            # $2.50 / 1M input, $10.00 / 1M output
            return round((input_tokens * 0.0000025) + (output_tokens * 0.00001), 6)
        elif "claude-3-5-sonnet" in m:
            # $3.00 / 1M input, $15.00 / 1M output
            return round((input_tokens * 0.000003) + (output_tokens * 0.000015), 6)
        elif "claude-3-5-haiku" in m:
            # $0.80 / 1M input, $4.00 / 1M output
            return round((input_tokens * 0.0000008) + (output_tokens * 0.000004), 6)
        elif "flash" in m and "gemini" in m:
            # $0.075 / 1M input, $0.30 / 1M output
            return round((input_tokens * 0.000000075) + (output_tokens * 0.0000003), 6)
        elif "gemini" in m and "pro" in m:
            # $1.25 / 1M input, $5.00 / 1M output
            return round((input_tokens * 0.00000125) + (output_tokens * 0.000005), 6)

        elif "deepseek" in m:
            # $0.14 / 1M input, $0.28 / 1M output
            return round((input_tokens * 0.00000014) + (output_tokens * 0.00000028), 6)
        else:
            # Default generic estimate: $0.50 / 1M tokens
            return round((input_tokens + output_tokens) * 0.0000005, 6)
