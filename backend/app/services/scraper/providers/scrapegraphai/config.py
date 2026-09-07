"""
ScrapeGraphAI Provider Configuration Adapter.

Resolves LLM and browser configurations for ScrapeGraphAI graphs,
reusing TrendPulse AI's existing settings and environment variables.
Guarantees API keys and secrets are NEVER logged or exposed.
"""

import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings

logger = logging.getLogger("trendpulse.scraper.scrapegraphai.config")

# Architectural Rule: Gemini is paused specifically for the ScrapeGraphAI marketplace scraping path.
# Groq is the active provider. Gemini support remains intact across the project for other AI agents.
GEMINI_PAUSED_FOR_SCRAPEGRAPHAI: bool = True


class ScrapeGraphAIConfig(BaseModel):
    enabled: bool = True
    provider: str = "groq"  # groq, openai, ollama, azure, mock (gemini paused for marketplace scraping)
    model: str = "groq/compound-mini"
    api_key: Optional[str] = None
    headless: bool = True
    timeout: float = 60.0
    verbose: bool = False
    rate_limit_per_minute: int = 30
    # Groq TPM rate-limiting and bounded concurrency settings
    max_concurrent_llm_requests: int = 1
    min_delay_between_requests: float = 2.5
    max_retries_on_429: int = 3
    retry_backoff_base: float = 2.0
    browser_waf_wait_timeout: float = 15.0

    @classmethod
    def load_from_settings(cls) -> "ScrapeGraphAIConfig":
        """
        Loads configuration from TrendPulse settings with intelligent fallbacks
        to the project's LLM Foundation settings.
        Enforces that Gemini is paused for marketplace scraping and Groq is active.
        """
        enabled = getattr(settings, "SCRAPEGRAPHAI_ENABLED", True)
        sg_provider = getattr(settings, "SCRAPEGRAPHAI_PROVIDER", None)
        sg_model = getattr(settings, "SCRAPEGRAPHAI_MODEL", None)
        sg_api_key = getattr(settings, "SCRAPEGRAPHAI_API_KEY", None)
        groq_api_key = getattr(settings, "GROQ_API_KEY", None)
        sg_headless = getattr(settings, "SCRAPEGRAPHAI_HEADLESS", True)
        sg_timeout = getattr(settings, "SCRAPEGRAPHAI_TIMEOUT", 60.0)

        # Check Groq key in settings or env
        env_groq_key = os.environ.get("GROQ_API_KEY")
        effective_groq_key = groq_api_key or env_groq_key

        # Check if provider requested is Gemini or Google
        requested_provider = (sg_provider or "").lower().strip()
        general_provider = (getattr(settings, "LLM_PROVIDER", "") or "").lower().strip()

        if requested_provider in ("gemini", "google", "google_genai") or (
            not requested_provider and general_provider in ("gemini", "google", "google_genai")
        ):
            logger.warning(
                "Gemini is paused for ScrapeGraphAI marketplace scraping path. "
                "Activating Groq as the active LLM provider."
            )
            llm_provider = "groq"
            llm_model = sg_model if (sg_model and "gemini" not in sg_model.lower()) else "groq/compound-mini"
            llm_api_key = sg_api_key or effective_groq_key
        elif effective_groq_key and (not requested_provider or requested_provider == "groq"):
            llm_provider = "groq"
            llm_model = sg_model or "groq/compound-mini"
            llm_api_key = sg_api_key or effective_groq_key
        else:
            llm_provider = requested_provider or "groq" if effective_groq_key else (general_provider or "openai")
            llm_model = sg_model or (
                "groq/compound-mini" if llm_provider == "groq" else (getattr(settings, "LLM_MODEL", "gpt-4o-mini"))
            )
            llm_api_key = sg_api_key or (
                effective_groq_key if llm_provider == "groq" else getattr(settings, "LLM_API_KEY", None)
            )

        # Environment variable overrides
        env_key = (
            os.environ.get("SCRAPEGRAPHAI_API_KEY")
            or (os.environ.get("GROQ_API_KEY") if llm_provider == "groq" else None)
            or os.environ.get("OPENAI_API_KEY")
        )
        if not llm_api_key and env_key:
            llm_api_key = env_key

        return cls(
            enabled=enabled,
            provider=llm_provider,
            model=llm_model,
            api_key=llm_api_key,
            headless=sg_headless,
            timeout=sg_timeout,
            verbose=False
        )

    def get_model_identifier(self) -> str:
        """
        Returns the formatted model identifier expected by ScrapeGraphAI.
        e.g. 'openai/gpt-4o-mini', 'google_genai/gemini-1.5-flash', 'ollama/llama3.2'
        """
        p = self.provider.lower()
        m = self.model

        # Already has provider prefix
        if "/" in m:
            return m

        if p in ("openai", "openrouter"):
            return f"openai/{m}"
        elif p in ("gemini", "google"):
            return f"google_genai/{m}"
        elif p == "groq":
            return f"groq/{m}"
        elif p == "ollama":
            return f"ollama/{m}"
        elif p == "azure":
            return f"azure_openai/{m}"
        return f"{p}/{m}"

    def to_graph_config(self) -> Dict[str, Any]:
        """
        Produces the dictionary format required by SmartScraperGraph and SearchGraph.
        """
        model_id = self.get_model_identifier()
        llm_cfg: Dict[str, Any] = {
            "model": model_id,
            "temperature": 0.0,
            "model_tokens": 8192,
        }
        if self.api_key:
            llm_cfg["api_key"] = self.api_key

        # When provider is groq, attach ChatGroq model_instance to support all Groq models seamlessly
        if self.provider.lower() == "groq":
            try:
                from langchain_groq import ChatGroq
                llm_cfg["model_instance"] = ChatGroq(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=0.0
                )
            except Exception as e:
                logger.warning(
                    f"Failed to instantiate ChatGroq model_instance: {e}. Falling back to standard config."
                )

        return {
            "llm": llm_cfg,
            "verbose": self.verbose,
            "headless": self.headless,
        }

    def get_sanitized_summary(self) -> Dict[str, Any]:
        """Returns non-sensitive metadata for telemetry and diagnostics."""
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "has_api_key": bool(self.api_key),
            "headless": self.headless,
            "timeout": self.timeout,
            "gemini_paused_for_marketplace": GEMINI_PAUSED_FOR_SCRAPEGRAPHAI,
            "max_concurrent_llm_requests": self.max_concurrent_llm_requests,
            "min_delay_between_requests": self.min_delay_between_requests,
        }
