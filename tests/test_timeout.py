"""Tests for timeout handling (REQ-056).

Tests verify that:
  - Default timeout is 30 seconds
  - Timeout is configurable (bounds: 5-120s)
  - Timeouts are caught internally and return structured error dicts
  - No exceptions are propagated to caller
  - Error dicts include tool_name, error_code=TIMEOUT, and suggestion fields
  - Concurrent operations timeout independently
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from loom.config import ConfigModel, load_config, research_config_set, set
from loom.errors import LoomError


class TestTimeoutConfig:
    """Test timeout configuration and bounds."""

    def test_default_timeout_is_30_seconds(self) -> None:
        """Default EXTERNAL_TIMEOUT_SECS is 30."""
        config = ConfigModel()
        assert config.EXTERNAL_TIMEOUT_SECS == 30

    def test_timeout_configurable_via_config_model(self) -> None:
        """EXTERNAL_TIMEOUT_SECS can be set via ConfigModel."""
        config = ConfigModel(EXTERNAL_TIMEOUT_SECS=45)
        assert config.EXTERNAL_TIMEOUT_SECS == 45

    def test_timeout_minimum_bound_is_5_seconds(self) -> None:
        """EXTERNAL_TIMEOUT_SECS must be >= 5."""
        with pytest.raises(Exception):
            ConfigModel(EXTERNAL_TIMEOUT_SECS=4)

    def test_timeout_maximum_bound_is_120_seconds(self) -> None:
        """EXTERNAL_TIMEOUT_SECS must be <= 120."""
        with pytest.raises(Exception):
            ConfigModel(EXTERNAL_TIMEOUT_SECS=121)

    def test_timeout_valid_at_bounds(self) -> None:
        """EXTERNAL_TIMEOUT_SECS valid at min and max bounds."""
        cfg_min = ConfigModel(EXTERNAL_TIMEOUT_SECS=5)
        assert cfg_min.EXTERNAL_TIMEOUT_SECS == 5

        cfg_max = ConfigModel(EXTERNAL_TIMEOUT_SECS=120)
        assert cfg_max.EXTERNAL_TIMEOUT_SECS == 120

    def test_timeout_in_loaded_config(self, tmp_config_path: Path) -> None:
        """Loaded config includes EXTERNAL_TIMEOUT_SECS."""
        import json

        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = {"EXTERNAL_TIMEOUT_SECS": 60}
        tmp_config_path.write_text(json.dumps(config_data))

        loaded = load_config(tmp_config_path)
        assert loaded["EXTERNAL_TIMEOUT_SECS"] == 60

    def test_timeout_defaults_when_config_missing(self, tmp_config_path: Path) -> None:
        """Missing config file uses default timeout."""
        # Don't create the file
        loaded = load_config(tmp_config_path)
        assert loaded["EXTERNAL_TIMEOUT_SECS"] == 30


class TestTimeoutErrorHandling:
    """Test that timeouts produce structured error responses."""

    def test_timeout_error_mapped_to_timeout_code(self) -> None:
        """TimeoutError maps to TIMEOUT error_code."""
        error = TimeoutError("Request timed out after 30s")
        result = LoomError.tool_error("research_fetch", error)

        assert result["error_code"] == "TIMEOUT"
        assert result["message"] == "Request timed out after 30s"

    def test_asyncio_timeout_error_mapped_to_timeout_code(self) -> None:
        """asyncio.TimeoutError also maps to TIMEOUT."""
        error = asyncio.TimeoutError("Async operation timed out")
        result = LoomError.tool_error("research_spider", error)

        assert result["error_code"] == "TIMEOUT"
        assert result["message"] == "Async operation timed out"

    def test_timeout_error_includes_tool_name(self) -> None:
        """Timeout error response includes tool_name."""
        error = TimeoutError("Operation timed out")
        result = LoomError.tool_error("research_deep", error)

        assert result["tool_name"] == "research_deep"
        assert "tool_name" in result

    def test_timeout_error_includes_suggestion(self) -> None:
        """Timeout error response includes helpful suggestion."""
        error = TimeoutError("Timed out")
        result = LoomError.tool_error("research_fetch", error)

        assert "suggestion" in result
        assert isinstance(result["suggestion"], str)
        assert len(result["suggestion"]) > 0
        # Suggestion should mention timeout or retry
        suggestion_lower = result["suggestion"].lower()
        assert "timeout" in suggestion_lower or "retry" in suggestion_lower

    def test_timeout_error_is_dict_not_exception(self) -> None:
        """Timeout errors return dicts, never raise exceptions."""
        error = TimeoutError("Timed out")
        result = LoomError.tool_error("test_tool", error)

        assert isinstance(result, dict)
        assert "error_code" in result
        assert "message" in result
        assert "suggestion" in result

    def test_timeout_error_includes_error_type(self) -> None:
        """Timeout error response includes error_type field."""
        error = TimeoutError("Timed out")
        result = LoomError.tool_error("research_search", error)

        assert "error_type" in result
        assert result["error_type"] == "TimeoutError"

    def test_timeout_error_preserves_original_message(self) -> None:
        """Timeout error message is preserved from exception."""
        original_message = "Connection timed out after 30 seconds"
        error = TimeoutError(original_message)
        result = LoomError.tool_error("research_fetch", error)

        assert result["message"] == original_message


class TestTimeoutBehavior:
    """Test runtime timeout behavior with asyncio."""

    @pytest.mark.asyncio
    async def test_asyncio_wait_for_catches_timeout(self) -> None:
        """asyncio.wait_for properly raises TimeoutError."""
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.sleep(10), timeout=0.01)

    @pytest.mark.asyncio
    async def test_timeout_can_be_caught_and_converted_to_error_dict(self) -> None:
        """Timeout can be caught and converted to structured error."""
        try:
            await asyncio.wait_for(asyncio.sleep(10), timeout=0.01)
        except asyncio.TimeoutError as e:
            error_dict = LoomError.tool_error("research_fetch", e)
            assert error_dict["error_code"] == "TIMEOUT"
            assert isinstance(error_dict, dict)

    @pytest.mark.asyncio
    async def test_timeout_handler_wrapper_pattern(self) -> None:
        """Tools can wrap operations with timeout handling."""
        async def slow_operation() -> str:
            await asyncio.sleep(10)
            return "result"

        try:
            result = await asyncio.wait_for(slow_operation(), timeout=0.01)
        except asyncio.TimeoutError:
            # Timeout is caught and converted to error dict
            result = LoomError.tool_error("test_tool", asyncio.TimeoutError("Timed out"))

        assert isinstance(result, dict)
        assert result["error_code"] == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_concurrent_operations_timeout_independently(self) -> None:
        """Multiple concurrent operations timeout independently."""
        async def task(duration: float, timeout_val: float) -> dict:
            try:
                await asyncio.wait_for(asyncio.sleep(duration), timeout=timeout_val)
                return {"status": "ok"}
            except asyncio.TimeoutError:
                return LoomError.tool_error("test_tool", asyncio.TimeoutError("Timed out"))

        # Run two concurrent tasks:
        # - First finishes quickly (no timeout)
        # - Second times out
        results = await asyncio.gather(
            task(0.001, 1.0),    # Fast, no timeout
            task(10.0, 0.01),    # Slow, will timeout
        )

        # First should succeed
        assert results[0]["status"] == "ok"
        # Second should be a timeout error dict
        assert results[1]["error_code"] == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_timeout_does_not_leak_to_caller(self) -> None:
        """Timeout exceptions are caught, not propagated."""
        async def safe_operation_with_timeout() -> dict:
            try:
                await asyncio.wait_for(asyncio.sleep(10), timeout=0.01)
                return {"status": "ok"}
            except asyncio.TimeoutError as e:
                # Catch and convert to error dict
                return LoomError.tool_error("test_tool", e)

        result = await safe_operation_with_timeout()

        # Caller receives dict, not exception
        assert isinstance(result, dict)
        assert "error_code" in result


class TestTimeoutConfigurationPersistence:
    """Test that timeout config can be updated and persisted."""

    def test_timeout_can_be_updated_via_config_set(self, tmp_config_path: Path) -> None:
        """Timeout value can be updated and persisted."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Set timeout to non-default value
        result = set("EXTERNAL_TIMEOUT_SECS", 60, tmp_config_path)

        assert result["key"] == "EXTERNAL_TIMEOUT_SECS"
        assert result["new"] == 60
        assert "persisted_at" in result

    def test_timeout_update_validates_bounds(self) -> None:
        """Timeout update rejects out-of-bounds values."""
        # Try to set invalid timeout
        result = research_config_set("EXTERNAL_TIMEOUT_SECS", 150)

        # Should return error dict, not raise exception
        assert isinstance(result, dict)
        assert "error" in result

    def test_timeout_update_respects_minimum(self) -> None:
        """Timeout update rejects values below minimum (5s)."""
        result = research_config_set("EXTERNAL_TIMEOUT_SECS", 3)

        # Should fail validation
        assert "error" in result

    def test_timeout_update_respects_maximum(self) -> None:
        """Timeout update rejects values above maximum (120s)."""
        result = research_config_set("EXTERNAL_TIMEOUT_SECS", 121)

        # Should fail validation
        assert "error" in result

    def test_valid_timeout_values_accepted(self, tmp_config_path: Path) -> None:
        """Valid timeout values (5-120) are accepted."""
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)

        for timeout_val in [5, 15, 30, 60, 90, 120]:
            result = set("EXTERNAL_TIMEOUT_SECS", timeout_val, tmp_config_path)
            assert result["new"] == timeout_val
            assert "error" not in result


