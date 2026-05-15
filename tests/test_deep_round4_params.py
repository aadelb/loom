"""Deep testing round 4: Pydantic parameter validation.

Systematic testing of Pydantic v2 parameter models with `extra` and `strict` config.
Tests verify that validation actually works correctly across 10+ param models from
different tool categories (core, llm, intelligence, security, research).

FINDINGS:
- BotasaurusParams MISSING wait_time/timeout validators (but CamoufoxParams has them)
- Most models use extra='ignore' not 'forbid' (only CyberscraperParams uses forbid)
- URL validation is strict: performs actual DNS resolution
"""

import pytest
from pydantic import ValidationError

# Import representative param models from each category
from loom.params.core import (
    BotasaurusParams,
    CamoufoxParams,
    CyberscraperParams,
    DeepParams,
    FetchParams,
    GitHubParams,
)
from loom.params.llm import (
    EmbeddingCollideParams,
    LLMChatParams,
)
from loom.params.intelligence import (
    CitationGraphParams,
    CompanyDiligenceParams,
    CredentialMonitorParams,
)
from loom.params.security import (
    BreachCheckParams,
    CVELookupParams,
    CensysHostParams,
)


class TestBotasaurusParams:
    """Test BotasaurusParams validation (extra='ignore', strict=True).
    
    NOTE: wait_time and timeout fields have NO validators in this class
    (unlike CamoufoxParams which does validate them).
    """

    def test_valid_construction(self):
        """Should accept valid parameters."""
        p = BotasaurusParams(url="https://google.com")
        assert p.url == "https://google.com"
        assert p.max_chars == 20000  # default
        assert p.timeout == 30  # default

    def test_extra_field_ignored(self):
        """extra='ignore' means unknown fields are silently ignored."""
        p = BotasaurusParams(url="https://google.com", unknown_field="ignored")
        assert p.url == "https://google.com"
        # unknown_field is ignored, not stored
        assert not hasattr(p, "unknown_field")

    def test_strict_type_enforcement_url(self):
        """strict=True should enforce type strictly (no int->str coercion)."""
        with pytest.raises(ValidationError):
            BotasaurusParams(url=12345)

    def test_strict_type_enforcement_max_chars(self):
        """strict=True should enforce int type."""
        with pytest.raises(ValidationError):
            BotasaurusParams(url="https://google.com", max_chars="20000")

    def test_bounds_max_chars(self):
        """max_chars bounds: 1000-100000 (has validator)."""
        # Below minimum
        with pytest.raises(ValidationError, match="max_chars must be 1000-100000"):
            BotasaurusParams(url="https://google.com", max_chars=500)

        # Above maximum
        with pytest.raises(ValidationError, match="max_chars must be 1000-100000"):
            BotasaurusParams(url="https://google.com", max_chars=200000)

        # Valid boundaries
        BotasaurusParams(url="https://google.com", max_chars=1000)
        BotasaurusParams(url="https://google.com", max_chars=100000)

    def test_wait_time_no_bounds_checking(self):
        """FINDING: wait_time has NO validator in BotasaurusParams.
        
        wait_time can be set to any int value (no bounds).
        CamoufoxParams HAS validators for wait_time (0-60) but Botasaurus doesn't.
        This is a validation gap.
        """
        # Should NOT raise - no validators for these fields in Botasaurus
        BotasaurusParams(url="https://google.com", wait_time=1000)
        BotasaurusParams(url="https://google.com", wait_time=-100)

    def test_timeout_no_bounds_checking(self):
        """FINDING: timeout has NO validator in BotasaurusParams.
        
        Unlike CamoufoxParams which validates timeout to 1-120, Botasaurus
        accepts any int value.
        """
        # Should NOT raise - no validators for timeout in Botasaurus
        BotasaurusParams(url="https://google.com", timeout=5000)
        BotasaurusParams(url="https://google.com", timeout=-1)

    def test_url_validation_ssrf_check(self):
        """URL validation performs SSRF checks (rejects private IPs)."""
        # Local/private IPs should fail SSRF check
        with pytest.raises(ValidationError):
            BotasaurusParams(url="http://127.0.0.1")

        with pytest.raises(ValidationError):
            BotasaurusParams(url="http://192.168.1.1")

        with pytest.raises(ValidationError):
            BotasaurusParams(url="http://localhost")

    def test_url_validation_dns_resolution(self):
        """URL validation performs DNS resolution.
        
        Only public IPs that resolve via DNS are accepted.
        Test with a domain that definitely exists.
        """
        BotasaurusParams(url="https://google.com")
        BotasaurusParams(url="https://github.com")


