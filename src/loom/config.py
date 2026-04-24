"""Runtime configuration for Loom MCP server.

Exposes a validated ``ConfigModel`` (Pydantic v2) plus a module-level ``CONFIG``
dict that callers read from, and helpers for loading from disk, atomic saves,
and validated in-memory updates.

Public API (stable — imported by server.py, tools/llm.py, tests):

    CONFIG                 module-level dict with current config values
    ConfigModel            Pydantic model with bounds validation
    load_config(path)      load from path or $LOOM_CONFIG_PATH; merges over defaults
    save_config(cfg, path) atomic write (uuid tmp + os.replace); validates first
    set(key, value)        validated update + persist; returns {key, old, new, persisted_at}
    research_config_get    MCP tool: return current config (or single key)
    research_config_set    MCP tool: same as set() but never raises — returns {error} on failure
    get_config()           read-only helper used by sessions.py and tools/search.py
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

logger = logging.getLogger("loom.config")

# ─── Module-level config dict ────────────────────────────────────────────────
# Callers read from this dict directly (e.g. CONFIG.get("SPIDER_CONCURRENCY", 5)).
# It starts empty; load_config() populates it on first call.
CONFIG: dict[str, Any] = {}


# ─── ConfigModel ─────────────────────────────────────────────────────────────
class ConfigModel(BaseModel):
    """Validated runtime configuration for Loom.

    All numeric fields have strict bounds. Extra fields are allowed so future
    versions can add keys without breaking older config files.
    """

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    # Scraping
    SPIDER_CONCURRENCY: int = Field(default=5, ge=1, le=20)
    EXTERNAL_TIMEOUT_SECS: int = Field(default=30, ge=5, le=120)
    MAX_CHARS_HARD_CAP: int = Field(default=200_000, ge=1_000, le=2_000_000)
    MAX_SPIDER_URLS: int = Field(default=100, ge=1, le=500)

    # Cache
    CACHE_TTL_DAYS: int = Field(default=30, ge=1, le=365)

    # Search defaults
    DEFAULT_SEARCH_PROVIDER: Literal[
        "exa",
        "tavily",
        "firecrawl",
        "brave",
        "ddgs",
        "arxiv",
        "wikipedia",
        "hackernews",
        "reddit",
    ] = "exa"
    DEFAULT_ACCEPT_LANGUAGE: str = "en-US,en;q=0.9,ar;q=0.8"

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # LLM
    LLM_DEFAULT_CHAT_MODEL: str = "meta/llama-4-maverick-17b-128e-instruct"
    LLM_DEFAULT_EMBED_MODEL: str = "nvidia/nv-embed-v2"
    LLM_DEFAULT_TRANSLATE_MODEL: str = "moonshotai/kimi-k2-instruct"
    LLM_MAX_PARALLEL: int = Field(default=12, ge=1, le=64)
    LLM_DAILY_COST_CAP_USD: float = Field(default=10.0, ge=0.0, le=1000.0)
    LLM_CASCADE_ORDER: list[str] = Field(
        default_factory=lambda: ["nvidia", "openai", "anthropic", "vllm"]
    )

    # Research pipeline
    RESEARCH_SEARCH_PROVIDERS: list[str] = Field(default_factory=lambda: ["exa", "brave"])
    RESEARCH_EXPAND_QUERIES: bool = True
    RESEARCH_EXTRACT: bool = True
    RESEARCH_SYNTHESIZE: bool = True
    RESEARCH_GITHUB_ENRICHMENT: bool = True
    RESEARCH_MAX_COST_USD: float = Field(default=0.50, ge=0.0, le=10.0)

    # Fetch
    FETCH_AUTO_ESCALATE: bool = True

    # Advanced pipeline stages (off by default — enable for thorough research)
    RESEARCH_COMMUNITY_SENTIMENT: bool = False
    RESEARCH_RED_TEAM: bool = False
    RESEARCH_MISINFO_CHECK: bool = False

    @field_validator("LLM_CASCADE_ORDER", mode="before")
    @classmethod
    def _coerce_cascade_order(cls, v: Any) -> list[str]:
        """Accept a comma-separated string or a single provider name and coerce to list.

        Empty strings and empty lists fall back to the default cascade so downstream
        code never sees an unusable `[""]` or `[]`.
        """
        default_order = ["nvidia", "openai", "anthropic", "vllm"]
        if v is None:
            return default_order
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",") if p.strip()]
            return parts or default_order
        if isinstance(v, list):
            parts = [str(p).strip() for p in v if str(p).strip()]
            return parts or default_order
        raise ValueError(f"LLM_CASCADE_ORDER must be list or string, got {type(v).__name__}")

    @field_validator("RESEARCH_SEARCH_PROVIDERS", mode="before")
    @classmethod
    def _coerce_search_providers(cls, v: Any) -> list[str]:
        """Coerce search provider list from string or list."""
        default = ["exa", "brave"]
        if v is None:
            return default
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",") if p.strip()]
            return parts or default
        if isinstance(v, list):
            parts = [str(p).strip() for p in v if str(p).strip()]
            return parts or default
        raise ValueError(
            f"RESEARCH_SEARCH_PROVIDERS must be list or string, got {type(v).__name__}"
        )


# ─── Internal helpers ────────────────────────────────────────────────────────
def _resolve_path(path: Path | str | None) -> Path:
    """Resolve the config path: explicit arg > $LOOM_CONFIG_PATH > ./config.json.

    Normalises and expands ``~``, then rejects paths containing parent-directory
    references (``..``) to prevent accidental traversal when the operator sets
    a crafted ``LOOM_CONFIG_PATH`` value.
    """
    if path is not None:
        p = Path(path)
    else:
        env_path = os.environ.get("LOOM_CONFIG_PATH")
        p = Path(env_path) if env_path else Path("config.json")

    p = p.expanduser()
    if ".." in p.parts:
        raise ValueError(f"config path must not contain '..' (got {p!s})")
    return p


def _defaults_dict() -> dict[str, Any]:
    """Return a fresh dict of code defaults from ConfigModel()."""
    return ConfigModel().model_dump()


# ─── Public API ──────────────────────────────────────────────────────────────
def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate config from a file, merging over code defaults.

    Priority (highest wins):
        1. File contents at ``path`` (or ``$LOOM_CONFIG_PATH``, or ``./config.json``)
        2. Code defaults from ``ConfigModel``

    On validation failure, logs the error and falls back to defaults.

    Returns the fully validated config dict and updates module-level ``CONFIG``.
    """
    global CONFIG

    cfg_path = _resolve_path(path)
    merged: dict[str, Any] = _defaults_dict()

    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                merged.update(raw)
            else:
                logger.warning("config_file_not_dict path=%s", cfg_path)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("config_file_load_failed path=%s error=%s", cfg_path, exc)

    try:
        validated = ConfigModel(**merged).model_dump()
    except ValidationError as exc:
        logger.error("config_validation_failed using_defaults errors=%s", exc.errors())
        validated = _defaults_dict()

    CONFIG.clear()
    CONFIG.update(validated)
    logger.info("config_loaded path=%s keys=%d", cfg_path, len(validated))
    return validated


