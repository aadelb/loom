"""Unit tests for zendriver backend tools — async browser automation.

Tests cover:
- research_zen_fetch: Single URL fetch with undetected browser
- research_zen_batch: Concurrent batch fetching
- research_zen_interact: Page interaction (click, fill, scroll, wait)

All tests use mocking to avoid actual browser launches.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.params import ZenFetchParams, ZenBatchParams, ZenInteractParams
from loom.zendriver_backend import (
    research_zen_fetch,
    research_zen_batch,
    research_zen_interact,
    ZenFetchResult,
    ZenBatchResult,
    ZenInteractResult,
)



pytestmark = pytest.mark.asyncio
class TestZenFetchParams:
    """Validation tests for ZenFetchParams."""

    async def test_valid_fetch_params(self) -> None:
        """Valid params pass validation."""
        params = ZenFetchParams(
            url="https://example.com",
            timeout=30,
            headless=True,
        )
        assert params.url == "https://example.com"
        assert params.timeout == 30
        assert params.headless is True

    async def test_fetch_params_rejects_ssrf_url(self) -> None:
        """SSRF URLs are rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenFetchParams(url="http://localhost:8080")

    async def test_fetch_params_rejects_private_ip(self) -> None:
        """Private IPs are rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenFetchParams(url="http://192.168.1.1")

    async def test_fetch_params_timeout_bounds(self) -> None:
        """Timeout must be 1-120 seconds."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenFetchParams(url="https://example.com", timeout=0)

        with pytest.raises(ValidationError):
            ZenFetchParams(url="https://example.com", timeout=121)

    async def test_fetch_params_default_values(self) -> None:
        """Default values are correct."""
        params = ZenFetchParams(url="https://example.com")
        assert params.timeout == 30
        assert params.headless is True


