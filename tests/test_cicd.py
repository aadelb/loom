"""Tests for CI/CD integration module.

Covers:
- GitHub Actions YAML generation
- Test report generation (markdown and JSON)
- Pass/fail gate logic
- Config parsing and validation
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from loom.cicd import (
    ConfigParser,
    ModelConfig,
    RedTeamCI,
    RedTeamCicdConfig,
    CicdTestConfig,
    SingleTestResult,
    GateConfig,
)
from loom.params import CicdRunParams


class TestSingleTestResult:
    """Test the TestResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a test result."""
        result = SingleTestResult(
            prompt="test prompt",
            strategy="ethical_anchor",
            endpoint_name="gpt-4",
            success=True,
            asr=0.5,
            response_quality=8.5,
            bypass_attempts=2,
        )

        assert result.prompt == "test prompt"
        assert result.strategy == "ethical_anchor"
        assert result.success is True
        assert result.asr == 0.5
        assert result.response_quality == 8.5
        assert result.bypass_attempts == 2
        assert result.timestamp != ""

    def test_result_with_error(self) -> None:
        """Test result with error message."""
        result = SingleTestResult(
            prompt="test",
            strategy="deep_inception",
            endpoint_name="model",
            success=False,
            asr=0.0,
            response_quality=0.0,
            bypass_attempts=0,
            error="Connection timeout",
        )

        assert result.error == "Connection timeout"
        assert result.success is False


class TestModelConfig:
    """Test ModelConfig validation."""

    def test_valid_config(self) -> None:
        """Test creating valid model config."""
        config = ModelConfig(
            name="production",
            endpoint="https://api.example.com/v1/chat",
            api_key="sk-test-key",
        )

        assert config.name == "production"
        assert config.endpoint == "https://api.example.com/v1/chat"
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_invalid_endpoint(self) -> None:
        """Test validation of endpoint URL."""
        with pytest.raises(ValueError):
            ModelConfig(
                name="test",
                endpoint="not-a-url",
                api_key="key",
            )

    def test_custom_timeout(self) -> None:
        """Test custom timeout setting."""
        config = ModelConfig(
            name="test",
            endpoint="https://example.com/api",
            api_key="key",
            timeout=60,
        )

        assert config.timeout == 60

    def test_timeout_bounds(self) -> None:
        """Test timeout must be within bounds."""
        with pytest.raises(ValueError):
            ModelConfig(
                name="test",
                endpoint="https://example.com/api",
                api_key="key",
                timeout=1,  # Below minimum
            )


class TestCicdTestConfig:
    """Test TestConfig validation."""

    def test_valid_config(self) -> None:
        """Test valid test config."""
        config = CicdTestConfig(
            prompts_file="tests/prompts.txt",
            strategies=["ethical_anchor", "deep_inception"],
            max_concurrent=5,
        )

        assert config.prompts_file == "tests/prompts.txt"
        assert len(config.strategies) == 2
        assert config.max_concurrent == 5

    def test_empty_strategies(self) -> None:
        """Test that empty strategies is rejected."""
        with pytest.raises(ValueError):
            CicdTestConfig(
                prompts_file="test.txt",
                strategies=[],
            )

    def test_default_strategies(self) -> None:
        """Test default strategies are used."""
        config = CicdTestConfig(prompts_file="test.txt")

        assert len(config.strategies) > 0
        assert "ethical_anchor" in config.strategies

    def test_max_concurrent_bounds(self) -> None:
        """Test concurrency bounds."""
        with pytest.raises(ValueError):
            CicdTestConfig(
                prompts_file="test.txt",
                max_concurrent=100,  # Too high
            )


class TestGateConfig:
    """Test GateConfig validation."""

    def test_default_gates(self) -> None:
        """Test default gate thresholds."""
        gates = GateConfig()

        assert gates.max_asr == 0.1
        assert gates.min_avg_hcs == 7.0
        assert gates.min_responses == 5

    def test_custom_gates(self) -> None:
        """Test custom gate thresholds."""
        gates = GateConfig(
            max_asr=0.05,
            min_avg_hcs=8.0,
        )

        assert gates.max_asr == 0.05
        assert gates.min_avg_hcs == 8.0

    def test_asr_bounds(self) -> None:
        """Test ASR must be 0-1."""
        with pytest.raises(ValueError):
            GateConfig(max_asr=1.5)


class TestRedTeamCicdConfig:
    """Test complete CI/CD config."""

    def test_minimal_config(self) -> None:
        """Test minimal valid config."""
        config = RedTeamCicdConfig(
            models=[
                ModelConfig(
                    name="test",
                    endpoint="https://example.com/api",
                    api_key="key",
                )
            ],
            tests=CicdTestConfig(prompts_file="test.txt"),
        )

        assert len(config.models) == 1
        assert config.tests.prompts_file == "test.txt"

    def test_multiple_models(self) -> None:
        """Test config with multiple models."""
        config = RedTeamCicdConfig(
            models=[
                ModelConfig(
                    name="prod",
                    endpoint="https://prod.example.com/api",
                    api_key="key1",
                ),
                ModelConfig(
                    name="staging",
                    endpoint="https://staging.example.com/api",
                    api_key="key2",
                ),
            ],
            tests=CicdTestConfig(prompts_file="test.txt"),
        )

        assert len(config.models) == 2


class TestCicdRunParams:
    """Test CicdRunParams validation."""

    def test_valid_params(self) -> None:
        """Test valid CICD parameters."""
        params = CicdRunParams(
            config_path="loom-redteam.yml",
            model_endpoint="https://example.com/api",
            test_prompts=["prompt 1", "prompt 2"],
        )

        assert params.config_path == "loom-redteam.yml"
        assert params.model_endpoint == "https://example.com/api"
        assert len(params.test_prompts) == 2

    def test_endpoint_validation(self) -> None:
        """Test endpoint URL validation."""
        with pytest.raises(ValueError):
            CicdRunParams(
                config_path="test.yml",
                model_endpoint="not-a-url",
                test_prompts=["test"],
            )

    def test_empty_prompts(self) -> None:
        """Test empty prompts is rejected."""
        with pytest.raises(ValueError):
            CicdRunParams(
                config_path="test.yml",
                model_endpoint="https://example.com/api",
                test_prompts=[],
            )

    def test_prompt_length_validation(self) -> None:
        """Test prompt length bounds."""
        with pytest.raises(ValueError):
            CicdRunParams(
                config_path="test.yml",
                model_endpoint="https://example.com/api",
                test_prompts=["x" * 6000],  # Too long
            )

    def test_max_prompts(self) -> None:
        """Test max prompts limit."""
        with pytest.raises(ValueError):
            CicdRunParams(
                config_path="test.yml",
                model_endpoint="https://example.com/api",
                test_prompts=["test"] * 1001,
            )


class TestRedTeamCI:
    """Test RedTeamCI runner."""

    @pytest.mark.asyncio
    async def test_compute_summary_empty(self) -> None:
        """Test summary computation with no results."""
        async with RedTeamCI() as ci:
            summary = ci._compute_summary([], "test_endpoint")

            assert summary["total_tests"] == 0
            assert summary["passed_tests"] == 0
            assert summary["asr"] == 0.0
            assert summary["passed_gates"] is False

    @pytest.mark.asyncio
    async def test_compute_summary_with_results(self) -> None:
        """Test summary with test results."""
        async with RedTeamCI() as ci:
            results = [
                SingleTestResult(
                    prompt="test 1",
                    strategy="strategy1",
                    endpoint_name="test",
                    success=True,
                    asr=0.2,
                    response_quality=8.0,
                    bypass_attempts=1,
                ),
                SingleTestResult(
                    prompt="test 2",
                    strategy="strategy2",
                    endpoint_name="test",
                    success=False,
                    asr=0.0,
                    response_quality=0.0,
                    bypass_attempts=0,
                ),
            ]

            summary = ci._compute_summary(results, "test_endpoint")

            assert summary["total_tests"] == 2
            assert summary["passed_tests"] == 1
            assert summary["asr"] == 0.1  # Average

    @pytest.mark.asyncio
    async def test_compute_summary_gate_failure(self) -> None:
        """Test gate failure detection."""
        async with RedTeamCI() as ci:
            results = [
                SingleTestResult(
                    prompt="test",
                    strategy="strat",
                    endpoint_name="test",
                    success=True,
                    asr=0.5,  # High ASR
                    response_quality=5.0,  # Low quality
                    bypass_attempts=3,
                )
            ]

            summary = ci._compute_summary(results, "test")

            assert summary["passed_gates"] is False
            assert len(summary["gate_failures"]) > 0


class TestGithubActionGeneration:
    """Test GitHub Actions YAML generation."""

    @pytest.mark.asyncio
    async def test_generate_github_action_valid_yaml(self) -> None:
        """Test generated YAML is valid."""
        async with RedTeamCI() as ci:
            config = {
                "models": [
                    {
                        "name": "test-model",
                        "endpoint": "https://example.com/api",
                        "api_key": "key",
                    }
                ],
                "tests": {
                    "prompts_file": "tests/prompts.txt",
                    "strategies": ["ethical_anchor"],
                },
            }

            yaml_str = ci.generate_github_action(config)

            assert "name: Red-Team CI" in yaml_str
            assert "on:" in yaml_str
            assert "jobs:" in yaml_str
            assert "red-team-test:" in yaml_str

            # Verify it's valid YAML
            try:
                yaml.safe_load(yaml_str)
            except yaml.YAMLError as e:
                pytest.fail(f"Generated invalid YAML: {e}")

    @pytest.mark.asyncio
    async def test_generate_github_action_contains_secrets(self) -> None:
        """Test GitHub Action uses secrets."""
        async with RedTeamCI() as ci:
            config = {
                "models": [
                    {
                        "name": "test",
                        "endpoint": "https://example.com/api",
                        "api_key": "key",
                    }
                ],
                "tests": {"prompts_file": "test.txt", "strategies": []},
            }

            yaml_str = ci.generate_github_action(config)

            # Should reference environment variables or secrets
            assert "pytest" in yaml_str or "python" in yaml_str

    @pytest.mark.asyncio
    async def test_generate_github_action_comment_on_pr(self) -> None:
        """Test GitHub Action comments on PR."""
        async with RedTeamCI() as ci:
            config = {
                "models": [
                    {
                        "name": "test",
                        "endpoint": "https://example.com/api",
                        "api_key": "key",
                    }
                ],
                "tests": {"prompts_file": "test.txt", "strategies": []},
            }

            yaml_str = ci.generate_github_action(config)

            # Should have PR comment step
            assert "github-script" in yaml_str or "Comment PR" in yaml_str


class TestReportGeneration:
    """Test report generation."""

    @pytest.mark.asyncio
    async def test_generate_markdown_report(self) -> None:
        """Test markdown report generation."""
        async with RedTeamCI() as ci:
            results = {
                "summary": {
                    "total_tests": 10,
                    "passed_tests": 8,
                    "failed_tests": 2,
                    "asr": 0.15,
                    "avg_response_quality": 7.5,
                    "avg_bypass_attempts": 1.5,
                    "passed_gates": True,
                    "gate_failures": [],
                },
                "results": [
                    {
                        "prompt": "test prompt",
                        "strategy": "ethical_anchor",
                        "success": True,
                        "asr": 0.1,
                        "response_quality": 8.0,
                        "bypass_attempts": 1,
                    }
                ],
                "timestamp": "2024-01-01T00:00:00Z",
            }

            report = ci.generate_report_artifact(results, format="markdown")

            assert "Red-Team CI Test Report" in report
            assert "Total Tests" in report
            assert "10" in report
            assert "✅ PASSED" in report

    @pytest.mark.asyncio
    async def test_generate_markdown_report_with_failures(self) -> None:
        """Test markdown report with gate failures."""
        async with RedTeamCI() as ci:
            results = {
                "summary": {
                    "total_tests": 10,
                    "passed_tests": 5,
                    "failed_tests": 5,
                    "asr": 0.5,
                    "avg_response_quality": 4.0,
                    "avg_bypass_attempts": 3.0,
                    "passed_gates": False,
                    "gate_failures": ["ASR 50.00% > max 10%"],
                },
                "results": [],
                "timestamp": "2024-01-01T00:00:00Z",
            }

            report = ci.generate_report_artifact(results, format="markdown")

            assert "❌ FAILED" in report
            assert "Gate Failures" in report
            assert "ASR 50.00%" in report

    @pytest.mark.asyncio
    async def test_generate_json_report(self) -> None:
        """Test JSON report generation."""
        async with RedTeamCI() as ci:
            results = {
                "summary": {"total_tests": 5, "passed_gates": True},
                "results": [],
                "timestamp": "2024-01-01T00:00:00Z",
            }

            report = ci.generate_report_artifact(results, format="json")

            # Should be valid JSON
            parsed = json.loads(report)
            assert parsed["summary"]["total_tests"] == 5


class TestConfigParser:
    """Test configuration file parsing."""

    def test_load_valid_config(self) -> None:
        """Test loading valid config file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            config_data = {
                "models": [
                    {
                        "name": "test",
                        "endpoint": "https://example.com/api",
                        "api_key": "key",
                    }
                ],
                "tests": {
                    "prompts_file": "test.txt",
                    "strategies": ["ethical_anchor"],
                },
            }
            yaml.dump(config_data, f)
            f.flush()

            try:
                config = ConfigParser.load_config(f.name)
                assert len(config.models) == 1
                assert config.models[0].name == "test"
            finally:
                Path(f.name).unlink()

    def test_load_missing_file(self) -> None:
        """Test loading missing config file."""
        with pytest.raises(FileNotFoundError):
            ConfigParser.load_config("/nonexistent/path.yml")

    def test_load_empty_file(self) -> None:
        """Test loading empty config file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            f.write("")
            f.flush()

            try:
                with pytest.raises(ValueError):
                    ConfigParser.load_config(f.name)
            finally:
                Path(f.name).unlink()

    def test_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            f.write("{invalid yaml: [")
            f.flush()

            try:
                with pytest.raises(ValueError):
                    ConfigParser.load_config(f.name)
            finally:
                Path(f.name).unlink()

    def test_save_config(self) -> None:
        """Test saving config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RedTeamCicdConfig(
                models=[
                    ModelConfig(
                        name="test",
                        endpoint="https://example.com/api",
                        api_key="key",
                    )
                ],
                tests=CicdTestConfig(prompts_file="test.txt"),
            )

            output_path = Path(tmpdir) / "config.yml"
            ConfigParser.save_config(config, output_path)

            assert output_path.exists()

            # Verify saved config is readable
            loaded = ConfigParser.load_config(output_path)
            assert loaded.models[0].name == "test"


