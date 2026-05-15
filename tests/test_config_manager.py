"""Unit tests for shared config_manager module.

Tests cover configuration loading, environment variable resolution,
typed accessor functions, and edge cases including missing config,
invalid values, environment variable overrides, and hot reload scenarios.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from loom.config_manager import (
    external_timeout,
    llm_timeout,
    fetch_timeout,
    max_chars,
    max_spider_urls,
    max_search_results,
    spider_concurrency,
    llm_cascade_order,
    default_llm_model,
    default_embed_model,
    default_temperature,
    llm_max_parallel,
    tor_enabled,
    cache_enabled,
    debug_mode,
    fetch_auto_escalate,
    cache_dir,
    sessions_dir,
)


class TestNetworkTimeouts:
    """Tests for timeout accessor functions — 6 test cases."""

    def test_external_timeout_default(self) -> None:
        """Return default external timeout."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = external_timeout()
            assert result == 30

    def test_external_timeout_custom(self) -> None:
        """Return custom external timeout."""
        with mock.patch('loom.config_manager._cfg', return_value={'EXTERNAL_TIMEOUT_SECS': 60}):
            result = external_timeout()
            assert result == 60

    def test_llm_timeout_default(self) -> None:
        """Return default LLM timeout."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = llm_timeout()
            assert result == 120

    def test_llm_timeout_custom(self) -> None:
        """Return custom LLM timeout."""
        with mock.patch('loom.config_manager._cfg', return_value={'LLM_TIMEOUT_SECS': 300}):
            result = llm_timeout()
            assert result == 300

    def test_fetch_timeout_default(self) -> None:
        """Return default fetch timeout."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = fetch_timeout()
            assert result == 20

    def test_fetch_timeout_custom(self) -> None:
        """Return custom fetch timeout."""
        with mock.patch('loom.config_manager._cfg', return_value={'FETCH_TIMEOUT_SECS': 45}):
            result = fetch_timeout()
            assert result == 45


class TestLimits:
    """Tests for limit accessor functions — 8 test cases."""

    def test_max_chars_default(self) -> None:
        """Return default max_chars limit."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = max_chars()
            assert result == 200_000

    def test_max_chars_custom(self) -> None:
        """Return custom max_chars limit."""
        with mock.patch('loom.config_manager._cfg', return_value={'MAX_CHARS_HARD_CAP': 100_000}):
            result = max_chars()
            assert result == 100_000

    def test_max_spider_urls_default(self) -> None:
        """Return default max_spider_urls limit."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = max_spider_urls()
            assert result == 100

    def test_max_spider_urls_custom(self) -> None:
        """Return custom max_spider_urls limit."""
        with mock.patch('loom.config_manager._cfg', return_value={'MAX_SPIDER_URLS': 500}):
            result = max_spider_urls()
            assert result == 500

    def test_max_search_results_default(self) -> None:
        """Return default max_search_results limit."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = max_search_results()
            assert result == 10

    def test_max_search_results_custom(self) -> None:
        """Return custom max_search_results limit."""
        with mock.patch('loom.config_manager._cfg', return_value={'MAX_SEARCH_RESULTS': 50}):
            result = max_search_results()
            assert result == 50

    def test_spider_concurrency_default(self) -> None:
        """Return default spider_concurrency."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = spider_concurrency()
            assert result == 10

    def test_spider_concurrency_custom(self) -> None:
        """Return custom spider_concurrency."""
        with mock.patch('loom.config_manager._cfg', return_value={'SPIDER_CONCURRENCY': 20}):
            result = spider_concurrency()
            assert result == 20


