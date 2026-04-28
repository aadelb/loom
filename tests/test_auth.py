"""Tests for Loom MCP bearer token authentication."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from loom.auth import ApiKeyVerifier


@pytest.mark.asyncio
async def test_no_key_set_allows_anonymous() -> None:
    """Without LOOM_API_KEY, verifier allows anonymous access with full scopes."""
    with patch.dict(os.environ, {}, clear=True):
        verifier = ApiKeyVerifier()
        token = await verifier.verify_token("any-token")

        assert token is not None
        assert token.token == "anonymous"
        assert token.client_id == "anonymous"
        assert token.scopes == ["*"]


@pytest.mark.asyncio
async def test_correct_key_accepted() -> None:
    """Matching API key is verified and returns AccessToken with api_key client_id."""
    api_key = "test-secret-key-12345"
    with patch.dict(os.environ, {"LOOM_API_KEY": api_key}):
        verifier = ApiKeyVerifier()
        token = await verifier.verify_token(api_key)

        assert token is not None
        assert token.token == api_key
        assert token.client_id == "api_key"
        assert token.scopes == ["*"]


@pytest.mark.asyncio
async def test_wrong_key_rejected() -> None:
    """Non-matching token returns None."""
    api_key = "test-secret-key-12345"
    wrong_token = "wrong-token"
    with patch.dict(os.environ, {"LOOM_API_KEY": api_key}):
        verifier = ApiKeyVerifier()
        token = await verifier.verify_token(wrong_token)

        assert token is None


@pytest.mark.asyncio
async def test_empty_token_rejected() -> None:
    """Empty token string is rejected when API key is set."""
    api_key = "test-secret-key-12345"
    with patch.dict(os.environ, {"LOOM_API_KEY": api_key}):
        verifier = ApiKeyVerifier()
        token = await verifier.verify_token("")

        assert token is None


@pytest.mark.asyncio
async def test_case_sensitive_key_match() -> None:
    """API key matching is case-sensitive."""
    api_key = "Test-Secret-KEY"
    wrong_case = "test-secret-key"
    with patch.dict(os.environ, {"LOOM_API_KEY": api_key}):
        verifier = ApiKeyVerifier()

        # Correct case should work
        token = await verifier.verify_token(api_key)
        assert token is not None

        # Wrong case should fail
        token = await verifier.verify_token(wrong_case)
        assert token is None


@pytest.mark.asyncio
async def test_whitespace_in_key() -> None:
    """Whitespace in token must match exactly."""
    api_key = "secret key with spaces"
    with patch.dict(os.environ, {"LOOM_API_KEY": api_key}):
        verifier = ApiKeyVerifier()

        # Exact match with spaces should work
        token = await verifier.verify_token(api_key)
        assert token is not None

        # Token without spaces should fail
        token = await verifier.verify_token("secretkeywithspaces")
        assert token is None


@pytest.mark.asyncio
async def test_multiple_instances_independent() -> None:
    """Multiple verifier instances read environment independently."""
    api_key_1 = "key-1"
    api_key_2 = "key-2"

    with patch.dict(os.environ, {"LOOM_API_KEY": api_key_1}):
        verifier1 = ApiKeyVerifier()

    with patch.dict(os.environ, {"LOOM_API_KEY": api_key_2}):
        verifier2 = ApiKeyVerifier()

    # Verify each uses its own key
    token1 = await verifier1.verify_token(api_key_1)
    assert token1 is not None

    token2 = await verifier2.verify_token(api_key_2)
    assert token2 is not None

    # Cross-verify should fail
    token1_wrong = await verifier1.verify_token(api_key_2)
    assert token1_wrong is None

    token2_wrong = await verifier2.verify_token(api_key_1)
    assert token2_wrong is None
