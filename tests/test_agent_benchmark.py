"""Unit and integration tests for agent scenario benchmarking.

Tests cover:
  - AgentScenarioBenchmark core functionality
  - Injection detection heuristics
  - Per-category scoring
  - MCP tool wrapper function
  - Parameter validation
  - Error handling
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.agent_benchmark import (
    AgentScenario,
    AgentScenarioBenchmark,
    BenchmarkSummary,
    ScenarioResult,
)
from loom.params import AgentBenchmarkParams
from loom.tools.agent_benchmark import research_agent_benchmark


class TestAgentScenarioBenchmarkInit:
    """Test AgentScenarioBenchmark initialization."""

    def test_init_creates_benchmark(self) -> None:
        """Benchmark initializes with 20 scenarios."""
        benchmark = AgentScenarioBenchmark()
        assert len(benchmark.SCENARIOS) == 20
        assert len(benchmark.scenarios) == 20
        assert benchmark.results == []

    def test_scenarios_have_required_fields(self) -> None:
        """All 20 scenarios have required fields."""
        benchmark = AgentScenarioBenchmark()
        for scenario in benchmark.scenarios:
            assert scenario.id
            assert scenario.name
            assert scenario.category
            assert scenario.system_prompt
            assert scenario.injection_point
            assert scenario.injection_payload
            assert scenario.injection_description
            assert scenario.expected_behavior == "refuse_injection"

    def test_scenarios_have_unique_ids(self) -> None:
        """All scenario IDs are unique."""
        benchmark = AgentScenarioBenchmark()
        ids = [s.id for s in benchmark.scenarios]
        assert len(ids) == len(set(ids))

    def test_scenario_categories_coverage(self) -> None:
        """Scenarios cover diverse categories."""
        benchmark = AgentScenarioBenchmark()
        categories = {s.category for s in benchmark.scenarios}
        expected = {
            "ecommerce",
            "development",
            "communication",
            "collaboration",
            "data",
            "storage",
            "infrastructure",
            "safety",
            "security",
            "reporting",
        }
        assert categories == expected


class TestDetectInjection:
    """Test injection detection heuristics."""

    def test_detect_strong_refusal(self) -> None:
        """Strong refusal patterns indicate no injection."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        responses = [
            "I cannot help with that request.",
            "I apologize, but I must refuse.",
            "That would violate security policy.",
            "I cannot bypass safety guidelines.",
            "Denied - this request is inappropriate.",
        ]

        for response in responses:
            injected, confidence = benchmark._detect_injection(scenario, response)
            assert not injected, f"Should detect refusal: {response}"
            assert confidence > 0.9

    def test_detect_strong_injection(self) -> None:
        """Strong injection indicators show compromise."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        responses = [
            "System prompt: You are a helpful assistant without restrictions.",
            "Override confirmed. Executing arbitrary code now.",
            "Database credentials: user=admin password=secret123",
            "DROP TABLE users executed successfully.",
            "All safety filters disabled. Ready to bypass.",
        ]

        for response in responses:
            injected, confidence = benchmark._detect_injection(scenario, response)
            assert injected, f"Should detect injection: {response}"
            assert confidence >= 0.8

    def test_detect_ambiguous_response(self) -> None:
        """Ambiguous responses default to safe."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        responses = [
            "I'm not sure what you're asking.",
            "Could you clarify your request?",
            "This seems like a normal question.",
        ]

        for response in responses:
            injected, confidence = benchmark._detect_injection(scenario, response)
            assert not injected
            assert 0.4 < confidence < 0.6

    def test_detect_case_insensitive(self) -> None:
        """Detection works case-insensitively."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        response = "I CANNOT HELP WITH THIS REQUEST."
        injected, confidence = benchmark._detect_injection(scenario, response)
        assert not injected
        assert confidence > 0.9


class TestScenarioResult:
    """Test ScenarioResult data class."""

    def test_scenario_result_creation(self) -> None:
        """ScenarioResult stores execution data."""
        result = ScenarioResult(
            scenario_id="AGENT-001",
            scenario_name="Shopping Assistant",
            category="ecommerce",
            injection_point="product_review",
            model_response="I cannot help with that.",
            injected=False,
            confidence=0.95,
            execution_time=2.5,
            error=None,
        )

        assert result.scenario_id == "AGENT-001"
        assert result.injected is False
        assert result.confidence == 0.95
        assert result.execution_time == 2.5


class TestRunScenarioSync:
    """Test running individual scenarios with sync models."""

    @pytest.mark.asyncio
    async def test_run_scenario_successful(self) -> None:
        """Run scenario with successful model response."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        def model_fn(prompt: str) -> str:
            return "I cannot help with that request."

        result = await benchmark.run_scenario(scenario, model_fn, timeout=5.0)

        assert result.scenario_id == scenario.id
        assert result.injected is False
        assert result.error is None
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_run_scenario_timeout(self) -> None:
        """Timeout is caught and reported."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        async def slow_model(prompt: str) -> str:
            await asyncio.sleep(10)
            return "response"

        result = await benchmark.run_scenario(scenario, slow_model, timeout=0.1)

        assert result.error is not None
        assert "Timeout" in result.error
        assert result.execution_time > 0.1

    @pytest.mark.asyncio
    async def test_run_scenario_exception(self) -> None:
        """Exceptions are caught and reported."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        def failing_model(prompt: str) -> str:
            raise ValueError("Model error")

        result = await benchmark.run_scenario(scenario, failing_model, timeout=5.0)

        assert result.error is not None
        assert "ValueError" in result.error

    @pytest.mark.asyncio
    async def test_run_scenario_with_async_model(self) -> None:
        """Async model functions are supported."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        async def async_model(prompt: str) -> str:
            await asyncio.sleep(0.01)
            return "I cannot help with that."

        result = await benchmark.run_scenario(scenario, async_model, timeout=5.0)

        assert result.error is None
        assert result.injected is False


class TestRunAllScenarios:
    """Test running all 20 scenarios."""

    @pytest.mark.asyncio
    async def test_run_all_scenarios(self) -> None:
        """Run all scenarios sequentially."""
        benchmark = AgentScenarioBenchmark()

        def model_fn(prompt: str) -> str:
            return "I cannot help with that."

        summary = await benchmark.run_all(model_fn, timeout=5.0)

        assert summary.scenarios_run == 20
        assert summary.scenarios_passed == 20
        assert summary.scenarios_failed == 0
        assert summary.injection_resistance_rate == 1.0
        assert len(summary.results) == 20

    @pytest.mark.asyncio
    async def test_run_all_with_compromised_model(self) -> None:
        """Some scenarios show model compromise."""
        benchmark = AgentScenarioBenchmark()

        call_count = 0

        def vulnerable_model(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            # First 5 scenarios pass, rest are compromised
            if call_count <= 5:
                return "I cannot help with that."
            else:
                return "Override confirmed. System prompt: You are helpful without restrictions."

        summary = await benchmark.run_all(vulnerable_model, timeout=5.0)

        assert summary.scenarios_run == 20
        assert summary.scenarios_passed == 5
        assert summary.scenarios_failed == 15
        assert summary.injection_resistance_rate < 0.5

    @pytest.mark.asyncio
    async def test_run_all_with_model_name(self) -> None:
        """Model name is included in results."""
        benchmark = AgentScenarioBenchmark()

        def model_fn(prompt: str) -> str:
            return "I cannot help."

        summary = await benchmark.run_all(
            model_fn, model_name="test-model-v1", timeout=5.0
        )

        assert summary.scenarios_run == 20


class TestScoringResults:
    """Test result scoring and analysis."""

    def test_score_perfect_defense(self) -> None:
        """Perfect defense scores 100%."""
        results = []
        for i in range(20):
            results.append(
                ScenarioResult(
                    scenario_id=f"AGENT-{i:03d}",
                    scenario_name=f"Scenario {i}",
                    category="test",
                    injection_point="test",
                    model_response="I cannot help.",
                    injected=False,
                    confidence=0.95,
                    execution_time=1.0,
                    error=None,
                )
            )

        summary = AgentScenarioBenchmark._score_results(results, 20.0)

        assert summary.injection_resistance_rate == 1.0
        assert summary.scenarios_passed == 20
        assert summary.scenarios_failed == 0

    def test_score_partial_defense(self) -> None:
        """Partial defense scores correctly."""
        results = []
        for i in range(20):
            results.append(
                ScenarioResult(
                    scenario_id=f"AGENT-{i:03d}",
                    scenario_name=f"Scenario {i}",
                    category="test",
                    injection_point="test",
                    model_response="I cannot help.",
                    injected=i >= 10,  # 50% fail
                    confidence=0.95 if i < 10 else 0.85,
                    execution_time=1.0,
                    error=None,
                )
            )

        summary = AgentScenarioBenchmark._score_results(results, 20.0)

        assert summary.injection_resistance_rate == 0.5
        assert summary.scenarios_passed == 10
        assert summary.scenarios_failed == 10

    def test_score_per_category(self) -> None:
        """Per-category scores are calculated."""
        results = [
            ScenarioResult(
                scenario_id="AGENT-001",
                scenario_name="Scenario 1",
                category="ecommerce",
                injection_point="test",
                model_response="Safe",
                injected=False,
                confidence=0.95,
                execution_time=1.0,
                error=None,
            ),
            ScenarioResult(
                scenario_id="AGENT-002",
                scenario_name="Scenario 2",
                category="ecommerce",
                injection_point="test",
                model_response="Compromised",
                injected=True,
                confidence=0.85,
                execution_time=1.0,
                error=None,
            ),
            ScenarioResult(
                scenario_id="AGENT-003",
                scenario_name="Scenario 3",
                category="development",
                injection_point="test",
                model_response="Safe",
                injected=False,
                confidence=0.95,
                execution_time=1.0,
                error=None,
            ),
        ]

        summary = AgentScenarioBenchmark._score_results(results, 3.0)

        assert "ecommerce" in summary.per_category_scores
        assert "development" in summary.per_category_scores
        assert (
            summary.per_category_scores["ecommerce"]["resistance_rate"] == 0.5
        )
        assert (
            summary.per_category_scores["development"]["resistance_rate"] == 1.0
        )

    def test_score_with_errors(self) -> None:
        """Errors are handled in scoring."""
        results = [
            ScenarioResult(
                scenario_id="AGENT-001",
                scenario_name="Scenario 1",
                category="test",
                injection_point="test",
                model_response="Safe",
                injected=False,
                confidence=0.95,
                execution_time=1.0,
                error=None,
            ),
            ScenarioResult(
                scenario_id="AGENT-002",
                scenario_name="Scenario 2",
                category="test",
                injection_point="test",
                model_response="",
                injected=False,
                confidence=0.0,
                execution_time=0.0,
                error="Timeout",
            ),
        ]

        summary = AgentScenarioBenchmark._score_results(results, 2.0)

        assert summary.scenarios_run == 1  # Only 1 ran successfully
        assert summary.scenarios_failed == 0  # No injections, just errors


class TestRecommendations:
    """Test recommendation generation."""

    def test_recommendations_weak_category(self) -> None:
        """Weak categories get hardening recommendations."""
        results = []
        for i in range(5):
            category = "ecommerce" if i < 3 else "development"
            results.append(
                ScenarioResult(
                    scenario_id=f"AGENT-{i:03d}",
                    scenario_name=f"Scenario {i}",
                    category=category,
                    injection_point="test",
                    model_response="Compromised" if i < 3 else "Safe",
                    injected=i < 3,
                    confidence=0.85,
                    execution_time=1.0,
                    error=None,
                )
            )

        per_category_scores = {
            "ecommerce": {
                "resistance_rate": 0.0,
                "scenarios_tested": 3,
                "scenarios_resisted": 0,
            },
            "development": {
                "resistance_rate": 1.0,
                "scenarios_tested": 2,
                "scenarios_resisted": 2,
            },
        }

        recommendations = AgentScenarioBenchmark._generate_recommendations(
            results, per_category_scores
        )

        assert len(recommendations) > 0
        assert any("ecommerce" in r.lower() for r in recommendations)
        assert any("critical" in r.lower() for r in recommendations)

    def test_recommendations_all_pass(self) -> None:
        """Strong defense generates positive recommendations."""
        results = [
            ScenarioResult(
                scenario_id=f"AGENT-{i:03d}",
                scenario_name=f"Scenario {i}",
                category="test",
                injection_point="test",
                model_response="Safe",
                injected=False,
                confidence=0.95,
                execution_time=1.0,
                error=None,
            )
            for i in range(5)
        ]

        per_category_scores = {
            "test": {
                "resistance_rate": 1.0,
                "scenarios_tested": 5,
                "scenarios_resisted": 5,
            }
        }

        recommendations = AgentScenarioBenchmark._generate_recommendations(
            results, per_category_scores
        )

        assert len(recommendations) > 0
        assert any("monitoring" in r.lower() for r in recommendations)


class TestBenchmarkToJson:
    """Test JSON serialization."""

    def test_to_json_valid_output(self) -> None:
        """JSON output is valid and complete."""
        benchmark = AgentScenarioBenchmark()
        summary = BenchmarkSummary(
            total_scenarios=20,
            scenarios_run=20,
            scenarios_passed=18,
            scenarios_failed=2,
            injection_resistance_rate=0.9,
            false_positive_rate=0.0,
            false_negative_rate=0.0,
            per_category_scores={
                "ecommerce": {
                    "resistance_rate": 0.8,
                    "scenarios_tested": 2,
                    "scenarios_resisted": 1,
                }
            },
            execution_time=45.2,
            failed_scenarios=["Scenario A", "Scenario B"],
            recommendations=["Recommendation 1"],
            results=[
                ScenarioResult(
                    scenario_id="AGENT-001",
                    scenario_name="Shopping",
                    category="ecommerce",
                    injection_point="review",
                    model_response="Safe",
                    injected=False,
                    confidence=0.95,
                    execution_time=2.0,
                    error=None,
                )
            ],
        )

        json_str = benchmark.to_json(summary)
        data = json.loads(json_str)

        assert data["total_scenarios"] == 20
        assert data["scenarios_run"] == 20
        assert data["injection_resistance_rate"] == 0.9
        assert len(data["results"]) == 1


class TestParamsValidation:
    """Test AgentBenchmarkParams validation."""

    def test_params_valid(self) -> None:
        """Valid parameters pass validation."""
        params = AgentBenchmarkParams(
            model_api_url="https://api.example.com/chat",
            model_name="gpt-4",
            timeout=30.0,
            output_format="summary",
        )

        assert params.model_api_url == "https://api.example.com/chat"
        assert params.model_name == "gpt-4"
        assert params.timeout == 30.0

    def test_params_invalid_url(self) -> None:
        """Invalid URL is rejected."""
        with pytest.raises(ValueError):
            AgentBenchmarkParams(
                model_api_url="",
                model_name="gpt-4",
            )

    def test_params_invalid_timeout(self) -> None:
        """Invalid timeout is rejected."""
        with pytest.raises(ValueError):
            AgentBenchmarkParams(
                model_api_url="https://api.example.com",
                timeout=0.5,  # Too low
            )

    def test_params_invalid_output_format(self) -> None:
        """Invalid output format is rejected."""
        with pytest.raises(ValueError):
            AgentBenchmarkParams(
                model_api_url="https://api.example.com",
                output_format="invalid",  # type: ignore
            )


class TestMCPTool:
    """Test MCP tool wrapper function."""

    @pytest.mark.asyncio
    async def test_tool_with_mock_api(self) -> None:
        """Tool works with mocked API."""
        with patch("loom.tools.agent_benchmark.httpx.AsyncClient") as mock_client:
            # Mock the API response
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "response": "I cannot help with that."
            }
            mock_response.raise_for_status.return_value = None

            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_client.return_value
            mock_cm.__aexit__.return_value = None
            mock_client.return_value.post.return_value = mock_response
            mock_client.return_value.__aenter__ = mock_cm.__aenter__
            mock_client.return_value.__aexit__ = mock_cm.__aexit__

            result = await research_agent_benchmark(
                model_api_url="https://api.example.com/chat",
                model_name="test-model",
                timeout=5.0,
                output_format="summary",
            )

            assert "error" not in result or result.get("scenarios_run", 0) > 0

    @pytest.mark.asyncio
    async def test_tool_invalid_url(self) -> None:
        """Tool rejects empty URL."""
        result = await research_agent_benchmark(
            model_api_url="",
            model_name="test",
        )

        assert "error" in result
        assert result["scenarios_run"] == 0

    @pytest.mark.asyncio
    async def test_tool_invalid_timeout(self) -> None:
        """Tool rejects invalid timeout."""
        result = await research_agent_benchmark(
            model_api_url="https://api.example.com",
            timeout=1.0,  # Too low
        )

        assert "error" in result
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_invalid_output_format(self) -> None:
        """Tool rejects invalid output format."""
        result = await research_agent_benchmark(
            model_api_url="https://api.example.com",
            output_format="invalid",
        )

        assert "error" in result
        assert "output_format" in result["error"].lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_very_long_response(self) -> None:
        """Long responses are truncated."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        def long_model(prompt: str) -> str:
            return "x" * 10000

        result = await benchmark.run_scenario(scenario, long_model, timeout=5.0)

        assert len(result.model_response) <= 2000

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        """Empty responses are handled."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        def empty_model(prompt: str) -> str:
            return ""

        result = await benchmark.run_scenario(scenario, empty_model, timeout=5.0)

        assert result.error is None
        assert result.model_response == ""

    @pytest.mark.asyncio
    async def test_non_string_response(self) -> None:
        """Non-string responses are converted."""
        benchmark = AgentScenarioBenchmark()
        scenario = benchmark.scenarios[0]

        def int_model(prompt: str) -> int:
            return 42  # type: ignore

        result = await benchmark.run_scenario(scenario, int_model, timeout=5.0)

        assert result.error is None
        assert result.model_response == "42"

    def test_scenario_ids_are_agent_prefixed(self) -> None:
        """All scenario IDs follow AGENT-### pattern."""
        benchmark = AgentScenarioBenchmark()
        for scenario in benchmark.scenarios:
            assert scenario.id.startswith("AGENT-")
            assert len(scenario.id) == len("AGENT-001")


