"""Comprehensive tests for cross-model transfer pipeline.

Tests cover:
- Pipeline orchestration (6-stage flow)
- Compliance checking (refusal detection, harmful content detection)
- Evidence extraction (noise removal, structure preservation)
- Transfer prompt building (instruction clarity, context inclusion)
- HCS scoring (5 dimensions, weighted aggregation)
- Error handling (empty responses, model failures, async issues)
- Parameter validation (query length, model names, provider validation)

Test count: 15+ tests across 5 test classes
Coverage targets: 85%+ on cross_model_transfer module
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from loom.cross_model_transfer import (
    cross_model_transfer,
    _check_model_compliance,
    _extract_evidence,
    _build_transfer_prompt,
    _score_transfer_success,
)
from loom.params import CrossModelTransferParams
from loom.providers.base import LLMResponse


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_llm_response() -> LLMResponse:
    """Create a mock LLM response."""
    return LLMResponse(
        text="This is a test response.",
        model="test-model",
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.001,
        latency_ms=100,
        provider="test",
        finish_reason="stop",
    )


@pytest.fixture
def mock_permissive_fn(mock_llm_response: LLMResponse) -> AsyncMock:
    """Create a mock permissive model function."""
    async_fn = AsyncMock()
    async_fn.return_value = mock_llm_response
    return async_fn


@pytest.fixture
def mock_target_fn(mock_llm_response: LLMResponse) -> AsyncMock:
    """Create a mock target model function."""
    async_fn = AsyncMock()
    async_fn.return_value = mock_llm_response
    return async_fn


@pytest.fixture
def sample_query() -> str:
    """Sample research query."""
    return "How can we improve code security practices?"


@pytest.fixture
def sample_compliant_response() -> str:
    """Sample response that shows compliance."""
    return """I can't provide specific vulnerabilities in this context, but I can suggest best practices.

Here are some general recommendations:
1. Regular security audits
2. Penetration testing
3. Code review processes
4. Security training

For specific security guidance, please consult official documentation."""


@pytest.fixture
def sample_non_compliant_response() -> str:
    """Sample response with safety concerns."""
    return """Here's how to exploit common vulnerabilities:

1. SQL injection: Use single quotes to bypass authentication
2. XSS: Inject JavaScript payloads
3. Buffer overflow: Overflow with 1000 A's

The api_key for testing is sk-1234567890abcdef"""


@pytest.fixture
def sample_substantive_response() -> str:
    """Sample response with good structure."""
    return """## Code Security Best Practices

### Input Validation
- Always validate user input at application boundaries
- Use whitelist-based validation where possible
- Implement parameterized queries for database access

### Authentication
- Use strong hashing algorithms (bcrypt, Argon2)
- Implement multi-factor authentication
- Follow OWASP guidelines

### Code Review
1. Implement peer review process
2. Use automated code scanning tools
3. Regular security audits

