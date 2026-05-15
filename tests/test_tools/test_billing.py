"""Tests for billing and usage tracking tools."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_billing_module():
    sys.modules.pop("loom.tools.infrastructure.billing", None)
    yield
    sys.modules.pop("loom.tools.infrastructure.billing", None)


@pytest.mark.asyncio
class TestResearchUsageReport:
    async def test_no_logs_directory(self):
        """Test handling when logs directory doesn't exist."""
        with patch("loom.tools.infrastructure.billing.Path") as mock_path_cls:
            # Create a mock that returns itself for all / operations
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path.__truediv__.return_value = mock_path
            mock_path_cls.home.return_value = mock_path

            from loom.tools.infrastructure.billing import research_usage_report

            result = await research_usage_report(days=7)

            assert result["total_cost"] == 0.0
            assert result["calls_by_provider"] == {}
            assert result["calls_by_day"] == {}
            assert result["error"] == "no logs directory found"

    async def test_success_with_log_files(self):
        """Test successful usage report generation."""
        log_content = (
            '{"cost_usd": 0.05, "provider": "openai", "model": "gpt-4", "timestamp": "2024-01-15T10:00:00"}\n'
            '{"cost_usd": 0.03, "provider": "anthropic", "model": "claude-3", "timestamp": "2024-01-15T11:00:00"}\n'
            '{"cost_usd": 0.02, "provider": "openai", "model": "gpt-3.5", "timestamp": "2024-01-15T12:00:00"}\n'
        )

        with patch("loom.tools.infrastructure.billing.Path") as mock_path_cls, patch(
            "builtins.open",
            create=True,
        ) as mock_open:
            from datetime import datetime

            from loom.tools.infrastructure.billing import research_usage_report

            # Create mock file
            mock_stat_result = MagicMock()
            mock_stat_result.st_mtime = datetime.now().timestamp()

            # Setup mock Path instance that will be returned by Path.home()
            mock_cache_dir = MagicMock()
            mock_cache_dir.exists.return_value = True
            mock_cache_dir.__truediv__.return_value = mock_cache_dir

            # Setup glob to return mock files
            mock_file = MagicMock()
            mock_file.stat.return_value = mock_stat_result
            mock_file.name = "llm_cost_2024-01-15.json"
            mock_cache_dir.glob.return_value = [mock_file]

            # Path.home() returns the mock cache dir
            mock_path_cls.home.return_value = mock_cache_dir

            mock_open.return_value.__enter__.return_value = MagicMock(
                __iter__=lambda self: iter(log_content.split("\n")[:-1])
            )

            result = await research_usage_report(days=7)

            assert result["total_cost"] == 0.10
            assert result["total_calls"] == 3
            assert "openai" in result["calls_by_provider"]
            assert result["calls_by_provider"]["openai"]["count"] == 2
            assert result["calls_by_provider"]["anthropic"]["count"] == 1

    async def test_empty_log_file(self):
        """Test handling of empty log file."""
        with patch("pathlib.Path.home"), patch(
            "pathlib.Path.exists",
            return_value=True,
        ), patch("pathlib.Path.glob") as mock_glob, patch(
            "pathlib.Path.stat",
        ) as mock_stat, patch(
            "builtins.open",
            create=True,
        ) as mock_open:
            from datetime import datetime

            from loom.tools.infrastructure.billing import research_usage_report

            mock_stat_result = MagicMock()
            mock_stat_result.st_mtime = datetime.now().timestamp()
            mock_stat.return_value = mock_stat_result

            mock_file = MagicMock()
            mock_file.stat.return_value = mock_stat_result
            mock_file.name = "llm_cost_empty.json"
            mock_glob.return_value = [mock_file]

            mock_open.return_value.__enter__.return_value = MagicMock(
                __iter__=lambda self: iter([])
            )

            result = await research_usage_report(days=7)

            assert result["total_cost"] == 0.0
            assert result["total_calls"] == 0


@pytest.mark.asyncio
class TestResearchStripeBalance:
    async def test_missing_api_key(self):
        """Test returns error when STRIPE_LIVE_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.tools.infrastructure.billing import research_stripe_balance

            result = await research_stripe_balance()

            assert result["error"] == "STRIPE_LIVE_KEY environment variable not set"
            assert result["available"] == 0
            assert result["pending"] == 0

    async def test_success(self):
        """Test successful Stripe balance retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "available": [
                {
                    "currency": "usd",
                    "amount": 50000,
                }
            ],
            "pending": [
                {
                    "currency": "usd",
                    "amount": 25000,
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"STRIPE_LIVE_KEY": "sk_live_test"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.billing import research_stripe_balance

            result = await research_stripe_balance()

            assert "error" not in result
            assert result["available"] == 50000
            assert result["pending"] == 25000
            assert result["available_usd"] == 500.0
            assert result["pending_usd"] == 250.0

    async def test_http_error_401(self):
        """Test handling of 401 unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"STRIPE_LIVE_KEY": "invalid"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.billing import research_stripe_balance

            result = await research_stripe_balance()

            assert result["error"] == "Invalid STRIPE_LIVE_KEY"
            assert result["available"] == 0
            assert result["pending"] == 0

    async def test_http_error_500(self):
        """Test handling of 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"STRIPE_LIVE_KEY": "key"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.billing import research_stripe_balance

            result = await research_stripe_balance()

            assert "API error" in result["error"]
            assert result["available"] == 0

    async def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"STRIPE_LIVE_KEY": "key"}), patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.ConnectError("Network error"),
        ):
            from loom.tools.infrastructure.billing import research_stripe_balance

            result = await research_stripe_balance()

            assert "error" in result
            assert result["available"] == 0

    async def test_no_usd_currency(self):
        """Test handling when no USD currency in response."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "available": [
                {
                    "currency": "eur",
                    "amount": 50000,
                }
            ],
            "pending": [],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"STRIPE_LIVE_KEY": "sk_test"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.billing import research_stripe_balance

            result = await research_stripe_balance()

            assert result["available"] == 0
            assert result["pending"] == 0
