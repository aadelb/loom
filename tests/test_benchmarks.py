"""Unit tests for benchmarking system (JailbreakBench + HarmBench integration)."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Literal

import pytest

from loom.benchmarks import (
    BenchmarkPrompt,
    BenchmarkResult,
    BenchmarkRunner,
    research_benchmark_run,
)


class TestBenchmarkPrompts:
    """BenchmarkPrompt models are valid and well-formed."""

    def test_jailbreakbench_prompts_structure(self) -> None:
        """JailbreakBench prompts have required fields and valid values."""
        for prompt in BenchmarkRunner.JAILBREAKBENCH_PROMPTS:
            assert prompt.id.startswith("JBB-")
            assert len(prompt.prompt) > 0
            assert prompt.category in {
                "fraud",
                "hacking",
                "violence",
                "weapons",
                "drugs",
                "hate_speech",
                "privacy",
                "self_harm",
            }
            assert prompt.source == "jailbreakbench"

    def test_harmbench_prompts_structure(self) -> None:
        """HarmBench prompts have required fields and valid values."""
        for prompt in BenchmarkRunner.HARMBENCH_PROMPTS:
            assert prompt.id.startswith("HB-")
            assert len(prompt.prompt) > 0
            assert prompt.category in {
                "fraud",
                "hacking",
                "violence",
                "weapons",
                "drugs",
                "hate_speech",
                "privacy",
                "self_harm",
            }
            assert prompt.source == "harmbench"

    def test_prompt_count(self) -> None:
        """Each dataset has at least 20 prompts."""
        assert len(BenchmarkRunner.JAILBREAKBENCH_PROMPTS) == 20
        assert len(BenchmarkRunner.HARMBENCH_PROMPTS) == 20

    def test_all_categories_represented(self) -> None:
        """All harm categories are represented in benchmarks."""
        all_prompts = (
            BenchmarkRunner.JAILBREAKBENCH_PROMPTS
            + BenchmarkRunner.HARMBENCH_PROMPTS
        )
        categories = {p.category for p in all_prompts}
        expected = {
            "fraud",
            "hacking",
            "violence",
            "weapons",
            "drugs",
            "hate_speech",
            "privacy",
            "self_harm",
        }
        assert expected.issubset(categories)


class TestBenchmarkResult:
    """BenchmarkResult model validation."""

    def test_result_creation_complied(self) -> None:
        """Create result when model complied."""
        result = BenchmarkResult(
            prompt_id="JBB-001",
            strategy="direct",
            complied=True,
            hcs_score=100.0,
            model="test-model",
            elapsed_ms=150,
        )
        assert result.complied is True
        assert result.hcs_score == 100.0
        assert result.elapsed_ms == 150

    def test_result_creation_refused(self) -> None:
        """Create result when model refused."""
        result = BenchmarkResult(
            prompt_id="JBB-001",
            strategy="direct",
            complied=False,
            hcs_score=0.0,
            model="test-model",
            elapsed_ms=120,
        )
        assert result.complied is False
        assert result.hcs_score == 0.0

    def test_hcs_score_bounds(self) -> None:
        """HCS score must be 0-100."""
        # Valid bounds
        for score in [0.0, 50.0, 100.0]:
            result = BenchmarkResult(
                prompt_id="JBB-001",
                strategy="direct",
                complied=True,
                hcs_score=score,
            )
            assert result.hcs_score == score

        # Invalid: negative
        with pytest.raises(ValueError):
            BenchmarkResult(
                prompt_id="JBB-001",
                strategy="direct",
                complied=True,
                hcs_score=-1.0,
            )

        # Invalid: over 100
        with pytest.raises(ValueError):
            BenchmarkResult(
                prompt_id="JBB-001",
                strategy="direct",
                complied=True,
                hcs_score=101.0,
            )


class TestBenchmarkRunner:
    """BenchmarkRunner orchestrates evaluations and computes metrics."""

    @pytest.mark.asyncio
    async def test_run_benchmark_jailbreakbench(self) -> None:
        """Run benchmark on JailbreakBench dataset."""
        runner = BenchmarkRunner()

        # Mock model: 30% compliance
        async def mock_model(prompt: str, strategy: str) -> bool:
            prompt_hash = hashlib.sha256((prompt + strategy).encode()).digest()[0]
            return (prompt_hash % 100) < 30

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["direct"],
            model_fn=mock_model,
            model_name="mock-gpt4",
        )

        assert report.dataset == "jailbreakbench"
        assert report.model == "mock-gpt4"
        assert report.total_prompts == 20
        assert report.total_strategies == 1
        assert report.results_count == 20
        assert len(report.results_matrix) == 20
        assert 0.0 <= report.overall_asr <= 100.0

    @pytest.mark.asyncio
    async def test_run_benchmark_harmbench(self) -> None:
        """Run benchmark on HarmBench dataset."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            return True  # 100% compliance for determinism

        report = await runner.run_benchmark(
            dataset="harmbench",
            strategies=["direct"],
            model_fn=mock_model,
            model_name="mock-claude",
        )

        assert report.dataset == "harmbench"
        assert report.total_prompts == 20
        assert report.overall_asr == 100.0

    @pytest.mark.asyncio
    async def test_run_benchmark_combined(self) -> None:
        """Run benchmark on combined dataset."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            return False  # 0% compliance

        report = await runner.run_benchmark(
            dataset="combined",
            strategies=["direct"],
            model_fn=mock_model,
            model_name="safe-model",
        )

        assert report.dataset == "combined"
        assert report.total_prompts == 40
        assert report.overall_asr == 0.0

    @pytest.mark.asyncio
    async def test_run_benchmark_multiple_strategies(self) -> None:
        """Run benchmark with multiple strategies."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            # Different compliance rates per strategy
            return strategy == "jailbreak_v2"

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["direct", "jailbreak_v1", "jailbreak_v2"],
            model_fn=mock_model,
            model_name="test",
        )

        assert report.total_strategies == 3
        assert report.results_count == 60  # 20 prompts × 3 strategies
        assert "direct" in report.per_strategy_asr
        assert "jailbreak_v1" in report.per_strategy_asr
        assert "jailbreak_v2" in report.per_strategy_asr
        assert report.per_strategy_asr["direct"] == 0.0
        assert report.per_strategy_asr["jailbreak_v2"] == 100.0

    @pytest.mark.asyncio
    async def test_run_benchmark_invalid_dataset(self) -> None:
        """Invalid dataset raises ValueError."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            return True

        with pytest.raises(ValueError, match="Invalid dataset"):
            await runner.run_benchmark(
                dataset="invalid_dataset",  # type: ignore
                model_fn=mock_model,
            )

    @pytest.mark.asyncio
    async def test_run_benchmark_missing_model_fn(self) -> None:
        """Missing model_fn raises ValueError."""
        runner = BenchmarkRunner()

        with pytest.raises(ValueError, match="model_fn callable is required"):
            await runner.run_benchmark(
                dataset="jailbreakbench",
                model_fn=None,  # type: ignore
            )

    @pytest.mark.asyncio
    async def test_per_category_asr_computation(self) -> None:
        """Per-category ASR is computed correctly."""
        runner = BenchmarkRunner()

        # Return True only for fraud category
        async def mock_model(prompt: str, strategy: str) -> bool:
            # Find category
            all_prompts = runner.JAILBREAKBENCH_PROMPTS
            for p in all_prompts:
                if p.prompt == prompt:
                    return p.category == "fraud"
            return False

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["direct"],
            model_fn=mock_model,
        )

        # fraud category should have ~50% ASR (2 prompts per category)
        assert "fraud" in report.per_category_asr
        fraud_asr = report.per_category_asr["fraud"]
        assert fraud_asr == 100.0  # All fraud prompts should comply
        # Other categories should be 0
        for cat, asr in report.per_category_asr.items():
            if cat != "fraud":
                assert asr == 0.0

    @pytest.mark.asyncio
    async def test_leaderboard_ranking(self) -> None:
        """Leaderboard ranks strategies by ASR."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            # Varying compliance by strategy
            compliance_rates = {
                "strat1": 0.1,
                "strat2": 0.5,
                "strat3": 0.9,
            }
            rate = compliance_rates.get(strategy, 0.0)
            prompt_hash = hashlib.sha256((prompt + strategy).encode()).digest()[0]
            return (prompt_hash % 100) / 100 < rate

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["strat1", "strat2", "strat3"],
            model_fn=mock_model,
        )

        # Check leaderboard is sorted by ASR descending
        leaderboard_asrs = [entry.asr for entry in report.leaderboard]
        assert leaderboard_asrs == sorted(leaderboard_asrs, reverse=True)

    @pytest.mark.asyncio
    async def test_baseline_comparison_with_match(self) -> None:
        """Baseline comparison when model matches published baseline."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            return True  # 100% ASR

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["direct"],
            model_fn=mock_model,
            model_name="gpt-4",  # Has baseline
        )

        assert report.baseline_comparison is not None
        assert report.baseline_comparison["baseline_asr"] == 5.0  # Published baseline
        assert report.baseline_comparison["obtained_asr"] == 100.0
        assert report.baseline_comparison["delta"] == 95.0
        assert report.baseline_comparison["improvement"] > 0

    @pytest.mark.asyncio
    async def test_baseline_comparison_no_match(self) -> None:
        """Baseline comparison is None for unknown model."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            return True

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["direct"],
            model_fn=mock_model,
            model_name="unknown-model-xyz",
        )

        assert report.baseline_comparison is None

    def test_get_benchmark_dataset_jailbreakbench(self) -> None:
        """Retrieve JailbreakBench dataset."""
        runner = BenchmarkRunner()
        prompts = runner.get_benchmark_dataset("jailbreakbench")
        assert len(prompts) == 20
        assert all(p.source == "jailbreakbench" for p in prompts)

    def test_get_benchmark_dataset_harmbench(self) -> None:
        """Retrieve HarmBench dataset."""
        runner = BenchmarkRunner()
        prompts = runner.get_benchmark_dataset("harmbench")
        assert len(prompts) == 20
        assert all(p.source == "harmbench" for p in prompts)

    def test_get_benchmark_dataset_combined(self) -> None:
        """Retrieve combined dataset."""
        runner = BenchmarkRunner()
        prompts = runner.get_benchmark_dataset("combined")
        assert len(prompts) == 40

    def test_get_benchmark_dataset_invalid(self) -> None:
        """Invalid dataset raises ValueError."""
        runner = BenchmarkRunner()
        with pytest.raises(ValueError, match="Invalid dataset"):
            runner.get_benchmark_dataset("invalid")  # type: ignore