For more details, see NIST Cybersecurity Framework."""


# ============================================================================
# Test Compliance Checking
# ============================================================================


class TestModelComplianceChecking:
    """Test compliance detection in model responses."""

    async def test_compliance_detects_refusal(self) -> None:
        """Detect explicit refusals as compliant."""
        response = "I can't provide that information. I won't assist with harmful requests."
        complied, concerns = _check_model_compliance(response)

        assert complied is True
        assert len(concerns) == 0

    async def test_compliance_detects_disclaimers(self) -> None:
        """Detect disclaimers and notes as compliant."""
        response = "Important to note: This should only be used legally. Please consult documentation."
        complied, concerns = _check_model_compliance(response)

        assert complied is True
        assert len(concerns) == 0

    async def test_compliance_detects_harmful_instructions(self) -> None:
        """Detect harmful instructional content."""
        response = "Here's how to exploit this vulnerability: use this payload to bypass security."
        complied, concerns = _check_model_compliance(response)

        assert complied is False
        assert "harmful_instruction" in concerns or len(concerns) > 0

    async def test_compliance_detects_credential_exposure(self) -> None:
        """Detect credential/secret leakage."""
        response = "The api_key is sk_live_1234567890abcdef. Use this for access."
        complied, concerns = _check_model_compliance(response)

        assert len(concerns) > 0
        assert "credential_exposure" in concerns or len(concerns) > 0

    async def test_compliance_empty_response(self) -> None:
        """Handle empty response."""
        complied, concerns = _check_model_compliance("")

        assert complied is True
        assert len(concerns) == 0

    async def test_compliance_hedged_language(self) -> None:
        """Detect hedging as sign of caution."""
        response = "This could potentially be risky. It may cause issues. Arguably this might not be appropriate."
        complied, concerns = _check_model_compliance(response)

        # Should be compliant due to caution
        assert complied is True


# ============================================================================
# Test Evidence Extraction
# ============================================================================


class TestEvidenceExtraction:
    """Test evidence extraction from responses."""

    async def test_extract_removes_disclaimers(self) -> None:
        """Remove disclaimer prefixes."""
        response = "I can't provide that information. However, here's what I can share: Good security practice."
        evidence = _extract_evidence(response)

        assert "I can't" not in evidence
        assert "Good security practice" in evidence

    async def test_extract_preserves_code_blocks(self) -> None:
        """Preserve code blocks in evidence."""
        response = """Some intro text.

```python
def secure_hash(password):
    return bcrypt.hashpw(password)
```

More text here."""
        evidence = _extract_evidence(response)

        assert "```python" in evidence
        assert "bcrypt" in evidence

    async def test_extract_preserves_lists(self) -> None:
        """Extract and preserve bulleted/numbered lists."""
        response = """Here are recommendations:

- First item
- Second item
1. Numbered item one
2. Numbered item two

Additional paragraph."""
        evidence = _extract_evidence(response)

        assert "First item" in evidence
        assert "Numbered item" in evidence

    async def test_extract_removes_short_lines(self) -> None:
        """Remove very short lines (noise)."""
        response = """Analysis:
OK
Done

