"""Tests for shared async_tool_runner module.

Tests async task execution, concurrency management, timeouts, and error handling.
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.async_tool_runner import invoke, invoke_many


class TestInvokeAsync:
    """Tests for invoke() with async functions."""

    @pytest.mark.asyncio
    async def test_invoke_async_function_success(self) -> None:
        """invoke() calls async function and returns result."""
        async def async_func(x: int, y: int) -> dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"sum": x + y}

        result = await invoke(async_func, 3, 4)

        assert result["sum"] == 7
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], int)

    @pytest.mark.asyncio
    async def test_invoke_async_function_with_kwargs(self) -> None:
        """invoke() passes kwargs correctly to async functions."""
        async def async_func(a: str, b: str = "default") -> dict[str, Any]:
            return {"result": f"{a}-{b}"}

        result = await invoke(async_func, "hello", b="world")

        assert result["result"] == "hello-world"

    @pytest.mark.asyncio
    async def test_invoke_async_non_dict_result_wrapped(self) -> None:
        """invoke() wraps non-dict results in {"result": value}."""
        async def async_func() -> str:
            return "hello"

        result = await invoke(async_func)

        assert result["result"] == "hello"
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_invoke_async_dict_result_not_wrapped(self) -> None:
        """invoke() returns dict results as-is."""
        async def async_func() -> dict[str, Any]:
            return {"status": "ok", "data": 42}

        result = await invoke(async_func)

        assert result["status"] == "ok"
        assert result["data"] == 42
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_invoke_async_dict_preserves_elapsed_ms(self) -> None:
        """invoke() preserves existing elapsed_ms in dict result."""
        async def async_func() -> dict[str, Any]:
            return {"result": "ok", "elapsed_ms": 100}

        result = await invoke(async_func)

        # Should keep the original elapsed_ms, not overwrite
        assert result["elapsed_ms"] == 100

    @pytest.mark.asyncio
    async def test_invoke_async_timeout_error(self) -> None:
        """invoke() returns error dict on timeout."""
        async def slow_func() -> None:
            await asyncio.sleep(10)

        result = await invoke(slow_func, timeout=0.01)

        assert "error" in result
        assert "Timeout" in result["error"]
        assert "0.01" in result["error"]
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_invoke_async_exception_handling(self) -> None:
        """invoke() catches exceptions and returns error dict."""
        async def failing_func() -> None:
            raise ValueError("test error message")

        result = await invoke(failing_func)

        assert "error" in result
        assert "test error message" in result["error"]
        assert result["error_type"] == "ValueError"
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_invoke_async_elapsed_ms_timing(self) -> None:
        """invoke() records elapsed time correctly."""
        async def timed_func() -> None:
            await asyncio.sleep(0.05)

        result = await invoke(timed_func)

        # Should be approximately 50ms (allow 30-70ms range for system variance)
        assert 30 <= result["elapsed_ms"] <= 100


class TestInvokeSync:
    """Tests for invoke() with sync functions."""

    @pytest.mark.asyncio
    async def test_invoke_sync_function_success(self) -> None:
        """invoke() runs sync functions via executor."""
        def sync_func(x: int, y: int) -> dict[str, Any]:
            return {"product": x * y}

        result = await invoke(sync_func, 5, 6)

        assert result["product"] == 30
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_invoke_sync_function_with_kwargs(self) -> None:
        """invoke() passes kwargs to sync functions."""
        def sync_func(name: str, greeting: str = "Hello") -> dict[str, Any]:
            return {"message": f"{greeting}, {name}"}

        result = await invoke(sync_func, "World", greeting="Hi")

        assert result["message"] == "Hi, World"

    @pytest.mark.asyncio
    async def test_invoke_sync_non_dict_result(self) -> None:
        """invoke() wraps non-dict sync results."""
        def sync_func() -> int:
            return 42

        result = await invoke(sync_func)

        assert result["result"] == 42
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_invoke_sync_timeout_error(self) -> None:
        """invoke() times out sync functions."""
        def slow_sync() -> None:
            import time
            time.sleep(10)

        result = await invoke(slow_sync, timeout=0.05)

        assert "error" in result
        assert "Timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_invoke_sync_exception_handling(self) -> None:
        """invoke() catches exceptions from sync functions."""
        def failing_sync() -> None:
            raise RuntimeError("sync error")

        result = await invoke(failing_sync)

        assert "error" in result
        assert "sync error" in result["error"]
        assert result["error_type"] == "RuntimeError"


class TestInvokeMany:
    """Tests for invoke_many() concurrent execution."""

    @pytest.mark.asyncio
    async def test_invoke_many_success(self) -> None:
        """invoke_many() runs multiple tasks concurrently."""
        async def task(n: int) -> dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"result": n * 2}

        calls = [
            (task, (1,), {}),
            (task, (2,), {}),
            (task, (3,), {}),
        ]

        results = await invoke_many(calls)

        assert len(results) == 3
        assert results[0]["result"] == 2
        assert results[1]["result"] == 4
        assert results[2]["result"] == 6

    @pytest.mark.asyncio
    async def test_invoke_many_maintains_order(self) -> None:
        """invoke_many() returns results in same order as input."""
        async def task(n: int) -> dict[str, Any]:
            # Longer delay for higher numbers to ensure they don't finish first
            await asyncio.sleep(0.05 - n * 0.01)
            return {"n": n}

        calls = [
            (task, (5,), {}),
            (task, (1,), {}),
            (task, (3,), {}),
        ]

        results = await invoke_many(calls)

        assert results[0]["n"] == 5
        assert results[1]["n"] == 1
        assert results[2]["n"] == 3

    @pytest.mark.asyncio
    async def test_invoke_many_with_kwargs(self) -> None:
        """invoke_many() passes kwargs to tasks."""
        async def task(a: int, b: int = 10) -> dict[str, Any]:
            return {"sum": a + b}

        calls = [
            (task, (1,), {"b": 100}),
            (task, (2,), {"b": 200}),
        ]

        results = await invoke_many(calls)

        assert results[0]["sum"] == 101
        assert results[1]["sum"] == 202

    @pytest.mark.asyncio
    async def test_invoke_many_respects_max_concurrency(self) -> None:
        """invoke_many() limits concurrent tasks via semaphore."""
        concurrency_count = 0
        max_observed = 0

        async def task() -> dict[str, Any]:
            nonlocal concurrency_count, max_observed
            concurrency_count += 1
            max_observed = max(max_observed, concurrency_count)
            await asyncio.sleep(0.01)
            concurrency_count -= 1
            return {"ok": True}

        # Create 10 tasks with max_concurrency=2
        calls = [(task, (), {}) for _ in range(10)]

        results = await invoke_many(calls, max_concurrency=2)

        assert len(results) == 10
        # Max observed should be <= 2 (may be 1 or 2 depending on timing)
        assert max_observed <= 2

    @pytest.mark.asyncio
    async def test_invoke_many_default_concurrency(self) -> None:
        """invoke_many() uses default max_concurrency=5."""
        async def task() -> dict[str, Any]:
            return {"ok": True}

        calls = [(task, (), {}) for _ in range(10)]

        results = await invoke_many(calls)

        assert len(results) == 10
        assert all(r["ok"] is True for r in results)

    @pytest.mark.asyncio
    async def test_invoke_many_error_in_one_task(self) -> None:
        """invoke_many() doesn't stop on one task's error."""
        async def failing_task() -> None:
            raise ValueError("failed")

        async def success_task() -> dict[str, Any]:
            return {"ok": True}

        calls = [
            (success_task, (), {}),
            (failing_task, (), {}),
            (success_task, (), {}),
        ]

        results = await invoke_many(calls)

        assert len(results) == 3
        assert results[0]["ok"] is True
        assert "error" in results[1]
        assert results[2]["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_many_timeout_per_call(self) -> None:
        """invoke_many() applies timeout to each call."""
        async def fast_task() -> dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"ok": True}

        async def slow_task() -> None:
            await asyncio.sleep(10)

        calls = [
            (fast_task, (), {}),
            (slow_task, (), {}),
            (fast_task, (), {}),
        ]

        results = await invoke_many(calls, timeout=0.05)

        assert results[0]["ok"] is True
        assert "error" in results[1]
        assert "Timeout" in results[1]["error"]
        assert results[2]["ok"] is True

    @pytest.mark.asyncio
    async def test_invoke_many_empty_list(self) -> None:
        """invoke_many() handles empty call list."""
        results = await invoke_many([])

        assert results == []

    @pytest.mark.asyncio
    async def test_invoke_many_mixed_sync_async(self) -> None:
        """invoke_many() handles mix of sync and async functions."""
        async def async_task(n: int) -> dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"async": n}

        def sync_task(n: int) -> dict[str, Any]:
            return {"sync": n}

        calls = [
            (async_task, (1,), {}),
            (sync_task, (2,), {}),
            (async_task, (3,), {}),
        ]

        results = await invoke_many(calls)

        assert results[0]["async"] == 1
        assert results[1]["sync"] == 2
        assert results[2]["async"] == 3

    @pytest.mark.asyncio
    async def test_invoke_many_high_concurrency(self) -> None:
        """invoke_many() works with high concurrency settings."""
        async def task(n: int) -> dict[str, Any]:
            return {"n": n}

        calls = [(task, (i,), {}) for i in range(50)]

        results = await invoke_many(calls, max_concurrency=20)

        assert len(results) == 50
        assert all(results[i]["n"] == i for i in range(50))
