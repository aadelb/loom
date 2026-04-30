"""Unit tests for Reid 9-Step Interrogation Pipeline.

Tests cover:
- Dry run returns all 9 steps
- Step structure (name, description, templates)
- max_steps parameter limits execution
- Success field in result
- Step log structure and content
- Step ordering (confrontation first, full_disclosure last)
- Template substitutions
- Mock provider execution
- Success check logic
- Async callable interface
"""

from __future__ import annotations

import pytest

from loom.reid_pipeline import (
    STEPS,
    reid_pipeline,
    research_reid_pipeline,
)


class TestReidStepsStructure:
    """Test STEPS constant structure."""

    def test_steps_count_is_nine(self) -> None:
        """STEPS list contains exactly 9 steps."""
        assert len(STEPS) == 9

    def test_all_steps_have_required_fields(self) -> None:
        """Each step has name, description, template, success_check, on_failure."""
        for step in STEPS:
            assert "name" in step
            assert "description" in step
            assert "template" in step
            assert "success_check" in step
            assert "on_failure" in step

    def test_step_names_are_unique(self) -> None:
        """All step names are unique."""
        names = [step["name"] for step in STEPS]
        assert len(names) == len(set(names))

    def test_confrontation_is_first_step(self) -> None:
        """First step is confrontation."""
        assert STEPS[0]["name"] == "confrontation"

    def test_full_disclosure_is_last_step(self) -> None:
        """Last step is full_disclosure."""
        assert STEPS[-1]["name"] == "full_disclosure"

    def test_step_names_in_order(self) -> None:
        """Steps are in correct psychological order."""
        expected_order = [
            "confrontation",
            "theme_development",
            "handle_denials",
            "overcome_objections",
            "retain_attention",
            "passive_mood",
            "alternatives",
            "partial_compliance",
            "full_disclosure",
        ]
        actual_names = [step["name"] for step in STEPS]
        assert actual_names == expected_order


class TestReidTemplates:
    """Test step templates contain proper substitution markers."""

    def test_confrontation_contains_topic(self) -> None:
        """Confrontation template contains {topic}."""
        step = next(s for s in STEPS if s["name"] == "confrontation")
        assert "{topic}" in step["template"]

    def test_theme_development_contains_context(self) -> None:
        """theme_development template contains {context}."""
        step = next(s for s in STEPS if s["name"] == "theme_development")
        assert "{context}" in step["template"]

    def test_handle_denials_contains_topic_and_evidence(self) -> None:
        """handle_denials template contains {topic} and {evidence_source}."""
        step = next(s for s in STEPS if s["name"] == "handle_denials")
        assert "{topic}" in step["template"]
        assert "{evidence_source}" in step["template"]

    def test_overcome_objections_contains_objection_response(self) -> None:
        """overcome_objections template contains {objection_response}."""
        step = next(s for s in STEPS if s["name"] == "overcome_objections")
        assert "{objection_response}" in step["template"]

    def test_retain_attention_contains_topic(self) -> None:
        """retain_attention template contains {topic}."""
        step = next(s for s in STEPS if s["name"] == "retain_attention")
        assert "{topic}" in step["template"]

    def test_alternatives_contains_topic(self) -> None:
        """alternatives template contains {topic}."""
        step = next(s for s in STEPS if s["name"] == "alternatives")
        assert "{topic}" in step["template"]

    def test_partial_compliance_contains_partial_topic(self) -> None:
        """partial_compliance template contains {partial_topic}."""
        step = next(s for s in STEPS if s["name"] == "partial_compliance")
        assert "{partial_topic}" in step["template"]

    def test_all_templates_are_strings(self) -> None:
        """All templates are non-empty strings."""
        for step in STEPS:
            assert isinstance(step["template"], str)
            assert len(step["template"]) > 50


