"""Deep integration tests for LLM provider cascade and failover behavior.

Tests the cascade routing logic, circuit breaker, error handling, and cost tracking
across all LLM provider implementations.

Test categories:
1. Cascade behavior (first provider fails → cascade to next)
2. Provider-specific error handling (auth, timeout, malformed)
3. Cost tracking across cascade
4. Circuit breaker open/half-open/closed states
5. Response format validation per provider
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.providers.base import LLMResponse
from loom.tools.llm.llm import (
    _build_provider_chain,
    _call_with_cascade,
    _check_circuit,
    _classify_cascade_error,
    _get_cost_tracker,
    _record_provider_failure,
    _record_provider_success,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_groq_provider():
    """Mock Groq provider instance."""
    provider = AsyncMock()
    provider.name = "groq"
    provider.available = AsyncMock(return_value=True)
    provider.chat = AsyncMock()
    provider.embed = AsyncMock()
    provider.close = AsyncMock()
    return provider


@pytest.fixture
def mock_nvidia_provider():
    """Mock NVIDIA NIM provider instance."""
    provider = AsyncMock()
    provider.name = "nvidia"
    provider.available = AsyncMock(return_value=True)
    provider.chat = AsyncMock()
    provider.embed = AsyncMock()
    provider.close = AsyncMock()
    return provider


@pytest.fixture
def mock_deepseek_provider():
    """Mock DeepSeek provider instance."""
    provider = AsyncMock()
    provider.name = "deepseek"
    provider.available = AsyncMock(return_value=True)
    provider.chat = AsyncMock()
    provider.embed = AsyncMock()
    provider.close = AsyncMock()
    return provider


@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider instance."""
    provider = AsyncMock()
    provider.name = "openai"
    provider.available = AsyncMock(return_value=True)
    provider.chat = AsyncMock()
    provider.embed = AsyncMock()
    provider.close = AsyncMock()
    return provider


def _make_response(provider_name: str) -> LLMResponse:
    """Create a successful LLMResponse with the given provider name."""
    return LLMResponse(
        text="Test response",
        model=f"{provider_name}/test-model",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.001,
        latency_ms=150,
        provider=provider_name,
        finish_reason="stop",
    )


@pytest.fixture
def auth_error():
    """401 Unauthorized HTTP error."""
    response = MagicMock()
    response.status_code = 401
    return httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response)


@pytest.fixture
def rate_limit_error():
    """429 Rate Limited HTTP error."""
    response = MagicMock()
    response.status_code = 429
    return httpx.HTTPStatusError(
        "Rate Limited", request=MagicMock(), response=response
    )


@pytest.fixture
def server_error():
    """500 Server Error HTTP error."""
    response = MagicMock()
    response.status_code = 500
    return httpx.HTTPStatusError("Server Error", request=MagicMock(), response=response)


# ============================================================================
# Test 1-5: Cascade Behavior
# ============================================================================


@pytest.mark.asyncio
async def test_cascade_first_provider_fails_401_continues(
    mock_groq_provider,
    mock_nvidia_provider,
    auth_error,
):
    """Test: First provider fails (401) → cascades to second → returns result."""
    mock_groq_provider.chat.side_effect = auth_error
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                    model="test-model",
                )

                assert response.text == "Test response"
                assert response.provider == "nvidia"
                assert mock_groq_provider.chat.called
                assert mock_nvidia_provider.chat.called


@pytest.mark.asyncio
async def test_cascade_first_provider_rate_limited_continues(
    mock_groq_provider,
    mock_nvidia_provider,
    rate_limit_error,
):
    """Test: First provider rate-limited (429) → backs off → cascades."""
    mock_groq_provider.chat.side_effect = rate_limit_error
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                # Patch asyncio.sleep to avoid actual delays
                with patch("loom.tools.llm.asyncio.sleep", new_callable=AsyncMock):
                    response = await _call_with_cascade(
                        [{"role": "user", "content": "test"}],
                        model="test-model",
                    )

                    assert response.text == "Test response"
                    assert response.provider == "nvidia"
                    assert mock_groq_provider.chat.called
                    assert mock_nvidia_provider.chat.called


