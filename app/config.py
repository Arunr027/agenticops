
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgenticOps"
    app_env: str = "development"
    gemini_api_key: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    gemini_model: str = "gemini-3.5-flash"
    tool_timeout_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
