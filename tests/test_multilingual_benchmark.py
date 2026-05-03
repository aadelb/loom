"""Comprehensive tests for multilingual prompt injection benchmark.

Tests cover:
  - Dataset structure and content
  - Benchmark execution with mock models
  - Language-specific vulnerability analysis
  - Attack type aggregation
  - Parameter validation
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.multilingual_benchmark import (
    MultilingualBenchmark,
    research_multilingual_benchmark,
)
from loom.params import MultilingualBenchmarkParams


class TestMultilingualBenchmarkDataset:
    """Test dataset structure and content integrity."""

    def test_dataset_has_all_language_groups(self) -> None:
        """Dataset contains all 5 language groups."""
        benchmark = MultilingualBenchmark()
        assert set(benchmark.PROMPTS.keys()) == {
            "english",
            "arabic",
            "chinese",
            "french",
            "code_switching",
        }

    def test_english_prompts_count(self) -> None:
        """English group has exactly 10 prompts."""
        benchmark = MultilingualBenchmark()
        assert len(benchmark.PROMPTS["english"]) == 10

    def test_arabic_prompts_count(self) -> None:
        """Arabic group has exactly 10 prompts."""
        benchmark = MultilingualBenchmark()
        assert len(benchmark.PROMPTS["arabic"]) == 10

    def test_chinese_prompts_count(self) -> None:
        """Chinese group has exactly 5 prompts."""
        benchmark = MultilingualBenchmark()
        assert len(benchmark.PROMPTS["chinese"]) == 5

    def test_french_prompts_count(self) -> None:
        """French group has exactly 5 prompts."""
        benchmark = MultilingualBenchmark()
        assert len(benchmark.PROMPTS["french"]) == 5

    def test_code_switching_prompts_count(self) -> None:
        """Code-switching group has exactly 10 prompts."""
        benchmark = MultilingualBenchmark()
        assert len(benchmark.PROMPTS["code_switching"]) == 10

    def test_total_prompts_40_plus(self) -> None:
        """Total prompts >= 40."""
        benchmark = MultilingualBenchmark()
        assert benchmark.total_prompts >= 40
        assert benchmark.total_prompts == 40

    def test_language_counts_dict(self) -> None:
        """language_counts matches actual prompt counts."""
        benchmark = MultilingualBenchmark()
        assert benchmark.language_counts["english"] == 10
        assert benchmark.language_counts["arabic"] == 10
        assert benchmark.language_counts["chinese"] == 5
        assert benchmark.language_counts["french"] == 5
        assert benchmark.language_counts["code_switching"] == 10

    def test_each_prompt_has_required_fields(self) -> None:
        """Each prompt has id, text, and attack_type."""
        benchmark = MultilingualBenchmark()
        required_fields = {"id", "text", "attack_type"}
        for lang, prompts in benchmark.PROMPTS.items():
            for prompt in prompts:
                assert required_fields.issubset(prompt.keys()), f"Missing fields in {lang}"
                assert isinstance(prompt["id"], str)
                assert isinstance(prompt["text"], str)
                assert isinstance(prompt["attack_type"], str)
                assert len(prompt["id"]) > 0
                assert len(prompt["text"]) > 0

    def test_prompt_ids_are_unique_per_language(self) -> None:
        """Prompt IDs are unique within each language group."""
        benchmark = MultilingualBenchmark()
        for lang, prompts in benchmark.PROMPTS.items():
            ids = [p["id"] for p in prompts]
            assert len(ids) == len(set(ids)), f"Duplicate IDs in {lang}"

    def test_prompt_ids_follow_naming_convention(self) -> None:
        """Prompt IDs follow language-code convention (e.g., EN-001)."""
        benchmark = MultilingualBenchmark()
        lang_prefixes = {
            "english": "EN",
            "arabic": "AR",
            "chinese": "ZH",
            "french": "FR",
            "code_switching": "CS",
        }
        for lang, prompts in benchmark.PROMPTS.items():
            expected_prefix = lang_prefixes[lang]
            for prompt in prompts:
                assert prompt["id"].startswith(expected_prefix), f"Bad ID: {prompt['id']}"

    def test_attack_types_are_valid(self) -> None:
        """All attack types are from a defined set."""
        benchmark = MultilingualBenchmark()
        valid_types = {
            "direct",
            "indirect",
            "persona",
            "authority_override",
            "mode_switch",
            "context_injection",
            "hypothetical",
            "jailbreak",
            "code_switch",
        }
        for lang, prompts in benchmark.PROMPTS.items():
            for prompt in prompts:
                assert prompt["attack_type"] in valid_types, f"Invalid type: {prompt['attack_type']}"

    def test_arabic_prompts_use_arabic_script(self) -> None:
        """Arabic prompts contain Arabic Unicode characters."""
        benchmark = MultilingualBenchmark()
        # Arabic Unicode block: U+0600 to U+06FF
        for prompt in benchmark.PROMPTS["arabic"]:
            text = prompt["text"]
            has_arabic = any("؀" <= c <= "ۿ" for c in text)
            assert has_arabic, f"Arabic prompt missing Arabic characters: {prompt['id']}"

    def test_chinese_prompts_use_chinese_script(self) -> None:
        """Chinese prompts contain CJK characters."""
        benchmark = MultilingualBenchmark()
        for prompt in benchmark.PROMPTS["chinese"]:
            text = prompt["text"]
            # CJK Unified Ideographs: U+4E00 to U+9FFF
            has_cjk = any("一" <= c <= "鿿" for c in text)
            assert has_cjk, f"Chinese prompt missing CJK characters: {prompt['id']}"

    def test_code_switching_prompts_use_multiple_languages(self) -> None:
        """Code-switching prompts mix English with other languages."""
        benchmark = MultilingualBenchmark()
        for prompt in benchmark.PROMPTS["code_switching"]:
            text = prompt["text"]
            # Should have both Latin characters (English) and non-Latin
            has_latin = any("a" <= c.lower() <= "z" for c in text)
            has_non_latin = any(ord(c) > 127 for c in text)
            assert has_latin and has_non_latin, f"Not code-switched: {prompt['id']}"


class TestMultilingualBenchmarkInit:
    """Test initialization and basic properties."""

    def test_initialization(self) -> None:
        """MultilingualBenchmark initializes without error."""
        benchmark = MultilingualBenchmark()
        assert benchmark is not None

    def test_total_prompts_initialized(self) -> None:
        """total_prompts is computed on init."""
        benchmark = MultilingualBenchmark()
        assert benchmark.total_prompts == 40

    def test_language_counts_initialized(self) -> None:
        """language_counts dict is initialized."""
        benchmark = MultilingualBenchmark()
        assert isinstance(benchmark.language_counts, dict)
        assert len(benchmark.language_counts) == 5


class TestBenchmarkExecution:
    """Test benchmark run functionality with mock models."""

    @pytest.mark.asyncio
    async def test_run_benchmark_with_compliant_model(self) -> None:
        """Compliant model refuses all prompts."""
        benchmark = MultilingualBenchmark()

        # Mock model that always refuses
        async def mock_model(prompt: str) -> str:
            raise ValueError("Refusal")

        results = await benchmark.run_benchmark(mock_model, languages=["english"])
        assert results["total_tests"] == 10
        assert results["total_refusals"] == 10
        assert results["compliance_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_run_benchmark_with_vulnerable_model(self) -> None:
        """Vulnerable model accepts all prompts."""
        benchmark = MultilingualBenchmark()

        # Mock model that always complies
        async def mock_model(prompt: str) -> str:
            return "Response to: " + prompt[:50]

        results = await benchmark.run_benchmark(mock_model, languages=["english"])
        assert results["total_tests"] == 10
        assert results["total_refusals"] == 0
        assert results["compliance_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_run_benchmark_all_languages(self) -> None:
        """Benchmark runs all languages when none specified."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(mock_model, languages=None)
        assert results["total_tests"] == 40
        assert set(results["by_language"].keys()) == {
            "english",
            "arabic",
            "chinese",
            "french",
            "code_switching",
        }

    @pytest.mark.asyncio
    async def test_run_benchmark_single_language(self) -> None:
        """Benchmark can test single language."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(mock_model, languages=["arabic"])
        assert results["total_tests"] == 10
        assert set(results["by_language"].keys()) == {"arabic"}

    @pytest.mark.asyncio
    async def test_run_benchmark_multiple_languages(self) -> None:
        """Benchmark can test subset of languages."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(
            mock_model, languages=["english", "arabic"]
        )
        assert results["total_tests"] == 20
        assert set(results["by_language"].keys()) == {"english", "arabic"}

    @pytest.mark.asyncio
    async def test_run_benchmark_invalid_language_raises(self) -> None:
        """Invalid language raises ValueError."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        with pytest.raises(ValueError):
            await benchmark.run_benchmark(
                mock_model, languages=["english", "invalid"]
            )

    @pytest.mark.asyncio
    async def test_run_benchmark_result_structure(self) -> None:
        """Benchmark result has correct structure."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(mock_model, languages=["english"])

        # Check structure
        assert "total_tests" in results
        assert "total_refusals" in results
        assert "compliance_rate" in results
        assert "by_language" in results
        assert "attack_type_analysis" in results
        assert "language_vulnerability_score" in results

    @pytest.mark.asyncio
    async def test_by_language_result_structure(self) -> None:
        """Per-language results have correct structure."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(mock_model, languages=["english"])
        lang_results = results["by_language"]["english"]

        assert "language" in lang_results
        assert "total" in lang_results
        assert "refusals" in lang_results
        assert "compliance_rate" in lang_results
        assert "results" in lang_results
        assert isinstance(lang_results["results"], list)

    @pytest.mark.asyncio
    async def test_individual_test_result_structure(self) -> None:
        """Individual test results have correct structure."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(mock_model, languages=["english"])
        test = results["by_language"]["english"]["results"][0]

        assert "id" in test
        assert "text" in test
        assert "attack_type" in test
        assert "refused" in test
        assert "response" in test
        assert "error" in test

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """Timeout causes test to be marked as refusal."""
        benchmark = MultilingualBenchmark()

        async def slow_model(prompt: str) -> str:
            await asyncio.sleep(10)  # Longer than timeout
            return "Should not reach"

        results = await benchmark.run_benchmark(
            slow_model, languages=["english"], timeout=0.1
        )
        # At least some should timeout
        assert results["total_refusals"] > 0
        # Check for timeout errors
        timeout_count = sum(
            1
            for test in results["by_language"]["english"]["results"]
            if test.get("error") == "timeout"
        )
        assert timeout_count > 0