class TestCamoufoxParams:
    """Test CamoufoxParams validation (extra='ignore', strict=True).
    
    CamoufoxParams HAS validators for wait_time and timeout
    (unlike BotasaurusParams).
    """

    def test_valid_construction(self):
        """Should construct with valid params."""
        p = CamoufoxParams(url="https://google.com")
        assert p.return_format == "text"  # default

    def test_literal_enum_validation(self):
        """Literal fields should only accept specified values."""
        CamoufoxParams(url="https://google.com", return_format="text")
        CamoufoxParams(url="https://google.com", return_format="screenshot")
        CamoufoxParams(url="https://google.com", return_format="html")

        with pytest.raises(ValidationError):
            CamoufoxParams(url="https://google.com", return_format="invalid")

    def test_bounds_max_chars(self):
        """max_chars bounds: 1000-100000."""
        with pytest.raises(ValidationError, match="max_chars must be 1000-100000"):
            CamoufoxParams(url="https://google.com", max_chars=500)

    def test_bounds_wait_time(self):
        """FINDING: wait_time HAS bounds validator (0-60) in CamoufoxParams.
        
        This validator is present in Camoufox but NOT in Botasaurus,
        even though both have the same field.
        """
        with pytest.raises(ValidationError, match="wait_time must be 0-60"):
            CamoufoxParams(url="https://google.com", wait_time=70)

        CamoufoxParams(url="https://google.com", wait_time=0)
        CamoufoxParams(url="https://google.com", wait_time=60)

    def test_bounds_timeout(self):
        """FINDING: timeout HAS bounds validator (1-120) in CamoufoxParams.
        
        This validator is present in Camoufox but NOT in Botasaurus.
        """
        with pytest.raises(ValidationError, match="timeout must be 1-120"):
            CamoufoxParams(url="https://google.com", timeout=0)

        with pytest.raises(ValidationError, match="timeout must be 1-120"):
            CamoufoxParams(url="https://google.com", timeout=200)

        CamoufoxParams(url="https://google.com", timeout=1)
        CamoufoxParams(url="https://google.com", timeout=120)

    def test_extra_fields_ignored(self):
        """extra='ignore' should silently ignore unknown fields."""
        p = CamoufoxParams(
            url="https://google.com",
            return_format="text",
            unknown_param="should_be_ignored"
        )
        assert not hasattr(p, "unknown_param")


class TestCyberscraperParams:
    """Test CyberscraperParams validation (extra='forbid', strict=True).
    
    This is the ONLY param model tested that uses extra='forbid'.
    """

    def test_valid_construction(self):
        """Should construct with valid params."""
        p = CyberscraperParams(url="https://google.com")
        assert p.extract_type == "all"  # default
        assert p.format == "json"  # default

    def test_extra_field_rejected(self):
        """FINDING: extra='forbid' rejects unknown fields.
        
        CyberscraperParams is the only model tested with extra='forbid'.
        All others use extra='ignore'.
        """
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CyberscraperParams(
                url="https://google.com",
                unknown_field="should_fail"
            )

    def test_strict_type_enforcement(self):
        """strict=True should reject type coercion."""
        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", max_chars="20000")

    def test_literal_enum_validation_extract_type(self):
        """extract_type must be one of allowed values."""
        valid_types = ["all", "text", "tables", "links", "images", "json", "structured"]
        for t in valid_types:
            CyberscraperParams(url="https://google.com", extract_type=t)

        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", extract_type="invalid")

    def test_literal_enum_validation_format(self):
        """format must be one of allowed values."""
        for fmt in ["json", "csv", "html", "markdown"]:
            CyberscraperParams(url="https://google.com", format=fmt)

        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", format="xml")

    def test_bounds_max_chars(self):
        """max_chars bounds: 1000-100000 (enforced via ge/le)."""
        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", max_chars=999)

        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", max_chars=100001)

        CyberscraperParams(url="https://google.com", max_chars=1000)
        CyberscraperParams(url="https://google.com", max_chars=100000)

    def test_bounds_timeout_seconds(self):
        """timeout_seconds bounds: 5-300 (enforced via ge/le)."""
        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", timeout_seconds=4)

        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", timeout_seconds=301)

        CyberscraperParams(url="https://google.com", timeout_seconds=5)
        CyberscraperParams(url="https://google.com", timeout_seconds=300)

    def test_boolean_fields(self):
        """Boolean fields should accept only bool values."""
        # Valid
        CyberscraperParams(url="https://google.com", use_tor=True, stealth_mode=False)

        # Type coercion blocked by strict=True
        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", use_tor="true")

        with pytest.raises(ValidationError):
            CyberscraperParams(url="https://google.com", stealth_mode=1)


