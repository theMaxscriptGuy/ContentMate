from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_FILE = Path(__file__).resolve()
DEFAULT_POSTGRES_DSN = "postgresql+asyncpg://contentmate:contentmate@localhost:5432/contentmate"


def _find_env_files() -> tuple[str, ...]:
    env_files = []
    for parent in CONFIG_FILE.parents:
        candidate = parent / ".env"
        if candidate.exists():
            env_files.append(str(candidate))
    return tuple(env_files)


class Settings(BaseSettings):
    app_name: str = "ContentMate API"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_to_file: bool = True
    log_file_path: str = "logs/contentmate-api.log"
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    )

    postgres_dsn: str = Field(default=DEFAULT_POSTGRES_DSN)
    database_url: str = Field(default="")
    redis_url: str = Field(default="redis://localhost:6379/0")

    youtube_min_duration_seconds: int = 301
    youtube_scan_limit: int = 0
    youtube_candidate_pool_size: int = 10
    transcript_use_ytdlp_fallback: bool = True
    trend_context_enabled: bool = True
    trend_default_geo: str = "US"
    trend_max_items: int = 10

    auth_token_secret: str = Field(default="change-me-in-production")
    auth_token_ttl_seconds: int = 604800
    google_client_id: str = Field(default="")
    daily_analysis_limit: int = 2
    rate_limit_global_requests_per_minute: int = 100
    rate_limit_auth_requests_per_minute: int = 10
    rate_limit_pipeline_requests_per_hour: int = 3
    max_request_body_bytes: int = 1_048_576

    openai_api_key: str = Field(default="")
    openai_analysis_model: str = "gpt-4.1-mini"
    openai_analysis_max_transcript_chars: int = 60000

    request_timeout_seconds: float = 20.0
    trend_request_timeout_seconds: float = 8.0

    model_config = SettingsConfigDict(
        env_file=_find_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def normalize_database_urls(self) -> "Settings":
        if self.postgres_dsn == DEFAULT_POSTGRES_DSN and self.database_url:
            self.postgres_dsn = self.database_url
        self.postgres_dsn = _as_async_postgres_dsn(self.postgres_dsn)
        return self


def _as_async_postgres_dsn(dsn: str) -> str:
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return dsn


def as_sync_postgres_dsn(dsn: str) -> str:
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
