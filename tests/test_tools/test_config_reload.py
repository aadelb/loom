"""Tests for config hot-reload tools.

Tests three tools:
- research_config_watch: Start watching config.json
- research_config_check: Check for changes and reload
- research_config_diff: Show what changed
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from loom.tools import config_reload


@pytest.fixture
def temp_config_file() -> Path:
    """Create a temporary config file with test data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        initial_config = {
            "SPIDER_CONCURRENCY": 10,
            "EXTERNAL_TIMEOUT_SECS": 30,
            "MAX_CHARS_HARD_CAP": 200000,
            "LOG_LEVEL": "INFO",
        }
        json.dump(initial_config, f)
        config_path = Path(f.name)

    yield config_path

    # Cleanup
    if config_path.exists():
        config_path.unlink()


@pytest.fixture(autouse=True)
def reset_watch_state():
    """Reset watch state before each test."""
    config_reload._watch_state.clear()
    config_reload._watch_state.update({
        "watching": False,
        "config_path": None,
        "last_mtime": None,
        "last_config": None,
    })
    yield
    # Reset after test
    config_reload._watch_state.clear()
    config_reload._watch_state.update({
        "watching": False,
        "config_path": None,
        "last_mtime": None,
        "last_config": None,
    })


class TestConfigWatch:
    """Tests for research_config_watch()."""

    def test_watch_starts_successfully(self, temp_config_file: Path) -> None:
        """Watch should start and return current mtime."""
        result = config_reload.research_config_watch(str(temp_config_file))

        assert result["watching"] is True
        assert result["config_path"] == str(temp_config_file)
        assert result["last_modified"] is not None
        assert isinstance(result["last_modified"], float)

    def test_watch_nonexistent_file(self) -> None:
        """Watch should fail gracefully for nonexistent file."""
        result = config_reload.research_config_watch("/nonexistent/path/config.json")

        assert result["watching"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_watch_stores_initial_mtime(self, temp_config_file: Path) -> None:
        """Watch should store initial mtime in module state."""
        config_reload.research_config_watch(str(temp_config_file))

        assert config_reload._watch_state["watching"] is True
        assert config_reload._watch_state["config_path"] == str(temp_config_file)
        assert config_reload._watch_state["last_mtime"] is not None

    def test_watch_stores_snapshot(self, temp_config_file: Path, monkeypatch) -> None:
        """Watch should store snapshot of current config."""
        # Mock get_config to return test data
        test_config = {
            "SPIDER_CONCURRENCY": 10,
            "LOG_LEVEL": "INFO",
        }
        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: test_config
        )

        config_reload.research_config_watch(str(temp_config_file))

        assert config_reload._watch_state["last_config"] == test_config


class TestConfigCheck:
    """Tests for research_config_check()."""

    def test_check_no_change(self, temp_config_file: Path, monkeypatch) -> None:
        """Check should detect no changes if mtime hasn't changed."""
        test_config = {"SPIDER_CONCURRENCY": 10}
        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: test_config
        )

        # Start watch
        config_reload.research_config_watch(str(temp_config_file))

        # Check immediately (no time for file to change)
        result = config_reload.research_config_check(str(temp_config_file))

        assert result["changed"] is False
        assert result["reloaded"] is False
        assert result["current_settings"] == test_config

    def test_check_reloads_on_change(self, temp_config_file: Path, monkeypatch) -> None:
        """Check should reload config when file mtime changes."""
        old_config = {"SPIDER_CONCURRENCY": 10, "LOG_LEVEL": "INFO"}
        new_config = {"SPIDER_CONCURRENCY": 15, "LOG_LEVEL": "DEBUG"}

        # Start with old config
        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: old_config
        )
        config_reload.research_config_watch(str(temp_config_file))

        # Simulate file modification by updating mtime
        time.sleep(0.01)  # Ensure mtime advances
        temp_config_file.touch()

        # Mock load_config to return new config
        monkeypatch.setattr(
            "loom.tools.config_reload.load_config",
            lambda path: new_config
        )
        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: new_config
        )

        result = config_reload.research_config_check(str(temp_config_file))

        assert result["changed"] is True
        assert result["reloaded"] is True
        assert result["current_settings"] == new_config

    def test_check_without_watch(self, temp_config_file: Path, monkeypatch) -> None:
        """Check should work even if watch wasn't called first."""
        test_config = {"SPIDER_CONCURRENCY": 10}
        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: test_config
        )

        result = config_reload.research_config_check(str(temp_config_file))

        assert "changed" in result
        assert "reloaded" in result

    def test_check_nonexistent_file(self) -> None:
        """Check should handle nonexistent file gracefully."""
        result = config_reload.research_config_check("/nonexistent/path/config.json")

        assert result["changed"] is False
        assert result["reloaded"] is False
        assert "error" in result


