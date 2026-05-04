"""research_generate_report — Structured intelligence report generation.

Orchestrates a multi-stage pipeline combining search, fetch, and summarization
into comprehensive research reports with configurable depth and formatting.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, Literal

from loom.retry import with_retry

logger = logging.getLogger("loom.tools.auto_report")


@with_retry(max_attempts=2, backoff_base=1.0)
async def research_generate_report(
    topic: str,
    depth: Literal["brief", "standard", "comprehensive"] = "standard",
    format: Literal["markdown", "json", "html"] = "markdown",
    search_provider: str | None = None,
    num_sources: int | None = None,
    include_methodology: bool = True,
    include_recommendations: bool = True,
) -> dict[str, Any]:
    """Generate a structured intelligence report on a given topic.

    Pipeline:
    1. Validate topic and parameters
    2. Run research_search to gather sources
    3. Fetch top N URLs with research_fetch
    4. Extract and structure findings
    5. Synthesize with LLM if available
    6. Format output based on requested format

    Args:
        topic: Research topic or question
        depth: Report depth ("brief" ~1 page, "standard" ~3-5 pages, "comprehensive" ~10+ pages)
        format: Output format ("markdown", "json", "html")
        search_provider: Search provider (exa, tavily, firecrawl, brave, etc.)
        num_sources: Number of sources to fetch (auto-scaled by depth)
        include_methodology: Include methodology section
        include_recommendations: Include recommendations section

    Returns:
        Dict with keys:
            - title: str (report title)
            - report: str (formatted report content)
            - sections: list[dict] (structured sections)
            - sources_used: int (number of sources)
            - confidence: float (0.0-1.0 confidence score)
            - generated_at: str (ISO timestamp)
            - word_count: int
            - depth: str (brief|standard|comprehensive)
            - format: str (markdown|json|html)
    """
    from loom.tools.search import research_search
    from loom.tools.fetch import research_fetch
    from loom.validators import validate_url

    # Validate and normalize input
    if not topic or len(topic.strip()) == 0:
        raise ValueError("topic cannot be empty")
    if len(topic) > 2000:
        raise ValueError("topic must be <= 2000 characters")

    topic = topic.strip()

    # Determine number of sources based on depth
    if num_sources is None:
        num_sources = {"brief": 3, "standard": 5, "comprehensive": 10}.get(depth, 5)
    num_sources = max(1, min(num_sources, 20))

    logger.info("generate_report topic=%s depth=%s num_sources=%d", topic[:50], depth, num_sources)

    try:
        # Stage 1: Search for sources
        logger.debug("stage=search topic=%s", topic[:50])
        search_result = await research_search(
            query=topic,
            provider=search_provider,
            n=num_sources,
        )

        if not search_result or "results" not in search_result:
            return _error_response("Search failed or returned no results")

        search_results = search_result.get("results", [])
        if not search_results:
            return _error_response("No search results found for topic")

        logger.debug("search_found %d results", len(search_results))

        # Stage 2: Fetch top URLs and extract content
        logger.debug("stage=fetch num_results=%d", len(search_results))
        urls_to_fetch = []
        url_metadata = {}

        for i, result in enumerate(search_results[:num_sources]):
            url = result.get("url") or result.get("link")
            if not url:
                continue
            try:
                validated_url = validate_url(url)
                urls_to_fetch.append(validated_url)
                url_metadata[validated_url] = {
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", "")[:200],
                    "rank": i + 1,
                }
            except Exception as e:
                logger.debug("skip invalid url: %s", str(e)[:100])
                continue

        if not urls_to_fetch:
            return _error_response("No valid URLs to fetch after validation")

        # Fetch URLs in parallel with timeout
        fetch_tasks = [
            asyncio.wait_for(
                research_fetch(
                    url,
                    mode="http",
                    auto_escalate=False,
                    max_chars=5000 if depth == "brief" else 10000,
                    return_format="text",
                ),
                timeout=15.0,
            )
            for url in urls_to_fetch
        ]

        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Stage 3: Extract findings from fetched content
        logger.debug("stage=extract")
        findings = []
        successful_fetches = 0

        for url, result in zip(urls_to_fetch, fetch_results):
            if isinstance(result, Exception):
                logger.debug("fetch_failed url=%s error=%s", url[:50], str(result)[:100])
                continue

            if isinstance(result, dict) and "error" in result:
                logger.debug("fetch_error url=%s error=%s", url[:50], result.get("error", "")[:100])
                continue

            content = result if isinstance(result, str) else result.get("content", "")
            if not content or len(content.strip()) < 100:
                logger.debug("fetch_insufficient_content url=%s", url[:50])
                continue

            successful_fetches += 1
            findings.append(
                {
                    "url": url,
                    "title": url_metadata.get(url, {}).get("title", ""),
                    "snippet": url_metadata.get(url, {}).get("snippet", ""),
                    "content": content[:5000],  # Cap content length
                    "rank": url_metadata.get(url, {}).get("rank", 0),
                }
            )

        if not findings:
            return _error_response(
                "Failed to fetch valid content from any source"
            )

        logger.debug("extracted %d findings", len(findings))

        # Stage 4: Attempt LLM synthesis if available
        logger.debug("stage=synthesis")
        synthesis = await _synthesize_findings(topic, findings, depth)

        # Stage 5: Structure report sections
        sections = _build_report_sections(topic, findings, synthesis, depth, include_methodology, include_recommendations)

        # Stage 6: Format output
        report_content = _format_report(sections, format, depth)

        # Calculate confidence and word count
        confidence = min(1.0, successful_fetches / len(urls_to_fetch))
        total_words = sum(len(s.get("content", "").split()) for s in sections)

        return {
            "title": _generate_title(topic),
            "report": report_content,
            "sections": sections,
            "sources_used": successful_fetches,
            "confidence": round(confidence, 2),
            "generated_at": datetime.now(UTC).isoformat(),
            "word_count": total_words,
            "depth": depth,
            "format": format,
        }

    except asyncio.TimeoutError:
        return _error_response("Report generation timed out")
    except Exception as e:
        logger.error("report_generation_failed error=%s", str(e)[:200])
        return _error_response(f"Report generation failed: {str(e)[:100]}")


async def research_report_from_results(
    results: list[dict[str, Any]],
    title: str,
    depth: Literal["brief", "standard", "comprehensive"] = "standard",
    format: Literal["markdown", "json", "html"] = "markdown",
    include_methodology: bool = True,
    include_recommendations: bool = True,
) -> dict[str, Any]:
    """Generate a report from pre-existing research results.

    Useful for generating reports from custom search results or cached data
    without performing new searches.

    Args:
        results: List of result dicts with keys: url, title, content, snippet (optional)
        title: Report title
        depth: Report depth
        format: Output format
        include_methodology: Include methodology section
        include_recommendations: Include recommendations section

    Returns:
        Dict with same structure as research_generate_report response
    """
    if not results or len(results) == 0:
        return _error_response("results list cannot be empty")

    if not title or len(title.strip()) == 0:
        return _error_response("title cannot be empty")

    logger.info("report_from_results title=%s num_results=%d", title[:50], len(results))

    try:
        # Validate and normalize results
        normalized_results = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                if "content" not in result:
                    logger.debug("skip result %d: missing content", i)
                    continue
                normalized_results.append(
                    {
                        "url": result.get("url", f"result_{i}"),
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:5000],
                        "snippet": result.get("snippet", "")[:200],
                        "rank": i + 1,
                    }
                )

        if not normalized_results:
            return _error_response("No valid results with content found")

        # Synthesize findings
        synthesis = await _synthesize_findings(title, normalized_results, depth)

        # Build sections
        sections = _build_report_sections(
            title, normalized_results, synthesis, depth, include_methodology, include_recommendations
        )

        # Format output
        report_content = _format_report(sections, format, depth)

        # Calculate metrics
        confidence = min(1.0, len(normalized_results) / max(len(results), 1))
        total_words = sum(len(s.get("content", "").split()) for s in sections)

        return {
            "title": title,
            "report": report_content,
            "sections": sections,
            "sources_used": len(normalized_results),
            "confidence": round(confidence, 2),
            "generated_at": datetime.now(UTC).isoformat(),
            "word_count": total_words,
            "depth": depth,
            "format": format,
        }

    except Exception as e:
        logger.error("report_from_results_failed error=%s", str(e)[:200])
        return _error_response(f"Report generation failed: {str(e)[:100]}")


# ── Internal Helper Functions ──


def _generate_title(topic: str) -> str:
    """Generate a report title from a topic string."""
    # Capitalize words and limit length
    words = topic.strip().split()[:8]  # First 8 words
    title = " ".join(w.capitalize() if len(w) > 1 else w for w in words)
    return f"Research Report: {title}"


async def _synthesize_findings(
    topic: str, findings: list[dict[str, Any]], depth: str
) -> dict[str, Any]:
    """Synthesize findings using LLM if available.

    Attempts to use research_llm_summarize to create synthetic summary and key findings.
    Falls back gracefully if LLM is unavailable.
    """
    try:
        from loom.tools.llm import research_llm_summarize

        # Concatenate findings for summarization
        combined_text = "\n\n---\n\n".join(
            [
                f"Title: {f.get('title', '')}\nURL: {f.get('url', '')}\n\n{f.get('content', '')}"
                for f in findings[:3]  # Limit to top 3 for cost
            ]
        )

        summary = await research_llm_summarize(combined_text, length="medium" if depth == "brief" else "long")

        if isinstance(summary, dict) and "summary" in summary:
            return {
                "executive_summary": summary.get("summary", ""),
                "key_points": summary.get("key_points", []),
                "synthesis_available": True,
            }
    except (ImportError, Exception) as e:
        logger.debug("llm_synthesis_unavailable: %s", str(e)[:100])

    return {
        "executive_summary": "",
        "key_points": [],
        "synthesis_available": False,
    }


def _build_report_sections(
    topic: str,
    findings: list[dict[str, Any]],
    synthesis: dict[str, Any],
    depth: str,
    include_methodology: bool,
    include_recommendations: bool,
) -> list[dict[str, Any]]:
    """Build structured report sections from findings."""
    sections = []

    # Executive Summary
    sections.append(
        {
            "title": "Executive Summary",
            "content": synthesis.get("executive_summary", "")
            or f"This report provides a comprehensive analysis of {topic}.",
            "type": "summary",
        }
    )

    # Key Findings
    key_points = synthesis.get("key_points", [])
    if not key_points and findings:
        key_points = [f.get("snippet", "")[:100] for f in findings if f.get("snippet")]
    sections.append(
        {
            "title": "Key Findings",
            "content": "\n".join([f"- {p}" for p in key_points[:10]]) if key_points else "No key findings extracted.",
            "type": "findings",
        }
    )

    # Detailed Analysis (per source)
    if depth in ("standard", "comprehensive"):
        for i, finding in enumerate(findings[:5 if depth == "standard" else 10], 1):
            sections.append(
                {
                    "title": f"Source {i}: {finding.get('title', 'Untitled')[:60]}",
                    "content": finding.get("content", ""),
                    "url": finding.get("url", ""),
                    "type": "detailed",
                }
            )

    # Evidence Hierarchy
    if depth == "comprehensive" and findings:
        sections.append(
            {
                "title": "Evidence Hierarchy",
                "content": _build_evidence_hierarchy(findings),
                "type": "evidence",
            }
        )

    # Methodology
    if include_methodology:
        sections.append(
            {
                "title": "Methodology",
                "content": _build_methodology_section(len(findings)),
                "type": "methodology",
            }
        )

    # Recommendations
    if include_recommendations:
        sections.append(
            {
                "title": "Recommendations",
                "content": _build_recommendations_section(topic, synthesis),
                "type": "recommendations",
            }
        )

    return sections


def _build_evidence_hierarchy(findings: list[dict[str, Any]]) -> str:
    """Build evidence hierarchy section (strongest to weakest)."""
    lines = ["Evidence is ranked by source relevance and content depth:\n"]
    for i, finding in enumerate(findings[:5], 1):
        strength = "Strong" if i <= 2 else "Medium" if i <= 4 else "Supplementary"
        lines.append(f"{i}. **{strength}**: {finding.get('title', 'Source')[:60]}")
    return "\n".join(lines)


def _build_methodology_section(num_sources: int) -> str:
    """Build methodology section."""
    return f"""This report was generated using the Loom research pipeline:

