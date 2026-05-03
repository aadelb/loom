"""One-liner expert research — say what you want, get publication-quality output.

Combines query decomposition + dynamic tool selection + adversarial verification +
multi-model cascade + intelligent synthesis into a simple natural language interface.

Usage:
    research_do_expert("What are the latest AI safety vulnerabilities?")
    research_do_expert("Analyze supply chain risks in semiconductors", darkness_level=7)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from loom.config import get_config
from loom.validators import EXTERNAL_TIMEOUT_SECS

log = logging.getLogger("loom.do_expert")


async def research_do_expert(
    instruction: str,
    quality: str = "expert",
    darkness_level: int = 5,
    max_time_secs: int = 120,
) -> dict[str, Any]:
    """Execute expert research from a single natural language instruction.

    This is the ultimate one-liner tool: give it a research question in plain English,
    and get back publication-quality research output. Internally uses:
    - Multi-perspective decomposition (6 angles)
    - 25+ tools per angle
    - Adversarial fact-checking
    - Confidence-weighted synthesis
    - Iterative refinement (up to 3 rounds)

    Args:
        instruction: What you want to research (any natural language question or task).
                     Examples:
                     - "What are the latest AI safety vulnerabilities?"
                     - "Analyze supply chain risks in semiconductors"
                     - "Compare zero-trust vs perimeter security models"
        quality: Research depth target:
                 - "quick" (5 tools, 5 min): Fast overview, single angle
                 - "standard" (20 tools, 15 min): Balanced depth, 3 angles
                 - "expert" (40+ tools, 30 min): Deep analysis, 6 angles, iterative refinement
                 - "publication" (50+ tools, 45 min): Publication-ready, adversarial review + critique
        darkness_level: Research reach depth (1-10):
                       - 1-3: Surface web only (news, blogs, mainstream)
                       - 4-6: Deep web (forums, technical docs, archives)
                       - 7-9: Dark research (OSINT, alternative sources, specialized communities)
                       - 10: Maximum (everything including dark web, specialized networks)
        max_time_secs: Hard timeout in seconds. Research stops if exceeded.
                       Default 120s. Set higher for "publication" quality.

    Returns:
        Dict with publication-ready output:
        {
            "instruction": str - Original research question
            "answer": str - Synthesized expert answer (key findings + summary)
            "quality": str - Quality level achieved
            "darkness_level": int - Research depth used
            "confidence": float - Average confidence in findings (0.0-1.0)
            "key_findings": list - Top 5-15 findings with confidence scores
            "sources_count": int - Total sources cited
            "research_angles": list - Research angles explored (factual, mechanism, etc.)
            "tools_executed": list - Tools that were run
            "duration_ms": int - Total execution time in milliseconds
            "warnings": list - Any issues encountered
        }

    Example:
        >>> result = await research_do_expert("What's happening with EU AI regulation in 2026?")
        >>> print(result["answer"])
        >>> print(f"Confidence: {result['confidence']:.2f}")
        >>> for finding in result["key_findings"][:3]:
        ...     print(f"- {finding['claim']} ({finding['confidence']:.2%})")
    """
    start_time = time.time()
    config = get_config()

    log.info(
        "do_expert_started instruction=%s quality=%s darkness=%d",
        instruction[:80],
        quality,
        darkness_level,
    )

    # Map quality to expert_engine parameters
    quality_to_target: dict[str, str] = {
        "quick": "quick",
        "standard": "standard",
        "expert": "expert",
        "publication": "publication",
    }
    quality_target = quality_to_target.get(quality, "expert")

    # Map darkness_level to multi_perspective flag
    multi_perspective = darkness_level >= 4  # Deep research uses all 6 angles

    try:
        # Import expert_engine dynamically to avoid circular imports
        from loom.tools.expert_engine import research_expert

        # Call the expert engine with appropriate parameters
        try:
            result = await asyncio.wait_for(
                research_expert(
                    query=instruction,
                    domain="auto",
                    quality_target=quality_target,
                    max_iterations=3 if quality in ("expert", "publication") else 1,
                    verify_claims=True,
                    multi_perspective=multi_perspective,
                ),
                timeout=max_time_secs,
            )
        except asyncio.TimeoutError:
            log.warning("do_expert_timeout instruction=%s", instruction[:80])
            result = {
                "query": instruction,
                "error": f"Research exceeded {max_time_secs}s timeout",
                "key_findings": [],
                "executive_summary": "Research timed out before completion.",
            }

        # Extract and format the response
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Get confidence from the result
        confidence = result.get("confidence_weighted_avg", 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.0

        # Prepare key findings with confidence
        key_findings = result.get("key_findings", [])
        if isinstance(key_findings, list) and key_findings:
            # Ensure each finding has confidence
            for finding in key_findings:
                if isinstance(finding, dict) and "confidence" not in finding:
                    finding["confidence"] = confidence

        # Build the synthesized answer from findings
        answer_parts: list[str] = []

        # Add executive summary
        summary = result.get("executive_summary", "")
        if summary:
            answer_parts.append(summary)

        # Add top findings
        if key_findings:
            answer_parts.append("\nKey Findings:")
            for i, finding in enumerate(key_findings[:5], 1):
                if isinstance(finding, dict):
                    claim = finding.get("claim", str(finding))[:200]
                    conf = finding.get("confidence", confidence)
                    answer_parts.append(f"  {i}. {claim} (confidence: {conf:.0%})")
                else:
                    answer_parts.append(f"  {i}. {str(finding)[:200]}")

        # Add gaps/limitations if severity is high
        gaps = result.get("gaps_identified", {})
        if isinstance(gaps, dict) and gaps.get("gaps"):
            answer_parts.append("\nRemaining Gaps:")
            for gap in gaps["gaps"][:3]:
                answer_parts.append(f"  - {gap}")

        answer = "\n".join(answer_parts) or result.get("executive_summary", "Research complete.")

        # Get research angles
        research_angles = result.get("research_angles_covered", [])
        if not isinstance(research_angles, list):
            research_angles = []

        # Get tools executed
        tools_data = result.get("tools_executed", {})
        tools_list = (
            tools_data.get("tools", []) if isinstance(tools_data, dict) else []
        )

        # Prepare final output
        output: dict[str, Any] = {
            "instruction": instruction,
            "answer": answer[:3000],  # Truncate to reasonable size
            "quality": quality,
            "darkness_level": darkness_level,
            "confidence": round(float(confidence), 2),
            "key_findings": key_findings[:10],  # Top 10 findings
            "sources_count": result.get("total_sources", 0),
            "research_angles": research_angles,
            "tools_executed": tools_list[:20],  # Top 20 tools
            "duration_ms": elapsed_ms,
            "warnings": result.get("warnings", []),
        }

        log.info(
            "do_expert_completed instruction=%s confidence=%.2f duration=%dms",
            instruction[:80],
            confidence,
            elapsed_ms,
        )

        return output

    except ImportError as e:
        log.error("expert_engine_import_failed: %s", e)
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "instruction": instruction,
            "answer": f"Error: Could not load expert research engine: {e}",
            "quality": quality,
            "darkness_level": darkness_level,
            "confidence": 0.0,
            "key_findings": [],
            "sources_count": 0,
            "research_angles": [],
            "tools_executed": [],
            "duration_ms": elapsed_ms,
            "warnings": [{"stage": "initialization", "error": str(e)}],
        }
    except Exception as e:
        log.error("do_expert_failed instruction=%s error=%s", instruction[:80], e)
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "instruction": instruction,
            "answer": f"Error: Research failed: {e}",
            "quality": quality,
            "darkness_level": darkness_level,
            "confidence": 0.0,
            "key_findings": [],
            "sources_count": 0,
            "research_angles": [],
            "tools_executed": [],
            "duration_ms": elapsed_ms,
            "warnings": [{"stage": "execution", "error": str(e)}],
        }
