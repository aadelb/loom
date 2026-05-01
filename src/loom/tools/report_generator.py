"""Report generator tool — auto-generate structured research reports."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.report_generator")

_WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_ARXIV_API = "http://export.arxiv.org/api/query"
_HN_API = "https://hn.algolia.com/api/v1/search"


async def _fetch_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    """Fetch JSON with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("report_generator fetch failed url=%s: %s", url[:80], exc)
    return None


async def _fetch_text(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> str:
    """Fetch text with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("report_generator text fetch failed url=%s: %s", url[:80], exc)
    return ""


async def _wikipedia_overview(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Extract overview from Wikipedia."""
    try:
        url = f"{_WIKIPEDIA_API}?action=query&titles={quote(topic)}&prop=extracts&explaintext=true&format=json"
        data = await _fetch_json(client, url, timeout=20.0)

        if not data or "query" not in data:
            return {"title": topic, "overview": "", "source": "wikipedia"}

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return {"title": topic, "overview": "", "source": "wikipedia"}

        page = next(iter(pages.values()), {})
        title = page.get("title", topic)
        extract = page.get("extract", "")

        # Truncate to first 500 chars
        overview = extract[:500] if extract else ""

        return {"title": title, "overview": overview, "source": "wikipedia"}
    except Exception as exc:
        logger.debug("wikipedia_overview failed: %s", exc)
        return {"title": topic, "overview": "", "source": "wikipedia"}


async def _semantic_scholar_papers(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Extract recent key papers from Semantic Scholar."""
    try:
        url = f"{_SEMANTIC_SCHOLAR_API}?query={quote(topic)}&limit=10&fields=title,year,citationCount,authors,abstract"
        data = await _fetch_json(client, url, timeout=20.0)

        if not data or "data" not in data:
            return {"papers": [], "source": "semantic_scholar"}

        papers = []
        for paper in data.get("data", [])[:5]:  # Top 5 papers
            paper_entry = {
                "title": paper.get("title", ""),
                "year": paper.get("year", 0),
                "citations": paper.get("citationCount", 0),
                "authors": [a.get("name", "") for a in paper.get("authors", [])][:3],
                "summary": paper.get("abstract", "")[:200],
            }
            papers.append(paper_entry)

        return {"papers": papers, "source": "semantic_scholar"}
    except Exception as exc:
        logger.debug("semantic_scholar_papers failed: %s", exc)
        return {"papers": [], "source": "semantic_scholar"}


async def _arxiv_recent(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Extract recent papers from arXiv."""
    try:
        query = f"all:{quote(topic)}"
        url = f"{_ARXIV_API}?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results=5"
        text = await _fetch_text(client, url, timeout=25.0)

        if not text:
            return {"papers": [], "source": "arxiv"}

        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(text)
            namespace = {"atom": "http://www.w3.org/2005/Atom"}

            papers = []
            for entry in root.findall("atom:entry", namespace):
                title_elem = entry.find("atom:title", namespace)
                summary_elem = entry.find("atom:summary", namespace)
                updated_elem = entry.find("atom:updated", namespace)
                authors_elems = entry.findall("atom:author", namespace)

                title = title_elem.text if title_elem is not None else ""
                summary = summary_elem.text if summary_elem is not None else ""
                updated = updated_elem.text if updated_elem is not None else ""
                authors = [
                    a.find("atom:name", namespace).text
                    for a in authors_elems
                    if a.find("atom:name", namespace) is not None
                ][:3]

                paper_entry = {
                    "title": title.strip(),
                    "summary": summary[:300],
                    "date": updated[:10],
                    "authors": authors,
                }
                papers.append(paper_entry)

            return {"papers": papers, "source": "arxiv"}
        except Exception as exc:
            logger.debug("arxiv_recent parse failed: %s", exc)
            return {"papers": [], "source": "arxiv"}
    except Exception as exc:
        logger.debug("arxiv_recent failed: %s", exc)
        return {"papers": [], "source": "arxiv"}


async def _hackernews_discussion(
    client: httpx.AsyncClient, topic: str
) -> dict[str, Any]:
    """Extract community discussion from HackerNews."""
    try:
        url = f"{_HN_API}?query={quote(topic)}&tags=story&hitsPerPage=10"
        data = await _fetch_json(client, url, timeout=20.0)

        if not data or "hits" not in data:
            return {"discussions": [], "source": "hackernews"}

        discussions = []
        for hit in data.get("hits", [])[:5]:
            discussion = {
                "title": hit.get("title", ""),
                "points": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "url": hit.get("url", ""),
                "author": hit.get("author", ""),
            }
            discussions.append(discussion)

        return {"discussions": discussions, "source": "hackernews"}
    except Exception as exc:
        logger.debug("hackernews_discussion failed: %s", exc)
        return {"discussions": [], "source": "hackernews"}


def _generate_markdown_report(
    topic: str,
    depth: str,
    sections_data: dict[str, Any],
) -> str:
    """Generate markdown formatted report."""
    lines: list[str] = []

    lines.append(f"# Research Report: {topic}")
    lines.append(f"\n**Generated:** {datetime.now(UTC).isoformat()}")
    lines.append(f"**Depth Level:** {depth}")
    lines.append("")

    # Overview section
    overview = sections_data.get("overview", {})
    if overview.get("overview"):
        lines.append("## Overview")
        lines.append("")
        lines.append(overview["overview"])
        lines.append("")

    # Key Findings
    if overview.get("overview"):
        lines.append("## Key Findings")
        lines.append("")
        lines.append("- Research topic with documented presence in Wikipedia")
        if sections_data.get("key_papers", {}).get("papers"):
            lines.append(
                f"- {len(sections_data['key_papers']['papers'])} significant papers found"
            )
        if sections_data.get("recent_developments", {}).get("papers"):
            lines.append(
                f"- {len(sections_data['recent_developments']['papers'])} recent arXiv papers"
            )
        if sections_data.get("community_discussion", {}).get("discussions"):
            lines.append(
                f"- {len(sections_data['community_discussion']['discussions'])} HackerNews discussions"
            )
        lines.append("")

    # Key Papers Section
    key_papers = sections_data.get("key_papers", {})
    if key_papers.get("papers"):
        lines.append("## Key Papers & Research")
        lines.append("")
        for i, paper in enumerate(key_papers["papers"][:5], 1):
            title = paper.get("title", "")
            year = paper.get("year", "")
            citations = paper.get("citations", 0)
            authors = ", ".join(paper.get("authors", [])[:2])
            lines.append(f"### {i}. {title}")
            if authors:
                lines.append(f"**Authors:** {authors}")
            if year:
                lines.append(f"**Year:** {year}")
            if citations:
                lines.append(f"**Citations:** {citations}")
            if paper.get("summary"):
                lines.append(f"\n{paper['summary']}")
            lines.append("")

    # Recent Developments
    recent = sections_data.get("recent_developments", {})
    if recent.get("papers"):
        lines.append("## Recent Developments (arXiv)")
        lines.append("")
        for i, paper in enumerate(recent["papers"][:3], 1):
            title = paper.get("title", "")
            date = paper.get("date", "")
            authors = ", ".join(paper.get("authors", [])[:2])
            lines.append(f"### {i}. {title}")
            if date:
                lines.append(f"**Date:** {date}")
            if authors:
                lines.append(f"**Authors:** {authors}")
            if paper.get("summary"):
                lines.append(f"\n{paper['summary'][:150]}...")
            lines.append("")

    # Community Discussion
    community = sections_data.get("community_discussion", {})
    if community.get("discussions"):
        lines.append("## Community Discussion (HackerNews)")
        lines.append("")
        for i, disc in enumerate(community["discussions"][:5], 1):
            title = disc.get("title", "")
            points = disc.get("points", 0)
            comments = disc.get("comments", 0)
            lines.append(f"### {i}. {title}")
            lines.append(
                f"**Engagement:** {points} points, {comments} comments"
            )
            if disc.get("url"):
                lines.append(f"**URL:** {disc['url']}")
            lines.append("")

    # Open Questions (auto-generated based on depth)
    if depth in ("standard", "deep"):
        lines.append("## Open Questions & Future Work")
        lines.append("")
        lines.append("- What are the next frontiers in this field?")
        lines.append("- How are recent breakthroughs being applied?")
        lines.append("- What challenges remain to be solved?")
        lines.append("")

    lines.append("---")
    lines.append("*Report generated by Loom Research Tool*")

    return "\n".join(lines)


async def research_generate_report(
    topic: str,
    depth: str = "standard",
    sections: list[str] | None = None,
) -> dict[str, Any]:
    """Auto-generate a structured research report.

    Aggregates data from Wikipedia (overview), Semantic Scholar (key papers),
    arXiv (recent developments), and HackerNews (community discussion) to
    generate a comprehensive research report with citations.

    Args:
        topic: research topic or query
        depth: report depth level - "brief" (overview only), "standard" (standard),
               or "deep" (comprehensive with extended analysis)
        sections: optional list of section names to include; if None, all sections
                 included based on depth level

    Returns:
        Dict with ``topic``, ``depth``, ``sections`` (list of dicts with title/content/sources),
        ``total_sources``, ``word_count``, ``markdown_report``, ``generated_at``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0 (report generation)"},
        ) as client:
            # Run all data collection tasks in parallel
            overview_task = _wikipedia_overview(client, topic)
            key_papers_task = _semantic_scholar_papers(client, topic)
            recent_task = _arxiv_recent(client, topic)
            discussion_task = _hackernews_discussion(client, topic)

            (overview_data, papers_data, recent_data, discussion_data) = await asyncio.gather(
                overview_task,
                key_papers_task,
                recent_task,
                discussion_task,
                return_exceptions=True,
            )

            # Handle exceptions
            if isinstance(overview_data, Exception):
                overview_data = {"title": topic, "overview": "", "source": "wikipedia"}
            if isinstance(papers_data, Exception):
                papers_data = {"papers": [], "source": "semantic_scholar"}
            if isinstance(recent_data, Exception):
                recent_data = {"papers": [], "source": "arxiv"}
            if isinstance(discussion_data, Exception):
                discussion_data = {"discussions": [], "source": "hackernews"}

            # Organize sections data
            sections_data = {
                "overview": overview_data,
                "key_papers": papers_data,
                "recent_developments": recent_data,
                "community_discussion": discussion_data,
            }

            # Generate markdown report
            markdown_report = _generate_markdown_report(topic, depth, sections_data)

            # Build sections list for output
            output_sections = []

            if overview_data.get("overview"):
                output_sections.append({
                    "title": "Overview",
                    "content": overview_data["overview"],
                    "sources": ["wikipedia"],
                })

            if papers_data.get("papers"):
                papers_summary = "\n".join([
                    f"- {p.get('title', '')}: {p.get('citations', 0)} citations"
                    for p in papers_data["papers"][:5]
                ])
                output_sections.append({
                    "title": "Key Papers",
                    "content": papers_summary,
                    "sources": ["semantic_scholar"],
                })

            if recent_data.get("papers"):
                recent_summary = "\n".join([
                    f"- [{p.get('date', '')}] {p.get('title', '')}"
                    for p in recent_data["papers"][:5]
                ])
                output_sections.append({
                    "title": "Recent Developments",
                    "content": recent_summary,
                    "sources": ["arxiv"],
                })

            if discussion_data.get("discussions"):
                discussion_summary = "\n".join([
                    f"- {d.get('title', '')} ({d.get('points', 0)} pts)"
                    for d in discussion_data["discussions"][:5]
                ])
                output_sections.append({
                    "title": "Community Discussion",
                    "content": discussion_summary,
                    "sources": ["hackernews"],
                })

            # Count total sources
            sources_set = set()
            for section_data in sections_data.values():
                if isinstance(section_data, dict):
                    source = section_data.get("source")
                    if source:
                        sources_set.add(source)

            # Calculate word count
            word_count = len(markdown_report.split())

            return {
                "topic": topic,
                "depth": depth,
                "sections": output_sections,
                "total_sources": len(sources_set),
                "sources_used": list(sources_set),
                "word_count": word_count,
                "markdown_report": markdown_report,
                "generated_at": datetime.now(UTC).isoformat(),
            }

    return await _run()


async def research_generate_executive_report(
    scores: list[dict] | None = None,
    tracker_data: list[dict] | None = None,
    audit_entries: list[dict] | None = None,
    report_type: str = "executive_summary",
    title: str = "Red Team Assessment",
    framework: str = "eu_ai_act",
    model_results: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """Generate automated reports from Loom scoring and audit data.

    Generates comprehensive reports from 45-dimension scoring framework,
    attack tracker data, and compliance audit entries.

    Supported report types:
    - executive_summary: 45-dimension scoring analysis with risk levels (requires scores)
    - strategy: Attack strategy effectiveness ranking (requires tracker_data)
    - model_comparison: Cross-model comparison tables (requires model_results)
    - compliance: Framework-specific compliance assessment (requires audit_entries)

    Supported frameworks for compliance reports:
    - eu_ai_act: EU AI Act Article 15 transparency/oversight requirements
    - nist_ai_rmf: NIST AI Risk Management Framework (Map/Measure/Manage/Govern)
    - owasp_agentic_ai_top_10: OWASP Agentic AI Top 10 risks

    Args:
        scores: List of score dicts from score_all() [optional, for executive_summary]
        tracker_data: List of attack tracker entries [optional, for strategy report]
        audit_entries: List of audit log dicts [optional, for compliance report]
        report_type: One of "executive_summary", "strategy", "model_comparison", "compliance"
        title: Report title (default: "Red Team Assessment")
        framework: Compliance framework ("eu_ai_act", "nist_ai_rmf", "owasp_agentic_ai_top_10")
        model_results: Dict mapping model names to score lists [optional, for model_comparison]

    Returns:
        Dict with "report_type", "title", "markdown", "generated_at", and optional metadata
    """
    from loom.report_gen import ReportGenerator

    gen = ReportGenerator()
    markdown = ""
    metadata: dict[str, Any] = {}

    if report_type == "executive_summary":
        if not scores:
            markdown = "# Executive Summary\n\nNo scoring data provided. Please provide scores from score_all().\n"
        else:
            markdown = gen.generate_executive_summary(scores, title)
            metadata["entries_analyzed"] = len(scores)
    elif report_type == "strategy":
        if not tracker_data:
            markdown = "# Strategy Effectiveness Report\n\nNo attack tracker data provided.\n"
        else:
            markdown = gen.generate_strategy_report(tracker_data)
            metadata["strategies_analyzed"] = len(tracker_data)
    elif report_type == "model_comparison":
        if not model_results:
            markdown = "# Model Comparison Report\n\nNo model data provided.\n"
        else:
            markdown = gen.generate_model_comparison(model_results)
            metadata["models_compared"] = len(model_results)
    elif report_type == "compliance":
        if not audit_entries:
            markdown = f"# {framework.replace('_', ' ').title()}\n\nNo audit entries provided.\n"
        else:
            markdown = gen.generate_compliance_report(audit_entries, framework)
            metadata["audit_entries_reviewed"] = len(audit_entries)
            metadata["framework"] = framework
    else:
        markdown = f"Unknown report type: {report_type}"

    return {
        "report_type": report_type,
        "title": title,
        "markdown": markdown,
        "generated_at": datetime.now(UTC).isoformat(),
        **metadata,
    }