def save_config(cfg: dict[str, Any], path: Path | str | None = None) -> Path:
    """Validate and atomically write a config dict to disk.

    Uses the standard atomic write pattern (write to uuid-suffixed temp file in
    the same directory, then ``os.replace``) so a crashed write never leaves a
    partial file.

    Raises ``ValueError`` if the config fails Pydantic validation.
    """
    try:
        validated = ConfigModel(**cfg).model_dump()
    except ValidationError as exc:
        raise ValueError(f"config validation failed: {exc.errors()}") from exc

    cfg_path = _resolve_path(path)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = cfg_path.parent / f".{cfg_path.name}.tmp-{uuid.uuid4().hex[:8]}"
    try:
        tmp_path.write_text(json.dumps(validated, indent=2, default=str), encoding="utf-8")
        os.replace(tmp_path, cfg_path)
    except Exception:
        with suppress_errors():
            if tmp_path.exists():
                tmp_path.unlink()
        raise

    logger.info("config_saved path=%s", cfg_path)
    return cfg_path


class suppress_errors:
    """Tiny contextmanager that swallows exceptions (cleanup-only)."""

    def __enter__(self) -> suppress_errors:
        return self

    def __exit__(self, *_: Any) -> bool:
        return True


def set(key: str, value: Any, path: Path | str | None = None) -> dict[str, Any]:
    """Validate and persist a single config key update.

    Returns a dict with ``key``, ``old``, ``new``, and ``persisted_at`` fields.
    Raises ``ValueError`` if the new value fails validation (the existing config
    on disk is left untouched).
    """
    if not CONFIG:
        load_config(path)

    old_value = CONFIG.get(key)
    candidate = dict(CONFIG)
    candidate[key] = value

    try:
        validated = ConfigModel(**candidate).model_dump()
    except ValidationError as exc:
        raise ValueError(f"invalid value for {key}: {exc.errors()}") from exc

    save_config(validated, path)
    CONFIG.clear()
    CONFIG.update(validated)

    return {
        "key": key,
        "old": old_value,
        "new": validated.get(key),
        "persisted_at": datetime.now(UTC).isoformat(),
    }


# ─── Read-only helper for sessions.py / tools/search.py ──────────────────────
def get_config() -> dict[str, Any]:
    """Return the current config dict (loading from disk on first call)."""
    if not CONFIG:
        load_config()
    return dict(CONFIG)


# ─── MCP tool wrappers ───────────────────────────────────────────────────────
def research_config_get(key: str | None = None) -> dict[str, Any]:
    """Return current runtime config. If ``key`` is given, return only that entry."""
    if not CONFIG:
        load_config()
    if key is None:
        return dict(CONFIG)
    if key not in CONFIG:
        return {"error": f"unknown key: {key}"}
    return {key: CONFIG[key]}


def research_config_set(key: str, value: Any) -> dict[str, Any]:
    """Validated runtime config update. Returns ``{error: ...}`` on failure."""
    try:
        return set(key, value)
    except ValueError as exc:
        logger.warning("research_config_set_failed key=%s error=%s", key, exc)
        return {"key": key, "error": str(exc)}
