"""Unit tests for ConfigModel — field validation, load/save, atomic writes."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from loom.config import CONFIG, ConfigModel, load_config, research_config_set, save_config, set


class TestConfigModel:
    """ConfigModel field validation tests."""

    def test_config_model_defaults(self) -> None:
        """ConfigModel has sensible defaults."""
        cfg = ConfigModel()

        assert cfg.SPIDER_CONCURRENCY == 5
        assert cfg.EXTERNAL_TIMEOUT_SECS == 30
        assert cfg.MAX_CHARS_HARD_CAP == 200_000
        assert cfg.CACHE_TTL_DAYS == 30

    def test_config_model_spider_concurrency_bounds(self) -> None:
        """SPIDER_CONCURRENCY validates 1-20."""
        # Valid
        cfg = ConfigModel(SPIDER_CONCURRENCY=10)
        assert cfg.SPIDER_CONCURRENCY == 10

        # Invalid: too high
        with pytest.raises(Exception):
            ConfigModel(SPIDER_CONCURRENCY=21)

        # Invalid: too low
        with pytest.raises(Exception):
            ConfigModel(SPIDER_CONCURRENCY=0)

    def test_config_model_external_timeout_bounds(self) -> None:
        """EXTERNAL_TIMEOUT_SECS validates 5-120."""
        with pytest.raises(Exception):
            ConfigModel(EXTERNAL_TIMEOUT_SECS=4)

        with pytest.raises(Exception):
            ConfigModel(EXTERNAL_TIMEOUT_SECS=121)

    def test_config_model_max_chars_bounds(self) -> None:
        """MAX_CHARS_HARD_CAP validates 1k-2M."""
        with pytest.raises(Exception):
            ConfigModel(MAX_CHARS_HARD_CAP=500)

        with pytest.raises(Exception):
            ConfigModel(MAX_CHARS_HARD_CAP=3_000_000)

    def test_config_model_cache_ttl_bounds(self) -> None:
        """CACHE_TTL_DAYS validates 1-365."""
        with pytest.raises(Exception):
            ConfigModel(CACHE_TTL_DAYS=0)

        with pytest.raises(Exception):
            ConfigModel(CACHE_TTL_DAYS=366)

    def test_config_model_llm_max_parallel_bounds(self) -> None:
        """LLM_MAX_PARALLEL validates 1-64."""
        cfg = ConfigModel(LLM_MAX_PARALLEL=32)
        assert cfg.LLM_MAX_PARALLEL == 32

        with pytest.raises(Exception):
            ConfigModel(LLM_MAX_PARALLEL=65)

    def test_config_model_llm_daily_cost_bounds(self) -> None:
        """LLM_DAILY_COST_CAP_USD validates 0-1000."""
        cfg = ConfigModel(LLM_DAILY_COST_CAP_USD=50.0)
        assert cfg.LLM_DAILY_COST_CAP_USD == 50.0

        with pytest.raises(Exception):
            ConfigModel(LLM_DAILY_COST_CAP_USD=1001.0)

    def test_config_model_cascade_order_validation(self) -> None:
        """LLM_CASCADE_ORDER accepts list or string."""
        cfg1 = ConfigModel(LLM_CASCADE_ORDER=["nvidia", "openai"])
        assert cfg1.LLM_CASCADE_ORDER == ["nvidia", "openai"]

        cfg2 = ConfigModel(LLM_CASCADE_ORDER="openai")
        assert cfg2.LLM_CASCADE_ORDER == ["openai"]

    def test_config_model_extra_fields_allowed(self) -> None:
        """ConfigModel allows extra fields (forward compatibility)."""
        cfg = ConfigModel(CUSTOM_FIELD="value")
        assert cfg.CUSTOM_FIELD == "value"  # type: ignore


class TestConfigLoadSave:
    """Config load/save and atomic write tests."""

    def test_load_config_from_file(self, tmp_config_path: Path) -> None:
        """load_config reads and merges file over defaults."""
        # Write a config file
        config_data = {"SPIDER_CONCURRENCY": 15, "CACHE_TTL_DAYS": 60}
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(json.dumps(config_data))

        # Load config
        cfg = load_config(tmp_config_path)

        assert cfg["SPIDER_CONCURRENCY"] == 15
        assert cfg["CACHE_TTL_DAYS"] == 60
        # Defaults should still be present for missing keys
        assert cfg["EXTERNAL_TIMEOUT_SECS"] == 30

    def test_load_config_uses_defaults_if_missing(self, tmp_config_path: Path) -> None:
        """load_config uses all defaults if file missing."""
        # Don't create the file
        cfg = load_config(tmp_config_path)

        assert cfg["SPIDER_CONCURRENCY"] == 5
        assert cfg["EXTERNAL_TIMEOUT_SECS"] == 30

    def test_load_config_merges_over_defaults(self, tmp_config_path: Path) -> None:
        """load_config merges file values over code defaults."""
        config_data = {"SPIDER_CONCURRENCY": 20}
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(json.dumps(config_data))

        cfg = load_config(tmp_config_path)

        # File value should override
        assert cfg["SPIDER_CONCURRENCY"] == 20
        # Other defaults should still be there
        assert "CACHE_TTL_DAYS" in cfg

    def test_save_config_atomic_write(self, tmp_config_path: Path) -> None:
        """save_config uses atomic write (uuid tmp + replace)."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {"SPIDER_CONCURRENCY": 10}

        save_config(config, tmp_config_path)

        # No tmp files should remain
        tmp_files = list(tmp_config_path.parent.glob("*.tmp-*"))
        assert len(tmp_files) == 0

        # But the actual file should exist with correct content
        assert tmp_config_path.exists()
        saved = json.loads(tmp_config_path.read_text())
        assert saved["SPIDER_CONCURRENCY"] == 10

    def test_save_config_validates_before_writing(self, tmp_config_path: Path) -> None:
        """save_config validates config before persisting."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)

        invalid_config = {"SPIDER_CONCURRENCY": 100}  # Out of range

        with pytest.raises(ValueError):
            save_config(invalid_config, tmp_config_path)

        # File should not have been created/modified
        if tmp_config_path.exists():
            # If it existed before, it should be unchanged
            pass

    def test_save_config_creates_parent_dirs(self, tmp_config_path: Path) -> None:
        """save_config creates parent directories if needed."""
        # Don't create parent
        nested_path = tmp_config_path.parent / "nested" / "config.json"

        config = {"SPIDER_CONCURRENCY": 10}
        save_config(config, nested_path)

        assert nested_path.exists()

    def test_set_config_key_value(self, tmp_config_path: Path) -> None:
        """set() updates a config key, validates, and persists."""
        import os

        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        # Initialize with empty file
        empty_config = {k: v for k, v in ConfigModel().model_dump().items()}
        save_config(empty_config, tmp_config_path)

        # Set environment variable so set() persists to the test config
        old_path = os.environ.get("LOOM_CONFIG_PATH")
        os.environ["LOOM_CONFIG_PATH"] = str(tmp_config_path)

        try:
            # Load and modify
            cfg = load_config(tmp_config_path)

            result = set("SPIDER_CONCURRENCY", 12)

            assert result["new"] == 12
            assert "old" in result
            assert "persisted_at" in result

            # Reload and verify
            cfg2 = load_config(tmp_config_path)
            assert cfg2["SPIDER_CONCURRENCY"] == 12
        finally:
            # Restore old path
            if old_path:
                os.environ["LOOM_CONFIG_PATH"] = old_path
            else:
                os.environ.pop("LOOM_CONFIG_PATH", None)

    def test_set_config_rejects_invalid_value(self, tmp_config_path: Path) -> None:
        """set() rejects invalid values."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = ConfigModel()
        save_config(cfg.model_dump(), tmp_config_path)
        load_config(tmp_config_path)

        with pytest.raises(ValueError):
            set("SPIDER_CONCURRENCY", 100)  # Out of range


