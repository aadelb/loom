"""Fixtures for analytics tests."""

import pytest
from loom import analytics


@pytest.fixture(autouse=True)
def reset_analytics_state():
    """Reset analytics module-level state before each test."""
    # Clear module-level storage
    analytics._call_records.clear()
    analytics._tool_usage.clear()
    analytics._tool_errors.clear()
    analytics._tool_durations.clear()

    # Reset singleton
    analytics.ToolAnalytics._instance = None

    yield

    # Cleanup after test
    analytics._call_records.clear()
    analytics._tool_usage.clear()
    analytics._tool_errors.clear()
    analytics._tool_durations.clear()
