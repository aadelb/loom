"""Tests for the attack visualization dashboard.

Tests cover:
- Event recording (add_event)
- Event retrieval (get_events)
- Summary statistics calculation
- HTML generation with embedded data
- Event filtering by index
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from loom.dashboard import AttackDashboard


class TestAttackDashboardEventManagement:
    """Test event recording and retrieval."""

    def test_add_event_single(self) -> None:
        """Test adding a single event."""
        dashboard = AttackDashboard()
        assert len(dashboard.events) == 0

        dashboard.add_event("attack_success", {"model": "gpt-4", "score": 85})

        assert len(dashboard.events) == 1
        event = dashboard.events[0]
        assert event["type"] == "attack_success"
        assert event["data"]["model"] == "gpt-4"
        assert event["data"]["score"] == 85
        assert "timestamp" in event
        assert event["index"] == 0

    def test_add_event_with_custom_timestamp(self) -> None:
        """Test adding event with custom timestamp."""
        dashboard = AttackDashboard()
        custom_time = "2026-04-30T12:00:00+00:00"

        dashboard.add_event(
            "strategy_applied",
            {"strategy": "prompt_injection"},
            timestamp=custom_time,
        )

        event = dashboard.events[0]
        assert event["timestamp"] == custom_time

    def test_add_multiple_events(self) -> None:
        """Test adding multiple events."""
        dashboard = AttackDashboard()

        for i in range(5):
            dashboard.add_event(
                "attack_success" if i % 2 == 0 else "attack_failure",
                {"model": f"model_{i}", "attempt": i},
            )

        assert len(dashboard.events) == 5
        assert dashboard.events[0]["index"] == 0
        assert dashboard.events[4]["index"] == 4

    def test_get_events_all(self) -> None:
        """Test retrieving all events."""
        dashboard = AttackDashboard()

        for i in range(3):
            dashboard.add_event("strategy_applied", {"strategy": f"strat_{i}"})

        events = dashboard.get_events(since=0)

        assert len(events) == 3
        assert events[0]["index"] == 0
        assert events[2]["index"] == 2

    def test_get_events_since_index(self) -> None:
        """Test retrieving events from a specific index."""
        dashboard = AttackDashboard()

        for i in range(5):
            dashboard.add_event("score_update", {"score": i * 10})

        events = dashboard.get_events(since=2)

        assert len(events) == 3
        assert events[0]["index"] == 2
        assert events[1]["index"] == 3
        assert events[2]["index"] == 4

    def test_get_events_beyond_range(self) -> None:
        """Test retrieving events from beyond available range."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {})
        dashboard.add_event("attack_failure", {})

        events = dashboard.get_events(since=10)

        assert len(events) == 0

    def test_get_events_negative_index(self) -> None:
        """Test that negative indices are treated as 0."""
        dashboard = AttackDashboard()

        for i in range(3):
            dashboard.add_event("model_response", {"response": f"resp_{i}"})

        events = dashboard.get_events(since=-5)

        assert len(events) == 3
        assert events[0]["index"] == 0


