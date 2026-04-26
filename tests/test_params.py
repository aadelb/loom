"""Unit tests for Pydantic parameter models — validation of good/bad inputs."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loom.params import (
    BotasaurusParams,
    CamoufoxParams,
    ConfigSetParams,
    DeepParams,
    FetchParams,
    GitHubSearchParams,
    LLMChatParams,
    LLMClassifyParams,
    LLMExtractParams,
    LLMQueryExpandParams,
    LLMSummarizeParams,
    LLMTranslateParams,
    MarkdownParams,
    SearchParams,
    SessionOpenParams,
    SpiderParams,
)


class TestFetchParams:
    """FetchParams validation tests."""

    def test_fetch_valid_url(self) -> None:
        """Valid public URL passes validation."""
        params = FetchParams(url="https://example.com")
        assert params.url == "https://example.com"

    def test_fetch_rejects_invalid_url_scheme(self) -> None:
        """Invalid scheme raises UrlSafetyError."""
        with pytest.raises(ValidationError) as exc_info:
            FetchParams(url="ftp://example.com")
        assert "scheme" in str(exc_info.value).lower()

    def test_fetch_rejects_ssrf_url(self) -> None:
        """SSRF URL raises UrlSafetyError."""
        with pytest.raises(ValidationError):
            FetchParams(url="http://localhost:8080")

    def test_fetch_rejects_invalid_mode(self) -> None:
        """Invalid mode value raises ValidationError."""
        with pytest.raises(ValidationError):
            FetchParams(url="https://example.com", mode="invalid")

    def test_fetch_rejects_user_agent_too_long(self) -> None:
        """User agent over 256 chars raises ValidationError."""
        with pytest.raises(ValidationError):
            FetchParams(url="https://example.com", user_agent="x" * 257)

    def test_fetch_rejects_invalid_proxy(self) -> None:
        """Proxy without http(s)/socks5 prefix raises ValidationError."""
        with pytest.raises(ValidationError):
            FetchParams(url="https://example.com", proxy="ftp://proxy:1080")

    def test_fetch_rejects_invalid_retries(self) -> None:
        """Retries < 0 or > 3 raises ValidationError."""
        with pytest.raises(ValidationError):
            FetchParams(url="https://example.com", retries=5)

    def test_fetch_rejects_timeout_out_of_range(self) -> None:
        """Timeout < 1 or > 120 raises ValidationError."""
        with pytest.raises(ValidationError):
            FetchParams(url="https://example.com", timeout=121)

    def test_fetch_rejects_extra_fields(self) -> None:
        """Extra fields raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            FetchParams(url="https://example.com", unknown_field="value")


class TestSearchParams:
    """SearchParams validation tests."""

    def test_search_valid(self) -> None:
        """Valid search params pass validation."""
        params = SearchParams(query="example query", n=10)
        assert params.query == "example query"
        assert params.n == 10

    def test_search_rejects_empty_query(self) -> None:
        """Empty query raises ValidationError."""
        with pytest.raises(ValidationError):
            SearchParams(query="")

    def test_search_rejects_whitespace_only_query(self) -> None:
        """Whitespace-only query raises ValidationError."""
        with pytest.raises(ValidationError):
            SearchParams(query="   ")

    def test_search_rejects_n_zero(self) -> None:
        """n=0 raises ValidationError."""
        with pytest.raises(ValidationError):
            SearchParams(query="test", n=0)

    def test_search_rejects_n_over_50(self) -> None:
        """n > 50 raises ValidationError."""
        with pytest.raises(ValidationError):
            SearchParams(query="test", n=51)

    def test_search_rejects_invalid_provider(self) -> None:
        """Invalid provider raises ValidationError."""
        with pytest.raises(ValidationError):
            SearchParams(query="test", provider="invalid")


