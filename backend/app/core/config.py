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
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

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

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()