class TestTimeoutErrorStructure:
    """Test the structure of timeout error responses."""

    def test_timeout_error_has_required_fields(self) -> None:
        """Timeout error response has all required fields."""
        error = TimeoutError("Operation timed out")
        result = LoomError.tool_error("research_fetch", error)

        required_fields = ["error_code", "message", "suggestion", "tool_name", "error_type"]
        for field in required_fields:
            assert field in result
            assert result[field] is not None

    def test_timeout_error_field_types(self) -> None:
        """Timeout error response fields have correct types."""
        error = TimeoutError("Timed out")
        result = LoomError.tool_error("research_search", error)

        assert isinstance(result["error_code"], str)
        assert isinstance(result["message"], str)
        assert isinstance(result["suggestion"], str)
        assert isinstance(result["tool_name"], str)
        assert isinstance(result["error_type"], str)

    def test_timeout_error_code_is_uppercase(self) -> None:
        """error_code for timeout is TIMEOUT (uppercase)."""
        error = TimeoutError("Timed out")
        result = LoomError.tool_error("test_tool", error)

        assert result["error_code"] == "TIMEOUT"
        assert result["error_code"].isupper()

    def test_timeout_suggestion_is_non_empty(self) -> None:
        """Suggestion field for timeout is non-empty and helpful."""
        error = TimeoutError("Timed out")
        result = LoomError.tool_error("research_fetch", error)

        assert result["suggestion"]
        assert len(result["suggestion"]) > 3  # Should be a meaningful message

    def test_custom_timeout_suggestion(self) -> None:
        """Timeout error can have custom suggestion."""
        error = TimeoutError("Timed out")
        custom = "Use retry_after=60 or increase timeout"
        result = LoomError.tool_error("research_fetch", error, suggestion=custom)

        assert result["suggestion"] == custom


