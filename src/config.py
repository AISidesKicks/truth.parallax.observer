"""Runtime settings for the app.

Everything is an environment variable with a sensible default, so the same
image runs in the container and on the host.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """The app configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- model server ----------------------------------------------------
    llm_api_base: str = "http://localhost:11433/v1"
    llm_model: str = "granite-4.0-h-tiny"
    llm_timeout: float = 300.0
    llm_max_tokens: int = 1200
    # room for the thinking tokens of a reasoning model
    llm_thinking_budget: int = 1500
    llm_temperature: float = 0.8

    # --- embedding server ------------------------------------------------
    embedding_api_base: str = "http://localhost:11433/v1"
    embedding_model: str = "embeddinggemma-2"
    embedding_dimension: int = 768

    # --- memory server ---------------------------------------------------
    openviking_url: str = "http://localhost:1933"
    openviking_user: str = "default"
    openviking_api_key: str = ""
    openviking_account: str = ""
    openviking_workspace: str = "memory/openviking"
    openviking_profile_dir: str = "memory/openviking/user"

    # --- retrieval -------------------------------------------------------
    retrieval_top_k: int = 4
    retrieval_target: str = "knowledge"
    context_max_tokens: int = 16000
    context_alert_threshold: int = 12000
    context_recent_turns: int = 5

    # --- app -------------------------------------------------------------
    app_host: str = "0.0.0.0"
    app_port: int = 8668
    log_level: str = "INFO"
    debug: bool = False
    phoenix_enabled: bool = False
    otel_endpoint: str = Field(
        default="http://localhost:4317",
        validation_alias=AliasChoices(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "OTEL_ENDPOINT",
        ),
    )

    @property
    def profile_path(self) -> Path:
        """Where the session profiles live."""
        return Path(self.openviking_profile_dir)

    @property
    def is_debug(self) -> bool:
        """Debug mode, on or off."""
        return self.debug


@lru_cache
def get_settings() -> Settings:
    """The settings, read once."""
    return Settings()
