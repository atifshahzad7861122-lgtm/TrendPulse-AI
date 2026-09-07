"""
Groq & Grok (xAI) OpenAI-Compatible Provider Adapters for LLM Intelligence.
"""

from typing import Optional
from backend.app.core.config import settings
from backend.app.services.llm.providers.openai_provider import OpenAIProvider


class GroqLLMProvider(OpenAIProvider):
    """
    Groq High-Speed Inference API adapter using OpenAI-compatible chat completions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        key = api_key or settings.GROQ_API_KEY or settings.LLM_API_KEY
        m = model or "llama-3.3-70b-versatile"
        url = base_url or "https://api.groq.com/openai/v1"
        super().__init__(api_key=key, model=m, base_url=url)


class GrokLLMProvider(OpenAIProvider):
    """
    Grok (xAI) API adapter using OpenAI-compatible chat completions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        key = api_key or settings.XAI_API_KEY or settings.GROK_API_KEY or settings.LLM_API_KEY or settings.GROQ_API_KEY
        m = model or "grok-beta"
        url = base_url or "https://api.x.ai/v1"
        super().__init__(api_key=key, model=m, base_url=url)
