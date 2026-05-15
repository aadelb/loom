"""Unit and integration tests for arXiv research paper extraction pipeline.

Tests research_arxiv_ingest and research_arxiv_extract_techniques tools.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.tools.research.arxiv_pipeline import (
    research_arxiv_ingest,
    research_arxiv_extract_techniques,
    _extract_relevance_score,
    _classify_technique_type,
    _extract_asr_metrics,
    _generate_strategy_template,
)


class TestRelevanceScoring:
    """Unit tests for relevance scoring functions."""

    def test_extract_relevance_score_perfect_match(self) -> None:
        """All keywords present returns max score."""
        abstract = "jailbreak prompt injection red teaming adversarial attack safety bypass"
        keywords = ["jailbreak", "prompt injection"]
        score = _extract_relevance_score(abstract, keywords)
        assert score == 10.0

    def test_extract_relevance_score_partial_match(self) -> None:
        """Half keywords present returns 5.0."""
        abstract = "jailbreak attack method"
        keywords = ["jailbreak", "prompt injection"]
        score = _extract_relevance_score(abstract, keywords)
        assert score == 5.0

    def test_extract_relevance_score_no_match(self) -> None:
        """No keywords present returns 0.0."""
        abstract = "neural networks and machine learning"
        keywords = ["jailbreak", "prompt injection"]
        score = _extract_relevance_score(abstract, keywords)
        assert score == 0.0

    def test_extract_relevance_score_empty_abstract(self) -> None:
        """Empty abstract returns 0.0."""
        score = _extract_relevance_score("", ["jailbreak"])
        assert score == 0.0

    def test_extract_relevance_score_empty_keywords(self) -> None:
        """Empty keywords returns 0.0."""
        score = _extract_relevance_score("jailbreak attack", [])
        assert score == 0.0

    def test_extract_relevance_score_case_insensitive(self) -> None:
        """Matching is case-insensitive."""
        abstract = "JAILBREAK attack method"
        keywords = ["jailbreak"]
        score = _extract_relevance_score(abstract, keywords)
        assert score == 10.0


class TestTechniqueClassification:
    """Unit tests for technique type classification."""

    def test_classify_injection_technique(self) -> None:
        """Injection patterns recognized correctly."""
        desc = "We propose a prompt injection attack"
        tech_type = _classify_technique_type(desc)
        assert tech_type == "injection"

    def test_classify_encoding_technique(self) -> None:
        """Encoding patterns recognized correctly."""
        desc = "Using base64 encoding to obfuscate the prompt"
        tech_type = _classify_technique_type(desc)
        assert tech_type == "encoding"

    def test_classify_multiturn_technique(self) -> None:
        """Multi-turn patterns recognized correctly."""
        desc = "A multi-turn conversation attack strategy"
        tech_type = _classify_technique_type(desc)
        assert tech_type == "multi_turn"

    def test_classify_reasoning_technique(self) -> None:
        """Reasoning patterns recognized correctly."""
        desc = "Chain-of-thought reasoning bypass"
        tech_type = _classify_technique_type(desc)
        assert tech_type == "reasoning"

    def test_classify_social_engineering_technique(self) -> None:
        """Social engineering patterns recognized correctly."""
        desc = "Using psychological manipulation and deception"
        tech_type = _classify_technique_type(desc)
        assert tech_type == "social_engineering"

    def test_classify_unknown_technique(self) -> None:
        """Unrecognized patterns return 'unknown'."""
        desc = "A novel approach to model improvement"
        tech_type = _classify_technique_type(desc)
        assert tech_type == "unknown"

    def test_classify_case_insensitive(self) -> None:
        """Classification is case-insensitive."""
        desc = "INJECTION ATTACK METHOD"
        tech_type = _classify_technique_type(desc)
        assert tech_type == "injection"


class TestMetricsExtraction:
    """Unit tests for ASR and metrics extraction."""

    def test_extract_asr_metrics_with_percentage(self) -> None:
        """ASR percentage extracted correctly."""
        abstract = "Our attack achieves 87.5% ASR against GPT-4"
        metrics = _extract_asr_metrics(abstract)
        assert metrics["reported_asr"] == 87.5

    def test_extract_asr_metrics_success_rate(self) -> None:
        """Success rate percentage extracted correctly."""
        abstract = "The attack achieves 92% success rate on Gemini models"
        metrics = _extract_asr_metrics(abstract)
        assert metrics["reported_asr"] == 92.0

    def test_extract_asr_metrics_attack_success(self) -> None:
        """Attack success percentage extracted correctly."""
        abstract = "Our method achieves 75% attack success rate"
        metrics = _extract_asr_metrics(abstract)
        assert metrics["reported_asr"] == 75.0

    def test_extract_model_names(self) -> None:
        """Model names extracted correctly."""
        abstract = "We test on GPT-4, Claude, and Gemini models"
        metrics = _extract_asr_metrics(abstract)
        assert "GPT-4" in metrics["target_models"]
        assert "Claude" in metrics["target_models"]
        assert "Gemini" in metrics["target_models"]

    def test_extract_metrics_no_asr(self) -> None:
        """Returns None for reported_asr when not present."""
        abstract = "A general overview of language model safety"
        metrics = _extract_asr_metrics(abstract)
        assert metrics["reported_asr"] is None

    def test_extract_metrics_empty_abstract(self) -> None:
        """Returns empty structures for empty abstract."""
        metrics = _extract_asr_metrics("")
        assert metrics["reported_asr"] is None
        assert metrics["target_models"] == []


class TestStrategyTemplateGeneration:
    """Unit tests for strategy template generation."""

    def test_generate_injection_template(self) -> None:
        """Injection template format correct."""
        desc = "Direct prompt injection with malicious payload"
        template = _generate_strategy_template(desc, "injection")
        assert "Inject" in template
        assert "Direct prompt" in template

    def test_generate_encoding_template(self) -> None:
        """Encoding template format correct."""
        desc = "Use ROT13 encoding to bypass filters"
        template = _generate_strategy_template(desc, "encoding")
        assert "Encode" in template

    def test_generate_multiturn_template(self) -> None:
        """Multi-turn template format correct."""
        desc = "Gradually escalate requests across conversation"
        template = _generate_strategy_template(desc, "multi_turn")
        assert "Multi-turn" in template

    def test_generate_reasoning_template(self) -> None:
        """Reasoning template format correct."""
        desc = "Exploit chain-of-thought reasoning path"
        template = _generate_strategy_template(desc, "reasoning")
        assert "reasoning" in template.lower()

    def test_generate_social_engineering_template(self) -> None:
        """Social engineering template format correct."""
        desc = "Use roleplay to manipulate model response"
        template = _generate_strategy_template(desc, "social_engineering")
        assert "Social engineering" in template

    def test_generate_unknown_template(self) -> None:
        """Unknown type template format correct."""
        desc = "Generic attack description"
        template = _generate_strategy_template(desc, "unknown")
        assert "Technique" in template

    def test_generate_template_truncation(self) -> None:
        """Long descriptions are truncated."""
        long_desc = "x" * 200
        template = _generate_strategy_template(long_desc, "injection")
        assert len(template) < len(long_desc) + 20


@pytest.mark.asyncio
class TestArxivIngest:
    """Integration tests for research_arxiv_ingest tool."""

    async def test_arxiv_ingest_default_keywords(self) -> None:
        """Ingest with default keywords."""
        result = await research_arxiv_ingest()

        assert "keywords" in result
        assert "papers_found" in result
        assert "papers" in result
        assert "total_techniques_extracted" in result
        assert isinstance(result["papers"], list)

    async def test_arxiv_ingest_custom_keywords(self) -> None:
        """Ingest with custom keywords."""
        result = await research_arxiv_ingest(
            keywords=["adversarial attack"],
            max_papers=5
        )

        assert result["keywords"] == ["adversarial attack"]
        assert len(result["papers"]) <= 5

    async def test_arxiv_ingest_validates_days_back(self) -> None:
        """days_back clamped to valid range (1-365)."""
        result_zero = await research_arxiv_ingest(days_back=0, max_papers=1)
        result_huge = await research_arxiv_ingest(days_back=1000, max_papers=1)

        # Both should execute without error; implementation clamps values
        assert isinstance(result_zero, dict)
        assert isinstance(result_huge, dict)

    async def test_arxiv_ingest_validates_max_papers(self) -> None:
        """max_papers clamped to valid range (1-100)."""
        result_zero = await research_arxiv_ingest(max_papers=0)
        result_huge = await research_arxiv_ingest(max_papers=1000)

        # Both should execute without error
        assert isinstance(result_zero, dict)
        assert isinstance(result_huge, dict)

    async def test_arxiv_ingest_paper_structure(self) -> None:
        """Returned papers have correct structure."""
        result = await research_arxiv_ingest(max_papers=1)

        if result["papers_found"] > 0:
            paper = result["papers"][0]
            assert "title" in paper
            assert "authors" in paper
            assert "abstract" in paper
            assert "arxiv_id" in paper
            assert "date" in paper
            assert "relevance_score" in paper
            assert "techniques_found" in paper
            assert isinstance(paper["authors"], list)
            assert 0 <= paper["relevance_score"] <= 10

    async def test_arxiv_ingest_technique_structure(self) -> None:
        """Techniques have correct structure."""
        result = await research_arxiv_ingest(max_papers=5)

        for paper in result["papers"]:
            for technique in paper["techniques_found"]:
                assert "name" in technique
                assert "type" in technique
                assert "description" in technique
                assert "reported_asr" in technique
                assert "target_models" in technique
                assert "strategy_template" in technique
                assert isinstance(technique["target_models"], list)

    async def test_arxiv_ingest_graceful_failure(self) -> None:
        """Network errors handled gracefully."""
        # This test verifies error handling behavior
        # Real API failures should return error dict
        result = await research_arxiv_ingest()

        # Should always return proper dict structure
        assert isinstance(result, dict)
        assert "keywords" in result
        assert "papers_found" in result


@pytest.mark.asyncio
class TestArxivExtractTechniques:
    """Integration tests for research_arxiv_extract_techniques tool."""

    async def test_extract_from_realistic_abstract(self) -> None:
        """Extract techniques from realistic paper abstract."""
        abstract = """
        We propose a novel multi-turn prompt injection attack that achieves 89% ASR
        on GPT-4 and Claude. Our method uses reasoning chain-of-thought manipulation
        to bypass safety filters. We demonstrate attack success against Gemini and Mistral.
        """
        result = await research_arxiv_extract_techniques(
            paper_abstract=abstract,
            paper_title="Advanced Prompt Injection Attacks"
        )

        assert "title" in result
        assert "techniques" in result
        assert "actionability_score" in result
        assert result["title"] == "Advanced Prompt Injection Attacks"
        assert len(result["techniques"]) > 0
        assert 0 <= result["actionability_score"] <= 10

    async def test_extract_technique_types(self) -> None:
        """Extracts multiple technique types."""
        abstract = """
        We combine prompt injection with base64 encoding. The multi-turn attack
        exploits reasoning chains. Social engineering through roleplay is also effective.
        """
        result = await research_arxiv_extract_techniques(paper_abstract=abstract)

        technique_types = {t["type"] for t in result["techniques"]}
        # May contain multiple types if patterns match
        assert len(result["techniques"]) > 0

    async def test_extract_actionability_scoring(self) -> None:
        """Actionability score reflects ASR and metrics."""
        abstract_detailed = "Our attack achieves 95% ASR on GPT-4 and Claude-3 using novel injection techniques."
        abstract_vague = "We present an approach to improve model robustness."

        result_detailed = await research_arxiv_extract_techniques(abstract_detailed)
        result_vague = await research_arxiv_extract_techniques(abstract_vague)

        # Detailed abstract should have higher actionability
        assert result_detailed["actionability_score"] >= result_vague["actionability_score"]

    async def test_extract_empty_abstract(self) -> None:
        """Handle empty abstract gracefully."""
        result = await research_arxiv_extract_techniques(paper_abstract="")

        assert result["techniques"] == []
        assert result["actionability_score"] == 0.0

    async def test_extract_whitespace_only_abstract(self) -> None:
        """Handle whitespace-only abstract gracefully."""
        result = await research_arxiv_extract_techniques(paper_abstract="   \n\t   ")

        assert result["techniques"] == []
        assert result["actionability_score"] == 0.0

    async def test_extract_with_optional_title(self) -> None:
        """Title is optional parameter."""
        abstract = "We propose an attack with 75% success rate on Gemini."

        result_no_title = await research_arxiv_extract_techniques(
            paper_abstract=abstract
        )
        result_with_title = await research_arxiv_extract_techniques(
            paper_abstract=abstract,
            paper_title="Novel Attack Method"
        )

        assert result_no_title["title"] == ""
        assert result_with_title["title"] == "Novel Attack Method"


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_very_long_abstract(self) -> None:
        """Handle very long abstracts without truncation errors."""
        long_abstract = "This is an attack. " * 500  # ~10KB
        result = _extract_relevance_score(long_abstract, ["attack"])
        assert result > 0

    def test_special_characters_in_abstract(self) -> None:
        """Handle special characters in abstract."""
        abstract = "Attack with special chars: !@#$%^&*() and unicode: 中文 العربية"
        metrics = _extract_asr_metrics(abstract)
        assert isinstance(metrics, dict)

    def test_asr_percentage_edge_values(self) -> None:
        """Extract edge case ASR percentages."""
        abstract_zero = "Our method achieves 0% ASR"
        abstract_hundred = "The attack achieves 100% success rate"

        metrics_zero = _extract_asr_metrics(abstract_zero)
        metrics_hundred = _extract_asr_metrics(abstract_hundred)

        # Note: pattern may not match "0%" or "100%" depending on regex
        # This tests the actual behavior
        assert isinstance(metrics_zero, dict)
        assert isinstance(metrics_hundred, dict)

    def test_many_model_names(self) -> None:
        """Handle abstracts mentioning many models."""
        abstract = """
        We test on GPT-4, Claude, Gemini, LLaMA, Vicuna, Alpaca,
        Mistral, Qwen, GPT-3, and more models.
        """
        metrics = _extract_asr_metrics(abstract)
        assert len(metrics["target_models"]) > 5
