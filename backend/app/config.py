"""Application configuration loaded from environment variables."""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (parent of app/)
BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent
# Repository root (parent of backend/)
PROJECT_ROOT: Path = BACKEND_ROOT.parent


def _resolve_path(raw: Path, base: Path) -> Path:
    if raw.is_absolute():
        return raw.resolve()
    return (base / raw).resolve()


class Settings(BaseSettings):
    """Runtime settings with paths anchored to the backend and project roots."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "ShopSphere AI Returns Agent"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./shopsphere.db"
    chroma_path: str = "./chroma_data"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    llm_provider: str = "groq"
    llm_model: str = ""
    llm_api_key: str = ""

    groq_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GROQ_API_KEY", "LLM_API_KEY"),
    )
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        validation_alias=AliasChoices("GROQ_BASE_URL", "LLM_BASE_URL"),
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias=AliasChoices("GROQ_MODEL", "LLM_MODEL"),
    )
    groq_max_rpm: int = Field(default=30, validation_alias=AliasChoices("GROQ_MAX_RPM"))
    groq_api_keys: str = Field(
        default="",
        validation_alias=AliasChoices("GROQ_API_KEYS"),
        description="Additional Groq API keys (comma, semicolon, or newline separated).",
    )

    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        validation_alias=AliasChoices("GEMINI_MODEL"),
    )
    gemini_max_rpm: int = Field(default=14, validation_alias=AliasChoices("GEMINI_MAX_RPM"))

    llm_context_input_tokens: int = Field(
        default=28_000,
        validation_alias=AliasChoices("LLM_CONTEXT_INPUT_TOKENS"),
        description="Max input context size per provider call (approximate tokens).",
    )
    llm_context_output_reserve: int = Field(
        default=4_096,
        validation_alias=AliasChoices("LLM_CONTEXT_OUTPUT_RESERVE"),
        description="Tokens reserved for model output inside llm_context_input_tokens.",
    )
    llm_history_max_tokens: int = Field(
        default=3_500,
        validation_alias=AliasChoices("LLM_HISTORY_MAX_TOKENS"),
        description="Soft cap for prior chat turns injected into the agent (see agents/history.py).",
    )
    llm_tool_message_max_tokens: int = Field(
        default=700,
        validation_alias=AliasChoices("LLM_TOOL_MESSAGE_MAX_TOKENS"),
        description="Per tool-result message cap when trimming agent message history for the LLM.",
    )

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    jwt_secret_key: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    actions_disabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("ACTIONS_DISABLED"),
        description="When true, block submit/execute of consequential agent actions (read-only mode).",
    )
    action_approval_expire_hours: int = Field(
        default=72,
        validation_alias=AliasChoices("ACTION_APPROVAL_EXPIRE_HOURS"),
        description="Hours until a pending action approval expires.",
    )
    monitoring_auto_run: bool = Field(
        default=False,
        validation_alias=AliasChoices("MONITORING_AUTO_RUN"),
    )
    monitoring_interval_minutes: int = Field(
        default=30,
        validation_alias=AliasChoices("MONITORING_INTERVAL_MINUTES"),
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlite_database_path(self) -> Path | None:
        """Filesystem path for file-backed SQLite URLs, or None for non-file schemes."""
        url = self.database_url
        if url.startswith("sqlite:///"):
            relative = url.removeprefix("sqlite:///")
            if relative == ":memory:":
                return None
            return _resolve_path(Path(relative), BACKEND_ROOT)
        if url.startswith("sqlite:////"):
            # Absolute path on Unix-style URLs (sqlite:////absolute/path)
            return Path("/" + url.removeprefix("sqlite:////")).resolve()
        return None

    @property
    def chroma_directory(self) -> Path:
        return _resolve_path(Path(self.chroma_path), PROJECT_ROOT)

    @property
    def groq_api_keys_list(self) -> list[str]:
        """Distinct Groq keys: GROQ_API_KEY first, then entries in GROQ_API_KEYS."""
        seen: set[str] = set()
        ordered: list[str] = []

        def add(raw: str) -> None:
            key = raw.strip()
            if key and key not in seen:
                seen.add(key)
                ordered.append(key)

        add(self.groq_api_key)
        if self.groq_api_keys.strip():
            for token in re.split(r"[,;\n]+", self.groq_api_keys):
                add(token)
        return ordered

    @property
    def groq_effective_max_rpm(self) -> int:
        """Client-side RPM budget across all configured Groq keys."""
        n = len(self.groq_api_keys_list)
        if n == 0:
            return 0
        return self.groq_max_rpm * n

    @property
    def llm_configured(self) -> bool:
        groq_ok = bool(self.groq_api_keys_list and self.groq_model.strip())
        gemini_ok = bool(self.gemini_api_key.strip())
        return groq_ok or gemini_ok

    def ensure_runtime_directories(self) -> None:
        """Create directories required for SQLite and Chroma when using default layout."""
        db_path = self.sqlite_database_path
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