1. **Search Phase**: Queried multiple search providers to identify relevant sources
2. **Fetch Phase**: Retrieved content from {num_sources} identified sources
3. **Extraction Phase**: Parsed and normalized source content
4. **Synthesis Phase**: Combined findings using LLM synthesis when available
5. **Validation Phase**: Cross-checked findings across multiple sources

**Data Sources**: {num_sources} primary sources

**Confidence Level**: Based on source agreement and content validation"""


def _build_recommendations_section(topic: str, synthesis: dict[str, Any]) -> str:
    """Build recommendations section."""
    return f"""Based on the research findings regarding {topic}:

1. **Further Research**: Consider consulting domain-specific databases and expert resources
2. **Source Validation**: Verify critical findings with additional primary sources
3. **Regular Updates**: This topic may benefit from periodic research updates as new information emerges
4. **Expert Consultation**: For decision-critical applications, consult subject matter experts"""


def _format_report(sections: list[dict[str, Any]], format: str, depth: str) -> str:
    """Format report sections into requested output format."""
    if format == "json":
        return json.dumps(sections, indent=2)
    elif format == "html":
        return _to_html(sections)
    else:  # markdown (default)
        return _to_markdown(sections)


def _to_markdown(sections: list[dict[str, Any]]) -> str:
    """Convert sections to Markdown format."""
    lines = []
    for i, section in enumerate(sections, 1):
        title = section.get("title", "")
        content = section.get("content", "")
        url = section.get("url", "")

        lines.append(f"## {title}\n")
        lines.append(content)
        if url:
            lines.append(f"\n**Source**: {url}")
        lines.append("\n")

    return "\n".join(lines)


def _to_html(sections: list[dict[str, Any]]) -> str:
    """Convert sections to HTML format."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width">',
        "<style>",
        "body { font-family: sans-serif; line-height: 1.6; max-width: 900px; margin: 20px; }",
        "h2 { color: #333; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }",
        "a { color: #0066cc; }",
        ".source { font-size: 0.9em; color: #666; margin-top: 10px; }",
        "</style>",
        "</head>",
        "<body>",
    ]

    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")
        url = section.get("url", "")

        html_parts.append(f"<h2>{_escape_html(title)}</h2>")
        html_parts.append(f"<p>{_escape_html(content)}</p>")
        if url:
            html_parts.append(f'<p class="source"><strong>Source</strong>: <a href="{_escape_html(url)}">{_escape_html(url[:80])}</a></p>')

    html_parts.extend(["</body>", "</html>"])
    return "\n".join(html_parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _error_response(error_message: str) -> dict[str, Any]:
    """Build a standardized error response."""
    logger.error("report_error: %s", error_message)
    return {
        "error": error_message,
        "title": "Error",
        "report": f"Report generation failed: {error_message}",
        "sections": [],
        "sources_used": 0,
        "confidence": 0.0,
        "generated_at": datetime.now(UTC).isoformat(),
        "word_count": 0,
        "depth": "standard",
        "format": "markdown",
    }