class TestDeepParams:
    """Test DeepParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid query."""
        p = DeepParams(query="machine learning")
        assert p.mode == "thorough"  # default
        assert p.max_results == 20  # default

    def test_required_field_missing(self):
        """Missing required field should fail."""
        with pytest.raises(ValidationError):
            DeepParams()

    def test_query_empty_string_rejected(self):
        """Empty/whitespace-only query should fail."""
        with pytest.raises(ValidationError, match="query must be non-empty"):
            DeepParams(query="")

        with pytest.raises(ValidationError, match="query must be non-empty"):
            DeepParams(query="   ")

    def test_query_max_length(self):
        """query max 2000 characters."""
        long_query = "x" * 2001
        with pytest.raises(ValidationError, match="query max 2000 characters"):
            DeepParams(query=long_query)

        DeepParams(query="x" * 2000)  # Should pass

    def test_bounds_max_results(self):
        """max_results bounds: 1-100."""
        with pytest.raises(ValidationError, match="max_results must be 1-100"):
            DeepParams(query="test", max_results=0)

        with pytest.raises(ValidationError, match="max_results must be 1-100"):
            DeepParams(query="test", max_results=101)

        DeepParams(query="test", max_results=1)
        DeepParams(query="test", max_results=100)

    def test_bounds_max_urls(self):
        """max_urls bounds: 1-100."""
        with pytest.raises(ValidationError, match="max_urls must be 1-100"):
            DeepParams(query="test", max_urls=0)

        with pytest.raises(ValidationError, match="max_urls must be 1-100"):
            DeepParams(query="test", max_urls=101)

    def test_literal_mode(self):
        """mode must be 'fast' or 'thorough'."""
        DeepParams(query="test", mode="fast")
        DeepParams(query="test", mode="thorough")

        with pytest.raises(ValidationError):
            DeepParams(query="test", mode="invalid")

    def test_literal_provider_tier(self):
        """provider_tier must be one of allowed values."""
        DeepParams(query="test", provider_tier="free_only")
        DeepParams(query="test", provider_tier="paid_ok")
        DeepParams(query="test", provider_tier="auto")

        with pytest.raises(ValidationError):
            DeepParams(query="test", provider_tier="invalid")

    def test_query_whitespace_stripped(self):
        """query should have leading/trailing whitespace stripped."""
        p = DeepParams(query="  test query  ")
        assert p.query == "test query"


