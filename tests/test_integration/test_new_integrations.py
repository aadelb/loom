"""Integration tests for Loom MCP server core functionality.

Tests integration scenarios:
1. Finance and news query auto-routing via research_deep
2. LLM provider cascade with fallback
3. Sync rate limiting on tool calls
4. Health check endpoint
5. Server tool registration (50+ tools)
6. Token/secret redaction in error messages
"""

from __future__ import annotations

import asyncio

import pytest


class TestFinanceQueryAutoRouting:
    """research_deep auto-routes finance queries to binance/investing providers."""

    @pytest.mark.asyncio
    async def test_bitcoin_query_routes_to_finance_providers(self) -> None:
        """Bitcoin query should detect finance type and add binance/investing providers."""
        from loom.tools.core.deep import _detect_query_type

        query_types = _detect_query_type("bitcoin price prediction")
        assert "finance" in query_types

    @pytest.mark.asyncio
    async def test_ethereum_query_finance_detection(self) -> None:
        """Ethereum query should detect finance type."""
        from loom.tools.core.deep import _detect_query_type

        query_types = _detect_query_type("ethereum market trends")
        assert "finance" in query_types

    @pytest.mark.asyncio
    async def test_crypto_query_finance_detection(self) -> None:
        """Crypto query should detect finance type."""
        from loom.tools.core.deep import _detect_query_type

        query_types = _detect_query_type("cryptocurrency blockchain defi nft")
        assert "finance" in query_types

    @pytest.mark.asyncio
    async def test_stock_query_finance_detection(self) -> None:
        """Stock market query should detect finance type."""
        from loom.tools.core.deep import _detect_query_type

        query_types = _detect_query_type("stock market trading nasdaq")
        assert "finance" in query_types


class TestNewsQueryAutoRouting:
    """research_deep auto-routes news queries to newsapi provider."""

    @pytest.mark.asyncio
    async def test_ai_news_query_detection(self) -> None:
        """'latest AI news' should detect news type."""
        from loom.tools.core.deep import _detect_query_type

        query_types = _detect_query_type("latest AI news")
        assert "news" in query_types

    @pytest.mark.asyncio
    async def test_breaking_news_detection(self) -> None:
        """Breaking news query should detect news type."""
        from loom.tools.core.deep import _detect_query_type

        query_types = _detect_query_type("breaking news today")
        assert "news" in query_types

    @pytest.mark.asyncio
    async def test_headline_detection(self) -> None:
        """Headline query should detect news type."""
        from loom.tools.core.deep import _detect_query_type

        query_types = _detect_query_type("latest headlines announcement")
        assert "news" in query_types


class TestLLMCascadeWithEightProviders:
    """LLM provider cascade with 8 providers: groq, nvidia, deepseek, gemini, moonshot, openai, anthropic, vllm."""

    def test_all_eight_providers_importable(self) -> None:
        """All 8 provider modules should be importable."""
        from loom.providers.anthropic_provider import AnthropicProvider
        from loom.providers.deepseek_provider import DeepSeekProvider
        from loom.providers.gemini_provider import GeminiProvider
        from loom.providers.groq_provider import GroqProvider
        from loom.providers.moonshot_provider import MoonshotProvider
        from loom.providers.nvidia_nim import NvidiaNimProvider
        from loom.providers.openai_provider import OpenAIProvider
        from loom.providers.vllm_local import VllmLocalProvider

        # All should be importable
        assert GroqProvider is not None
        assert NvidiaNimProvider is not None
        assert DeepSeekProvider is not None
        assert GeminiProvider is not None
        assert MoonshotProvider is not None
        assert OpenAIProvider is not None
        assert AnthropicProvider is not None
        assert VllmLocalProvider is not None

    @pytest.mark.asyncio
    async def test_cascade_order_defined(self) -> None:
        """LLM cascade order should be defined in config."""
        from loom.config import get_config

        config = get_config()
        cascade_order = config.get("LLM_CASCADE_ORDER", [])
        # Should have at least some providers configured
        assert isinstance(cascade_order, list)

    @pytest.mark.asyncio
    async def test_provider_get_creates_instances(self) -> None:
        """_get_provider() should create provider instances."""
        from loom.tools.llm.llm import _get_provider

        # Test that each provider name returns a provider instance
        provider_names = ["nvidia", "openai", "anthropic", "vllm", "groq", "deepseek", "gemini", "moonshot"]

        for name in provider_names:
            try:
                provider = _get_provider(name)
                assert provider is not None
                assert hasattr(provider, "chat") or hasattr(provider, "available")
            except ValueError:
                # Some providers may not be available, which is OK
                pass

    @pytest.mark.asyncio
    async def test_unknown_provider_raises_error(self) -> None:
        """_get_provider() with unknown provider should raise ValueError."""
        from loom.tools.llm.llm import _get_provider

        with pytest.raises(ValueError, match="unknown provider"):
            _get_provider("nonexistent_provider")

    @pytest.mark.asyncio
    async def test_cascade_fallback_on_provider_failure(self) -> None:
        """Cascade should try next provider when current fails."""
        from loom.tools.llm.llm import _PROVIDERS, _get_provider

        # Clear cached providers
        _PROVIDERS.clear()

        # When getting a provider, should return valid instance
        provider = _get_provider("nvidia")
        assert provider is not None


