from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"
LOCAL_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "ContentMate API"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    )

    postgres_dsn: str = Field(
        default="postgresql+asyncpg://contentmate:contentmate@localhost:5432/contentmate"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    youtube_min_duration_seconds: int = 301
    youtube_scan_limit: int = 0
    youtube_candidate_pool_size: int = 30
    transcript_use_ytdlp_fallback: bool = True

    auth_token_secret: str = Field(default="change-me-in-production")
    auth_token_ttl_seconds: int = 604800
    google_client_id: str = Field(default="")

    openai_api_key: str = Field(default="")
    openai_analysis_model: str = "gpt-4.1-mini"
    openai_analysis_max_transcript_chars: int = 60000

    request_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_file=(str(LOCAL_ENV_FILE), str(ROOT_ENV_FILE)),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
