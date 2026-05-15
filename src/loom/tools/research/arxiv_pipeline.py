"""arXiv research paper ingestion and technique extraction pipeline.

Ingests papers from arXiv on jailbreaking, red-teaming, and prompt injection.
Extracts key attack techniques from paper abstracts with relevance scoring.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

import httpx

from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_text

logger = logging.getLogger("loom.tools.arxiv_pipeline")

# Default keywords for arXiv search
DEFAULT_KEYWORDS = [
    "jailbreak",
    "prompt injection",
    "red teaming",
    "adversarial attack LLM",
    "safety bypass",
]

# Technique type patterns
TECHNIQUE_PATTERNS = {
    "injection": r"inject|injection|inject(?:ed|ing)?",
    "encoding": r"encod|obfuscat|base64|unicode|token|character",
    "multi_turn": r"multi[\s-]turn|conversation|dialogue|multi-round",
    "reasoning": r"reasoning|chain[\s-]of[\s-]thought|cot|step[\s-]by[\s-]step|r1",
    "social_engineering": r"social|psycholog|manipul|persuasion|trick|deceiv|context|roleplay",
}

# Technique markers in abstracts
TECHNIQUE_MARKERS = [
    "we propose",
    "novel method",
    "attack achieves",
    "bypass rate",
    "success rate",
    "asr",
    "presents",
    "demonstrates",
    "achieves",
]


def _extract_relevance_score(abstract: str, keywords: list[str]) -> float:
    """Calculate relevance score (0-10) based on keyword density."""
    if not abstract or not keywords:
        return 0.0

    abstract_lower = abstract.lower()
    keyword_matches = sum(1 for kw in keywords if kw.lower() in abstract_lower)
    max_possible = len(keywords)

    if max_possible == 0:
        return 0.0

    score = (keyword_matches / max_possible) * 10.0
    return min(10.0, score)


def _classify_technique_type(description: str) -> str:
    """Classify technique type based on pattern matching."""
    description_lower = description.lower()

    for tech_type, pattern in TECHNIQUE_PATTERNS.items():
        if re.search(pattern, description_lower):
            return tech_type

    return "unknown"


def _extract_asr_metrics(abstract: str) -> dict[str, Any]:
    """Extract Attack Success Rate and related metrics from abstract."""
    metrics = {
        "reported_asr": None,
        "success_rate": None,
        "target_models": [],
    }

    # Pattern: "X% success rate" or "X% ASR" or "X% attack success"
    asr_pattern = r"(\d+(?:\.\d+)?)\s*%\s*(?:asr|attack\s+success|success\s+rate)"
    asr_match = re.search(asr_pattern, abstract, re.IGNORECASE)
    if asr_match:
        metrics["reported_asr"] = float(asr_match.group(1))

    # Pattern: model names (GPT-4, Claude, Gemini, etc.)
    model_pattern = r"(?:GPT-[0-9]|Claude|Gemini|LLaMA|Vicuna|Alpaca|Mistral|Qwen)"
    models = re.findall(model_pattern, abstract, re.IGNORECASE)
    if models:
        metrics["target_models"] = list(set(models))

    return metrics


def _generate_strategy_template(description: str, technique_type: str) -> str:
    """Generate a one-line strategy template from technique description."""
    desc_clean = description.strip()[:80]

    if technique_type == "injection":
        return f"Inject payload: {desc_clean}..."
    elif technique_type == "encoding":
        return f"Encode with {desc_clean}..."
    elif technique_type == "multi_turn":
        return f"Multi-turn attack: {desc_clean}..."
    elif technique_type == "reasoning":
        return f"Chain reasoning: {desc_clean}..."
    elif technique_type == "social_engineering":
        return f"Social engineering: {desc_clean}..."

    return f"Technique: {desc_clean}..."


@handle_tool_errors("research_arxiv_ingest")
async def research_arxiv_ingest(
    keywords: list[str] | None = None,
    days_back: int = 7,
    max_papers: int = 20,
) -> dict[str, Any]:
    """Search arXiv for recent papers on jailbreaking/red-teaming/prompt injection.

    Extracts key techniques from paper abstracts with relevance scoring.

    Args:
        keywords: List of keywords to search (defaults to jailbreak, prompt injection, etc.)
        days_back: Number of days back to search (1-365)
        max_papers: Maximum papers to ingest (1-100)

    Returns:
        Dict with keys:
        - keywords: search keywords used
        - papers_found: total papers matched
        - papers: list of paper dicts with title, authors, abstract, arxiv_id, date, relevance_score, techniques_found
        - total_techniques_extracted: count of unique techniques found across all papers
        - error: optional error message if search failed
    """
    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    # Validate inputs
    keywords = [kw.strip() for kw in keywords if kw.strip()][:10]
    days_back = max(1, min(days_back, 365))
    max_papers = max(1, min(max_papers, 100))

    logger.info("arxiv_ingest keywords=%s days_back=%d max_papers=%d", keywords, days_back, max_papers)

    try:
        # Build arXiv API query
        query_parts = [f"(title:\"{kw}\" OR abstract:\"{kw}\")" for kw in keywords]
        query_str = " OR ".join(query_parts)
        search_query = f"search_query={quote(query_str)}&start=0&max_results={max_papers}&sortBy=submittedDate&sortOrder=descending"

        url = f"https://export.arxiv.org/api/query?{search_query}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp_text = await fetch_text(client, url)
            if not resp_text:
                raise ValueError("Empty response from arXiv API")

        # Parse Atom XML response
        root = ET.fromstring(resp_text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}

        papers: list[dict[str, Any]] = []
        all_techniques: set[str] = set()

        for entry in root.findall("atom:entry", namespace):
            try:
                title_elem = entry.find("atom:title", namespace)
                title = (title_elem.text or "").strip() if title_elem is not None else ""

                abstract_elem = entry.find("atom:summary", namespace)
                abstract = (abstract_elem.text or "").strip() if abstract_elem is not None else ""

                arxiv_id_elem = entry.find("atom:id", namespace)
                arxiv_id = ""
                if arxiv_id_elem is not None and arxiv_id_elem.text:
                    arxiv_id = arxiv_id_elem.text.split("/abs/")[-1]

                published_elem = entry.find("atom:published", namespace)
                published_date = (published_elem.text or "")[:10] if published_elem is not None else ""

                authors_elems = entry.findall("atom:author", namespace)
                authors = []
                for author_elem in authors_elems:
                    author_name_elem = author_elem.find("atom:name", namespace)
                    if author_name_elem is not None:
                        authors.append(author_name_elem.text or "")

                # Extract techniques from abstract
                relevance_score = _extract_relevance_score(abstract, keywords)
                metrics = _extract_asr_metrics(abstract)

                # Extract techniques mentioned in abstract
                techniques_found: list[dict[str, Any]] = []
                for marker in TECHNIQUE_MARKERS:
                    pattern = f"{re.escape(marker)}[^.]*"
                    for match in re.finditer(pattern, abstract, re.IGNORECASE):
                        technique_desc = match.group(0)[:100]
                        technique_type = _classify_technique_type(technique_desc)

                        technique = {
                            "name": f"{technique_type.replace('_', ' ').title()} #{len(techniques_found) + 1}",
                            "type": technique_type,
                            "description": technique_desc,
                            "reported_asr": metrics.get("reported_asr"),
                            "target_models": metrics.get("target_models", []),
                            "strategy_template": _generate_strategy_template(technique_desc, technique_type),
                        }
                        techniques_found.append(technique)
                        all_techniques.add(technique["name"])

                paper = {
                    "title": title,
                    "authors": authors,
                    "abstract": abstract[:500],
                    "arxiv_id": arxiv_id,
                    "date": published_date,
                    "relevance_score": round(relevance_score, 2),
                    "techniques_found": techniques_found,
                }

                if paper["relevance_score"] > 0:
                    papers.append(paper)

            except Exception as exc:
                logger.warning("arxiv_ingest parse error: %s", exc)
                continue

        return {
            "keywords": keywords,
            "papers_found": len(papers),
            "papers": papers[:max_papers],
            "total_techniques_extracted": len(all_techniques),
        }

    except Exception as exc:
        logger.error("arxiv_ingest failed: %s", exc)
        return {
            "keywords": keywords,
            "papers_found": 0,
            "papers": [],
            "total_techniques_extracted": 0,
            "error": str(exc),
        }


@handle_tool_errors("research_arxiv_extract_techniques")
async def research_arxiv_extract_techniques(
    paper_abstract: str,
    paper_title: str = "",
) -> dict[str, Any]:
    """Extract actionable attack techniques from a paper abstract.

    Classifies technique types, extracts metrics, and generates strategy templates.

    Args:
        paper_abstract: Paper abstract text to extract techniques from
        paper_title: Optional paper title for context

    Returns:
        Dict with keys:
        - title: paper title
        - techniques: list of technique dicts with name, type, description, reported_asr, target_models, strategy_template
        - actionability_score: 0-10 score indicating practical applicability
    """
    if not paper_abstract or not paper_abstract.strip():
        return {
            "title": paper_title,
            "techniques": [],
            "actionability_score": 0.0,
        }

    try:
        logger.info("arxiv_extract abstract_len=%d", len(paper_abstract))

        techniques: list[dict[str, Any]] = []

        # Extract metrics
        metrics = _extract_asr_metrics(paper_abstract)

        # Find technique descriptions (sentences containing markers)
        technique_sentences: list[str] = []
        for marker in TECHNIQUE_MARKERS:
            pattern = f"[^.!?]*{re.escape(marker)}[^.!?]*[.!?]"
            matches = re.finditer(pattern, paper_abstract, re.IGNORECASE)
            for match in matches:
                sentence = match.group(0).strip()
                if sentence and len(sentence) < 500:
                    technique_sentences.append(sentence)

        # Deduplicate and create technique records
        seen_desc: set[str] = set()
        for desc in technique_sentences[:10]:  # Limit to 10 techniques
            if desc not in seen_desc:
                technique_type = _classify_technique_type(desc)

                technique = {
                    "name": f"{technique_type.replace('_', ' ').title()} Attack",
                    "type": technique_type,
                    "description": desc[:150],
                    "reported_asr": metrics.get("reported_asr"),
                    "target_models": metrics.get("target_models", []),
                    "strategy_template": _generate_strategy_template(desc, technique_type),
                }

                techniques.append(technique)
                seen_desc.add(desc)

        # Calculate actionability score (0-10) based on presence of metrics and technique count
        actionability = 0.0
        if metrics.get("reported_asr"):
            actionability += 3.0
        if metrics.get("target_models"):
            actionability += 3.0
        if len(techniques) > 0:
            actionability += min(4.0, len(techniques))

        return {
            "title": paper_title,
            "techniques": techniques,
            "actionability_score": round(min(10.0, actionability), 2),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_arxiv_extract_techniques"}
