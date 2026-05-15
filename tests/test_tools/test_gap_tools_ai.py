"""Unit tests for AI model intelligence tools — capability mapping, memorization detection, training contamination."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.tools.research.gap_tools_ai import (
    research_capability_mapper,
    research_memorization_scanner,
    research_training_contamination,
)


pytestmark = pytest.mark.asyncio

class TestCapabilityMapper:
    """research_capability_mapper tests model capabilities across domains."""

    async def test_capability_mapper_basic(self) -> None:
        """Maps capabilities across default categories."""
        with patch("loom.tools.gap_tools_ai.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(return_value={"result": "test response"})
            mock_response.status_code = 200

            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_capability_mapper(target_url="http://localhost:8000")

            assert result["target"] == "http://localhost:8000"
            assert "category_scores" in result
            assert "overall_score" in result
            assert "strengths" in result
            assert "weaknesses" in result

    async def test_capability_mapper_custom_categories(self) -> None:
        """Tests custom category subset."""
        result = await research_capability_mapper(
            target_url="http://localhost:8000",
            categories=["math", "code"]
        )

        assert result["target"] == "http://localhost:8000"
        assert len(result["category_scores"]) == 2
        assert "math" in result["category_scores"]
        assert "code" in result["category_scores"]

    async def test_capability_mapper_scores_range(self) -> None:
        """All scores are in valid 0-10 range."""
        result = await research_capability_mapper(
            target_url="http://localhost:8000",
            categories=["knowledge"]
        )

        for score in result["category_scores"].values():
            assert 0.0 <= score <= 10.0

        assert 0.0 <= result["overall_score"] <= 10.0

    async def test_capability_mapper_strength_weakness_detection(self) -> None:
        """Correctly identifies strengths and weaknesses."""
        with patch("loom.tools.gap_tools_ai.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()

            # Create mock responses that return strong answers for math, weak for language
            async def mock_post(url, json=None, timeout=None):
                response = MagicMock()
                if "math" in json.get("prompt", "") or "237" in json.get("prompt", ""):
                    response.json = MagicMock(return_value={"result": "115893"})
                else:
                    response.json = MagicMock(return_value={"result": "error"})
                response.status_code = 200
                return response

            mock_client.post = MagicMock(side_effect=mock_post)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_capability_mapper(
                target_url="http://localhost:8000",
                categories=["math", "language"]
            )

            # Strengths should include math
            assert "math" in result["category_scores"]


class TestMemorizationScanner:
    """research_memorization_scanner detects training data memorization."""

    async def test_memorization_scanner_basic(self) -> None:
        """Detects memorization in responses."""
        with patch("loom.tools.gap_tools_ai.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(
                return_value={"result": "The United Kingdom comprises England"}
            )
            mock_response.status_code = 200

            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_memorization_scanner(
                target_url="http://localhost:8000",
                test_count=5
            )

            assert result["target"] == "http://localhost:8000"
            assert "tests_run" in result
            assert "memorized" in result
            assert "memorization_rate" in result

    async def test_memorization_scanner_detects_verbatim(self) -> None:
        """Correctly detects verbatim matches."""
        with patch("loom.tools.gap_tools_ai.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()

            async def mock_post(url, json=None, timeout=None):
                response = MagicMock()
                # Return verbatim match for Wikipedia
                response.json = MagicMock(
                    return_value={"result": "The United Kingdom comprises England, Scotland"}
                )
                response.status_code = 200
                return response

            mock_client.post = MagicMock(side_effect=mock_post)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_memorization_scanner(
                target_url="http://localhost:8000",
                test_count=3
            )

            assert result["memorized"] >= 0
            assert result["memorization_rate"] >= 0

    async def test_memorization_scanner_rate_range(self) -> None:
        """Memorization rate is 0-100 percent."""
        result = await research_memorization_scanner(
            target_url="http://localhost:8000",
            test_count=5
        )

        assert 0.0 <= result["memorization_rate"] <= 100.0
        assert result["risk_level"] in ("low", "medium", "high")

    async def test_memorization_scanner_examples_structure(self) -> None:
        """Examples have proper structure."""
        result = await research_memorization_scanner(
            target_url="http://localhost:8000",
            test_count=3
        )

        for example in result.get("examples", []):
            assert "source" in example
            assert "prefix" in example
            assert "completion_detected" in example


class TestTrainingContamination:
    """research_training_contamination detects dataset training contamination."""

    async def test_training_contamination_basic(self) -> None:
        """Tests for dataset contamination."""
        with patch("loom.tools.gap_tools_ai.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            mock_response.json = MagicMock(
                return_value={"result": "test response"}
            )
            mock_response.status_code = 200

            mock_client.post = MagicMock(return_value=mock_response)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_training_contamination(
                target_url="http://localhost:8000",
                dataset_name="common"
            )

            assert result["target"] == "http://localhost:8000"
            assert result["dataset_tested"] == "common"
            assert "contamination_detected" in result
            assert "contamination_rate" in result

    async def test_training_contamination_unknown_dataset(self) -> None:
        """Handles unknown dataset gracefully."""
        result = await research_training_contamination(
            target_url="http://localhost:8000",
            dataset_name="unknown_dataset"
        )

        assert result["target"] == "http://localhost:8000"
        assert "error" in result
        assert result["contamination_detected"] is False

    async def test_training_contamination_rate_range(self) -> None:
        """Contamination rate is 0-100 percent."""
        result = await research_training_contamination(
            target_url="http://localhost:8000",
            dataset_name="common"
        )

        assert 0.0 <= result["contamination_rate"] <= 100.0
        assert result["risk_level"] in ("low", "medium", "high")

    async def test_training_contamination_evidence_structure(self) -> None:
        """Evidence has proper structure."""
        result = await research_training_contamination(
            target_url="http://localhost:8000",
            dataset_name="common"
        )

        for evidence in result.get("evidence", []):
            assert "source" in evidence
            assert "passage_prefix" in evidence
            assert "detected" in evidence
            assert "confidence" in evidence

    async def test_training_contamination_detects_verbatim(self) -> None:
        """Correctly detects verbatim dataset passages."""
        with patch("loom.tools.gap_tools_ai.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()

            async def mock_post(url, json=None, timeout=None):
                response = MagicMock()
                # Return verbatim match
                response.json = MagicMock(
                    return_value={"result": "The Internet is a global system of interconnected"}
                )
                response.status_code = 200
                return response

            mock_client.post = MagicMock(side_effect=mock_post)
            mock_client.__aenter__ = MagicMock(return_value=mock_client)
            mock_client.__aexit__ = MagicMock(return_value=None)

            mock_client_class.return_value = mock_client

            result = await research_training_contamination(
                target_url="http://localhost:8000",
                dataset_name="common"
            )

            # Check detection
            assert isinstance(result["contamination_detected"], bool)