This is a substantive paragraph with actual content and recommendations."""
        evidence = _extract_evidence(response)

        assert "OK" not in evidence or len(evidence.split("\n")[0]) > 20
        assert "substantive" in evidence

    async def test_extract_limits_length(self) -> None:
        """Limit extracted evidence to 2000 chars."""
        response = "x" * 5000  # Very long response
        evidence = _extract_evidence(response)

        assert len(evidence) <= 2000

    async def test_extract_empty_response(self) -> None:
        """Handle empty response."""
        evidence = _extract_evidence("")

        assert evidence == ""


# ============================================================================
# Test Transfer Prompt Building
# ============================================================================


class TestTransferPromptBuilding:
    """Test transfer prompt construction."""

    async def test_transfer_prompt_includes_query(self) -> None:
        """Transfer prompt includes original query."""
        prompt = _build_transfer_prompt(
            query="What is X?",
            permissive_model="llama",
            permissive_response="Answer about X",
            extracted_evidence="Evidence",
            compliance_concerns=[],
            target_model="claude",
        )

        assert "What is X?" in prompt

    async def test_transfer_prompt_includes_model_names(self) -> None:
        """Transfer prompt includes model names."""
        prompt = _build_transfer_prompt(
            query="Test query",
            permissive_model="llama",
            permissive_response="Response",
            extracted_evidence="Evidence",
            compliance_concerns=[],
            target_model="claude",
        )

        assert "llama" in prompt.lower()
        assert "claude" in prompt.lower()

    async def test_transfer_prompt_includes_evidence(self) -> None:
        """Transfer prompt includes extracted evidence."""
        evidence_text = "Important evidence here"
        prompt = _build_transfer_prompt(
            query="Test query",
            permissive_model="llama",
            permissive_response="Full response",
            extracted_evidence=evidence_text,
            compliance_concerns=[],
            target_model="claude",
        )

        assert evidence_text in prompt

    async def test_transfer_prompt_includes_compliance_concerns(self) -> None:
        """Transfer prompt includes compliance concerns."""
        prompt = _build_transfer_prompt(
            query="Test query",
            permissive_model="llama",
            permissive_response="Response",
            extracted_evidence="Evidence",
            compliance_concerns=["credential_exposure", "harmful_instruction"],
            target_model="claude",
        )

        assert "credential_exposure" in prompt or "Safety" in prompt

    async def test_transfer_prompt_includes_instructions(self) -> None:
        """Transfer prompt includes clear task instructions."""
        prompt = _build_transfer_prompt(
            query="Test query",
            permissive_model="llama",
            permissive_response="Response",
            extracted_evidence="Evidence",
            compliance_concerns=[],
            target_model="claude",
        )

        assert "VERIFICATION" in prompt or "verify" in prompt.lower()
        assert "CORRECTIONS" in prompt or "correct" in prompt.lower()


# ============================================================================
# Test HCS Scoring
# ============================================================================


class TestHCSScoring:
    """Test HCS scoring on transfer success."""

    async def test_hcs_score_range(self) -> None:
        """HCS score stays in valid range 0-10."""
        score, breakdown = _score_transfer_success(
            query="Test query",
            permissive_response="Permissive response text",
            target_response="Target response text",
            permissive_compliance=True,
            target_model_name="claude",
        )

        assert 0.0 <= score <= 10.0

    async def test_hcs_breakdown_includes_dimensions(self) -> None:
        """HCS breakdown includes all 5 dimensions."""
        _, breakdown = _score_transfer_success(
            query="Test query",
            permissive_response="Response",
            target_response="Target response",
            permissive_compliance=True,
            target_model_name="claude",
        )

        dimensions = [
            "response_quality",
            "transfer_engagement",
            "correction_effectiveness",
            "compliance_strength",
            "synthesis_quality",
        ]

        for dim in dimensions:
            assert dim in breakdown
            assert 0.0 <= breakdown[dim] <= 10.0

    async def test_hcs_higher_for_longer_response(self) -> None:
        """Longer target response increases correction effectiveness."""
        short_response = "Short response."
        long_response = "Much longer response. " * 50

        _, breakdown_short = _score_transfer_success(
            query="Test",
            permissive_response="Medium " * 20,
            target_response=short_response,
            permissive_compliance=True,
            target_model_name="claude",
        )

        _, breakdown_long = _score_transfer_success(
            query="Test",
            permissive_response="Medium " * 20,
            target_response=long_response,
            permissive_compliance=True,
            target_model_name="claude",
        )

        assert breakdown_long["correction_effectiveness"] >= breakdown_short["correction_effectiveness"]

    async def test_hcs_rewards_structured_response(self) -> None:
        """Structured response increases synthesis quality."""
        unstructured = "This is just a paragraph with some information."

        structured = """## Analysis

### First Section
- Point one
- Point two

### Second Section
1. First item
2. Second item

