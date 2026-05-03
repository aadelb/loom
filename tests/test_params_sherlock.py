"""Unit tests for Sherlock parameter models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loom.params import SherlockBatchParams, SherlockLookupParams



pytestmark = pytest.mark.asyncio
class TestSherlockLookupParams:
    """Test SherlockLookupParams validation."""

    async def test_valid_minimal(self) -> None:
        """Minimal valid params."""
        params = SherlockLookupParams(username="john_doe")
        assert params.username == "john_doe"
        assert params.platforms is None
        assert params.timeout == 30

    async def test_valid_full(self) -> None:
        """Full valid params."""
        params = SherlockLookupParams(
            username="test_user",
            platforms=["twitter", "github"],
            timeout=60,
        )
        assert params.username == "test_user"
        assert params.platforms == ["twitter", "github"]
        assert params.timeout == 60

    async def test_username_stripped(self) -> None:
        """Username whitespace is stripped."""
        params = SherlockLookupParams(username="  john_doe  ")
        assert params.username == "john_doe"

    async def test_invalid_username_empty(self) -> None:
        """Empty username fails."""
        with pytest.raises(ValidationError) as exc_info:
            SherlockLookupParams(username="")
        assert "username must be" in str(exc_info.value)

    async def test_invalid_username_too_long(self) -> None:
        """Username exceeding 255 chars fails."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(username="a" * 256)

    async def test_invalid_username_disallowed_chars(self) -> None:
        """Username with disallowed chars fails."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(username="user@invalid")

        with pytest.raises(ValidationError):
            SherlockLookupParams(username="user name")

    async def test_invalid_platforms_not_list(self) -> None:
        """Platforms must be a list."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(username="user", platforms="twitter")  # type: ignore

    async def test_invalid_platforms_too_many(self) -> None:
        """Platforms list cannot exceed 50 items."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(
                username="user",
                platforms=[f"platform{i}" for i in range(51)],
            )

    async def test_invalid_platform_too_long(self) -> None:
        """Platform name cannot exceed 100 chars."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(
                username="user",
                platforms=["a" * 101],
            )

    async def test_invalid_platform_disallowed_chars(self) -> None:
        """Platform with disallowed chars fails."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(
                username="user",
                platforms=["twitter.com"],
            )

    async def test_invalid_timeout_too_low(self) -> None:
        """Timeout must be at least 1."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(username="user", timeout=0)

    async def test_invalid_timeout_too_high(self) -> None:
        """Timeout cannot exceed 300."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(username="user", timeout=301)

    async def test_extra_fields_forbidden(self) -> None:
        """Extra fields are forbidden."""
        with pytest.raises(ValidationError):
            SherlockLookupParams(  # type: ignore
                username="user",
                extra_field="value",
            )

    async def test_valid_special_chars(self) -> None:
        """Username with allowed special chars."""
        params = SherlockLookupParams(username="john_doe-123.test+tag")
        assert params.username == "john_doe-123.test+tag"


class TestSherlockBatchParams:
    """Test SherlockBatchParams validation."""

    async def test_valid_minimal(self) -> None:
        """Minimal valid params."""
        params = SherlockBatchParams(usernames=["user1", "user2"])
        assert params.usernames == ["user1", "user2"]
        assert params.platforms is None
        assert params.timeout == 30

    async def test_valid_full(self) -> None:
        """Full valid params."""
        params = SherlockBatchParams(
            usernames=["user1", "user2", "user3"],
            platforms=["twitter", "instagram"],
            timeout=90,
        )
        assert params.usernames == ["user1", "user2", "user3"]
        assert params.platforms == ["twitter", "instagram"]
        assert params.timeout == 90

    async def test_usernames_stripped(self) -> None:
        """Usernames whitespace is stripped."""
        params = SherlockBatchParams(usernames=["  user1  ", "user2"])
        assert params.usernames == ["user1", "user2"]

    async def test_invalid_usernames_not_list(self) -> None:
        """Usernames must be a list."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(usernames="user1")  # type: ignore

    async def test_invalid_usernames_empty_list(self) -> None:
        """Usernames list cannot be empty."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(usernames=[])

    async def test_invalid_usernames_too_many(self) -> None:
        """Usernames list cannot exceed 100 items."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(usernames=[f"user{i}" for i in range(101)])

    async def test_invalid_username_in_list(self) -> None:
        """Invalid username in list fails."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(usernames=["user1", "invalid@user"])

    async def test_invalid_platforms_not_list(self) -> None:
        """Platforms must be a list."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(
                usernames=["user1"],
                platforms="twitter",  # type: ignore
            )

    async def test_invalid_platforms_too_many(self) -> None:
        """Platforms list cannot exceed 50 items."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(
                usernames=["user1"],
                platforms=[f"platform{i}" for i in range(51)],
            )

    async def test_invalid_timeout_too_low(self) -> None:
        """Timeout must be at least 1."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(usernames=["user1"], timeout=0)

    async def test_invalid_timeout_too_high(self) -> None:
        """Timeout cannot exceed 300."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(usernames=["user1"], timeout=301)

    async def test_extra_fields_forbidden(self) -> None:
        """Extra fields are forbidden."""
        with pytest.raises(ValidationError):
            SherlockBatchParams(  # type: ignore
                usernames=["user1"],
                extra_field="value",
            )

    async def test_valid_platform_list(self) -> None:
        """Valid platform list."""
        params = SherlockBatchParams(
            usernames=["user1"],
            platforms=["twitter", "github", "instagram"],
        )
        assert params.platforms == ["twitter", "github", "instagram"]

    async def test_max_valid_usernames(self) -> None:
        """100 usernames exactly is valid."""
        usernames = [f"user{i}" for i in range(100)]
        params = SherlockBatchParams(usernames=usernames)
        assert len(params.usernames) == 100

    async def test_max_valid_platforms(self) -> None:
        """50 platforms exactly is valid."""
        platforms = [f"platform{i}" for i in range(50)]
        params = SherlockBatchParams(
            usernames=["user1"],
            platforms=platforms,
        )
        assert len(params.platforms) == 50
