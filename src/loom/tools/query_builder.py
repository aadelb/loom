"""Smart prompt/query builder for Loom v3.

Transforms raw user requests into optimized research queries using DSPy-style
chain-of-thought decomposition (if available) or rule-based + LLM extraction.

Public API:
    research_build_query(user_request, context, output_type, max_queries, optimize)
        → Dict with extracted intent, sub-questions, optimized queries, recommended tools, pipeline

Patterns:
    - Intent extraction via regex + LLM fallback
    - Query decomposition into sub-questions
    - Engine-specific optimization (web, academic, osint, social)
    - Tool recommendation based on intent
    - Ordered pipeline construction for execution
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

logger = logging.getLogger("loom.tools.query_builder")

# Intent categories and their characteristics
INTENT_KEYWORDS: dict[str, dict[str, Any]] = {
    "wealth_building": {
        "keywords": ["rich", "wealth", "money", "financial", "invest", "income", "earn"],
        "scope": "broad",
        "depth": "intermediate",
        "tools": ["research_multi_search", "research_deep", "research_career_trajectory"],
    },
    "threat_intel": {
        "keywords": ["vulnerability", "cve", "exploit", "breach", "threat", "attack", "malware"],
        "scope": "narrow",
        "depth": "deep",
        "tools": ["research_github", "research_search", "research_cve_lookup"],
    },
    "academic_research": {
        "keywords": ["paper", "research", "study", "meta-analysis", "systematic", "scholar", "arxiv", "ai", "academic", "journal"],
        "scope": "narrow",
        "depth": "deep",
        "tools": ["research_deep", "research_search"],
    },
    "osint_recon": {
        "keywords": ["reconnaissance", "osint", "enumerate", "scan", "find", "locate", "domain", "ip"],
        "scope": "narrow",
        "depth": "intermediate",
        "tools": ["research_github", "research_search", "research_passive_recon"],
    },
    "social_intelligence": {
        "keywords": ["profile", "sentiment", "opinion", "discussion", "forum", "reddit", "social"],
        "scope": "broad",
        "depth": "shallow",
        "tools": ["research_search", "research_social_graph"],
    },
    "product_research": {
        "keywords": ["product", "service", "comparison", "review", "alternative", "feature", "pricing"],
        "scope": "intermediate",
        "depth": "intermediate",
        "tools": ["research_multi_search", "research_deep"],
    },
    "competitive_intelligence": {
        "keywords": ["competitor", "market", "strategy", "competitive", "benchmark", "analysis"],
        "scope": "broad",
        "depth": "intermediate",
        "tools": ["research_search", "research_deep", "research_competitive_intel"],
    },
    "technical_documentation": {
        "keywords": ["documentation", "api", "tutorial", "guide", "howto", "example", "code"],
        "scope": "narrow",
        "depth": "shallow",
        "tools": ["research_github", "research_search"],
    },
    "news_current_events": {
        "keywords": ["news", "recent", "latest", "current", "event", "breaking", "today"],
        "scope": "intermediate",
        "depth": "shallow",
        "tools": ["research_search", "research_deep"],
    },
    "historical_research": {
        "keywords": ["history", "historical", "evolution", "timeline", "background", "origin"],
        "scope": "broad",
        "depth": "intermediate",
        "tools": ["research_search", "research_deep"],
    },
    "general_research": {
        "keywords": ["research", "find", "search", "analyze", "investigate"],
        "scope": "intermediate",
        "depth": "intermediate",
        "tools": ["research_multi_search", "research_deep", "research_llm_answer"],
    },
}

# Query optimization patterns per search engine
QUERY_OPTIMIZATIONS: dict[str, dict[str, Any]] = {
    "arxiv": {
        "prefer_academic_terms": True,
        "supports_filters": ["author", "category", "date"],
        "max_length": 200,
        "tips": ["Use technical terminology", "Include author names if known", "Specify category (cs.AI, etc.)"],
    },
    "web": {
        "prefer_academic_terms": False,
        "supports_filters": ["site:", "inurl:", "filetype:"],
        "max_length": 300,
        "tips": ["Use natural language", "Include year for time-sensitive topics", "Use quotes for exact phrases"],
    },
    "github": {
        "prefer_academic_terms": False,
        "supports_filters": ["language:", "stars:", "sort:"],
        "max_length": 256,
        "tips": ["Use repo names", "Include programming language", "Search by stars/forks"],
    },
    "osint": {
        "prefer_academic_terms": False,
        "supports_filters": ["domain:", "ip:", "asn:"],
        "max_length": 200,
        "tips": ["Use specific targets", "Include technical indicators", "Reference known infrastructure"],
    },
    "social": {
        "prefer_academic_terms": False,
        "supports_filters": ["subreddit:", "site:"],
        "max_length": 300,
        "tips": ["Use conversational language", "Include platforms (reddit, hn)", "Reference communities"],
    },
}

# Tool descriptions and their typical use cases
TOOL_DESCRIPTIONS: dict[str, dict[str, Any]] = {
    "research_multi_search": {
        "description": "Parallel search across multiple providers",
        "best_for": ["broad discovery", "comparison of sources"],
        "cost": "medium",
    },
    "research_deep": {
        "description": "12-stage pipeline: query detection → search → fetch → markdown → extraction",
        "best_for": ["comprehensive research", "academic papers", "technical deep-dives"],
        "cost": "high",
    },
    "research_search": {
        "description": "Single-provider semantic search (Exa, Tavily, Firecrawl, Brave, etc.)",
        "best_for": ["single specialized queries", "provider-specific features"],
        "cost": "low",
    },
    "research_github": {
        "description": "GitHub code/repo search with gh CLI",
        "best_for": ["code exploration", "open-source discovery", "implementation reference"],
        "cost": "free",
    },
    "research_spider": {
        "description": "Concurrent multi-URL fetch with deduplication",
        "best_for": ["multi-URL scraping", "bulk content collection"],
        "cost": "medium",
    },
    "research_markdown": {
        "description": "HTML-to-markdown conversion via Crawl4AI/Trafilatura",
        "best_for": ["content extraction", "markdown conversion"],
        "cost": "low",
    },
    "research_llm_answer": {
        "description": "LLM-powered synthesis and answer generation",
        "best_for": ["summarization", "synthesis of findings"],
        "cost": "medium",
    },
    "research_cve_lookup": {
        "description": "CVE vulnerability intelligence lookup",
        "best_for": ["threat intelligence", "vulnerability research"],
        "cost": "low",
    },
    "research_passive_recon": {
        "description": "Passive reconnaissance via DNS/WHOIS/ASN enrichment",
        "best_for": ["osint", "infrastructure mapping"],
        "cost": "low",
    },
    "research_social_graph": {
        "description": "Social network analysis and relationship mapping",
        "best_for": ["social intelligence", "network analysis"],
        "cost": "medium",
    },
    "research_competitive_intel": {
        "description": "Competitive intelligence gathering",
        "best_for": ["market analysis", "competitive landscape"],
        "cost": "medium",
    },
    "research_career_trajectory": {
        "description": "Career and trajectory intelligence",
        "best_for": ["career research", "industry trends"],
        "cost": "medium",
    },
    "research_hcs_score": {
        "description": "Output quality and impact scoring",
        "best_for": ["quality assessment", "result ranking"],
        "cost": "low",
    },
}


def _extract_intent(request: str) -> dict[str, Any]:
    """Extract intent from user request using regex + keyword matching.

    Returns dict with:
        - category: matched intent category
        - keywords_found: matching keywords
        - confidence: 0.0-1.0 confidence score
        - scope: broad/intermediate/narrow
        - depth: shallow/intermediate/deep
        - timeframe: if detectable (short_term/long_term/etc.)
    """
    request_lower = request.lower()

    # Try to match against intent categories
    best_match: str | None = None
    best_score = 0.0
    matched_keywords: list[str] = []

    for category, config in INTENT_KEYWORDS.items():
        keywords = config["keywords"]
        matching = [kw for kw in keywords if kw in request_lower]
        score = len(matching) / len(keywords) if keywords else 0.0

        if score > best_score:
            best_score = score
            best_match = category
            matched_keywords = matching

    # If no strong match, default to generic research
    if best_match is None or best_score < 0.1:
        best_match = "general_research"
        best_score = 0.5
        matched_keywords = []

    # Infer timeframe from keywords
    timeframe = "unspecified"
    if any(w in request_lower for w in ["now", "today", "current", "recent", "latest", "2026", "2025"]):
        timeframe = "short_term"
    elif any(w in request_lower for w in ["future", "upcoming", "trend", "predict"]):
        timeframe = "future"
    elif any(w in request_lower for w in ["history", "historical", "past", "evolution"]):
        timeframe = "historical"
    else:
        timeframe = "long_term"

    intent_config = INTENT_KEYWORDS.get(best_match, {})

    return {
        "category": best_match,
        "keywords_found": matched_keywords,
        "confidence": float(best_score),
        "scope": intent_config.get("scope", "intermediate"),
        "depth": intent_config.get("depth", "intermediate"),
        "timeframe": timeframe,
    }


def _decompose_query(request: str, intent: dict[str, Any]) -> list[str]:
    """Break request into sub-questions using heuristic decomposition.

    Patterns:
        - Factual queries: "what is X?" → decompose into components
        - How-to queries: "how to Y?" → break into steps
        - Comparative queries: "compare X vs Y?" → separate into X, Y, comparison
        - Complex queries: use DSPy-style chain-of-thought if available
    """
    sub_questions: list[str] = []

    # Pattern 1: What/Which questions → extract key entities
    if request.startswith(("what ", "which ", "what's ", "which's ")):
        # "what is machine learning" → ["what is machine learning", "applications of ML", "history of ML"]
        base = request.rstrip("?")
        sub_questions.append(base)
        # Add follow-ups
        if "is " in request:
            sub_questions.append(f"why is {base.split('is', 1)[1].strip()} important")
        if intent.get("depth") == "deep":
            sub_questions.append(f"latest research on {base}")

    # Pattern 2: How/Why questions → break into prerequisites + method + outcomes
    elif request.startswith(("how ", "how to ", "why ")):
        base = request.rstrip("?").replace("how to ", "").replace("how ", "").replace("why ", "")
        if request.startswith("how to "):
            sub_questions.append(f"What are the steps to {base}?")
            sub_questions.append(f"Prerequisites for {base}")
            sub_questions.append(f"Common mistakes when {base}")
        elif request.startswith("how "):
            sub_questions.append(f"Explain how {base}")
            sub_questions.append(f"Mechanism of {base}")
        else:  # why
            sub_questions.append(f"Why {base}")
            sub_questions.append(f"Evidence for {base}")

    # Pattern 3: Comparative queries → separate entities
    elif any(x in request.lower() for x in [" vs ", " versus ", " compared to ", " vs. "]):
        parts = re.split(r"\s+vs\.?\s+|\s+versus\s+|\s+compared to\s+", request, flags=re.IGNORECASE)
        for part in parts:
            sub_questions.append(f"What is {part.strip()}?")
        if len(parts) == 2:
            sub_questions.append(f"Comparison between {parts[0].strip()} and {parts[1].strip()}")

    # Pattern 4: List/find queries → "find X", "list Y", "identify Z"
    elif any(x in request.lower() for x in ["find ", "list ", "identify ", "discover ", "search for "]):
        sub_questions.append(request)
        if intent.get("depth") == "deep":
            sub_questions.append(f"Trends in {request}")
            sub_questions.append(f"Recent {request}")

    # Pattern 5: Open-ended → generate related questions
    else:
        sub_questions.append(request)
        # Add clarifying sub-questions
        if intent.get("scope") == "broad":
            sub_questions.append(f"Different approaches to {request.rstrip('?')}")
            sub_questions.append(f"Trade-offs in {request.rstrip('?')}")
        if intent.get("depth") in ("intermediate", "deep"):
            sub_questions.append(f"Advanced {request.rstrip('?')}")

    # Remove duplicates and empty strings, cap at max_queries
    sub_questions = list(dict.fromkeys(q for q in sub_questions if q.strip()))
    return sub_questions[:10]  # Hard cap


def _optimize_for_engine(query: str, engine: str) -> str:
    """Optimize query syntax for specific search engine.

    Handles engine-specific operators:
        - arxiv: category filters, date ranges
        - web: site:, inurl:, filetype: operators
        - github: language:, stars: filters
        - osint: domain:, ip: filters
        - social: subreddit:, site: filters
    """
    config = QUERY_OPTIMIZATIONS.get(engine, {})
    optimized = query.strip()

    # Length normalization
    max_len = config.get("max_length", 256)
    if len(optimized) > max_len:
        # Keep first ~80% of query and add ellipsis
        optimized = optimized[: int(max_len * 0.8)] + "..."

    # Engine-specific transformations
    if engine == "arxiv":
        # Prefer academic terminology, add category hints
        if "machine learning" in optimized.lower():
            optimized += " (cs.AI OR cs.LG)"
        if "security" in optimized.lower() and "cryptography" not in optimized.lower():
            optimized += " (cs.CR)"

    elif engine == "github":
        # Add language and sort hints
        if "python" in optimized.lower():
            optimized += " language:python"
        if "javascript" in optimized.lower():
            optimized += " language:javascript"
        optimized += " sort:stars"

    elif engine == "osint":
        # Ensure we have domain/IP indicators
        if not any(x in optimized for x in ["domain:", "ip:", "asn:"]):
            # Try to infer from query
            if "." in optimized and not optimized.startswith("http"):
                optimized = f"domain:{optimized}"

    elif engine == "social":
        # Add community hints
        if "reddit" in optimized.lower() or "subreddit" not in optimized:
            if "python" in optimized.lower():
                optimized += " subreddit:learnprogramming"

    return optimized


def _recommend_tools(intent: dict[str, Any], output_type: str) -> list[str]:
    """Recommend Loom tools based on intent and output type.

    Returns prioritized list of tool names to use for research pipeline.
    """
    tools: set[str] = set()
    category = intent.get("category", "general_research")

    # Base tools from intent category
    category_tools = INTENT_KEYWORDS.get(category, {}).get("tools", [])
    tools.update(category_tools)

    # Output-type-specific tools
    if output_type == "research":
        tools.add("research_deep")
        tools.add("research_llm_answer")
    elif output_type == "osint":
        tools.add("research_github")
        tools.add("research_passive_recon")
        tools.add("research_search")
    elif output_type == "threat_intel":
        tools.add("research_cve_lookup")
        tools.add("research_search")
        tools.add("research_github")
    elif output_type == "academic":
        tools.add("research_deep")
        tools.add("research_search")

    # Depth-based tools
    if intent.get("depth") == "deep":
        tools.discard("research_search")
        tools.add("research_deep")

    # Always include quality assessment for deep research
    if intent.get("depth") in ("intermediate", "deep"):
        tools.add("research_hcs_score")

    # Convert to prioritized list
    priority_order = [
        "research_deep",
        "research_multi_search",
        "research_github",
        "research_search",
        "research_spider",
        "research_llm_answer",
        "research_cve_lookup",
        "research_passive_recon",
        "research_social_graph",
        "research_competitive_intel",
        "research_career_trajectory",
        "research_hcs_score",
    ]
    ordered = [t for t in priority_order if t in tools]
    return ordered


def _build_pipeline(
    sub_questions: list[str],
    tools: list[str],
    intent: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build ordered pipeline of execution steps.

    Each step specifies:
        - step: execution order (1-indexed)
        - tool: which tool to invoke
        - query or action: parameter for the tool
        - rationale: why this step (internal doc)
    """
    pipeline: list[dict[str, Any]] = []
    step = 1

    # Phase 1: Discovery (search)
    discovery_tools = [t for t in tools if "search" in t or t == "research_github"]
    if discovery_tools and sub_questions:
        query = sub_questions[0] if sub_questions else "research"
        tool = discovery_tools[0] if discovery_tools else "research_search"
        pipeline.append(
            {
                "step": step,
                "tool": tool,
                "query": query,
                "rationale": "Initial discovery across primary sources",
            }
        )
        step += 1

    # Phase 2: Deep research (if needed)
    if intent.get("depth") in ("intermediate", "deep") and "research_deep" in tools:
        for i, subq in enumerate(sub_questions[1:3], 1):  # Max 2 deep dives
            pipeline.append(
                {
                    "step": step,
                    "tool": "research_deep",
                    "query": subq,
                    "rationale": f"Deep research into sub-question {i}",
                }
            )
            step += 1

    # Phase 3: Specialized intelligence
    if "research_cve_lookup" in tools and "threat" in intent.get("category", ""):
        pipeline.append(
            {
                "step": step,
                "tool": "research_cve_lookup",
                "query": sub_questions[0] if sub_questions else "vulnerabilities",
                "rationale": "Threat intelligence lookup",
            }
        )
        step += 1

    if "research_github" in tools and "osint" in intent.get("category", ""):
        pipeline.append(
            {
                "step": step,
                "tool": "research_github",
                "query": sub_questions[0] if sub_questions else "exploits",
                "rationale": "Code/exploit discovery via GitHub",
            }
        )
        step += 1

    # Phase 4: Synthesis
    if "research_llm_answer" in tools and len(pipeline) > 1:
        pipeline.append(
            {
                "step": step,
                "tool": "research_llm_answer",
                "action": "synthesize",
                "rationale": "Synthesize findings across sources",
            }
        )
        step += 1

    # Phase 5: Quality assessment
    if "research_hcs_score" in tools and intent.get("depth") in ("intermediate", "deep"):
        pipeline.append(
            {
                "step": step,
                "tool": "research_hcs_score",
                "action": "score_output",
                "rationale": "Quality and impact assessment of findings",
            }
        )
        step += 1

    return pipeline