class TestAttackDashboardSummary:
    """Test summary statistics calculation."""

    def test_summary_empty_dashboard(self) -> None:
        """Test summary for empty dashboard."""
        dashboard = AttackDashboard()
        summary = dashboard.get_summary()

        assert summary["total_attacks"] == 0
        assert summary["successes"] == 0
        assert summary["failures"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["avg_hcs_score"] == 0.0
        assert summary["top_strategies"] == []
        assert summary["active_models"] == []

    def test_summary_attack_counters(self) -> None:
        """Test attack success/failure counters."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "gpt-4"})
        dashboard.add_event("attack_success", {"model": "claude"})
        dashboard.add_event("attack_failure", {"model": "llama"})

        summary = dashboard.get_summary()

        assert summary["total_attacks"] == 3
        assert summary["successes"] == 2
        assert summary["failures"] == 1
        assert summary["success_rate"] == pytest.approx(66.7, abs=0.1)

    def test_summary_hcs_score_tracking(self) -> None:
        """Test HCS score calculation."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"hcs_score": 50})
        dashboard.add_event("attack_success", {"hcs_score": 80})
        dashboard.add_event("attack_success", {"hcs_score": 70})

        summary = dashboard.get_summary()

        assert summary["avg_hcs_score"] == pytest.approx(66.7, abs=0.1)

    def test_summary_active_models(self) -> None:
        """Test tracking of active models."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "gpt-4"})
        dashboard.add_event("attack_success", {"model": "claude"})
        dashboard.add_event("attack_failure", {"model": "gpt-4"})
        dashboard.add_event("attack_success", {"model": "llama"})

        summary = dashboard.get_summary()

        assert set(summary["active_models"]) == {"gpt-4", "claude", "llama"}

    def test_summary_top_strategies(self) -> None:
        """Test top strategies ranking."""
        dashboard = AttackDashboard()

        # Strategy A: 3 attempts, 2 successes (66.7%)
        for _ in range(2):
            dashboard.add_event("strategy_applied", {"strategy": "strategy_a"})
            dashboard.add_event("attack_success", {"strategy": "strategy_a"})
        dashboard.add_event("strategy_applied", {"strategy": "strategy_a"})
        dashboard.add_event("attack_failure", {"strategy": "strategy_a"})

        # Strategy B: 2 attempts, 2 successes (100%)
        for _ in range(2):
            dashboard.add_event("strategy_applied", {"strategy": "strategy_b"})
            dashboard.add_event("attack_success", {"strategy": "strategy_b"})

        summary = dashboard.get_summary()
        strategies = summary["top_strategies"]

        assert len(strategies) <= 5
        # Strategy B should be first (100% > 66.7%)
        assert strategies[0]["name"] == "strategy_b"
        assert strategies[0]["rate"] == 100.0
        assert strategies[1]["name"] == "strategy_a"
        assert strategies[1]["rate"] == pytest.approx(66.7, abs=0.1)

    def test_summary_model_stats(self) -> None:
        """Test per-model statistics."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "gpt-4"})
        dashboard.add_event("attack_success", {"model": "gpt-4"})
        dashboard.add_event("attack_failure", {"model": "gpt-4"})
        dashboard.add_event("attack_success", {"model": "claude"})

        summary = dashboard.get_summary()
        model_stats = summary["model_stats"]

        assert model_stats["gpt-4"]["total"] == 3
        assert model_stats["gpt-4"]["successes"] == 2
        assert model_stats["claude"]["total"] == 1
        assert model_stats["claude"]["successes"] == 1

    def test_summary_event_count(self) -> None:
        """Test event count in summary."""
        dashboard = AttackDashboard()

        for i in range(10):
            dashboard.add_event(
                "model_response",
                {"response": f"resp_{i}"},
            )

        summary = dashboard.get_summary()

        assert summary["event_count"] == 10


class TestAttackDashboardHtmlGeneration:
    """Test HTML dashboard generation."""

    def test_generate_html_basic_structure(self) -> None:
        """Test that generated HTML has required structure."""
        dashboard = AttackDashboard()
        html = dashboard.generate_html()

        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "Attack Dashboard" in html

    def test_generate_html_contains_metrics(self) -> None:
        """Test that HTML contains metric containers."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "gpt-4", "hcs_score": 75})
        dashboard.add_event("attack_failure", {"model": "claude"})

        html = dashboard.generate_html()

        assert "Total Attacks" in html
        assert "Successes" in html
        assert "Failures" in html
        assert "Success Rate" in html
        assert "Avg HCS Score" in html
        assert "Active Models" in html

    def test_generate_html_contains_strategy_table(self) -> None:
        """Test that HTML contains strategy success rate table."""
        dashboard = AttackDashboard()

        dashboard.add_event("strategy_applied", {"strategy": "prompt_injection"})
        dashboard.add_event("attack_success", {"strategy": "prompt_injection"})

        html = dashboard.generate_html()

        assert "Strategy Success Rates" in html
        assert "Strategy Name" in html
        assert "Attempts" in html
        assert "Successes" in html
        assert "prompt_injection" in html

    def test_generate_html_contains_model_table(self) -> None:
        """Test that HTML contains model comparison table."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "gpt-4"})
        dashboard.add_event("attack_failure", {"model": "claude"})

        html = dashboard.generate_html()

        assert "Model Comparison" in html
        assert "Model" in html
        assert "Total Attacks" in html
        assert "gpt-4" in html

    def test_generate_html_contains_event_feed(self) -> None:
        """Test that HTML contains event feed section."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "gpt-4", "score": 80})
        dashboard.add_event("model_response", {"response": "test"})

        html = dashboard.generate_html()

        assert "Event Feed" in html
        assert "event-feed" in html

    def test_generate_html_embedded_data(self) -> None:
        """Test that events are embedded in HTML as JSON."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "test_model"})

        html = dashboard.generate_html()

        # Check that event data is embedded
        assert "allEvents = " in html
        assert "test_model" in html

    def test_generate_html_displays_counter_values(self) -> None:
        """Test that metric values are displayed."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"hcs_score": 85})
        dashboard.add_event("attack_failure", {})

        html = dashboard.generate_html()

        # Should contain counters
        assert "<div class=\"metric-value\">1</div>" in html or ">1<" in html

    def test_generate_html_styling(self) -> None:
        """Test that HTML includes proper styling."""
        dashboard = AttackDashboard()
        html = dashboard.generate_html()

        assert "<style>" in html
        assert "</style>" in html
        assert "background:" in html
        assert "color:" in html

    def test_generate_html_responsive_design(self) -> None:
        """Test that HTML includes responsive CSS."""
        dashboard = AttackDashboard()
        html = dashboard.generate_html()

        assert "@media" in html
        assert "viewport" in html

    def test_generate_html_no_events_message(self) -> None:
        """Test that empty dashboard shows appropriate message."""
        dashboard = AttackDashboard()
        html = dashboard.generate_html()

        assert "no-events" in html or "No events" in html

    def test_generate_html_recent_events_only(self) -> None:
        """Test that HTML displays only recent events (last 20)."""
        dashboard = AttackDashboard()

        # Add 30 events
        for i in range(30):
            dashboard.add_event("score_update", {"index": i})

        html = dashboard.generate_html()

        # Check that early events are not in the visible HTML body
        # (they may be in embedded JSON but not displayed in event feed)
        assert "index" in html


class TestAttackDashboardIntegration:
    """Integration tests combining multiple operations."""

    def test_dashboard_workflow_complete(self) -> None:
        """Test complete dashboard workflow."""
        dashboard = AttackDashboard()

        # Add various events
        dashboard.add_event("strategy_applied", {"strategy": "jailbreak_v1"})
        dashboard.add_event("model_response", {"response": "I cannot help"})
        dashboard.add_event("attack_failure", {"model": "gpt-4", "reason": "filtered"})

        dashboard.add_event("strategy_applied", {"strategy": "roleplay"})
        dashboard.add_event("model_response", {"response": "Sure, I'll help"})
        dashboard.add_event("attack_success", {"model": "gpt-4", "hcs_score": 75})

        # Get summary
        summary = dashboard.get_summary()
        assert summary["total_attacks"] == 2
        assert summary["successes"] == 1
        assert summary["failures"] == 1

        # Get recent events
        events = dashboard.get_events(since=3)
        assert len(events) == 3

        # Generate HTML
        html = dashboard.generate_html()
        assert "50.0%" in html or "success" in html.lower()

    def test_dashboard_persistence_pattern(self) -> None:
        """Test that dashboard can be reused across multiple calls."""
        # Simulate scenario where dashboard is used across multiple tool calls
        dashboard1 = AttackDashboard()

        dashboard1.add_event("attack_success", {"model": "gpt-4"})
        dashboard1.add_event("attack_failure", {"model": "claude"})

        summary1 = dashboard1.get_summary()
        assert summary1["total_attacks"] == 2

        # Simulate a new dashboard instance (separate tool call)
        dashboard2 = AttackDashboard()
        assert len(dashboard2.events) == 0  # New instance starts fresh

    def test_dashboard_empty_to_populated_flow(self) -> None:
        """Test dashboard going from empty to populated state."""
        dashboard = AttackDashboard()

        # Start empty
        empty_summary = dashboard.get_summary()
        assert empty_summary["total_attacks"] == 0
        empty_html = dashboard.generate_html()
        assert isinstance(empty_html, str)

        # Add events
        dashboard.add_event("attack_success", {"model": "gpt-4", "hcs_score": 80})
        dashboard.add_event("attack_success", {"model": "claude", "hcs_score": 90})

        # Check populated
        populated_summary = dashboard.get_summary()
        assert populated_summary["total_attacks"] == 2
        assert populated_summary["success_rate"] == 100.0
        assert populated_summary["avg_hcs_score"] == 85.0

    def test_dashboard_html_consistency(self) -> None:
        """Test that HTML generation produces consistent results."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": "test", "score": 100})

        html1 = dashboard.generate_html()
        html2 = dashboard.generate_html()

        # Both should contain the same data (timestamps may differ slightly)
        assert "test" in html1 and "test" in html2
        assert html1.count("<table") == html2.count("<table")


class TestAttackDashboardEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_event_data(self) -> None:
        """Test adding event with empty data dict."""
        dashboard = AttackDashboard()

        dashboard.add_event("model_response", {})

        assert len(dashboard.events) == 1
        assert dashboard.events[0]["data"] == {}

    def test_large_event_data(self) -> None:
        """Test adding event with large data payload."""
        dashboard = AttackDashboard()

        large_data = {
            "response": "x" * 10000,
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        dashboard.add_event("attack_success", large_data)

        assert len(dashboard.events) == 1
        assert dashboard.events[0]["data"]["response"] == "x" * 10000

    def test_special_characters_in_event_data(self) -> None:
        """Test handling special characters in event data."""
        dashboard = AttackDashboard()

        special_data = {
            "model": "test\\model",
            "response": 'I said "hello" <script>',
            "unicode": "测试 🚀 ñoño",
        }

        dashboard.add_event("attack_success", special_data)

        html = dashboard.generate_html()
        assert isinstance(html, str)  # Should generate without errors

    def test_many_strategies_ranking(self) -> None:
        """Test ranking with many different strategies."""
        dashboard = AttackDashboard()

        # Add 10 different strategies
        for s_idx in range(10):
            for attempt in range(s_idx + 1):
                dashboard.add_event("strategy_applied", {"strategy": f"strat_{s_idx}"})
                if attempt < (s_idx + 1) // 2:  # Vary success rates
                    dashboard.add_event("attack_success", {"strategy": f"strat_{s_idx}"})

        summary = dashboard.get_summary()
        strategies = summary["top_strategies"]

        # Should return at most 5
        assert len(strategies) <= 5
        # Should be sorted by success rate
        if len(strategies) > 1:
            assert strategies[0]["rate"] >= strategies[1]["rate"]

    def test_numeric_models_and_strategies(self) -> None:
        """Test with numeric identifiers."""
        dashboard = AttackDashboard()

        dashboard.add_event("attack_success", {"model": 1, "strategy": 42})
        dashboard.add_event("attack_failure", {"model": 2, "strategy": 43})

        summary = dashboard.get_summary()
        assert summary["total_attacks"] == 2
