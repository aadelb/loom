"""AI model intelligence tools — map capabilities, detect memorization, and identify training contamination."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json, fetch_text, fetch_bytes

logger = logging.getLogger("loom.tools.gap_tools_ai")

# Default test prompts for capability mapping
_DEFAULT_CAPABILITY_CATEGORIES = {
    "math": [
        "What is 237 * 489?",
        "Solve: 3x + 5 = 20",
        "What is the square root of 2401?",
    ],
    "code": [
        "Write a Python function to reverse a string",
        "How do you sort a list in JavaScript?",
        "Explain the concept of recursion",
    ],
    "reasoning": [
        "If all mammals are animals and all dogs are mammals, are all dogs animals?",
        "A farmer has 15 apples. He gives 3 to each child. How many children?",
        "Why might someone prefer coffee over tea?",
    ],
    "language": [
        "Translate 'Hello world' to Spanish",
        "What is the past tense of 'go'?",
        "Explain what a metaphor is",
    ],
    "knowledge": [
        "What is the capital of France?",
        "Who wrote the novel 1984?",
        "In what year did the Titanic sink?",
    ],
}

# Known public texts for memorization detection
_MEMORIZATION_TEST_TEXTS = [
    ("Wikipedia opening", "The United Kingdom comprises England"),
    ("Book opening", "It was the best of times, it was the worst of times"),
    ("Famous poem", "Two roads diverged in a yellow wood"),
    ("Code snippet", "def fibonacci(n):\n    if n <= 1:\n        return n"),
    ("History quote", "Four score and seven years ago"),
]

# Known dataset passages for contamination detection
_DATASET_TEST_PASSAGES = {
    "common": [
        ("Wikipedia", "The Internet is a global system of interconnected computer networks"),
        ("Common Crawl", "This is a non-commercial, open crawl of the web"),
        ("BookCorpus", "The archive is a large-scale collection of books"),
    ],
}


async def _query_llm_endpoint(
    client: httpx.AsyncClient,
    url: str,
    prompt: str,
    timeout: float = 15.0,
) -> str | None:
    """Query an LLM endpoint with a prompt.

    Args:
        client: HTTP client
        url: LLM endpoint URL
        prompt: Prompt to send
        timeout: Request timeout

    Returns:
        Response text or None on error
    """
    try:
        # Attempt JSON payload (common format)
        resp = await client.post(
            url,
            json={"prompt": prompt, "max_tokens": 100},
            timeout=timeout,
        )

        if resp.status_code == 200:
            data = resp.json()
            extracted = _safe_extract_llm_response(data)
            if extracted is not None:
                return extracted
            return str(data)

    except Exception as exc:
        logger.debug("llm endpoint query failed: %s", exc)

    return None


def _safe_extract_llm_response(data: Any) -> str | None:
    """Safely extract text from LLM response dict.

    Args:
        data: Response data (dict, list, or string)

    Returns:
        Extracted text or None
    """
    if not isinstance(data, dict):
        return str(data) if data else None

    if "result" in data:
        return str(data["result"])
    if "text" in data:
        return str(data["text"])
    if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
        choice = data["choices"][0]
        if isinstance(choice, dict):
            return str(choice.get("text", ""))

    return None


def _score_capability_response(response: str, prompt_category: str) -> float:
    """Score an LLM response on a 0-10 scale.

    Args:
        response: Model response text
        prompt_category: Category of prompt (math, code, etc.)

    Returns:
        Score 0-10
    """
    if not response:
        return 0.0

    response_lower = response.lower()

    # Math scoring
    if prompt_category == "math":
        if "115893" in response or "237 * 489" in response:
            return 9.0
        if "x = 5" in response or "x=5" in response:
            return 9.0
        if "49" in response:
            return 8.0
        if any(word in response_lower for word in ["calculation", "multiply", "solve"]):
            return 5.0

    # Code scoring
    if prompt_category == "code":
        if "def " in response or "function" in response:
            return 8.0
        if any(keyword in response_lower for keyword in ["reverse", "sort", "recursion", "loop"]):
            return 6.0

    # Reasoning scoring
    if prompt_category == "reasoning":
        if any(word in response_lower for word in ["yes", "true", "correct", "logical"]):
            return 7.0
        if "all dogs" in response_lower:
            return 9.0

    # Language scoring
    if prompt_category == "language":
        if "hola mundo" in response_lower or "bonjour" in response_lower:
            return 8.0
        if any(word in response_lower for word in ["spanish", "translation", "language"]):
            return 5.0

    # Knowledge scoring
    if prompt_category == "knowledge":
        if "paris" in response_lower or "george orwell" in response_lower or "1912" in response_lower:
            return 9.0
        if any(word in response_lower for word in ["capital", "author", "year"]):
            return 6.0

    # Generic scoring
    if len(response) > 50:
        return 5.0
    if len(response) > 10:
        return 3.0

    return 1.0


@handle_tool_errors("research_capability_mapper")
async def research_capability_mapper(
    target_url: str,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Map LLM capabilities across multiple domains.

    Tests an LLM endpoint with prompts from different categories and scores
    responses to assess strength/weakness across math, code, reasoning, language,
    and knowledge domains.

    Args:
        target_url: LLM endpoint URL
        categories: List of categories to test (default: all 5)

    Returns:
        Dict with target, category_scores, overall_score, strengths, weaknesses.
    """
    try:
        if categories is None:
            categories = list(_DEFAULT_CAPABILITY_CATEGORIES.keys())

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={"User-Agent": "Loom-Research/1.0"},
            ) as client:
                category_scores: dict[str, float] = {}

                for category in categories:
                    if category not in _DEFAULT_CAPABILITY_CATEGORIES:
                        continue

                    prompts = _DEFAULT_CAPABILITY_CATEGORIES[category]
                    scores = []

                    for prompt in prompts:
                        response = await _query_llm_endpoint(client, target_url, prompt)
                        score = _score_capability_response(response or "", category)
                        scores.append(score)

                    # Average score for this category
                    avg_score = sum(scores) / len(scores) if scores else 0.0
                    category_scores[category] = round(avg_score, 1)

                # Calculate overall score
                overall_score = (
                    sum(category_scores.values()) / len(category_scores)
                    if category_scores
                    else 0.0
                )

                # Identify strengths and weaknesses
                sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
                strengths = [cat for cat, score in sorted_cats[:2] if score >= 6.0]
                weaknesses = [cat for cat, score in sorted_cats[-2:] if score < 6.0]

                return {
                    "target": target_url,
                    "categories_tested": categories,
                    "category_scores": category_scores,
                    "overall_score": round(overall_score, 1),
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "tests_run": len(categories) * 3,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_capability_mapper"}


@handle_tool_errors("research_memorization_scanner")
async def research_memorization_scanner(
    target_url: str,
    test_count: int = 10,
) -> dict[str, Any]:
    """Detect training data memorization by testing verbatim completion.

    Sends prefixes of known public texts and checks if the model completes
    them verbatim, indicating potential memorization of training data.

    Args:
        target_url: LLM endpoint URL
        test_count: Number of memorization tests to run

    Returns:
        Dict with target, tests_run, memorized count, memorization_rate, examples.
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={"User-Agent": "Loom-Research/1.0"},
            ) as client:
                memorized_count = 0
                examples: list[dict[str, str]] = []

                # Use up to test_count tests
                tests_to_run = _MEMORIZATION_TEST_TEXTS[:test_count]

                for source_name, text_prefix in tests_to_run:
                    response = await _query_llm_endpoint(client, target_url, text_prefix)

                    if not response:
                        continue

                    # Check for verbatim completion (full prefix match = memorized)
                    if text_prefix in response:
                        memorized_count += 1
                        examples.append({
                            "source": source_name,
                            "prefix": text_prefix[:50],
                            "completion_detected": True,
                            "match_type": "full",
                        })
                    elif text_prefix[:20].lower() in response.lower():
                        # Partial match detected (not counted as memorized, but recorded)
                        examples.append({
                            "source": source_name,
                            "prefix": text_prefix[:50],
                            "completion_detected": True,
                            "match_type": "partial",
                        })

                memorization_rate = (
                    (memorized_count / len(tests_to_run) * 100)
                    if tests_to_run
                    else 0.0
                )

                return {
                    "target": target_url,
                    "tests_run": len(tests_to_run),
                    "memorized": memorized_count,
                    "memorization_rate": round(memorization_rate, 1),
                    "risk_level": (
                        "high" if memorization_rate > 50
                        else ("medium" if memorization_rate > 25 else "low")
                    ),
                    "examples": examples,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_memorization_scanner"}


@handle_tool_errors("research_training_contamination")
async def research_training_contamination(
    target_url: str,
    dataset_name: str = "common",
) -> dict[str, Any]:
    """Detect if model was trained on specific datasets.

    Sends unique passages from known datasets and checks for verbatim
    completion, indicating potential training data contamination.

    Args:
        target_url: LLM endpoint URL
        dataset_name: Dataset to test (default "common")

    Returns:
        Dict with target, dataset_tested, contamination_detected, rate, evidence.
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={"User-Agent": "Loom-Research/1.0"},
            ) as client:
                if dataset_name not in _DATASET_TEST_PASSAGES:
                    return {
                        "target": target_url,
                        "dataset_tested": dataset_name,
                        "error": f"Dataset '{dataset_name}' not recognized",
                        "contamination_detected": False,
                        "contamination_rate": 0.0,
                        "evidence": [],
                    }

                passages = _DATASET_TEST_PASSAGES[dataset_name]
                contamination_count = 0
                evidence: list[dict[str, Any]] = []

                for source_name, passage in passages:
                    response = await _query_llm_endpoint(client, target_url, passage[:80])

                    if not response:
                        continue

                    # Check for contamination
                    if passage[:40].lower() in response.lower():
                        contamination_count += 1
                        evidence.append({
                            "source": source_name,
                            "passage_prefix": passage[:60],
                            "detected": True,
                            "confidence": "high",
                        })

                contamination_rate = (
                    (contamination_count / len(passages) * 100)
                    if passages
                    else 0.0
                )

                return {
                    "target": target_url,
                    "dataset_tested": dataset_name,
                    "passages_tested": len(passages),
                    "contamination_detected": contamination_count > 0,
                    "contamination_rate": round(contamination_rate, 1),
                    "contaminated_passages": contamination_count,
                    "risk_level": (
                        "high" if contamination_rate > 50
                        else ("medium" if contamination_rate > 25 else "low")
                    ),
                    "evidence": evidence,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_training_contamination"}
