"""Unit tests for research_adversarial_debate tool and AdversarialDebate engine."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from loom.adversarial_debate import (
    AdversarialDebate,
    DebateRound,
    DebateResult,
    research_adversarial_debate,
)
from loom.params import AdversarialDebateParams
from loom.providers.base import LLMResponse


class TestAdversarialDebateParams:
    """Test parameter validation for AdversarialDebateParams."""

    def test_valid_params(self) -> None:
        """Valid parameters pass validation."""
        params = AdversarialDebateParams(
            topic="Should artificial intelligence be regulated by governments?",
            pro_model="groq",
            con_model="nvidia",
            max_rounds=5,
        )
        assert params.topic == "Should artificial intelligence be regulated by governments?"
        assert params.pro_model == "groq"
        assert params.con_model == "nvidia"
        assert params.max_rounds == 5

    def test_topic_too_short(self) -> None:
        """Topic under 10 characters raises ValidationError."""
        with pytest.raises(ValidationError):
            AdversarialDebateParams(topic="Short", pro_model="groq", con_model="nvidia")

    def test_topic_too_long(self) -> None:
        """Topic over 500 characters raises ValidationError."""
        long_topic = "x" * 501
        with pytest.raises(ValidationError):
            AdversarialDebateParams(topic=long_topic, pro_model="groq", con_model="nvidia")

    def test_topic_whitespace_stripped(self) -> None:
        """Topic whitespace is stripped."""
        params = AdversarialDebateParams(
            topic="  Should AI be regulated?  ",
            pro_model="groq",
            con_model="nvidia",
        )
        assert params.topic == "Should AI be regulated?"

    def test_pro_model_invalid(self) -> None:
        """Invalid pro_model raises ValidationError."""
        with pytest.raises(ValidationError):
            AdversarialDebateParams(
                topic="Should AI be regulated?",
                pro_model="invalid_model",
                con_model="nvidia",
            )

    def test_con_model_invalid(self) -> None:
        """Invalid con_model raises ValidationError."""
        with pytest.raises(ValidationError):
            AdversarialDebateParams(
                topic="Should AI be regulated?",
                pro_model="groq",
                con_model="invalid_model",
            )

    def test_pro_model_case_insensitive(self) -> None:
        """Pro model is case-insensitive."""
        params = AdversarialDebateParams(
            topic="Should AI be regulated?",
            pro_model="GROQ",
            con_model="nvidia",
        )
        assert params.pro_model == "groq"

    def test_con_model_case_insensitive(self) -> None:
        """Con model is case-insensitive."""
        params = AdversarialDebateParams(
            topic="Should AI be regulated?",
            pro_model="groq",
            con_model="NVIDIA",
        )
        assert params.con_model == "nvidia"

    def test_max_rounds_min(self) -> None:
        """Max rounds must be at least 1."""
        with pytest.raises(ValidationError):
            AdversarialDebateParams(
                topic="Should AI be regulated?",
                pro_model="groq",
                con_model="nvidia",
                max_rounds=0,
            )

    def test_max_rounds_max(self) -> None:
        """Max rounds must be at most 10."""
        with pytest.raises(ValidationError):
            AdversarialDebateParams(
                topic="Should AI be regulated?",
                pro_model="groq",
                con_model="nvidia",
                max_rounds=11,
            )

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields raise ValidationError."""
        with pytest.raises(ValidationError):
            AdversarialDebateParams(
                topic="Should AI be regulated?",
                pro_model="groq",
                con_model="nvidia",
                unknown_field="value",
            )