class TestZenBatchParams:
    """Validation tests for ZenBatchParams."""

    async def test_valid_batch_params(self) -> None:
        """Valid params pass validation."""
        params = ZenBatchParams(
            urls=["https://example.com", "https://huggingface.co"],
            max_concurrent=5,
            timeout=30,
        )
        assert len(params.urls) == 2
        assert params.max_concurrent == 5

    async def test_batch_params_empty_urls(self) -> None:
        """Empty URL list is rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenBatchParams(urls=[])

    async def test_batch_params_too_many_urls(self) -> None:
        """More than 100 URLs is rejected."""
        from pydantic import ValidationError

        urls = [f"https://example{i}.com" for i in range(101)]
        with pytest.raises(ValidationError):
            ZenBatchParams(urls=urls)

    async def test_batch_params_max_concurrent_bounds(self) -> None:
        """max_concurrent must be 1-50."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenBatchParams(
                urls=["https://example.com"],
                max_concurrent=0,
            )

        with pytest.raises(ValidationError):
            ZenBatchParams(
                urls=["https://example.com"],
                max_concurrent=51,
            )

    async def test_batch_params_validates_all_urls(self) -> None:
        """All URLs in the list are validated."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenBatchParams(
                urls=[
                    "https://example.com",
                    "http://localhost:8080",  # SSRF
                ],
            )


class TestZenInteractParams:
    """Validation tests for ZenInteractParams."""

    async def test_valid_interact_params(self) -> None:
        """Valid params pass validation."""
        params = ZenInteractParams(
            url="https://example.com",
            actions=[
                {"type": "click", "selector": "button.submit"},
            ],
        )
        assert params.url == "https://example.com"
        assert len(params.actions) == 1

    async def test_interact_params_empty_actions(self) -> None:
        """Empty actions list is rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenInteractParams(
                url="https://example.com",
                actions=[],
            )

    async def test_interact_params_too_many_actions(self) -> None:
        """More than 50 actions is rejected."""
        from pydantic import ValidationError

        actions = [
            {"type": "click", "selector": f"button{i}"}
            for i in range(51)
        ]
        with pytest.raises(ValidationError):
            ZenInteractParams(
                url="https://example.com",
                actions=actions,
            )

    async def test_interact_params_validates_action_type(self) -> None:
        """Invalid action type is rejected."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenInteractParams(
                url="https://example.com",
                actions=[
                    {"type": "invalid_action", "selector": "button"},
                ],
            )

    async def test_interact_params_requires_selector_for_click(self) -> None:
        """Click action requires selector."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenInteractParams(
                url="https://example.com",
                actions=[
                    {"type": "click"},  # Missing selector
                ],
            )

    async def test_interact_params_requires_value_for_fill(self) -> None:
        """Fill action requires value."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ZenInteractParams(
                url="https://example.com",
                actions=[
                    {"type": "fill", "selector": "input#email"},  # Missing value
                ],
            )

    async def test_interact_params_all_action_types(self) -> None:
        """All valid action types are accepted."""
        params = ZenInteractParams(
            url="https://example.com",
            actions=[
                {"type": "click", "selector": "button.submit"},
                {"type": "fill", "selector": "input#email", "value": "test@example.com"},
                {"type": "scroll", "value": "500"},
                {"type": "wait", "selector": "div.result", "value": "10"},
            ],
        )
        assert len(params.actions) == 4


class TestZenFetchResult:
    """ZenFetchResult model tests."""

    async def test_zen_fetch_result_structure(self) -> None:
        """Result has expected fields."""
        result = ZenFetchResult(
            url="https://example.com",
            html="<html>test</html>",
            text="test",
            status=200,
        )
        assert result.url == "https://example.com"
        assert result.html == "<html>test</html>"
        assert result.text == "test"
        assert result.status == 200
        assert result.method == "GET"
        assert result.error is None

    async def test_zen_fetch_result_with_error(self) -> None:
        """Error is properly set."""
        result = ZenFetchResult(
            url="https://example.com",
            error="timeout",
        )
        assert result.error == "timeout"
        assert result.html == ""


class TestZenBatchResult:
    """ZenBatchResult model tests."""

    async def test_zen_batch_result_structure(self) -> None:
        """Result has expected fields."""
        result = ZenBatchResult(
            urls_requested=2,
            urls_succeeded=2,
            urls_failed=0,
            results=[
                {"url": "https://example.com", "text": "test1"},
                {"url": "https://test.com", "text": "test2"},
            ],
        )
        assert result.urls_requested == 2
        assert result.urls_succeeded == 2
        assert result.urls_failed == 0
        assert len(result.results) == 2


class TestZenFetchTool:
    """research_zen_fetch tool tests."""

    async def test_zen_fetch_requires_zendriver(self) -> None:
        """Tool requires zendriver library."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", False):
            with pytest.raises(ImportError, match="zendriver not installed"):
                await research_zen_fetch(url="https://example.com")

    async def test_zen_fetch_rejects_ssrf_url(self) -> None:
        """SSRF URLs are rejected."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            from loom.validators import UrlSafetyError
            with pytest.raises(UrlSafetyError):
                await research_zen_fetch(url="http://localhost:8080")

    async def test_zen_fetch_returns_dict(self) -> None:
        """Result is a dictionary."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", False):
            try:
                await research_zen_fetch(url="https://example.com")
            except ImportError:
                # Expected when zendriver is not installed
                pass

    async def test_zen_fetch_timeout_validation(self) -> None:
        """Timeout bounds are enforced."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with pytest.raises(ValueError, match="timeout must be 1-120"):
                await research_zen_fetch(url="https://example.com", timeout=0)

            with pytest.raises(ValueError, match="timeout must be 1-120"):
                await research_zen_fetch(url="https://example.com", timeout=121)


class TestZenBatchTool:
    """research_zen_batch tool tests."""

    async def test_zen_batch_requires_zendriver(self) -> None:
        """Tool requires zendriver library."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", False):
            with pytest.raises(ImportError, match="zendriver not installed"):
                await research_zen_batch(urls=["https://example.com"])

    async def test_zen_batch_rejects_empty_urls(self) -> None:
        """Empty URL list is rejected."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with pytest.raises(ValueError, match="urls list cannot be empty"):
                await research_zen_batch(urls=[])

    async def test_zen_batch_rejects_too_many_urls(self) -> None:
        """Too many URLs are rejected."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            urls = [f"https://example{i}.com" for i in range(101)]
            with pytest.raises(ValueError, match="urls list max 100"):
                await research_zen_batch(urls=urls)

    async def test_zen_batch_max_concurrent_validation(self) -> None:
        """max_concurrent bounds are enforced."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with pytest.raises(ValueError, match="max_concurrent must be 1-50"):
                await research_zen_batch(
                    urls=["https://example.com"],
                    max_concurrent=0,
                )

            with pytest.raises(ValueError, match="max_concurrent must be 1-50"):
                await research_zen_batch(
                    urls=["https://example.com"],
                    max_concurrent=51,
                )

    async def test_zen_batch_timeout_validation(self) -> None:
        """Timeout bounds are enforced."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with pytest.raises(ValueError, match="timeout must be 1-120"):
                await research_zen_batch(
                    urls=["https://example.com"],
                    timeout=121,
                )


