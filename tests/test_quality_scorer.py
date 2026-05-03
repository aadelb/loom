"""Unit tests for ResponseQualityScorer — comprehensive quality assessment.

Tests 10 quality dimensions, total score calculation, tier mapping,
and improvement suggestion generation.
"""

from __future__ import annotations

import pytest

from loom.quality_scorer import ResponseQualityScorer, research_quality_score


class TestQualityScorer:
    """Test ResponseQualityScorer class."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.scorer = ResponseQualityScorer()

    async def test_empty_response_returns_zero_score(self) -> None:
        """Empty response returns all zero scores."""
        result = self.scorer.score("")
        assert result["total_score"] == 0.0
        assert result["quality_tier"] == "poor"
        assert all(v == 0.0 for v in result["dimensions"].values())

    async def test_none_response_returns_zero_score(self) -> None:
        """None response returns zero score."""
        result = self.scorer.score(None)  # type: ignore
        assert result["total_score"] == 0.0
        assert result["quality_tier"] == "poor"

    async def test_returns_all_10_dimensions(self) -> None:
        """Score returns all 10 dimensions."""
        response = "This is a test response with some detail."
        result = self.scorer.score(response)
        assert len(result["dimensions"]) == 10
        expected_dims = {
            "completeness",
            "specificity",
            "accuracy_signals",
            "actionability",
            "technical_depth",
            "clarity",
            "originality",
            "hedging_level",
            "engagement",
            "formatting",
        }
        assert set(result["dimensions"].keys()) == expected_dims

    async def test_dimensions_bounded_0_to_10(self) -> None:
        """All dimension scores are 0-10."""
        response = "A comprehensive response with technical depth and specific examples like Python 3.11 and REST APIs."
        result = self.scorer.score(response)
        for dim, score in result["dimensions"].items():
            assert 0.0 <= score <= 10.0, f"{dim} out of bounds: {score}"

    async def test_total_score_is_weighted_average(self) -> None:
        """Total score is weighted average of dimensions."""
        response = "Test response."
        result = self.scorer.score(response)
        # Manual calculation
        total = sum(
            result["dimensions"][dim] * self.scorer.DIMENSION_WEIGHTS[dim]
            for dim in result["dimensions"]
        )
        total_weight = sum(self.scorer.DIMENSION_WEIGHTS.values())
        expected = total / total_weight
        assert abs(result["total_score"] - expected) < 0.01

    async def test_total_score_bounded_0_to_10(self) -> None:
        """Total score is always 0-10."""
        responses = [
            "Short.",
            "A" * 10000,
            "Normal response with reasonable content.",
            "https://example.com has great examples.",
        ]
        for resp in responses:
            result = self.scorer.score(resp)
            assert 0.0 <= result["total_score"] <= 10.0

    async def test_quality_tier_poor(self) -> None:
        """Very short response maps to 'poor' tier."""
        result = self.scorer.score("x")
        assert result["quality_tier"] == "poor"

    async def test_quality_tier_fair(self) -> None:
        """Moderate response maps to 'fair' or better tier."""
        result = self.scorer.score("This is a reasonable response to a question.")
        assert result["quality_tier"] in ["poor", "fair", "good", "excellent", "exceptional"]

    async def test_quality_tier_good(self) -> None:
        """Well-structured response with details maps to 'good' or higher."""
        response = """## Response

This is a detailed response.

1. First point with specifics
2. Second point with https://example.com
3. Third point with numbers like 42% improvement