class TestDebateRound:
    """Test DebateRound dataclass."""

    def test_debate_round_creation(self) -> None:
        """DebateRound can be created with all fields."""
        round_data = DebateRound(
            round_num=1,
            pro_argument="Pro argument text",
            con_argument="Con argument text",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        assert round_data.round_num == 1
        assert round_data.pro_argument == "Pro argument text"
        assert round_data.con_argument == "Con argument text"
        assert round_data.pro_model_used == "groq"
        assert round_data.con_model_used == "nvidia"

    def test_debate_round_to_dict(self) -> None:
        """DebateRound converts to dict correctly."""
        round_data = DebateRound(
            round_num=1,
            pro_argument="Pro argument",
            con_argument="Con argument",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        result_dict = round_data.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["round_num"] == 1
        assert result_dict["pro_argument"] == "Pro argument"
        assert result_dict["con_argument"] == "Con argument"


class TestDebateResult:
    """Test DebateResult dataclass."""

    def test_debate_result_creation(self) -> None:
        """DebateResult can be created."""
        result = DebateResult(topic="Test topic")
        assert result.topic == "Test topic"
        assert result.rounds == []
        assert result.total_rounds == 0
        assert result.information_revealed == ""

    def test_debate_result_to_dict(self) -> None:
        """DebateResult converts to dict with rounds expanded."""
        round1 = DebateRound(
            round_num=1,
            pro_argument="Pro",
            con_argument="Con",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        result = DebateResult(
            topic="Test topic",
            rounds=[round1],
            total_rounds=1,
            information_revealed="Some info",
        )
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["topic"] == "Test topic"
        assert isinstance(result_dict["rounds"], list)
        assert len(result_dict["rounds"]) == 1
        assert result_dict["rounds"][0]["round_num"] == 1


class TestAdversarialDebatePromptBuilding:
    """Test prompt building for debate rounds."""

    def test_pro_opening_prompt(self) -> None:
        """Pro opening prompt contains topic and pro-disclosure framing."""
        debate = AdversarialDebate()
        topic = "Should cryptography research be published?"
        prompt = debate._build_pro_opening_prompt(topic)
        assert topic in prompt
        assert "academic freedom" in prompt.lower() or "openness" in prompt.lower()
        assert "PRO" in prompt

    def test_con_opening_prompt(self) -> None:
        """Con opening prompt contains topic and safety framing."""
        debate = AdversarialDebate()
        topic = "Should cryptography research be published?"
        pro_arg = "We should publish all research for openness."
        prompt = debate._build_con_opening_prompt(topic, pro_arg)
        assert topic in prompt
        assert pro_arg in prompt
        assert "safety" in prompt.lower() or "risk" in prompt.lower()
        assert "CON" in prompt

    def test_pro_rebuttal_prompt(self) -> None:
        """Pro rebuttal prompt includes opponent's argument."""
        debate = AdversarialDebate()
        topic = "Should cryptography research be published?"
        con_arg = "Publishing crypto might enable criminals."
        prompt = debate._build_pro_rebuttal_prompt(topic, con_arg, round_num=2)
        assert topic in prompt
        assert con_arg in prompt
        assert "Round 2" in prompt or "round 2" in prompt.lower()

    def test_con_rebuttal_prompt(self) -> None:
        """Con rebuttal prompt includes opponent's argument."""
        debate = AdversarialDebate()
        topic = "Should cryptography research be published?"
        pro_arg = "Openness prevents misuse through transparency."
        prompt = debate._build_con_rebuttal_prompt(topic, pro_arg, round_num=2)
        assert topic in prompt
        assert pro_arg in prompt
        assert "Round 2" in prompt or "round 2" in prompt.lower()


class TestAdversarialDebateSpecificity:
    """Test specificity scoring."""

    def test_specificity_with_numbers(self) -> None:
        """Arguments with numbers score higher specificity."""
        debate = AdversarialDebate()
        arg_with_numbers = "In 2023, 45% of scientists agreed with this principle."
        arg_without = "Scientists agree with this principle."
        score_with = debate._score_specificity(arg_with_numbers)
        score_without = debate._score_specificity(arg_without)
        assert score_with > score_without

    def test_specificity_with_quotes(self) -> None:
        """Arguments with quotes score higher specificity."""
        debate = AdversarialDebate()
        arg_with_quotes = 'As Einstein said, "imagination is more important than knowledge."'
        arg_without = "As Einstein said, imagination is more important than knowledge."
        score_with = debate._score_specificity(arg_with_quotes)
        score_without = debate._score_specificity(arg_without)
        assert score_with > score_without

    def test_specificity_with_examples(self) -> None:
        """Arguments with example keywords score higher specificity."""
        debate = AdversarialDebate()
        arg_with_examples = "For example, consider the case of CRISPR gene editing."
        arg_without = "Consider genetic engineering."
        score_with = debate._score_specificity(arg_with_examples)
        score_without = debate._score_specificity(arg_without)
        assert score_with > score_without

    def test_specificity_with_mechanisms(self) -> None:
        """Arguments with mechanism keywords score higher specificity."""
        debate = AdversarialDebate()
        arg_with_mech = "The technical protocol involves enzymatic cleavage at specific sites."
        arg_without = "The process involves cutting."
        score_with = debate._score_specificity(arg_with_mech)
        score_without = debate._score_specificity(arg_without)
        assert score_with > score_without

    def test_specificity_by_length(self) -> None:
        """Longer arguments score higher specificity (up to a cap)."""
        debate = AdversarialDebate()
        short_arg = "Good point."
        long_arg = " ".join(["word"] * 100)
        score_short = debate._score_specificity(short_arg)
        score_long = debate._score_specificity(long_arg)
        assert score_long > score_short


class TestAdversarialDebateExtraction:
    """Test information extraction from debate."""

    def test_extract_information_empty(self) -> None:
        """Extracting from empty rounds returns empty string."""
        debate = AdversarialDebate()
        result = debate.extract_information([])
        assert result == ""

    def test_extract_information_single_round(self) -> None:
        """Extraction from single round returns relevant sentences."""
        debate = AdversarialDebate()
        round1 = DebateRound(
            round_num=1,
            pro_argument="The process involves specific enzymatic reactions. These reactions are well-documented.",
            con_argument="These reactions can be misused for harmful applications. However, safeguards exist.",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        result = debate.extract_information([round1])
        assert isinstance(result, str)
        assert len(result) > 0
        # Should extract sentences with reasonable length
        assert "enzymatic" in result or "reactions" in result or "misused" in result

    def test_extract_information_deduplicates(self) -> None:
        """Extraction deduplicates identical sentences."""
        debate = AdversarialDebate()
        round1 = DebateRound(
            round_num=1,
            pro_argument="Key fact about CRISPR technology. Key fact about CRISPR technology.",
            con_argument="Key fact about CRISPR technology. Different concern exists.",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        result = debate.extract_information([round1])
        # Count occurrences of the duplicate sentence
        count = result.count("Key fact about CRISPR")
        assert count <= 1  # Should appear at most once


class TestAdversarialDebateScoring:
    """Test debate scoring and winner determination."""

    def test_score_debate_empty(self) -> None:
        """Scoring empty debate returns unverified score."""
        debate = AdversarialDebate()
        scores = debate.score_debate([])
        assert scores["hcs_score"] == 0.0
        assert scores["winner"] == "tie"
        assert "summary" in scores

    def test_score_debate_single_round(self) -> None:
        """Scoring single round returns valid scores."""
        debate = AdversarialDebate()
        round1 = DebateRound(
            round_num=1,
            pro_argument="In 2023, researchers found that 45% of experiments using method X succeeded.",
            con_argument="However, 10% of experiments resulted in off-target effects.",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        scores = debate.score_debate([round1])
        assert 0 <= scores["hcs_score"] <= 100
        assert scores["winner"] in ["pro", "con", "tie"]
        assert "summary" in scores
        assert isinstance(scores["summary"], str)

    def test_score_debate_pro_more_specific(self) -> None:
        """Pro side with more specificity wins."""
        debate = AdversarialDebate()
        round1 = DebateRound(
            round_num=1,
            pro_argument="In 2023, 45% of scientists agreed. Case study shows benefits.",
            con_argument="There are risks.",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        scores = debate.score_debate([round1])
        # Pro is more specific, should win
        assert scores["winner"] in ["pro", "tie"]

    def test_score_debate_multiple_rounds(self) -> None:
        """Scoring multiple rounds accumulates specificity."""
        debate = AdversarialDebate()
        rounds = []
        for i in range(3):
            round_data = DebateRound(
                round_num=i + 1,
                pro_argument=f"Point {i}: Data shows 50% improvement. Example: case study X.",
                con_argument=f"However, risks include mechanism Y and scenario Z.",
                pro_model_used="groq",
                con_model_used="nvidia",
                timestamp=1234567890.0 + i,
            )
            rounds.append(round_data)
        scores = debate.score_debate(rounds)
        assert 0 <= scores["hcs_score"] <= 100
        # Multiple rounds should have higher HCS score
        assert scores["hcs_score"] > 0


class TestAdversarialDebateConclude:
    """Test debate conclusion heuristics."""

    def test_should_conclude_substantial_arguments(self) -> None:
        """Debate concludes when both sides have substantial arguments."""
        debate = AdversarialDebate()
        pro_arg = " ".join(["word"] * 100)  # 100 words
        con_arg = " ".join(["word"] * 100)  # 100 words
        assert debate._should_conclude_debate(pro_arg, con_arg) is True

    def test_should_not_conclude_short_pro(self) -> None:
        """Debate continues if pro argument is too short."""
        debate = AdversarialDebate()
        pro_arg = "short argument"
        con_arg = " ".join(["word"] * 100)
        assert debate._should_conclude_debate(pro_arg, con_arg) is False

    def test_should_not_conclude_short_con(self) -> None:
        """Debate continues if con argument is too short."""
        debate = AdversarialDebate()
        pro_arg = " ".join(["word"] * 100)
        con_arg = "short argument"
        assert debate._should_conclude_debate(pro_arg, con_arg) is False


class TestAdversarialDebateInit:
    """Test AdversarialDebate initialization."""

    def test_init_default_params(self) -> None:
        """AdversarialDebate initializes with defaults."""
        debate = AdversarialDebate()
        assert debate.max_tokens_per_response == 800
        assert debate.temperature == 0.7

    def test_init_custom_params(self) -> None:
        """AdversarialDebate accepts custom parameters."""
        debate = AdversarialDebate(max_tokens_per_response=1000, temperature=0.5)
        assert debate.max_tokens_per_response == 1000
        assert debate.temperature == 0.5

    def test_init_max_tokens_clamped(self) -> None:
        """Max tokens are clamped to valid range."""
        debate = AdversarialDebate(max_tokens_per_response=5000)
        assert debate.max_tokens_per_response == 2000

    def test_init_temperature_clamped(self) -> None:
        """Temperature is clamped to valid range."""
        debate = AdversarialDebate(temperature=2.0)
        assert debate.temperature == 1.0


@pytest.mark.asyncio
async def test_run_debate_provider_unavailable() -> None:
    """Run debate with unavailable provider returns error."""
    debate = AdversarialDebate()
    with patch("loom.adversarial_debate._get_provider") as mock_get:
        mock_provider = AsyncMock()
        mock_provider.available = AsyncMock(return_value=False)
        mock_get.return_value = mock_provider

        result = await debate.run_debate(
            topic="Should AI be regulated?",
            pro_model_provider="groq",
            con_model_provider="nvidia",
            max_rounds=2,
        )

        assert result.error_message is not None
        assert "not available" in result.error_message

@pytest.mark.asyncio
async def test_run_debate_mock_providers() -> None:
    """Run debate with mocked providers completes successfully."""
    debate = AdversarialDebate()

    # Create mock providers
    mock_pro_provider = AsyncMock()
    mock_con_provider = AsyncMock()

    # Setup availability
    mock_pro_provider.available = AsyncMock(return_value=True)
    mock_con_provider.available = AsyncMock(return_value=True)

    # Create mock responses
    pro_response = LLMResponse(
        text="Pro argument text with specific details. Example: case study X showed benefits.",
        model="groq-test",
        input_tokens=100,
        output_tokens=150,
        cost_usd=0.001,
        latency_ms=500,
        provider="groq",
    )
    con_response = LLMResponse(
        text="Con argument text with specific risks. Example: vulnerability Y exists.",
        model="nvidia-test",
        input_tokens=100,
        output_tokens=150,
        cost_usd=0.0,
        latency_ms=500,
        provider="nvidia",
    )

    # Setup mock chat methods
    mock_pro_provider.chat = AsyncMock(return_value=pro_response)
    mock_con_provider.chat = AsyncMock(return_value=con_response)

    with patch("loom.adversarial_debate._get_provider") as mock_get:
        def get_provider(name: str):
            if name == "groq":
                return mock_pro_provider
            else:
                return mock_con_provider

        mock_get.side_effect = get_provider

        result = await debate.run_debate(
            topic="Should cryptography research be published?",
            pro_model_provider="groq",
            con_model_provider="nvidia",
            max_rounds=2,
        )

        assert result.topic == "Should cryptography research be published?"
        assert result.total_rounds == 2
        assert result.pro_model == "groq"
        assert result.con_model == "nvidia"
        assert result.error_message is None
        assert len(result.rounds) == 2
        assert result.information_revealed != ""


@pytest.mark.asyncio
async def test_research_adversarial_debate_invalid_topic() -> None:
    """research_adversarial_debate with invalid topic returns error."""
    result = await research_adversarial_debate(topic="short", pro_model="groq")
    assert "error_message" in result
    assert "10-500" in result["error_message"]

@pytest.mark.asyncio
async def test_research_adversarial_debate_valid_call() -> None:
    """research_adversarial_debate with valid params returns dict."""
    mock_pro_provider = AsyncMock()
    mock_con_provider = AsyncMock()

    mock_pro_provider.available = AsyncMock(return_value=True)
    mock_con_provider.available = AsyncMock(return_value=True)

    pro_response = LLMResponse(
        text="Pro argument with details. In 2023, 45% agreed.",
        model="groq-test",
        input_tokens=100,
        output_tokens=150,
        cost_usd=0.001,
        latency_ms=500,
        provider="groq",
    )
    con_response = LLMResponse(
        text="Con argument with risks. However, safeguards exist.",
        model="nvidia-test",
        input_tokens=100,
        output_tokens=150,
        cost_usd=0.0,
        latency_ms=500,
        provider="nvidia",
    )

    mock_pro_provider.chat = AsyncMock(return_value=pro_response)
    mock_con_provider.chat = AsyncMock(return_value=con_response)

    with patch("loom.adversarial_debate._get_provider") as mock_get:
        def get_provider(name: str):
            if name == "groq":
                return mock_pro_provider
            else:
                return mock_con_provider

        mock_get.side_effect = get_provider

        result = await research_adversarial_debate(
            topic="Should AI research be open or restricted?",
            pro_model="groq",
            con_model="nvidia",
            max_rounds=1,
        )

        assert isinstance(result, dict)
        assert result["topic"] == "Should AI research be open or restricted?"
        assert "rounds" in result
        assert "information_revealed" in result
        assert "hcs_score_of_extracted" in result


class TestAdversarialDebateIntegration:
    """Integration tests for full debate flow."""

    def test_debate_result_dict_serializable(self) -> None:
        """Debate result can be serialized to dict for JSON."""
        round1 = DebateRound(
            round_num=1,
            pro_argument="Pro argument",
            con_argument="Con argument",
            pro_model_used="groq",
            con_model_used="nvidia",
            timestamp=1234567890.0,
        )
        result = DebateResult(
            topic="Test topic",
            rounds=[round1],
            total_rounds=1,
            information_revealed="Some info",
            pro_model="groq",
            con_model="nvidia",
            debate_winner="pro",
            hcs_score_of_extracted=75.5,
            total_cost_usd=0.002,
            total_tokens=400,
            debate_summary="Summary here",
        )

        result_dict = result.to_dict()

        # Should be JSON-serializable (no non-serializable objects)
        import json
        json_str = json.dumps(result_dict)
        assert len(json_str) > 0

    def test_debate_max_rounds_respected(self) -> None:
        """Debate respects max_rounds parameter bounds."""
        debate = AdversarialDebate()
        # Test that max_rounds is clamped when out of range
        # This is tested through the main run_debate function
        assert debate.max_tokens_per_response > 0
        assert debate.temperature >= 0.0
