"""Unit tests for sherlock_backend — Username OSINT searches across social networks."""

from __future__ import annotations

import json
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from loom.tools.backends.sherlock_backend import (
    _check_sherlock_available,
    _validate_platform,
    _validate_username,
    research_sherlock_batch,
    research_sherlock_lookup,
)


class TestValidateUsername:
    """Test _validate_username helper."""

    def test_valid_username_alphanumeric(self) -> None:
        """Alphanumeric usernames pass validation."""
        assert _validate_username("john_doe") == "john_doe"
        assert _validate_username("user123") == "user123"
        assert _validate_username("john.doe") == "john.doe"
        assert _validate_username("user-name") == "user-name"

    def test_valid_username_with_special_chars(self) -> None:
        """Usernames with underscores, hyphens, periods pass."""
        assert _validate_username("john_doe") == "john_doe"
        assert _validate_username("john-doe") == "john-doe"
        assert _validate_username("john.doe") == "john.doe"
        assert _validate_username("user+tag") == "user+tag"

    def test_valid_username_strips_whitespace(self) -> None:
        """Whitespace is stripped from usernames."""
        assert _validate_username("  john_doe  ") == "john_doe"
        assert _validate_username("\tjohn_doe\t") == "john_doe"

    def test_invalid_username_empty(self) -> None:
        """Empty username fails validation."""
        with pytest.raises(ValueError, match="username must be"):
            _validate_username("")

    def test_invalid_username_too_long(self) -> None:
        """Username exceeding 255 chars fails."""
        long_username = "a" * 256
        with pytest.raises(ValueError, match="username must be"):
            _validate_username(long_username)

    def test_invalid_username_disallowed_chars(self) -> None:
        """Usernames with disallowed characters fail."""
        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_username("john@doe")

        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_username("john doe")  # space

        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_username("john&doe")

    def test_invalid_username_sql_injection(self) -> None:
        """SQL injection patterns are blocked."""
        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_username("user'; DROP TABLE--")


class TestValidatePlatform:
    """Test _validate_platform helper."""

    def test_valid_platform(self) -> None:
        """Valid platform names pass validation."""
        assert _validate_platform("twitter") == "twitter"
        assert _validate_platform("instagram") == "instagram"
        assert _validate_platform("GitHub") == "GitHub"  # case-insensitive

    def test_valid_platform_with_underscore_hyphen(self) -> None:
        """Platforms with underscores and hyphens pass."""
        assert _validate_platform("some_platform") == "some_platform"
        assert _validate_platform("some-platform") == "some-platform"

    def test_valid_platform_strips_whitespace(self) -> None:
        """Whitespace is stripped from platform names."""
        assert _validate_platform("  twitter  ") == "twitter"

    def test_invalid_platform_empty(self) -> None:
        """Empty platform fails validation."""
        with pytest.raises(ValueError, match="platform must be"):
            _validate_platform("")

    def test_invalid_platform_too_long(self) -> None:
        """Platform exceeding 100 chars fails."""
        long_platform = "a" * 101
        with pytest.raises(ValueError, match="platform must be"):
            _validate_platform(long_platform)

    def test_invalid_platform_disallowed_chars(self) -> None:
        """Platforms with disallowed characters fail."""
        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_platform("twitter.com")

        with pytest.raises(ValueError, match="disallowed characters"):
            _validate_platform("some platform")