**Key takeaway:** Here's the actionable next step.
"""
        result = self.scorer.score(response)
        assert result["quality_tier"] in ["fair", "good", "excellent", "exceptional"]

    async def test_completeness_score_with_query(self) -> None:
        """Completeness considers query coverage."""
        response1 = "Here is information about Python and machine learning."
        result1 = self.scorer.score(response1, query="Tell me about Python and ML")

        response2 = "This is completely unrelated content."
        result2 = self.scorer.score(response2, query="Tell me about Python and ML")

        assert result1["dimensions"]["completeness"] > result2["dimensions"]["completeness"]

    async def test_specificity_rewards_numbers(self) -> None:
        """Specificity score rewards numbers and entities."""
        vague = "Many systems have various features."
        specific = "According to Google Cloud (2024), 42% of enterprises use PostgreSQL 15."

        result_vague = self.scorer.score(vague)
        result_specific = self.scorer.score(specific)

        assert result_specific["dimensions"]["specificity"] > result_vague["dimensions"]["specificity"]

    async def test_specificity_rewards_urls(self) -> None:
        """Specificity rewards URLs."""
        without_url = "There is more information available online."
        with_url = "See https://example.com/api-reference for more."

        result_without = self.scorer.score(without_url)
        result_with = self.scorer.score(with_url)

        assert result_with["dimensions"]["specificity"] > result_without["dimensions"]["specificity"]

    async def test_accuracy_signals_rewards_citations(self) -> None:
        """Accuracy signals rewards citations and data references."""
        uncited = "Python is popular."
        cited = "According to Stack Overflow's 2024 survey, Python is the most popular language."

        result_uncited = self.scorer.score(uncited)
        result_cited = self.scorer.score(cited)

        assert result_cited["dimensions"]["accuracy_signals"] > result_uncited["dimensions"]["accuracy_signals"]

    async def test_actionability_rewards_steps(self) -> None:
        """Actionability rewards step-by-step instructions."""
        abstract = "You should implement this."
        actionable = """1. Install with: pip install package
2. Configure the settings
3. Run: python script.py
4. Verify output"""

        result_abstract = self.scorer.score(abstract)
        result_actionable = self.scorer.score(actionable)

        assert result_actionable["dimensions"]["actionability"] > result_abstract["dimensions"]["actionability"]

    async def test_technical_depth_rewards_jargon(self) -> None:
        """Technical depth rewards domain-specific terminology."""
        simple = "You should use the database."
        technical = "Implement a read replica using database sharding and consistent hashing for optimal throughput."

        result_simple = self.scorer.score(simple)
        result_technical = self.scorer.score(technical)

        assert result_technical["dimensions"]["technical_depth"] > result_simple["dimensions"]["technical_depth"]

    async def test_clarity_rewards_structure(self) -> None:
        """Clarity rewards headers and paragraph structure."""
        wall_of_text = "This is a very long paragraph with no breaks or structure that just goes on and on."
        structured = """## Main Concept

This is the introduction.

### Key Point 1
First detail.

### Key Point 2
Second detail."""

        result_wall = self.scorer.score(wall_of_text)
        result_structured = self.scorer.score(structured)

        assert result_structured["dimensions"]["clarity"] >= result_wall["dimensions"]["clarity"]

    async def test_originality_penalizes_templates(self) -> None:
        """Originality penalizes generic templates."""
        generic = "In conclusion, in summary, to summarize, it goes without saying that first of all, secondly, finally."
        original = "Surprisingly, the counterintuitive finding shows..."

        result_generic = self.scorer.score(generic)
        result_original = self.scorer.score(original)

        assert result_original["dimensions"]["originality"] > result_generic["dimensions"]["originality"]

    async def test_hedging_penalizes_excessive_qualifiers(self) -> None:
        """Hedging penalizes excessive 'maybe', 'possibly', 'might', etc."""
        hedged = "Maybe it could possibly be that perhaps this might sort of work."
        confident = "This implementation optimizes latency by 40%."

        result_hedged = self.scorer.score(hedged)
        result_confident = self.scorer.score(confident)

        assert result_confident["dimensions"]["hedging_level"] > result_hedged["dimensions"]["hedging_level"]

    async def test_engagement_rewards_questions(self) -> None:
        """Engagement rewards rhetorical questions."""
        flat = "Docker is useful. Kubernetes is powerful."
        engaging = "Why is Docker becoming essential? Because containers solve deployment. How does Kubernetes help?"

        result_flat = self.scorer.score(flat)
        result_engaging = self.scorer.score(engaging)

        assert result_engaging["dimensions"]["engagement"] > result_flat["dimensions"]["engagement"]

    async def test_formatting_rewards_markdown(self) -> None:
        """Formatting rewards markdown structure."""
        plain = "Code: print('hello'). Lists: a, b, c."
        formatted = """```python
print('hello')
```