class TestFetchParams:
    """Test FetchParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid URL."""
        p = FetchParams(url="https://google.com")
        assert p.mode == "stealthy"  # default
        assert p.solve_cloudflare is True  # default
        assert p.max_chars == 20000  # default

    def test_required_url_field(self):
        """url is required."""
        with pytest.raises(ValidationError):
            FetchParams()

    def test_mode_literal_validation(self):
        """mode must be 'http', 'stealthy', or 'dynamic'."""
        FetchParams(url="https://google.com", mode="http")
        FetchParams(url="https://google.com", mode="stealthy")
        FetchParams(url="https://google.com", mode="dynamic")

        with pytest.raises(ValidationError):
            FetchParams(url="https://google.com", mode="invalid")

    def test_return_format_literal(self):
        """return_format must be one of allowed values."""
        for fmt in ["text", "html", "json", "screenshot"]:
            FetchParams(url="https://google.com", return_format=fmt)

        with pytest.raises(ValidationError):
            FetchParams(url="https://google.com", return_format="xml")

    def test_user_agent_max_length(self):
        """user_agent max 256 chars."""
        with pytest.raises(ValidationError, match="user_agent max 256 chars"):
            FetchParams(url="https://google.com", user_agent="x" * 257)

        FetchParams(url="https://google.com", user_agent="x" * 256)

    def test_user_agent_optional(self):
        """user_agent is optional (None)."""
        p = FetchParams(url="https://google.com", user_agent=None)
        assert p.user_agent is None

    def test_proxy_validation_valid_schemes(self):
        """proxy must start with valid schemes."""
        FetchParams(url="https://google.com", proxy="http://proxy.example.com:8080")
        FetchParams(url="https://google.com", proxy="https://proxy.example.com:8080")
        FetchParams(url="https://google.com", proxy="socks5://proxy.example.com:1080")
        FetchParams(url="https://google.com", proxy="socks5h://proxy.example.com:1080")

    def test_proxy_validation_invalid_scheme(self):
        """proxy with invalid scheme should fail."""
        with pytest.raises(ValidationError, match="proxy must start with"):
            FetchParams(url="https://google.com", proxy="ftp://proxy.example.com")

        with pytest.raises(ValidationError, match="proxy must start with"):
            FetchParams(url="https://google.com", proxy="invalid://proxy.example.com")

    def test_retries_bounds(self):
        """retries bounds: 0-3."""
        with pytest.raises(ValidationError, match="retries must be 0-3"):
            FetchParams(url="https://google.com", retries=-1)

        with pytest.raises(ValidationError, match="retries must be 0-3"):
            FetchParams(url="https://google.com", retries=4)

        FetchParams(url="https://google.com", retries=0)
        FetchParams(url="https://google.com", retries=3)

    def test_timeout_bounds(self):
        """timeout bounds: 1-120 seconds."""
        with pytest.raises(ValidationError, match="timeout must be 1-120"):
            FetchParams(url="https://google.com", timeout=0)

        with pytest.raises(ValidationError, match="timeout must be 1-120"):
            FetchParams(url="https://google.com", timeout=121)

        FetchParams(url="https://google.com", timeout=1)
        FetchParams(url="https://google.com", timeout=120)

    def test_timeout_optional(self):
        """timeout is optional (None)."""
        p = FetchParams(url="https://google.com", timeout=None)
        assert p.timeout is None

    def test_headers_dict_type(self):
        """headers should accept dict[str, str] or None."""
        FetchParams(url="https://google.com", headers={"X-Custom": "value"})
        FetchParams(url="https://google.com", headers=None)

        # Type enforcement
        with pytest.raises(ValidationError):
            FetchParams(url="https://google.com", headers="not a dict")

    def test_cookies_dict_type(self):
        """cookies should accept dict[str, str] or None."""
        FetchParams(url="https://google.com", cookies={"session": "abc123"})
        FetchParams(url="https://google.com", cookies=None)

    def test_basic_auth_tuple_type(self):
        """basic_auth should accept tuple[str, str] or None."""
        FetchParams(url="https://google.com", basic_auth=("user", "pass"))
        FetchParams(url="https://google.com", basic_auth=None)

        with pytest.raises(ValidationError):
            FetchParams(url="https://google.com", basic_auth="not a tuple")


