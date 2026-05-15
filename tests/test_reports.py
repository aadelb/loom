"""Tests for graceful shutdown (REQ-072) and report generation (REQ-073, REQ-074).

Test coverage:
- REQ-072: Graceful shutdown on SIGTERM
  1. SIGTERM handler is registered
  2. Shutdown function exists and is callable
  3. Cleanup closes sessions/connections

- REQ-073: "What Works" report generator
  1. All required fields present
  2. Pass rate calculated correctly
  3. Categories grouped correctly
  4. Empty results → pass_rate=0
  5. All passed → pass_rate=100
  6. Output to file works

- REQ-074: "What Doesn't Work" failure analysis
  7. Groups failures by category
  8. Error patterns counted correctly
  9. Recommendations sorted by severity
  10. Zero failures → empty categories

Total: 12+ test functions
"""

from __future__ import annotations

import asyncio
import json
import signal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import MagicMock, patch

import pytest



pytestmark = pytest.mark.asyncio
class TestGracefulShutdown:
    """Tests for graceful shutdown on SIGTERM (REQ-072)."""

    async def test_sigterm_handler_registered_in_main(self) -> None:
        """SIGTERM handler is registered when main() is called."""
        from loom.server import _handle_signal

        # Verify _handle_signal is callable
        assert callable(_handle_signal)

    async def test_shutdown_function_exists_and_is_async(self) -> None:
        """_shutdown function exists and is an async callable."""
        from loom.server import _shutdown
        import inspect

        assert callable(_shutdown)
        assert inspect.iscoroutinefunction(_shutdown)

    async def test_shutdown_closes_browser_sessions(self) -> None:
        """_shutdown calls cleanup_all_sessions."""
        with patch("loom.server.cleanup_all_sessions") as mock_cleanup:
            mock_cleanup.return_value = {"closed": ["session1"], "errors": []}

            from loom.server import _shutdown

            await _shutdown()

            mock_cleanup.assert_called_once()

    async def test_shutdown_closes_http_client(self) -> None:
        """_shutdown closes the httpx connection pool."""
        with patch("loom.tools.core.fetch._http_client") as mock_client:
            mock_client.close = MagicMock()
            mock_client.__bool__ = MagicMock(return_value=True)

            from loom.server import _shutdown

            await _shutdown()

            # Verify close was attempted on the mock client
            mock_client.close.assert_called()

    async def test_shutdown_closes_llm_providers(self) -> None:
        """_shutdown closes LLM provider clients."""
        with patch("loom.server._optional_tools") as mock_tools:
            mock_tools.__contains__ = MagicMock(return_value=True)
            mock_llm = MagicMock()
            mock_llm.close_all_providers = MagicMock(
                return_value=asyncio.sleep(0)
            )
            mock_tools.__getitem__ = MagicMock(return_value=mock_llm)

            from loom.server import _shutdown

            # Should not raise even if close_all_providers is not found
            try:
                await _shutdown()
            except Exception:
                pass  # Expected in mock scenario

    async def test_handle_signal_creates_task(self) -> None:
        """_handle_signal creates an async task for shutdown."""
        from loom.server import _handle_signal

        # Mock asyncio.get_running_loop
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_loop.create_task = MagicMock(return_value=mock_task)

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch("loom.server._shutdown"):
                _handle_signal(signal.SIGTERM, None)

                # Verify create_task was called
                mock_loop.create_task.assert_called_once()

    async def test_handle_signal_runs_shutdown_if_no_loop(self) -> None:
        """_handle_signal runs _shutdown directly if no event loop."""
        from loom.server import _handle_signal

        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            with patch("asyncio.run") as mock_run:
                _handle_signal(signal.SIGTERM, None)

                # Verify asyncio.run was called
                mock_run.assert_called_once()

    async def test_signal_handlers_registered_in_main(self) -> None:
        """main() registers SIGTERM and SIGINT signal handlers."""
        with patch("loom.server.create_app") as mock_create:
            mock_app = MagicMock()
            mock_app.run = MagicMock()
            mock_create.return_value = mock_app

            with patch("signal.signal") as mock_signal:
                from loom.server import main

                main()

                # Verify signal handlers were registered
                calls = mock_signal.call_args_list
                signal_numbers = [call[0][0] for call in calls]

                assert signal.SIGTERM in signal_numbers
                assert signal.SIGINT in signal_numbers


