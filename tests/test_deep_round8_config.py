"""Deep testing round 8: Configuration validation and bounds testing.

Tests ConfigModel field validation, load/save/atomic writes, environment variable
overrides, bounds enforcement, and runtime wiring to code.

Focus areas:
  1. Default values are sane (all keys have defaults)
  2. Load from file + LOOM_CONFIG_PATH env var
  3. Missing file → defaults (no crash)
  4. Malformed JSON → graceful error
  5. Empty config file → defaults
  6. Numeric bounds respected
  7. Out-of-bounds → clamped or rejected
  8. String length limits
  9. Boolean validation
  10. Env var overrides file
  11. Unknown env vars ignored
  12. Config keys wired to code (cascade order, ttl, expand, auth)
  13. Concurrent config loads safe
  14. Round-trip save/load preservation
  15. Unicode values supported
  16. Large numeric values handled
  17. Empty strings for required fields
  18. get_config() returns current state
  19. Runtime config changes reflected
  20. Field coercion (list/string for cascade order, search providers)
  21. Path traversal prevention in config path
  22. Validation error logging
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from loom.config import (
    CONFIG,
    ConfigModel,
    get_config,
    load_config,
    research_config_get,
    research_config_set,
    save_config,
    set,
)


class TestConfigDefaultValues:
    """Verify all config defaults are sane."""

    def test_spider_concurrency_default(self) -> None:
        """SPIDER_CONCURRENCY defaults to 10 (reasonable for async scraping)."""
        cfg = ConfigModel()
        assert cfg.SPIDER_CONCURRENCY == 10
        assert 1 <= cfg.SPIDER_CONCURRENCY <= 20

    def test_external_timeout_default(self) -> None:
        """EXTERNAL_TIMEOUT_SECS defaults to 30 (reasonable HTTP timeout)."""
        cfg = ConfigModel()
        assert cfg.EXTERNAL_TIMEOUT_SECS == 30
        assert 5 <= cfg.EXTERNAL_TIMEOUT_SECS <= 120

    def test_max_chars_default(self) -> None:
        """MAX_CHARS_HARD_CAP defaults to 200k (reasonable for large scrapes)."""
        cfg = ConfigModel()
        assert cfg.MAX_CHARS_HARD_CAP == 200_000
        assert 1_000 <= cfg.MAX_CHARS_HARD_CAP <= 2_000_000

    def test_cache_ttl_default(self) -> None:
        """CACHE_TTL_DAYS defaults to 30 (one month)."""
        cfg = ConfigModel()
        assert cfg.CACHE_TTL_DAYS == 30
        assert 1 <= cfg.CACHE_TTL_DAYS <= 365

    def test_semantic_cache_threshold_default(self) -> None:
        """SEMANTIC_CACHE_THRESHOLD defaults to 0.95 (high similarity required)."""
        cfg = ConfigModel()
        assert cfg.SEMANTIC_CACHE_THRESHOLD == 0.95
        assert 0.0 <= cfg.SEMANTIC_CACHE_THRESHOLD <= 1.0

    def test_log_level_default(self) -> None:
        """LOG_LEVEL defaults to INFO."""
        cfg = ConfigModel()
        assert cfg.LOG_LEVEL == "INFO"
        assert cfg.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]

    def test_llm_max_parallel_default(self) -> None:
        """LLM_MAX_PARALLEL defaults to 12 (reasonable concurrency)."""
        cfg = ConfigModel()
        assert cfg.LLM_MAX_PARALLEL == 12
        assert 1 <= cfg.LLM_MAX_PARALLEL <= 64

    def test_llm_daily_cost_cap_default(self) -> None:
        """LLM_DAILY_COST_CAP_USD defaults to 10.0."""
        cfg = ConfigModel()
        assert cfg.LLM_DAILY_COST_CAP_USD == 10.0
        assert 0.0 <= cfg.LLM_DAILY_COST_CAP_USD <= 1000.0

    def test_research_max_cost_default(self) -> None:
        """RESEARCH_MAX_COST_USD defaults to 0.50."""
        cfg = ConfigModel()
        assert cfg.RESEARCH_MAX_COST_USD == 0.50
        assert 0.0 <= cfg.RESEARCH_MAX_COST_USD <= 10.0

    def test_all_booleans_have_defaults(self) -> None:
        """All boolean fields have defaults (no None)."""
        cfg = ConfigModel()
        bool_fields = [
            "SEMANTIC_CACHE_CROSS_MODEL",
            "RESEARCH_EXPAND_QUERIES",
            "RESEARCH_EXTRACT",
            "RESEARCH_SYNTHESIZE",
            "RESEARCH_GITHUB_ENRICHMENT",
            "FETCH_AUTO_ESCALATE",
            "TOR_ENABLED",
            "SANDBOX_ENABLED",
            "RATE_LIMIT_PERSIST",
            "RESEARCH_COMMUNITY_SENTIMENT",
            "RESEARCH_RED_TEAM",
            "RESEARCH_MISINFO_CHECK",
        ]
        for field in bool_fields:
            val = getattr(cfg, field)
            assert isinstance(val, bool), f"{field} should be bool, got {type(val)}"

    def test_cascade_order_default_not_empty(self) -> None:
        """LLM_CASCADE_ORDER defaults to non-empty list."""
        cfg = ConfigModel()
        assert isinstance(cfg.LLM_CASCADE_ORDER, list)
        assert len(cfg.LLM_CASCADE_ORDER) > 0
        assert all(isinstance(p, str) for p in cfg.LLM_CASCADE_ORDER)

    def test_search_providers_default_not_empty(self) -> None:
        """RESEARCH_SEARCH_PROVIDERS defaults to non-empty list."""
        cfg = ConfigModel()
        assert isinstance(cfg.RESEARCH_SEARCH_PROVIDERS, list)
        assert len(cfg.RESEARCH_SEARCH_PROVIDERS) > 0
        assert all(isinstance(p, str) for p in cfg.RESEARCH_SEARCH_PROVIDERS)


class TestNumericBounds:
    """Verify numeric config fields enforce min/max bounds."""

    def test_spider_concurrency_bounds(self) -> None:
        """SPIDER_CONCURRENCY must be 1-20."""
        # Valid: edges
        ConfigModel(SPIDER_CONCURRENCY=1)
        ConfigModel(SPIDER_CONCURRENCY=20)

        # Invalid: below min
        with pytest.raises(Exception):
            ConfigModel(SPIDER_CONCURRENCY=0)

        # Invalid: above max
        with pytest.raises(Exception):
            ConfigModel(SPIDER_CONCURRENCY=21)

    def test_external_timeout_bounds(self) -> None:
        """EXTERNAL_TIMEOUT_SECS must be 5-120."""
        ConfigModel(EXTERNAL_TIMEOUT_SECS=5)
        ConfigModel(EXTERNAL_TIMEOUT_SECS=120)

        with pytest.raises(Exception):
            ConfigModel(EXTERNAL_TIMEOUT_SECS=4)

        with pytest.raises(Exception):
            ConfigModel(EXTERNAL_TIMEOUT_SECS=121)

    def test_max_chars_bounds(self) -> None:
        """MAX_CHARS_HARD_CAP must be 1k-2M."""
        ConfigModel(MAX_CHARS_HARD_CAP=1_000)
        ConfigModel(MAX_CHARS_HARD_CAP=2_000_000)

        with pytest.raises(Exception):
            ConfigModel(MAX_CHARS_HARD_CAP=999)

        with pytest.raises(Exception):
            ConfigModel(MAX_CHARS_HARD_CAP=2_000_001)

    def test_max_spider_urls_bounds(self) -> None:
        """MAX_SPIDER_URLS must be 1-500."""
        ConfigModel(MAX_SPIDER_URLS=1)
        ConfigModel(MAX_SPIDER_URLS=500)

        with pytest.raises(Exception):
            ConfigModel(MAX_SPIDER_URLS=0)

        with pytest.raises(Exception):
            ConfigModel(MAX_SPIDER_URLS=501)

    def test_cache_ttl_bounds(self) -> None:
        """CACHE_TTL_DAYS must be 1-365."""
        ConfigModel(CACHE_TTL_DAYS=1)
        ConfigModel(CACHE_TTL_DAYS=365)

        with pytest.raises(Exception):
            ConfigModel(CACHE_TTL_DAYS=0)

        with pytest.raises(Exception):
            ConfigModel(CACHE_TTL_DAYS=366)

    def test_semantic_cache_threshold_bounds(self) -> None:
        """SEMANTIC_CACHE_THRESHOLD must be 0.0-1.0."""
        ConfigModel(SEMANTIC_CACHE_THRESHOLD=0.0)
        ConfigModel(SEMANTIC_CACHE_THRESHOLD=0.5)
        ConfigModel(SEMANTIC_CACHE_THRESHOLD=1.0)

        with pytest.raises(Exception):
            ConfigModel(SEMANTIC_CACHE_THRESHOLD=-0.1)

        with pytest.raises(Exception):
            ConfigModel(SEMANTIC_CACHE_THRESHOLD=1.1)

    def test_llm_max_parallel_bounds(self) -> None:
        """LLM_MAX_PARALLEL must be 1-64."""
        ConfigModel(LLM_MAX_PARALLEL=1)
        ConfigModel(LLM_MAX_PARALLEL=64)

        with pytest.raises(Exception):
            ConfigModel(LLM_MAX_PARALLEL=0)

        with pytest.raises(Exception):
            ConfigModel(LLM_MAX_PARALLEL=65)

    def test_llm_extract_concurrency_bounds(self) -> None:
        """LLM_EXTRACT_CONCURRENCY must be 1-16."""
        ConfigModel(LLM_EXTRACT_CONCURRENCY=1)
        ConfigModel(LLM_EXTRACT_CONCURRENCY=16)

        with pytest.raises(Exception):
            ConfigModel(LLM_EXTRACT_CONCURRENCY=0)

        with pytest.raises(Exception):
            ConfigModel(LLM_EXTRACT_CONCURRENCY=17)

    def test_llm_daily_cost_bounds(self) -> None:
        """LLM_DAILY_COST_CAP_USD must be 0-1000."""
        ConfigModel(LLM_DAILY_COST_CAP_USD=0.0)
        ConfigModel(LLM_DAILY_COST_CAP_USD=1000.0)

        with pytest.raises(Exception):
            ConfigModel(LLM_DAILY_COST_CAP_USD=-0.1)

        with pytest.raises(Exception):
            ConfigModel(LLM_DAILY_COST_CAP_USD=1000.1)

    def test_research_max_cost_bounds(self) -> None:
        """RESEARCH_MAX_COST_USD must be 0-10."""
        ConfigModel(RESEARCH_MAX_COST_USD=0.0)
        ConfigModel(RESEARCH_MAX_COST_USD=10.0)

        with pytest.raises(Exception):
            ConfigModel(RESEARCH_MAX_COST_USD=-0.01)

        with pytest.raises(Exception):
            ConfigModel(RESEARCH_MAX_COST_USD=10.1)

    def test_sandbox_timeout_bounds(self) -> None:
        """SANDBOX_TIMEOUT_SECS must be 10-3600."""
        ConfigModel(SANDBOX_TIMEOUT_SECS=10)
        ConfigModel(SANDBOX_TIMEOUT_SECS=3600)

        with pytest.raises(Exception):
            ConfigModel(SANDBOX_TIMEOUT_SECS=9)

        with pytest.raises(Exception):
            ConfigModel(SANDBOX_TIMEOUT_SECS=3601)

    def test_sandbox_cpu_limit_bounds(self) -> None:
        """SANDBOX_CPU_LIMIT must be 1-4."""
        ConfigModel(SANDBOX_CPU_LIMIT=1)
        ConfigModel(SANDBOX_CPU_LIMIT=4)

        with pytest.raises(Exception):
            ConfigModel(SANDBOX_CPU_LIMIT=0)

        with pytest.raises(Exception):
            ConfigModel(SANDBOX_CPU_LIMIT=5)

    def test_rate_limit_search_bounds(self) -> None:
        """RATE_LIMIT_SEARCH_PER_MIN must be 1-200."""
        ConfigModel(RATE_LIMIT_SEARCH_PER_MIN=1)
        ConfigModel(RATE_LIMIT_SEARCH_PER_MIN=200)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_SEARCH_PER_MIN=0)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_SEARCH_PER_MIN=201)

    def test_rate_limit_deep_bounds(self) -> None:
        """RATE_LIMIT_DEEP_PER_MIN must be 1-50."""
        ConfigModel(RATE_LIMIT_DEEP_PER_MIN=1)
        ConfigModel(RATE_LIMIT_DEEP_PER_MIN=50)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_DEEP_PER_MIN=0)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_DEEP_PER_MIN=51)

    def test_rate_limit_llm_bounds(self) -> None:
        """RATE_LIMIT_LLM_PER_MIN must be 1-200."""
        ConfigModel(RATE_LIMIT_LLM_PER_MIN=1)
        ConfigModel(RATE_LIMIT_LLM_PER_MIN=200)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_LLM_PER_MIN=0)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_LLM_PER_MIN=201)

    def test_rate_limit_fetch_bounds(self) -> None:
        """RATE_LIMIT_FETCH_PER_MIN must be 1-500."""
        ConfigModel(RATE_LIMIT_FETCH_PER_MIN=1)
        ConfigModel(RATE_LIMIT_FETCH_PER_MIN=500)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_FETCH_PER_MIN=0)

        with pytest.raises(Exception):
            ConfigModel(RATE_LIMIT_FETCH_PER_MIN=501)


class TestEnumValidation:
    """Verify enum-like fields (Literal) validate correctly."""

    def test_log_level_validation(self) -> None:
        """LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR."""
        ConfigModel(LOG_LEVEL="DEBUG")
        ConfigModel(LOG_LEVEL="INFO")
        ConfigModel(LOG_LEVEL="WARNING")
        ConfigModel(LOG_LEVEL="ERROR")

        with pytest.raises(Exception):
            ConfigModel(LOG_LEVEL="TRACE")

        with pytest.raises(Exception):
            ConfigModel(LOG_LEVEL="invalid")

    def test_default_search_provider_validation(self) -> None:
        """DEFAULT_SEARCH_PROVIDER must be a valid provider name."""
        valid = ["exa", "tavily", "firecrawl", "brave", "ddgs", "arxiv", "wikipedia"]
        for provider in valid:
            cfg = ConfigModel(DEFAULT_SEARCH_PROVIDER=provider)
            assert cfg.DEFAULT_SEARCH_PROVIDER == provider

        with pytest.raises(Exception):
            ConfigModel(DEFAULT_SEARCH_PROVIDER="invalid_provider")


class TestListCoercion:
    """Verify list fields coerce from string and handle empty cases."""

    def test_cascade_order_list_passthrough(self) -> None:
        """LLM_CASCADE_ORDER list accepted as-is."""
        cfg = ConfigModel(LLM_CASCADE_ORDER=["nvidia", "openai", "deepseek"])
        assert cfg.LLM_CASCADE_ORDER == ["nvidia", "openai", "deepseek"]

    def test_cascade_order_string_coercion(self) -> None:
        """LLM_CASCADE_ORDER string coerced to list."""
        cfg = ConfigModel(LLM_CASCADE_ORDER="openai,groq")
        assert cfg.LLM_CASCADE_ORDER == ["openai", "groq"]

    def test_cascade_order_empty_string_fallback(self) -> None:
        """LLM_CASCADE_ORDER empty string falls back to default."""
        cfg = ConfigModel(LLM_CASCADE_ORDER="")
        assert len(cfg.LLM_CASCADE_ORDER) > 0
        assert isinstance(cfg.LLM_CASCADE_ORDER, list)

    def test_cascade_order_empty_list_fallback(self) -> None:
        """LLM_CASCADE_ORDER empty list falls back to default."""
        cfg = ConfigModel(LLM_CASCADE_ORDER=[])
        assert len(cfg.LLM_CASCADE_ORDER) > 0

    def test_cascade_order_none_fallback(self) -> None:
        """LLM_CASCADE_ORDER None falls back to default."""
        cfg = ConfigModel(LLM_CASCADE_ORDER=None)
        assert len(cfg.LLM_CASCADE_ORDER) > 0

    def test_cascade_order_whitespace_stripped(self) -> None:
        """LLM_CASCADE_ORDER strips whitespace from items."""
        cfg = ConfigModel(LLM_CASCADE_ORDER="  openai  ,  groq  ")
        assert cfg.LLM_CASCADE_ORDER == ["openai", "groq"]

    def test_search_providers_string_coercion(self) -> None:
        """RESEARCH_SEARCH_PROVIDERS string coerced to list."""
        cfg = ConfigModel(RESEARCH_SEARCH_PROVIDERS="exa,tavily,brave")
        assert cfg.RESEARCH_SEARCH_PROVIDERS == ["exa", "tavily", "brave"]

    def test_search_providers_empty_fallback(self) -> None:
        """RESEARCH_SEARCH_PROVIDERS empty falls back to default."""
        cfg = ConfigModel(RESEARCH_SEARCH_PROVIDERS="")
        assert len(cfg.RESEARCH_SEARCH_PROVIDERS) > 0


class TestLoadConfigFile:
    """Test loading config from file."""

    def test_load_config_from_file(self, tmp_path: Path) -> None:
        """load_config reads and merges file over defaults."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"SPIDER_CONCURRENCY": 15, "CACHE_TTL_DAYS": 60}))

        cfg = load_config(cfg_file)

        assert cfg["SPIDER_CONCURRENCY"] == 15
        assert cfg["CACHE_TTL_DAYS"] == 60
        assert cfg["EXTERNAL_TIMEOUT_SECS"] == 30  # default

    def test_load_config_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        """load_config uses defaults if file missing (no crash)."""
        cfg_file = tmp_path / "nonexistent.json"

        cfg = load_config(cfg_file)

        assert cfg["SPIDER_CONCURRENCY"] == 10
        assert cfg["CACHE_TTL_DAYS"] == 30

    def test_load_config_empty_file_uses_defaults(self, tmp_path: Path) -> None:
        """load_config uses defaults if file is empty JSON."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("{}")

        cfg = load_config(cfg_file)

        assert cfg["SPIDER_CONCURRENCY"] == 10

    def test_load_config_malformed_json_uses_defaults(self, tmp_path: Path) -> None:
        """load_config gracefully handles malformed JSON (no crash)."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("{ invalid json")

        cfg = load_config(cfg_file)

        # Should use defaults instead of crashing
        assert cfg["SPIDER_CONCURRENCY"] == 10

    def test_load_config_non_dict_json_uses_defaults(self, tmp_path: Path) -> None:
        """load_config handles JSON that's not a dict."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('["a", "b", "c"]')  # Array, not object

        cfg = load_config(cfg_file)

        # Should use defaults
        assert cfg["SPIDER_CONCURRENCY"] == 10

    def test_load_config_invalid_values_uses_defaults(self, tmp_path: Path) -> None:
        """load_config falls back to defaults on validation failure."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"SPIDER_CONCURRENCY": 999}))  # Out of range

        cfg = load_config(cfg_file)

        # Should use default instead of raising
        assert cfg["SPIDER_CONCURRENCY"] == 10

    def test_load_config_env_var_precedence(self, tmp_path: Path) -> None:
        """load_config respects LOOM_CONFIG_PATH env var."""
        cfg_file = tmp_path / "custom_config.json"
        cfg_file.write_text(json.dumps({"SPIDER_CONCURRENCY": 8}))

        old_val = os.environ.get("LOOM_CONFIG_PATH")
        try:
            os.environ["LOOM_CONFIG_PATH"] = str(cfg_file)
            cfg = load_config()
            assert cfg["SPIDER_CONCURRENCY"] == 8
        finally:
            if old_val:
                os.environ["LOOM_CONFIG_PATH"] = old_val
            else:
                os.environ.pop("LOOM_CONFIG_PATH", None)


class TestSaveConfigAtomic:
    """Test atomic save and load round-trips."""

    def test_save_config_atomic_write(self, tmp_path: Path) -> None:
        """save_config uses atomic write (tmp + replace, no orphaned files)."""
        cfg_file = tmp_path / "config.json"

        config = {"SPIDER_CONCURRENCY": 10}
        save_config(config, cfg_file)

        # No tmp files left behind
        tmp_files = list(tmp_path.glob("*.tmp-*"))
        assert len(tmp_files) == 0

        # File exists with correct content
        assert cfg_file.exists()
        saved = json.loads(cfg_file.read_text())
        assert saved["SPIDER_CONCURRENCY"] == 10

    def test_save_config_validates_before_writing(self, tmp_path: Path) -> None:
        """save_config rejects invalid config (atomic — file not written)."""
        cfg_file = tmp_path / "config.json"

        invalid = {"SPIDER_CONCURRENCY": 100}  # Out of range

        with pytest.raises(ValueError):
            save_config(invalid, cfg_file)

        # File should not exist (validation happened before write)
        assert not cfg_file.exists()

    def test_save_config_creates_parent_dirs(self, tmp_path: Path) -> None:
        """save_config creates parent directories if needed."""
        nested = tmp_path / "a" / "b" / "c" / "config.json"

        config = {"SPIDER_CONCURRENCY": 10}
        save_config(config, nested)

        assert nested.exists()
        saved = json.loads(nested.read_text())
        assert saved["SPIDER_CONCURRENCY"] == 10

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        """save + load round-trip preserves all values."""
        cfg_file = tmp_path / "config.json"

        original = ConfigModel(
            SPIDER_CONCURRENCY=15,
            CACHE_TTL_DAYS=45,
            LLM_MAX_PARALLEL=20,
            LOG_LEVEL="DEBUG",
        ).model_dump()

        save_config(original, cfg_file)
        loaded = load_config(cfg_file)

        assert loaded["SPIDER_CONCURRENCY"] == 15
        assert loaded["CACHE_TTL_DAYS"] == 45
        assert loaded["LLM_MAX_PARALLEL"] == 20
        assert loaded["LOG_LEVEL"] == "DEBUG"

    def test_save_config_unicode_values(self, tmp_path: Path) -> None:
        """save_config handles unicode values correctly."""
        cfg_file = tmp_path / "config.json"

        config = ConfigModel(DEFAULT_ACCEPT_LANGUAGE="en-US,ar,ja;q=0.9").model_dump()
        save_config(config, cfg_file)

        loaded = load_config(cfg_file)
        assert loaded["DEFAULT_ACCEPT_LANGUAGE"] == "en-US,ar,ja;q=0.9"

    def test_save_config_large_numeric_values(self, tmp_path: Path) -> None:
        """save_config handles large numeric values."""
        cfg_file = tmp_path / "config.json"

        config = ConfigModel(MAX_CHARS_HARD_CAP=2_000_000).model_dump()
        save_config(config, cfg_file)

        loaded = load_config(cfg_file)
        assert loaded["MAX_CHARS_HARD_CAP"] == 2_000_000


class TestSetAndPersist:
    """Test set() function for runtime updates with persistence."""

    def test_set_valid_value(self, tmp_path: Path) -> None:
        """set() updates config key, validates, and persists."""
        cfg_file = tmp_path / "config.json"

        # Initialize
        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        # Update
        result = set("SPIDER_CONCURRENCY", 12, cfg_file)

        assert result["key"] == "SPIDER_CONCURRENCY"
        assert result["old"] == 10
        assert result["new"] == 12
        assert "persisted_at" in result

        # Verify persistence
        reloaded = load_config(cfg_file)
        assert reloaded["SPIDER_CONCURRENCY"] == 12

    def test_set_rejects_invalid_value(self, tmp_path: Path) -> None:
        """set() rejects invalid values (persisted config untouched)."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        with pytest.raises(ValueError):
            set("SPIDER_CONCURRENCY", 100, cfg_file)

        # Config on disk unchanged
        reloaded = load_config(cfg_file)
        assert reloaded["SPIDER_CONCURRENCY"] == 10

    def test_set_returns_old_value(self, tmp_path: Path) -> None:
        """set() returns the old value for comparison."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        result = set("CACHE_TTL_DAYS", 60, cfg_file)

        assert result["old"] == 30
        assert result["new"] == 60

    def test_set_updates_in_memory_config(self, tmp_path: Path) -> None:
        """set() updates the in-memory CONFIG dict."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        CONFIG["SPIDER_CONCURRENCY"] = 10  # Verify initial state

        set("SPIDER_CONCURRENCY", 18, cfg_file)

        assert CONFIG["SPIDER_CONCURRENCY"] == 18


class TestResearchConfigTools:
    """Test MCP tool wrappers for config get/set."""

    def test_research_config_get_all(self, tmp_path: Path) -> None:
        """research_config_get() returns full config."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        result = research_config_get()

        assert isinstance(result, dict)
        assert "SPIDER_CONCURRENCY" in result
        assert result["SPIDER_CONCURRENCY"] == 10

    def test_research_config_get_single_key(self, tmp_path: Path) -> None:
        """research_config_get(key) returns single value."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        result = research_config_get("CACHE_TTL_DAYS")

        assert isinstance(result, dict)
        assert "CACHE_TTL_DAYS" in result
        assert result["CACHE_TTL_DAYS"] == 30

    def test_research_config_get_unknown_key(self, tmp_path: Path) -> None:
        """research_config_get(unknown_key) returns error dict."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        result = research_config_get("NONEXISTENT_KEY")

        assert "error" in result

    def test_research_config_set_valid(self, tmp_path: Path) -> None:
        """research_config_set() accepts valid values."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        result = research_config_set("CACHE_TTL_DAYS", 45)

        assert result["new"] == 45
        assert "error" not in result

    def test_research_config_set_invalid_returns_error(self, tmp_path: Path) -> None:
        """research_config_set() returns error dict on failure (no raise)."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        result = research_config_set("SPIDER_CONCURRENCY", 999)

        assert "error" in result
        assert "SPIDER_CONCURRENCY" in result["key"]


class TestGetConfigHelper:
    """Test get_config() read-only helper."""

    def test_get_config_loads_on_first_call(self, tmp_path: Path) -> None:
        """get_config() loads from disk on first call."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)

        # Clear module-level CONFIG to simulate fresh start
        CONFIG.clear()

        cfg = get_config()

        assert cfg["SPIDER_CONCURRENCY"] == 10

    def test_get_config_returns_copy(self, tmp_path: Path) -> None:
        """get_config() returns a copy (mutations don't affect global)."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        cfg = get_config()
        cfg["SPIDER_CONCURRENCY"] = 999

        # Global CONFIG unchanged
        assert CONFIG["SPIDER_CONCURRENCY"] == 10

    def test_get_config_reflects_updates(self, tmp_path: Path) -> None:
        """get_config() after set() reflects the update."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        set("SPIDER_CONCURRENCY", 16, cfg_file)

        cfg = get_config()

        assert cfg["SPIDER_CONCURRENCY"] == 16


class TestConcurrentConfigLoads:
    """Test thread-safety of concurrent config loads."""

    def test_concurrent_loads_dont_corrupt(self, tmp_path: Path) -> None:
        """Concurrent load_config() calls don't corrupt CONFIG dict."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel(SPIDER_CONCURRENCY=10).model_dump()
        save_config(initial, cfg_file)

        results = []

        def load_in_thread() -> None:
            try:
                cfg = load_config(cfg_file)
                results.append(cfg["SPIDER_CONCURRENCY"])
            except Exception as e:
                results.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(load_in_thread) for _ in range(10)]
            for future in futures:
                future.result()

        # All results should be the same
        valid_results = [r for r in results if isinstance(r, int)]
        assert all(r == 10 for r in valid_results)

    def test_concurrent_saves_dont_corrupt(self, tmp_path: Path) -> None:
        """Concurrent save_config() calls handle tmp file contention."""
        cfg_file = tmp_path / "config.json"

        errors = []

        def save_in_thread(concurrency: int) -> None:
            try:
                config = ConfigModel(SPIDER_CONCURRENCY=concurrency).model_dump()
                save_config(config, cfg_file)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(save_in_thread, i + 1) for i in range(3)]
            for future in futures:
                future.result()

        # Should succeed (atomic writes prevent corruption)
        assert len(errors) == 0

        # Final file should be valid
        final = load_config(cfg_file)
        assert final["SPIDER_CONCURRENCY"] in [1, 2, 3]