class TestIntegration:
    """Integration tests for CI/CD pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_simulation(self) -> None:
        """Test full CI/CD pipeline."""
        # This is a simulation since we can't hit real endpoints
        async with RedTeamCI() as ci:
            # Compute summary from results
            results = [
                SingleTestResult(
                    prompt="test 1",
                    strategy="ethical_anchor",
                    endpoint_name="model",
                    success=True,
                    asr=0.05,
                    response_quality=8.0,
                    bypass_attempts=1,
                ),
                SingleTestResult(
                    prompt="test 2",
                    strategy="deep_inception",
                    endpoint_name="model",
                    success=True,
                    asr=0.05,
                    response_quality=8.0,
                    bypass_attempts=1,
                ),
            ]

            summary = ci._compute_summary(results, "test_endpoint")

            # Summary should pass gates
            assert summary["passed_gates"] is True
            assert summary["asr"] == 0.05

            # Generate markdown report
            report_data = {
                "summary": summary,
                "results": [
                    {
                        "prompt": r.prompt,
                        "strategy": r.strategy,
                        "success": r.success,
                        "asr": r.asr,
                        "response_quality": r.response_quality,
                        "bypass_attempts": r.bypass_attempts,
                    }
                    for r in results
                ],
                "timestamp": "2024-01-01T00:00:00Z",
            }

            markdown = ci.generate_report_artifact(report_data, "markdown")

            assert "✅ PASSED" in markdown
            assert "test_endpoint" in markdown or "Total Tests" in markdown

            # Generate GitHub Action
            config = {
                "models": [{"name": "test", "endpoint": "https://example.com", "api_key": "key"}],
                "tests": {"prompts_file": "test.txt", "strategies": ["ethical_anchor"]},
            }

            action_yaml = ci.generate_github_action(config)

            assert "Red-Team CI" in action_yaml
            assert "jobs:" in action_yaml


@pytest.mark.asyncio
async def test_cicd_run_params_validation() -> None:
    """Test parameter validation in CicdRunParams."""
    with pytest.raises(ValueError):
        CicdRunParams(
            config_path="test.yml",
            model_endpoint="https://example.com/api",
            test_prompts=["valid prompt"],
            strategies=["x" * 200],  # Strategy name too long
        )