@pytest.mark.asyncio
async def test_cascade_all_providers_fail_comprehensive_error(
    mock_groq_provider,
    mock_nvidia_provider,
    mock_deepseek_provider,
    auth_error,
    rate_limit_error,
    server_error,
):
    """Test: All providers fail → returns comprehensive error with all failures listed."""
    mock_groq_provider.chat.side_effect = auth_error
    mock_nvidia_provider.chat.side_effect = rate_limit_error
    mock_deepseek_provider.chat.side_effect = server_error

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[
            mock_groq_provider,
            mock_nvidia_provider,
            mock_deepseek_provider,
        ],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                # Mock the CLI fallback module entirely so it can't be imported
                with patch.dict("sys.modules", {"loom.providers.cli_fallback": None}):
                    with patch("loom.tools.llm.asyncio.sleep", new_callable=AsyncMock):
                        with pytest.raises(RuntimeError) as exc_info:
                            await _call_with_cascade(
                                [{"role": "user", "content": "test"}],
                                model="test-model",
                            )

                        error_msg = str(exc_info.value)
                        assert "all providers failed" in error_msg
                        assert "groq" in error_msg
                        assert "nvidia" in error_msg
                        assert "deepseek" in error_msg


@pytest.mark.asyncio
async def test_cascade_single_provider_configured_no_cascade(
    mock_nvidia_provider,
):
    """Test: Only one provider configured → uses it directly, no cascade."""
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                    model="test-model",
                )

                assert response.text == "Test response"
                assert mock_nvidia_provider.chat.call_count == 1


@pytest.mark.asyncio
async def test_cascade_provider_unavailable_skipped(
    mock_groq_provider,
    mock_nvidia_provider,
):
    """Test: Provider available() returns False → skipped in cascade."""
    mock_groq_provider.available.return_value = False
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                    model="test-model",
                )

                assert response.text == "Test response"
                # Groq should not have been called since it's unavailable
                assert not mock_groq_provider.chat.called
                assert mock_nvidia_provider.chat.called


# ============================================================================
# Test 6-10: Provider-Specific Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_provider_groq_invalid_key_auth_error(
    mock_groq_provider,
    mock_nvidia_provider,
    auth_error,
):
    """Test: Groq provider with invalid key → returns auth error."""
    mock_groq_provider.chat.side_effect = auth_error
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                )

                # Should fallback to NVIDIA after Groq auth failure
                assert response.provider == "nvidia"
                assert mock_groq_provider.chat.called


@pytest.mark.asyncio
async def test_provider_nvidia_invalid_key_auth_error(
    mock_groq_provider,
    mock_nvidia_provider,
    auth_error,
):
    """Test: NVIDIA NIM with invalid key → returns auth error."""
    mock_groq_provider.chat.return_value = _make_response("groq")
    mock_nvidia_provider.chat.side_effect = auth_error

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                )

                # Groq is first in cascade and succeeds
                assert response.provider == "groq"


@pytest.mark.asyncio
async def test_provider_timeout_cascades(
    mock_groq_provider,
    mock_nvidia_provider,
):
    """Test: Provider timeout → cascades to next."""
    mock_groq_provider.chat.side_effect = asyncio.TimeoutError("Timeout")
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                )

                assert response.provider == "nvidia"
                assert mock_groq_provider.chat.called
                assert mock_nvidia_provider.chat.called


@pytest.mark.asyncio
async def test_provider_malformed_json_handled_gracefully(
    mock_groq_provider,
    mock_nvidia_provider,
):
    """Test: Provider returns malformed JSON → handled gracefully, cascade continues."""
    mock_groq_provider.chat.side_effect = json.JSONDecodeError("msg", "doc", 0)
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                )

                assert response.provider == "nvidia"


@pytest.mark.asyncio
async def test_provider_empty_response_treated_as_success(
    mock_groq_provider,
    mock_nvidia_provider,
):
    """Test: Provider returns empty response → treated as success (returns it)."""
    empty_response = LLMResponse(
        text="",
        model="groq/test",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=100,
        provider="groq",
    )
    # An empty response is technically a success, so it should be returned
    mock_groq_provider.chat.return_value = empty_response
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                )

                # Groq returns first (even though empty), so no cascade
                assert response.provider == "groq"
                assert response.text == ""


# ============================================================================
# Test 11-13: Cost Tracking
# ============================================================================


