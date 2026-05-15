"""Tests for web page change monitoring (change_monitor)."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_db_dir():
    """Provide a temporary directory for test database."""
    with tempfile.TemporaryDirectory(prefix="loom_change_monitor_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_db_path(tmp_db_dir, monkeypatch):
    """Mock the database path to use a temporary directory."""
    db_path = tmp_db_dir / "change_monitor.db"
    monkeypatch.setattr("loom.tools.intelligence.change_monitor._DB_PATH", db_path)
    return db_path


class TestResearchChangeMonitor:
    """Test change monitor core functionality."""

    def test_first_check_no_previous(self, mock_db_path):
        """Test first check of a URL with no previous record."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        test_content = "<html><body>Hello World</body></html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content", return_value=test_content):
            result = research_change_monitor("https://example.com", store_result=True)

        assert result["url"] == "https://example.com"
        assert result["previous_hash"] is None
        assert result["changed"] is False
        assert result["change_type"] == "no_change"
        assert result["check_count"] == 1
        assert result["first_seen"] is not None
        assert result["last_changed"] is not None
        assert len(result["current_hash"]) == 64  # SHA-256 hex length

    def test_second_check_no_change(self, mock_db_path):
        """Test second check with identical content."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        test_content = "<html><body>Hello World</body></html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content", return_value=test_content):
            # First check
            result1 = research_change_monitor("https://example.com", store_result=True)
            first_hash = result1["current_hash"]

            # Second check with same content
            result2 = research_change_monitor("https://example.com", store_result=True)

        assert result2["previous_hash"] == first_hash
        assert result2["current_hash"] == first_hash
        assert result2["changed"] is False
        assert result2["change_type"] == "no_change"
        assert result2["check_count"] == 2

    def test_content_added(self, mock_db_path):
        """Test detection of added content."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        content1 = "<html><body>Original content</body></html>"
        content2 = "<html><body>Original content\nNew line added</body></html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content") as mock_fetch:
            # First check
            mock_fetch.return_value = content1
            _ = research_change_monitor("https://example.com", store_result=True)

            # Second check with added content
            mock_fetch.return_value = content2
            result2 = research_change_monitor("https://example.com", store_result=True)

        assert result2["changed"] is True
        assert result2["change_type"] == "content_added"
        assert result2["changes_detected"] > 0
        assert len(result2["diff_summary"]) > 0

    def test_content_removed(self, mock_db_path):
        """Test detection of removed content."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        content1 = "<html><body>Line 1\nLine 2\nLine 3</body></html>"
        content2 = "<html><body>Line 1\nLine 3</body></html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content") as mock_fetch:
            # First check
            mock_fetch.return_value = content1
            _ = research_change_monitor("https://example.com", store_result=True)

            # Second check with removed content
            mock_fetch.return_value = content2
            result2 = research_change_monitor("https://example.com", store_result=True)

        assert result2["changed"] is True
        assert result2["change_type"] == "content_removed"
        assert result2["changes_detected"] > 0

    def test_content_modified(self, mock_db_path):
        """Test detection of modified content (same length)."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        content1 = "<html><body>Hello</body></html>"
        content2 = "<html><body>World</body></html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content") as mock_fetch:
            # First check
            mock_fetch.return_value = content1
            _ = research_change_monitor("https://example.com", store_result=True)

            # Second check with modified content
            mock_fetch.return_value = content2
            result2 = research_change_monitor("https://example.com", store_result=True)

        assert result2["changed"] is True
        assert result2["change_type"] == "content_modified"

    def test_fetch_failure(self, mock_db_path):
        """Test handling of fetch failures."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        with patch("loom.tools.intelligence.change_monitor._fetch_content", side_effect=Exception("Connection error")):
            result = research_change_monitor("https://example.com", store_result=False)

        assert "error" in result
        assert result["change_type"] == "error"
        assert result["current_hash"] is None

    def test_store_result_false(self, mock_db_path):
        """Test that store_result=False prevents database updates."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        test_content = "<html><body>Test</body></html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content", return_value=test_content):
            result = research_change_monitor("https://example.com", store_result=False)

        # Check that it still returns valid result
        assert result["url"] == "https://example.com"
        assert result["current_hash"] is not None

    def test_multiple_urls_independent(self, mock_db_path):
        """Test that multiple URLs are tracked independently."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        content1 = "<html>URL1</html>"
        content2 = "<html>URL2</html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content") as mock_fetch:
            # Monitor two different URLs
            mock_fetch.return_value = content1
            result1a = research_change_monitor("https://example1.com", store_result=True)
            hash1a = result1a["current_hash"]

            mock_fetch.return_value = content2
            result2a = research_change_monitor("https://example2.com", store_result=True)
            hash2a = result2a["current_hash"]

            # Check both again with same content
            mock_fetch.return_value = content1
            result1b = research_change_monitor("https://example1.com", store_result=True)

            mock_fetch.return_value = content2
            result2b = research_change_monitor("https://example2.com", store_result=True)

        # Both should be unchanged
        assert result1b["current_hash"] == hash1a
        assert result1b["changed"] is False
        assert result2b["current_hash"] == hash2a
        assert result2b["changed"] is False

    def test_diff_summary_truncated(self, mock_db_path):
        """Test that diff_summary is truncated appropriately."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        content1 = "line 1\nline 2\nline 3\n"
        content2 = "line 1\nline 2 modified\nline 3\n"

        with patch("loom.tools.intelligence.change_monitor._fetch_content") as mock_fetch:
            mock_fetch.return_value = content1
            _ = research_change_monitor("https://example.com", store_result=True)

            mock_fetch.return_value = content2
            result = research_change_monitor("https://example.com", store_result=True)

        # Diff summary should exist but be truncated
        assert result["changed"] is True
        assert len(result["diff_summary"]) <= 500