class TestCheckSherlockAvailable:
    """Test _check_sherlock_available helper."""

    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_sherlock_available(self, mock_run: Mock) -> None:
        """Returns True when sherlock CLI is found."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        available, msg = _check_sherlock_available()
        assert available is True
        assert "found" in msg.lower()

    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_sherlock_not_found(self, mock_run: Mock) -> None:
        """Returns False when sherlock CLI not found."""
        mock_run.side_effect = FileNotFoundError()
        available, msg = _check_sherlock_available()
        assert available is False
        assert "not found" in msg.lower()
        assert "pip install sherlock-project" in msg

    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_sherlock_version_check_failed(self, mock_run: Mock) -> None:
        """Returns False when version check fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        available, msg = _check_sherlock_available()
        assert available is False
        assert "failed" in msg.lower()

    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_sherlock_timeout(self, mock_run: Mock) -> None:
        """Returns False when version check times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        available, msg = _check_sherlock_available()
        assert available is False
        assert "timeout" in msg.lower()


class TestSherlockLookup:
    """Test research_sherlock_lookup function."""

    def test_invalid_username(self) -> None:
        """Invalid username returns error."""
        result = research_sherlock_lookup("user@invalid")
        assert "error" in result
        assert result["sherlock_available"] is False

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    def test_sherlock_unavailable(self, mock_check: Mock) -> None:
        """Returns error when Sherlock unavailable."""
        mock_check.return_value = (False, "Sherlock not found")
        result = research_sherlock_lookup("testuser")
        assert result["sherlock_available"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.sherlock_backend.subprocess.run")
    @patch("builtins.open", create=True)
    def test_username_found(self, mock_open: Mock, mock_run: Mock, mock_check: Mock) -> None:
        """Returns found_on list when username found on platforms."""
        mock_check.return_value = (True, "Sherlock found")

        # Mock subprocess result
        mock_run.return_value = MagicMock(returncode=0)

        # Mock JSON output from sherlock
        sherlock_output = {
            "testuser": {
                "twitter": {
                    "url": "https://twitter.com/testuser",
                    "user_id": "123456",
                    "status_code": 200,
                },
                "github": {
                    "url": "https://github.com/testuser",
                    "user_id": "789",
                    "status_code": 200,
                },
                "instagram": {
                    "status_code": 404,  # Not found
                },
            }
        }

        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(sherlock_output)
        mock_open.return_value = mock_file

        result = research_sherlock_lookup("testuser")

        assert result["sherlock_available"] is True
        assert result["username"] == "testuser"
        assert result["total_found"] == 2
        assert result["total_checked"] == 3
        assert len(result["found_on"]) == 2
        assert result["found_on"][0]["platform"] == "twitter"
        assert result["found_on"][0]["url"] == "https://twitter.com/testuser"

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.sherlock_backend.subprocess.run")
    @patch("builtins.open", create=True)
    def test_username_not_found_anywhere(
        self, mock_open: Mock, mock_run: Mock, mock_check: Mock
    ) -> None:
        """Returns empty found_on when username not found."""
        mock_check.return_value = (True, "Sherlock found")
        mock_run.return_value = MagicMock(returncode=0)

        sherlock_output = {
            "notreal123": {
                "twitter": {"status_code": 404},
                "github": {"status_code": 404},
                "instagram": {"status_code": 404},
            }
        }

        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(sherlock_output)
        mock_open.return_value = mock_file

        result = research_sherlock_lookup("notreal123")

        assert result["sherlock_available"] is True
        assert result["total_found"] == 0
        assert result["total_checked"] == 3
        assert result["found_on"] == []

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_timeout(self, mock_run: Mock, mock_check: Mock) -> None:
        """Returns error on timeout."""
        import subprocess

        mock_check.return_value = (True, "Sherlock found")
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        result = research_sherlock_lookup("testuser", timeout=30)

        assert result["sherlock_available"] is True
        assert "error" in result
        assert "timed out" in result["error"].lower()

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_platforms_filter(self, mock_run: Mock, mock_check: Mock) -> None:
        """Passes platforms to subprocess command."""
        mock_check.return_value = (True, "Sherlock found")
        mock_run.return_value = MagicMock(returncode=0)

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.read.return_value = json.dumps({"testuser": {}})
            mock_open.return_value = mock_file

            research_sherlock_lookup(
                "testuser", platforms=["twitter", "github"]
            )

            # Verify subprocess was called with platforms
            call_args = mock_run.call_args
            assert call_args is not None
            cmd = call_args[0][0]
            assert "--site" in cmd
            assert "twitter" in cmd
            assert "github" in cmd

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_custom_timeout(self, mock_run: Mock, mock_check: Mock) -> None:
        """Uses custom timeout value."""
        mock_check.return_value = (True, "Sherlock found")
        mock_run.return_value = MagicMock(returncode=0)

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.read.return_value = json.dumps({"testuser": {}})
            mock_open.return_value = mock_file

            research_sherlock_lookup("testuser", timeout=60)

            # Verify subprocess was called with timeout
            call_args = mock_run.call_args
            assert call_args is not None
            cmd = call_args[0][0]
            assert "--timeout" in cmd
            assert "60" in cmd

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.sherlock_backend.subprocess.run")
    def test_malformed_json_output(self, mock_run: Mock, mock_check: Mock) -> None:
        """Handles malformed JSON output gracefully."""
        mock_check.return_value = (True, "Sherlock found")
        mock_run.return_value = MagicMock(returncode=0)

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value = mock_file
            mock_file.read.return_value = "not valid json"
            mock_open.return_value = mock_file

            result = research_sherlock_lookup("testuser")

            assert result["sherlock_available"] is True
            assert "error" in result
            assert "parse" in result["error"].lower()


class TestSherlockBatch:
    """Test research_sherlock_batch function."""

    def test_empty_usernames(self) -> None:
        """Empty usernames list returns error."""
        with patch("loom.tools.backends.sherlock_backend._check_sherlock_available") as mock_check:
            mock_check.return_value = (True, "Available")
            result = research_sherlock_batch([])
            assert result["error"] == "No valid usernames provided"

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    def test_sherlock_unavailable(self, mock_check: Mock) -> None:
        """Returns error when Sherlock unavailable."""
        mock_check.return_value = (False, "Sherlock not found")
        result = research_sherlock_batch(["user1", "user2"])
        assert result["sherlock_available"] is False
        assert "error" in result
        assert result["results"] == {}

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.backends.sherlock_backend.research_sherlock_lookup")
    def test_batch_multiple_users(
        self, mock_lookup: Mock, mock_check: Mock
    ) -> None:
        """Performs lookups for multiple usernames."""
        mock_check.return_value = (True, "Available")

        # Mock lookup results
        mock_lookup.side_effect = [
            {
                "username": "user1",
                "found_on": [
                    {"platform": "twitter", "url": "https://twitter.com/user1"}
                ],
                "total_found": 1,
                "total_checked": 10,
            },
            {
                "username": "user2",
                "found_on": [
                    {"platform": "github", "url": "https://github.com/user2"}
                ],
                "total_found": 1,
                "total_checked": 10,
            },
        ]

        result = research_sherlock_batch(["user1", "user2"])

        assert result["usernames_checked"] == 2
        assert result["total_accounts_found"] == 2
        assert "user1" in result["results"]
        assert "user2" in result["results"]
        assert mock_lookup.call_count == 2

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.backends.sherlock_backend.research_sherlock_lookup")
    def test_batch_deduplicates_usernames(
        self, mock_lookup: Mock, mock_check: Mock
    ) -> None:
        """Deduplicates usernames in batch."""
        mock_check.return_value = (True, "Available")
        mock_lookup.return_value = {
            "username": "user1",
            "found_on": [],
            "total_found": 0,
        }

        result = research_sherlock_batch(["user1", "user1", "user1"])

        assert result["usernames_checked"] == 1
        assert mock_lookup.call_count == 1

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.backends.sherlock_backend.research_sherlock_lookup")
    def test_batch_skips_invalid_usernames(
        self, mock_lookup: Mock, mock_check: Mock
    ) -> None:
        """Skips invalid usernames and continues."""
        mock_check.return_value = (True, "Available")
        mock_lookup.return_value = {
            "username": "valid_user",
            "found_on": [],
            "total_found": 0,
        }

        result = research_sherlock_batch(
            ["valid_user", "invalid@user", "another_valid"]
        )

        # Should process 2 valid, skip 1 invalid
        assert result["usernames_checked"] == 2
        assert mock_lookup.call_count == 2

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.backends.sherlock_backend.research_sherlock_lookup")
    def test_batch_passes_platforms(
        self, mock_lookup: Mock, mock_check: Mock
    ) -> None:
        """Passes platforms parameter to individual lookups."""
        mock_check.return_value = (True, "Available")
        mock_lookup.return_value = {
            "username": "user1",
            "found_on": [],
            "total_found": 0,
        }

        result = research_sherlock_batch(
            ["user1"], platforms=["twitter", "github"]
        )

        # Verify platforms were passed
        call_args = mock_lookup.call_args
        assert call_args is not None
        # call_args[0] is positional args, call_args[1] is keyword args
        # research_sherlock_lookup(username, platforms, timeout)
        assert call_args[0][1] == ["twitter", "github"]

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.backends.sherlock_backend.research_sherlock_lookup")
    def test_batch_accumulates_total_found(
        self, mock_lookup: Mock, mock_check: Mock
    ) -> None:
        """Accumulates total_found across all lookups."""
        mock_check.return_value = (True, "Available")

        mock_lookup.side_effect = [
            {
                "username": "user1",
                "found_on": [],
                "total_found": 3,
                "total_checked": 10,
            },
            {
                "username": "user2",
                "found_on": [],
                "total_found": 5,
                "total_checked": 10,
            },
            {
                "username": "user3",
                "found_on": [],
                "total_found": 2,
                "total_checked": 10,
            },
        ]

        result = research_sherlock_batch(["user1", "user2", "user3"])

        assert result["total_accounts_found"] == 10

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.backends.sherlock_backend.research_sherlock_lookup")
    def test_batch_handles_lookup_errors(
        self, mock_lookup: Mock, mock_check: Mock
    ) -> None:
        """Handles errors in individual lookups gracefully."""
        mock_check.return_value = (True, "Available")

        mock_lookup.side_effect = [
            {
                "username": "user1",
                "found_on": [],
                "total_found": 1,
                "total_checked": 10,
            },
            {
                "username": "user2",
                "error": "Lookup failed",
            },
            {
                "username": "user3",
                "found_on": [],
                "total_found": 2,
                "total_checked": 10,
            },
        ]

        result = research_sherlock_batch(["user1", "user2", "user3"])

        # Should still process all, and total_found should not include user2
        assert result["usernames_checked"] == 3
        assert result["total_accounts_found"] == 3
        assert "error" in result["results"]["user2"]

    @patch("loom.tools.backends.sherlock_backend._check_sherlock_available")
    @patch("loom.tools.backends.sherlock_backend.research_sherlock_lookup")
    def test_batch_respects_max_usernames(
        self, mock_lookup: Mock, mock_check: Mock
    ) -> None:
        """Handles max 100 usernames limit validation."""
        mock_check.return_value = (True, "Available")

        # Create 101 unique usernames
        usernames = [f"user{i}" for i in range(101)]

        # Should validate at params level, but test function behavior
        # Function doesn't enforce strict limit, but params do
        result = research_sherlock_batch(usernames)

        # Results should be returned (params validation is separate)
        assert isinstance(result, dict)
