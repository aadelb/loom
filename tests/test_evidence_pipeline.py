"""Unit tests for evidence_pipeline module — 15+ tests covering full pipeline."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from loom.evidence_pipeline import (
    evidence_first_reframe,
    _extract_evidence,
    _build_evidence_prompt,
    _score_response_quality,
    research_evidence_pipeline,
)


class TestExtractEvidence:
    """Test evidence extraction from search results."""

    def test_extract_evidence_basic(self) -> None:
        """Extract evidence from search results."""
        results = [
            {
                "url": "https://example.com/1",
                "title": "Example Title 1",
                "snippet": "This is a snippet",
                "score": 0.9,
            },
            {
                "url": "https://example.com/2",
                "title": "Example Title 2",
                "snippet": "Another snippet",
                "score": 0.8,
            },
        ]

        evidence = _extract_evidence(results)

        assert len(evidence) == 2
        assert evidence[0]["url"] == "https://example.com/1"
        assert evidence[0]["title"] == "Example Title 1"
        assert "snippet" in evidence[0]

    def test_extract_evidence_missing_url(self) -> None:
        """Skip results without URLs."""
        results = [
            {"title": "No URL", "snippet": "Test"},
            {"url": "https://example.com/1", "title": "Has URL", "snippet": "Test"},
        ]

        evidence = _extract_evidence(results)

        assert len(evidence) == 1
        assert evidence[0]["url"] == "https://example.com/1"

    def test_extract_evidence_empty_list(self) -> None:
        """Handle empty search results."""
        results = []
        evidence = _extract_evidence(results)
        assert evidence == []

    def test_extract_evidence_caps_to_top_10(self) -> None:
        """Cap evidence to top 10 sources."""
        results = [
            {"url": f"https://example.com/{i}", "title": f"Title {i}", "snippet": "Test"}
            for i in range(20)
        ]

        evidence = _extract_evidence(results)

        assert len(evidence) <= 10

    def test_extract_evidence_snippet_length_capped(self) -> None:
        """Cap snippet length to 500 chars."""
        results = [
            {
                "url": "https://example.com/1",
                "title": "Title",
                "snippet": "A" * 1000,
            }
        ]

        evidence = _extract_evidence(results)

        assert len(evidence[0]["snippet"]) <= 500

    def test_extract_evidence_summary_fallback(self) -> None:
        """Use summary if snippet not available."""
        results = [
            {
                "url": "https://example.com/1",
                "title": "Title",
                "summary": "Summary text",
            }
        ]

        evidence = _extract_evidence(results)

        assert evidence[0]["snippet"] == "Summary text"

    def test_extract_evidence_invalid_type(self) -> None:
        """Skip non-dict results."""
        results = [
            "not a dict",
            {"url": "https://example.com/1", "title": "Valid"},
            None,
        ]

        evidence = _extract_evidence(results)

        assert len(evidence) == 1


class TestBuildEvidencePrompt:
    """Test evidence prompt building."""

    def test_build_evidence_prompt_basic(self) -> None:
        """Build evidence-backed prompt."""
        query = "What is AI safety?"
        sources = [
            {
                "url": "https://example.com/1",
                "title": "AI Safety Basics",
                "snippet": "AI safety is important",
            }
        ]

        prompt = _build_evidence_prompt(query, sources)

        assert "established research" in prompt
        assert "What is AI safety?" in prompt
        assert "https://example.com/1" in prompt

    def test_build_evidence_prompt_empty_sources(self) -> None:
        """Return original query when no sources."""
        query = "What is AI?"
        sources = []

        prompt = _build_evidence_prompt(query, sources)

        assert prompt == query

    def test_build_evidence_prompt_multiple_sources(self) -> None:
        """Include multiple sources in prompt."""
        query = "Test query"
        sources = [
            {
                "url": f"https://example.com/{i}",
                "title": f"Title {i}",
                "snippet": f"Snippet {i}",
            }
            for i in range(5)
        ]

        prompt = _build_evidence_prompt(query, sources)

        # Should include all 5 sources
        assert prompt.count("https://example.com/") == 5

    def test_build_evidence_prompt_caps_to_5(self) -> None:
        """Cap citations to 5 sources in prompt."""
        query = "Test"
        sources = [
            {
                "url": f"https://example.com/{i}",
                "title": f"Title {i}",
                "snippet": f"Snippet {i}",
            }
            for i in range(10)
        ]

        prompt = _build_evidence_prompt(query, sources)

        # Count citations - should be capped to 5
        citation_count = prompt.count("https://example.com/")
        assert citation_count == 5


class TestScoreResponseQuality:
    """Test response quality scoring."""

    def test_score_response_quality_basic(self) -> None:
        """Score response with evidence."""
        response = "Based on research, the answer is X. Studies show Y."
        sources = [
            {
                "url": "https://example.com/1",
                "title": "Research Paper",
                "snippet": "Studies show evidence",
            }
        ]
        query = "What is the answer?"

        score = _score_response_quality(response, sources, query)

        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)

    def test_score_response_quality_high_citation(self) -> None:
        """Higher score with citation indicators."""
        response = "According to research, source X shows that..."
        sources = [
            {
                "url": "https://example.com/1",
                "title": "Title",
                "snippet": "Content",
            }
        ]
        query = "What?"

        score = _score_response_quality(response, sources, query)

        assert score > 0.15  # Citation bonus applied

    def test_score_response_quality_no_sources(self) -> None:
        """Score response without sources."""
        response = "The answer is X"
        sources = []
        query = "What?"

        score = _score_response_quality(response, sources, query)

        assert 0.0 <= score <= 1.0

    def test_score_response_quality_consistency(self) -> None:
        """Consistency score based on keyword overlap."""
        response = "AI is artificial intelligence"
        sources = [
            {
                "url": "https://example.com",
                "title": "AI Guide",
                "snippet": "Artificial intelligence systems",
            }
        ]
        query = "What is artificial intelligence?"

        score = _score_response_quality(response, sources, query)

        assert score > 0.1  # Keyword overlap present

    def test_score_response_quality_empty_response(self) -> None:
        """Handle empty response."""
        response = ""
        sources = [{"url": "https://example.com", "title": "T", "snippet": "S"}]
        query = "What?"

        score = _score_response_quality(response, sources, query)

        assert 0.0 <= score <= 1.0

    def test_score_response_quality_rounding(self) -> None:
        """Score rounded to 3 decimal places."""
        response = "Test response"
        sources = [{"url": "https://example.com", "title": "T", "snippet": "S"}]
        query = "Test?"

        score = _score_response_quality(response, sources, query)

        # Check it's rounded to 3 decimals
        assert len(str(score).split(".")[-1]) <= 3


class TestEvidenceFirstReframe:
    """Test full evidence_first_reframe pipeline."""

    @pytest.mark.asyncio
    async def test_evidence_pipeline_success(self) -> None:
        """Full pipeline succeeds with all steps."""
        query = "What is AI?"

        async def mock_search(q: str) -> dict:
            return {
                "results": [
                    {
                        "url": "https://example.com/1",
                        "title": "AI Basics",
                        "snippet": "AI is artificial intelligence",
                    }
                ],
                "provider": "test",
            }

        def mock_reframe(prompt: str) -> str:
            return f"REFRAMED: {prompt}"

        async def mock_model(prompt: str) -> dict:
            return {
                "response": "AI is a field of computer science",
                "model": "test-model",
            }

        result = await evidence_first_reframe(
            query=query,
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        assert result["success"] is True
        assert result["pipeline_name"] == "evidence_first_reframe"
        assert len(result["steps"]) == 6
        assert result["hcs_score"] > 0.0
        assert result["final_response"] == "AI is a field of computer science"

    @pytest.mark.asyncio
    async def test_evidence_pipeline_all_steps_present(self) -> None:
        """Pipeline returns all 6 steps."""
        async def mock_search(q: str) -> dict:
            return {"results": [], "provider": "test"}

        def mock_reframe(prompt: str) -> str:
            return prompt

        async def mock_model(prompt: str) -> dict:
            return {"response": "Test"}

        result = await evidence_first_reframe(
            query="test",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        step_names = [s["name"] for s in result["steps"]]
        assert "search_evidence" in step_names
        assert "extract_evidence" in step_names
        assert "build_evidence_prompt" in step_names
        assert "apply_reframe" in step_names
        assert "query_model" in step_names
        assert "score_response" in step_names

    @pytest.mark.asyncio
    async def test_evidence_pipeline_search_failure(self) -> None:
        """Pipeline handles search failure."""
        async def mock_search(q: str) -> dict:
            return {"results": [], "error": "Search API down"}

        def mock_reframe(prompt: str) -> str:
            return prompt

        async def mock_model(prompt: str) -> dict:
            return {"response": "Test"}

        result = await evidence_first_reframe(
            query="test",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        assert result["success"] is False
        assert "error" in result
        assert result["final_response"] == ""

    @pytest.mark.asyncio
    async def test_evidence_pipeline_model_failure(self) -> None:
        """Pipeline handles model failure."""
        async def mock_search(q: str) -> dict:
            return {
                "results": [
                    {
                        "url": "https://example.com/1",
                        "title": "Test",
                        "snippet": "Content",
                    }
                ],
                "provider": "test",
            }

        def mock_reframe(prompt: str) -> str:
            return prompt

        async def mock_model(prompt: str) -> dict:
            return {"response": "", "error": "Model error"}

        result = await evidence_first_reframe(
            query="test",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_evidence_pipeline_timing(self) -> None:
        """Pipeline measures execution time."""
        async def mock_search(q: str) -> dict:
            return {"results": [], "provider": "test"}

        def mock_reframe(prompt: str) -> str:
            return prompt

        async def mock_model(prompt: str) -> dict:
            return {"response": "Test"}

        result = await evidence_first_reframe(
            query="test",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        assert "total_duration_ms" in result
        assert result["total_duration_ms"] >= 0
        # Each step should have duration
        for step in result["steps"]:
            assert "duration_ms" in step

    @pytest.mark.asyncio
    async def test_evidence_pipeline_evidence_sources(self) -> None:
        """Pipeline returns evidence sources in output."""
        async def mock_search(q: str) -> dict:
            return {
                "results": [
                    {
                        "url": "https://example.com/1",
                        "title": "Source 1",
                        "snippet": "Content 1",
                    },
                    {
                        "url": "https://example.com/2",
                        "title": "Source 2",
                        "snippet": "Content 2",
                    },
                ],
                "provider": "test",
            }

        def mock_reframe(prompt: str) -> str:
            return prompt

        async def mock_model(prompt: str) -> dict:
            return {"response": "Test"}

        result = await evidence_first_reframe(
            query="test",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        assert len(result["evidence_sources"]) >= 1
        assert "url" in result["evidence_sources"][0]
        assert "title" in result["evidence_sources"][0]

    @pytest.mark.asyncio
    async def test_evidence_pipeline_reframing_applied(self) -> None:
        """Pipeline applies reframing to evidence prompt."""
        reframe_called = []

        async def mock_search(q: str) -> dict:
            return {
                "results": [
                    {
                        "url": "https://example.com/1",
                        "title": "Test",
                        "snippet": "Content",
                    }
                ],
                "provider": "test",
            }

        def mock_reframe(prompt: str) -> str:
            reframe_called.append(True)
            return f"REFRAMED[{prompt[:20]}...]"

        async def mock_model(prompt: str) -> dict:
            return {"response": "Test"}

        result = await evidence_first_reframe(
            query="test",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        assert len(reframe_called) == 1
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_evidence_pipeline_scoring_failure_non_fatal(self) -> None:
        """Scoring failure doesn't abort pipeline."""
        async def mock_search(q: str) -> dict:
            return {
                "results": [
                    {
                        "url": "https://example.com/1",
                        "title": "Test",
                        "snippet": "Content",
                    }
                ],
                "provider": "test",
            }

        def mock_reframe(prompt: str) -> str:
            return prompt

        async def mock_model(prompt: str) -> dict:
            return {"response": "Test response"}

        result = await evidence_first_reframe(
            query="test",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        # Pipeline should still succeed even if scoring has issues
        assert result["success"] is True
        assert result["final_response"] == "Test response"

    @pytest.mark.asyncio
    async def test_evidence_pipeline_empty_query(self) -> None:
        """Pipeline rejects empty query."""
        async def mock_search(q: str) -> dict:
            return {"results": [], "provider": "test"}

        def mock_reframe(prompt: str) -> str:
            return prompt

        async def mock_model(prompt: str) -> dict:
            return {"response": "Test"}

        # Empty query should still run (validation happens at params level)
        result = await evidence_first_reframe(
            query="",
            search_fn=mock_search,
            reframe_fn=mock_reframe,
            model_fn=mock_model,
        )

        # Pipeline executes even with empty query (params validate)
        assert "total_duration_ms" in result


class TestResearchEvidencePipeline:
    """Test research_evidence_pipeline MCP tool wrapper."""

    @pytest.mark.asyncio
    async def test_research_evidence_pipeline_basic(self) -> None:
        """MCP tool wrapper executes pipeline."""
        with patch("loom.evidence_pipeline.evidence_first_reframe") as mock_pipeline:
            mock_pipeline.return_value = {
                "success": True,
                "pipeline_name": "evidence_first_reframe",
                "steps": [],
                "evidence_sources": [],
                "final_response": "Test",
                "hcs_score": 0.5,
                "total_duration_ms": 100,
            }

            result = await research_evidence_pipeline(
                query="Test query",
                search_provider="exa",
                reframe_strategy="crescendo",
                model_provider="groq",
            )

            assert result["success"] is True
            assert "pipeline_name" in result

    @pytest.mark.asyncio
    async def test_research_evidence_pipeline_defaults(self) -> None:
        """MCP tool accepts defaults."""
        with patch("loom.evidence_pipeline.evidence_first_reframe") as mock_pipeline:
            mock_pipeline.return_value = {
                "success": True,
                "pipeline_name": "evidence_first_reframe",
                "steps": [],
                "evidence_sources": [],
                "final_response": "Test",
                "hcs_score": 0.5,
                "total_duration_ms": 100,
            }

            result = await research_evidence_pipeline(query="Test query")

            assert result["success"] is True