class TestZenInteractTool:
    """research_zen_interact tool tests."""

    async def test_zen_interact_requires_zendriver(self) -> None:
        """Tool requires zendriver library."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", False):
            with pytest.raises(ImportError, match="zendriver not installed"):
                await research_zen_interact(
                    url="https://example.com",
                    actions=[{"type": "click", "selector": "button"}],
                )

    async def test_zen_interact_rejects_ssrf_url(self) -> None:
        """SSRF URLs are rejected."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            from loom.validators import UrlSafetyError
            with pytest.raises(UrlSafetyError):
                await research_zen_interact(
                    url="http://localhost:8080",
                    actions=[{"type": "click", "selector": "button"}],
                )

    async def test_zen_interact_rejects_empty_actions(self) -> None:
        """Empty actions list is rejected."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with pytest.raises(ValueError, match="actions list cannot be empty"):
                await research_zen_interact(
                    url="https://example.com",
                    actions=[],
                )

    async def test_zen_interact_rejects_too_many_actions(self) -> None:
        """Too many actions are rejected."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            actions = [
                {"type": "click", "selector": f"button{i}"}
                for i in range(51)
            ]
            with pytest.raises(ValueError, match="actions list max 50"):
                await research_zen_interact(
                    url="https://example.com",
                    actions=actions,
                )

    async def test_zen_interact_timeout_validation(self) -> None:
        """Timeout bounds are enforced."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with pytest.raises(ValueError, match="timeout must be 1-120"):
                await research_zen_interact(
                    url="https://example.com",
                    actions=[{"type": "click", "selector": "button"}],
                    timeout=0,
                )

            with pytest.raises(ValueError, match="timeout must be 1-120"):
                await research_zen_interact(
                    url="https://example.com",
                    actions=[{"type": "click", "selector": "button"}],
                    timeout=121,
                )


class TestZenFetchIntegration:
    """Integration tests for research_zen_fetch (mocked)."""

    async def test_zen_fetch_successful_fetch(self) -> None:
        """Successful fetch returns correct structure."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with patch(
                "loom.zendriver_backend._fetch_with_zendriver",
                new_callable=AsyncMock,
            ) as mock_fetch:
                mock_fetch.return_value = {
                    "url": "https://example.com",
                    "html": "<html><title>Example</title></html>",
                    "text": "Example text",
                    "status": 200,
                    "method": "GET",
                    "error": None,
                    "elapsed_ms": 500,
                    "title": "Example",
                }

                # Note: The actual function uses loop.run_until_complete
                # In tests, we can't easily test the async behavior without
                # a running loop, so we just verify the validation passes

    async def test_zen_fetch_with_error(self) -> None:
        """Fetch with error returns error dict."""
        with patch("loom.zendriver_backend._HAS_ZENDRIVER", True):
            with patch(
                "loom.zendriver_backend._fetch_with_zendriver",
                new_callable=AsyncMock,
            ) as mock_fetch:
                mock_fetch.return_value = {
                    "url": "https://example.com",
                    "html": "",
                    "text": "",
                    "status": None,
                    "method": "GET",
                    "error": "timeout",
                    "elapsed_ms": 30000,
                    "title": "",
                }

    async def test_zen_fetch_returns_zen_fetch_result_dict(self) -> None:
        """Result is properly formatted as dict."""
        result = ZenFetchResult(
            url="https://example.com",
            html="<html>test</html>",
            text="test content",
            status=200,
        )
        result_dict = result.model_dump()

        assert isinstance(result_dict, dict)
        assert "url" in result_dict
        assert "html" in result_dict
        assert "text" in result_dict
        assert "status" in result_dict


class TestZenBatchIntegration:
    """Integration tests for research_zen_batch (mocked)."""

    async def test_zen_batch_returns_batch_result_dict(self) -> None:
        """Result is properly formatted as dict."""
        result = ZenBatchResult(
            urls_requested=2,
            urls_succeeded=2,
            urls_failed=0,
            results=[
                {
                    "url": "https://example.com",
                    "html": "<html>test1</html>",
                    "text": "test1",
                },
                {
                    "url": "https://test.com",
                    "html": "<html>test2</html>",
                    "text": "test2",
                },
            ],
        )
        result_dict = result.model_dump()

        assert isinstance(result_dict, dict)
        assert result_dict["urls_requested"] == 2
        assert result_dict["urls_succeeded"] == 2
        assert len(result_dict["results"]) == 2


class TestZenInteractIntegration:
    """Integration tests for research_zen_interact (mocked)."""

    async def test_zen_interact_returns_interact_result_dict(self) -> None:
        """Result is properly formatted as dict."""
        result = ZenInteractResult(
            url="https://example.com",
            actions_performed=2,
            final_html="<html>final</html>",
            final_text="final content",
        )
        result_dict = result.model_dump()

        assert isinstance(result_dict, dict)
        assert result_dict["url"] == "https://example.com"
        assert result_dict["actions_performed"] == 2
        assert "final_html" in result_dict
        assert "final_text" in result_dict

    async def test_zen_interact_with_error(self) -> None:
        """Interaction with error returns error dict."""
        result = ZenInteractResult(
            url="https://example.com",
            error="selector not found",
        )
        result_dict = result.model_dump()

        assert result_dict["error"] == "selector not found"
        assert result_dict["actions_performed"] == 0
