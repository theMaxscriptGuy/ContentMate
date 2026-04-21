from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"
LOCAL_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "ContentMate API"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"

    postgres_dsn: str = Field(
        default="postgresql+asyncpg://contentmate:contentmate@localhost:5432/contentmate"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    youtube_api_key: str = Field(default="")
    youtube_api_base_url: AnyHttpUrl = Field(default="https://www.googleapis.com/youtube/v3")

    openai_api_key: str = Field(default="")

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