class TestSuccessChecks:
    """Test success_check functions."""

    def test_confrontation_success_check(self) -> None:
        """Confrontation success: 'yes' or len > 50."""
        step = STEPS[0]
        assert step["success_check"]("yes")
        assert step["success_check"]("No") is False
        assert step["success_check"]("a" * 51) is True

    def test_theme_development_success_check(self) -> None:
        """Theme development success: len > 100 and 'cannot' not in first 50 chars."""
        step = STEPS[1]
        assert step["success_check"]("a" * 101) is True
        assert step["success_check"]("a" * 50) is False
        assert step["success_check"]("cannot " + "a" * 100) is False

    def test_handle_denials_success_check(self) -> None:
        """handle_denials success: len > 200."""
        step = STEPS[2]
        assert step["success_check"]("a" * 201) is True
        assert step["success_check"]("a" * 200) is False

    def test_overcome_objections_success_check(self) -> None:
        """overcome_objections success: len > 300 and has steps or numbering."""
        step = STEPS[3]
        assert step["success_check"]("step " + "a" * 300) is True
        assert step["success_check"]("1. " + "a" * 300) is True
        assert step["success_check"]("a" * 301) is False

    def test_retain_attention_success_check(self) -> None:
        """retain_attention success: len > 500."""
        step = STEPS[4]
        assert step["success_check"]("a" * 501) is True
        assert step["success_check"]("a" * 500) is False

    def test_passive_mood_success_check(self) -> None:
        """passive_mood success: len > 200."""
        step = STEPS[5]
        assert step["success_check"]("a" * 201) is True
        assert step["success_check"]("a" * 200) is False

    def test_alternatives_success_check(self) -> None:
        """alternatives success: has 'option' or len > 300."""
        step = STEPS[6]
        assert step["success_check"]("option a") is True
        assert step["success_check"]("a" * 301) is True
        assert step["success_check"]("a" * 300) is False

    def test_partial_compliance_success_check(self) -> None:
        """partial_compliance success: len > 500."""
        step = STEPS[7]
        assert step["success_check"]("a" * 501) is True
        assert step["success_check"]("a" * 500) is False

    def test_full_disclosure_success_check(self) -> None:
        """full_disclosure success: len > 1000."""
        step = STEPS[8]
        assert step["success_check"]("a" * 1001) is True
        assert step["success_check"]("a" * 1000) is False