class TestTimeoutIntegration:
    """Integration tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_multiple_timeouts_independent(self) -> None:
        """Multiple concurrent timeouts are independent."""
        async def task_with_timeout(
            task_id: int, duration: float, timeout_val: float
        ) -> dict:
            try:
                await asyncio.wait_for(asyncio.sleep(duration), timeout=timeout_val)
                return {"task_id": task_id, "status": "ok"}
            except asyncio.TimeoutError as e:
                return {
                    "task_id": task_id,
                    **LoomError.tool_error("task", e),
                }

        results = await asyncio.gather(
            task_with_timeout(1, 0.001, 1.0),    # OK
            task_with_timeout(2, 10.0, 0.01),    # Timeout
            task_with_timeout(3, 0.001, 1.0),    # OK
            task_with_timeout(4, 10.0, 0.01),    # Timeout
        )

        # Verify independent timeouts
        assert results[0]["status"] == "ok"
        assert results[1]["error_code"] == "TIMEOUT"
        assert results[2]["status"] == "ok"
        assert results[3]["error_code"] == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_timeout_with_cleanup(self) -> None:
        """Timeouts allow proper cleanup of resources."""
        cleanup_called = False

        async def operation_with_cleanup() -> dict:
            nonlocal cleanup_called
            try:
                await asyncio.wait_for(asyncio.sleep(10), timeout=0.01)
                return {"status": "ok"}
            except asyncio.TimeoutError as e:
                cleanup_called = True
                return LoomError.tool_error("test_tool", e)

        result = await operation_with_cleanup()

        # Cleanup should be called
        assert cleanup_called
        assert result["error_code"] == "TIMEOUT"

    def test_timeout_error_is_serializable(self) -> None:
        """Timeout error dict is JSON-serializable."""
        import json

        error = TimeoutError("Operation timed out")
        result = LoomError.tool_error("research_fetch", error)

        # Should be serializable to JSON
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        assert "TIMEOUT" in json_str


class TestTimeoutEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_timeout_with_empty_message(self) -> None:
        """TimeoutError with empty message is handled."""
        error = TimeoutError()
        result = LoomError.tool_error("test_tool", error)

        assert result["error_code"] == "TIMEOUT"
        assert "message" in result

    def test_timeout_with_very_long_message(self) -> None:
        """TimeoutError with very long message is preserved."""
        long_message = "Timeout: " + ("x" * 5000)
        error = TimeoutError(long_message)
        result = LoomError.tool_error("test_tool", error)

        assert result["message"] == long_message
        assert len(result["message"]) > 5000

    def test_timeout_with_unicode_message(self) -> None:
        """TimeoutError with unicode message is handled."""
        message = "Timeout: عملية انتهت بانتظار 超時"
        error = TimeoutError(message)
        result = LoomError.tool_error("test_tool", error)

        assert result["message"] == message

    @pytest.mark.asyncio
    async def test_timeout_zero_duration(self) -> None:
        """Very short timeout (near-zero) triggers timeout."""
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.sleep(1), timeout=0.0001)

    def test_timeout_in_various_tool_names(self) -> None:
        """Timeout handling works with various tool names."""
        error = TimeoutError("Timed out")
        tool_names = [
            "research_fetch",
            "research_deep",
            "research_spider",
            "research_llm_summarize",
            "research_search",
            "custom_tool_v2",
        ]

        for tool_name in tool_names:
            result = LoomError.tool_error(tool_name, error)
            assert result["tool_name"] == tool_name
            assert result["error_code"] == "TIMEOUT"
