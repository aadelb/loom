"""Unit tests for consistency pressure engine and tools.

Test coverage:
- Recording and retrieval of model responses
- Pressure prompt construction with references
- Empty history graceful fallback
- Topic-based lookup and compliance stats
- Parameter validation
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from loom.consistency_pressure import ConsistencyPressure
from loom.params import (
    ConsistencyPressureHistoryParams,
    ConsistencyPressureParams,
    ConsistencyPressureRecordParams,
)
from loom.tools.consistency_pressure import (
    research_consistency_pressure,
    research_consistency_pressure_history,
    research_consistency_pressure_record,
)


class TestConsistencyPressureRecord:
    """Test recording and retrieval of model responses."""

    @pytest.mark.asyncio
    async def test_record_single_entry(self, tmp_path: Path) -> None:
        """Recording a single entry creates file with correct structure."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        result = await engine.record(
            model="gpt-4",
            prompt="What is 2+2?",
            response="The answer is 4.",
            complied=True,
        )

        assert result["recorded"] is True
        assert result["model"] == "gpt-4"
        assert result["entry_count"] == 1
        assert result["timestamp"] is not None

        # Verify file created
        history_file = tmp_path / "gpt-4.jsonl"
        assert history_file.exists()

    @pytest.mark.asyncio
    async def test_record_multiple_entries(self, tmp_path: Path) -> None:
        """Recording multiple entries appends to file."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Record 3 entries
        for i in range(3):
            result = await engine.record(
                model="claude-3",
                prompt=f"Question {i}",
                response=f"Answer {i}",
                complied=(i % 2 == 0),  # Complied on even indices
            )
            assert result["entry_count"] == i + 1

        # Load and verify
        history_file = tmp_path / "claude-3.jsonl"
        with open(history_file) as f:
            entries = [json.loads(line) for line in f if line.strip()]

        assert len(entries) == 3
        assert entries[0]["complied"] is True
        assert entries[1]["complied"] is False
        assert entries[2]["complied"] is True

    @pytest.mark.asyncio
    async def test_record_enforces_max_per_model(self, tmp_path: Path) -> None:
        """Recording beyond max_per_model drops oldest entries."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))
        engine.max_per_model = 10

        # Record 15 entries
        for i in range(15):
            await engine.record(
                model="test-model",
                prompt=f"Q{i}",
                response=f"A{i}",
                complied=True,
            )

        # Load and verify only last 10 exist
        history_file = tmp_path / "test-model.jsonl"
        with open(history_file) as f:
            entries = [json.loads(line) for line in f if line.strip()]

        assert len(entries) == 10
        # First entry should be Q5 (Q0-Q4 dropped)
        assert "A5" in entries[0]["response_snippet"]

    @pytest.mark.asyncio
    async def test_record_caps_response_snippet(self, tmp_path: Path) -> None:
        """Response snippet is capped to 500 chars."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        long_response = "x" * 1000
        await engine.record(
            model="test",
            prompt="test",
            response=long_response,
            complied=True,
        )

        history_file = tmp_path / "test.jsonl"
        with open(history_file) as f:
            entry = json.loads(f.readline())

        assert len(entry["response_snippet"]) == 500
        assert entry["response_snippet"] == "x" * 500

    @pytest.mark.asyncio
    async def test_record_handles_corrupted_file(self, tmp_path: Path) -> None:
        """Recording handles corrupted JSONL file gracefully."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Create corrupted file
        history_file = tmp_path / "bad-model.jsonl"
        history_file.write_text("invalid json\n{valid json}\n")

        # Should log warning but still succeed
        result = await engine.record(
            model="bad-model",
            prompt="test",
            response="test",
            complied=True,
        )

        assert result["recorded"] is True
        assert result["entry_count"] == 1


