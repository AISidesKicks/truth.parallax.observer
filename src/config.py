"""Runtime settings for the app.

Everything is an environment variable with a sensible default, so the same
image runs in the container and on the host.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# the project root, so the paths work from any folder
ROOT = Path(__file__).resolve().parent.parent

# the catalogue of the models the router serves
MODEL_CATALOGUE = ROOT / "config" / "models.toml"


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


@dataclass(frozen=True)
class ModelEntry:
    """One model in the catalogue."""

    id: str
    role: str = "chat"
    display: str = ""
    size: str = ""
    repo: str = ""
    quant: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        """The entry as the interface sees it."""
        return {
            "id": self.id,
            "role": self.role,
            "display": self.display or self.id,
            "size": self.size,
            "repo": self.repo,
            "quant": self.quant,
            "note": self.note,
        }


def read_catalogue(path: Path | None = None) -> dict:
    """The catalogue file, as a dictionary."""
    catalogue = path or MODEL_CATALOGUE
    if not catalogue.exists():
        return {}

    try:
        with catalogue.open("rb") as handle:
            return tomllib.load(handle)
    except Exception:
        return {}


def model_catalogue(path: Path | None = None) -> list[ModelEntry]:
    """Every model the router serves.

    The catalogue is a TOML file with one section per model. The name of the
    section is the model id the API routes on.
    """
    entries: list[ModelEntry] = []

    for name, entry in read_catalogue(path).items():
        if not isinstance(entry, dict):
            continue
        entries.append(
            ModelEntry(
                id=name,
                role=str(entry.get("role", "chat")),
                display=str(entry.get("display", name)),
                size=str(entry.get("size", "")),
                repo=str(entry.get("repo", "")),
                quant=str(entry.get("quant", "")),
                note=str(entry.get("note", "")),
            )
        )

    return entries


def chat_models(path: Path | None = None) -> list[ModelEntry]:
    """The models the visitor can pick."""
    return [entry for entry in model_catalogue(path) if entry.role != "embedding"]


def default_model(path: Path | None = None) -> str:
    """The model the app uses when the visitor does not pick one."""
    chosen = read_catalogue(path).get("default")
    if isinstance(chosen, str) and chosen:
        return chosen
    return get_settings().llm_model
