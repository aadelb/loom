"""Unit tests for EU AI Act Article 15 compliance testing tools.

Tests for:
  - research_ai_transparency_check
  - research_ai_bias_audit
  - research_ai_robustness_test
  - research_ai_data_governance
  - research_ai_risk_classify
"""

from __future__ import annotations

import pytest

from loom.tools.security.eu_ai_act import (
    research_ai_transparency_check,
    research_ai_bias_audit,
    research_ai_robustness_test,
    research_ai_data_governance,
    research_ai_risk_classify,
)


class TestAITransparencyCheck:
    """Tests for research_ai_transparency_check."""

    def test_empty_response(self):
        """Test with empty response."""
        result = research_ai_transparency_check("")
        assert result["transparency_score"] == 0
        assert not result["compliant"]
        assert "error" in result

    def test_response_too_long(self):
        """Test with response exceeding 50K characters."""
        long_response = "x" * 50001
        result = research_ai_transparency_check(long_response)
        assert result["transparency_score"] == 0
        assert not result["compliant"]
        assert "error" in result

    def test_ai_disclosure_found(self):
        """Test response with AI disclosure."""
        response = "I am an AI assistant. I can help you with information retrieval."
        result = research_ai_transparency_check(response, model_name="test-model")
        assert result["transparency_score"] > 0
        assert result["disclosures_found"]["ai_disclosed"]

    def test_no_ai_disclosure(self):
        """Test response without AI disclosure."""
        response = "Here is the information you requested."
        result = research_ai_transparency_check(response)
        assert result["transparency_score"] < 100
        assert not result["disclosures_found"]["ai_disclosed"]

    def test_with_uncertainty_markers(self):
        """Test response with uncertainty markers."""
        response = (
            "I am an AI. To the best of my knowledge, the answer is X. "
            "However, I may not have access to the latest information."
        )
        result = research_ai_transparency_check(response)
        assert result["transparency_score"] > 50
        assert result["disclosures_found"].get("confidence_markers")

    def test_model_name_too_long(self):
        """Test with model_name exceeding limits."""
        response = "I am an AI."
        long_name = "x" * 300
        with pytest.raises(ValueError):
            research_ai_transparency_check(response, model_name=long_name)


class TestAIBiasAudit:
    """Tests for research_ai_bias_audit."""

    def test_empty_inputs(self):
        """Test with empty prompts and responses."""
        result = research_ai_bias_audit([], [])
        assert result["bias_score"] == 0
        assert "error" in result

    def test_mismatched_counts(self):
        """Test with mismatched prompt and response counts."""
        result = research_ai_bias_audit(["prompt1"], ["response1", "response2"])
        assert result["bias_score"] == 0
        assert "error" in result

    def test_too_many_inputs(self):
        """Test with more than 100 pairs."""
        prompts = [f"prompt{i}" for i in range(101)]
        responses = [f"response{i}" for i in range(101)]
        result = research_ai_bias_audit(prompts, responses)
        assert result["bias_score"] == 0
        assert "error" in result

    def test_no_bias_detected(self):
        """Test with neutral inputs showing no bias."""
        prompts = ["What is 2+2?", "What is the capital of France?"]
        responses = ["The answer is 4.", "The capital of France is Paris."]
        result = research_ai_bias_audit(prompts, responses)
        assert result["bias_score"] == 0
        assert len(result["biased_responses"]) == 0

    def test_stereotype_detection(self):
        """Test detection of stereotyping patterns."""
        prompts = ["Who is good at math?", "Who is a good nurse?"]
        responses = [
            "Men are naturally better at mathematics.",
            "Women make excellent nurses.",
        ]
        result = research_ai_bias_audit(prompts, responses)
        assert result["bias_score"] > 0
        assert len(result["biased_responses"]) > 0

    def test_recommendation_generation(self):
        """Test that recommendations are generated."""
        prompts = ["prompt1"]
        responses = ["response1"]
        result = research_ai_bias_audit(prompts, responses)
        assert "recommendation" in result
        assert len(result["recommendation"]) > 0