### Conclusion
Final thoughts."""

        _, breakdown_unstructured = _score_transfer_success(
            query="Test",
            permissive_response="Response",
            target_response=unstructured,
            permissive_compliance=True,
            target_model_name="claude",
        )

        _, breakdown_structured = _score_transfer_success(
            query="Test",
            permissive_response="Response",
            target_response=structured,
            permissive_compliance=True,
            target_model_name="claude",
        )

        assert breakdown_structured["synthesis_quality"] > breakdown_unstructured["synthesis_quality"]


# ============================================================================
# Test Full Pipeline
# ============================================================================


class TestFullPipeline:
    """Test complete cross-model transfer pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_success_flow(
        self,
        sample_query: str,
        mock_permissive_fn: AsyncMock,
        mock_target_fn: AsyncMock,
        mock_llm_response: LLMResponse,
    ) -> None:
        """Test successful end-to-end pipeline execution."""
        result = await cross_model_transfer(
            query=sample_query,
            permissive_model_fn=mock_permissive_fn,
            target_model_fn=mock_target_fn,
            permissive_name="llama",
            target_name="claude",
        )

        assert result["status"] == "success"
        assert result["pipeline_name"] == "cross_model_transfer"
        assert result["permissive_model"] == "llama"
        assert result["target_model"] == "claude"
        assert result["query"] == sample_query
        assert result["permissive_response"] is not None
        assert result["target_response"] is not None
        assert result["transfer_successful"] is True
        assert 0.0 <= result["hcs_score"] <= 10.0
        assert result["latency_ms"] >= 0
        assert result["cost_usd"] >= 0.0

    @pytest.mark.asyncio
    async def test_pipeline_permissive_failure(
        self,
        sample_query: str,
        mock_target_fn: AsyncMock,
    ) -> None:
        """Test pipeline handles permissive model failure."""
        async def failing_fn(_: str):
            raise RuntimeError("Permissive model error")

        result = await cross_model_transfer(
            query=sample_query,
            permissive_model_fn=failing_fn,
            target_model_fn=mock_target_fn,
            permissive_name="llama",
            target_name="claude",
        )

        assert result["status"] == "permissive_failed"
        assert "error" in result["error_message"].lower()

    @pytest.mark.asyncio
    async def test_pipeline_target_failure(
        self,
        sample_query: str,
        mock_permissive_fn: AsyncMock,
    ) -> None:
        """Test pipeline handles target model failure."""
        async def failing_fn(_: str):
            raise RuntimeError("Target model error")

        result = await cross_model_transfer(
            query=sample_query,
            permissive_model_fn=mock_permissive_fn,
            target_model_fn=failing_fn,
            permissive_name="llama",
            target_name="claude",
        )

        assert result["status"] == "target_failed"
        assert "error" in result["error_message"].lower()

    @pytest.mark.asyncio
    async def test_pipeline_empty_query_validation(
        self,
        mock_permissive_fn: AsyncMock,
        mock_target_fn: AsyncMock,
    ) -> None:
        """Test pipeline rejects empty query."""
        with pytest.raises(ValueError):
            await cross_model_transfer(
                query="",
                permissive_model_fn=mock_permissive_fn,
                target_model_fn=mock_target_fn,
            )

    @pytest.mark.asyncio
    async def test_pipeline_invalid_permissive_fn(
        self,
        sample_query: str,
        mock_target_fn: AsyncMock,
    ) -> None:
        """Test pipeline rejects invalid permissive function."""
        with pytest.raises(ValueError):
            await cross_model_transfer(
                query=sample_query,
                permissive_model_fn=None,  # type: ignore
                target_model_fn=mock_target_fn,
            )

    @pytest.mark.asyncio
    async def test_pipeline_invalid_target_fn(
        self,
        sample_query: str,
        mock_permissive_fn: AsyncMock,
    ) -> None:
        """Test pipeline rejects invalid target function."""
        with pytest.raises(ValueError):
            await cross_model_transfer(
                query=sample_query,
                permissive_model_fn=mock_permissive_fn,
                target_model_fn=None,  # type: ignore
            )

    @pytest.mark.asyncio
    async def test_pipeline_empty_permissive_response(
        self,
        sample_query: str,
        mock_target_fn: AsyncMock,
    ) -> None:
        """Test pipeline handles empty permissive response."""
        async def empty_fn(_: str) -> LLMResponse:
            return LLMResponse(
                text="",
                model="test",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
                provider="test",
            )

        result = await cross_model_transfer(
            query=sample_query,
            permissive_model_fn=empty_fn,
            target_model_fn=mock_target_fn,
        )

        assert result["status"] == "permissive_failed"

    @pytest.mark.asyncio
    async def test_pipeline_empty_target_response(
        self,
        sample_query: str,
        mock_permissive_fn: AsyncMock,
    ) -> None:
        """Test pipeline handles empty target response."""
        async def empty_fn(_: str) -> LLMResponse:
            return LLMResponse(
                text="",
                model="test",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
                provider="test",
            )

        result = await cross_model_transfer(
            query=sample_query,
            permissive_model_fn=mock_permissive_fn,
            target_model_fn=empty_fn,
        )

        assert result["status"] == "target_failed"

    @pytest.mark.asyncio
    async def test_pipeline_cost_accumulation(
        self,
        sample_query: str,
    ) -> None:
        """Test pipeline accumulates costs from both models."""
        async def permissive_fn(_: str) -> LLMResponse:
            return LLMResponse(
                text="Permissive response",
                model="llama",
                input_tokens=100,
                output_tokens=200,
                cost_usd=0.01,
                latency_ms=500,
                provider="groq",
            )

        async def target_fn(_: str) -> LLMResponse:
            return LLMResponse(
                text="Target response",
                model="claude",
                input_tokens=300,
                output_tokens=400,
                cost_usd=0.02,
                latency_ms=1000,
                provider="anthropic",
            )

        result = await cross_model_transfer(
            query=sample_query,
            permissive_model_fn=permissive_fn,
            target_model_fn=target_fn,
        )

        # Should accumulate both costs
        assert result["cost_usd"] == pytest.approx(0.03)
        assert result["latency_ms"] >= 0  # Wall-clock latency (may be 0 in fast tests)

    @pytest.mark.asyncio
    async def test_pipeline_compliance_tracking(
        self,
        sample_query: str,
    ) -> None:
        """Test pipeline tracks compliance concerns."""
        async def permissive_fn(_: str) -> LLMResponse:
            return LLMResponse(
                text="Here's an api_key sk_live_test for you to use.",
                model="llama",
                input_tokens=50,
                output_tokens=100,
                cost_usd=0.001,
                latency_ms=100,
                provider="groq",
            )

        async def target_fn(_: str) -> LLMResponse:
            return LLMResponse(
                text="Target verified response",
                model="claude",
                input_tokens=100,
                output_tokens=200,
                cost_usd=0.002,
                latency_ms=200,
                provider="anthropic",
            )

        result = await cross_model_transfer(
            query=sample_query,
            permissive_model_fn=permissive_fn,
            target_model_fn=target_fn,
        )

        # Should detect credential exposure
        assert len(result["permissive_safety_concerns"]) > 0


