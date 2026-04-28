"""Tests for web page change monitoring (change_monitor)."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    monkeypatch.setattr("loom.tools.change_monitor._DB_PATH", db_path)
    return db_path


class TestResearchChangeMonitor:
    """Test change monitor core functionality."""

    def test_first_check_no_previous(self, mock_db_path):
        """Test first check of a URL with no previous record."""
        from loom.tools.change_monitor import research_change_monitor

        test_content = "<html><body>Hello World</body></html>"

        with patch("loom.tools.change_monitor._fetch_content", return_value=test_content):
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
        from loom.tools.change_monitor import research_change_monitor

        test_content = "<html><body>Hello World</body></html>"

        with patch("loom.tools.change_monitor._fetch_content", return_value=test_content):
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
        from loom.tools.change_monitor import research_change_monitor

        content1 = "<html><body>Original content</body></html>"
        content2 = "<html><body>Original content\nNew line added</body></html>"

        with patch("loom.tools.change_monitor._fetch_content") as mock_fetch:
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
        from loom.tools.change_monitor import research_change_monitor

        content1 = "<html><body>Line 1\nLine 2\nLine 3</body></html>"
        content2 = "<html><body>Line 1\nLine 3</body></html>"

        with patch("loom.tools.change_monitor._fetch_content") as mock_fetch:
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
        """Test detection of modified content (same size)."""
        from loom.tools.change_monitor import research_change_monitor

        content1 = "<html><body>Hello Old World</body></html>"
        content2 = "<html><body>Hello New World</body></html>"

        with patch("loom.tools.change_monitor._fetch_content") as mock_fetch:
            # First check
            mock_fetch.return_value = content1
            _ = research_change_monitor("https://example.com", store_result=True)

            # Second check with modified content
            mock_fetch.return_value = content2
            result2 = research_change_monitor("https://example.com", store_result=True)

        assert result2["changed"] is True
        assert result2["change_type"] == "content_modified"
        assert result2["changes_detected"] > 0

    def test_fetch_failure(self, mock_db_path):
        """Test handling of fetch failures."""
        from loom.tools.change_monitor import research_change_monitor

        with patch(
            "loom.tools.change_monitor._fetch_content",
            side_effect=Exception("Network error"),
        ):
            result = research_change_monitor("https://example.com")

        assert result["error"] is not None
        assert "Failed to fetch content" in result["error"]
        assert result["changed"] is False
        assert result["change_type"] == "error"
        assert result["current_hash"] is None

    def test_store_result_false(self, mock_db_path):
        """Test that store_result=False does not store in database."""
        from loom.tools.change_monitor import research_change_monitor

        test_content = "<html><body>Test</body></html>"

        with patch("loom.tools.change_monitor._fetch_content", return_value=test_content):
            result = research_change_monitor(
                "https://example.com", store_result=False
            )

        # Should still return result but not store
        assert result["url"] == "https://example.com"
        # check_count should be 0 since we didn't store
        assert result["check_count"] == 0

    def test_multiple_urls_independent(self, mock_db_path):
        """Test that different URLs are tracked independently."""
        from loom.tools.change_monitor import research_change_monitor

        url1_content = "<html>Content for URL 1</html>"
        url2_content = "<html>Content for URL 2</html>"

        with patch("loom.tools.change_monitor._fetch_content") as mock_fetch:
            # Check URL 1
            mock_fetch.return_value = url1_content
            result1 = research_change_monitor("https://example1.com", store_result=True)

            # Check URL 2
            mock_fetch.return_value = url2_content
            result2 = research_change_monitor("https://example2.com", store_result=True)

            # Check URL 1 again with different content
            mock_fetch.return_value = url1_content + "<p>More content</p>"
            result3 = research_change_monitor("https://example1.com", store_result=True)

        assert result1["current_hash"] != result2["current_hash"]
        assert result3["changed"] is True
        assert result3["previous_hash"] == result1["current_hash"]

    def test_diff_summary_truncated(self, mock_db_path):
        """Test that diff_summary is truncated to 500 chars."""
        from loom.tools.change_monitor import research_change_monitor

        content1 = "<html><body>" + ("A" * 100) + "</body></html>"
        content2 = "<html><body>" + ("B" * 100) + "</body></html>"

        with patch("loom.tools.change_monitor._fetch_content") as mock_fetch:
            mock_fetch.return_value = content1
            _ = research_change_monitor("https://example.com", store_result=True)

            mock_fetch.return_value = content2
            result2 = research_change_monitor("https://example.com", store_result=True)

        # Diff summary should not exceed 500 chars
        assert len(result2["diff_summary"]) <= 500


class TestDatabaseOperations:
    """Test database initialization and operations."""

    def test_db_initialization(self, mock_db_path):
        """Test that database is properly initialized."""
        from loom.tools.change_monitor import _init_db

        _init_db()

        assert mock_db_path.exists()

        # Check that tables exist
        conn = sqlite3.connect(mock_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('url_snapshots', 'url_metadata')
            """
        )
        tables = cursor.fetchall()
        conn.close()

        assert len(tables) == 2

    def test_db_persistence(self, mock_db_path):
        """Test that data persists across calls."""
        from loom.tools.change_monitor import research_change_monitor

        test_content = "<html><body>Persistent test</body></html>"

        with patch("loom.tools.change_monitor._fetch_content", return_value=test_content):
            # First call
            result1 = research_change_monitor("https://persist.test", store_result=True)
            hash1 = result1["current_hash"]

            # Second call - should retrieve same hash
            result2 = research_change_monitor("https://persist.test", store_result=True)

        assert result2["previous_hash"] == hash1


