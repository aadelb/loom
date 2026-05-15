"""Unit tests for LazyToolLoader.

Tests:
- Basic registration and loading
- Caching behavior
- Error handling (ImportError, AttributeError, KeyError)
- Statistics tracking
- Load time measurement
- Singleton pattern
"""

from __future__ import annotations

import pytest
import time
from unittest.mock import Mock, patch

from loom.tool_loader import LazyToolLoader, get_loader


class TestLazyToolLoader:
    """Tests for LazyToolLoader class."""

    @pytest.fixture
    def loader(self) -> LazyToolLoader:
        """Create a fresh loader instance for each test."""
        return LazyToolLoader()

    def test_register_simple(self, loader: LazyToolLoader) -> None:
        """Test basic tool registration."""
        loader.register("test_tool", "loom.tools.core.fetch", "research_fetch")
        assert "test_tool" in loader.get_all_registered()

    def test_register_duplicate_raises(self, loader: LazyToolLoader) -> None:
        """Test that registering duplicate tool name raises ValueError."""
        loader.register("test_tool", "loom.tools.core.fetch", "research_fetch")
        with pytest.raises(ValueError, match="already registered"):
            loader.register("test_tool", "loom.tools.core.spider", "research_spider")

    def test_load_valid_tool(self) -> None:
        """Test loading a real tool from loom.validators."""
        loader = LazyToolLoader()
        loader.register("research_validate_url", "loom.validators", "validate_url")

        func = loader.load("research_validate_url")
        assert callable(func)
        assert loader.is_loaded("research_validate_url")

    def test_load_caches_function(self, loader: LazyToolLoader) -> None:
        """Test that loaded functions are cached."""
        loader.register("research_validate_url", "loom.validators", "validate_url")

        func1 = loader.load("research_validate_url")
        func2 = loader.load("research_validate_url")

        # Should be same object (cached)
        assert func1 is func2

    def test_load_not_registered_raises(self, loader: LazyToolLoader) -> None:
        """Test that loading unregistered tool raises KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            loader.load("nonexistent_tool")

    def test_load_invalid_module_raises(self, loader: LazyToolLoader) -> None:
        """Test that invalid module path raises ImportError."""
        loader.register("bad_tool", "nonexistent.module", "func")

        with pytest.raises(ImportError):
            loader.load("bad_tool")

    def test_load_invalid_function_raises(self, loader: LazyToolLoader) -> None:
        """Test that invalid function name raises AttributeError."""
        loader.register("bad_func", "loom.validators", "nonexistent_function")

        with pytest.raises(AttributeError):
            loader.load("bad_func")

    def test_load_failed_marked_as_failed(self, loader: LazyToolLoader) -> None:
        """Test that failed load marks tool as failed."""
        loader.register("bad_tool", "nonexistent.module", "func")

        with pytest.raises(ImportError):
            loader.load("bad_tool")

        # Second attempt should raise ImportError immediately
        with pytest.raises(ImportError, match="previously failed"):
            loader.load("bad_tool")

    def test_is_loaded_before_and_after(self, loader: LazyToolLoader) -> None:
        """Test is_loaded() before and after loading."""
        loader.register("research_validate_url", "loom.validators", "validate_url")

        assert not loader.is_loaded("research_validate_url")
        loader.load("research_validate_url")
        assert loader.is_loaded("research_validate_url")

    def test_get_all_registered(self, loader: LazyToolLoader) -> None:
        """Test getting all registered tool names."""
        loader.register("tool1", "module1", "func1")
        loader.register("tool2", "module2", "func2")
        loader.register("tool3", "module3", "func3")

        registered = loader.get_all_registered()
        assert len(registered) == 3
        assert "tool1" in registered
        assert "tool2" in registered
        assert "tool3" in registered

    def test_get_load_stats_initial(self, loader: LazyToolLoader) -> None:
        """Test load stats before any loads."""
        loader.register("tool1", "module1", "func1")

        stats = loader.get_load_stats()
        assert stats["loaded_count"] == 0
        assert stats["failed_count"] == 0
        assert stats["registered_count"] == 1
        assert stats["avg_load_time_ms"] == 0.0
        assert stats["failed_tools"] == []

    def test_get_load_stats_after_load(self) -> None:
        """Test load stats after successful load."""
        loader = LazyToolLoader()
        loader.register("research_validate_url", "loom.validators", "validate_url")

        loader.load("research_validate_url")

        stats = loader.get_load_stats()
        assert stats["loaded_count"] == 1
        assert stats["failed_count"] == 0
        assert stats["registered_count"] == 1
        # Load time may be 0 if module already cached, so just check >= 0
        assert stats["avg_load_time_ms"] >= 0

    def test_get_load_stats_with_failures(self, loader: LazyToolLoader) -> None:
        """Test load stats with both successes and failures."""
        loader.register("good_tool", "loom.validators", "validate_url")
        loader.register("bad_tool", "nonexistent.module", "func")

        loader.load("good_tool")

        try:
            loader.load("bad_tool")
        except ImportError:
            pass

        stats = loader.get_load_stats()
        assert stats["loaded_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["registered_count"] == 2
        assert "bad_tool" in stats["failed_tools"]

    def test_get_load_time(self) -> None:
        """Test getting load time for specific tool."""
        loader = LazyToolLoader()
        loader.register("research_validate_url", "loom.validators", "validate_url")

        assert loader.get_load_time("research_validate_url") is None

        loader.load("research_validate_url")

        load_time = loader.get_load_time("research_validate_url")
        assert load_time is not None
        # Load time may be 0 if module already cached
        assert load_time >= 0

    def test_get_load_time_unloaded(self, loader: LazyToolLoader) -> None:
        """Test getting load time for unloaded tool returns None."""
        loader.register("tool1", "module1", "func1")
        assert loader.get_load_time("tool1") is None

    def test_unload_removes_from_cache(self) -> None:
        """Test that unload removes function from cache."""
        loader = LazyToolLoader()
        loader.register("research_validate_url", "loom.validators", "validate_url")

        loader.load("research_validate_url")
        assert loader.is_loaded("research_validate_url")

        loader.unload("research_validate_url")
        assert not loader.is_loaded("research_validate_url")

    def test_unload_not_loaded_raises(self, loader: LazyToolLoader) -> None:
        """Test that unloading non-cached tool raises KeyError."""
        loader.register("tool1", "module1", "func1")

        with pytest.raises(KeyError, match="not in cache"):
            loader.unload("tool1")

    def test_reset_clears_cache(self) -> None:
        """Test that reset clears all caches."""
        loader = LazyToolLoader()
        loader.register("research_validate_url", "loom.validators", "validate_url")
        loader.register("tool2", "module2", "func2")

        loader.load("research_validate_url")

        stats_before = loader.get_load_stats()
        assert stats_before["loaded_count"] > 0

        loader.reset()

        stats_after = loader.get_load_stats()
        assert stats_after["loaded_count"] == 0
        assert stats_after["failed_count"] == 0
        assert not loader.is_loaded("research_validate_url")

    def test_reset_preserves_registry(self) -> None:
        """Test that reset preserves tool registry."""
        loader = LazyToolLoader()
        loader.register("tool1", "module1", "func1")
        loader.register("tool2", "module2", "func2")

        loader.reset()

        registered = loader.get_all_registered()
        assert len(registered) == 2

    def test_get_loader_singleton(self) -> None:
        """Test that get_loader() returns singleton instance."""
        loader1 = get_loader()
        loader2 = get_loader()

        assert loader1 is loader2

    def test_load_time_measurement(self) -> None:
        """Test that load time is measured and reasonable."""
        loader = LazyToolLoader()
        loader.register("research_validate_url", "loom.validators", "validate_url")

        loader.load("research_validate_url")

        load_time = loader.get_load_time("research_validate_url")
        assert load_time is not None
        # Load time should be reasonable (0 to 5 seconds)
        assert 0 <= load_time < 5000

    def test_multiple_loads_same_cache(self) -> None:
        """Test that multiple registrations can be loaded."""
        loader = LazyToolLoader()
        loader.register("tool1", "loom.validators", "validate_url")
        loader.register("tool2", "loom.validators", "validate_url")

        func1 = loader.load("tool1")
        func2 = loader.load("tool2")

        # Both should be loaded and callable
        assert callable(func1)
        assert callable(func2)
        assert loader.get_load_stats()["loaded_count"] == 2

    def test_stats_calculations(self, loader: LazyToolLoader) -> None:
        """Test that statistics are calculated correctly."""
        loader.register("tool1", "loom.validators", "validate_url")
        loader.register("tool2", "loom.validators", "validate_url")
        loader.register("tool3", "invalid.module", "func")

        loader.load("tool1")
        loader.load("tool2")

        try:
            loader.load("tool3")
        except ImportError:
            pass

        stats = loader.get_load_stats()
        assert stats["registered_count"] == 3
        assert stats["loaded_count"] == 2
        assert stats["failed_count"] == 1
        # avg_load_time_ms may be 0 if modules are cached
        assert stats["avg_load_time_ms"] >= 0
        assert len(stats["load_times_by_tool"]) == 2
