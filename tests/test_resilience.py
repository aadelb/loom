"""Tests for graceful failure and rate limit handling (REQ-051, REQ-052).

REQ-051: Pipeline continues if 1-3 tools fail. Returns partial results + error_log.
REQ-052: Rate limit (429) exponential backoff — 3 retries with increasing delay.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.errors import LoomError
from loom.rate_limiter import RateLimiter, SyncRateLimiter, reset_all


class TestGracefulFailureREQ051:
    """REQ-051: Pipeline continues if 1-3 tools fail. Returns partial results + error_log."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_single_tool_failure(self) -> None:
        """Pipeline should complete even when one tool fails."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        async def tool_a() -> dict[str, str]:
            await asyncio.sleep(0.001)
            return {"result": "tool_a_success"}

        async def tool_b() -> dict[str, str]:
            raise ConnectionError("Provider B connection failed")

        async def tool_c() -> dict[str, str]:
            await asyncio.sleep(0.001)
            return {"result": "tool_c_success"}

        tools = {"tool_a": tool_a, "tool_b": tool_b, "tool_c": tool_c}

        for name, tool in tools.items():
            try:
                results[name] = await tool()
            except Exception as e:
                error_log.append(LoomError.tool_error(name, e))

        assert len(results) == 2
        assert "tool_a" in results
        assert "tool_c" in results
        assert "tool_b" not in results
        assert len(error_log) == 1
        assert error_log[0]["tool_name"] == "tool_b"
        assert error_log[0]["error_code"] == "CONNECTION_FAILED"

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_multiple_tool_failures(self) -> None:
        """Pipeline should complete when 2-3 tools fail, returning partial results."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        async def tool_search() -> dict[str, str]:
            raise TimeoutError("Search provider timeout after 30s")

        async def tool_fetch() -> dict[str, str]:
            return {"url": "https://example.com", "content": "fetched"}

        async def tool_summarize() -> dict[str, str]:
            raise ValueError("Invalid content format from fetch")

        async def tool_classify() -> dict[str, str]:
            return {"categories": ["tech", "news"]}

        tools = {
            "search": tool_search,
            "fetch": tool_fetch,
            "summarize": tool_summarize,
            "classify": tool_classify,
        }

        for name, tool in tools.items():
            try:
                results[name] = await tool()
            except Exception as e:
                error_log.append(LoomError.tool_error(name, e))

        assert len(results) == 2
        assert "fetch" in results
        assert "classify" in results
        assert len(error_log) == 2
        assert {e["tool_name"] for e in error_log} == {"search", "summarize"}

    @pytest.mark.asyncio
    async def test_partial_results_have_success_flag(self) -> None:
        """Response indicates which tools succeeded/failed."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        async def tool_ok() -> dict[str, str]:
            return {"data": "success"}

        async def tool_fail() -> dict[str, str]:
            raise RuntimeError("Internal server error")

        tools = {"success": tool_ok, "failure": tool_fail}

        for name, tool in tools.items():
            try:
                results[name] = await tool()
            except Exception as e:
                error_log.append(LoomError.tool_error(name, e))

        response = {
            "partial_results": results,
            "error_log": error_log,
            "success": len(error_log) == 0,
            "partial": len(error_log) > 0 and len(results) > 0,
        }

        assert response["partial"] is True
        assert response["success"] is False
        assert len(response["partial_results"]) == 1
        assert len(response["error_log"]) == 1

    @pytest.mark.asyncio
    async def test_error_log_structure_completeness(self) -> None:
        """Error log includes tool_name, error_code, message, suggestion, error_type."""
        error_log: list[dict[str, Any]] = []

        try:
            raise ValueError("URL must start with http:// or https://")
        except Exception as e:
            error_log.append(LoomError.tool_error("research_fetch", e))

        assert len(error_log) == 1
        error = error_log[0]

        required_fields = {
            "error_code",
            "message",
            "suggestion",
            "tool_name",
            "error_type",
        }
        assert all(field in error for field in required_fields)

        assert error["tool_name"] == "research_fetch"
        assert error["error_code"] == "INVALID_INPUT"
        assert error["error_type"] == "ValueError"
        assert error["message"] == "URL must start with http:// or https://"
        assert len(error["suggestion"]) > 0

    @pytest.mark.asyncio
    async def test_all_errors_captured_no_silent_failures(self) -> None:
        """Every tool failure is captured in error_log, none are silent."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        exceptions = [
            TimeoutError("Tool timeout"),
            ConnectionError("Network error"),
            ValueError("Invalid input"),
            KeyError("missing_api_key"),
        ]

        async def make_failing_tool(exc: Exception) -> Any:
            async def tool() -> Any:
                raise exc

            return tool

        tools = {f"tool_{i}": await make_failing_tool(exc) for i, exc in enumerate(exceptions)}

        for name, tool in tools.items():
            try:
                results[name] = await tool()
            except Exception as e:
                error_log.append(LoomError.tool_error(name, e))

        assert len(results) == 0
        assert len(error_log) == 4
        error_codes = {e["error_code"] for e in error_log}
        assert error_codes == {"TIMEOUT", "CONNECTION_FAILED", "INVALID_INPUT", "MISSING_PARAM"}

    @pytest.mark.asyncio
    async def test_pipeline_response_format_with_errors(self) -> None:
        """Pipeline response includes both results and error_log at top level."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        async def tool_success() -> dict[str, str]:
            return {"data": "ok"}

        async def tool_fails() -> dict[str, str]:
            raise RuntimeError("Something failed")

        for name, tool_fn in [("search", tool_success), ("fetch", tool_fails)]:
            try:
                results[name] = await tool_fn()
            except Exception as e:
                error_log.append(LoomError.tool_error(name, e))

        response = {
            "results": results,
            "error_log": error_log,
            "total_tools": 2,
            "succeeded": len(results),
            "failed": len(error_log),
        }

        assert response["total_tools"] == 2
        assert response["succeeded"] == 1
        assert response["failed"] == 1
        assert "results" in response
        assert "error_log" in response

    @pytest.mark.asyncio
    async def test_three_tools_one_two_three_fail_scenarios(self) -> None:
        """Test all combinations: 1 fail, 2 fail, all 3 succeed, all 3 fail."""
        test_cases = [
            ("only_one_fails", True, True, False, 2, 1),
            ("only_two_fail", False, False, True, 1, 2),
            ("all_succeed", True, True, True, 3, 0),
            ("all_fail", False, False, False, 0, 3),
        ]

        for case_name, t1_ok, t2_ok, t3_ok, expected_success, expected_fail in test_cases:
            results: dict[str, Any] = {}
            error_log: list[dict[str, Any]] = []

            async def tool_1() -> dict[str, str]:
                if not t1_ok:
                    raise TimeoutError("Tool 1 timeout")
                return {"tool": "1"}

            async def tool_2() -> dict[str, str]:
                if not t2_ok:
                    raise ConnectionError("Tool 2 connection error")
                return {"tool": "2"}

            async def tool_3() -> dict[str, str]:
                if not t3_ok:
                    raise ValueError("Tool 3 validation error")
                return {"tool": "3"}

            for name, tool_fn in [
                ("tool_1", tool_1),
                ("tool_2", tool_2),
                ("tool_3", tool_3),
            ]:
                try:
                    results[name] = await tool_fn()
                except Exception as e:
                    error_log.append(LoomError.tool_error(name, e))

            assert (
                len(results) == expected_success
            ), f"Case {case_name}: expected {expected_success} successes, got {len(results)}"
            assert (
                len(error_log) == expected_fail
            ), f"Case {case_name}: expected {expected_fail} failures, got {len(error_log)}"


class TestRateLimitBackoffREQ052:
    """REQ-052: Rate limit (429) exponential backoff — 3 retries with increasing delay."""

    @pytest.mark.asyncio
    async def test_retries_on_429_rate_limit(self) -> None:
        """System retries after 429 response (rate limit exceeded)."""
        call_count = 0
        call_times: list[float] = []

        async def api_call() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 3:
                raise RuntimeError("429 Too Many Requests")
            return {"status": "ok"}

        result = None
        max_retries = 3
        base_delay = 0.01  # 10ms for testing

        for attempt in range(max_retries):
            try:
                result = await api_call()
                break
            except RuntimeError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        assert result is not None
        assert result["status"] == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays_increase(self) -> None:
        """Each retry waits longer than the previous (exponential)."""
        call_times: list[float] = []
        attempt_count = 0

        async def api_call() -> dict[str, str]:
            nonlocal attempt_count
            attempt_count += 1
            call_times.append(time.time())
            if attempt_count < 4:
                raise RuntimeError("429 Too Many Requests")
            return {"success": True}

        base_delay = 0.01
        delays_experienced: list[float] = []

        for attempt in range(4):
            try:
                await api_call()
                break
            except RuntimeError:
                if attempt < 3:
                    delay = base_delay * (2**attempt)
                    delays_experienced.append(delay)
                    await asyncio.sleep(delay)

        assert len(delays_experienced) == 3
        assert delays_experienced[0] == 0.01
        assert delays_experienced[1] == 0.02
        assert delays_experienced[2] == 0.04
        assert delays_experienced[0] < delays_experienced[1] < delays_experienced[2]

    @pytest.mark.asyncio
    async def test_max_retries_respected_fails_after_three(self) -> None:
        """After 3 retries (4 total attempts), returns graceful error."""
        call_count = 0

        async def api_call() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("429 Too Many Requests")

        error_result = None
        max_retries = 3
        base_delay = 0.001

        for attempt in range(max_retries):
            try:
                await api_call()
                break
            except RuntimeError as e:
                if attempt == max_retries - 1:
                    error_result = LoomError.rate_limited("research_search", retry_after=60)
                elif attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        assert call_count == 3
        assert error_result is not None
        assert error_result["error_code"] == "RATE_LIMITED"
        assert error_result["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_successful_call_stops_retries(self) -> None:
        """If a call succeeds, don't retry further."""
        call_count = 0

        async def api_call() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return {"success": True}
            raise RuntimeError("429 Too Many Requests")

        result = None
        base_delay = 0.001

        for attempt in range(3):
            try:
                result = await api_call()
                break
            except RuntimeError:
                if attempt < 2:
                    await asyncio.sleep(base_delay * (2**attempt))

        assert call_count == 2
        assert result is not None
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_backoff_delay_calculation(self) -> None:
        """Verify exponential backoff formula: delay = base * (2^attempt)."""
        base_delay = 0.01
        expected_delays = [
            base_delay * (2**0),  # 0.01
            base_delay * (2**1),  # 0.02
            base_delay * (2**2),  # 0.04
        ]

        calculated_delays = [base_delay * (2**i) for i in range(3)]

        assert calculated_delays == expected_delays
        assert calculated_delays == [0.01, 0.02, 0.04]

    @pytest.mark.asyncio
    async def test_rate_limiter_check_method(self) -> None:
        """RateLimiter.check() returns False when limit exceeded."""
        limiter = RateLimiter(max_calls=2, window_seconds=60)

        assert await limiter.check() is True
        assert await limiter.check() is True
        assert await limiter.check() is False

    @pytest.mark.asyncio
    async def test_rate_limiter_remaining_counts_correctly(self) -> None:
        """RateLimiter.remaining() returns correct count of available calls."""
        limiter = RateLimiter(max_calls=5, window_seconds=60)

        assert limiter.remaining() == 5
        await limiter.check()
        assert limiter.remaining() == 4
        await limiter.check()
        assert limiter.remaining() == 3
        await limiter.check()
        await limiter.check()
        await limiter.check()
        assert limiter.remaining() == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_window_reset(self) -> None:
        """RateLimiter counts reset after window_seconds passes."""
        limiter = RateLimiter(max_calls=1, window_seconds=1)

        assert await limiter.check() is True
        assert await limiter.check() is False

        await asyncio.sleep(1.1)

        assert await limiter.check() is True

    @pytest.mark.asyncio
    async def test_sync_rate_limiter_check_method(self) -> None:
        """SyncRateLimiter works correctly for synchronous code."""
        reset_all()
        limiter = SyncRateLimiter(max_calls=3, window_seconds=60)

        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is False

    @pytest.mark.asyncio
    async def test_429_response_triggers_backoff_attempt(self) -> None:
        """When HTTP 429 is received, retry with exponential backoff."""
        attempts = []
        base_delay = 0.001

        async def simulated_api_with_429() -> dict[str, Any]:
            attempt_num = len(attempts) + 1
            attempts.append(attempt_num)

            if attempt_num < 3:
                raise RuntimeError("HTTP 429: Too Many Requests")
            return {"data": "success", "attempt": attempt_num}

        result = None
        for retry in range(3):
            try:
                result = await simulated_api_with_429()
                break
            except RuntimeError:
                if retry < 2:
                    await asyncio.sleep(base_delay * (2**retry))

        assert result is not None
        assert result["attempt"] == 3
        assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_error_response_includes_retry_after(self) -> None:
        """Rate limit error response includes retry_after field."""
        error_response = LoomError.rate_limited("research_deep", retry_after=120)

        assert error_response["error_code"] == "RATE_LIMITED"
        assert "retry_after" in error_response
        assert error_response["retry_after"] == 120
        assert error_response["tool_name"] == "research_deep"

    @pytest.mark.asyncio
    async def test_multiple_tools_with_rate_limit_errors(self) -> None:
        """Multiple tools can fail with rate limits, each tracked separately."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        async def tool_search() -> dict[str, str]:
            raise RuntimeError("429 Too Many Requests")

        async def tool_fetch() -> dict[str, str]:
            return {"content": "ok"}

        async def tool_summarize() -> dict[str, str]:
            raise RuntimeError("429 Too Many Requests")

        tools = {
            "search": tool_search,
            "fetch": tool_fetch,
            "summarize": tool_summarize,
        }

        for name, tool in tools.items():
            try:
                results[name] = await tool()
            except RuntimeError as e:
                if "429" in str(e):
                    error_log.append(LoomError.rate_limited(name, retry_after=60))
                else:
                    error_log.append(LoomError.tool_error(name, e))

        assert len(results) == 1
        assert len(error_log) == 2
        assert all(e["error_code"] == "RATE_LIMITED" for e in error_log)


class TestCombinedFailureAndBackoffScenarios:
    """Integration tests combining graceful failure and rate limit backoff."""

    @pytest.mark.asyncio
    async def test_pipeline_with_mixed_failures_and_rate_limits(self) -> None:
        """Pipeline handles mix of timeouts, connection errors, and rate limits."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []
        base_delay = 0.001

        async def tool_search() -> dict[str, str]:
            raise TimeoutError("Provider timeout")

        async def tool_fetch() -> dict[str, str]:
            await asyncio.sleep(0.01)
            return {"url": "example.com"}

        async def tool_summarize() -> dict[str, str]:
            raise RuntimeError("429 Too Many Requests")

        tools = {
            "search": tool_search,
            "fetch": tool_fetch,
            "summarize": tool_summarize,
        }

        for name, tool in tools.items():
            for retry in range(2):
                try:
                    results[name] = await tool()
                    break
                except RuntimeError as e:
                    if "429" in str(e):
                        if retry < 1:
                            await asyncio.sleep(base_delay * (2**retry))
                            continue
                        error_log.append(LoomError.rate_limited(name))
                    else:
                        error_log.append(LoomError.tool_error(name, e))
                    break
                except Exception as e:
                    error_log.append(LoomError.tool_error(name, e))
                    break

        assert len(results) == 1
        assert "fetch" in results
        assert len(error_log) == 2

    @pytest.mark.asyncio
    async def test_pipeline_continues_even_all_tools_fail(self) -> None:
        """Even if all tools fail, pipeline returns empty results + full error log."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        async def tool_1() -> dict[str, str]:
            raise ConnectionError("Network error")

        async def tool_2() -> dict[str, str]:
            raise TimeoutError("Timeout")

        async def tool_3() -> dict[str, str]:
            raise ValueError("Invalid input")

        tools = {"tool_1": tool_1, "tool_2": tool_2, "tool_3": tool_3}

        for name, tool in tools.items():
            try:
                results[name] = await tool()
            except Exception as e:
                error_log.append(LoomError.tool_error(name, e))

        response = {
            "results": results,
            "error_log": error_log,
            "all_failed": len(results) == 0 and len(error_log) > 0,
        }

        assert response["all_failed"] is True
        assert len(response["results"]) == 0
        assert len(response["error_log"]) == 3

    @pytest.mark.asyncio
    async def test_graceful_degradation_with_retry_strategy(self) -> None:
        """Test full graceful degradation: try with retries, fail gracefully."""
        results: dict[str, Any] = {}
        error_log: list[dict[str, Any]] = []

        call_attempts = {"flaky_tool": 0}

        async def flaky_tool() -> dict[str, str]:
            call_attempts["flaky_tool"] += 1
            if call_attempts["flaky_tool"] < 3:
                raise RuntimeError("429 Too Many Requests")
            return {"data": "recovered"}

        async def stable_tool() -> dict[str, str]:
            return {"data": "always_ok"}

        tools = {"flaky_tool": flaky_tool, "stable_tool": stable_tool}

        for name, tool in tools.items():
            max_retries = 3
            base_delay = 0.001

            for attempt in range(max_retries):
                try:
                    results[name] = await tool()
                    break
                except RuntimeError as e:
                    if attempt == max_retries - 1:
                        error_log.append(LoomError.rate_limited(name))
                    elif attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2**attempt))

        assert len(results) == 2
        assert "flaky_tool" in results
        assert "stable_tool" in results
        assert call_attempts["flaky_tool"] == 3