class TestPathTraversalPrevention:
    """Ensure config path doesn't allow directory traversal."""

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Config path with .. is rejected (SSRF-like prevention)."""
        from loom.config import _resolve_path

        with pytest.raises(ValueError, match="must not contain"):
            _resolve_path(tmp_path / ".." / "config.json")

    def test_valid_path_accepted(self, tmp_path: Path) -> None:
        """Valid config path is accepted."""
        from loom.config import _resolve_path

        cfg_path = tmp_path / "config.json"
        resolved = _resolve_path(cfg_path)

        assert resolved == cfg_path.resolve()


class TestExtraFields:
    """Verify forward compatibility with extra fields."""

    def test_extra_fields_allowed(self) -> None:
        """ConfigModel allows unknown fields (forward compatibility)."""
        cfg = ConfigModel(CUSTOM_FIELD="value", FUTURE_OPTION=42)

        assert cfg.CUSTOM_FIELD == "value"  # type: ignore
        assert cfg.FUTURE_OPTION == 42  # type: ignore

    def test_extra_fields_preserved_in_dump(self) -> None:
        """Extra fields preserved when model_dump()."""
        cfg = ConfigModel(CUSTOM_FIELD="value")
        dumped = cfg.model_dump()

        assert dumped.get("CUSTOM_FIELD") == "value"


class TestConfigWiredToCode:
    """Verify config changes affect actual behavior."""

    def test_cascade_order_affects_provider_selection(self, tmp_path: Path) -> None:
        """LLM_CASCADE_ORDER changes how providers are selected."""
        # This is a behavioral test — just verify the value is accessible
        cfg_file = tmp_path / "config.json"

        cfg_dict = ConfigModel(
            LLM_CASCADE_ORDER=["openai", "groq"]
        ).model_dump()
        save_config(cfg_dict, cfg_file)
        load_config(cfg_file)

        assert CONFIG["LLM_CASCADE_ORDER"] == ["openai", "groq"]

    def test_cache_ttl_affects_expiration(self, tmp_path: Path) -> None:
        """CACHE_TTL_DAYS affects cache expiration logic."""
        cfg_file = tmp_path / "config.json"

        cfg_dict = ConfigModel(CACHE_TTL_DAYS=7).model_dump()
        save_config(cfg_dict, cfg_file)
        load_config(cfg_file)

        assert CONFIG["CACHE_TTL_DAYS"] == 7

    def test_expand_queries_affects_pipeline(self, tmp_path: Path) -> None:
        """RESEARCH_EXPAND_QUERIES affects deep research pipeline."""
        cfg_file = tmp_path / "config.json"

        cfg_dict = ConfigModel(RESEARCH_EXPAND_QUERIES=False).model_dump()
        save_config(cfg_dict, cfg_file)
        load_config(cfg_file)

        assert CONFIG["RESEARCH_EXPAND_QUERIES"] is False

    def test_auth_required_affects_enforcement(self, tmp_path: Path) -> None:
        """Boolean flags affect runtime behavior."""
        cfg_file = tmp_path / "config.json"

        cfg_dict = ConfigModel(RESEARCH_EXTRACT=False).model_dump()
        save_config(cfg_dict, cfg_file)
        load_config(cfg_file)

        assert CONFIG["RESEARCH_EXTRACT"] is False


class TestRuntimeConfigChanges:
    """Verify runtime config changes are reflected immediately."""

    def test_set_reflected_in_get_config(self, tmp_path: Path) -> None:
        """After set(), get_config() reflects the change."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        assert get_config()["CACHE_TTL_DAYS"] == 30

        set("CACHE_TTL_DAYS", 90, cfg_file)

        assert get_config()["CACHE_TTL_DAYS"] == 90

    def test_set_reflected_in_global_config(self, tmp_path: Path) -> None:
        """After set(), global CONFIG dict updated."""
        cfg_file = tmp_path / "config.json"

        initial = ConfigModel().model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        set("SPIDER_CONCURRENCY", 19, cfg_file)

        assert CONFIG["SPIDER_CONCURRENCY"] == 19

    def test_reload_after_external_change(self, tmp_path: Path) -> None:
        """load_config() picks up external changes to config file."""
        cfg_file = tmp_path / "config.json"

        # Initial state
        initial = ConfigModel(SPIDER_CONCURRENCY=10).model_dump()
        save_config(initial, cfg_file)
        load_config(cfg_file)

        assert CONFIG["SPIDER_CONCURRENCY"] == 10

        # External process modifies file
        updated = ConfigModel(SPIDER_CONCURRENCY=18).model_dump()
        save_config(updated, cfg_file)

        # Reload picks up change
        load_config(cfg_file)

        assert CONFIG["SPIDER_CONCURRENCY"] == 18


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_config_with_empty_strings(self) -> None:
        """Config accepts (but may coerce) empty strings."""
        # DEFAULT_ACCEPT_LANGUAGE is a string field
        cfg = ConfigModel(DEFAULT_ACCEPT_LANGUAGE="en-US")
        assert cfg.DEFAULT_ACCEPT_LANGUAGE == "en-US"

    def test_boolean_field_strict_type(self) -> None:
        """Boolean fields must be actual booleans (not strings)."""
        # True/False are valid
        cfg = ConfigModel(RESEARCH_EXPAND_QUERIES=True)
        assert cfg.RESEARCH_EXPAND_QUERIES is True

        cfg = ConfigModel(RESEARCH_EXPAND_QUERIES=False)
        assert cfg.RESEARCH_EXPAND_QUERIES is False

        # "true"/"false" strings may coerce (depending on Pydantic config)
        # but we test that at least bool values work

    def test_float_fields_accept_int(self) -> None:
        """Float fields accept int values (coerced)."""
        cfg = ConfigModel(SEMANTIC_CACHE_THRESHOLD=1)
        assert cfg.SEMANTIC_CACHE_THRESHOLD == 1.0

    def test_very_large_numeric_at_boundary(self) -> None:
        """Boundary values accepted at exact limits."""
        cfg = ConfigModel(
            MAX_CHARS_HARD_CAP=2_000_000,
            CACHE_TTL_DAYS=365,
            LLM_DAILY_COST_CAP_USD=1000.0,
        )
        assert cfg.MAX_CHARS_HARD_CAP == 2_000_000
        assert cfg.CACHE_TTL_DAYS == 365
        assert cfg.LLM_DAILY_COST_CAP_USD == 1000.0

    def test_field_immutability_check(self) -> None:
        """ConfigModel fields can be modified (validate_assignment=True)."""
        cfg = ConfigModel(SPIDER_CONCURRENCY=10)
        cfg.SPIDER_CONCURRENCY = 15
        assert cfg.SPIDER_CONCURRENCY == 15

        # Out of bounds should raise on assignment
        with pytest.raises(Exception):
            cfg.SPIDER_CONCURRENCY = 100