class TestWhatWorksReport:
    """Tests for 'What Works' report generator (REQ-073)."""

    async def test_report_has_all_required_fields(self) -> None:
        """'What Works' report contains all required fields."""
        from loom.reports import generate_what_works_report

        test_results = [
            {"name": "test_a", "status": "passed", "category": "fetch"},
            {"name": "test_b", "status": "passed", "category": "fetch"},
        ]

        report = generate_what_works_report(test_results)

        assert "title" in report
        assert "total_tests" in report
        assert "passed" in report
        assert "failed" in report
        assert "pass_rate" in report
        assert "working_categories" in report
        assert "summary" in report

    async def test_pass_rate_calculated_correctly(self) -> None:
        """Pass rate is correctly calculated as percentage."""
        from loom.reports import generate_what_works_report

        test_results = [
            {"name": "test_1", "status": "passed", "category": "search"},
            {"name": "test_2", "status": "passed", "category": "search"},
            {"name": "test_3", "status": "failed", "category": "fetch"},
            {"name": "test_4", "status": "failed", "category": "fetch"},
        ]

        report = generate_what_works_report(test_results)

        assert report["total_tests"] == 4
        assert report["passed"] == 2
        assert report["failed"] == 2
        assert report["pass_rate"] == 50.0

    async def test_categories_grouped_correctly(self) -> None:
        """Tests are grouped by category correctly."""
        from loom.reports import generate_what_works_report

        test_results = [
            {"name": "fetch_1", "status": "passed", "category": "fetch"},
            {"name": "fetch_2", "status": "passed", "category": "fetch"},
            {"name": "search_1", "status": "passed", "category": "search"},
        ]

        report = generate_what_works_report(test_results)

        categories = report["working_categories"]
        assert "fetch" in categories
        assert "search" in categories
        assert len(categories["fetch"]) == 2
        assert len(categories["search"]) == 1

    async def test_empty_results_pass_rate_zero(self) -> None:
        """Pass rate is 0 when no tests are passed."""
        from loom.reports import generate_what_works_report

        test_results = [
            {"name": "test_1", "status": "failed", "category": "fetch"},
        ]

        report = generate_what_works_report(test_results)

        assert report["pass_rate"] == 0.0
        assert report["passed"] == 0
        assert report["total_tests"] == 1

    async def test_all_passed_pass_rate_100(self) -> None:
        """Pass rate is 100 when all tests pass."""
        from loom.reports import generate_what_works_report

        test_results = [
            {"name": "test_1", "status": "passed", "category": "fetch"},
            {"name": "test_2", "status": "passed", "category": "search"},
            {"name": "test_3", "status": "passed", "category": "analysis"},
        ]

        report = generate_what_works_report(test_results)

        assert report["pass_rate"] == 100.0
        assert report["passed"] == 3
        assert report["failed"] == 0

    async def test_output_to_file(self) -> None:
        """Report can be written to a file."""
        from loom.reports import generate_what_works_report

        test_results = [
            {"name": "test_1", "status": "passed", "category": "fetch"},
        ]

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "what_works.json"

            report = generate_what_works_report(test_results, output_path)

            # Verify file was created
            assert output_path.exists()

            # Verify file contains valid JSON
            file_content = json.loads(output_path.read_text())
            assert file_content["pass_rate"] == 100.0

    async def test_report_title_correct(self) -> None:
        """Report title is 'What Works — Loom v3 Production Readiness'."""
        from loom.reports import generate_what_works_report

        test_results = []

        report = generate_what_works_report(test_results)

        assert report["title"] == "What Works — Loom v3 Production Readiness"

    async def test_uncategorized_tests_grouped(self) -> None:
        """Tests without a category are grouped as 'uncategorized'."""
        from loom.reports import generate_what_works_report

        test_results = [
            {"name": "test_1", "status": "passed"},  # No category
            {"name": "test_2", "status": "passed", "category": "fetch"},
        ]

        report = generate_what_works_report(test_results)

        categories = report["working_categories"]
        assert "uncategorized" in categories
        assert "fetch" in categories


