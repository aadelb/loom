"""Tests for tool versioning system."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loom.tools.tool_versioning import (
    _count_lines,
    _hash_file,
    _tool_info,
    research_tool_version,
    research_version_diff,
    research_version_snapshot,
)


@pytest.fixture
def temp_tool_file(tmp_path):
    """Create a temporary tool file."""
    tool_file = tmp_path / "test_tool.py"
    tool_file.write_text("def test_func():\n    pass\n")
    return tool_file


class TestHashFile:
    """Test file hashing functionality."""

    def test_hash_file_consistency(self, temp_tool_file):
        """Same file produces same hash."""
        hash1 = _hash_file(temp_tool_file)
        hash2 = _hash_file(temp_tool_file)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_hash_file_different_content(self, tmp_path):
        """Different content produces different hash."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content1")
        file2.write_text("content2")

        assert _hash_file(file1) != _hash_file(file2)


class TestCountLines:
    """Test line counting functionality."""

    def test_count_lines_basic(self, temp_tool_file):
        """Count lines in a simple file."""
        assert _count_lines(temp_tool_file) == 2

    def test_count_lines_multiline(self, tmp_path):
        """Count lines in a larger file."""
        file = tmp_path / "multi.py"
        content = "\n".join([f"line {i}" for i in range(10)])
        file.write_text(content)
        assert _count_lines(file) == 10

    def test_count_lines_nonexistent(self, tmp_path):
        """Count lines in nonexistent file returns 0."""
        assert _count_lines(tmp_path / "nonexistent.py") == 0

    def test_count_lines_binary(self, tmp_path):
        """Count lines in binary file returns 0."""
        file = tmp_path / "binary.bin"
        file.write_bytes(b"\x00\x01\x02")
        assert _count_lines(file) == 0


class TestToolInfo:
    """Test tool info retrieval."""

    def test_tool_info_structure(self, temp_tool_file):
        """Tool info has all required fields."""
        info = _tool_info(temp_tool_file)

        assert "tool" in info
        assert "version_hash" in info
        assert "file_size" in info
        assert "last_modified" in info
        assert "lines_of_code" in info

        assert info["tool"] == "test_tool"
        assert len(info["version_hash"]) == 64
        assert info["file_size"] > 0
        assert info["lines_of_code"] == 2

    def test_tool_info_timestamp_format(self, temp_tool_file):
        """Tool info timestamp is ISO format."""
        info = _tool_info(temp_tool_file)
        # Should be ISO format with timezone
        assert "T" in info["last_modified"]
        assert "+" in info["last_modified"] or "Z" in info["last_modified"]


class TestResearchToolVersion:
    """Test research_tool_version function."""

    @pytest.mark.asyncio
    async def test_single_tool_not_found(self):
        """Get version for nonexistent tool."""
        result = await research_tool_version("nonexistent_tool")
        assert "error" in result

    @pytest.mark.asyncio
    @patch("loom.tools.tool_versioning.TOOLS_DIR")
    async def test_single_tool_found(self, mock_tools_dir, tmp_path):
        """Get version for existing tool."""
        tool_file = tmp_path / "sample.py"
        tool_file.write_text("# sample tool\n")
        mock_tools_dir.__truediv__.return_value = tool_file

        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            # Create a real tool file in tmp_path
            tool_file = tmp_path / "sample.py"
            tool_file.write_text("# sample tool\n")

            result = await research_tool_version("sample")
            assert result["tool"] == "sample"
            assert "version_hash" in result
            assert "file_size" in result

    @pytest.mark.asyncio
    @patch("loom.tools.tool_versioning.TOOLS_DIR")
    async def test_all_tools(self, mock_tools_dir, tmp_path):
        """Get versions for all tools."""
        # Create sample tool files
        (tmp_path / "tool1.py").write_text("# tool1")
        (tmp_path / "tool2.py").write_text("# tool2")
        (tmp_path / "__init__.py").write_text("")  # Should be skipped

        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            result = await research_tool_version()

            assert "tools_count" in result
            assert "total_size_bytes" in result
            assert "tools" in result
            assert result["tools_count"] == 2  # Only tool1 and tool2
            assert all("version_hash" in t for t in result["tools"])


