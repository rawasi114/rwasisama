"""Application configuration loaded from environment."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_secret_key: str = "change_me"
    app_port: int = 8000
    app_log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://rawasi:rawasi_dev_pwd@localhost:5432/rawasi_pricing"

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"
    claude_max_tokens: int = 8192
    claude_timeout_seconds: int = 120
    claude_max_retries: int = 3

    embedding_dimension: int = 1536
    normalization_keyword_threshold: float = 0.90
    normalization_semantic_threshold: float = 0.85
    normalization_claude_threshold: float = 0.75

    reference_min_observations: int = 3
    reference_lookback_months: int = 18

    win_probability_iterations: int = 10_000

    alerts_to: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def alert_emails(self) -> list[str]:
        return [e.strip() for e in self.alerts_to.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