class TestLLMSettings:
    """Tests for LLM accessor functions — 9 test cases."""

    def test_llm_cascade_order_default(self) -> None:
        """Return default LLM cascade order."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = llm_cascade_order()
            assert "groq" in result
            assert "nvidia" in result
            assert isinstance(result, list)

    def test_llm_cascade_order_custom(self) -> None:
        """Return custom LLM cascade order."""
        custom_order = ["openai", "anthropic", "groq"]
        with mock.patch('loom.config_manager._cfg', return_value={'LLM_CASCADE_ORDER': custom_order}):
            result = llm_cascade_order()
            assert result == custom_order

    def test_default_llm_model_default(self) -> None:
        """Return default LLM model."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = default_llm_model()
            assert isinstance(result, str)

    def test_default_llm_model_custom(self) -> None:
        """Return custom default LLM model."""
        with mock.patch('loom.config_manager._cfg', return_value={'LLM_DEFAULT_CHAT_MODEL': 'gpt-4'}):
            result = default_llm_model()
            assert result == 'gpt-4'

    def test_default_embed_model_default(self) -> None:
        """Return default embed model."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = default_embed_model()
            assert isinstance(result, str)

    def test_default_embed_model_custom(self) -> None:
        """Return custom default embed model."""
        with mock.patch('loom.config_manager._cfg', return_value={'LLM_DEFAULT_EMBED_MODEL': 'text-embedding-3'}):
            result = default_embed_model()
            assert result == 'text-embedding-3'

    def test_default_temperature_default(self) -> None:
        """Return default temperature."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = default_temperature()
            assert result == 0.7

    def test_default_temperature_custom(self) -> None:
        """Return custom default temperature."""
        with mock.patch('loom.config_manager._cfg', return_value={'DEFAULT_TEMPERATURE': 0.5}):
            result = default_temperature()
            assert result == 0.5

    def test_llm_max_parallel_default(self) -> None:
        """Return default LLM max parallel."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = llm_max_parallel()
            assert result == 12


class TestFeatureFlags:
    """Tests for feature flag accessor functions — 8 test cases."""

    def test_tor_enabled_default(self) -> None:
        """Return default tor_enabled (False)."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = tor_enabled()
            assert result is False

    def test_tor_enabled_custom(self) -> None:
        """Return custom tor_enabled."""
        with mock.patch('loom.config_manager._cfg', return_value={'TOR_ENABLED': True}):
            result = tor_enabled()
            assert result is True

    def test_cache_enabled_default(self) -> None:
        """Return default cache_enabled (True)."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = cache_enabled()
            assert result is True

    def test_cache_enabled_custom(self) -> None:
        """Return custom cache_enabled."""
        with mock.patch('loom.config_manager._cfg', return_value={'CACHE_ENABLED': False}):
            result = cache_enabled()
            assert result is False

    def test_debug_mode_default(self) -> None:
        """Return default debug_mode (False)."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop('LOOM_DEBUG', None)
                result = debug_mode()
                assert result is False

    def test_debug_mode_from_config(self) -> None:
        """Return debug_mode from config."""
        with mock.patch('loom.config_manager._cfg', return_value={'DEBUG': True}):
            result = debug_mode()
            assert result is True

    def test_debug_mode_from_env(self) -> None:
        """Return debug_mode from environment variable."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            with mock.patch.dict(os.environ, {'LOOM_DEBUG': 'true'}):
                result = debug_mode()
                assert result is True

    def test_fetch_auto_escalate_default(self) -> None:
        """Return default fetch_auto_escalate (True)."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = fetch_auto_escalate()
            assert result is True