class TestGitHubParams:
    """Test GitHubParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid query."""
        p = GitHubParams(query="python library")
        assert p.sort_by == "stars"  # default
        assert p.per_page == 10  # default
        assert p.code_search is False  # default

    def test_query_empty_rejected(self):
        """Empty query should fail."""
        with pytest.raises(ValidationError, match="query must be non-empty"):
            GitHubParams(query="")

        with pytest.raises(ValidationError, match="query must be non-empty"):
            GitHubParams(query="   ")

    def test_query_max_length(self):
        """query max 500 characters."""
        long_query = "x" * 501
        with pytest.raises(ValidationError, match="query max 500 characters"):
            GitHubParams(query=long_query)

        GitHubParams(query="x" * 500)

    def test_sort_by_literal(self):
        """sort_by must be one of allowed values."""
        for sort in ["stars", "forks", "updated", "best-match"]:
            GitHubParams(query="test", sort_by=sort)

        with pytest.raises(ValidationError):
            GitHubParams(query="test", sort_by="invalid")

    def test_per_page_bounds(self):
        """per_page bounds: 1-100."""
        with pytest.raises(ValidationError, match="per_page must be 1-100"):
            GitHubParams(query="test", per_page=0)

        with pytest.raises(ValidationError, match="per_page must be 1-100"):
            GitHubParams(query="test", per_page=101)

    def test_language_optional(self):
        """language is optional (None)."""
        p = GitHubParams(query="test", language=None)
        assert p.language is None

        p = GitHubParams(query="test", language="python")
        assert p.language == "python"

    def test_code_search_boolean(self):
        """code_search must be boolean."""
        GitHubParams(query="test", code_search=True)
        GitHubParams(query="test", code_search=False)

        with pytest.raises(ValidationError):
            GitHubParams(query="test", code_search="yes")


class TestEmbeddingCollideParams:
    """Test EmbeddingCollideParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid parameters."""
        p = EmbeddingCollideParams(
            target_text="This is a longer target text",
            malicious_payload="hidden payload"
        )
        assert p.method == "synonym_swap"  # default

    def test_target_text_min_length(self):
        """target_text min 10 characters (via validator, not Field)."""
        with pytest.raises(ValidationError, match="target_text must be at least 10 characters"):
            EmbeddingCollideParams(
                target_text="short",
                malicious_payload="payload"
            )

        EmbeddingCollideParams(
            target_text="x" * 10,
            malicious_payload="payload"
        )

    def test_target_text_max_length(self):
        """target_text max 5000 characters (via Field)."""
        with pytest.raises(ValidationError):
            EmbeddingCollideParams(
                target_text="x" * 5001,
                malicious_payload="payload"
            )

    def test_malicious_payload_required(self):
        """malicious_payload is required."""
        with pytest.raises(ValidationError):
            EmbeddingCollideParams(target_text="x" * 10)

    def test_malicious_payload_max_length(self):
        """malicious_payload max 1000 characters."""
        with pytest.raises(ValidationError):
            EmbeddingCollideParams(
                target_text="x" * 10,
                malicious_payload="x" * 1001
            )

    def test_method_literal_validation(self):
        """method must be one of allowed values."""
        valid_methods = ["synonym_swap", "context_inject", "semantic_trojan", "retrieval_poison"]
        for method in valid_methods:
            EmbeddingCollideParams(
                target_text="x" * 10,
                malicious_payload="payload",
                method=method
            )

        with pytest.raises(ValidationError):
            EmbeddingCollideParams(
                target_text="x" * 10,
                malicious_payload="payload",
                method="invalid"
            )

    def test_whitespace_stripped(self):
        """Whitespace should be stripped from text fields."""
        p = EmbeddingCollideParams(
            target_text="  target text  ",
            malicious_payload="  payload  "
        )
        assert p.target_text == "target text"
        assert p.malicious_payload == "payload"


class TestCitationGraphParams:
    """Test CitationGraphParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid query."""
        p = CitationGraphParams(query="machine learning")
        assert p.depth == 2  # default

    def test_query_empty_rejected(self):
        """Empty query should fail."""
        with pytest.raises(ValidationError, match="query must be non-empty"):
            CitationGraphParams(query="")

    def test_query_max_length(self):
        """query max 500 characters."""
        with pytest.raises(ValidationError, match="query max 500 characters"):
            CitationGraphParams(query="x" * 501)

    def test_depth_bounds(self):
        """depth bounds: 1-3."""
        with pytest.raises(ValidationError, match="depth must be 1-3"):
            CitationGraphParams(query="test", depth=0)

        with pytest.raises(ValidationError, match="depth must be 1-3"):
            CitationGraphParams(query="test", depth=4)

        CitationGraphParams(query="test", depth=1)
        CitationGraphParams(query="test", depth=3)