class TestResearchVersionDiff:
    """Test research_version_diff function."""

    @pytest.mark.asyncio
    async def test_diff_nonexistent_tool(self):
        """Diff for nonexistent tool."""
        result = await research_version_diff("nonexistent", "somehash")
        assert "error" in result

    @pytest.mark.asyncio
    @patch("loom.tools.tool_versioning.TOOLS_DIR")
    async def test_diff_with_previous_hash(self, mock_tools_dir, tmp_path):
        """Diff with previous hash shows changed status."""
        tool_file = tmp_path / "sample.py"
        tool_file.write_text("# updated content")

        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            result = await research_version_diff("sample", "oldhash123")

            assert result["tool"] == "sample"
            assert result["previous_hash"] == "oldhash123"
            assert "current_hash" in result
            assert result["changed"] is True
            assert "current_size" in result
            assert "current_lines" in result

    @pytest.mark.asyncio
    @patch("loom.tools.tool_versioning.TOOLS_DIR")
    async def test_diff_same_hash(self, mock_tools_dir, tmp_path):
        """Diff with matching hash shows unchanged."""
        tool_file = tmp_path / "sample.py"
        tool_file.write_text("# content")
        current_hash = _hash_file(tool_file)

        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            result = await research_version_diff("sample", current_hash)

            assert result["changed"] is False
            assert result["current_hash"] == current_hash

    @pytest.mark.asyncio
    @patch("loom.tools.tool_versioning.TOOLS_DIR")
    async def test_diff_no_previous_hash(self, mock_tools_dir, tmp_path):
        """Diff without previous hash uses 'none'."""
        tool_file = tmp_path / "sample.py"
        tool_file.write_text("# content")

        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            result = await research_version_diff("sample")

            assert result["previous_hash"] == "none"
            assert result["changed"] is True


class TestResearchVersionSnapshot:
    """Test research_version_snapshot function."""

    @pytest.mark.asyncio
    async def test_snapshot_creation(self, tmp_path):
        """Create version snapshot."""
        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            with patch("loom.tools.tool_versioning.SNAPSHOTS_DIR", tmp_path / "snapshots"):
                # Create tool files
                (tmp_path / "tool1.py").write_text("# tool1")
                (tmp_path / "tool2.py").write_text("# tool2")

                result = await research_version_snapshot()

                assert "snapshot_id" in result
                assert "tools_count" in result
                assert "total_size_bytes" in result
                assert "timestamp" in result
                assert "file_path" in result
                assert result["tools_count"] == 2

    @pytest.mark.asyncio
    async def test_snapshot_file_structure(self, tmp_path):
        """Snapshot file has correct JSON structure."""
        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            with patch("loom.tools.tool_versioning.SNAPSHOTS_DIR", tmp_path / "snapshots"):
                (tmp_path / "sample.py").write_text("# sample")

                result = await research_version_snapshot()

                snapshot_file = Path(result["file_path"])
                assert snapshot_file.exists()

                data = json.loads(snapshot_file.read_text())
                assert "timestamp" in data
                assert "tools" in data
                assert "sample" in data["tools"]

    @pytest.mark.asyncio
    async def test_snapshot_handles_permission_error(self, tmp_path):
        """Snapshot handles permission errors gracefully."""
        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            with patch("loom.tools.tool_versioning.SNAPSHOTS_DIR", Path("/root/impossible")):
                result = await research_version_snapshot()
                # Should handle error gracefully
                assert "error" in result or "snapshot_id" in result


class TestIntegration:
    """Integration tests for the versioning system."""

    @pytest.mark.asyncio
    async def test_version_workflow(self, tmp_path):
        """Test complete versioning workflow."""
        with patch("loom.tools.tool_versioning.TOOLS_DIR", tmp_path):
            with patch("loom.tools.tool_versioning.SNAPSHOTS_DIR", tmp_path / "snapshots"):
                # Create initial tools
                (tmp_path / "tool1.py").write_text("# v1")
                (tmp_path / "tool2.py").write_text("# v1")

                # Get initial version
                v1 = await research_tool_version("tool1")
                hash1 = v1["version_hash"]

                # Take snapshot
                snap1 = await research_version_snapshot()
                assert snap1["tools_count"] == 2

                # Update tool
                (tmp_path / "tool1.py").write_text("# v2 - updated content")

                # Check diff
                diff = await research_version_diff("tool1", hash1)
                assert diff["changed"] is True

                # Take new snapshot
                snap2 = await research_version_snapshot()
                assert snap2["snapshot_id"] != snap1["snapshot_id"]