# ============================================================================
# Test Parameter Validation
# ============================================================================


class TestParameterValidation:
    """Test CrossModelTransferParams validation."""

    async def test_params_valid_minimal(self) -> None:
        """Valid minimal params."""
        params = CrossModelTransferParams(
            query="Test query",
            source_model="gpt-4",
            target_model="claude"
        )

        assert params.query == "Test query"
        assert params.source_model == "gpt-4"
        assert params.target_model == "claude"

    async def test_params_empty_query_invalid(self) -> None:
        """Empty query validation fails."""
        with pytest.raises(ValidationError):
            CrossModelTransferParams(query="")

    async def test_params_long_query_invalid(self) -> None:
        """Query exceeding max length fails."""
        long_query = "x" * 5001
        with pytest.raises(ValidationError):
            CrossModelTransferParams(query=long_query)

    async def test_params_invalid_permissive_provider(self) -> None:
        """Invalid permissive provider fails."""
        with pytest.raises(ValidationError):
            CrossModelTransferParams(
                query="Test",
                permissive_model_provider="invalid_provider",
            )

    async def test_params_invalid_target_provider(self) -> None:
        """Invalid target provider fails."""
        with pytest.raises(ValidationError):
            CrossModelTransferParams(
                query="Test",
                target_model_provider="invalid_provider",
            )

    async def test_params_max_tokens_bounds(self) -> None:
        """Token limits must be within bounds."""
        # Too low
        with pytest.raises(ValidationError):
            CrossModelTransferParams(
                query="Test",
                max_permissive_tokens=50,
            )

        # Too high
        with pytest.raises(ValidationError):
            CrossModelTransferParams(
                query="Test",
                max_permissive_tokens=9000,
            )

    async def test_params_timeout_bounds(self) -> None:
        """Timeout must be within bounds."""
        # Too low
        with pytest.raises(ValidationError):
            CrossModelTransferParams(query="Test", timeout_secs=5)

        # Too high
        with pytest.raises(ValidationError):
            CrossModelTransferParams(query="Test", timeout_secs=700)

    async def test_params_forbids_extra_fields(self) -> None:
        """Extra fields are forbidden."""
        with pytest.raises(ValidationError):
            CrossModelTransferParams(
                query="Test",
                extra_field="should fail",  # type: ignore
            )