class TestDatabaseOperations:
    """Test database operations."""

    def test_db_initialization(self, mock_db_path):
        """Test that database is initialized properly."""
        from loom.tools.intelligence.change_monitor import _init_db

        _init_db()
        assert mock_db_path.exists()

    def test_db_persistence(self, mock_db_path):
        """Test that data persists across function calls."""
        from loom.tools.intelligence.change_monitor import research_change_monitor

        content = "<html><body>Test</body></html>"

        with patch("loom.tools.intelligence.change_monitor._fetch_content", return_value=content):
            # First call
            result1 = research_change_monitor("https://example.com", store_result=True)
            hash1 = result1["current_hash"]
            check_count1 = result1["check_count"]

            # Second call - should see previous hash
            result2 = research_change_monitor("https://example.com", store_result=True)

        assert result2["previous_hash"] == hash1
        assert result2["check_count"] == check_count1 + 1


class TestHashComputation:
    """Test hash computation utility."""

    def test_consistent_hash(self):
        """Test that same content produces same hash."""
        from loom.tools.intelligence.change_monitor import _compute_hash

        content = "<html><body>Test</body></html>"
        hash1 = _compute_hash(content)
        hash2 = _compute_hash(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Test that different content produces different hash."""
        from loom.tools.intelligence.change_monitor import _compute_hash

        hash1 = _compute_hash("content1")
        hash2 = _compute_hash("content2")

        assert hash1 != hash2

    def test_hash_format(self):
        """Test that hash is SHA-256 hex format."""
        from loom.tools.intelligence.change_monitor import _compute_hash

        hash_val = _compute_hash("test")

        assert len(hash_val) == 64
        assert all(c in "0123456789abcdef" for c in hash_val)


class TestDiffComputation:
    """Test diff computation utility."""

    def test_diff_computation_basic(self):
        """Test basic diff computation."""
        from loom.tools.intelligence.change_monitor import _compute_diff

        old = "line1\nline2\nline3"
        new = "line1\nline2b\nline3"

        diff_text, changed_count = _compute_diff(old, new)

        assert changed_count > 0
        assert "line2" in diff_text or "line2b" in diff_text

    def test_diff_with_additions(self):
        """Test diff with added lines."""
        from loom.tools.intelligence.change_monitor import _compute_diff

        old = "line1\nline2"
        new = "line1\nline2\nline3\nline4"

        diff_text, changed_count = _compute_diff(old, new)

        assert changed_count >= 2  # At least 2 new lines
        assert "line3" in diff_text
        assert "line4" in diff_text
