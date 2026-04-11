"""Unit tests for OpenAIProvider."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("loom.providers.openai_provider")

from loom.providers.openai_provider import OpenAIProvider


@pytest.fixture
def clear_openai_key() -> None:
    """Clear OPENAI_API_KEY for testing."""
    old_val = os.environ.pop("OPENAI_API_KEY", None)
    yield
    if old_val:
        os.environ["OPENAI_API_KEY"] = old_val


class TestOpenAIProvider:
    """OpenAIProvider availability and basic tests."""

    def test_available_false_without_key(self, clear_openai_key: None) -> None:
        """available() returns False if OPENAI_API_KEY not set."""
        provider = OpenAIProvider()
        assert not provider.available()

    def test_available_true_with_key(self) -> None:
        """available() returns True if OPENAI_API_KEY is set."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        try:
            provider = OpenAIProvider()
            assert provider.available()
        finally:
            os.environ.pop("OPENAI_API_KEY", None)

    def test_provider_name(self) -> None:
        """Provider name is 'openai'."""
        provider = OpenAIProvider()
        assert provider.name == "openai"

    @pytest.mark.asyncio
    async def test_chat_requires_key(self, clear_openai_key: None) -> None:
        """chat() raises or returns error without API key."""
        os.environ.pop("OPENAI_API_KEY", None)
        provider = OpenAIProvider()

        with pytest.raises(Exception):
            await provider.chat(
                messages=[{"role": "user", "content": "test"}],
                timeout=5,
            )

    @pytest.mark.asyncio
    async def test_close_is_safe(self) -> None:
        """close() is safe to call even without initialization."""
        provider = OpenAIProvider()
        await provider.close()  # Should not raise