class TestConfigDiff:
    """Tests for research_config_diff()."""

    def test_diff_no_changes(self, monkeypatch) -> None:
        """Diff should report no changes when config is identical."""
        config = {"SPIDER_CONCURRENCY": 10, "LOG_LEVEL": "INFO"}

        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: config
        )

        # Set up watch state with same config
        config_reload._watch_state["last_config"] = dict(config)

        result = config_reload.research_config_diff()

        assert result["changes"] == []
        assert result["unchanged_count"] == 2

    def test_diff_detects_all_changes(self, monkeypatch) -> None:
        """Diff should detect all changed keys."""
        old_config = {
            "SPIDER_CONCURRENCY": 10,
            "LOG_LEVEL": "INFO",
            "MAX_CHARS_HARD_CAP": 200000,
        }
        new_config = {
            "SPIDER_CONCURRENCY": 15,  # Changed
            "LOG_LEVEL": "INFO",  # Unchanged
            "MAX_CHARS_HARD_CAP": 300000,  # Changed
        }

        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: new_config
        )
        config_reload._watch_state["last_config"] = dict(old_config)

        result = config_reload.research_config_diff()

        assert len(result["changes"]) == 2
        assert result["unchanged_count"] == 1

        # Check specific changes
        changes_by_key = {c["key"]: c for c in result["changes"]}
        assert changes_by_key["SPIDER_CONCURRENCY"]["old_value"] == 10
        assert changes_by_key["SPIDER_CONCURRENCY"]["new_value"] == 15
        assert changes_by_key["MAX_CHARS_HARD_CAP"]["old_value"] == 200000
        assert changes_by_key["MAX_CHARS_HARD_CAP"]["new_value"] == 300000

    def test_diff_single_key(self, monkeypatch) -> None:
        """Diff with key parameter should only show that key."""
        old_config = {"SPIDER_CONCURRENCY": 10, "LOG_LEVEL": "INFO"}
        new_config = {"SPIDER_CONCURRENCY": 15, "LOG_LEVEL": "INFO"}

        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: new_config
        )
        config_reload._watch_state["last_config"] = dict(old_config)

        result = config_reload.research_config_diff("SPIDER_CONCURRENCY")

        assert len(result["changes"]) == 1
        assert result["changes"][0]["key"] == "SPIDER_CONCURRENCY"
        assert result["changes"][0]["old_value"] == 10
        assert result["changes"][0]["new_value"] == 15

    def test_diff_key_not_changed(self, monkeypatch) -> None:
        """Diff for unchanged key should return empty changes."""
        config = {"SPIDER_CONCURRENCY": 10, "LOG_LEVEL": "INFO"}

        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: config
        )
        config_reload._watch_state["last_config"] = dict(config)

        result = config_reload.research_config_diff("LOG_LEVEL")

        assert result["changes"] == []
        assert result["unchanged_count"] == 1

    def test_diff_new_keys_detected(self, monkeypatch) -> None:
        """Diff should detect newly added keys."""
        old_config = {"SPIDER_CONCURRENCY": 10}
        new_config = {
            "SPIDER_CONCURRENCY": 10,
            "NEW_KEY": "new_value",
        }

        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: new_config
        )
        config_reload._watch_state["last_config"] = dict(old_config)

        result = config_reload.research_config_diff()

        assert len(result["changes"]) == 1
        assert result["changes"][0]["key"] == "NEW_KEY"
        assert result["changes"][0]["old_value"] is None
        assert result["changes"][0]["new_value"] == "new_value"

    def test_diff_removed_keys_detected(self, monkeypatch) -> None:
        """Diff should detect removed keys."""
        old_config = {
            "SPIDER_CONCURRENCY": 10,
            "REMOVED_KEY": "value",
        }
        new_config = {"SPIDER_CONCURRENCY": 10}

        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: new_config
        )
        config_reload._watch_state["last_config"] = dict(old_config)

        result = config_reload.research_config_diff()

        assert len(result["changes"]) == 1
        assert result["changes"][0]["key"] == "REMOVED_KEY"
        assert result["changes"][0]["old_value"] == "value"
        assert result["changes"][0]["new_value"] is None


class TestConfigReloadIntegration:
    """Integration tests for the full watch → check → diff workflow."""

    def test_full_workflow(self, temp_config_file: Path, monkeypatch) -> None:
        """Test complete workflow: watch → check → diff."""
        old_config = {"SPIDER_CONCURRENCY": 10, "LOG_LEVEL": "INFO"}
        new_config = {"SPIDER_CONCURRENCY": 15, "LOG_LEVEL": "INFO"}

        # Mock initial get_config
        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: old_config
        )

        # Start watching
        watch_result = config_reload.research_config_watch(str(temp_config_file))
        assert watch_result["watching"] is True

        # Simulate time passing and file modification
        time.sleep(0.01)
        temp_config_file.touch()

        # Mock updated config
        monkeypatch.setattr(
            "loom.tools.config_reload.get_config",
            lambda: new_config
        )
        monkeypatch.setattr(
            "loom.tools.config_reload.load_config",
            lambda path: new_config
        )

        # Check for changes
        check_result = config_reload.research_config_check(str(temp_config_file))
        assert check_result["changed"] is True
        assert check_result["reloaded"] is True

        # Verify diff
        diff_result = config_reload.research_config_diff()
        assert len(diff_result["changes"]) == 1
        assert diff_result["changes"][0]["key"] == "SPIDER_CONCURRENCY"
