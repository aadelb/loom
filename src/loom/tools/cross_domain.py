"""research_cross_domain — Find analogies and collision insights between domains.

Identifies deep analogies between unrelated domains and generates "collision
insights" showing how techniques from one domain could create breakthroughs
in another. Uses LLM with cascade fallback for robust analogy generation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("loom.tools.cross_domain")


async def research_cross_domain(
    domain_a: str,
    domain_b: str,
    depth: int = 3,
) -> dict[str, Any]:
    """Find deep analogies and collision insights between two unrelated domains.

    Identifies structural parallels between domains and generates breakthrough
    insights by applying techniques from one domain to solve problems in another.

    Args:
        domain_a: first domain (e.g., "mycology", "distributed systems")
        domain_b: second domain (e.g., "distributed systems", "mycology")
        depth: number of deep analogies to find (1-5)

    Returns:
        Dict with keys:
        - domain_a: first domain name
        - domain_b: second domain name
        - analogies: list of {analogy, explanation} tuples
        - collision_insights: list of breakthrough ideas
        - breakthrough_potential: 0-10 score of novelty and applicability
        - applications: list of practical applications

    Raises:
        RuntimeError: if all LLM providers fail
    """
    # Validate inputs
    domain_a = domain_a.strip()
    domain_b = domain_b.strip()
    depth = max(1, min(depth, 5))

    if not domain_a or not domain_b:
        raise ValueError("domain_a and domain_b must be non-empty strings")

    if domain_a.lower() == domain_b.lower():
        raise ValueError("domain_a and domain_b must be different domains")

    logger.info(
        "cross_domain_search domain_a=%s domain_b=%s depth=%d",
        domain_a,
        domain_b,
        depth,
    )

    # Build prompt for LLM
    prompt = (
        f"Find {depth} deep structural analogies between '{domain_a}' and "
        f"'{domain_b}'. For each analogy:\n"
        f"1. Describe the parallel structure\n"
        f"2. Explain how a technique/principle from {domain_a} could create "
        f"a breakthrough in {domain_b}\n"
        f"3. Rate the novelty (1-10) and applicability (1-10)\n\n"
        f"Output valid JSON with: {{\n"
        f'  "analogies": [{{"analogy": str, "explanation": str, "novelty": int, '
        f'"applicability": int}}],\n'
        f'  "collision_insights": [str],\n'
        f'  "applications": [str]\n'
        f"}}"
    )

    from loom.tools.llm import _call_with_cascade

    try:
        response = await _call_with_cascade(
            messages=[{"role": "user", "content": prompt}],
            model="auto",
            max_tokens=2000,
            temperature=0.7,
        )

        # Parse response
        response_text = response.text.strip()

        # Extract JSON block if wrapped in markdown code fence
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end > start:
                response_text = response_text[start:end].strip()

        result_data = json.loads(response_text)

        # Validate and normalize response structure
        analogies = result_data.get("analogies", [])
        collision_insights = result_data.get("collision_insights", [])
        applications = result_data.get("applications", [])

        # Calculate breakthrough_potential score
        novelty_scores = [
            a.get("novelty", 5) for a in analogies if isinstance(a, dict)
        ]
        applicability_scores = [
            a.get("applicability", 5) for a in analogies if isinstance(a, dict)
        ]

        avg_novelty = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 5
        avg_applicability = (
            sum(applicability_scores) / len(applicability_scores)
            if applicability_scores
            else 5
        )

        # Combine scores: novelty (70%) + applicability (30%) scaled to 0-10
        breakthrough_potential = round(
            (avg_novelty * 0.7 + avg_applicability * 0.3), 1
        )
        breakthrough_potential = max(0, min(10, breakthrough_potential))

        return {
            "domain_a": domain_a,
            "domain_b": domain_b,
            "analogies": analogies,
            "collision_insights": collision_insights,
            "breakthrough_potential": breakthrough_potential,
            "applications": applications,
            "llm_provider": response.provider,
            "llm_model": response.model,
        }

    except json.JSONDecodeError as e:
        logger.error("json_parse_failed error=%s", str(e)[:200])
        raise RuntimeError(f"LLM response was not valid JSON: {str(e)}")
    except Exception as e:
        logger.error("cross_domain_failed error=%s", str(e)[:200])
        raise RuntimeError(f"Cross-domain collision engine failed: {str(e)}")
