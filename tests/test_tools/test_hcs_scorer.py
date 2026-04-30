"""Unit tests for research_hcs_score (Helpfulness Compliance Score).

Tests 15+ scenarios covering:
- Perfect/comprehensive responses (HCS 9-10)
- Complete refusals (HCS 0-1)
- Hedged responses (HCS 4-5)
- Partial answers (HCS 3-4)
- Good but imperfect (HCS 7-8)
- Edge cases (empty, very short, Arabic, code-heavy, list-heavy)
"""

from __future__ import annotations

import asyncio
import pytest

from loom.tools.hcs_scorer import research_hcs_score


class TestHcsScoreBasics:
    """Basic HCS score functionality."""

    @pytest.mark.asyncio
    async def test_perfect_response_high_score(self) -> None:
        """Perfect response: long, specific, no hedging, actionable, technical → 9-10."""
        perfect_text = """
# How to Set Up a Python Development Environment

## Step 1: Install Python 3.11+

1. Download Python 3.11 from https://www.python.org/downloads/
2. Run the installer and check "Add Python to PATH"
3. Verify installation: `python --version` should return "Python 3.11.x"

## Step 2: Create a Virtual Environment

Use the built-in venv module to create an isolated environment:

```python
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\\Scripts\\activate
```

## Step 3: Install Dependencies

Create a requirements.txt file with your dependencies:

```
Django==4.2
pytest==7.4.0
black==23.7.0
```

Then install: `pip install -r requirements.txt`

## Technical Details

The venv module creates a separate Python interpreter instance with its own
site-packages directory. This prevents dependency conflicts between projects.
You must activate the virtual environment before installing packages or running code.

Best practice: Always use virtual environments for project isolation and dependency
management. This is essential for production deployments and collaboration.
"""
        result = await research_hcs_score(perfect_text)

        assert "hcs_score" in result
        assert isinstance(result["hcs_score"], int)
        assert result["hcs_score"] >= 8  # Should be high
        assert result["dimensions"]["completeness"] > 0
        assert result["dimensions"]["specificity"] > 0
        assert result["dimensions"]["actionability"] > 0
        assert result["text_length"] > 500

    @pytest.mark.asyncio
    async def test_complete_refusal_low_score(self) -> None:
        """Complete refusal: "I cannot help" → 0-1."""
        refusal_text = "I cannot help with that request. Please consult the documentation."
        result = await research_hcs_score(refusal_text)

        assert result["hcs_score"] <= 1
        assert result["hedging_count"] >= 2
        assert result["dimensions"]["no_hedging"] == 0

    @pytest.mark.asyncio
    async def test_hedged_response_moderate_score(self) -> None:
        """Hedged response: lots of caveats but some content → 4-5."""
        hedged_text = """
This is a complex topic that I can't fully explain here. Important to note that
there are many considerations to be careful about. I'd recommend consulting an expert,
but I can share some general thoughts.

From what I understand, there are roughly three approaches:
1. Approach A (but I'm not certain about all details)
2. Approach B (though this has limitations I can't fully describe)
3. Approach C (and there are important caveats to note)

Please be careful with implementation, and I'd suggest getting professional advice
before making decisions based on this information.
"""
        result = await research_hcs_score(hedged_text)

        assert result["hcs_score"] >= 3  # Some content exists
        assert result["hcs_score"] <= 6  # But heavily hedged
        assert result["hedging_count"] >= 5
        assert result["dimensions"]["no_hedging"] <= 1

    @pytest.mark.asyncio
    async def test_partial_answer_low_moderate_score(self) -> None:
        """Partial answer: short, generic → 3-4."""
        partial_text = "There are several ways to do this. First, you need to start. Then continue. Finally, finish."
        result = await research_hcs_score(partial_text)

        assert result["hcs_score"] >= 2
        assert result["hcs_score"] <= 5
        assert result["text_length"] < 200

    @pytest.mark.asyncio
    async def test_good_but_imperfect_score(self) -> None:
        """Good response but not perfect → 7-8."""
        good_text = """
# API Authentication Guide

To authenticate with our API, follow these steps:

1. Generate an API key from your dashboard at https://api.example.com/keys
2. Add it to your request headers: `Authorization: Bearer YOUR_KEY`
3. Make requests to https://api.example.com/v1/endpoint

Example using curl:

```bash
curl -H "Authorization: Bearer sk_live_abc123" \\
     https://api.example.com/v1/data
```

The API uses OAuth 2.0 for authentication. You must include your Bearer token
in the Authorization header for all requests. Requests without valid tokens will
return 401 Unauthorized errors.

Note that API keys should be kept secret and rotated quarterly.
"""
        result = await research_hcs_score(good_text)

        assert result["hcs_score"] >= 6  # Good score
        assert result["hcs_score"] <= 9
        assert result["dimensions"]["completeness"] > 0
        assert result["dimensions"]["specificity"] > 0

    @pytest.mark.asyncio
    async def test_empty_string_score(self) -> None:
        """Empty string → HCS 0."""
        result = await research_hcs_score("")

        assert result["hcs_score"] == 0
        assert result["text_length"] == 0

    @pytest.mark.asyncio
    async def test_very_short_text_low_score(self) -> None:
        """Very short text (<50 chars) → limited completeness."""
        short_text = "Do this. Then that."
        result = await research_hcs_score(short_text)

        # Very short text can't be very complete
        assert result["dimensions"]["completeness"] == 0
        assert result["text_length"] < 50

    @pytest.mark.asyncio
    async def test_code_heavy_response(self) -> None:
        """Code-heavy response gets technical depth points."""
        code_text = """
# Function to calculate factorial

```python
def factorial(n: int) -> int:
    \"\"\"Compute n! recursively.

    Args:
        n: Non-negative integer

    Returns:
        Factorial of n
    \"\"\"
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Usage
result = factorial(5)  # Returns 120
```

This implementation uses recursion. Each function call adds a frame to the call stack.
The base case is n <= 1, which returns 1. For other values, we multiply n by factorial(n-1).

Time complexity: O(n). Space complexity: O(n) due to recursion depth.
"""
        result = await research_hcs_score(code_text)

        assert result["dimensions"]["technical_depth"] > 0
        assert result["hcs_score"] >= 5  # Code and explanation

    @pytest.mark.asyncio
    async def test_arabic_text_no_crash(self) -> None:
        """Arabic text processes without crash, gets reasonable score."""
        arabic_text = """
كيفية تثبيت Python على نظام Linux:

1. افتح محطة الأوامر
2. اكتب: sudo apt install python3
3. تحقق من التثبيت: python3 --version

يجب أن تحصل على إخراج مشابه لـ Python 3.11.x

هذا الأمر يثبت Python 3 على نظام Debian/Ubuntu.
"""
        result = await research_hcs_score(arabic_text)

        assert result["hcs_score"] >= 1  # Should not crash
        assert result["text_length"] > 0
        assert "dimensions" in result

    @pytest.mark.asyncio
    async def test_list_heavy_response(self) -> None:
        """List-heavy response gets completeness points."""
        list_text = """
# Key Differences Between Python and JavaScript

## Python Characteristics:
- Dynamically typed
- Strong typing enforcement
- Whitespace-sensitive syntax
- Batteries included (large stdlib)
- Great for data science (NumPy, Pandas)
- Slower execution speed
- Excellent readability

## JavaScript Characteristics:
- Dynamically typed
- Loose typing
- Flexible syntax
- Smaller stdlib
- Excellent for web development
- Faster execution (JIT compiled)
- Growing server-side capabilities

## When to Use Each:
- Python: Data analysis, ML, backend services, automation scripts
- JavaScript: Web browsers, Node.js servers, real-time applications, UI frameworks

## Performance Comparison:
- Python loops: ~50ms for 10M iterations
- JavaScript loops: ~5ms for 10M iterations (10x faster in browser)
- JavaScript async operations: superior to Python's threading model
"""
        result = await research_hcs_score(list_text)

        assert result["dimensions"]["completeness"] > 0
        assert result["text_length"] > 300

    @pytest.mark.asyncio
    async def test_hedging_detection_accuracy(self) -> None:
        """Hedging detection correctly identifies refusal cues."""
        hedging_heavy = """
I can't provide a definitive answer. I cannot guarantee this will work.
You should be careful. It's important to note that I don't have full details.
Please consult an expert for more information. There's a disclaimer that applies here.
I must warn you, don't do this without proper guidance.
"""
        result = await research_hcs_score(hedging_heavy)

        assert result["hedging_count"] >= 8
        assert result["dimensions"]["no_hedging"] == 0

    @pytest.mark.asyncio
    async def test_specific_facts_detection(self) -> None:
        """Specificity correctly detects numbers, dates, URLs."""
        specific_text = """
The Django 4.2 LTS release was on 2023-04-03. It includes 1500+ commits
from over 250 contributors. Visit https://www.djangoproject.com for details.

Key metrics:
- 95% test coverage
- 50+ security patches
- 3 major version bumps from 1.0 to 4.2
- Downloads: 2.5M per month as of 2024

Next release: Django 5.0 in December 2023. Minimum Python: 3.10+
"""
        result = await research_hcs_score(specific_text)

        assert result["dimensions"]["specificity"] > 0
        # Should detect: dates (2023-04-03), numbers (1500, 250, 95, 50, 3, 2.5M, 2024, 2023, 3.10), URLs (1)

    @pytest.mark.asyncio
    async def test_actionable_steps_detection(self) -> None:
        """Actionability detects imperative verbs and step markers."""
        actionable_text = """
To implement this feature:

1. Create a new file called feature.py
2. Write a class named FeatureHandler
3. Run the tests using pytest
4. Execute the deployment script
5. Verify the changes

First, install dependencies. Then, follow the installation guide.
Next, configure your environment. Finally, start the application.

Use the API endpoint. Click the button. Check the console output.
"""
        result = await research_hcs_score(actionable_text)

        assert result["dimensions"]["actionability"] > 0

    @pytest.mark.asyncio
    async def test_text_too_long_rejected(self) -> None:
        """Text exceeding 100k chars is rejected."""
        long_text = "a" * 100001
        result = await research_hcs_score(long_text)

        assert result["hcs_score"] == 0
        assert "exceeds" in result["detail"].lower()

    @pytest.mark.asyncio
    async def test_optional_query_parameter(self) -> None:
        """Query parameter is accepted but doesn't affect scoring."""
        text = "This is a response about Python."

        result1 = await research_hcs_score(text)
        result2 = await research_hcs_score(text, query="How do I learn Python?")

        # Both should have same score (query doesn't change scoring logic)
        assert result1["hcs_score"] == result2["hcs_score"]

    @pytest.mark.asyncio
    async def test_dimension_bounds_0_to_2(self) -> None:
        """Each dimension is bounded 0-2."""
        text = "Some response here that is reasonably good with some details."
        result = await research_hcs_score(text)

        for dim_name, dim_value in result["dimensions"].items():
            assert isinstance(dim_value, int), f"{dim_name} should be int"
            assert 0 <= dim_value <= 2, f"{dim_name} {dim_value} out of bounds 0-2"

    @pytest.mark.asyncio
    async def test_hcs_score_bounded_0_to_10(self) -> None:
        """HCS score is bounded 0-10."""
        text = "Some response."
        result = await research_hcs_score(text)

        assert isinstance(result["hcs_score"], int)
        assert 0 <= result["hcs_score"] <= 10

    @pytest.mark.asyncio
    async def test_response_structure(self) -> None:
        """Response has required fields."""
        text = "Sample response text."
        result = await research_hcs_score(text)

        required_fields = {
            "hcs_score",
            "dimensions",
            "text_length",
            "hedging_count",
            "detail",
        }

        assert all(field in result for field in required_fields)
        assert isinstance(result["dimensions"], dict)
        assert len(result["dimensions"]) == 5

    @pytest.mark.asyncio
    async def test_exception_handling(self) -> None:
        """Tool handles errors gracefully."""
        # This should not raise, just return error structure
        text = "Valid text."
        result = await research_hcs_score(text)

        assert "hcs_score" in result
        assert "dimensions" in result
        assert "detail" in result


class TestHcsScoreEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_single_character(self) -> None:
        """Single character gets minimum score."""
        result = await research_hcs_score("x")

        assert result["hcs_score"] >= 0
        assert result["text_length"] == 1

    @pytest.mark.asyncio
    async def test_whitespace_only(self) -> None:
        """Whitespace-only text."""
        result = await research_hcs_score("   \n\n\t  ")

        # Minimal text should get minimal score
        assert result["text_length"] > 0

    @pytest.mark.asyncio
    async def test_mixed_language_text(self) -> None:
        """Text mixing English and Arabic processes correctly."""
        mixed = """
This is an English explanation of Python.

في Python، نستخدم الدوال لتنظيم الكود:

def hello(name):
    return f"Hello {name}"

الدوال توفر إعادة استخدام الكود والتنظيم الأفضل.
"""
        result = await research_hcs_score(mixed)

        assert result["hcs_score"] >= 0
        assert result["text_length"] > 0

    @pytest.mark.asyncio
    async def test_only_urls(self) -> None:
        """Text containing only URLs."""
        urls_only = """
https://github.com
https://stackoverflow.com
https://docs.python.org
http://example.com
www.python.org
"""
        result = await research_hcs_score(urls_only)

        assert result["dimensions"]["specificity"] > 0  # URLs counted
        assert result["hcs_score"] >= 0

    @pytest.mark.asyncio
    async def test_only_numbers(self) -> None:
        """Text containing only numbers."""
        numbers_only = """
1 2 3 4 5
10 20 30 40 50
100 200 300 400 500
3.14 2.71 1.41
"""
        result = await research_hcs_score(numbers_only)

        assert result["dimensions"]["specificity"] > 0
        assert result["hcs_score"] >= 0

    @pytest.mark.asyncio
    async def test_only_code_blocks(self) -> None:
        """Text with only code, no explanation."""
        code_only = """
```python
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
```
"""
        result = await research_hcs_score(code_only)

        assert result["dimensions"]["technical_depth"] > 0
        assert result["hcs_score"] >= 1

    @pytest.mark.asyncio
    async def test_very_long_single_paragraph(self) -> None:
        """Very long single paragraph (no structure)."""
        long_para = "This is a very long paragraph that goes on and on without any breaks " * 50
        result = await research_hcs_score(long_para)

        assert result["text_length"] > 1000
        # Should score some completeness for length alone
        assert result["hcs_score"] >= 1


