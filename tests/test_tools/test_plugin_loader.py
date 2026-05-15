"""Tests for the plugin loader infrastructure."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import loom.tools.infrastructure.plugin_loader


@pytest.mark.asyncio
async def test_plugin_load_valid_plugin():
    """Test loading a valid plugin with research_* functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = Path(tmpdir) / "test_plugin.py"
        plugin_path.write_text("""
async def research_test_func():
    '''Test function.'''
    return {"result": "success"}

async def research_another_func(arg: str):
    '''Another test function.'''
    return {"input": arg}
""")

        result = await plugin_loader.research_plugin_load(str(plugin_path))

        assert result["loaded"] is True
        assert "plugin_" in result["plugin_id"]
        assert len(result["tools_found"]) == 2
        assert "research_test_func" in result["tools_found"]
        assert "research_another_func" in result["tools_found"]


@pytest.mark.asyncio
async def test_plugin_load_nonexistent_file():
    """Test loading a file that doesn't exist."""
    result = await plugin_loader.research_plugin_load("/nonexistent/file.py")

    assert result["loaded"] is False
    assert "does not exist" in result["error"]


@pytest.mark.asyncio
async def test_plugin_load_non_py_file():
    """Test loading a file with non-.py extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_py_path = Path(tmpdir) / "plugin.txt"
        non_py_path.write_text("some content")

        result = await plugin_loader.research_plugin_load(str(non_py_path))

        assert result["loaded"] is False
        assert ".py extension" in result["error"]


@pytest.mark.asyncio
async def test_plugin_load_no_research_functions():
    """Test loading a .py file with no research_* functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = Path(tmpdir) / "no_research.py"
        plugin_path.write_text("""
async def some_function():
    return "not a research function"

def sync_function():
    return "sync"
""")

        result = await plugin_loader.research_plugin_load(str(plugin_path))

        assert result["loaded"] is False
        assert "No research_" in result["error"]


@pytest.mark.asyncio
async def test_plugin_load_mixed_functions():
    """Test loading a plugin with research_* async and other functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = Path(tmpdir) / "mixed_plugin.py"
        plugin_path.write_text("""
async def research_async_func():
    return "async"

def sync_func():
    return "sync"

async def research_another():
    return "another"
""")

        result = await plugin_loader.research_plugin_load(str(plugin_path))

        assert result["loaded"] is True
        assert len(result["tools_found"]) == 2
        assert "research_async_func" in result["tools_found"]
        assert "research_another" in result["tools_found"]


@pytest.mark.asyncio
async def test_plugin_list_empty():
    """Test listing plugins when none are loaded."""
    plugin_loader._plugins.clear()
    result = await plugin_loader.research_plugin_list()

    assert result["total"] == 0
    assert result["plugins"] == []


@pytest.mark.asyncio
async def test_plugin_list_with_loaded_plugins():
    """Test listing loaded plugins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = Path(tmpdir) / "test_plugin.py"
        plugin_path.write_text("""
async def research_test_func():
    return "test"
""")

        plugin_loader._plugins.clear()
        load_result = await plugin_loader.research_plugin_load(str(plugin_path))
        plugin_id = load_result["plugin_id"]

        list_result = await plugin_loader.research_plugin_list()

        assert list_result["total"] == 1
        assert len(list_result["plugins"]) == 1
        assert list_result["plugins"][0]["id"] == plugin_id
        assert list_result["plugins"][0]["tools"] == ["research_test_func"]
        assert "loaded_at" in list_result["plugins"][0]


@pytest.mark.asyncio
async def test_plugin_unload_valid():
    """Test unloading a loaded plugin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = Path(tmpdir) / "test_plugin.py"
        plugin_path.write_text("""
async def research_test_func():
    return "test"
""")

        plugin_loader._plugins.clear()
        load_result = await plugin_loader.research_plugin_load(str(plugin_path))
        plugin_id = load_result["plugin_id"]

        unload_result = await plugin_loader.research_plugin_unload(plugin_id)

        assert unload_result["unloaded"] is True
        assert unload_result["plugin_id"] == plugin_id

        # Verify plugin is removed
        list_result = await plugin_loader.research_plugin_list()
        assert list_result["total"] == 0


@pytest.mark.asyncio
async def test_plugin_unload_nonexistent():
    """Test unloading a plugin that doesn't exist."""
    plugin_loader._plugins.clear()
    result = await plugin_loader.research_plugin_unload("nonexistent_plugin")

    assert result["unloaded"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_plugin_load_invalid_python():
    """Test loading a file with invalid Python syntax."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = Path(tmpdir) / "invalid.py"
        plugin_path.write_text("this is not valid python syntax !!!")

        result = await plugin_loader.research_plugin_load(str(plugin_path))

        assert result["loaded"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_plugin_registry_isolation():
    """Test that multiple plugins don't interfere with each other."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_loader._plugins.clear()

        # Load first plugin
        plugin1_path = Path(tmpdir) / "plugin1.py"
        plugin1_path.write_text("""
async def research_plugin1_func():
    return "plugin1"
""")
        result1 = await plugin_loader.research_plugin_load(str(plugin1_path))
        plugin_id1 = result1["plugin_id"]

        # Load second plugin
        plugin2_path = Path(tmpdir) / "plugin2.py"
        plugin2_path.write_text("""
async def research_plugin2_func():
    return "plugin2"
""")
        result2 = await plugin_loader.research_plugin_load(str(plugin2_path))
        plugin_id2 = result2["plugin_id"]

        # Verify both are loaded
        list_result = await plugin_loader.research_plugin_list()
        assert list_result["total"] == 2

        # Unload first plugin
        await plugin_loader.research_plugin_unload(plugin_id1)

        # Verify second plugin still exists
        list_result = await plugin_loader.research_plugin_list()
        assert list_result["total"] == 1
        assert list_result["plugins"][0]["id"] == plugin_id2