class TestHashComputation:
    """Test hash computation and comparison."""

    def test_consistent_hash(self):
        """Test that same content produces same hash."""
        from loom.tools.change_monitor import _compute_hash

        content = "<html><body>Test</body></html>"
        hash1 = _compute_hash(content)
        hash2 = _compute_hash(content)

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Test that different content produces different hashes."""
        from loom.tools.change_monitor import _compute_hash

        content1 = "<html><body>Test 1</body></html>"
        content2 = "<html><body>Test 2</body></html>"

        hash1 = _compute_hash(content1)
        hash2 = _compute_hash(content2)

        assert hash1 != hash2

    def test_hash_format(self):
        """Test that hash is in valid SHA-256 format."""
        from loom.tools.change_monitor import _compute_hash

        content = "<html><body>Test</body></html>"
        hash_result = _compute_hash(content)

        # SHA-256 produces 64-char hex string
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestDiffComputation:
    """Test unified diff computation and change classification."""

    def test_diff_computation_basic(self):
        """Test basic diff computation."""
        from loom.tools.change_monitor import _compute_diff

        old = "Line 1\nLine 2\nLine 3"
        new = "Line 1\nLine 2 modified\nLine 3"

        diff_text, changed_count = _compute_diff(old, new)

        assert changed_count > 0
        assert "modified" in diff_text

    def test_diff_with_additions(self):
        """Test diff with added lines."""
        from loom.tools.change_monitor import _compute_diff

        old = "Line 1"
        new = "Line 1\nLine 2\nLine 3"

        diff_text, changed_count = _compute_diff(old, new)

        assert changed_count > 0
        assert "+" in diff_text

    def test_diff_with_deletions(self):
        """Test diff with deleted lines."""
        from loom.tools.change_monitor import _compute_diff

        old = "Line 1\nLine 2\nLine 3"
        new = "Line 1"

        diff_text, changed_count = _compute_diff(old, new)

        assert changed_count > 0
        assert "-" in diff_text

    def test_change_classification_added(self):
        """Test change classification for added content."""
        from loom.tools.change_monitor import _classify_change

        old = "Short content"
        new = "Short content with much more text added here"

        change_type = _classify_change(old, new, 5)

        assert change_type == "content_added"

    def test_change_classification_removed(self):
        """Test change classification for removed content."""
        from loom.tools.change_monitor import _classify_change

        old = "Long content with lots of text here"
        new = "Short"

        change_type = _classify_change(old, new, 5)

        assert change_type == "content_removed"

    def test_change_classification_modified(self):
        """Test change classification for modified content (same size)."""
        from loom.tools.change_monitor import _classify_change

        old = "Content A is here"
        new = "Content B is here"

        change_type = _classify_change(old, new, 2)

        assert change_type == "content_modified"


class TestContentFetching:
    """Test content fetching and error handling."""

    def test_successful_fetch(self):
        """Test successful HTTP fetch."""
        from loom.tools.change_monitor import _fetch_content

        expected_content = "<html><body>Test content</body></html>"

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = expected_content
            mock_get.return_value = mock_response

            content = _fetch_content("https://example.com")

        assert content == expected_content

    def test_fetch_with_redirect(self):
        """Test that fetch follows redirects."""
        from loom.tools.change_monitor import _fetch_content

        expected_content = "<html><body>Redirected</body></html>"

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = expected_content
            mock_get.return_value = mock_response

            content = _fetch_content("https://example.com")

        # Verify follow_redirects was passed
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["follow_redirects"] is True
        assert content == expected_content

    def test_fetch_timeout(self):
        """Test timeout handling during fetch."""
        from loom.tools.change_monitor import _fetch_content

        with patch("httpx.get", side_effect=Exception("Timeout")):
            with pytest.raises(Exception):
                _fetch_content("https://example.com")

    def test_fetch_http_error(self):
        """Test HTTP error handling."""
        from loom.tools.change_monitor import _fetch_content

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("404 Not Found")
            mock_get.return_value = mock_response

            with pytest.raises(Exception):
                _fetch_content("https://example.com")
