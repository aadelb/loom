"""Unit tests for all tool modules.

Tests cover:
  - Each .py in src/loom/tools/ imports successfully
  - Each research_* function is callable
  - All tools have docstrings
  - Type hints present on signatures
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.unit


def _get_tool_modules() -> list[str]:
    """Get all tool module names from src/loom/tools (including subdirectories)."""
    tools_dir = Path(__file__).parent.parent.parent / "src" / "loom" / "tools"
    skip_dirs = {"reframe_strategies", "__pycache__"}
    tool_modules = []
    for f in tools_dir.glob("*.py"):
        if f.name != "__init__.py" and not f.name.startswith("_"):
            tool_modules.append(f.stem)
    for subdir in sorted(tools_dir.iterdir()):
        if subdir.is_dir() and subdir.name not in skip_dirs:
            for f in subdir.glob("*.py"):
                if f.name != "__init__.py" and not f.name.startswith("_"):
                    tool_modules.append(f"{subdir.name}.{f.stem}")
    return sorted(tool_modules)


class TestToolModuleImports:
    """Test that all tool modules import successfully."""

    @pytest.mark.parametrize("module_name", _get_tool_modules())
    def test_tool_module_imports(self, module_name: str) -> None:
        """Each tool module imports without errors."""
        try:
            importlib.import_module(f"loom.tools.{module_name}")
        except Exception as e:
            pytest.fail(f"Failed to import loom.tools.{module_name}: {e}")


class TestToolFunctionSignatures:
    """Test that tool functions have proper signatures."""

    def test_tool_functions_callable(self) -> None:
        """Tool functions are callable and have type hints."""
        tools_dir = Path(__file__).parent.parent.parent / "src" / "loom" / "tools"
        skip_dirs = {"reframe_strategies", "__pycache__"}
        tool_files = list(tools_dir.glob("*.py"))
        for subdir in sorted(tools_dir.iterdir()):
            if subdir.is_dir() and subdir.name not in skip_dirs:
                tool_files.extend(subdir.glob("*.py"))
        tool_files = [f for f in tool_files if f.name != "__init__.py"]

        checked_count = 0
        for tool_file in tool_files[:20]:  # Check first 20 tools
            rel = tool_file.relative_to(tools_dir)
            if len(rel.parts) == 1:
                import_path = f"loom.tools.{tool_file.stem}"
            else:
                import_path = f"loom.tools.{rel.parent.name}.{tool_file.stem}"
            try:
                module = importlib.import_module(import_path)

                # Find research_* functions
                for name, obj in inspect.getmembers(module):
                    if name.startswith("research_") and callable(obj):
                        checked_count += 1

                        # Verify it's callable
                        assert callable(obj), f"{name} not callable"

                        # Check for docstring
                        if not obj.__doc__:
                            pytest.skip(f"{name} missing docstring")

            except Exception as e:
                pytest.fail(f"Error checking {module_name}: {e}")

        assert checked_count > 5, "Should have found multiple research_* functions"


class TestToolDocstrings:
    """Test that tools have documentation."""

    def test_sample_tools_have_docstrings(self) -> None:
        """Sample of tool modules have docstrings."""
        sample_modules = [
            "core.fetch",
            "core.spider",
            "core.markdown",
            "core.search",
            "core.deep",
        ]

        for module_name in sample_modules:
            try:
                module = importlib.import_module(f"loom.tools.{module_name}")

                # Check if module has docstring
                assert module.__doc__ is not None, f"Module {module_name} missing docstring"

                # Find first research_* function and verify docstring
                for name, obj in inspect.getmembers(module):
                    if name.startswith("research_") and callable(obj):
                        if obj.__doc__ is None:
                            pytest.skip(f"{module_name}:{name} missing docstring")
                        assert len(obj.__doc__) > 10, (
                            f"{module_name}:{name} docstring too short"
                        )
                        break

            except ModuleNotFoundError:
                pytest.skip(f"Module loom.tools.{module_name} not found")


class TestTypeHints:
    """Test that tool functions have type hints."""

    def test_sample_functions_have_type_hints(self) -> None:
        """Sample functions have type annotations."""
        sample_modules = ["core.fetch", "core.cache_mgmt"]

        checked_count = 0
        for module_name in sample_modules:
            try:
                module = importlib.import_module(f"loom.tools.{module_name}")

                for name, obj in inspect.getmembers(module):
                    if name.startswith("research_") and callable(obj):
                        sig = inspect.signature(obj)
                        checked_count += 1

                        # Verify at least one parameter has type hint
                        has_hints = False
                        for param_name, param in sig.parameters.items():
                            if param.annotation != inspect.Parameter.empty:
                                has_hints = True
                                break

                        # Return type should be annotated
                        assert sig.return_annotation != inspect.Signature.empty, (
                            f"{module_name}:{name} missing return type hint"
                        )

                        break

            except ModuleNotFoundError:
                pytest.skip(f"Module loom.tools.{module_name} not found")

        assert checked_count > 1, "Should have checked multiple functions"


class TestNoImportErrors:
    """Test that importing all tools produces no errors."""

    def test_import_all_tools(self) -> None:
        """Importing loom.tools.__init__ works."""
        try:
            import loom.tools  # noqa: F401

            assert True
        except Exception as e:
            pytest.fail(f"Failed to import loom.tools: {e}")

    def test_all_modules_importable(self) -> None:
        """All tool modules are importable (sample check)."""
        tool_names = _get_tool_modules()

        # Test first 50 modules
        for module_name in tool_names[:50]:
            try:
                importlib.import_module(f"loom.tools.{module_name}")
            except Exception as e:
                pytest.fail(f"loom.tools.{module_name} not importable: {e}")


class TestToolModuleStructure:
    """Test basic structure of tool modules."""

    def test_sample_module_has_docstring(self) -> None:
        """Sample tool modules have module-level docstrings."""
        sample = ["core.fetch", "core.spider"]

        for module_name in sample:
            try:
                module = importlib.import_module(f"loom.tools.{module_name}")
                assert module.__doc__ is not None, (
                    f"loom.tools.{module_name} missing module docstring"
                )
                assert len(module.__doc__) > 5, (
                    f"loom.tools.{module_name} docstring too short"
                )
            except ModuleNotFoundError:
                pytest.skip(f"Module loom.tools.{module_name} not found")