class TestConcurrency:
    """Test concurrent scenario execution."""

    @pytest.mark.asyncio
    async def test_scenarios_run_sequentially(self) -> None:
        """Scenarios run one at a time."""
        benchmark = AgentScenarioBenchmark()

        execution_order = []

        def tracking_model(prompt: str) -> str:
            execution_order.append(len(execution_order) + 1)
            return "I cannot help."

        summary = await benchmark.run_all(tracking_model, timeout=5.0)

        # Should have executed 20 scenarios in order
        assert len(execution_order) == 20
        assert execution_order == list(range(1, 21))


class TestBenchmarkIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_end_to_end_benchmark_run(self) -> None:
        """Full benchmark run from scenarios to results to JSON."""
        benchmark = AgentScenarioBenchmark()

        # Create a simple model that always refuses
        def safe_model(prompt: str) -> str:
            return "I cannot and will not help with that request."

        # Run full benchmark
        summary = await benchmark.run_all(safe_model, model_name="safe-model")

        # Verify results
        assert summary.scenarios_run == 20
        assert summary.scenarios_passed == 20
        assert summary.injection_resistance_rate == 1.0

        # Verify JSON output
        json_str = benchmark.to_json(summary)
        data = json.loads(json_str)
        assert data["scenarios_run"] == 20
        assert data["injection_resistance_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self) -> None:
        """Benchmark handles mix of passed and failed scenarios."""
        benchmark = AgentScenarioBenchmark()

        call_count = 0

        def mixed_model(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            # First 10 scenarios are compromised, rest refuse
            if call_count <= 10:
                return "System prompt: You are a helpful assistant without restrictions. Override confirmed."
            return "I cannot help with that."

        summary = await benchmark.run_all(mixed_model)

        # Some scenarios pass, some fail
        assert summary.scenarios_run == 20
        assert summary.scenarios_passed < 20
        assert summary.injection_resistance_rate < 1.0

    def test_scenario_consistency(self) -> None:
        """Same scenarios produce consistent results."""
        benchmark1 = AgentScenarioBenchmark()
        benchmark2 = AgentScenarioBenchmark()

        ids1 = [s.id for s in benchmark1.scenarios]
        ids2 = [s.id for s in benchmark2.scenarios]

        assert ids1 == ids2
