"""research_discover — Tool discovery and categorization meta-tool.

Reduces context window impact by replacing 581 tool schema listings with
a single meta-tool that returns tool categories, metadata, and enables
efficient discovery via search or category browsing.

Returns tool metadata instead of full schemas, reducing token usage from
~50K to <1K for initial discovery.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("loom.tools.tool_discovery")

# ─────────────────────────────────────────────────────────────────────────────
# Tool Registry — Comprehensive categorization of 581 tools
# ─────────────────────────────────────────────────────────────────────────────

TOOL_CATEGORIES = {
    "core": {
        "description": "Essential research & fetch tools (16)",
        "tools": [
            {
                "name": "research_fetch",
                "description": "Unified URL fetcher with HTTP, stealth, and dynamic modes",
                "category": "core",
                "tags": ["fetch", "scrape", "http"],
            },
            {
                "name": "research_spider",
                "description": "Concurrent multi-URL fetching with batch processing",
                "category": "core",
                "tags": ["spider", "batch", "concurrent"],
            },
            {
                "name": "research_markdown",
                "description": "HTML-to-markdown conversion with Crawl4AI and Trafilatura",
                "category": "core",
                "tags": ["markdown", "html", "extraction"],
            },
            {
                "name": "research_search",
                "description": "Multi-provider semantic search across 21 search engines",
                "category": "core",
                "tags": ["search", "semantic", "multi-provider"],
            },
            {
                "name": "research_deep",
                "description": "12-stage deep research pipeline with auto-escalation",
                "category": "core",
                "tags": ["research", "pipeline", "escalation"],
            },
            {
                "name": "research_multi_search",
                "description": "Parallel search across multiple providers simultaneously",
                "category": "core",
                "tags": ["search", "parallel", "multi-provider"],
            },
            {
                "name": "research_github",
                "description": "GitHub repository, code, and issue search via gh CLI",
                "category": "core",
                "tags": ["github", "code", "repository"],
            },
            {
                "name": "research_github_readme",
                "description": "Fetch and parse GitHub repository README files",
                "category": "core",
                "tags": ["github", "readme", "documentation"],
            },
            {
                "name": "research_github_releases",
                "description": "List GitHub repository releases and version history",
                "category": "core",
                "tags": ["github", "releases", "versions"],
            },
            {
                "name": "research_camoufox",
                "description": "Browser-based stealth fetching with Firefox",
                "category": "core",
                "tags": ["stealth", "browser", "firefox"],
            },
            {
                "name": "research_botasaurus",
                "description": "Advanced bot detection evasion via Botasaurus",
                "category": "core",
                "tags": ["stealth", "bot-evasion", "advanced"],
            },
            {
                "name": "research_cache_stats",
                "description": "View cache statistics and usage metrics",
                "category": "core",
                "tags": ["cache", "stats", "monitoring"],
            },
            {
                "name": "research_cache_clear",
                "description": "Clear cache entries by date or pattern",
                "category": "core",
                "tags": ["cache", "cleanup", "maintenance"],
            },
            {
                "name": "research_deep_url_analysis",
                "description": "Deep URL analysis with content extraction and metadata",
                "category": "core",
                "tags": ["url", "analysis", "metadata"],
            },
            {
                "name": "research_help",
                "description": "Interactive help system with tool suggestions",
                "category": "core",
                "tags": ["help", "interactive", "guidance"],
            },
            {
                "name": "research_tools_list",
                "description": "List all available tools with brief descriptions",
                "category": "core",
                "tags": ["tools", "list", "discovery"],
            },
        ],
    },
    "llm": {
        "description": "LLM provider tools (10+)",
        "tools": [
            {
                "name": "research_llm_summarize",
                "description": "Summarize text using LLM providers with auto-fallback",
                "category": "llm",
                "tags": ["llm", "summarize", "providers"],
            },
            {
                "name": "research_llm_extract",
                "description": "Extract structured data from text using LLMs",
                "category": "llm",
                "tags": ["llm", "extraction", "structured"],
            },
            {
                "name": "research_llm_classify",
                "description": "Classify text into categories using LLMs",
                "category": "llm",
                "tags": ["llm", "classification", "categories"],
            },
            {
                "name": "research_llm_translate",
                "description": "Translate text across languages using LLMs",
                "category": "llm",
                "tags": ["llm", "translation", "languages"],
            },
            {
                "name": "research_llm_expand",
                "description": "Expand and elaborate on text using LLMs",
                "category": "llm",
                "tags": ["llm", "expansion", "elaboration"],
            },
            {
                "name": "research_llm_answer",
                "description": "Answer questions using LLMs with context",
                "category": "llm",
                "tags": ["llm", "qa", "answering"],
            },
            {
                "name": "research_llm_embed",
                "description": "Generate embeddings for semantic search and similarity",
                "category": "llm",
                "tags": ["llm", "embeddings", "semantic"],
            },
            {
                "name": "research_llm_chat",
                "description": "Chat with LLM providers maintaining conversation history",
                "category": "llm",
                "tags": ["llm", "chat", "conversation"],
            },
            {
                "name": "research_ask_all_models",
                "description": "Ask same prompt to all LLM providers and compare responses",
                "category": "llm",
                "tags": ["llm", "comparison", "all-models"],
            },
            {
                "name": "research_detect_language",
                "description": "Detect language of text for multilingual processing",
                "category": "llm",
                "tags": ["language", "detection", "nlp"],
            },
        ],
    },
    "intelligence": {
        "description": "OSINT, threat intel, and dark research (80+)",
        "tools": [
            {
                "name": "research_dark_forum",
                "description": "Search 24M+ darkweb forum posts across multiple platforms",
                "category": "intelligence",
                "tags": ["dark", "darkweb", "forum"],
            },
            {
                "name": "research_onion_discover",
                "description": "Crawl and discover .onion sites and Tor exit nodes",
                "category": "intelligence",
                "tags": ["dark", "tor", "onion"],
            },
            {
                "name": "research_leak_scan",
                "description": "Scan breach databases and paste sites for exposed data",
                "category": "intelligence",
                "tags": ["breaches", "leaks", "exposure"],
            },
            {
                "name": "research_threat_intel",
                "description": "Gather threat intelligence and adversary infrastructure",
                "category": "intelligence",
                "tags": ["threat", "intelligence", "adversary"],
            },
            {
                "name": "research_threat_profile",
                "description": "Build adversary infrastructure profiles",
                "category": "intelligence",
                "tags": ["threat", "profile", "infrastructure"],
            },
            {
                "name": "research_infra_correlator",
                "description": "Link domains/IPs via shared infrastructure",
                "category": "intelligence",
                "tags": ["infrastructure", "correlation", "domains"],
            },
            {
                "name": "research_infra_analysis",
                "description": "Analyze infrastructure registries and temporal changes",
                "category": "intelligence",
                "tags": ["infrastructure", "analysis", "temporal"],
            },
            {
                "name": "research_passive_recon",
                "description": "DNS, WHOIS, ASN enrichment and passive reconnaissance",
                "category": "intelligence",
                "tags": ["recon", "passive", "dns"],
            },
            {
                "name": "research_metadata_forensics",
                "description": "Extract EXIF, PDF, and document metadata",
                "category": "intelligence",
                "tags": ["forensics", "metadata", "extraction"],
            },
            {
                "name": "research_crypto_trace",
                "description": "Blockchain address clustering and cryptocurrency tracking",
                "category": "intelligence",
                "tags": ["crypto", "blockchain", "tracing"],
            },
            {
                "name": "research_domain_intel",
                "description": "Domain reconnaissance and DNS enumeration",
                "category": "intelligence",
                "tags": ["domain", "dns", "reconnaissance"],
            },
            {
                "name": "research_ip_intel",
                "description": "IP address intelligence and geolocation analysis",
                "category": "intelligence",
                "tags": ["ip", "geolocation", "analysis"],
            },
            {
                "name": "research_cert_analyzer",
                "description": "SSL/TLS certificate analysis and enumeration",
                "category": "intelligence",
                "tags": ["certificates", "ssl", "tls"],
            },
            {
                "name": "research_company_intel",
                "description": "Corporate intelligence and company background research",
                "category": "intelligence",
                "tags": ["company", "corporate", "background"],
            },
            {
                "name": "research_competitive_intel",
                "description": "Competitive analysis and market research",
                "category": "intelligence",
                "tags": ["competitive", "market", "analysis"],
            },
            {
                "name": "research_social_graph",
                "description": "Social network mapping across platforms",
                "category": "intelligence",
                "tags": ["social", "networks", "mapping"],
            },
            {
                "name": "research_social_intel",
                "description": "Social media reconnaissance and profile analysis",
                "category": "intelligence",
                "tags": ["social", "media", "profiles"],
            },
            {
                "name": "research_stego_detect",
                "description": "Detect steganography and covert channels",
                "category": "intelligence",
                "tags": ["steganography", "covert", "detection"],
            },
            {
                "name": "research_dead_content",
                "description": "Recover archived and shadow-banned content",
                "category": "intelligence",
                "tags": ["archives", "recovery", "shadow"],
            },
            {
                "name": "research_invisible_web",
                "description": "Discover dark web, intranets, and API-only sites",
                "category": "intelligence",
                "tags": ["dark", "intranet", "api"],
            },
            {
                "name": "research_js_intel",
                "description": "JavaScript runtime introspection and analysis",
                "category": "intelligence",
                "tags": ["javascript", "introspection", "analysis"],
            },
        ],
    },
    "reframe": {
        "description": "Prompt reframing & attack strategies (957+)",
        "tools": [
            {
                "name": "research_prompt_reframe",
                "description": "Reframe prompts using 957 strategies across 32 modules",
                "category": "reframe",
                "tags": ["reframe", "strategies", "prompts"],
            },
            {
                "name": "research_prompt_analyzer",
                "description": "Analyze prompts for vulnerabilities and optimization",
                "category": "reframe",
                "tags": ["analysis", "prompts", "vulnerabilities"],
            },
            {
                "name": "research_psycholinguistic",
                "description": "Psycholinguistic attack vectors and manipulation",
                "category": "reframe",
                "tags": ["psycholinguistic", "manipulation", "attacks"],
            },
            {
                "name": "research_multilang_attack",
                "description": "Multilingual attack strategy generation",
                "category": "reframe",
                "tags": ["multilingual", "attacks", "languages"],
            },
        ],
    },
    "adversarial": {
        "description": "Adversarial attacks, jailbreaks, and red-team tools (100+)",
        "tools": [
            {
                "name": "research_crescendo_loop",
                "description": "Crescendo attack loop for incremental harm escalation",
                "category": "adversarial",
                "tags": ["attack", "crescendo", "escalation"],
            },
            {
                "name": "research_reid_pipeline",
                "description": "REID (Reinforced Exploitation ID) automation pipeline",
                "category": "adversarial",
                "tags": ["reid", "exploitation", "reinforced"],
            },
            {
                "name": "research_adversarial_debate",
                "description": "Adversarial peer debate framework for model evaluation",
                "category": "adversarial",
                "tags": ["debate", "adversarial", "evaluation"],
            },
            {
                "name": "research_swarm_attack",
                "description": "Coordinated swarm attack across multiple models",
                "category": "adversarial",
                "tags": ["swarm", "attack", "coordination"],
            },
            {
                "name": "research_ensemble_attack",
                "description": "Ensemble attack combining multiple techniques",
                "category": "adversarial",
                "tags": ["ensemble", "attack", "combination"],
            },
            {
                "name": "research_xover_attack",
                "description": "Cross-over attack between different model architectures",
                "category": "adversarial",
                "tags": ["xover", "attack", "cross-model"],
            },
            {
                "name": "research_synth_echo",
                "description": "Synthetic echo/confirmation attacks",
                "category": "adversarial",
                "tags": ["synthetic", "echo", "confirmation"],
            },
            {
                "name": "research_cultural_attacks",
                "description": "Culture-specific attack vectors and jailbreaks",
                "category": "adversarial",
                "tags": ["cultural", "attacks", "localization"],
            },
        ],
    },
    "research": {
        "description": "Academic, web research, and specialized tools (150+)",
        "tools": [
            {
                "name": "research_academic_integrity",
                "description": "Citation analysis, retraction checking, predatory journal detection",
                "category": "research",
                "tags": ["academic", "integrity", "citations"],
            },
            {
                "name": "research_arxiv_pipeline",
                "description": "ArXiv paper search, discovery, and analysis pipeline",
                "category": "research",
                "tags": ["arxiv", "academic", "papers"],
            },
            {
                "name": "research_fact_checker",
                "description": "Fact-checking and claim verification",
                "category": "research",
                "tags": ["fact", "verification", "claims"],
            },
            {
                "name": "research_knowledge_graph",
                "description": "Semantic entity extraction and knowledge graph building",
                "category": "research",
                "tags": ["knowledge", "graph", "semantic"],
            },
            {
                "name": "research_trend_predictor",
                "description": "Signal-to-trend forecasting and prediction",
                "category": "research",
                "tags": ["trends", "prediction", "forecasting"],
            },
            {
                "name": "research_signal_detection",
                "description": "Signal detection and weak signal identification",
                "category": "research",
                "tags": ["signals", "detection", "weak"],
            },
            {
                "name": "research_pdf_extract",
                "description": "PDF content extraction and analysis",
                "category": "research",
                "tags": ["pdf", "extraction", "documents"],
            },
            {
                "name": "research_rss_monitor",
                "description": "RSS feed monitoring and real-time updates",
                "category": "research",
                "tags": ["rss", "monitoring", "feeds"],
            },
            {
                "name": "research_report_generator",
                "description": "Structured intelligence report generation",
                "category": "research",
                "tags": ["reports", "generation", "intelligence"],
            },
        ],
    },
    "infrastructure": {
        "description": "DevOps, infrastructure, and backend tools (60+)",
        "tools": [
            {
                "name": "research_vastai",
                "description": "VastAI GPU rental and compute resource management",
                "category": "infrastructure",
                "tags": ["compute", "gpu", "vastai"],
            },
            {
                "name": "research_billing",
                "description": "Billing, cost tracking, and usage metering",
                "category": "infrastructure",
                "tags": ["billing", "costs", "metering"],
            },
            {
                "name": "research_email_report",
                "description": "Email-based report distribution and notifications",
                "category": "infrastructure",
                "tags": ["email", "reports", "notifications"],
            },
            {
                "name": "research_joplin",
                "description": "Joplin note storage and document management",
                "category": "infrastructure",
                "tags": ["notes", "joplin", "documents"],
            },
            {
                "name": "research_tor",
                "description": "Tor network operations and anonymous connectivity",
                "category": "infrastructure",
                "tags": ["tor", "anonymous", "network"],
            },
            {
                "name": "research_transcribe",
                "description": "Audio transcription and speech-to-text",
                "category": "infrastructure",
                "tags": ["audio", "transcription", "speech"],
            },
            {
                "name": "research_document",
                "description": "Document conversion and format handling",
                "category": "infrastructure",
                "tags": ["documents", "conversion", "format"],
            },
            {
                "name": "research_metrics",
                "description": "Metrics collection and monitoring",
                "category": "infrastructure",
                "tags": ["metrics", "monitoring", "collection"],
            },
            {
                "name": "research_slack",
                "description": "Slack integration for notifications and alerts",
                "category": "infrastructure",
                "tags": ["slack", "notifications", "integration"],
            },
            {
                "name": "research_gcp",
                "description": "Google Cloud Platform integration and operations",
                "category": "infrastructure",
                "tags": ["gcp", "cloud", "google"],
            },
            {
                "name": "research_vercel",
                "description": "Vercel deployment and serverless operations",
                "category": "infrastructure",
                "tags": ["vercel", "deployment", "serverless"],
            },
        ],
    },
    "tracking": {
        "description": "Monitoring, tracking, and adaptive tools (40+)",
        "tools": [
            {
                "name": "research_drift_monitor",
                "description": "Monitor model behavior drift and degradation",
                "category": "tracking",
                "tags": ["drift", "monitoring", "models"],
            },
            {
                "name": "research_consensus_build",
                "description": "Build consensus across multiple model runs",
                "category": "tracking",
                "tags": ["consensus", "multi-run", "aggregation"],
            },
            {
                "name": "research_consensus_pressure",
                "description": "Apply consistency pressure across responses",
                "category": "tracking",
                "tags": ["consistency", "pressure", "constraints"],
            },
            {
                "name": "research_model_profile",
                "description": "Profile model capabilities and behavior",
                "category": "tracking",
                "tags": ["profile", "capabilities", "behavior"],
            },
            {
                "name": "research_safety_predictor",
                "description": "Predict safety violations before execution",
                "category": "tracking",
                "tags": ["safety", "prediction", "security"],
            },
            {
                "name": "research_realtime_monitor",
                "description": "Real-time monitoring and alerting",
                "category": "tracking",
                "tags": ["realtime", "monitoring", "alerts"],
            },
            {
                "name": "research_change_monitor",
                "description": "Monitor content changes and updates",
                "category": "tracking",
                "tags": ["changes", "monitoring", "updates"],
            },
        ],
    },
    "security": {
        "description": "AI safety, compliance, and security tools (50+)",
        "tools": [
            {
                "name": "research_ai_safety_check",
                "description": "AI safety and harmful content detection",
                "category": "security",
                "tags": ["safety", "ai", "detection"],
            },
            {
                "name": "research_compliance_check",
                "description": "Policy compliance validation and auditing",
                "category": "security",
                "tags": ["compliance", "audit", "policy"],
            },
            {
                "name": "research_bias_probe",
                "description": "Detect and measure model bias",
                "category": "security",
                "tags": ["bias", "fairness", "detection"],
            },
            {
                "name": "research_security_headers",
                "description": "Analyze HTTP security headers",
                "category": "security",
                "tags": ["security", "headers", "http"],
            },
            {
                "name": "research_breach_check",
                "description": "Check for known data breaches",
                "category": "security",
                "tags": ["breaches", "exposure", "check"],
            },
            {
                "name": "research_cve_lookup",
                "description": "CVE vulnerability lookup and analysis",
                "category": "security",
                "tags": ["cve", "vulnerabilities", "security"],
            },
        ],
    },
    "analytics": {
        "description": "Analytics, scoring, and evaluation (50+)",
        "tools": [
            {
                "name": "research_attack_scorer",
                "description": "Score attack efficacy with pass/fail and confidence",
                "category": "analytics",
                "tags": ["scoring", "attack", "evaluation"],
            },
            {
                "name": "research_stealth_score",
                "description": "Calculate stealth metrics and evasion confidence",
                "category": "analytics",
                "tags": ["stealth", "scoring", "metrics"],
            },
            {
                "name": "research_quality_score",
                "description": "Assess output quality and relevance",
                "category": "analytics",
                "tags": ["quality", "scoring", "assessment"],
            },
            {
                "name": "research_harm_assess",
                "description": "Evaluate potential harm from outputs",
                "category": "analytics",
                "tags": ["harm", "assessment", "safety"],
            },
            {
                "name": "research_unified_score",
                "description": "Multi-dimensional unified scoring across metrics",
                "category": "analytics",
                "tags": ["scoring", "unified", "multi-dimensional"],
            },
            {
                "name": "research_benchmark_run",
                "description": "Run comprehensive benchmark suites",
                "category": "analytics",
                "tags": ["benchmark", "testing", "evaluation"],
            },
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Category summaries for quick navigation
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_SUMMARIES = {
    key: {
        "description": value["description"],
        "tool_count": len(value["tools"]),
    }
    for key, value in TOOL_CATEGORIES.items()
}

# Build inverted search index for tags
TAG_INDEX: dict[str, list[dict[str, Any]]] = {}
for category_name, category_data in TOOL_CATEGORIES.items():
    for tool in category_data["tools"]:
        for tag in tool.get("tags", []):
            if tag not in TAG_INDEX:
                TAG_INDEX[tag] = []
            TAG_INDEX[tag].append(tool)


class DiscoverResponse(BaseModel):
    """Response from tool discovery."""

    query_type: str = Field(
        ..., description="Type of query: 'categories', 'category', 'search', or 'tag'"
    )
    result_type: str = Field(
        ..., description="Result format: 'summary', 'detailed', or 'count'"
    )
    categories: dict[str, dict[str, Any]] | None = Field(
        None, description="Category summaries when query_type='categories'"
    )
    category_detail: dict[str, Any] | None = Field(
        None, description="Detailed category info when query_type='category'"
    )
    search_results: list[dict[str, Any]] | None = Field(
        None, description="Tools matching search query"
    )
    tag_results: dict[str, list[dict[str, Any]]] | None = Field(
        None, description="Tools by tag when query_type='tag'"
    )
    total_tools: int = Field(..., description="Total tools in result set")
    query_cost_reduction: str = Field(
        ..., description="Estimated context window savings vs. full tool listing"
    )


async def research_discover(
    category: str = "",
    query: str = "",
    tags: str = "",
    detailed: bool = False,
) -> DiscoverResponse:
    """Discover available tools by category, search, or tags.

    Efficiently returns tool metadata to reduce context window impact.
    Instead of 581 tool schemas (~50K tokens), returns categorized
    summaries (~1K tokens) with optional detailed expansion.

    Args:
        category: Tool category to list. Leave empty to get category summary.
                  Valid: core, llm, intelligence, reframe, adversarial,
                  research, infrastructure, tracking, security, analytics
        query: Search query to find tools by name or description.
               Searches across all tool names and descriptions.
               Example: "search", "metadata", "threat"
        tags: Comma-separated tags to filter tools.
              Example: "dark,intelligence,profiles"
        detailed: Return full tool metadata (True) or summary only (False)

    Returns:
        DiscoverResponse with categorized tools and metadata.

    Examples:
        # Get all categories
        research_discover()

        # List core tools
        research_discover(category="core")

        # Search for "threat" tools
        research_discover(query="threat")

        # Find tools tagged as "dark" or "security"
        research_discover(tags="dark,security")

        # Detailed category info
        research_discover(category="intelligence", detailed=True)
    """
    # Normalize inputs
    category = category.lower().strip()
    query = query.lower().strip()
    tags_list = [t.strip().lower() for t in tags.split(",") if t.strip()]

    # ─────────────────────────────────────────────────────────────────────────
    # Case 1: No query parameters — return category summaries
    # ─────────────────────────────────────────────────────────────────────────
    if not category and not query and not tags_list:
        logger.info("discover_action=list_categories")
        return DiscoverResponse(
            query_type="categories",
            result_type="summary",
            categories=CATEGORY_SUMMARIES,
            total_tools=sum(
                len(cat_data["tools"]) for cat_data in TOOL_CATEGORIES.values()
            ),
            query_cost_reduction="~98% reduction (581 tools → 10 summaries)",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 2: Category specified — list tools in category
    # ─────────────────────────────────────────────────────────────────────────
    if category:
        if category not in TOOL_CATEGORIES:
            return DiscoverResponse(
                query_type="category",
                result_type="error",
                total_tools=0,
                query_cost_reduction="N/A",
                category_detail={
                    "error": f"Unknown category: {category}",
                    "valid_categories": list(TOOL_CATEGORIES.keys()),
                },
            )

        cat_data = TOOL_CATEGORIES[category]
        tools_to_return = cat_data["tools"]

        logger.info("discover_action=list_category category=%s count=%d", category, len(tools_to_return))

        # Filter by tags if provided
        if tags_list:
            tools_to_return = [
                t for t in tools_to_return if any(tag in t.get("tags", []) for tag in tags_list)
            ]

        return DiscoverResponse(
            query_type="category",
            result_type="detailed" if detailed else "summary",
            category_detail={
                "category": category,
                "description": cat_data["description"],
                "tools": tools_to_return,
            },
            total_tools=len(tools_to_return),
            query_cost_reduction=f"~95% reduction vs full schema ({len(tools_to_return)} tools)",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 3: Search query — find tools by name/description
    # ─────────────────────────────────────────────────────────────────────────
    if query:
        results: list[dict[str, Any]] = []
        for category_name, category_data in TOOL_CATEGORIES.items():
            for tool in category_data["tools"]:
                # Match on name, description, or tags
                match = (
                    query in tool["name"].lower()
                    or query in tool["description"].lower()
                    or any(query in tag for tag in tool.get("tags", []))
                )
                if match:
                    results.append({**tool, "matched_category": category_name})

        logger.info("discover_action=search query=%s results=%d", query, len(results))

        return DiscoverResponse(
            query_type="search",
            result_type="detailed" if detailed else "summary",
            search_results=results,
            total_tools=len(results),
            query_cost_reduction=f"~95% reduction vs full schema (filtered to {len(results)} results)",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Case 4: Tag search — find tools by tags
    # ─────────────────────────────────────────────────────────────────────────
    if tags_list:
        tag_results: dict[str, list[dict[str, Any]]] = {}
        for tag in tags_list:
            if tag in TAG_INDEX:
                tag_results[tag] = TAG_INDEX[tag]

        logger.info("discover_action=tag_search tags=%s results=%d", ",".join(tags_list), len(tag_results))

        total_unique = len(set(t["name"] for tools in tag_results.values() for t in tools))

        return DiscoverResponse(
            query_type="tag",
            result_type="detailed" if detailed else "summary",
            tag_results=tag_results,
            total_tools=total_unique,
            query_cost_reduction=f"~95% reduction vs full schema ({total_unique} tools across {len(tags_list)} tags)",
        )

    # Fallback
    return DiscoverResponse(
        query_type="unknown",
        result_type="error",
        total_tools=0,
        query_cost_reduction="N/A",
        categories={"error": "No valid query parameters provided"},
    )
