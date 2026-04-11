"""Unit tests for NvidiaNimProvider."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("loom.providers.nvidia_nim")

from loom.providers.nvidia_nim import NvidiaNimProvider


@pytest.fixture
def clear_nvidia_key() -> None:
    """Clear NVIDIA_NIM_API_KEY for testing."""
    old_val = os.environ.pop("NVIDIA_NIM_API_KEY", None)
    yield
    if old_val:
        os.environ["NVIDIA_NIM_API_KEY"] = old_val


class TestNvidiaNimProvider:
    """NvidiaNimProvider availability and basic tests."""

    def test_available_false_without_key(self, clear_nvidia_key: None) -> None:
        """available() returns False if NVIDIA_NIM_API_KEY not set."""
        provider = NvidiaNimProvider()
        assert not provider.available()

    def test_available_true_with_key(self) -> None:
        """available() returns True if NVIDIA_NIM_API_KEY is set."""
        os.environ["NVIDIA_NIM_API_KEY"] = "test-key"
        try:
            provider = NvidiaNimProvider()
            assert provider.available()
        finally:
            os.environ.pop("NVIDIA_NIM_API_KEY", None)

    def test_provider_name(self) -> None:
        """Provider name is 'nvidia'."""
        provider = NvidiaNimProvider()
        assert provider.name == "nvidia"

    @pytest.mark.asyncio
    async def test_chat_requires_key(self, clear_nvidia_key: None) -> None:
        """chat() raises or returns error without API key."""
        os.environ.pop("NVIDIA_NIM_API_KEY", None)
        provider = NvidiaNimProvider()

        # Should raise or return error response
        with pytest.raises(Exception):
            await provider.chat(
                messages=[{"role": "user", "content": "test"}],
                timeout=5,
            )

    @pytest.mark.asyncio
    async def test_close_is_safe(self) -> None:
        """close() is safe to call even without initialization."""
        provider = NvidiaNimProvider()
        await provider.close()  # Should not raise