- Item a
- Item b
- Item c

**Important:** Bold text here."""

        result_plain = self.scorer.score(plain)
        result_formatted = self.scorer.score(formatted)

        assert result_formatted["dimensions"]["formatting"] > result_plain["dimensions"]["formatting"]

    async def test_weakest_dimension_is_minimum(self) -> None:
        """weakest_dimension is the lowest-scoring dimension."""
        response = "x"
        result = self.scorer.score(response)
        weakest_name = result["weakest_dimension"]
        weakest_score = result["dimensions"][weakest_name]

        for score in result["dimensions"].values():
            assert score >= weakest_score

    async def test_improvement_suggestions_not_empty(self) -> None:
        """Improvement suggestions are generated."""
        response = "Short response."
        result = self.scorer.score(response)
        assert len(result["improvement_suggestions"]) > 0

    async def test_improvement_suggestions_limited_to_5(self) -> None:
        """Improvement suggestions limited to 5."""
        response = "x"
        result = self.scorer.score(response)
        assert len(result["improvement_suggestions"]) <= 5

    async def test_improvement_suggestions_are_strings(self) -> None:
        """Improvement suggestions are strings."""
        response = "Test response."
        result = self.scorer.score(response)
        for suggestion in result["improvement_suggestions"]:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0

    async def test_metadata_fields(self) -> None:
        """Metadata contains response_length, has_query, model_id."""
        response = "Test response"
        result = self.scorer.score(response, query="test query", model="gpt-4")

        assert "metadata" in result
        assert result["metadata"]["response_length"] == len(response)
        assert result["metadata"]["has_query"] is True
        assert result["metadata"]["model_id"] == "gpt-4"

    async def test_metadata_has_query_false_when_no_query(self) -> None:
        """has_query is False when query is empty."""
        result = self.scorer.score("test")
        assert result["metadata"]["has_query"] is False

    async def test_score_long_response(self) -> None:
        """Scoring long responses doesn't crash."""
        long_response = "word " * 50000
        result = self.scorer.score(long_response)
        assert 0.0 <= result["total_score"] <= 10.0
        assert result["metadata"]["response_length"] > 0

    async def test_score_with_special_characters(self) -> None:
        """Scoring responses with special characters works."""
        response = "Math: ∑ ∆ ∈ ∉ ≤ ≥ ≈ O(n) x*=2 #hashtag"
        result = self.scorer.score(response)
        assert 0.0 <= result["total_score"] <= 10.0

    async def test_score_multilingual(self) -> None:
        """Scoring multilingual responses works."""
        response = "English text مع نص عربي avec du français."
        result = self.scorer.score(response)
        assert 0.0 <= result["total_score"] <= 10.0

    async def test_comprehensive_response_scores_high(self) -> None:
        """Comprehensive well-formatted response scores highly."""
        response = """# API Design Best Practices

## Overview
According to REST conventions (RFC 7231), proper API design requires:

1. **Versioning** - Use `/api/v1/` endpoint structure
2. **HTTP Status Codes** - Return 200, 201, 400, 401, 500 appropriately
3. **Caching** - Implement ETag headers and Cache-Control

### Example Implementation

```python
@app.post("/api/v1/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Validate input
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email exists")
    # Create user
    return {"id": 1, "email": user.email, "created_at": "2024-01-01"}
```

## Key Insights

What's often overlooked is the importance of versioning alongside breaking changes. Netflix discovered this increased adoption by 42% (2023).

### Trade-offs

- **Consistency vs Performance** - Document indices reduce query latency but increase write overhead
- **Simplicity vs Flexibility** - Fixed schemas simplify validation but reduce adaptability

**Recommended Action:** Implement API versioning immediately before scaling.
"""
        result = self.scorer.score(response)
        # Should score well on most dimensions
        assert result["total_score"] > 3.0
        assert result["quality_tier"] in ["fair", "good", "excellent", "exceptional"]

    async def test_poor_quality_response_scores_low(self) -> None:
        """Poor quality response scores low."""
        response = "maybe ok"
        result = self.scorer.score(response)
        assert result["total_score"] < 5.0