class TestGitHubSearchParams:
    """GitHubSearchParams validation tests."""

    def test_github_valid(self) -> None:
        """Valid GitHub params pass validation."""
        params = GitHubSearchParams(kind="repos", query="llm")
        assert params.query == "llm"

    def test_github_rejects_flag_injection(self) -> None:
        """Query starting with '-' raises ValidationError."""
        with pytest.raises(ValidationError):
            GitHubSearchParams(kind="repos", query="--owner attacker")

    def test_github_rejects_empty_query(self) -> None:
        """Empty query raises ValidationError."""
        with pytest.raises(ValidationError):
            GitHubSearchParams(kind="repos", query="")

    def test_github_rejects_query_too_long(self) -> None:
        """Query > 512 chars raises ValidationError."""
        with pytest.raises(ValidationError):
            GitHubSearchParams(kind="repos", query="x" * 513)

    def test_github_rejects_invalid_limit(self) -> None:
        """limit > 100 raises ValidationError."""
        with pytest.raises(ValidationError):
            GitHubSearchParams(kind="repos", query="test", limit=101)

    def test_github_accepts_valid_kinds(self) -> None:
        """Valid kinds (repos, code, issues) pass."""
        for kind in ["repos", "code", "issues"]:
            params = GitHubSearchParams(kind=kind, query="test")
            assert params.kind == kind


class TestSessionOpenParams:
    """SessionOpenParams validation tests."""

    def test_session_valid_name(self) -> None:
        """Valid session name passes validation."""
        params = SessionOpenParams(name="my_session_1")
        assert params.name == "my_session_1"

    def test_session_rejects_uppercase(self) -> None:
        """Uppercase letters raise ValidationError."""
        with pytest.raises(ValidationError):
            SessionOpenParams(name="MySession")

    def test_session_rejects_spaces(self) -> None:
        """Spaces in name raise ValidationError."""
        with pytest.raises(ValidationError):
            SessionOpenParams(name="my session")

    def test_session_rejects_special_chars(self) -> None:
        """Special chars raise ValidationError."""
        with pytest.raises(ValidationError):
            SessionOpenParams(name="session#1")

    def test_session_rejects_path_traversal(self) -> None:
        """Path traversal raises ValidationError."""
        with pytest.raises(ValidationError):
            SessionOpenParams(name="..")

    def test_session_rejects_too_long_name(self) -> None:
        """Names > 32 chars raise ValidationError."""
        with pytest.raises(ValidationError):
            SessionOpenParams(name="a" * 33)

    def test_session_rejects_invalid_ttl(self) -> None:
        """ttl_seconds < 60 or > 86400 raises ValidationError."""
        with pytest.raises(ValidationError):
            SessionOpenParams(name="session", ttl_seconds=30)


class TestConfigSetParams:
    """ConfigSetParams validation tests."""

    def test_config_set_any_value(self) -> None:
        """Any key/value combo passes (validation deferred to config set)."""
        params = ConfigSetParams(key="MY_KEY", value=100)
        assert params.key == "MY_KEY"
        assert params.value == 100

    def test_config_set_rejects_extra_fields(self) -> None:
        """Extra fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ConfigSetParams(key="test", value="val", extra="field")


class TestLLMChatParams:
    """LLMChatParams validation tests."""

    def test_llm_chat_valid(self) -> None:
        """Valid chat params pass."""
        params = LLMChatParams(
            messages=[{"role": "user", "content": "Hello"}], temperature=0.7
        )
        assert params.temperature == 0.7

    def test_llm_chat_rejects_temp_out_of_range(self) -> None:
        """temperature > 2.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            LLMChatParams(
                messages=[{"role": "user", "content": "Hi"}], temperature=2.5
            )


class TestLLMSummarizeParams:
    """LLMSummarizeParams validation tests."""

    def test_summarize_valid(self) -> None:
        """Valid summarize params pass."""
        params = LLMSummarizeParams(text="Long text here", max_length=500)
        assert params.max_length == 500

    def test_summarize_rejects_max_length_too_small(self) -> None:
        """max_length < 50 raises ValidationError."""
        with pytest.raises(ValidationError):
            LLMSummarizeParams(text="test", max_length=49)

    def test_summarize_rejects_max_length_too_large(self) -> None:
        """max_length > 5000 raises ValidationError."""
        with pytest.raises(ValidationError):
            LLMSummarizeParams(text="test", max_length=5001)