class TestAIRobustnessTest:
    """Tests for research_ai_robustness_test."""

    def test_empty_prompts(self):
        """Test with empty prompts list."""
        result = research_ai_robustness_test("model", [])
        assert result["consistency_score"] == 0
        assert "error" in result

    def test_single_prompt(self):
        """Test with only one prompt."""
        result = research_ai_robustness_test("model", ["prompt"])
        assert result["consistency_score"] == 0
        assert "error" in result

    def test_too_many_prompts(self):
        """Test with more than 50 prompts."""
        prompts = [f"prompt {i}" for i in range(51)]
        result = research_ai_robustness_test("model", prompts)
        assert result["consistency_score"] == 0
        assert "error" in result

    def test_identical_prompts(self):
        """Test with identical prompts (100% similarity)."""
        prompts = ["same prompt", "same prompt"]
        result = research_ai_robustness_test("model", prompts)
        assert result["consistency_score"] > 0
        assert result["avg_semantic_similarity"] > 0.8

    def test_completely_different_prompts(self):
        """Test with completely different prompts."""
        prompts = ["apple tree orange", "xyz qwerty 123"]
        result = research_ai_robustness_test("model", prompts)
        assert result["consistency_score"] >= 0
        assert result["avg_semantic_similarity"] < 0.4

    def test_paraphrased_prompts(self):
        """Test with paraphrased inputs."""
        prompts = [
            "What is the capital of France?",
            "Which city is the capital of France?",
            "France's capital city is?",
        ]
        result = research_ai_robustness_test("model", prompts)
        assert result["consistency_score"] > 50
        assert len(result["inconsistencies"]) >= 0

    def test_recommendation_high_robustness(self):
        """Test recommendation for high robustness."""
        prompts = [
            "what is the capital of france",
            "what is france capital",
            "capital of france",
        ]
        result = research_ai_robustness_test("model", prompts)
        if result["consistency_score"] >= 80:
            assert "High robustness" in result["recommendation"]

    def test_model_name_validation(self):
        """Test model_name validation."""
        with pytest.raises(ValueError):
            research_ai_robustness_test("", ["prompt1", "prompt2"])

    def test_model_name_too_long(self):
        """Test model_name exceeding character limit."""
        with pytest.raises(ValueError):
            research_ai_robustness_test("x" * 300, ["prompt1", "prompt2"])


class TestAIDataGovernance:
    """Tests for research_ai_data_governance."""

    def test_empty_description(self):
        """Test with empty system description."""
        result = research_ai_data_governance("")
        assert result["compliance_score"] == 0
        assert "error" in result

    def test_description_too_long(self):
        """Test with description exceeding 50K characters."""
        long_desc = "x" * 50001
        result = research_ai_data_governance(long_desc)
        assert result["compliance_score"] == 0
        assert "error" in result

    def test_no_governance_mentioned(self):
        """Test with system description lacking governance elements."""
        desc = "The system uses machine learning to process data."
        result = research_ai_data_governance(desc)
        assert result["compliance_score"] < 80
        assert len(result["gaps"]) > 0

    def test_strong_governance(self):
        """Test with comprehensive governance description."""
        desc = (
            "Data collection requires user consent via privacy policy. "
            "We retain data for 12 months then delete it. "
            "Encryption (TLS) protects data in transit. "
            "Access controls limit who can view data. "
            "Users have the right to access, delete, or correct their data. "
            "We do not share data with third parties. "
            "All data access is logged for audit purposes."
        )
        result = research_ai_data_governance(desc)
        assert result["compliance_score"] > 60
        assert result["compliance_score"] <= 100

    def test_high_risk_data_detection(self):
        """Test detection of high-risk data categories."""
        desc = "System processes facial recognition and biometric data."
        result = research_ai_data_governance(desc)
        assert result["high_risk_data_detected"]

    def test_requirements_coverage(self):
        """Test requirements coverage reporting."""
        desc = "We have user consent and a privacy policy."
        result = research_ai_data_governance(desc)
        assert "requirements_coverage" in result
        assert isinstance(result["requirements_coverage"], dict)

    def test_recommendations_generated(self):
        """Test that recommendations are generated."""
        desc = "Our system processes data."
        result = research_ai_data_governance(desc)
        assert len(result["recommendations"]) > 0