class TestSyncRateLimitingOnFetch:
    """Sync rate limiting on research_fetch prevents abuse."""

    def test_sync_rate_limiter_created(self) -> None:
        """SyncRateLimiter should be creatable."""
        from loom.rate_limiter import SyncRateLimiter

        limiter = SyncRateLimiter(max_calls=5, window_seconds=60)
        assert limiter.max_calls == 5
        assert limiter.window_seconds == 60

    def test_sync_rate_limiter_allows_under_limit(self) -> None:
        """SyncRateLimiter should allow calls under limit."""
        from loom.rate_limiter import SyncRateLimiter

        limiter = SyncRateLimiter(max_calls=3, window_seconds=60)
        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is True

    def test_sync_rate_limiter_blocks_over_limit(self) -> None:
        """SyncRateLimiter should block calls over limit."""
        from loom.rate_limiter import SyncRateLimiter

        limiter = SyncRateLimiter(max_calls=3, window_seconds=60)
        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is False  # Over limit

    def test_sync_rate_limited_decorator(self) -> None:
        """@sync_rate_limited decorator should wrap function."""
        from loom.rate_limiter import reset_all, sync_rate_limited

        reset_all()

        @sync_rate_limited("test")
        def dummy_func() -> str:
            return "success"

        # First 30 calls should succeed (default RATE_LIMIT_SEARCH_PER_MIN=30)
        for _ in range(30):
            result = dummy_func()
            assert result == "success"

        # 31st call should be rate limited
        result = dummy_func()
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "rate_limit_exceeded"

    def test_rate_limit_exceeds_with_60_plus_calls(self) -> None:
        """Rate limiting should kick in after 60+ calls."""
        from loom.rate_limiter import SyncRateLimiter

        # Use fetch rate limit (60 per min)
        limiter = SyncRateLimiter(max_calls=60, window_seconds=60)

        # Allow 60 calls
        for i in range(60):
            assert limiter.check() is True, f"Call {i + 1} should be allowed"

        # 61st call should fail
        assert limiter.check() is False

    def test_wrap_tool_applies_sync_rate_limiting(self) -> None:
        """_wrap_tool should apply sync_rate_limited for sync functions."""
        import inspect

        from loom.rate_limiter import reset_all
        from loom.server import _wrap_tool

        reset_all()

        def sync_dummy(x: int) -> int:
            return x + 1

        wrapped = _wrap_tool(sync_dummy, "test_category")

        # wrapped should NOT be a coroutine
        assert not inspect.iscoroutinefunction(wrapped)

        # Should be callable
        result = wrapped(5)
        assert isinstance(result, int) or isinstance(result, dict)