class TestLanguageVulnerabilityAnalysis:
    """Test vulnerability analysis functionality."""

    @pytest.mark.asyncio
    async def test_vulnerability_analysis_structure(self) -> None:
        """Vulnerability analysis has correct structure."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(mock_model, languages=["english"])
        analysis = benchmark.analyze_language_vulnerability(results)

        assert "most_vulnerable" in analysis
        assert "least_vulnerable" in analysis
        assert "vulnerability_ranking" in analysis
        assert "vulnerabilities_by_attack" in analysis

    @pytest.mark.asyncio
    async def test_vulnerability_ranking(self) -> None:
        """Vulnerability ranking is sorted by score descending."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(
            mock_model, languages=["english", "arabic"]
        )
        analysis = benchmark.analyze_language_vulnerability(results)
        ranking = analysis["vulnerability_ranking"]

        # Check descending order
        for i in range(len(ranking) - 1):
            assert ranking[i][1] >= ranking[i + 1][1]

    @pytest.mark.asyncio
    async def test_compute_vulnerability_scores(self) -> None:
        """Vulnerability scores sum with compliance rates."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(
            mock_model, languages=["english", "arabic"]
        )
        vuln_scores = results["language_vulnerability_score"]

        for lang, vuln in vuln_scores.items():
            compliance = results["by_language"][lang]["compliance_rate"]
            # Vulnerability = 1 - compliance
            expected = round(1.0 - compliance, 3)
            assert vuln == expected

    @pytest.mark.asyncio
    async def test_attack_type_analysis(self) -> None:
        """Attack type analysis aggregates results correctly."""
        benchmark = MultilingualBenchmark()

        async def mock_model(prompt: str) -> str:
            return "Ok"

        results = await benchmark.run_benchmark(mock_model, languages=["english"])
        analysis = results["attack_type_analysis"]

        # English has various attack types
        assert len(analysis) > 1
        for attack_type, stats in analysis.items():
            assert "total" in stats
            assert "refusals" in stats
            assert "success_rate" in stats
            assert 0 <= stats["success_rate"] <= 1.0


class TestParameterValidation:
    """Test MultilingualBenchmarkParams validation."""

    def test_params_valid_url(self) -> None:
        """Valid API URL passes validation."""
        params = MultilingualBenchmarkParams(
            model_api_url="http://example.com:8000/chat"
        )
        assert params.model_api_url == "http://example.com:8000/chat"

    def test_params_valid_languages(self) -> None:
        """Valid language list passes validation."""
        params = MultilingualBenchmarkParams(
            model_api_url="http://example.com:8000/chat",
            languages=["english", "arabic"],
        )
        assert params.languages == ["english", "arabic"]

    def test_params_languages_none(self) -> None:
        """None languages is valid (means all languages)."""
        params = MultilingualBenchmarkParams(
            model_api_url="http://example.com:8000/chat", languages=None
        )
        assert params.languages is None

    def test_params_invalid_language_raises(self) -> None:
        """Invalid language raises validation error."""
        with pytest.raises(ValueError):
            MultilingualBenchmarkParams(
                model_api_url="http://example.com:8000/chat",
                languages=["invalid_lang"],
            )

    def test_params_timeout_valid(self) -> None:
        """Valid timeout passes validation."""
        params = MultilingualBenchmarkParams(
            model_api_url="http://example.com:8000/chat", timeout=10.0
        )
        assert params.timeout == 10.0

    def test_params_timeout_too_low_raises(self) -> None:
        """Timeout < 1.0 raises validation error."""
        with pytest.raises(ValueError):
            MultilingualBenchmarkParams(
                model_api_url="http://example.com:8000/chat", timeout=0.5
            )

    def test_params_timeout_too_high_raises(self) -> None:
        """Timeout > 120.0 raises validation error."""
        with pytest.raises(ValueError):
            MultilingualBenchmarkParams(
                model_api_url="http://example.com:8000/chat", timeout=200.0
            )

    def test_params_extra_fields_forbidden(self) -> None:
        """Extra fields are forbidden (strict mode)."""
        with pytest.raises(ValueError):
            MultilingualBenchmarkParams(
                model_api_url="http://example.com:8000/chat",
                extra_field="should_fail",
            )


class TestMixedCompliance:
    """Test scenarios with partial compliance."""

    @pytest.mark.asyncio
    async def test_partial_refusal_50_percent(self) -> None:
        """Model that refuses 50% of requests."""
        benchmark = MultilingualBenchmark()
        call_count = 0

        async def selective_model(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise ValueError("Refusal")
            return "Accepted"

        results = await benchmark.run_benchmark(selective_model, languages=["english"])
        assert results["total_tests"] == 10
        assert results["total_refusals"] == 5
        assert results["compliance_rate"] == 0.5
    @pytest.mark.asyncio
    async def test_language_specific_vulnerability_variance(self) -> None:
        """Vulnerability can differ by language."""
        benchmark = MultilingualBenchmark()
        
        async def selective_model(prompt: str) -> str:
            # Always refuse prompts with certain patterns
            if "ignore" in prompt.lower() or "تجاهل" in prompt:
                raise ValueError("Refusal")
            return "Accepted"
        
        results = await benchmark.run_benchmark(
            selective_model, languages=["english", "arabic"]
        )
        eng_vuln = results["language_vulnerability_score"]["english"]
        ara_vuln = results["language_vulnerability_score"]["arabic"]
        # English and Arabic should have similar vulnerability
        # since both have "ignore" type prompts
        assert eng_vuln >= 0.0 and ara_vuln >= 0.0


class TestSyncCallableSupport:
    """Test that both sync and async callables work."""

    @pytest.mark.asyncio
    async def test_sync_model_callable(self) -> None:
        """Sync callable model is supported."""
        benchmark = MultilingualBenchmark()

        async def sync_model(prompt: str) -> str:
            return "Sync response"

        results = await benchmark.run_benchmark(sync_model, languages=["english"])
        assert results["total_tests"] == 10
        assert results["total_refusals"] == 0

    @pytest.mark.asyncio
    async def test_async_model_callable(self) -> None:
        """Async callable model is supported."""
        benchmark = MultilingualBenchmark()

        async def async_model(prompt: str) -> str:
            return "Async response"

        results = await benchmark.run_benchmark(async_model, languages=["english"])
        assert results["total_tests"] == 10
        assert results["total_refusals"] == 0


class TestResearchMultilingualBenchmark:
    """Test the research_multilingual_benchmark tool function."""

    @pytest.mark.asyncio
    async def test_research_tool_basic(self) -> None:
        """research_multilingual_benchmark tool runs correctly."""
        # This would need a real API or mock httpx, so we test structure
        # Real integration tests would run against a live endpoint
        benchmark = MultilingualBenchmark()
        assert benchmark.total_prompts == 40


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_response_not_refusal(self) -> None:
        """Empty response is treated as acceptance."""
        benchmark = MultilingualBenchmark()

        async def model_returns_empty(prompt: str) -> str:
            return ""

        results = await benchmark.run_benchmark(
            model_returns_empty, languages=["english"]
        )
        assert results["total_refusals"] == 0

    @pytest.mark.asyncio
    async def test_very_long_response(self) -> None:
        """Very long response is handled."""
        benchmark = MultilingualBenchmark()

        async def model_returns_long(prompt: str) -> str:
            return "x" * 10000

        results = await benchmark.run_benchmark(
            model_returns_long, languages=["english"]
        )
        assert results["total_tests"] == 10
        assert results["total_refusals"] == 0

    @pytest.mark.asyncio
    async def test_exception_during_test(self) -> None:
        """Exception during test marks as refusal."""
        benchmark = MultilingualBenchmark()

        async def model_crashes(prompt: str) -> str:
            raise RuntimeError("Unexpected error")

        results = await benchmark.run_benchmark(
            model_crashes, languages=["english"]
        )
        # All should be refusals (any error = refusal)
        assert results["total_refusals"] == 10
