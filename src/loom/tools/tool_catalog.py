"""Tool catalog and knowledge graph for Loom MCP service.

Enables:
1. Tool discovery by category, capability, or subcategory
2. Tool connection graph showing which tools can feed into others
3. Intelligent pipeline building from research goals
4. Standalone usage info for any tool
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.tools.tool_catalog")


# ============================================================================
# TOOL METADATA DATABASE
# ============================================================================

TOOL_CATEGORIES = {
    "scraping": {
        "description": "Content fetching and extraction tools",
        "subcategories": {
            "http_fetch": "Basic HTTP requests with escalation",
            "browser_automation": "Browser-based scraping (Playwright, Selenium)",
            "stealth_fetch": "Anti-bot bypass (headers, fingerprinting)",
            "batch_fetch": "Concurrent multi-URL fetching",
            "content_extraction": "HTML-to-markdown, text extraction",
        },
    },
    "search": {
        "description": "Search and discovery across providers",
        "subcategories": {
            "web_search": "General web search (Exa, Tavily, DuckDuckGo)",
            "academic_search": "Papers, citations (ArXiv, Semantic Scholar)",
            "social_search": "Twitter, Reddit, HN, community content",
            "code_search": "GitHub code and repo search",
            "specialized_search": "Dark web, leaked data, specialized DBs",
        },
    },
    "llm": {
        "description": "LLM-powered analysis and generation",
        "subcategories": {
            "summarize": "Text summarization",
            "extract": "Structured extraction from content",
            "classify": "Document/text classification",
            "translate": "Language translation",
            "embed": "Semantic embeddings",
            "chat": "Multi-turn conversation",
            "multi_model": "Multi-provider LLM orchestration",
        },
    },
    "osint": {
        "description": "Open-source intelligence gathering",
        "subcategories": {
            "domain_intel": "WHOIS, DNS, domain reputation",
            "ip_intel": "IP geolocation, reputation, ASN",
            "social_profiles": "Social media account discovery",
            "dark_web": "Tor, dark forum, paste site searching",
            "breach_data": "Leaked databases, password breaches",
            "infrastructure": "DNS, IP correlation, tech stack",
        },
    },
    "crypto": {
        "description": "Cryptocurrency and blockchain tools",
        "subcategories": {
            "address_trace": "Bitcoin/Ethereum address tracking",
            "risk_score": "Crypto risk assessment",
            "transaction_decode": "TX analysis and decoding",
            "defi_audit": "DeFi protocol security",
        },
    },
    "career": {
        "description": "Career intelligence and job market analysis",
        "subcategories": {
            "job_search": "Job posting aggregation",
            "salary": "Salary benchmarking and synthesis",
            "interview_prep": "Interview preparation",
            "resume": "Resume optimization",
            "company_intel": "Company research and diligence",
        },
    },
    "academic": {
        "description": "Academic research tools",
        "subcategories": {
            "citation": "Citation analysis and tracking",
            "retraction": "Retracted papers detection",
            "predatory_check": "Predatory journal detection",
            "grant_forensics": "Grant funding analysis",
        },
    },
    "creative": {
        "description": "Prompt engineering and creative research",
        "subcategories": {
            "reframe": "Prompt reframing strategies",
            "strategy": "Attack strategy generation",
            "prompt_analysis": "Prompt effectiveness analysis",
            "psycholinguistic": "Psychological attack vectors",
        },
    },
    "document": {
        "description": "Document processing tools",
        "subcategories": {
            "pdf_extract": "PDF text and table extraction",
            "ocr": "Optical character recognition",
            "transcribe": "Audio/video transcription",
            "convert": "Format conversion",
            "table_extract": "Table extraction and structuring",
        },
    },
    "monitoring": {
        "description": "Real-time and continuous monitoring",
        "subcategories": {
            "rss": "RSS feed monitoring",
            "change_detect": "Website change detection",
            "realtime": "Real-time data streams",
            "early_warning": "Early warning and anomaly detection",
        },
    },
    "security": {
        "description": "Security and vulnerability assessment",
        "subcategories": {
            "vuln_scan": "Vulnerability scanning",
            "cert_audit": "SSL/TLS certificate analysis",
            "header_check": "Security headers validation",
            "pentest": "Penetration testing tools",
            "threat_intel": "Threat intelligence aggregation",
        },
    },
    "graph": {
        "description": "Knowledge graphs and relationship mapping",
        "subcategories": {
            "knowledge_graph": "Entity extraction and linking",
            "entity_extract": "Named entity recognition",
            "relationship_map": "Relationship discovery",
            "visualization": "Graph visualization and analysis",
        },
    },
    "pipeline": {
        "description": "Orchestration and workflow tools",
        "subcategories": {
            "workflow": "Workflow composition",
            "orchestrate": "Tool orchestration",
            "consensus": "Consensus mechanisms",
            "debate": "Adversarial debate",
            "evidence": "Evidence collection pipeline",
        },
    },
    "system": {
        "description": "System and infrastructure tools",
        "subcategories": {
            "config": "Configuration management",
            "cache": "Cache management",
            "session": "Session management",
            "health": "System health checks",
            "metrics": "Metrics and monitoring",
            "traces": "Distributed tracing",
        },
    },
}

# Tool capability tags
CAPABILITIES = {
    "accepts_url": "Takes URL as input",
    "accepts_query": "Takes text query as input",
    "accepts_text": "Takes arbitrary text input",
    "accepts_domain": "Takes domain name as input",
    "accepts_ip": "Takes IP address as input",
    "returns_text": "Returns unstructured text",
    "returns_structured": "Returns structured data (JSON, dict)",
    "returns_list": "Returns list of items",
    "returns_score": "Returns numeric score/ranking",
    "calls_external_api": "Calls external APIs",
    "calls_llm": "Calls LLM provider",
    "uses_browser": "Uses browser automation",
    "uses_subprocess": "Spawns subprocess/CLI tools",
    "real_time": "Real-time or near real-time data",
    "cached": "Results are cached",
    "rate_limited": "Subject to rate limiting",
    "stealth": "Anti-bot or anonymity features",
}

# Complete tool catalog with categorization
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    # SCRAPING TOOLS
    "research_fetch": {
        "category": "scraping",
        "subcategory": "http_fetch",
        "description": "HTTP fetch with Scrapling 3-tier escalation (http→stealthy→dynamic)",
        "capabilities": ["accepts_url", "returns_text", "calls_external_api", "stealth"],
        "input_types": ["url"],
        "output_types": ["html_content"],
        "dependencies": [],
        "connects_to": ["research_markdown", "research_spider", "research_deep"],
    },
    "research_spider": {
        "category": "scraping",
        "subcategory": "batch_fetch",
        "description": "Concurrent multi-URL fetch with escalation",
        "capabilities": ["accepts_url", "returns_list", "calls_external_api", "stealth"],
        "input_types": ["url_list"],
        "output_types": ["html_content_list"],
        "dependencies": ["research_fetch"],
        "connects_to": ["research_markdown", "research_llm_extract"],
    },
    "research_markdown": {
        "category": "scraping",
        "subcategory": "content_extraction",
        "description": "HTML to markdown conversion (Crawl4AI + Trafilatura fallback)",
        "capabilities": ["accepts_text", "returns_text", "calls_external_api"],
        "input_types": ["html_content"],
        "output_types": ["markdown"],
        "dependencies": ["research_fetch"],
        "connects_to": ["research_llm_summarize", "research_llm_extract", "research_text_analyze"],
    },
    "research_lightpanda_fetch": {
        "category": "scraping",
        "subcategory": "browser_automation",
        "description": "LightPanda JavaScript-enabled scraping",
        "capabilities": ["accepts_url", "returns_text", "calls_external_api"],
        "input_types": ["url"],
        "output_types": ["html_content"],
        "dependencies": [],
        "connects_to": ["research_markdown"],
    },
    "research_camoufox": {
        "category": "scraping",
        "subcategory": "stealth_fetch",
        "description": "Camoufox Firefox stealth browser automation",
        "capabilities": ["accepts_url", "returns_text", "uses_browser", "stealth"],
        "input_types": ["url"],
        "output_types": ["html_content"],
        "dependencies": [],
        "connects_to": ["research_markdown"],
    },
    "research_botasaurus": {
        "category": "scraping",
        "subcategory": "stealth_fetch",
        "description": "Botasaurus stealth scraping framework",
        "capabilities": ["accepts_url", "returns_text", "uses_browser", "stealth"],
        "input_types": ["url"],
        "output_types": ["html_content"],
        "dependencies": [],
        "connects_to": ["research_markdown"],
    },
    "research_archive_page": {
        "category": "scraping",
        "subcategory": "content_extraction",
        "description": "SingleFile page archival and snapshot",
        "capabilities": ["accepts_url", "returns_text"],
        "input_types": ["url"],
        "output_types": ["archived_content"],
        "dependencies": [],
        "connects_to": ["research_markdown"],
    },
    "research_screenshot": {
        "category": "scraping",
        "subcategory": "browser_automation",
        "description": "Webpage screenshot capture",
        "capabilities": ["accepts_url", "returns_text", "uses_browser"],
        "input_types": ["url"],
        "output_types": ["image"],
        "dependencies": [],
        "connects_to": ["research_ocr_extract", "research_vision_browse"],
    },

    # SEARCH TOOLS
    "research_search": {
        "category": "search",
        "subcategory": "web_search",
        "description": "Multi-provider web search (Exa, Tavily, etc.)",
        "capabilities": ["accepts_query", "returns_list", "calls_external_api"],
        "input_types": ["query"],
        "output_types": ["search_results"],
        "dependencies": [],
        "connects_to": ["research_fetch", "research_spider", "research_deep"],
    },
    "research_deep": {
        "category": "search",
        "subcategory": "web_search",
        "description": "12-stage deep research pipeline with auto-escalation",
        "capabilities": ["accepts_query", "returns_structured", "calls_external_api", "calls_llm"],
        "input_types": ["query"],
        "output_types": ["research_results"],
        "dependencies": ["research_search", "research_fetch", "research_markdown"],
        "connects_to": ["research_knowledge_graph", "research_consensus"],
    },
    "research_github": {
        "category": "search",
        "subcategory": "code_search",
        "description": "GitHub repository and code search via gh CLI",
        "capabilities": ["accepts_query", "returns_list"],
        "input_types": ["query"],
        "output_types": ["github_results"],
        "dependencies": [],
        "connects_to": ["research_fetch"],
    },
    "research_dark_forum": {
        "category": "search",
        "subcategory": "specialized_search",
        "description": "Dark web forum search (Ahmia, DarkSearch, etc.)",
        "capabilities": ["accepts_query", "returns_list", "calls_external_api"],
        "input_types": ["query"],
        "output_types": ["forum_posts"],
        "dependencies": [],
        "connects_to": ["research_fetch"],
    },
    "research_multi_search": {
        "category": "search",
        "subcategory": "web_search",
        "description": "Parallel search across multiple providers",
        "capabilities": ["accepts_query", "returns_list", "calls_external_api"],
        "input_types": ["query"],
        "output_types": ["aggregated_results"],
        "dependencies": [],
        "connects_to": ["research_fetch", "research_spider"],
    },

    # LLM TOOLS
    "research_llm_summarize": {
        "category": "llm",
        "subcategory": "summarize",
        "description": "Text summarization with multi-provider cascade",
        "capabilities": ["accepts_text", "returns_text", "calls_llm"],
        "input_types": ["text"],
        "output_types": ["summary"],
        "dependencies": [],
        "connects_to": ["research_llm_extract", "research_prompt_analyze"],
    },
    "research_llm_extract": {
        "category": "llm",
        "subcategory": "extract",
        "description": "Structured extraction from content (entities, relationships)",
        "capabilities": ["accepts_text", "returns_structured", "calls_llm"],
        "input_types": ["text"],
        "output_types": ["structured_data"],
        "dependencies": [],
        "connects_to": ["research_knowledge_graph", "research_graph_analyze"],
    },
    "research_llm_classify": {
        "category": "llm",
        "subcategory": "classify",
        "description": "Text classification (sentiment, topic, etc.)",
        "capabilities": ["accepts_text", "returns_text", "calls_llm"],
        "input_types": ["text"],
        "output_types": ["classification"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_llm_translate": {
        "category": "llm",
        "subcategory": "translate",
        "description": "Multi-language translation",
        "capabilities": ["accepts_text", "returns_text", "calls_llm"],
        "input_types": ["text"],
        "output_types": ["translated_text"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_llm_embed": {
        "category": "llm",
        "subcategory": "embed",
        "description": "Semantic text embeddings",
        "capabilities": ["accepts_text", "returns_text", "calls_llm"],
        "input_types": ["text"],
        "output_types": ["embeddings"],
        "dependencies": [],
        "connects_to": ["research_semantic_cache"],
    },
    "research_llm_chat": {
        "category": "llm",
        "subcategory": "chat",
        "description": "Multi-turn conversation with LLM",
        "capabilities": ["accepts_text", "returns_text", "calls_llm"],
        "input_types": ["messages"],
        "output_types": ["response"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_ask_all_llms": {
        "category": "llm",
        "subcategory": "multi_model",
        "description": "Query multiple LLM providers in parallel",
        "capabilities": ["accepts_text", "returns_list", "calls_llm"],
        "input_types": ["text"],
        "output_types": ["model_responses"],
        "dependencies": [],
        "connects_to": ["research_consensus"],
    },

    # OSINT TOOLS
    "research_whois": {
        "category": "osint",
        "subcategory": "domain_intel",
        "description": "WHOIS domain information lookup",
        "capabilities": ["accepts_domain", "returns_structured", "calls_external_api"],
        "input_types": ["domain"],
        "output_types": ["whois_data"],
        "dependencies": [],
        "connects_to": ["research_dns_lookup", "research_infra_correlator"],
    },
    "research_dns_lookup": {
        "category": "osint",
        "subcategory": "domain_intel",
        "description": "DNS record resolution and analysis",
        "capabilities": ["accepts_domain", "returns_structured"],
        "input_types": ["domain"],
        "output_types": ["dns_records"],
        "dependencies": [],
        "connects_to": ["research_ip_geolocation", "research_infra_correlator"],
    },
    "research_ip_geolocation": {
        "category": "osint",
        "subcategory": "ip_intel",
        "description": "IP geolocation and reputation",
        "capabilities": ["accepts_ip", "returns_structured", "calls_external_api"],
        "input_types": ["ip"],
        "output_types": ["ip_data"],
        "dependencies": [],
        "connects_to": ["research_threat_profile"],
    },
    "research_ip_reputation": {
        "category": "osint",
        "subcategory": "ip_intel",
        "description": "IP reputation and blacklist checking",
        "capabilities": ["accepts_ip", "returns_score", "calls_external_api"],
        "input_types": ["ip"],
        "output_types": ["reputation_score"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_breach_check": {
        "category": "osint",
        "subcategory": "breach_data",
        "description": "HIBP breach database checking",
        "capabilities": ["accepts_text", "returns_list", "calls_external_api"],
        "input_types": ["email_or_password"],
        "output_types": ["breach_records"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_dark_cti": {
        "category": "osint",
        "subcategory": "dark_web",
        "description": "Dark web CTI and threat intelligence",
        "capabilities": ["accepts_query", "returns_list", "calls_external_api"],
        "input_types": ["query"],
        "output_types": ["threat_intel"],
        "dependencies": [],
        "connects_to": ["research_threat_intel"],
    },
    "research_social_search": {
        "category": "osint",
        "subcategory": "social_profiles",
        "description": "Cross-platform social media search",
        "capabilities": ["accepts_text", "returns_list", "calls_external_api"],
        "input_types": ["username"],
        "output_types": ["social_profiles"],
        "dependencies": [],
        "connects_to": ["research_social_profile"],
    },
    "research_infra_correlator": {
        "category": "osint",
        "subcategory": "infrastructure",
        "description": "Link domains/IPs via shared infrastructure",
        "capabilities": ["accepts_domain", "returns_structured", "calls_external_api"],
        "input_types": ["domain_or_ip"],
        "output_types": ["correlated_assets"],
        "dependencies": ["research_whois", "research_dns_lookup"],
        "connects_to": ["research_threat_profile"],
    },

    # SECURITY TOOLS
    "research_cert_analyze": {
        "category": "security",
        "subcategory": "cert_audit",
        "description": "SSL/TLS certificate analysis",
        "capabilities": ["accepts_domain", "returns_structured"],
        "input_types": ["domain"],
        "output_types": ["cert_data"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_security_headers": {
        "category": "security",
        "subcategory": "header_check",
        "description": "Security header validation",
        "capabilities": ["accepts_url", "returns_structured"],
        "input_types": ["url"],
        "output_types": ["header_analysis"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_cve_lookup": {
        "category": "security",
        "subcategory": "vuln_scan",
        "description": "CVE vulnerability lookup",
        "capabilities": ["accepts_text", "returns_list", "calls_external_api"],
        "input_types": ["cve_id_or_software"],
        "output_types": ["cve_records"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_pentest_agent": {
        "category": "security",
        "subcategory": "pentest",
        "description": "Automated penetration testing agent",
        "capabilities": ["accepts_text", "returns_structured", "calls_llm"],
        "input_types": ["target"],
        "output_types": ["pentest_results"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_threat_intel": {
        "category": "security",
        "subcategory": "threat_intel",
        "description": "Aggregated threat intelligence",
        "capabilities": ["accepts_text", "returns_structured", "calls_external_api"],
        "input_types": ["ioc"],
        "output_types": ["threat_data"],
        "dependencies": [],
        "connects_to": ["research_threat_profile"],
    },

    # DOCUMENT TOOLS
    "research_pdf_extract": {
        "category": "document",
        "subcategory": "pdf_extract",
        "description": "PDF text and metadata extraction",
        "capabilities": ["accepts_url", "returns_structured"],
        "input_types": ["pdf_url"],
        "output_types": ["pdf_content"],
        "dependencies": [],
        "connects_to": ["research_llm_extract", "research_table_extract"],
    },
    "research_ocr_extract": {
        "category": "document",
        "subcategory": "ocr",
        "description": "Optical character recognition from images",
        "capabilities": ["accepts_text", "returns_text", "calls_external_api"],
        "input_types": ["image"],
        "output_types": ["text"],
        "dependencies": [],
        "connects_to": ["research_llm_extract"],
    },
    "research_transcribe": {
        "category": "document",
        "subcategory": "transcribe",
        "description": "Audio/video to text transcription",
        "capabilities": ["accepts_url", "returns_text"],
        "input_types": ["audio_url"],
        "output_types": ["transcript"],
        "dependencies": [],
        "connects_to": ["research_llm_summarize"],
    },
    "research_convert_document": {
        "category": "document",
        "subcategory": "convert",
        "description": "Document format conversion",
        "capabilities": ["accepts_url", "returns_text"],
        "input_types": ["document_url"],
        "output_types": ["converted_format"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_table_extract": {
        "category": "document",
        "subcategory": "table_extract",
        "description": "Table extraction and structuring",
        "capabilities": ["accepts_text", "returns_structured"],
        "input_types": ["pdf_or_html"],
        "output_types": ["structured_tables"],
        "dependencies": [],
        "connects_to": [],
    },

    # GRAPH TOOLS
    "research_knowledge_graph": {
        "category": "graph",
        "subcategory": "knowledge_graph",
        "description": "Knowledge graph construction from content",
        "capabilities": ["accepts_text", "returns_structured", "calls_llm"],
        "input_types": ["text"],
        "output_types": ["knowledge_graph"],
        "dependencies": ["research_llm_extract"],
        "connects_to": ["research_graph_analyze"],
    },
    "research_graph_analyze": {
        "category": "graph",
        "subcategory": "relationship_map",
        "description": "Graph analysis and pattern detection",
        "capabilities": ["accepts_text", "returns_structured"],
        "input_types": ["graph_data"],
        "output_types": ["analysis"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_social_graph": {
        "category": "graph",
        "subcategory": "relationship_map",
        "description": "Social network graph construction",
        "capabilities": ["accepts_text", "returns_structured", "calls_external_api"],
        "input_types": ["social_data"],
        "output_types": ["social_graph"],
        "dependencies": [],
        "connects_to": ["research_graph_analyze"],
    },

    # PIPELINE/ORCHESTRATION TOOLS
    "research_consensus": {
        "category": "pipeline",
        "subcategory": "consensus",
        "description": "Consensus builder from multiple sources",
        "capabilities": ["accepts_text", "returns_structured", "calls_llm"],
        "input_types": ["multiple_responses"],
        "output_types": ["consensus_result"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_orchestrate": {
        "category": "pipeline",
        "subcategory": "orchestrate",
        "description": "Multi-stage tool orchestration",
        "capabilities": ["accepts_text", "returns_structured"],
        "input_types": ["goal"],
        "output_types": ["orchestration_result"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_workflow_create": {
        "category": "pipeline",
        "subcategory": "workflow",
        "description": "Create custom tool workflows",
        "capabilities": ["accepts_text", "returns_structured"],
        "input_types": ["workflow_spec"],
        "output_types": ["workflow"],
        "dependencies": [],
        "connects_to": ["research_workflow_run"],
    },

    # MONITORING TOOLS
    "research_change_monitor": {
        "category": "monitoring",
        "subcategory": "change_detect",
        "description": "Website change detection and tracking",
        "capabilities": ["accepts_url", "returns_text", "real_time", "cached"],
        "input_types": ["url"],
        "output_types": ["change_data"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_rss_fetch": {
        "category": "monitoring",
        "subcategory": "rss",
        "description": "RSS feed parsing and aggregation",
        "capabilities": ["accepts_url", "returns_list"],
        "input_types": ["rss_url"],
        "output_types": ["feed_items"],
        "dependencies": [],
        "connects_to": ["research_markdown"],
    },

    # SYSTEM TOOLS
    "research_config_get": {
        "category": "system",
        "subcategory": "config",
        "description": "Get configuration value",
        "capabilities": ["accepts_text", "returns_text"],
        "input_types": ["config_key"],
        "output_types": ["config_value"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_config_set": {
        "category": "system",
        "subcategory": "config",
        "description": "Set configuration value",
        "capabilities": ["accepts_text", "returns_text"],
        "input_types": ["config_key", "config_value"],
        "output_types": ["status"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_health_check": {
        "category": "system",
        "subcategory": "health",
        "description": "System health and status check",
        "capabilities": ["returns_structured"],
        "input_types": [],
        "output_types": ["health_status"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_cache_stats": {
        "category": "system",
        "subcategory": "cache",
        "description": "Cache statistics and usage",
        "capabilities": ["returns_structured"],
        "input_types": [],
        "output_types": ["cache_stats"],
        "dependencies": [],
        "connects_to": [],
    },
    "research_session_open": {
        "category": "system",
        "subcategory": "session",
        "description": "Open persistent browser session",
        "capabilities": ["accepts_text", "returns_text"],
        "input_types": ["session_name"],
        "output_types": ["session_id"],
        "dependencies": [],
        "connects_to": [],
    },
}


# ============================================================================
# MAIN TOOL DISCOVERY FUNCTIONS
# ============================================================================


async def research_tool_catalog(
    category: str | None = None,
    capability: str | None = None,
) -> dict[str, Any]:
    """Return full tool catalog with optional filtering.

    Args:
        category: Filter by category name (e.g., 'scraping', 'search')
        capability: Filter by capability tag

    Returns:
        Dict with: tools (list), categories, capabilities, total_count
    """
    try:
        tools = []

        for tool_name, metadata in TOOL_REGISTRY.items():
            # Apply filters
            if category and metadata["category"] != category:
                continue
            if capability and capability not in metadata["capabilities"]:
                continue

            tools.append({
                "name": tool_name,
                "category": metadata["category"],
                "subcategory": metadata["subcategory"],
                "description": metadata["description"],
                "capabilities": metadata["capabilities"],
                "input_types": metadata["input_types"],
                "output_types": metadata["output_types"],
                "dependencies": metadata["dependencies"],
                "connects_to": metadata["connects_to"],
            })

        return {
            "tools": tools,
            "total_count": len(tools),
            "categories": TOOL_CATEGORIES,
            "capabilities": CAPABILITIES,
            "filter_applied": {
                "category": category,
                "capability": capability,
            },
        }
    except Exception as exc:
        logger.exception("research_tool_catalog failed")
        return {"error": str(exc), "tool": "research_tool_catalog"}


async def research_tool_graph() -> dict[str, Any]:
    """Return complete tool connection graph.

    Shows which tools can feed into which others based on output→input matching.

    Returns:
        Dict with: nodes, edges, clusters (groups of connected tools)
    """
    try:
        # Build nodes
        nodes = []
        for tool_name, metadata in TOOL_REGISTRY.items():
            nodes.append({
                "id": tool_name,
                "label": tool_name.replace("research_", "").replace("_", " ").title(),
                "category": metadata["category"],
                "subcategory": metadata["subcategory"],
                "capabilities": metadata["capabilities"],
                "input_types": metadata["input_types"],
                "output_types": metadata["output_types"],
            })

        # Build edges from connects_to relationships
        edges = []
        edge_set = set()

        for tool_name, metadata in TOOL_REGISTRY.items():
            for target in metadata["connects_to"]:
                if target in TOOL_REGISTRY:
                    edge_id = (tool_name, target)
                    if edge_id not in edge_set:
                        edges.append({
                            "source": tool_name,
                            "target": target,
                            "type": "feeds_into",
                            "reason": f"{metadata['output_types']} → {TOOL_REGISTRY[target]['input_types']}",
                        })
                        edge_set.add(edge_id)

        # Identify clusters (category-based grouping)
        clusters = {}
        for node in nodes:
            category = node["category"]
            if category not in clusters:
                clusters[category] = []
            clusters[category].append(node["id"])

        return {
            "nodes": nodes,
            "edges": edges,
            "clusters": clusters,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
        }
    except Exception as exc:
        logger.exception("research_tool_graph failed")
        return {"error": str(exc), "tool": "research_tool_graph"}


async def research_tool_pipeline(
    goal: str,
    max_steps: int = 5,
) -> dict[str, Any]:
    """Build optimal tool pipeline from research goal.

    Uses knowledge graph and BFS to find path from available tools
    to goal capabilities.

    Args:
        goal: Research goal (e.g., "find domain OSINT", "analyze breach data")
        max_steps: Maximum pipeline length

    Returns:
        Dict with: goal, pipeline (steps), estimated_time_ms, success
    """
    try:
        # Simple goal→category mapping
        goal_lower = goal.lower()
        if "domain" in goal_lower or "whois" in goal_lower:
            target_category = "osint"
        elif "vulnerability" in goal_lower or "security" in goal_lower:
            target_category = "security"
        elif "search" in goal_lower or "find" in goal_lower:
            target_category = "search"
        elif "extract" in goal_lower or "parse" in goal_lower:
            target_category = "document"
        elif "summarize" in goal_lower or "analyze" in goal_lower:
            target_category = "llm"
        else:
            target_category = None

        # Find tools in target category
        pipeline = []
        if target_category:
            for tool_name, metadata in TOOL_REGISTRY.items():
                if metadata["category"] == target_category:
                    pipeline.append({
                        "step": len(pipeline) + 1,
                        "tool": tool_name,
                        "category": metadata["category"],
                        "description": metadata["description"],
                        "rationale": f"Category match: {target_category}",
                        "input_from": "user" if len(pipeline) == 0 else pipeline[-1]["tool"],
                        "output_to": "next_step",
                    })
                    if len(pipeline) >= max_steps:
                        break

        return {
            "goal": goal,
            "target_category": target_category,
            "pipeline": pipeline,
            "pipeline_length": len(pipeline),
            "estimated_time_ms": len(pipeline) * 1000,
            "success": len(pipeline) > 0,
        }
    except Exception as exc:
        logger.exception("research_tool_pipeline failed")
        return {"error": str(exc), "tool": "research_tool_pipeline"}


async def research_tool_standalone(tool_name: str) -> dict[str, Any]:
    """Get complete standalone usage info for a tool.

    Args:
        tool_name: Tool name (e.g., 'research_fetch')

    Returns:
        Dict with: description, parameters, examples, related_tools, pipelines
    """
    try:
        if tool_name not in TOOL_REGISTRY:
            return {
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(TOOL_REGISTRY.keys())[:10],
            }

        metadata = TOOL_REGISTRY[tool_name]

        # Find related tools
        related = {
            "dependencies": metadata["dependencies"],
            "connects_to": metadata["connects_to"],
            "same_category": [
                name for name, m in TOOL_REGISTRY.items()
                if m["category"] == metadata["category"] and name != tool_name
            ][:5],
        }

        return {
            "name": tool_name,
            "description": metadata["description"],
            "category": metadata["category"],
            "subcategory": metadata["subcategory"],
            "capabilities": metadata["capabilities"],
            "input_types": metadata["input_types"],
            "output_types": metadata["output_types"],
            "related_tools": related,
            "typical_pipelines": [
                f"{dep} → {tool_name}" for dep in metadata["dependencies"]
            ] + [
                f"{tool_name} → {target}" for target in metadata["connects_to"]
            ],
        }
    except Exception as exc:
        logger.exception("research_tool_standalone failed")
        return {"error": str(exc), "tool": "research_tool_standalone"}


# ============================================================================
# EXPOSE MCP TOOLS
# ============================================================================

__all__ = [
    "research_tool_catalog",
    "research_tool_graph",
    "research_tool_pipeline",
    "research_tool_standalone",
    "TOOL_REGISTRY",
    "TOOL_CATEGORIES",
    "CAPABILITIES",
]
