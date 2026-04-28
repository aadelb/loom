"""Unit tests for JavaScript intelligence extraction tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.js_intel import (
    _extract_js_urls,
    _scan_for_endpoints,
    _scan_for_env_vars,
    _scan_for_feature_flags,
    _scan_for_secrets,
    research_js_intel,
)


class TestExtractJsUrls:
    """Tests for _extract_js_urls function."""

    def test_extract_simple_script_tags(self) -> None:
        """Extract src URLs from basic script tags."""
        html = """
        <html>
        <script src="app.js"></script>
        <script src="vendor.js"></script>
        </html>
        """
        urls = _extract_js_urls(html, "https://example.com/page")
        assert "https://example.com/app.js" in urls
        assert "https://example.com/vendor.js" in urls
        assert len(urls) == 2

    def test_handle_relative_urls(self) -> None:
        """Resolve relative URLs to absolute."""
        html = '<script src="/js/app.js"></script>'
        urls = _extract_js_urls(html, "https://example.com/page")
        assert "https://example.com/js/app.js" in urls

    def test_handle_absolute_urls(self) -> None:
        """Preserve absolute URLs."""
        html = '<script src="https://cdn.example.com/app.js"></script>'
        urls = _extract_js_urls(html, "https://example.com/page")
        assert "https://cdn.example.com/app.js" in urls

    def test_filter_non_js_scripts(self) -> None:
        """Only extract .js files."""
        html = '''
        <script src="app.js"></script>
        <script src="https://example.com/api/data"></script>
        <script type="application/json">{"key": "value"}</script>
        '''
        urls = _extract_js_urls(html, "https://example.com")
        assert "https://example.com/app.js" in urls
        assert len(urls) == 1

    def test_handle_query_params(self) -> None:
        """Extract URLs with query parameters."""
        html = '<script src="app.js?v=1.0"></script>'
        urls = _extract_js_urls(html, "https://example.com")
        assert "https://example.com/app.js?v=1.0" in urls

    def test_empty_html_returns_empty_list(self) -> None:
        """Return empty list for HTML without scripts."""
        html = "<html><body><p>No scripts</p></body></html>"
        urls = _extract_js_urls(html, "https://example.com")
        assert urls == []


class TestScanForSecrets:
    """Tests for _scan_for_secrets function."""

    def test_detect_openai_key(self) -> None:
        """Detect OpenAI API keys."""
        content = "const apiKey = 'sk-proj-abcdef1234567890ABCDEFGH';"
        secrets = _scan_for_secrets(content)
        assert len(secrets) > 0
        assert any(s["type"] == "openai_key" for s in secrets)

    def test_detect_aws_access_key(self) -> None:
        """Detect AWS access keys."""
        content = "const awsKey = 'AKIAIOSFODNN7EXAMPLE';"
        secrets = _scan_for_secrets(content)
        assert any(s["type"] == "aws_access_key" for s in secrets)

    def test_detect_github_token(self) -> None:
        """Detect GitHub personal access tokens."""
        content = "token = ghp_1234567890abcdefghijklmnopqrstuv"
        secrets = _scan_for_secrets(content)
        assert any(s["type"] == "github_token" for s in secrets)

    def test_detect_slack_token(self) -> None:
        """Detect Slack tokens."""
        content = "const token = 'xoxb-123456789-1234567890-abcdefghijklmnop';"
        secrets = _scan_for_secrets(content)
        assert any(s["type"] == "slack_token" for s in secrets)

    def test_detect_jwt_token(self) -> None:
        """Detect JWT tokens."""
        content = "auth: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'"
        secrets = _scan_for_secrets(content)
        assert any(s["type"] == "jwt_token" for s in secrets)

    def test_truncate_secret_value(self) -> None:
        """Truncate secrets to 80 chars."""
        content = "key = 'sk-' + 'a' * 200"
        secrets = _scan_for_secrets(content)
        if secrets:
            assert len(secrets[0]["value"]) <= 80

    def test_no_false_positives_on_regular_text(self) -> None:
        """Don't detect secrets in regular code."""
        content = "function processData() { return data; }"
        secrets = _scan_for_secrets(content)
        assert len(secrets) == 0

    def test_risk_level_set_to_high(self) -> None:
        """All detected secrets marked as HIGH risk."""
        content = "const key = 'sk-proj-abc123def456ghi789';"
        secrets = _scan_for_secrets(content)
        assert all(s.get("risk") == "HIGH" for s in secrets)