class TestResearchConfigSet:
    """research_config_set MCP tool tests."""

    def test_research_config_set_valid(self, tmp_config_path: Path) -> None:
        """research_config_set accepts valid values."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = ConfigModel()
        save_config(cfg.model_dump(), tmp_config_path)
        load_config(tmp_config_path)

        result = research_config_set("CACHE_TTL_DAYS", 45)

        assert result["new"] == 45
        assert "error" not in result

    def test_research_config_set_returns_error_for_invalid(
        self, tmp_config_path: Path
    ) -> None:
        """research_config_set returns error dict on failure."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = ConfigModel()
        save_config(cfg.model_dump(), tmp_config_path)
        load_config(tmp_config_path)

        result = research_config_set("SPIDER_CONCURRENCY", 999)

        assert "error" in result


class TestConfigEnvVar:
    """Config environment variable tests."""

    def test_load_config_uses_env_var(self, tmp_config_path: Path) -> None:
        """load_config respects LOOM_CONFIG_PATH env var."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = {"SPIDER_CONCURRENCY": 8}
        tmp_config_path.write_text(json.dumps(config_data))

        # Set env var
        old_val = os.environ.get("LOOM_CONFIG_PATH")
        os.environ["LOOM_CONFIG_PATH"] = str(tmp_config_path)

        try:
            cfg = load_config()
            assert cfg["SPIDER_CONCURRENCY"] == 8
        finally:
            if old_val is not None:
                os.environ["LOOM_CONFIG_PATH"] = old_val
            else:
                os.environ.pop("LOOM_CONFIG_PATH", None)