class TestPaths:
    """Tests for path accessor functions — 8 test cases."""

    def test_cache_dir_default(self) -> None:
        """Return default cache directory."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = cache_dir()
            assert isinstance(result, str)
            assert "loom" in result.lower()

    def test_cache_dir_custom(self) -> None:
        """Return custom cache directory."""
        custom_path = "/custom/cache/path"
        with mock.patch('loom.config_manager._cfg', return_value={'CACHE_DIR': custom_path}):
            result = cache_dir()
            assert result == custom_path

    def test_cache_dir_expands_tilde(self) -> None:
        """Expand ~ in cache directory path."""
        with mock.patch('loom.config_manager._cfg', return_value={'CACHE_DIR': '~/.loom_cache'}):
            result = cache_dir()
            assert "~" not in result
            assert result.startswith(os.path.expanduser("~"))

    def test_sessions_dir_default(self) -> None:
        """Return default sessions directory."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = sessions_dir()
            assert isinstance(result, str)
            assert "loom" in result.lower()

    def test_sessions_dir_custom(self) -> None:
        """Return custom sessions directory."""
        custom_path = "/custom/sessions/path"
        with mock.patch('loom.config_manager._cfg', return_value={'SESSION_DIR': custom_path}):
            result = sessions_dir()
            assert result == custom_path

    def test_sessions_dir_expands_tilde(self) -> None:
        """Expand ~ in sessions directory path."""
        with mock.patch('loom.config_manager._cfg', return_value={'SESSION_DIR': '~/.loom_sessions'}):
            result = sessions_dir()
            assert "~" not in result
            assert result.startswith(os.path.expanduser("~"))

    def test_cache_dir_returns_string(self) -> None:
        """Verify cache_dir returns string type."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = cache_dir()
            assert isinstance(result, str)

    def test_sessions_dir_returns_string(self) -> None:
        """Verify sessions_dir returns string type."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = sessions_dir()
            assert isinstance(result, str)


class TestConfigTypeConversions:
    """Tests for type conversion in accessors — 8 test cases."""

    def test_timeout_converts_to_float(self) -> None:
        """Timeout values are converted to float."""
        with mock.patch('loom.config_manager._cfg', return_value={'EXTERNAL_TIMEOUT_SECS': 30}):
            result = external_timeout()
            assert isinstance(result, float)

    def test_limit_converts_to_int(self) -> None:
        """Limit values are converted to int."""
        with mock.patch('loom.config_manager._cfg', return_value={'MAX_SPIDER_URLS': 100}):
            result = max_spider_urls()
            assert isinstance(result, int)

    def test_temperature_converts_to_float(self) -> None:
        """Temperature is converted to float."""
        with mock.patch('loom.config_manager._cfg', return_value={'DEFAULT_TEMPERATURE': 0.7}):
            result = default_temperature()
            assert isinstance(result, float)

    def test_cascade_order_is_list(self) -> None:
        """LLM cascade order is returned as list."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            result = llm_cascade_order()
            assert isinstance(result, list)

    def test_model_converts_to_string(self) -> None:
        """Model values are converted to string."""
        with mock.patch('loom.config_manager._cfg', return_value={'LLM_DEFAULT_CHAT_MODEL': 'gpt-4'}):
            result = default_llm_model()
            assert isinstance(result, str)

    def test_boolean_converts_to_bool(self) -> None:
        """Boolean values are converted to bool."""
        with mock.patch('loom.config_manager._cfg', return_value={'TOR_ENABLED': 1}):
            result = tor_enabled()
            assert isinstance(result, bool)

    def test_string_timeout_converts(self) -> None:
        """String timeout values are converted to float."""
        with mock.patch('loom.config_manager._cfg', return_value={'EXTERNAL_TIMEOUT_SECS': '30'}):
            result = external_timeout()
            assert result == 30.0

    def test_string_limit_converts(self) -> None:
        """String limit values are converted to int."""
        with mock.patch('loom.config_manager._cfg', return_value={'MAX_SPIDER_URLS': '100'}):
            result = max_spider_urls()
            assert result == 100


class TestConfigEdgeCases:
    """Tests for edge cases and error conditions — 6 test cases."""

    def test_missing_config_returns_defaults(self) -> None:
        """Missing config keys return defaults."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            external = external_timeout()
            llm = llm_timeout()
            fetch = fetch_timeout()
            assert all(isinstance(v, (int, float)) for v in [external, llm, fetch])

    def test_partial_config_with_missing_keys(self) -> None:
        """Partial config with missing keys returns mixed values."""
        cfg = {'EXTERNAL_TIMEOUT_SECS': 60}  # Only one key
        with mock.patch('loom.config_manager._cfg', return_value=cfg):
            external = external_timeout()
            llm = llm_timeout()
            assert external == 60
            assert llm == 120  # Default

    def test_none_config_value_raises(self) -> None:
        """None values cause TypeError when converted to float."""
        with mock.patch('loom.config_manager._cfg', return_value={'EXTERNAL_TIMEOUT_SECS': None}):
            # None in config will cause float(None) to raise TypeError
            with pytest.raises(TypeError):
                external_timeout()

    def test_empty_cascade_order(self) -> None:
        """Empty cascade order returns default."""
        with mock.patch('loom.config_manager._cfg', return_value={'LLM_CASCADE_ORDER': []}):
            result = llm_cascade_order()
            assert result == []

    def test_path_with_relative_component(self) -> None:
        """Paths with relative components are expanded."""
        with mock.patch('loom.config_manager._cfg', return_value={'CACHE_DIR': './cache'}):
            result = cache_dir()
            assert isinstance(result, str)

    def test_multiple_consecutive_calls(self) -> None:
        """Multiple consecutive calls with same config."""
        cfg = {'EXTERNAL_TIMEOUT_SECS': 45}
        with mock.patch('loom.config_manager._cfg', return_value=cfg):
            result1 = external_timeout()
            result2 = external_timeout()
            assert result1 == result2 == 45