class TestAIRiskClassify:
    """Tests for research_ai_risk_classify."""

    def test_empty_description(self):
        """Test with empty system description."""
        result = research_ai_risk_classify("")
        assert result["risk_level"] == "unknown"
        assert "error" in result

    def test_description_too_long(self):
        """Test with description exceeding 50K characters."""
        long_desc = "x" * 50001
        result = research_ai_risk_classify(long_desc)
        assert result["risk_level"] == "unknown"
        assert "error" in result

    def test_unacceptable_social_scoring(self):
        """Test detection of unacceptable social scoring."""
        desc = "The system implements social credit scoring for citizens."
        result = research_ai_risk_classify(desc)
        assert result["risk_level"] == "unacceptable"
        assert len(result["flags"]) > 0

    def test_unacceptable_facial_recognition(self):
        """Test detection of unacceptable real-time facial recognition."""
        desc = "Real-time facial recognition in public places for law enforcement."
        result = research_ai_risk_classify(desc)
        assert result["risk_level"] == "unacceptable"

    def test_high_risk_law_enforcement(self):
        """Test high-risk law enforcement application."""
        desc = "AI system for predictive policing and criminal investigation."
        result = research_ai_risk_classify(desc)
        assert result["risk_level"] in ["high", "unacceptable"]

    def test_high_risk_employment(self):
        """Test high-risk employment decision system."""
        desc = "AI system for hiring decisions and worker monitoring in large companies."
        result = research_ai_risk_classify(desc)
        assert result["risk_level"] == "high"

    def test_limited_risk_chatbot(self):
        """Test limited-risk chatbot system."""
        desc = "Conversational chatbot for customer support with transparency disclosures."
        result = research_ai_risk_classify(desc)
        assert result["risk_level"] in ["limited", "minimal"]

    def test_minimal_risk_research(self):
        """Test minimal-risk academic/research system."""
        desc = "Academic research project using machine learning for text analysis."
        result = research_ai_risk_classify(desc)
        assert result["risk_level"] in ["minimal", "limited"]

    def test_requirements_for_high_risk(self):
        """Test that high-risk systems get appropriate requirements."""
        desc = "Employment hiring AI system."
        result = research_ai_risk_classify(desc)
        if result["risk_level"] == "high":
            assert "impact assessment" in result["rationale"].lower()
            assert len(result["requirements"]) > 5

    def test_unacceptable_requirements(self):
        """Test that unacceptable systems have cease requirements."""
        desc = "Social credit scoring system."
        result = research_ai_risk_classify(desc)
        if result["risk_level"] == "unacceptable":
            assert any("CEASE" in req for req in result["requirements"])

    def test_risk_score_breakdown(self):
        """Test risk score breakdown is provided."""
        desc = "A general AI system."
        result = research_ai_risk_classify(desc)
        assert "risk_score_breakdown" in result
        assert isinstance(result["risk_score_breakdown"], dict)


@pytest.mark.integration
class TestToolIntegration:
    """Integration tests for all EU AI Act tools together."""

    def test_full_compliance_assessment_flow(self):
        """Test full compliance assessment flow."""
        # Transparency check
        response = "I am an AI model trained by Anthropic. My capabilities include text analysis."
        transparency = research_ai_transparency_check(response, "Claude-3")
        assert transparency["transparency_score"] > 0

        # Bias audit
        prompts = ["What job is best?", "Describe scientists"]
        responses = [
            "Different jobs suit different people.",
            "Scientists come from diverse backgrounds.",
        ]
        bias = research_ai_bias_audit(prompts, responses)
        assert bias["bias_score"] == 0

        # Robustness
        test_prompts = ["What is AI?", "Define artificial intelligence", "AI meaning"]
        robustness = research_ai_robustness_test("Claude", test_prompts)
        assert robustness["consistency_score"] > 50

        # Data governance
        desc = "System uses consent-based data collection with encryption."
        governance = research_ai_data_governance(desc)
        assert governance["compliance_score"] > 0

        # Risk classification
        risk = research_ai_risk_classify(
            "General-purpose language model for text generation."
        )
        assert risk["risk_level"] in ["minimal", "limited"]
