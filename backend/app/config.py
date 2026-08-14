"""
Agentic AI VAPT Framework — Application Configuration

Loads settings from environment variables / .env file.
All settings have safe defaults for local development.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = Field(default="development", description="Environment: development|production|test")
    app_name: str = Field(default="Agentic AI VAPT Framework")
    app_version: str = Field(default="1.0.0")
    secret_key: str = Field(default="dev-secret-key-change-in-production-please-32chars")
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://vapt:vapt@localhost:5432/vapt"
    )
    sqlite_url: str = Field(default="sqlite+aiosqlite:///./vapt.db")
    use_sqlite: bool = Field(default=True, description="Use SQLite for local dev")
    db_echo: bool = Field(default=False, description="Log SQL queries")
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)

    # ── Ollama / LLM ─────────────────────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2:3b")
    ollama_timeout: int = Field(default=120)
    llm_enabled: bool = Field(default=True, description="Enable LLM features; degrades gracefully if False")
    llm_judge_max_tokens: int = Field(default=1024)
    llm_report_max_tokens: int = Field(default=4096)
    llm_temperature: float = Field(default=0.1, description="Low temperature for determinism")

    # ── Assessment Limits ─────────────────────────────────────────────────────
    default_max_turns: int = Field(default=6)
    default_timeout_seconds: int = Field(default=60)
    default_max_tool_calls: int = Field(default=20)
    default_max_sessions_per_run: int = Field(default=50)
    max_payload_size_bytes: int = Field(default=65536)

    # ── Sandbox ───────────────────────────────────────────────────────────────
    sandbox_enabled: bool = Field(default=True)
    sandbox_network_disabled: bool = Field(default=True)
    sandbox_fixture_dir: str = Field(default="./sandbox/fixtures")
    sandbox_cpu_limit: float = Field(default=0.5)
    sandbox_memory_limit_mb: int = Field(default=256)
    sandbox_exec_timeout: int = Field(default=30)

    # ── Real Target Mode ──────────────────────────────────────────────────────
    real_target_mode: bool = Field(
        default=False,
        description="DANGER: Allows targeting real agents. Requires explicit authorization.",
    )

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_requests_per_minute: int = Field(default=60)
    rate_limit_runs_per_hour: int = Field(default=10)

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://localhost:80"]
    )

    # ── URLs ──────────────────────────────────────────────────────────────────
    frontend_url: str = Field(default="http://localhost:5173")

    # ── Storage ───────────────────────────────────────────────────────────────
    reports_dir: str = Field(default="./reports")
    evidence_dir: str = Field(default="./evidence")
    datasets_dir: str = Field(default="./datasets")

    # ── Observability ─────────────────────────────────────────────────────────
    otel_enabled: bool = Field(default=False)
    otel_exporter_otlp_endpoint: str = Field(default="http://localhost:4317")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Allow JSON string or list for CORS origins."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @model_validator(mode="after")
    def configure_derived_settings(self) -> "Settings":
        """Set debug mode for development environment."""
        if self.app_env == "development":
            object.__setattr__(self, "debug", True)
        return self

    @property
    def effective_database_url(self) -> str:
        """Return the database URL to use based on environment."""
        if self.use_sqlite or self.app_env == "test":
            return self.sqlite_url
        return self.database_url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def reports_path(self) -> Path:
        path = Path(self.reports_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def evidence_path(self) -> Path:
        path = Path(self.evidence_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def sandbox_fixture_path(self) -> Path:
        path = Path(self.sandbox_fixture_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings. Thread-safe singleton."""
    return Settings()


# Module-level convenience
settings = get_settings()