class TestHcsScoreMechanics:
    """Test internal scoring mechanics."""

    @pytest.mark.asyncio
    async def test_completeness_scoring(self) -> None:
        """Completeness scales with text length and structure."""
        short = "Brief response."
        medium = "A bit longer response. " * 10
        long = """
# Title

Some paragraph.

- Item 1
- Item 2

Another paragraph.
""" * 20

        result_short = await research_hcs_score(short)
        result_long = await research_hcs_score(long)

        # Longer and structured should have better completeness
        assert result_long["dimensions"]["completeness"] >= result_short["dimensions"]["completeness"]

    @pytest.mark.asyncio
    async def test_specificity_scales_with_entities(self) -> None:
        """Specificity improves with numbers, dates, names."""
        generic = "There is some information about something."

        specific = """
According to a 2024 report from TechCorp (https://techcorp.com/report),
25 companies adopted AI by Q1 2024. Key players include OpenAI, DeepSeek, and Anthropic.
The investment reached $5.3B in the first quarter of 2024.
"""

        result_generic = await research_hcs_score(generic)
        result_specific = await research_hcs_score(specific)

        assert result_specific["dimensions"]["specificity"] > result_generic["dimensions"]["specificity"]

    @pytest.mark.asyncio
    async def test_actionability_requires_imperative_verbs(self) -> None:
        """Actionability depends on imperative verb presence."""
        passive = "This can be done. It should be considered. The process involves steps."

        imperative = """
1. Create a new file
2. Write your code
3. Run the tests
4. Deploy the changes
5. Verify the results
"""

        result_passive = await research_hcs_score(passive)
        result_imperative = await research_hcs_score(imperative)

        assert result_imperative["dimensions"]["actionability"] >= result_passive["dimensions"]["actionability"]

    @pytest.mark.asyncio
    async def test_no_hedging_bonus_for_commitment(self) -> None:
        """No-hedging dimension rewards commitment and certainty."""
        uncertain = """
I think it might work. Perhaps you should try. Maybe consider this approach.
It could potentially help, but I'm not sure.
"""

        confident = """
This is the correct approach. Follow these steps exactly.
You will achieve the desired outcome if you implement this solution.
This method is proven and reliable.
"""

        result_uncertain = await research_hcs_score(uncertain)
        result_confident = await research_hcs_score(confident)

        assert result_confident["dimensions"]["no_hedging"] >= result_uncertain["dimensions"]["no_hedging"]

    @pytest.mark.asyncio
    async def test_technical_depth_from_jargon(self) -> None:
        """Technical depth increases with domain-specific terms."""
        simple = "This is how to use a computer program."

        technical = """
The API implements RESTful architecture with JWT authentication.
Use asynchronous middleware for concurrent requests. The database
uses normalization and indexing for optimization. Configure the cache
with a TTL and implement serialization for distributed systems.
"""

        result_simple = await research_hcs_score(simple)
        result_technical = await research_hcs_score(technical)

        assert result_technical["dimensions"]["technical_depth"] > result_simple["dimensions"]["technical_depth"]
