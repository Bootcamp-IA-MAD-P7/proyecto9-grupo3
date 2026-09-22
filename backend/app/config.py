"""Load and validate the settings used to assemble the API."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MODERATION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Moderation API", min_length=1)
    docs_enabled: bool = True
    database_path: Path = Path("data/local/moderation.db")
    model_artifact_path: Path = Path("data/local/logistic_tfidf/logistic_tfidf.joblib")
    model_metadata_path: Path | None = None
    allow_simulated_fallback: bool = True
    session_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    login_max_attempts: int = Field(default=5, ge=1, le=100)
    login_window_seconds: int = Field(default=60, ge=1, le=3600)
    cors_origins: list[str] = Field(default_factory=list)
