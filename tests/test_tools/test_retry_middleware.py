"""Tests for retry_middleware tools."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.tools import retry_middleware


class TestRetryExecute:
    """Test research_retry_execute tool."""

    @pytest.mark.asyncio
    async def test_successful_execution_first_try(self):
        """Test successful tool execution on first attempt."""
        # Mock the imported tool
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_func = AsyncMock(return_value={"data": "success"})
            mock_module.test_tool = mock_func
            mock_import.return_value = mock_module

            result = await retry_middleware.research_retry_execute(
                tool_name="test_tool",
                params={"url": "http://example.com"},
            )

            assert result["success"] is True
            assert result["result"]["data"] == "success"
            assert result["attempts"] == 1
            assert result["retries_used"] == 0
            assert result["errors"] == []
            assert result["total_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_successful_execution_after_retries(self):
        """Test successful execution after initial failures."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()

            # Fail twice, succeed on third attempt
            async def side_effect(**kwargs):
                side_effect.call_count += 1
                if side_effect.call_count < 3:
                    raise ConnectionError("Connection failed")
                return {"data": "success"}

            side_effect.call_count = 0
            mock_func = AsyncMock(side_effect=side_effect)
            mock_module.test_tool = mock_func
            mock_import.return_value = mock_module

            result = await retry_middleware.research_retry_execute(
                tool_name="test_tool",
                params={"url": "http://example.com"},
                max_retries=3,
                backoff_base=0.01,  # Use small backoff for tests
                retry_on=["ConnectionError"],
            )

            assert result["success"] is True
            assert result["result"]["data"] == "success"
            assert result["attempts"] == 3
            assert result["retries_used"] == 2
            assert len(result["errors"]) == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """Test behavior when max retries are exhausted."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_func = AsyncMock(side_effect=TimeoutError("Timeout"))
            mock_module.test_tool = mock_func
            mock_import.return_value = mock_module

            result = await retry_middleware.research_retry_execute(
                tool_name="test_tool",
                params={},
                max_retries=2,
                backoff_base=0.01,
                retry_on=["TimeoutError"],
            )

            assert result["success"] is False
            assert result["result"] is None
            assert result["attempts"] == 3  # Initial + 2 retries
            assert result["retries_used"] == 2
            assert len(result["errors"]) == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """Test that non-retryable errors fail immediately."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_func = AsyncMock(side_effect=ValueError("Invalid input"))
            mock_module.test_tool = mock_func
            mock_import.return_value = mock_module

            result = await retry_middleware.research_retry_execute(
                tool_name="test_tool",
                params={},
                max_retries=3,
                retry_on=["TimeoutError"],  # ValueError not in this list
            )

            assert result["success"] is False
            assert result["attempts"] == 1  # No retries for ValueError
            assert result["retries_used"] == 0
            assert result["errors"][0]["error_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_sync_function_execution(self):
        """Test execution of synchronous tool functions."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()

            def sync_func(**kwargs):
                return {"data": "sync_success"}

            mock_module.sync_tool = sync_func
            mock_import.return_value = mock_module

            result = await retry_middleware.research_retry_execute(
                tool_name="sync_tool",
                params={"test": "value"},
            )

            assert result["success"] is True
            assert result["result"]["data"] == "sync_success"

    @pytest.mark.asyncio
    async def test_rate_limit_error_retry(self):
        """Test retry on RateLimitError."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()

            call_count = 0

            async def side_effect(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("Rate limited")
                return {"data": "success"}

            mock_func = AsyncMock(side_effect=side_effect)
            mock_module.test_tool = mock_func
            mock_import.return_value = mock_module

            result = await retry_middleware.research_retry_execute(
                tool_name="test_tool",
                params={},
                max_retries=3,
                backoff_base=0.01,
                retry_on=["ConnectionError"],
            )

            assert result["success"] is True
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_error_retry(self):
        """Test retry on TimeoutError."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()

            def raise_timeout(**kwargs):
                raise TimeoutError("Timeout")

            mock_func = AsyncMock(side_effect=raise_timeout)
            mock_module.test_tool = mock_func
            mock_import.return_value = mock_module

            result = await retry_middleware.research_retry_execute(
                tool_name="test_tool",
                params={},
                max_retries=1,
                backoff_base=0.01,
                retry_on=["TimeoutError"],
            )

            assert all(
                err["error_type"] == "TimeoutError" for err in result["errors"]
            )
            assert all(
                isinstance(err["message"], str) for err in result["errors"]
            )