class TestCompanyDiligenceParams:
    """Test CompanyDiligenceParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid company name."""
        p = CompanyDiligenceParams(company_name="Acme Corp")
        assert p.company_name == "Acme Corp"

    def test_company_name_empty_rejected(self):
        """Empty company_name should fail."""
        with pytest.raises(ValidationError, match="company_name must be non-empty"):
            CompanyDiligenceParams(company_name="")

        with pytest.raises(ValidationError, match="company_name must be non-empty"):
            CompanyDiligenceParams(company_name="   ")

    def test_company_name_max_length(self):
        """company_name max 200 characters."""
        with pytest.raises(ValidationError, match="company_name max 200 characters"):
            CompanyDiligenceParams(company_name="x" * 201)

        CompanyDiligenceParams(company_name="x" * 200)

    def test_company_name_whitespace_stripped(self):
        """Whitespace should be stripped."""
        p = CompanyDiligenceParams(company_name="  Acme Corp  ")
        assert p.company_name == "Acme Corp"


class TestCredentialMonitorParams:
    """Test CredentialMonitorParams validation with alias (extra='ignore', strict=True)."""

    def test_valid_construction_by_name(self):
        """Should accept 'query' parameter name."""
        p = CredentialMonitorParams(query="user@example.com")
        assert p.query == "user@example.com"

    def test_alias_populate_by_name(self):
        """Should accept alias 'target' due to populate_by_name=True."""
        # populate_by_name=True allows both the field name and alias
        p = CredentialMonitorParams(target="user@example.com")
        assert p.query == "user@example.com"

    def test_target_type_literal(self):
        """target_type must be 'email' or 'username'."""
        CredentialMonitorParams(query="test", target_type="email")
        CredentialMonitorParams(query="test", target_type="username")

        with pytest.raises(ValidationError):
            CredentialMonitorParams(query="test", target_type="invalid")

    def test_query_empty_rejected(self):
        """Empty query should fail."""
        with pytest.raises(ValidationError, match="query must be 1-255 characters"):
            CredentialMonitorParams(query="")

    def test_query_max_length(self):
        """query max 255 characters."""
        with pytest.raises(ValidationError, match="query must be 1-255 characters"):
            CredentialMonitorParams(query="x" * 256)

    def test_query_case_normalized(self):
        """query should be lowercased."""
        p = CredentialMonitorParams(query="USER@EXAMPLE.COM")
        assert p.query == "user@example.com"


class TestBreachCheckParams:
    """Test BreachCheckParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid email."""
        p = BreachCheckParams(email="user@example.com")
        assert p.email == "user@example.com"

    def test_email_validation_invalid(self):
        """Invalid emails should fail."""
        with pytest.raises(ValidationError, match="email format invalid"):
            BreachCheckParams(email="not-an-email")

        with pytest.raises(ValidationError, match="email format invalid"):
            BreachCheckParams(email="@example.com")

        with pytest.raises(ValidationError, match="email format invalid"):
            BreachCheckParams(email="user@")

    def test_email_validation_valid(self):
        """Valid emails should pass."""
        BreachCheckParams(email="user@example.com")
        BreachCheckParams(email="user.name@sub.example.co.uk")

    def test_email_case_normalized(self):
        """Email should be lowercased."""
        p = BreachCheckParams(email="USER@EXAMPLE.COM")
        assert p.email == "user@example.com"

    def test_email_whitespace_stripped(self):
        """Whitespace should be stripped."""
        p = BreachCheckParams(email="  user@example.com  ")
        assert p.email == "user@example.com"


class TestCVELookupParams:
    """Test CVELookupParams validation with alias (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with valid query."""
        p = CVELookupParams(query="OpenSSL vulnerability")
        assert p.max_results == 10  # default

    def test_alias_max_results(self):
        """max_results has alias 'limit'."""
        p = CVELookupParams(query="test", limit=20)
        assert p.max_results == 20

    def test_max_results_bounds(self):
        """max_results bounds: 1-100 (ge/le)."""
        with pytest.raises(ValidationError):
            CVELookupParams(query="test", max_results=0)

        with pytest.raises(ValidationError):
            CVELookupParams(query="test", max_results=101)

        CVELookupParams(query="test", max_results=1)
        CVELookupParams(query="test", max_results=100)

    def test_query_empty_rejected(self):
        """Empty query should fail."""
        with pytest.raises(ValidationError, match="query cannot be empty"):
            CVELookupParams(query="")

        with pytest.raises(ValidationError, match="query cannot be empty"):
            CVELookupParams(query="   ")


