from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "TrendPulse AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "trendpulse-super-secret-development-key-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ENVIRONMENT: str = "development"  # "development", "staging", "production"
    CORS_ORIGINS: List[str] = [
        "https://trend-pulse-ai-three.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Email & Verification Configuration (Demo/Hackathon flag)
    EMAIL_VERIFICATION_ENABLED: bool = False

    # Hackathon Demo Access Configuration
    DEMO_MODE: bool = True
    DEMO_USER_ID: str = "usr_demo_101"
    DEMO_USER_EMAIL: str = "judge@trendpulse.demo"
    DEMO_WORKSPACE_ID: str = "ws_demo_101"

    # Database & Storage Backend Configuration
    DATABASE_URL: Optional[str] = None
    SUPABASE_PROJECT_ID: Optional[str] = None
    DATA_BACKEND: str = "in_memory"  # "in_memory" | "postgres"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False
    SUPABASE_INTEGRATION_TEST: bool = False

    # Data Source & Ingestion Configuration
    YOUTUBE_API_KEY: Optional[str] = None
    YOUTUBE_API_BASE_URL: str = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_DATA_SOURCE_ENABLED: bool = True
    DATA_SOURCE_TIMEOUT_SECONDS: float = 15.0
    DATA_SOURCE_MAX_RETRIES: int = 3
    DATA_SOURCE_RETRY_BACKOFF_FACTOR: float = 1.5
    YOUTUBE_MAX_RESULTS: int = 50
    YOUTUBE_REGION_CODE: str = "US"
    YOUTUBE_LANGUAGE: str = "en"

    # Daraz Pakistan / Parse Scraper API Configuration
    PARSE_API_KEY: Optional[str] = None
    PARSE_DARAZ_API_BASE_URL: str = "https://api.parse.bot/scraper/668a2f8a-7eec-4765-8e69-8089abdf24ae"
    DARAZ_CACHE_TTL_SECONDS: int = 300  # 5 minutes for price/product caching
    DARAZ_CATEGORY_CACHE_TTL_SECONDS: int = 3600  # 1 hour for categories
    DARAZ_TIMEOUT_SECONDS: float = 20.0
    DARAZ_MAX_RETRIES: int = 3
    DARAZ_RETRY_BACKOFF_FACTOR: float = 1.5

    # Daraz Official Open Platform Configuration
    DARAZ_APP_KEY: Optional[str] = None
    DARAZ_APP_SECRET: Optional[str] = None
    DARAZ_CALLBACK_URL: Optional[str] = None
    DARAZ_API_BASE_URL: str = "https://api.daraz.pk/rest"
    DARAZ_AUTH_BASE_URL: str = "https://api.daraz.pk/oauth/authorize"
    DARAZ_ACCESS_TOKEN: Optional[str] = None
    DARAZ_REFRESH_TOKEN: Optional[str] = None
    DARAZ_SELLER_ID: Optional[str] = None

    # LLM Intelligence Foundation Configuration
    LLM_PROVIDER: str = "mock"  # "mock" | "openai" | "gemini" | "anthropic" | "openrouter"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: Optional[str] = None
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.2
    LLM_TIMEOUT: float = 30.0
    LLM_ENABLED: bool = True
    LLM_CACHE_ENABLED: bool = True
    LLM_CACHE_TTL_SECONDS: int = 86400  # 24 hours

    # Groq & Grok (xAI) API Configuration
    GROQ_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None

    # ScrapeGraphAI Provider Configuration
    SCRAPEGRAPHAI_ENABLED: bool = True
    SCRAPEGRAPHAI_PROVIDER: Optional[str] = "groq"  # "groq", "openai", "gemini", "ollama", "azure"
    SCRAPEGRAPHAI_MODEL: Optional[str] = "groq/compound-mini"
    SCRAPEGRAPHAI_API_KEY: Optional[str] = None
    SCRAPEGRAPHAI_HEADLESS: bool = True
    SCRAPEGRAPHAI_TIMEOUT: float = 60.0

    model_config = SettingsConfigDict(case_sensitive=True, env_file=("backend/.env", ".env"), extra="ignore")

settings = Settings()

