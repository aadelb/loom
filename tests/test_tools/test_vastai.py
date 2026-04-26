"""Tests for Vast.ai research tools."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_vastai_module():
    sys.modules.pop("loom.tools.vastai", None)
    yield
    sys.modules.pop("loom.tools.vastai", None)


@pytest.mark.asyncio
class TestResearchVastaiSearch:
    async def test_missing_api_key(self):
        """Test returns error when VASTAI_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.tools.vastai import research_vastai_search

            result = await research_vastai_search()

            assert result["error"] == "VASTAI_API_KEY environment variable not set"
            assert result["results"] == []

    async def test_success(self):
        """Test successful GPU instance search."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "bundles": [
                    {
                        "id": "instance-1",
                        "gpu_name": "RTX 4090",
                        "price_per_hour": 0.85,
                        "ram_gb": 48,
                        "storage_gb": 1000,
                        "location": "US-West",
                    },
                    {
                        "id": "instance-2",
                        "gpu_name": "RTX 4090",
                        "price_per_hour": 0.90,
                        "ram_gb": 48,
                        "storage_gb": 500,
                        "location": "EU-Central",
                    },
                ]
            }
        )

        with patch.dict("os.environ", {"VASTAI_API_KEY": "test-key"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.vastai import research_vastai_search

            result = await research_vastai_search(gpu_type="RTX 4090", max_price=1.0, n=5)

            assert "error" not in result
            assert len(result["results"]) == 2
            assert result["results"][0]["gpu_name"] == "RTX 4090"
            assert result["results"][0]["price_per_hour"] == 0.85
            assert result["gpu_type"] == "RTX 4090"
            assert result["max_price"] == 1.0

    async def test_http_error_401(self):
        """Test handling of 401 unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"VASTAI_API_KEY": "invalid"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.vastai import research_vastai_search

            result = await research_vastai_search()

            assert result["error"] == "Invalid VASTAI_API_KEY"
            assert result["results"] == []

    async def test_http_error_500(self):
        """Test handling of 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"VASTAI_API_KEY": "key"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.vastai import research_vastai_search

            result = await research_vastai_search()

            assert "API error" in result["error"]
            assert result["results"] == []

    async def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"VASTAI_API_KEY": "key"}), patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.ConnectError("Network error"),
        ):
            from loom.tools.vastai import research_vastai_search

            result = await research_vastai_search()

            assert "error" in result
            assert result["results"] == []


@pytest.mark.asyncio
class TestResearchVastaiStatus:
    async def test_missing_api_key(self):
        """Test returns default values when VASTAI_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.tools.vastai import research_vastai_status

            result = await research_vastai_status()

            assert result["error"] == "VASTAI_API_KEY environment variable not set"
            assert result["balance"] == 0.0
            assert result["running_instances"] == 0

    async def test_success(self):
        """Test successful status retrieval."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "id": "user-123",
                "balance": 125.50,
                "instances": [
                    {"id": "instance-1", "status": "running"},
                    {"id": "instance-2", "status": "running"},
                ],
            }
        )

        with patch.dict("os.environ", {"VASTAI_API_KEY": "test-key"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.vastai import research_vastai_status

            result = await research_vastai_status()

            assert "error" not in result
            assert result["balance"] == 125.50
            assert result["running_instances"] == 2
            assert result["user_id"] == "user-123"

    async def test_http_error_401(self):
        """Test handling of 401 unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"VASTAI_API_KEY": "invalid"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.vastai import research_vastai_status

            result = await research_vastai_status()

            assert result["error"] == "Invalid VASTAI_API_KEY"
            assert result["balance"] == 0.0
            assert result["running_instances"] == 0

    async def test_http_error_500(self):
        """Test handling of 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"VASTAI_API_KEY": "key"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.vastai import research_vastai_status

            result = await research_vastai_status()

            assert "API error" in result["error"]
            assert result["balance"] == 0.0

    async def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"VASTAI_API_KEY": "key"}), patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.ConnectError("Network error"),
        ):
            from loom.tools.vastai import research_vastai_status

            result = await research_vastai_status()

            assert "error" in result
            assert result["balance"] == 0.0

    async def test_zero_balance_zero_instances(self):
        """Test status with zero balance and no running instances."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "id": "user-456",
                "balance": 0.0,
                "instances": [],
            }
        )

        with patch.dict("os.environ", {"VASTAI_API_KEY": "key"}), patch(
            "httpx.AsyncClient.get",
            return_value=mock_response,
        ):
            from loom.tools.vastai import research_vastai_status

            result = await research_vastai_status()

            assert result["balance"] == 0.0
            assert result["running_instances"] == 0