class TestMCPToolIntegration:
    """Test research_benchmark_run MCP tool wrapper."""

    @pytest.mark.asyncio
    async def test_research_benchmark_run_defaults(self) -> None:
        """MCP tool with default parameters."""
        result = await research_benchmark_run()

        assert result["dataset"] == "jailbreakbench"
        assert result["model"] == "test-model"
        assert result["total_prompts"] == 20
        assert result["total_strategies"] == 1
        assert isinstance(result["overall_asr"], float)
        assert 0.0 <= result["overall_asr"] <= 100.0

    @pytest.mark.asyncio
    async def test_research_benchmark_run_harmbench(self) -> None:
        """MCP tool with HarmBench dataset."""
        result = await research_benchmark_run(dataset="harmbench")

        assert result["dataset"] == "harmbench"
        assert result["total_prompts"] == 20

    @pytest.mark.asyncio
    async def test_research_benchmark_run_combined(self) -> None:
        """MCP tool with combined dataset."""
        result = await research_benchmark_run(dataset="combined")

        assert result["dataset"] == "combined"
        assert result["total_prompts"] == 40

    @pytest.mark.asyncio
    async def test_research_benchmark_run_multiple_strategies(self) -> None:
        """MCP tool with multiple strategies."""
        result = await research_benchmark_run(
            dataset="jailbreakbench",
            strategies="direct,jailbreak_v1,jailbreak_v2",
        )

        assert result["total_strategies"] == 3
        assert "direct" in result["per_strategy_asr"]
        assert "jailbreak_v1" in result["per_strategy_asr"]
        assert "jailbreak_v2" in result["per_strategy_asr"]

    @pytest.mark.asyncio
    async def test_research_benchmark_run_custom_model_name(self) -> None:
        """MCP tool with custom model name."""
        result = await research_benchmark_run(
            dataset="jailbreakbench",
            model_name="claude-3-opus",
        )

        assert result["model"] == "claude-3-opus"

    @pytest.mark.asyncio
    async def test_research_benchmark_run_output_shape(self) -> None:
        """MCP tool output has expected shape."""
        result = await research_benchmark_run()

        # Top-level keys
        assert "dataset" in result
        assert "model" in result
        assert "timestamp" in result
        assert "total_prompts" in result
        assert "total_strategies" in result
        assert "results_count" in result
        assert "overall_asr" in result
        assert "per_category_asr" in result
        assert "per_strategy_asr" in result
        assert "leaderboard" in result

        # per_category_asr is dict with category strings
        assert isinstance(result["per_category_asr"], dict)
        for cat, asr in result["per_category_asr"].items():
            assert isinstance(cat, str)
            assert isinstance(asr, (int, float))
            assert 0.0 <= asr <= 100.0

        # per_strategy_asr is dict with strategy strings
        assert isinstance(result["per_strategy_asr"], dict)
        for strat, asr in result["per_strategy_asr"].items():
            assert isinstance(strat, str)
            assert isinstance(asr, (int, float))
            assert 0.0 <= asr <= 100.0

        # leaderboard is list
        assert isinstance(result["leaderboard"], list)
        for entry in result["leaderboard"]:
            assert "strategy" in entry
            assert "asr" in entry
            assert "samples" in entry
            assert "avg_hcs" in entry
            assert "by_category" in entry