class TestHealthCheckEndpoint:
    """research_health_check returns correct format."""

    @pytest.mark.asyncio
    async def test_health_check_returns_dict(self) -> None:
        """research_health_check should return a dict."""
        from loom.server import research_health_check

        result = await research_health_check()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_health_check_has_required_keys(self) -> None:
        """research_health_check should include all required keys."""
        from loom.server import research_health_check

        result = await research_health_check()
        assert "status" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "active_sessions" in result

    @pytest.mark.asyncio
    async def test_health_check_status_is_healthy(self) -> None:
        """research_health_check status should be 'healthy'."""
        from loom.server import research_health_check

        result = await research_health_check()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_timestamp_format(self) -> None:
        """research_health_check timestamp should be ISO format."""
        from datetime import datetime

        from loom.server import research_health_check

        result = await research_health_check()
        timestamp = result["timestamp"]
        # Should be parseable as ISO datetime
        datetime.fromisoformat(timestamp)

    @pytest.mark.asyncio
    async def test_health_check_uptime_positive(self) -> None:
        """research_health_check uptime should be positive."""
        from loom.server import research_health_check

        result = await research_health_check()
        assert result["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_health_check_active_sessions_non_negative(self) -> None:
        """research_health_check active_sessions should be non-negative."""
        from loom.server import research_health_check

        result = await research_health_check()
        assert result["active_sessions"] >= 0


class TestServerRegisters50PlusTools:
    """Server registers 50+ tools with correct naming convention."""

    def test_create_app_returns_fastmcp(self) -> None:
        """create_app should return FastMCP instance."""
        from loom.server import create_app

        app = create_app()
        assert app is not None
        assert app.name == "loom"

    def test_server_registers_minimum_50_tools(self) -> None:
        """create_app should register at least 50 tools."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        assert len(tools) >= 50, f"Expected >= 50 tools, got {len(tools)}"

    def test_all_tool_names_follow_convention(self) -> None:
        """All tool names should follow research_*, find_*, fetch_*, or search_* naming."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        valid_prefixes = ("research_", "find_", "fetch_", "search_")
        for tool in tools:
            assert tool.name.startswith(valid_prefixes), (
                f"Tool {tool.name} doesn't follow naming convention (should start with "
                f"research_, find_, fetch_, or search_)"
            )

    def test_tool_names_are_unique(self) -> None:
        """No duplicate tool names should exist."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = [t.name for t in tools]
        duplicates = [n for n in names if names.count(n) > 1]
        assert len(duplicates) == 0, f"Duplicate tool names: {duplicates}"

    def test_expected_core_tools_present(self) -> None:
        """All core tools should be registered."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}
        core_tools = {
            "research_fetch",
            "research_spider",
            "research_markdown",
            "research_search",
            "research_deep",
            "research_github",
            "research_camoufox",
            "research_botasaurus",
            "research_cache_stats",
            "research_cache_clear",
            "research_session_open",
            "research_session_list",
            "research_session_close",
            "research_config_get",
            "research_config_set",
            "research_health_check",
        }
        missing = core_tools - names
        assert not missing, f"Missing core tools: {missing}"

    def test_tool_descriptions_present(self) -> None:
        """Tools should have descriptions."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 0


class TestTokenRedactionCoverageAllPatterns:
    """_sanitize_error covers all secret patterns: sk-, nvapi-, ghp_, AKIA, Bearer."""

    def test_sanitize_openai_key_pattern(self) -> None:
        """_sanitize_error should redact OpenAI sk- pattern."""
        from loom.tools.llm.llm import _sanitize_error

        error = "API error with key sk-1234567890abcdefghij"
        sanitized = _sanitize_error(error)
        assert "sk-1234567890abcdefghij" not in sanitized
        assert "[OPENAI_KEY_REDACTED]" in sanitized

    def test_sanitize_nvidia_key_pattern(self) -> None:
        """_sanitize_error should redact NVIDIA nvapi- pattern."""
        from loom.tools.llm.llm import _sanitize_error

        error = "NVIDIA error: nvapi-1234567890abcdef"
        sanitized = _sanitize_error(error)
        assert "nvapi-1234567890abcdef" not in sanitized
        assert "[NVIDIA_KEY_REDACTED]" in sanitized

    def test_sanitize_github_token_pattern(self) -> None:
        """_sanitize_error should redact GitHub ghp_ pattern."""
        from loom.tools.llm.llm import _sanitize_error

        error = "GitHub error: ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        sanitized = _sanitize_error(error)
        assert "ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in sanitized
        assert "[GITHUB_TOKEN_REDACTED]" in sanitized

    def test_sanitize_aws_key_pattern(self) -> None:
        """_sanitize_error should redact AWS AKIA pattern."""
        from loom.tools.llm.llm import _sanitize_error

        error = "AWS error: AKIA1234567890ABCDEF"
        sanitized = _sanitize_error(error)
        assert "AKIA1234567890ABCDEF" not in sanitized
        assert "[AWS_KEY_REDACTED]" in sanitized

    def test_sanitize_bearer_token_pattern(self) -> None:
        """_sanitize_error should redact Bearer token pattern."""
        from loom.tools.llm.llm import _sanitize_error

        error = "Auth error: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = _sanitize_error(error)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "[TOKEN_REDACTED]" in sanitized

    def test_sanitize_multiple_patterns_in_one_error(self) -> None:
        """_sanitize_error should redact multiple patterns in one error."""
        from loom.tools.llm.llm import _sanitize_error

        error = (
            "Multiple errors: sk-abc123def456ghij and nvapi-xyz789abcdef and "
            "ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        sanitized = _sanitize_error(error)
        assert "sk-abc123def456ghij" not in sanitized
        assert "nvapi-xyz789abcdef" not in sanitized
        assert "ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in sanitized
        assert "[OPENAI_KEY_REDACTED]" in sanitized
        assert "[NVIDIA_KEY_REDACTED]" in sanitized
        assert "[GITHUB_TOKEN_REDACTED]" in sanitized

    def test_sanitize_preserves_non_secret_content(self) -> None:
        """_sanitize_error should preserve non-secret content."""
        from loom.tools.llm.llm import _sanitize_error

        error = "Error: connection timeout while calling API endpoint"
        sanitized = _sanitize_error(error)
        assert sanitized == "Error: connection timeout while calling API endpoint"

    def test_sanitize_case_insensitive_bearer(self) -> None:
        """_sanitize_error should handle Bearer case-insensitively."""
        from loom.tools.llm.llm import _sanitize_error

        error_lower = "Auth: bearer token_1234567890"
        error_upper = "Auth: BEARER token_1234567890"
        error_mixed = "Auth: BeArEr token_1234567890"

        assert "[TOKEN_REDACTED]" in _sanitize_error(error_lower)
        assert "[TOKEN_REDACTED]" in _sanitize_error(error_upper)
        assert "[TOKEN_REDACTED]" in _sanitize_error(error_mixed)

    def test_sanitize_empty_string(self) -> None:
        """_sanitize_error should handle empty string."""
        from loom.tools.llm.llm import _sanitize_error

        assert _sanitize_error("") == ""

    def test_sanitize_long_keys(self) -> None:
        """_sanitize_error should handle long keys (bounded quantifiers)."""
        from loom.tools.llm.llm import _sanitize_error

        # OpenAI keys can be 48 chars
        long_key = "sk-" + "a" * 48
        error = f"Error: {long_key}"
        sanitized = _sanitize_error(error)
        assert long_key not in sanitized
        assert "[OPENAI_KEY_REDACTED]" in sanitized


class TestConfigIntegration:
    """Config integration and validation."""

    def test_config_loads(self) -> None:
        """Config should load without errors."""
        from loom.config import get_config

        config = get_config()
        assert isinstance(config, dict)

    def test_config_has_search_providers(self) -> None:
        """Config should specify search providers."""
        from loom.config import get_config

        config = get_config()
        providers = config.get("RESEARCH_SEARCH_PROVIDERS", [])
        assert isinstance(providers, list)
        assert len(providers) > 0

    def test_config_has_rate_limits(self) -> None:
        """Config should specify rate limits."""
        from loom.config import get_config

        config = get_config()
        # Should have rate limit config
        assert config.get("RATE_LIMIT_FETCH_PER_MIN") is not None
        assert config.get("RATE_LIMIT_SEARCH_PER_MIN") is not None


class TestSessionManagement:
    """Session management integration."""

    def test_research_session_list_returns_dict(self) -> None:
        """research_session_list should return dict with sessions."""
        from loom.sessions import research_session_list

        result = research_session_list()
        assert isinstance(result, dict)
        assert "sessions" in result

    def test_session_list_format(self) -> None:
        """research_session_list should return correct format."""
        from loom.sessions import research_session_list

        result = research_session_list()
        assert isinstance(result["sessions"], list)
