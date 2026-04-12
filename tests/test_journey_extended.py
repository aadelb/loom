"""Extended tests for journey module — JourneyReport, Step, callbacks, formatting.

Tests edge cases: markdown rendering, step serialization, callback safety, duration formatting.
"""

from __future__ import annotations

import pytest

pytest.importorskip("loom.journey")


def test_journey_report_markdown_output() -> None:
    """JourneyReport.as_markdown() renders all required sections."""
    from loom.journey import JourneyReport, Step

    report = JourneyReport(
        topic="test research",
        server_url="http://localhost:8787",
        started_at="2026-04-11T12:00:00+00:00",
        ended_at="2026-04-11T12:00:10+00:00",
        ok_count=2,
        fail_count=1,
    )

    report.steps.append(
        Step(
            n=0,
            name="initialize",
            tool="mcp.initialize",
            params={},
            ok=True,
            duration_ms=100,
            result={"server": "loom", "version": "1.0"},
        )
    )

    markdown = report.as_markdown()

    assert "# Loom journey test" in markdown
    assert "**Topic:** test research" in markdown
    assert "**Server:** http://localhost:8787" in markdown
    assert "Step 0" in markdown
    assert "mcp.initialize" in markdown
    assert "✅" in markdown


def test_journey_step_to_dict() -> None:
    """Step.to_dict() serializes all fields for JSON."""
    from loom.journey import Step

    step = Step(
        n=1,
        name="test_step",
        tool="test.tool",
        params={"key": "value"},
        ok=True,
        duration_ms=250,
        result={"output": "test"},
        error=None,
    )

    d = step.to_dict()

    assert d["n"] == 1
    assert d["name"] == "test_step"
    assert d["tool"] == "test.tool"
    assert d["params"] == {"key": "value"}
    assert d["ok"] is True
    assert d["duration_ms"] == 250
    assert d["result"] == {"output": "test"}
    assert d["error"] is None


def test_safe_on_step_catches_exception() -> None:
    """_safe_on_step catches callback exceptions and logs warnings."""
    from loom.journey import Step, _safe_on_step

    step = Step(
        n=0,
        name="test",
        tool="test.tool",
        params={},
    )

    def failing_callback(_step):
        raise ValueError("Test error")

    # Should not raise
    _safe_on_step(failing_callback, step)


def test_safe_on_step_none_callback_noop() -> None:
    """_safe_on_step with None callback does nothing."""
    from loom.journey import Step, _safe_on_step

    step = Step(
        n=0,
        name="test",
        tool="test.tool",
        params={},
    )

    # Should not raise
    _safe_on_step(None, step)


def test_format_duration_seconds() -> None:
    """_format_duration converts milliseconds to seconds for >= 1000ms."""
    from loom.journey import _format_duration

    assert _format_duration(1500) == "1.5s"
    assert _format_duration(1000) == "1.0s"
    assert _format_duration(2500) == "2.5s"


def test_format_duration_milliseconds() -> None:
    """_format_duration keeps milliseconds for < 1000ms."""
    from loom.journey import _format_duration

    assert _format_duration(800) == "800ms"
    assert _format_duration(100) == "100ms"
    assert _format_duration(999) == "999ms"