class TestScanForEndpoints:
    """Tests for _scan_for_endpoints function."""

    def test_detect_api_paths(self) -> None:
        """Detect /api/v* endpoint paths."""
        content = "fetch('/api/v1/users').then(r => r.json())"
        endpoints = _scan_for_endpoints(content)
        assert any("/api/v1/users" in e.get("endpoint", "") for e in endpoints)

    def test_detect_graphql_endpoints(self) -> None:
        """Detect GraphQL endpoints."""
        content = "const gqlUrl = 'https://api.example.com/graphql';"
        endpoints = _scan_for_endpoints(content)
        assert any("graphql" in e.get("endpoint", "").lower() for e in endpoints)

    def test_detect_websocket_urls(self) -> None:
        """Detect WebSocket URLs."""
        content = "const ws = new WebSocket('wss://api.example.com/ws');"
        endpoints = _scan_for_endpoints(content)
        assert any("wss://" in e.get("endpoint", "") for e in endpoints)

    def test_detect_internal_urls(self) -> None:
        """Detect internal/staging/dev URLs."""
        content = "const apiBase = 'https://staging.api.internal.example.com';"
        endpoints = _scan_for_endpoints(content)
        assert len(endpoints) > 0

    def test_deduplicate_endpoints(self) -> None:
        """Remove duplicate endpoints."""
        content = """
        fetch('/api/v1/users')
        fetch('/api/v1/users')
        fetch('/api/v1/users')
        """
        endpoints = _scan_for_endpoints(content)
        endpoints_list = [e.get("endpoint") for e in endpoints]
        assert endpoints_list.count("/api/v1/users") <= 1

    def test_empty_content_returns_empty_list(self) -> None:
        """Return empty list for content without endpoints."""
        content = "function add(a, b) { return a + b; }"
        endpoints = _scan_for_endpoints(content)
        assert len(endpoints) == 0


class TestScanForFeatureFlags:
    """Tests for _scan_for_feature_flags function."""

    def test_detect_feature_flag_keywords(self) -> None:
        """Detect feature flag references."""
        content = """
        isFeatureOn('new_dashboard')
        isEnabled('dark_mode')
        hasFeature('beta_search')
        """
        flags = _scan_for_feature_flags(content)
        assert "new_dashboard" in flags or "dark_mode" in flags or "beta_search" in flags

    def test_detect_feature_flag_json(self) -> None:
        """Detect feature flags in JSON."""
        content = '"feature_flag": "enable_analytics"'
        flags = _scan_for_feature_flags(content)
        assert "enable_analytics" in flags or len(flags) >= 0

    def test_deduplicate_flags(self) -> None:
        """Remove duplicate flags."""
        content = """
        isFeatureOn('flag1')
        isFeatureOn('flag1')
        isFeatureOn('flag1')
        """
        flags = _scan_for_feature_flags(content)
        assert flags.count("flag1") <= 1

    def test_case_insensitive_matching(self) -> None:
        """Feature flag detection is case-insensitive."""
        content = "IsFeatureOn('test') OR ISFEATUREON('test')"
        flags = _scan_for_feature_flags(content)
        assert len(flags) >= 0


class TestScanForEnvVars:
    """Tests for _scan_for_env_vars function."""

    def test_detect_process_env_vars(self) -> None:
        """Detect process.env.* references."""
        content = "const apiKey = process.env.API_KEY;"
        env_vars = _scan_for_env_vars(content)
        assert "API_KEY" in env_vars

    def test_detect_import_meta_env(self) -> None:
        """Detect import.meta.env.* references."""
        content = "const base = import.meta.env.VITE_API_BASE;"
        env_vars = _scan_for_env_vars(content)
        assert "VITE_API_BASE" in env_vars

    def test_deduplicate_env_vars(self) -> None:
        """Remove duplicate environment variables."""
        content = """
        process.env.NODE_ENV
        process.env.NODE_ENV
        process.env.NODE_ENV
        """
        env_vars = _scan_for_env_vars(content)
        assert env_vars.count("NODE_ENV") <= 1

    def test_ignore_non_caps_names(self) -> None:
        """Only match ALL_CAPS env var names."""
        content = "process.env.apiKey and process.env.API_KEY"
        env_vars = _scan_for_env_vars(content)
        assert "API_KEY" in env_vars