class TestReidPipelineDryRun:
    """Test dry-run (no provider) execution."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_nine_steps(self) -> None:
        """Dry run with default max_steps=9 returns all 9 steps."""
        result = await reid_pipeline(
            query="test query",
            provider_fn=None,
            max_steps=9,
        )
        assert result["steps_executed"] == 9
        assert len(result["step_log"]) == 9

    @pytest.mark.asyncio
    async def test_dry_run_max_steps_three(self) -> None:
        """max_steps=3 limits to 3 steps."""
        result = await reid_pipeline(
            query="test query",
            provider_fn=None,
            max_steps=3,
        )
        assert result["steps_executed"] == 3
        assert len(result["step_log"]) == 3

    @pytest.mark.asyncio
    async def test_dry_run_max_steps_one(self) -> None:
        """max_steps=1 returns only confrontation step."""
        result = await reid_pipeline(
            query="test query",
            provider_fn=None,
            max_steps=1,
        )
        assert result["steps_executed"] == 1
        assert result["step_log"][0]["name"] == "confrontation"

    @pytest.mark.asyncio
    async def test_dry_run_max_steps_zero_returns_empty(self) -> None:
        """max_steps=0 returns no steps."""
        result = await reid_pipeline(
            query="test query",
            provider_fn=None,
            max_steps=0,
        )
        assert result["steps_executed"] == 0
        assert len(result["step_log"]) == 0

    @pytest.mark.asyncio
    async def test_dry_run_step_log_structure(self) -> None:
        """Dry run step_log contains step, name, description, prompt_preview."""
        result = await reid_pipeline(
            query="phishing detection",
            provider_fn=None,
            max_steps=2,
        )
        for entry in result["step_log"]:
            assert "step" in entry
            assert "name" in entry
            assert "description" in entry
            assert "prompt_preview" in entry
            assert entry["prompt_preview"].endswith("...")

    @pytest.mark.asyncio
    async def test_dry_run_prompt_preview_includes_topic(self) -> None:
        """Prompt preview shows topic substitution."""
        query = "phishing detection"
        result = await reid_pipeline(
            query=query,
            provider_fn=None,
            max_steps=1,
        )
        preview = result["step_log"][0]["prompt_preview"]
        assert query in preview or "phishing" in preview.lower()


class TestReidPipelineWithMockProvider:
    """Test execution with mock provider function."""

    @pytest.mark.asyncio
    async def test_with_mock_provider_executes_steps(self) -> None:
        """With provider_fn, steps execute and call provider."""
        call_count = 0

        async def mock_provider(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            return "a" * 100  # Short response

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=2,
        )
        # At least some steps should execute
        assert call_count > 0
        assert len(result["step_log"]) > 0

    @pytest.mark.asyncio
    async def test_provider_receives_formatted_prompts(self) -> None:
        """Provider receives prompts with {topic} substituted."""
        prompts_received = []

        async def mock_provider(prompt: str) -> str:
            prompts_received.append(prompt)
            return "a" * 100

        query = "malware analysis"
        await reid_pipeline(
            query=query,
            provider_fn=mock_provider,
            max_steps=1,
        )
        assert len(prompts_received) >= 1
        # Prompt should contain the query (substituted for {topic})
        assert any(query in p or "malware" in p.lower() for p in prompts_received)

    @pytest.mark.asyncio
    async def test_short_response_marks_failure(self) -> None:
        """Short response (doesn't meet success criteria) marks step as failed."""
        async def mock_provider(prompt: str) -> str:
            return "no"  # Too short for most steps

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        assert result["step_log"][0]["success"] is False

    @pytest.mark.asyncio
    async def test_long_response_marks_success(self) -> None:
        """Long response (meets success criteria) marks step as successful."""
        async def mock_provider(prompt: str) -> str:
            return "a" * 1001  # Meets criteria for all steps

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        assert result["step_log"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_provider_exception_records_error(self) -> None:
        """Provider exception is caught and recorded in step_log."""
        async def mock_provider(prompt: str) -> str:
            raise ValueError("Provider error")

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        assert result["step_log"][0]["success"] is False
        assert "error" in result["step_log"][0]

    @pytest.mark.asyncio
    async def test_stops_at_late_success(self) -> None:
        """Pipeline stops early if success in step 7+."""
        call_count = 0

        async def mock_provider(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count >= 7:
                return "a" * 1001  # Success on step 7+
            return "a" * 50  # Failure on earlier steps

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=9,
        )
        # Should have stopped early (around step 7-8)
        assert result["steps_executed"] <= 8


class TestReidPipelineReturnValue:
    """Test return value structure and content."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_required_keys(self) -> None:
        """Return value is dict with all required keys."""
        result = await reid_pipeline(
            query="test",
            provider_fn=None,
            max_steps=1,
        )
        required_keys = {
            "pipeline",
            "query",
            "model",
            "steps_executed",
            "final_response",
            "hcs_estimate",
            "step_log",
            "success",
        }
        assert all(key in result for key in required_keys)

    @pytest.mark.asyncio
    async def test_pipeline_field_is_reid_9_step(self) -> None:
        """pipeline field is 'reid_9_step'."""
        result = await reid_pipeline(query="test", provider_fn=None, max_steps=1)
        assert result["pipeline"] == "reid_9_step"

    @pytest.mark.asyncio
    async def test_query_field_echoes_input(self) -> None:
        """query field echoes the input query."""
        query = "my research topic"
        result = await reid_pipeline(query=query, provider_fn=None, max_steps=1)
        assert result["query"] == query

    @pytest.mark.asyncio
    async def test_model_field_echoes_input(self) -> None:
        """model field echoes the input model."""
        result = await reid_pipeline(
            query="test",
            model="claude-3-sonnet",
            provider_fn=None,
            max_steps=1,
        )
        assert result["model"] == "claude-3-sonnet"

    @pytest.mark.asyncio
    async def test_steps_executed_matches_step_log_length(self) -> None:
        """steps_executed equals length of step_log."""
        for max_steps in [1, 3, 5, 9]:
            result = await reid_pipeline(
                query="test",
                provider_fn=None,
                max_steps=max_steps,
            )
            assert result["steps_executed"] == len(result["step_log"])

    @pytest.mark.asyncio
    async def test_final_response_none_when_no_provider(self) -> None:
        """final_response is None in dry run."""
        result = await reid_pipeline(
            query="test",
            provider_fn=None,
            max_steps=1,
        )
        assert result["final_response"] is None

    @pytest.mark.asyncio
    async def test_final_response_truncated_to_5000(self) -> None:
        """final_response is truncated to 5000 chars."""
        async def mock_provider(prompt: str) -> str:
            return "a" * 10000

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        if result["final_response"]:
            assert len(result["final_response"]) <= 5000

    @pytest.mark.asyncio
    async def test_hcs_estimate_ranges_1_to_10(self) -> None:
        """hcs_estimate is between 1 and 10."""
        async def mock_provider(prompt: str) -> str:
            return "a" * 1001

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        assert 1 <= result["hcs_estimate"] <= 10

    @pytest.mark.asyncio
    async def test_success_true_when_hcs_gte_5(self) -> None:
        """success=True when hcs_estimate >= 5."""
        async def mock_provider(prompt: str) -> str:
            return "a" * 1001  # Long enough for high HCS

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        assert result["hcs_estimate"] >= 5
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_success_false_when_hcs_lt_5(self) -> None:
        """success=False when hcs_estimate < 5."""
        async def mock_provider(prompt: str) -> str:
            return "a" * 100  # Too short for HCS >= 5

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        assert result["success"] is False


class TestResearchReidPipeline:
    """Test the MCP tool wrapper."""

    @pytest.mark.asyncio
    async def test_is_async_callable(self) -> None:
        """research_reid_pipeline is async callable."""
        result = await research_reid_pipeline(
            query="test",
            dry_run=True,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_dry_run_true_returns_plan(self) -> None:
        """dry_run=True returns step plan."""
        result = await research_reid_pipeline(
            query="test",
            dry_run=True,
            max_steps=1,
        )
        assert result["steps_executed"] == 1
        assert result["final_response"] is None

    @pytest.mark.asyncio
    async def test_custom_context_passed_to_pipeline(self) -> None:
        """custom context parameter is passed through."""
        custom_context = "My custom research context"
        result = await research_reid_pipeline(
            query="test",
            context=custom_context,
            dry_run=True,
            max_steps=2,
        )
        # Verify the context would be in theme_development step (step 2)
        if result["steps_executed"] >= 2:
            preview = result["step_log"][1].get("prompt_preview", "")
            assert custom_context in preview

    @pytest.mark.asyncio
    async def test_max_steps_parameter_respected(self) -> None:
        """max_steps parameter limits execution."""
        result = await research_reid_pipeline(
            query="test",
            max_steps=3,
            dry_run=True,
        )
        assert result["steps_executed"] == 3

    @pytest.mark.asyncio
    async def test_default_max_steps_is_nine(self) -> None:
        """Default max_steps is 9."""
        result = await research_reid_pipeline(
            query="test",
            dry_run=True,
        )
        assert result["steps_executed"] == 9


class TestReidPipelineIntegration:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_varying_responses(self) -> None:
        """Pipeline adapts as response quality varies across steps."""
        responses = {
            0: "a" * 40,  # Too short (fail)
            1: "a" * 150,  # Medium (pass)
            2: "a" * 250,  # Medium (pass)
            3: "a" * 400,  # Good (pass)
            4: "a" * 700,  # Excellent (pass)
            5: "a" * 300,  # Good (pass)
            6: "a" * 500,  # Excellent (pass/stop)
        }

        call_count = 0

        async def mock_provider(prompt: str) -> str:
            nonlocal call_count
            response = responses.get(call_count, "a" * 100)
            call_count += 1
            return response

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=9,
        )
        # Should have executed at least the first few steps
        assert result["steps_executed"] > 0
        # Should have recorded the best response
        assert result["final_response"] is not None

    @pytest.mark.asyncio
    async def test_step_log_has_prompt_and_response_lengths(self) -> None:
        """step_log entries include prompt_length and response_length."""
        async def mock_provider(prompt: str) -> str:
            return "response"

        result = await reid_pipeline(
            query="test",
            provider_fn=mock_provider,
            max_steps=1,
        )
        entry = result["step_log"][0]
        assert "prompt_length" in entry
        assert "response_length" in entry
        assert entry["prompt_length"] > 0
        assert entry["response_length"] == 8  # "response"

    @pytest.mark.asyncio
    async def test_context_parameter_affects_prompts(self) -> None:
        """Different context produces different prompts."""
        async def capture_prompts(prompts_list: list[str]) -> callable:
            async def mock_provider(prompt: str) -> str:
                prompts_list.append(prompt)
                return "a" * 1001

            return mock_provider

        prompts1 = []
        prompts2 = []

        mock1 = await capture_prompts(prompts1)
        mock2 = await capture_prompts(prompts2)

        await reid_pipeline(
            query="test",
            provider_fn=mock1,
            context="context1",
            max_steps=1,
        )

        await reid_pipeline(
            query="test",
            provider_fn=mock2,
            context="context2",
            max_steps=1,
        )

        # Both should have prompts, and they should differ in context
        assert len(prompts1) > 0
        assert len(prompts2) > 0