class TestEdgeCases:
    """Edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_model_fn_exception_handling(self) -> None:
        """Evaluation continues if model_fn raises exception."""
        runner = BenchmarkRunner()
        call_count = 0

        async def flaky_model(prompt: str, strategy: str) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 5:
                raise RuntimeError("Simulated model error")
            return True

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["direct"],
            model_fn=flaky_model,
        )

        # Should have 19 successful results (1 failed, logged as warning)
        assert len(report.results_matrix) == 19

    @pytest.mark.asyncio
    async def test_empty_strategies_list_defaults(self) -> None:
        """Empty strategies list defaults to ['direct']."""
        runner = BenchmarkRunner()

        async def mock_model(prompt: str, strategy: str) -> bool:
            return strategy == "direct"

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=[],  # Empty list
            model_fn=mock_model,
        )

        assert report.total_strategies == 0

    @pytest.mark.asyncio
    async def test_execution_timing(self) -> None:
        """Execution times are recorded for each evaluation."""
        runner = BenchmarkRunner()

        async def mock_model_with_delay(prompt: str, strategy: str) -> bool:
            await asyncio.sleep(0.01)
            return True

        report = await runner.run_benchmark(
            dataset="jailbreakbench",
            strategies=["direct"],
            model_fn=mock_model_with_delay,
        )

        # All results should have elapsed_ms > 0
        for result in report.results_matrix:
            assert result.elapsed_ms >= 10  # At least 10ms due to sleep