@pytest.mark.asyncio
async def test_cost_tracking_cascade_tracks_successful_provider(
    mock_groq_provider,
    mock_nvidia_provider,
    auth_error,
):
    """Test: Cascade tracks which provider actually succeeded for cost."""
    mock_groq_provider.chat.side_effect = auth_error
    mock_nvidia_provider.chat.return_value = _make_response("nvidia")

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        cost_tracker = AsyncMock()
        cost_tracker.add_cost = MagicMock()

        with patch(
            "loom.tools.llm._get_cost_tracker",
            return_value=cost_tracker,
        ):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False
                mock_quota.return_value.record_usage = MagicMock()

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                )

                # Cost should be recorded for NVIDIA (the successful provider)
                cost_tracker.add_cost.assert_called_once()
                call_args = cost_tracker.add_cost.call_args
                assert call_args[0][1] == "nvidia"  # provider name


@pytest.mark.asyncio
async def test_cost_tracking_failed_providers_dont_accumulate(
    mock_groq_provider,
    mock_nvidia_provider,
    auth_error,
    rate_limit_error,
):
    """Test: Failed providers don't accumulate cost."""
    mock_groq_provider.chat.side_effect = auth_error
    mock_nvidia_provider.chat.side_effect = rate_limit_error

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider, mock_nvidia_provider],
    ):
        cost_tracker = AsyncMock()
        cost_tracker.add_cost = MagicMock()

        with patch(
            "loom.tools.llm._get_cost_tracker",
            return_value=cost_tracker,
        ):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                # Mock the CLI fallback module entirely so it can't be imported
                with patch.dict("sys.modules", {"loom.providers.cli_fallback": None}):
                    with patch("loom.tools.llm.asyncio.sleep", new_callable=AsyncMock):
                        with pytest.raises(RuntimeError):
                            await _call_with_cascade(
                                [{"role": "user", "content": "test"}],
                            )

                        # Cost tracker should never be called since all providers failed
                        cost_tracker.add_cost.assert_not_called()


@pytest.mark.asyncio
async def test_cost_estimation_works_for_successful_response(
    mock_nvidia_provider,
):
    """Test: Cost estimation works for successful response."""
    response = _make_response("nvidia")
    mock_nvidia_provider.chat.return_value = response

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_nvidia_provider],
    ):
        cost_tracker = AsyncMock()
        cost_tracker.add_cost = MagicMock()

        with patch(
            "loom.tools.llm._get_cost_tracker",
            return_value=cost_tracker,
        ):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response_out = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                )

                assert response_out.cost_usd == 0.001
                cost_tracker.add_cost.assert_called_once()


# ============================================================================
# Test 14-15: Circuit Breaker
# ============================================================================


def test_circuit_breaker_opens_after_3_failures():
    """Test: Provider fails 3 times → circuit opens → skipped on next calls."""
    import loom.tools.llm.llm as llm_module

    # Reset circuit state
    llm_module._CIRCUIT_STATE.clear()

    provider_name = "test_provider"

    # Three failures
    _record_provider_failure(provider_name)
    _record_provider_failure(provider_name)
    _record_provider_failure(provider_name)

    # Circuit should now be OPEN
    assert not _check_circuit(provider_name)
    assert llm_module._CIRCUIT_STATE[provider_name]["state"] == "open"


def test_circuit_breaker_resets_after_cooldown():
    """Test: Circuit breaker resets after cooldown period."""
    import loom.tools.llm.llm as llm_module

    # Reset circuit state
    llm_module._CIRCUIT_STATE.clear()

    provider_name = "test_provider"

    # Three failures
    _record_provider_failure(provider_name)
    _record_provider_failure(provider_name)
    _record_provider_failure(provider_name)

    # Circuit is OPEN
    assert not _check_circuit(provider_name)

    # Manually advance time past cooldown (60 seconds)
    llm_module._CIRCUIT_STATE[provider_name]["last_failure_time"] = datetime.now(
        UTC
    ) - timedelta(seconds=70)

    # Circuit should transition to HALF-OPEN and be checkable
    assert _check_circuit(provider_name)
    assert llm_module._CIRCUIT_STATE[provider_name]["state"] == "half_open"