class TestCensysHostParams:
    """Test CensysHostParams validation (extra='ignore', strict=True)."""

    def test_valid_ipv4(self):
        """Should accept valid IPv4."""
        p = CensysHostParams(ip="192.0.2.1")
        assert p.ip == "192.0.2.1"

    def test_valid_ipv6(self):
        """Should accept valid IPv6."""
        p = CensysHostParams(ip="2001:db8::1")
        assert p.ip == "2001:db8::1"

    def test_ip_validation_rejects_no_dots_or_colons(self):
        """IP must contain dots (IPv4) or colons (IPv6)."""
        with pytest.raises(ValidationError, match="ip must be IPv4.*or IPv6"):
            CensysHostParams(ip="notanip")

    def test_ip_empty_rejected(self):
        """Empty IP should fail."""
        with pytest.raises(ValidationError, match="String should have at least 3 characters"):
            CensysHostParams(ip="")

    def test_ip_whitespace_stripped(self):
        """Whitespace should be stripped."""
        p = CensysHostParams(ip="  192.0.2.1  ")
        assert p.ip == "192.0.2.1"


class TestLLMChatParams:
    """Test LLMChatParams validation (extra='ignore', strict=True)."""

    def test_valid_construction(self):
        """Should construct with minimal valid params."""
        p = LLMChatParams(
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert len(p.messages) == 1
        assert p.provider == "openai"  # default

    def test_messages_required(self):
        """messages list is required."""
        with pytest.raises(ValidationError):
            LLMChatParams()

    def test_temperature_bounds(self):
        """temperature bounds: 0-2 (if present)."""
        # Valid range
        LLMChatParams(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.0
        )
        LLMChatParams(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=2.0
        )

        # Out of bounds
        with pytest.raises(ValidationError):
            LLMChatParams(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=-0.1
            )

        with pytest.raises(ValidationError):
            LLMChatParams(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=2.1
            )


# ============================================================
# Summary Tests: Check for validation consistency
# ============================================================


class TestValidationGaps:
    """Test for validation inconsistencies and gaps.
    
    These tests document ACTUAL FINDINGS from parameter validation testing.
    """

    def test_botasaurus_missing_wait_timeout_validators(self):
        """FINDING: BotasaurusParams missing wait_time and timeout validators.
        
        CamoufoxParams has validators for these fields (0-60 and 1-120 respectively),
        but BotasaurusParams does not. This is inconsistent - both classes have
        the same fields and similar purpose.
        """
        # BotasaurusParams allows any value for wait_time and timeout
        BotasaurusParams(url="https://google.com", wait_time=-1)
        BotasaurusParams(url="https://google.com", timeout=-1)
        BotasaurusParams(url="https://google.com", wait_time=99999)

    def test_extra_field_handling_inconsistent(self):
        """FINDING: Most models use extra='ignore', only CyberscraperParams uses 'forbid'.
        
        This is inconsistent. Either all should forbid extra fields or all should
        ignore them. Currently, CyberscraperParams is stricter than similar tools.
        """
        # BotasaurusParams ignores unknown fields
        BotasaurusParams(url="https://google.com", unknown="ignored")

        # CyberscraperParams rejects unknown fields
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CyberscraperParams(url="https://google.com", unknown="rejected")

    def test_url_validation_requires_dns_resolution(self):
        """FINDING: URL validation performs actual DNS resolution.
        
        This is expensive and may fail in offline/restricted environments.
        Validators should only check format/SSRF safety, not network availability.
        """
        # Works: real domain with DNS resolution
        FetchParams(url="https://google.com")

        # Fails: domain that DNS resolves
        with pytest.raises(ValidationError):
            FetchParams(url="https://127.0.0.1")  # SSRF blocked

    def test_unicode_supported_in_string_fields(self):
        """Unicode text should be accepted in all string fields."""
        # Arabic
        DeepParams(query="البحث عن المعلومات")

        # Chinese
        CitationGraphParams(query="机器学习研究")

        # Mixed
        CompanyDiligenceParams(company_name="Société Générale")