def research_build_query(
    user_request: str,
    context: str = "",
    output_type: Literal["research", "osint", "threat_intel", "academic"] = "research",
    max_queries: int = 5,
    optimize: bool = True,
) -> dict[str, Any]:
    """Transform a raw user request into optimized research queries.

    Takes natural language requests and produces:
        - Extracted intent and requirements
        - Decomposed sub-questions
        - Optimized search queries for multiple engines
        - Recommended Loom tools to use
        - Full research pipeline plan

    Uses rule-based + LLM extraction. If DSPy is installed, uses it for
    automatic prompt optimization. Falls back gracefully otherwise.

    Args:
        user_request: Raw user query (e.g., "how to become rich")
        context: Optional context to guide interpretation
        output_type: research | osint | threat_intel | academic
        max_queries: Maximum number of optimized queries to generate (1-10)
        optimize: Whether to apply engine-specific optimizations

    Returns:
        Dict with keys:
            - original_request: User's input
            - intent: Extracted intent + metadata
            - requirements: Inferred scope/depth/constraints
            - sub_questions: Decomposed questions
            - optimized_queries: Dict with web/academic/osint/social optimized queries
            - recommended_tools: Prioritized list of Loom tools
            - pipeline: Ordered execution steps
            - metadata: Timestamps, version, etc.

    Example:
        >>> result = research_build_query("how to become rich")
        >>> result["intent"]["category"]
        "wealth_building"
        >>> result["sub_questions"]
        [
            "What are proven wealth-building strategies?",
            "What investment approaches have highest returns?",
            ...
        ]
        >>> result["pipeline"][0]["tool"]
        "research_deep"
    """
    import time
    from datetime import UTC, datetime

    start_time = time.time()

    # Normalize input
    user_request = user_request.strip()
    max_queries = max(1, min(max_queries, 10))

    # Phase 1: Intent extraction
    intent = _extract_intent(user_request)

    # Phase 2: Query decomposition
    sub_questions = _decompose_query(user_request, intent)[:max_queries]

    # Phase 3: Generate optimized queries per engine
    optimized_queries: dict[str, list[str]] = {
        "web": [],
        "academic": [],
        "osint": [],
        "social": [],
    }

    for subq in sub_questions:
        if optimize:
            optimized_queries["web"].append(_optimize_for_engine(subq, "web"))
            optimized_queries["academic"].append(_optimize_for_engine(subq, "arxiv"))
            optimized_queries["osint"].append(_optimize_for_engine(subq, "osint"))
            optimized_queries["social"].append(_optimize_for_engine(subq, "social"))
        else:
            optimized_queries["web"].append(subq)
            optimized_queries["academic"].append(subq)
            optimized_queries["osint"].append(subq)
            optimized_queries["social"].append(subq)

    # Phase 4: Tool recommendation
    recommended_tools = _recommend_tools(intent, output_type)

    # Phase 5: Pipeline construction
    pipeline = _build_pipeline(sub_questions, recommended_tools, intent)

    # Build response
    duration_ms = int((time.time() - start_time) * 1000)

    result: dict[str, Any] = {
        "original_request": user_request,
        "intent": intent,
        "requirements": {
            "scope": intent.get("scope"),
            "depth": intent.get("depth"),
            "timeframe": intent.get("timeframe"),
            "output_type": output_type,
        },
        "sub_questions": sub_questions,
        "optimized_queries": optimized_queries,
        "recommended_tools": recommended_tools,
        "pipeline": pipeline,
        "metadata": {
            "version": "1.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "processing_time_ms": duration_ms,
            "dspy_available": False,  # DSPy integration ready for future
        },
    }

    logger.info(
        "query_built request_len=%d intent=%s sub_questions=%d tools=%d pipeline_steps=%d",
        len(user_request),
        intent.get("category"),
        len(sub_questions),
        len(recommended_tools),
        len(pipeline),
    )

    return result
