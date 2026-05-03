"""Unit tests for research_vercel_status — Vercel integration placeholder."""

from __future__ import annotations

import pytest

from loom.tools.vercel import research_vercel_status


pytestmark = pytest.mark.asyncio

class TestVercelStatus:
    """research_vercel_status returns placeholder integration status."""

    async def test_vercel_status_returns_dict(self) -> None:
        """Status returns a dictionary."""
        result = await research_vercel_status()

        assert isinstance(result, dict)

    async def test_vercel_status_not_implemented(self) -> None:
        """Status indicates tool is not yet implemented."""
        result = await research_vercel_status()

        assert result["status"] == "not_implemented"

    async def test_vercel_status_has_documentation_reference(self) -> None:
        """Status includes documentation URL."""
        result = await research_vercel_status()

        assert "documentation" in result
        assert "vercel.com/docs" in result["documentation"]

    async def test_vercel_status_has_api_reference(self) -> None:
        """Status includes API reference URL."""
        result = await research_vercel_status()

        assert "api_reference" in result
        assert "rest-api" in result["api_reference"]

    async def test_vercel_status_has_note(self) -> None:
        """Status includes explanatory note."""
        result = await research_vercel_status()

        assert "note" in result
        assert "CI/CD" in result["note"] or "Vercel" in result["note"]

    async def test_vercel_status_consistency(self) -> None:
        """Status returns consistent response across calls."""
        result1 = await research_vercel_status()
        result2 = await research_vercel_status()

        assert result1 == result2

    async def test_vercel_status_all_keys_are_strings(self) -> None:
        """All status response values are strings."""
        result = await research_vercel_status()

        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    async def test_vercel_status_no_sensitive_data(self) -> None:
        """Status response contains no sensitive data."""
        result = await research_vercel_status()

        # Check that no API keys or tokens are present
        response_text = " ".join(str(v) for v in result.values())
        assert "xoxb" not in response_text.lower()
        assert "apikey" not in response_text.lower()
        assert "secret" not in response_text.lower()