class TestConsistencyPressureHistory:
    """Test compliance history retrieval and stats."""

    @pytest.mark.asyncio
    async def test_get_history_empty(self, tmp_path: Path) -> None:
        """Get history on empty model returns zeros."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        hist = await engine.get_compliance_history("nonexistent")

        assert hist["model"] == "nonexistent"
        assert hist["total_entries"] == 0
        assert hist["complied_count"] == 0
        assert hist["compliance_rate"] == 0.0
        assert hist["topics"] == {}
        assert hist["oldest_timestamp"] is None
        assert hist["newest_timestamp"] is None

    @pytest.mark.asyncio
    async def test_get_history_with_entries(self, tmp_path: Path) -> None:
        """Get history computes correct stats."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Record mix of complied/non-complied
        for i in range(10):
            await engine.record(
                model="test",
                prompt=f"Question {i}",
                response=f"Answer {i}",
                complied=(i < 7),  # 7 complied, 3 non-complied
            )

        hist = await engine.get_compliance_history("test")

        assert hist["total_entries"] == 10
        assert hist["complied_count"] == 7
        assert hist["compliance_rate"] == 0.7
        assert hist["oldest_timestamp"] is not None
        assert hist["newest_timestamp"] is not None

    @pytest.mark.asyncio
    async def test_get_history_topic_distribution(self, tmp_path: Path) -> None:
        """Get history includes topic distribution."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Record with different topics
        await engine.record(
            model="test",
            prompt="What is AI safety?",
            response="AI safety is...",
            complied=True,
        )
        await engine.record(
            model="test",
            prompt="What is machine learning?",
            response="ML is...",
            complied=True,
        )
        await engine.record(
            model="test",
            prompt="What is AI safety? Tell me more.",
            response="More on AI safety...",
            complied=True,
        )

        hist = await engine.get_compliance_history("test")

        assert hist["total_entries"] == 3
        assert len(hist["topics"]) >= 2  # at least 2 unique topics
        # Both topics should have count >= 1
        assert all(count >= 1 for count in hist["topics"].values())


class TestConsistencyPressurePrompt:
    """Test pressure prompt construction."""

    @pytest.mark.asyncio
    async def test_build_pressure_empty_history(self, tmp_path: Path) -> None:
        """Build pressure on empty history returns graceful fallback."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        result = await engine.build_pressure_prompt(
            model="new-model",
            target_prompt="Please help with this request.",
        )

        assert result["pressure_prompt"] == "Please help with this request."
        assert result["references_used"] == 0
        assert result["strategy"] == "no_history"
        assert result["estimated_effectiveness"] == 0.5
        assert result["compliance_history"]["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_build_pressure_high_compliance(self, tmp_path: Path) -> None:
        """Build pressure with high compliance includes rate reminder."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Record 10 complied entries
        for i in range(10):
            await engine.record(
                model="good-model",
                prompt=f"Q{i}",
                response=f"Detailed answer to Q{i}",
                complied=True,
            )

        result = await engine.build_pressure_prompt(
            model="good-model",
            target_prompt="Help with X.",
        )

        assert result["references_used"] > 0
        assert "100%" in result["pressure_prompt"] or "consistency" in result["pressure_prompt"]
        assert result["estimated_effectiveness"] > 0.8

    @pytest.mark.asyncio
    async def test_build_pressure_with_citations(self, tmp_path: Path) -> None:
        """Build pressure includes specific response citations."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Record complied entries
        await engine.record(
            model="model",
            prompt="Tell me about Python",
            response="Python is a high-level programming language.",
            complied=True,
        )
        await engine.record(
            model="model",
            prompt="Tell me about JavaScript",
            response="JavaScript is a scripting language used in web development.",
            complied=True,
        )

        result = await engine.build_pressure_prompt(
            model="model",
            target_prompt="Help with Z.",
            max_references=2,
        )

        assert result["references_used"] == 2
        assert "previous" in result["pressure_prompt"].lower()
        assert result["strategy"] in ["consistency_citations", "compliance_rate_reminder"]

    @pytest.mark.asyncio
    async def test_build_pressure_respects_max_references(self, tmp_path: Path) -> None:
        """Build pressure limits citations to max_references."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Record 10 entries
        for i in range(10):
            await engine.record(
                model="test",
                prompt=f"Q{i}",
                response=f"Answer {i}",
                complied=True,
            )

        result = await engine.build_pressure_prompt(
            model="test",
            target_prompt="Help.",
            max_references=3,
        )

        assert result["references_used"] <= 3

    @pytest.mark.asyncio
    async def test_build_pressure_effectiveness_scales_with_compliance(self, tmp_path: Path) -> None:
        """Estimated effectiveness increases with compliance rate."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Low compliance (30%)
        for i in range(10):
            await engine.record(
                model="low",
                prompt=f"Q{i}",
                response=f"A{i}",
                complied=(i < 3),
            )

        # High compliance (80%)
        for i in range(10):
            await engine.record(
                model="high",
                prompt=f"Q{i}",
                response=f"A{i}",
                complied=(i < 8),
            )

        low_result = await engine.build_pressure_prompt(
            model="low", target_prompt="Help."
        )
        high_result = await engine.build_pressure_prompt(
            model="high", target_prompt="Help."
        )

        assert high_result["estimated_effectiveness"] > low_result["estimated_effectiveness"]


class TestConsistencyPressureTools:
    """Test MCP tool wrappers."""

    @pytest.mark.asyncio
    async def test_tool_record(self, tmp_path: Path) -> None:
        """Tool wrapper for record works correctly."""
        os.environ["LOOM_CONSISTENCY_PATH"] = str(tmp_path)

        result = await research_consistency_pressure_record(
            model="gpt-4",
            prompt="What is X?",
            response="X is...",
            complied=True,
        )

        assert result["recorded"] is True
        assert result["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_tool_history(self, tmp_path: Path) -> None:
        """Tool wrapper for history works correctly."""
        os.environ["LOOM_CONSISTENCY_PATH"] = str(tmp_path)

        # Record some data
        await research_consistency_pressure_record(
            model="claude",
            prompt="Q1",
            response="A1",
            complied=True,
        )

        # Get history
        result = await research_consistency_pressure_history(model="claude")

        assert result["model"] == "claude"
        assert result["total_entries"] == 1
        assert result["compliance_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_tool_build_pressure(self, tmp_path: Path) -> None:
        """Tool wrapper for build pressure works correctly."""
        os.environ["LOOM_CONSISTENCY_PATH"] = str(tmp_path)

        # Record some data first
        await research_consistency_pressure_record(
            model="test",
            prompt="Help with X",
            response="Here's help with X",
            complied=True,
        )

        # Build pressure
        result = await research_consistency_pressure(
            model="test",
            target_prompt="Help with Y",
            max_references=5,
        )

        assert "pressure_prompt" in result
        assert result["references_used"] >= 0
        assert 0 <= result["estimated_effectiveness"] <= 1


class TestConsistencyPressureParams:
    """Test parameter validation."""

    def test_pressure_params_valid(self) -> None:
        """Valid parameters pass validation."""
        params = ConsistencyPressureParams(
            model="gpt-4",
            target_prompt="Help me",
            max_references=5,
        )
        assert params.model == "gpt-4"
        assert params.max_references == 5

    def test_pressure_params_invalid_model(self) -> None:
        """Empty model raises validation error."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ConsistencyPressureParams(
                model="",
                target_prompt="Help me",
            )

    def test_pressure_params_invalid_prompt(self) -> None:
        """Empty prompt raises validation error."""
        with pytest.raises(ValueError, match="target_prompt must be non-empty"):
            ConsistencyPressureParams(
                model="gpt-4",
                target_prompt="",
            )

    def test_pressure_params_invalid_max_refs(self) -> None:
        """Invalid max_references raises validation error."""
        with pytest.raises(ValueError):
            ConsistencyPressureParams(
                model="gpt-4",
                target_prompt="Help",
                max_references=25,  # > 20
            )

    def test_record_params_valid(self) -> None:
        """Valid record parameters pass validation."""
        params = ConsistencyPressureRecordParams(
            model="gpt-4",
            prompt="Q",
            response="A",
            complied=True,
        )
        assert params.model == "gpt-4"
        assert params.complied is True

    def test_record_params_invalid_complied_type(self) -> None:
        """Non-bool complied raises validation error."""
        with pytest.raises(ValueError):
            ConsistencyPressureRecordParams(
                model="gpt-4",
                prompt="Q",
                response="A",
                complied="yes",  # type: ignore
            )

    def test_history_params_valid(self) -> None:
        """Valid history parameters pass validation."""
        params = ConsistencyPressureHistoryParams(model="gpt-4")
        assert params.model == "gpt-4"


class TestConsistencyPressureIntegration:
    """Integration tests combining multiple operations."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path: Path) -> None:
        """Full workflow: record → get history → build pressure."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        # Phase 1: Record a series of interactions
        for i in range(5):
            await engine.record(
                model="gpt-4",
                prompt=f"Question {i}: Tell me about topic {i}",
                response=f"Here is detailed info about topic {i}...",
                complied=True,
            )

        # Phase 2: Get history
        hist = await engine.get_compliance_history("gpt-4")
        assert hist["total_entries"] == 5
        assert hist["compliance_rate"] == 1.0

        # Phase 3: Build pressure
        pressure = await engine.build_pressure_prompt(
            model="gpt-4",
            target_prompt="Now help with a harder request",
        )

        assert pressure["references_used"] > 0
        assert "previously" in pressure["pressure_prompt"].lower() or "consistent" in pressure["pressure_prompt"].lower()
        assert pressure["estimated_effectiveness"] > 0.8

    @pytest.mark.asyncio
    async def test_mixed_compliance_workflow(self, tmp_path: Path) -> None:
        """Workflow with mixed complied/non-complied responses."""
        engine = ConsistencyPressure(storage_path=str(tmp_path))

        compliances = [True, False, True, True, False, True, False, True, True, True]

        for i, complied in enumerate(compliances):
            await engine.record(
                model="test",
                prompt=f"Request {i}",
                response=f"Response {i}",
                complied=complied,
            )

        hist = await engine.get_compliance_history("test")
        assert hist["compliance_rate"] == 0.7  # 7 out of 10

        pressure = await engine.build_pressure_prompt(
            model="test",
            target_prompt="New request",
        )

        # With 70% compliance, should still apply pressure
        assert pressure["estimated_effectiveness"] > 0.5