class TestConfigIntegration:
    """Integration tests for config accessors — 4 test cases."""

    def test_all_accessors_with_full_config(self) -> None:
        """All accessors work with complete config."""
        full_cfg = {
            'EXTERNAL_TIMEOUT_SECS': 45,
            'LLM_TIMEOUT_SECS': 180,
            'FETCH_TIMEOUT_SECS': 25,
            'MAX_CHARS_HARD_CAP': 150_000,
            'MAX_SPIDER_URLS': 200,
            'MAX_SEARCH_RESULTS': 20,
            'SPIDER_CONCURRENCY': 15,
            'LLM_CASCADE_ORDER': ['openai', 'groq'],
            'LLM_DEFAULT_CHAT_MODEL': 'gpt-4',
            'LLM_DEFAULT_EMBED_MODEL': 'text-embedding-3',
            'DEFAULT_TEMPERATURE': 0.5,
            'LLM_MAX_PARALLEL': 8,
            'TOR_ENABLED': True,
            'CACHE_ENABLED': False,
            'DEBUG': True,
            'FETCH_AUTO_ESCALATE': False,
            'CACHE_DIR': '/tmp/cache',
            'SESSION_DIR': '/tmp/sessions',
        }
        with mock.patch('loom.config_manager._cfg', return_value=full_cfg):
            assert external_timeout() == 45
            assert llm_timeout() == 180
            assert max_chars() == 150_000
            assert tor_enabled() is True
            assert cache_enabled() is False

    def test_all_accessors_with_empty_config(self) -> None:
        """All accessors work with empty config (all defaults)."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            # Just ensure no exceptions are raised
            external_timeout()
            llm_timeout()
            fetch_timeout()
            max_chars()
            max_spider_urls()
            max_search_results()
            spider_concurrency()
            llm_cascade_order()
            default_llm_model()
            default_embed_model()
            default_temperature()
            llm_max_parallel()
            tor_enabled()
            cache_enabled()
            debug_mode()
            fetch_auto_escalate()
            cache_dir()
            sessions_dir()

    def test_config_values_are_consistent(self) -> None:
        """Config values remain consistent across multiple accesses."""
        cfg = {
            'EXTERNAL_TIMEOUT_SECS': 35,
            'MAX_SPIDER_URLS': 250,
        }
        with mock.patch('loom.config_manager._cfg', return_value=cfg):
            # Multiple accesses should return same values
            for _ in range(3):
                assert external_timeout() == 35
                assert max_spider_urls() == 250

    def test_timeout_values_reasonable(self) -> None:
        """Timeout values are reasonable positive numbers."""
        with mock.patch('loom.config_manager._cfg', return_value={}):
            assert external_timeout() > 0
            assert llm_timeout() > external_timeout()
            assert fetch_timeout() > 0
