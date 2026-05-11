"""Brain Perception Layer — Intent parsing and query understanding."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.brain.perception")

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "search": ["find", "search", "look", "query", "discover", "locate"],
    "fetch": ["get", "fetch", "retrieve", "download", "scrape", "crawl"],
    "analyze": ["analyze", "analyse", "examine", "inspect", "assess", "evaluate"],
    "security": ["vuln", "cve", "exploit", "breach", "scan", "pentest", "osint"],
    "academic": ["paper", "citation", "journal", "arxiv", "retraction", "doi"],
    "legal": ["law", "article", "regulation", "court", "legal", "statute", "uae"],
    "crypto": ["bitcoin", "ethereum", "blockchain", "wallet", "token", "defi"],
    "darkweb": ["onion", "tor", "dark", "hidden", "underground"],
    "job": ["job", "career", "salary", "hiring", "resume", "employment"],
    "llm": ["summarize", "translate", "classify", "expand", "embed", "rewrite"],
    "privacy": ["fingerprint", "tracking", "steganography", "anonymity", "privacy"],
}

_INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("comparison", re.compile(r"\b(compare|versus|vs\.?|differ|contrast)\b", re.I)),
    ("multi_step", re.compile(r"\b(then|and also|additionally|after that|next)\b", re.I)),
    ("explanation", re.compile(r"\b(explain|describe|what is|how does|why)\b", re.I)),
    ("monitoring", re.compile(r"\b(monitor|watch|alert|track|detect changes)\b", re.I)),
]


def parse_intent(query: str) -> dict[str, Any]:
    """Parse user query into structured intent representation.

    Returns dict with:
        - query: original query text
        - domains: detected domain categories
        - intent_type: single_tool | multi_step | comparison | explanation | monitoring
        - entities: extracted named entities (URLs, emails, IPs, etc.)
        - keywords: significant keywords for tool matching
    """
    query_lower = query.lower().strip()

    domains = _detect_domains(query_lower)
    intent_type = _detect_intent_type(query_lower)
    entities = _extract_entities(query)
    keywords = _extract_keywords(query_lower)

    return {
        "query": query,
        "domains": domains,
        "intent_type": intent_type,
        "entities": entities,
        "keywords": keywords,
    }


def _detect_domains(query_lower: str) -> list[str]:
    """Detect which domain categories the query relates to."""
    matched = []
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            matched.append(domain)
    return matched or ["general"]


def _detect_intent_type(query_lower: str) -> str:
    """Detect the high-level intent type."""
    for intent_name, pattern in _INTENT_PATTERNS:
        if pattern.search(query_lower):
            return intent_name
    return "single_tool"


def _extract_entities(query: str) -> dict[str, list[str]]:
    """Extract named entities (URLs, emails, IPs, domains)."""
    entities: dict[str, list[str]] = {}

    urls = re.findall(r"https?://[^\s,\"'<>]+", query)
    if urls:
        entities["urls"] = urls

    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", query)
    if emails:
        entities["emails"] = emails

    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", query)
    if ips:
        entities["ips"] = ips

    domains = re.findall(
        r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", query.lower()
    )
    domain_set = set(domains) - set(emails) - {"e.g", "i.e", "etc.com"}
    if domain_set:
        entities["domains"] = list(domain_set)

    return entities


def _extract_keywords(query_lower: str) -> list[str]:
    """Extract significant keywords for tool matching."""
    stop_words = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "because", "about",
        "this", "that", "these", "those", "it", "its", "my", "me", "i",
        "and", "or", "but", "if", "while", "although", "what", "which", "who",
    })
    words = re.findall(r"[a-z][a-z0-9_]+", query_lower)
    return [w for w in words if w not in stop_words and len(w) > 2]