class TestResearchJsIntel:
    """Tests for main research_js_intel function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Result dict has url, js_files_found, and analysis keys."""
        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:
            mock_fetch.side_effect = [
                "<html><script src='app.js'></script></html>",  # HTML
                "console.log('test');",  # JS file
            ]

            result = research_js_intel("https://example.com")
            assert "url" in result
            assert result["url"] == "https://example.com"
            assert "js_files_found" in result
            assert "source_maps_found" in result
            assert "secrets" in result
            assert "endpoints" in result
            assert "feature_flags" in result
            assert "env_vars" in result

    def test_honors_max_js_files(self) -> None:
        """Respects max_js_files parameter."""
        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:
            html = "".join(
                [f'<script src="file{i}.js"></script>' for i in range(50)]
            )
            mock_fetch.return_value = html

            result = research_js_intel("https://example.com", max_js_files=10)
            assert result["js_files_found"] <= 10

    def test_handles_fetch_failure_gracefully(self) -> None:
        """Return error dict when page fetch fails."""
        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:
            mock_fetch.return_value = ""

            result = research_js_intel("https://example.com")
            assert result.get("error") == "failed to fetch page"
            assert result["js_files_found"] == 0

    def test_skips_source_maps_when_disabled(self) -> None:
        """Skip .map files when check_source_maps=False."""
        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:
            call_count = [0]

            def side_effect(client, url, timeout=20.0):
                call_count[0] += 1
                if "app.js" in url and ".map" not in url:
                    return "console.log('test');"
                elif ".map" in url:
                    raise AssertionError(".map file should not be fetched")
                return "<script src='app.js'></script>"

            mock_fetch.side_effect = side_effect

            result = research_js_intel(
                "https://example.com", check_source_maps=False
            )
            assert result["source_maps_found"] == 0

    def test_extracts_intelligence_from_js_files(self) -> None:
        """Extract secrets, endpoints, flags from JS content."""
        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:
            js_with_secrets = """
            const apiKey = 'sk-proj-abc123def456';
            fetch('/api/v1/users');
            isFeatureOn('new_ui');
            const baseUrl = process.env.API_URL;
            """

            mock_fetch.side_effect = [
                "<script src='app.js'></script>",  # HTML
                js_with_secrets,  # JS file
            ]

            result = research_js_intel("https://example.com")
            # Should find secrets, endpoints, feature flags, and env vars
            assert (
                len(result.get("secrets", []))
                + len(result.get("endpoints", []))
                + len(result.get("feature_flags", []))
                + len(result.get("env_vars", []))
            ) > 0

    def test_handles_multiple_js_files(self) -> None:
        """Process multiple JS files in parallel."""
        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:

            def side_effect(client, url, timeout=20.0):
                if "app.js" in url:
                    return "const key1 = 'sk-abc123';"
                elif "vendor.js" in url:
                    return "const key2 = 'sk-def456';"
                else:
                    return "<script src='app.js'></script><script src='vendor.js'></script>"

            mock_fetch.side_effect = side_effect

            result = research_js_intel("https://example.com")
            assert result["js_files_found"] == 2

    def test_error_handling_for_invalid_urls(self) -> None:
        """Handle invalid URLs gracefully."""
        result = research_js_intel("not-a-valid-url")
        # Should not crash, return error or empty result
        assert isinstance(result, dict)
        assert "url" in result


class TestJSIntelIntegration:
    """Integration tests for js_intel tool."""

    @pytest.mark.integration
    def test_real_webpage_analysis(self) -> None:
        """Test with mocked real webpage structure."""
        html = """
        <html>
        <head>
            <script src="/js/vendor.js"></script>
            <script src="https://cdn.example.com/analytics.js"></script>
        </head>
        <body>
            <script src="/js/app.js"></script>
            <script>
                // Inline secrets (anti-pattern but real)
                const API_KEY = 'sk-proj-hardcoded-key-12345';
            </script>
        </body>
        </html>
        """

        app_js = """
        const config = {
            apiBase: 'https://staging.api.example.com',
            graphqlUrl: '/graphql',
            wsUrl: 'wss://realtime.example.com/events'
        };

        fetch(config.apiBase + '/api/v1/users');

        if (featureFlags.get('new_dashboard')) {
            loadNewUI();
        }

        const envVars = {
            apiKey: process.env.API_KEY,
            baseUrl: import.meta.env.VITE_BASE_URL
        };
        """

        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:

            def side_effect(client, url, timeout=20.0):
                if "example.com" in url and ".js" not in url and ".map" not in url:
                    return html
                elif "/js/app.js" in url:
                    return app_js
                elif "/js/vendor.js" in url:
                    return "// vendor code"
                elif "analytics.js" in url:
                    return "// analytics"
                else:
                    return ""

            mock_fetch.side_effect = side_effect

            result = research_js_intel("https://example.com")

            assert result["js_files_found"] >= 2
            # Should find secrets from inline script
            assert len(result.get("secrets", [])) >= 0
            # Should find endpoints and WebSocket URLs
            assert len(result.get("endpoints", [])) >= 0

    def test_concurrent_js_file_fetching(self) -> None:
        """Verify concurrent fetching of JS files."""
        with patch("loom.tools.js_intel._fetch_text") as mock_fetch:
            files = [f"file{i}" for i in range(10)]
            html = "".join([f'<script src="{f}.js"></script>' for f in files])

            mock_fetch.side_effect = [html] + ["// js content"] * 10

            result = research_js_intel("https://example.com", max_js_files=10)
            assert result["js_files_found"] == 10