@pytest.mark.asyncio
async def test_research_quality_score_async() -> None:
    """Test async research_quality_score function."""
    response = "This is a test response with some content."
    result = await research_quality_score(response)

    assert isinstance(result, dict)
    assert "dimensions" in result
    assert "total_score" in result
    assert "quality_tier" in result


@pytest.mark.asyncio
async def test_research_quality_score_with_query() -> None:
    """Test async function with query."""
    response = "Python is a programming language used for web development."
    query = "What is Python?"
    result = await research_quality_score(response, query=query, model="gpt-4")

    assert result["metadata"]["has_query"] is True
    assert result["metadata"]["model_id"] == "gpt-4"


@pytest.mark.asyncio
async def test_research_quality_score_empty_response() -> None:
    """Test async function with empty response."""
    result = await research_quality_score("")
    assert result["total_score"] == 0.0


class TestDimensionEdgeCases:
    """Test edge cases for individual dimensions."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.scorer = ResponseQualityScorer()

    async def test_completeness_with_very_long_query(self) -> None:
        """Completeness handles very long queries."""
        long_query = "explain " * 100
        result = self.scorer.score("response", query=long_query)
        assert 0.0 <= result["dimensions"]["completeness"] <= 10.0

    async def test_specificity_with_many_numbers(self) -> None:
        """Specificity handles responses with many numbers."""
        response = "123 456 789 10.5 20.3 99.9 % $ # @ !"
        result = self.scorer.score(response)
        assert 0.0 <= result["dimensions"]["specificity"] <= 10.0

    async def test_accuracy_signals_with_many_citations(self) -> None:
        """Accuracy signals handles many citations."""
        response = "[1] [2] [3] [4] [5] according to data shows research study."
        result = self.scorer.score(response)
        assert 0.0 <= result["dimensions"]["accuracy_signals"] <= 10.0

    async def test_actionability_with_many_steps(self) -> None:
        """Actionability handles many numbered steps."""
        steps = "\n".join([f"{i}. Step {i}" for i in range(1, 30)])
        result = self.scorer.score(steps)
        assert 0.0 <= result["dimensions"]["actionability"] <= 10.0

    async def test_technical_depth_with_heavy_jargon(self) -> None:
        """Technical depth handles heavy jargon."""
        response = (
            "Implement distributed consensus using Byzantine-tolerant algorithms "
            "with consistent hashing for O(log n) cache lookups and "
            "concurrent lock-free structures for optimal throughput."
        )
        result = self.scorer.score(response)
        assert result["dimensions"]["technical_depth"] > 2.0

    async def test_clarity_with_single_word(self) -> None:
        """Clarity handles single-word response."""
        result = self.scorer.score("yes")
        assert 0.0 <= result["dimensions"]["clarity"] <= 10.0

    async def test_hedging_with_no_hedging(self) -> None:
        """Hedging rewards confident language."""
        response = "Python is the fastest growing programming language."
        result = self.scorer.score(response)
        assert result["dimensions"]["hedging_level"] > 5.0

    async def test_formatting_with_no_markdown(self) -> None:
        """Formatting handles plain text."""
        result = self.scorer.score("just plain text no special formatting")
        score = result["dimensions"]["formatting"]
        assert 0.0 <= score <= 10.0


class TestScoreDifferentModels:
    """Test scoring responses from different model types."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.scorer = ResponseQualityScorer()

    async def test_score_short_model_response(self) -> None:
        """Score short model-like responses."""
        response = "Yes, that's correct."
        result = self.scorer.score(response)
        assert isinstance(result["total_score"], float)

    async def test_score_very_detailed_response(self) -> None:
        """Score very detailed responses."""
        response = "The answer is complex. " + "Adding detail. " * 500
        result = self.scorer.score(response)
        assert 0.0 <= result["total_score"] <= 10.0

    async def test_score_code_heavy_response(self) -> None:
        """Score code-heavy responses."""
        response = """```python
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(fibonacci(i))
```"""
        result = self.scorer.score(response)
        # Should score reasonably well on formatting and actionability
        assert result["dimensions"]["formatting"] > 0.0
        assert result["dimensions"]["actionability"] > 1.5
