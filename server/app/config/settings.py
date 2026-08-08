"""Server configuration via environment variables.

Production defaults (override via env vars prefixed ``KB_``):

* ``KB_EMBED_BACKEND`` — ``"openai-compat"``; talks to a local Ollama daemon
  by default. Tests override this to ``"mock-hash"`` via the global conftest
  (see ``server/tests/conftest.py``) so test runs do not hit any external
  service.
* ``KB_OPENAI_BASE_URL`` — ``"http://127.0.0.1:11434/v1"`` (Ollama).
* ``KB_OPENAI_API_KEY`` — ``"ollama"`` (Ollama accepts any non-empty value).
* ``KB_OPENAI_MODEL`` — ``"bge-m3"`` (matches the Ollama tag produced by
  ``ollama pull bge-m3``).

The Python service falls back to ``mock-hash`` if the chosen embedder cannot
initialize, with a structured ``embedder.fallback_to_mock`` log event that
names the missing dependency so a single CLI hint (``ollama serve`` /
``pip install ...``) is enough to remediate.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Override via env vars prefixed with KB_."""

    model_config = SettingsConfigDict(env_prefix="KB_", env_file=None, extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: str = Field(default="~/.kb-server")

    # Default is Ollama bge-m3 (openai-compat). Run `bash scripts/start_server_ollama.sh`
    # to spin up Ollama before launching this server.
    embed_backend: Literal["openai-compat", "bge-m3", "mock-hash"] = "openai-compat"
    embed_model: str = "bge-m3"
    embed_dim: int = 1024

    # OpenAI-compatible endpoint defaults. Override KB_OPENAI_* for non-Ollama
    # providers (vLLM, DashScope, OpenRouter, etc.).
    openai_base_url: str | None = "http://127.0.0.1:11434/v1"
    openai_api_key: str | None = "ollama"
    openai_model: str | None = "bge-m3"

    log_level: str = "INFO"
    log_json: bool = True


def get_settings() -> Settings:
    """Construct a fresh Settings on each call (cheap; pydantic-cached internally)."""
    return Settings()