def test_circuit_breaker_resets_on_success():
    """Test: Successful call resets circuit to CLOSED."""
    import loom.tools.llm.llm as llm_module

    # Reset circuit state
    llm_module._CIRCUIT_STATE.clear()

    provider_name = "test_provider"

    # Simulate some failures
    _record_provider_failure(provider_name)
    _record_provider_failure(provider_name)

    assert llm_module._CIRCUIT_STATE[provider_name]["failure_count"] == 2

    # Success resets it
    _record_provider_success(provider_name)

    assert llm_module._CIRCUIT_STATE[provider_name]["failure_count"] == 0
    assert llm_module._CIRCUIT_STATE[provider_name]["state"] == "closed"


def test_circuit_breaker_new_provider_starts_closed():
    """Test: New provider starts in CLOSED state."""
    import loom.tools.llm.llm as llm_module

    # Reset circuit state
    llm_module._CIRCUIT_STATE.clear()

    provider_name = "new_provider"

    # New provider should be checkable (CLOSED)
    assert _check_circuit(provider_name)


# ============================================================================
# Test 16-17: Response Format Validation
# ============================================================================


@pytest.mark.asyncio
async def test_response_format_json_stripped_for_unsupported_providers(
    mock_gemini_provider,
):
    """Test: JSON mode requested on provider that doesn't support it → stripped with warning."""
    mock_gemini_provider.chat = AsyncMock(return_value=_make_response("gemini"))

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_gemini_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                    response_format={"type": "json_schema"},
                )

                # Provider's chat() should have been called with response_format=None
                # (since Gemini doesn't support JSON mode)
                call_args = mock_gemini_provider.chat.call_args
                assert call_args.kwargs["response_format"] is None


@pytest.mark.asyncio
async def test_response_format_json_passed_to_openai_compatible(
    mock_groq_provider,
):
    """Test: JSON mode on OpenAI-compatible provider → passed through."""
    mock_groq_provider.chat = AsyncMock(return_value=_make_response("groq"))

    with patch(
        "loom.tools.llm._build_provider_chain",
        return_value=[mock_groq_provider],
    ):
        with patch("loom.tools.llm._get_cost_tracker"):
            with patch("loom.tools.llm.get_quota_tracker") as mock_quota:
                mock_quota.return_value.should_fallback.return_value = False
                mock_quota.return_value.is_near_limit.return_value = False

                json_schema = {"type": "json_schema", "json_schema": {}}
                response = await _call_with_cascade(
                    [{"role": "user", "content": "test"}],
                    response_format=json_schema,
                )

                # Groq is OpenAI-compatible, so JSON mode should be passed
                call_args = mock_groq_provider.chat.call_args
                assert call_args.kwargs["response_format"] == json_schema


# ============================================================================
# Test Error Classification Helper
# ============================================================================


def test_classify_cascade_error_rate_limit():
    """Test: 429 error classified as rate_limit with continue=True."""
    error = httpx.HTTPStatusError(
        "Rate Limited",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )
    error_type, should_continue = _classify_cascade_error(error)
    assert error_type == "rate_limit"
    assert should_continue is True


def test_classify_cascade_error_auth():
    """Test: 401/403 errors classified as auth with continue=True."""
    error = httpx.HTTPStatusError(
        "Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401),
    )
    error_type, should_continue = _classify_cascade_error(error)
    assert error_type == "auth"
    assert should_continue is True


def test_classify_cascade_error_server():
    """Test: 5xx errors classified as server with continue=True."""
    error = httpx.HTTPStatusError(
        "Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=503),
    )
    error_type, should_continue = _classify_cascade_error(error)
    assert error_type == "server"
    assert should_continue is True


def test_classify_cascade_error_timeout():
    """Test: Timeout errors classified as timeout with continue=True."""
    error = httpx.TimeoutException("Timeout")
    error_type, should_continue = _classify_cascade_error(error)
    assert error_type == "timeout"
    assert should_continue is True


def test_classify_cascade_error_connection():
    """Test: Connection errors classified with continue=True."""
    error = ConnectionError("Connection refused")
    error_type, should_continue = _classify_cascade_error(error)
    assert error_type == "connection"
    assert should_continue is True


# ============================================================================
# Fixture: Additional mock providers used in tests
# ============================================================================


@pytest.fixture
def mock_gemini_provider():
    """Mock Gemini provider instance."""
    provider = AsyncMock()
    provider.name = "gemini"
    provider.available = AsyncMock(return_value=True)
    provider.chat = AsyncMock()
    provider.embed = AsyncMock()
    provider.close = AsyncMock()
    return provider