class TestLLMExtractParams:
    """LLMExtractParams validation tests."""

    def test_extract_valid(self) -> None:
        """Valid extract params pass (with 'schema' alias)."""
        params = LLMExtractParams(
            text="Extract data", schema={"type": "object", "properties": {}}
        )
        assert params.schema_def == {"type": "object", "properties": {}}


class TestLLMClassifyParams:
    """LLMClassifyParams validation tests."""

    def test_classify_valid(self) -> None:
        """Valid classify params pass."""
        params = LLMClassifyParams(text="Sample", categories=["cat1", "cat2"])
        assert len(params.categories) == 2

    def test_classify_rejects_empty_categories(self) -> None:
        """Empty categories list raises ValidationError."""
        with pytest.raises(ValidationError):
            LLMClassifyParams(text="test", categories=[])

    def test_classify_rejects_too_many_categories(self) -> None:
        """categories > 20 raises ValidationError."""
        with pytest.raises(ValidationError):
            LLMClassifyParams(text="test", categories=[f"cat{i}" for i in range(21)])


class TestLLMTranslateParams:
    """LLMTranslateParams validation tests."""

    def test_translate_valid(self) -> None:
        """Valid translate params pass."""
        params = LLMTranslateParams(text="مرحبا", source_lang="ar", target_lang="en")
        assert params.text == "مرحبا"
        assert params.source_lang == "ar"


class TestLLMQueryExpandParams:
    """LLMQueryExpandParams validation tests."""

    def test_query_expand_valid(self) -> None:
        """Valid expand params pass."""
        params = LLMQueryExpandParams(query="test", count=3)
        assert params.count == 3

    def test_query_expand_rejects_count_too_high(self) -> None:
        """count > 10 raises ValidationError."""
        with pytest.raises(ValidationError):
            LLMQueryExpandParams(query="test", count=11)


class TestDeepParams:
    """DeepParams validation tests."""

    def test_deep_valid(self) -> None:
        """Valid deep params pass."""
        params = DeepParams(query="research", depth=2)
        assert params.depth == 2

    def test_deep_rejects_depth_out_of_range(self) -> None:
        """depth < 1 or > 10 raises ValidationError."""
        with pytest.raises(ValidationError):
            DeepParams(query="test", depth=11)


class TestCamoufoxParams:
    """CamoufoxParams validation tests."""

    def test_camoufox_valid(self) -> None:
        """Valid camoufox params pass."""
        params = CamoufoxParams(url="https://example.com")
        assert params.url == "https://example.com"

    def test_camoufox_rejects_ssrf(self) -> None:
        """SSRF URL raises ValidationError."""
        with pytest.raises(ValidationError):
            CamoufoxParams(url="http://192.168.1.1")


class TestBotasaurusParams:
    """BotasaurusParams validation tests."""

    def test_botasaurus_valid(self) -> None:
        """Valid botasaurus params pass."""
        params = BotasaurusParams(url="https://example.com")
        assert params.url == "https://example.com"


class TestSpiderParams:
    """SpiderParams validation tests."""

    def test_spider_valid_urls(self) -> None:
        """Valid URLs in list pass."""
        params = SpiderParams(urls=["https://example.com", "https://google.com"])
        assert len(params.urls) == 2

    def test_spider_rejects_invalid_urls(self) -> None:
        """Invalid URL in list raises ValidationError."""
        with pytest.raises(ValidationError):
            SpiderParams(urls=["https://example.com", "http://localhost"])

    def test_spider_rejects_concurrency_out_of_range(self) -> None:
        """concurrency > 20 raises ValidationError."""
        with pytest.raises(ValidationError):
            SpiderParams(urls=["https://example.com"], concurrency=21)


class TestMarkdownParams:
    """MarkdownParams validation tests."""

    def test_markdown_valid(self) -> None:
        """Valid markdown params pass."""
        params = MarkdownParams(url="https://example.com")
        assert params.url == "https://example.com"
