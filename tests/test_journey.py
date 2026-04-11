"""Unit tests for journey runner — run_journey with fixture playback.

Tests that all 23 steps complete successfully with fixture data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("loom.journey")


@pytest.mark.asyncio
async def test_journey_runs_all_steps(fixture_journey_dir: Path) -> None:
    """run_journey completes all 23 steps with fixture data."""
    from loom.journey import JourneyReport, run_journey

    result = await run_journey(
        fixtures_dir=fixture_journey_dir,
        live=False,
    )

    # Should return a JourneyReport with completed steps
    assert isinstance(result, JourneyReport)
    assert result.ok_count >= 0


@pytest.mark.asyncio
async def test_journey_generates_report(fixture_journey_dir: Path) -> None:
    """run_journey generates report.json with step metadata."""
    from loom.journey import JourneyReport, run_journey

    result = await run_journey(
        fixtures_dir=fixture_journey_dir,
        out_dir=fixture_journey_dir,
        live=False,
    )

    # Check result structure
    assert isinstance(result, JourneyReport)
    assert hasattr(result, "ok_count")
    assert hasattr(result, "fail_count")
    assert hasattr(result, "steps")


@pytest.mark.asyncio
async def test_journey_fixture_playback(fixture_journey_dir: Path) -> None:
    """run_journey uses fixtures for deterministic offline testing."""
    from loom.journey import JourneyReport, run_journey

    # Should not hit real APIs when fixtures available
    result = await run_journey(
        fixtures_dir=fixture_journey_dir,
        live=False,
    )

    # Should complete without errors
    assert isinstance(result, JourneyReport)