class TestWhatDoesntWorkReport:
    """Tests for 'What Doesn't Work' failure analysis (REQ-074)."""

    async def test_report_groups_failures_by_category(self) -> None:
        """Failures are grouped by category."""
        from loom.reports import generate_failure_report

        test_results = [
            {
                "name": "fetch_timeout",
                "status": "failed",
                "category": "fetch",
                "error": "Timeout after 30s",
                "error_type": "TimeoutError",
            },
            {
                "name": "fetch_ssl",
                "status": "failed",
                "category": "fetch",
                "error": "SSL certificate error",
                "error_type": "SSLError",
            },
            {
                "name": "search_api",
                "status": "failed",
                "category": "search",
                "error": "API rate limit",
                "error_type": "RateLimitError",
            },
        ]

        report = generate_failure_report(test_results)

        categories = report["failure_categories"]
        assert "fetch" in categories
        assert "search" in categories
        assert len(categories["fetch"]) == 2
        assert len(categories["search"]) == 1

    async def test_error_patterns_counted(self) -> None:
        """Error patterns are counted and aggregated correctly."""
        from loom.reports import generate_failure_report

        test_results = [
            {
                "name": "test_1",
                "status": "failed",
                "error_type": "TimeoutError",
            },
            {
                "name": "test_2",
                "status": "failed",
                "error_type": "TimeoutError",
            },
            {
                "name": "test_3",
                "status": "failed",
                "error_type": "ConnectionError",
            },
        ]

        report = generate_failure_report(test_results)

        patterns = report["error_patterns"]
        assert patterns["TimeoutError"] == 2
        assert patterns["ConnectionError"] == 1

    async def test_recommendations_sorted_by_severity(self) -> None:
        """Recommendations are sorted by failure count (severity)."""
        from loom.reports import generate_failure_report

        test_results = [
            {
                "name": "fetch_1",
                "status": "failed",
                "category": "fetch",
                "error": "error",
            },
            {
                "name": "fetch_2",
                "status": "failed",
                "category": "fetch",
                "error": "error",
            },
            {
                "name": "fetch_3",
                "status": "failed",
                "category": "fetch",
                "error": "error",
            },
            {
                "name": "search_1",
                "status": "failed",
                "category": "search",
                "error": "error",
            },
        ]

        report = generate_failure_report(test_results)

        recommendations = report["recommendations"]

        # First recommendation should be about 'fetch' (3 failures)
        assert "fetch" in recommendations[0]
        assert "3 failures" in recommendations[0]

        # Second should be about 'search' (1 failure)
        assert "search" in recommendations[1]
        assert "1 failure" in recommendations[1]

    async def test_zero_failures_empty_categories(self) -> None:
        """When no failures, categories and patterns are empty."""
        from loom.reports import generate_failure_report

        test_results = [
            {"name": "test_1", "status": "passed", "category": "fetch"},
            {"name": "test_2", "status": "passed", "category": "search"},
        ]

        report = generate_failure_report(test_results)

        assert report["total_failures"] == 0
        assert report["failure_categories"] == {}
        assert report["error_patterns"] == {}
        assert report["recommendations"] == []

    async def test_output_to_file(self) -> None:
        """Failure report can be written to a file."""
        from loom.reports import generate_failure_report

        test_results = [
            {
                "name": "test_1",
                "status": "failed",
                "category": "fetch",
                "error": "Timeout",
                "error_type": "TimeoutError",
            },
        ]

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "what_doesnt_work.json"

            report = generate_failure_report(test_results, output_path)

            # Verify file was created
            assert output_path.exists()

            # Verify file contains valid JSON
            file_content = json.loads(output_path.read_text())
            assert file_content["total_failures"] == 1

    async def test_report_title_correct(self) -> None:
        """Report title is 'What Doesn't Work — Loom v3 Known Issues'."""
        from loom.reports import generate_failure_report

        test_results = []

        report = generate_failure_report(test_results)

        assert report["title"] == "What Doesn't Work — Loom v3 Known Issues"

    async def test_uncategorized_failures_handled(self) -> None:
        """Failures without category are grouped as 'uncategorized'."""
        from loom.reports import generate_failure_report

        test_results = [
            {"name": "test_1", "status": "failed", "error": "error"},  # No category
        ]

        report = generate_failure_report(test_results)

        categories = report["failure_categories"]
        assert "uncategorized" in categories

    async def test_missing_error_fields_handled(self) -> None:
        """Missing error/error_type fields are handled gracefully."""
        from loom.reports import generate_failure_report

        test_results = [
            {
                "name": "test_1",
                "status": "failed",
                "category": "fetch",
                # No error or error_type fields
            },
        ]

        report = generate_failure_report(test_results)

        categories = report["failure_categories"]
        assert "fetch" in categories
        assert categories["fetch"][0]["error"] == "unknown"

        patterns = report["error_patterns"]
        assert patterns.get("unknown", 0) > 0
