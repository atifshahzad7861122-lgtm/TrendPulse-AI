"""Application settings and configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_USER_AGENT, Environment
from app.core.exceptions import ConfigurationError


class Settings(BaseSettings):
    """Centralized application configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Environment Settings
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)
    LOG_LEVEL: str = Field(default="INFO")
    DATABASE_URL: str = Field(default="sqlite:///./scraper.db")
    STORAGE_TYPE: str = Field(default="memory", description="Storage provider (memory, sqlite, postgres, supabase)")

    # Timeouts (seconds)
    HTTP_TIMEOUT: float = Field(default=30.0, gt=0, description="HTTP request timeout in seconds")
    BROWSER_TIMEOUT: float = Field(default=60.0, gt=0, description="Browser action timeout in seconds")

    # Concurrency & Retry Policies
    MAX_CONCURRENCY: int = Field(default=5, ge=1, le=100, description="Maximum concurrent tasks")
    MAX_RETRIES: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")

    # Rate Limiting & Delays (seconds)
    REQUEST_DELAY_MIN: float = Field(default=1.0, ge=0.0, description="Minimum request delay")
    REQUEST_DELAY_MAX: float = Field(default=3.0, ge=0.0, description="Maximum request delay")

    # Checkpointing
    CHECKPOINT_INTERVAL: int = Field(default=50, ge=1, description="Interval for crawl checkpoints")
    CHECKPOINT_DIR: str = Field(default="./checkpoints", description="Directory for disk checkpoints")

    # Raw Data Preservation
    SAVE_RAW_HTML: bool = Field(default=True, description="Whether to persist raw HTML/JSON responses")
    RAW_DATA_DIR: str = Field(default="./data/raw", description="Directory for raw response persistence")

    # User Agent & Browser Options
    SCRAPER_USER_AGENT: str = Field(default=DEFAULT_USER_AGENT)
    BROWSER_HEADLESS: bool = Field(default=True, description="Whether to run browser in headless mode")

    # Proxy Configuration
    PROXY_ENABLED: bool = Field(default=False, description="Enable proxy routing")
    PROXY_URL: Optional[str] = Field(default=None)
    PROXY_POOL: Optional[str] = Field(default=None)

    # Daraz Marketplace
    DARAZ_BASE_URL: str = Field(default="https://www.daraz.pk")

    # Future External Integrations
    SUPABASE_URL: Optional[str] = Field(default=None)
    SUPABASE_KEY: Optional[str] = Field(default=None)

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Invalid LOG_LEVEL '{v}'. Must be one of {valid_levels}")
        return upper_v

    @model_validator(mode="after")
    def validate_delay_bounds(self) -> "Settings":
        if self.REQUEST_DELAY_MIN > self.REQUEST_DELAY_MAX:
            raise ValueError(
                f"REQUEST_DELAY_MIN ({self.REQUEST_DELAY_MIN}) cannot be greater than "
                f"REQUEST_DELAY_MAX ({self.REQUEST_DELAY_MAX})"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached accessor for application settings."""
    try:
        return Settings()
    except Exception as e:
        raise ConfigurationError(f"Failed to load application configuration: {e}") from e
