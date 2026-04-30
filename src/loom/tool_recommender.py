"""Tool recommendation engine for Loom MCP research server.

Suggests relevant tools based on user query content using keyword matching,
semantic similarity, and tool category clustering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolRecommendation:
    """A recommended tool with relevance score and reasoning."""

    tool_name: str
    category: str
    relevance_score: float
    reason: str
    usage_example: str


class ToolRecommender:
    """Suggest relevant Loom tools based on user's query.

    Uses keyword matching and semantic clustering to identify tools that
    match the intent of a research query.
    """

    # Comprehensive tool catalog with categories and keywords
    TOOL_CATALOG = {
        # Web Scraping & Fetching
        "web_scraping": {
            "tools": [
                "research_fetch",
                "research_spider",
                "research_markdown",
                "research_camoufox",
                "research_botasaurus",
            ],
            "keywords": [
                "scrape",
                "fetch",
                "website",
                "page",
                "url",
                "crawl",
                "html",
                "content",
                "download",
                "extract text",
            ],
            "description": "Extract and process content from web pages",
        },
        # Search & Discovery
        "search": {
            "tools": [
                "research_search",
                "research_multi_search",
                "research_deep",
            ],
            "keywords": [
                "search",
                "find",
                "look up",
                "discover",
                "query",
                "locate",
                "find information",
                "semantic",
            ],
            "description": "Search across multiple providers and discover information",
        },
        # OSINT & Reconnaissance
        "osint": {
            "tools": [
                "research_passive_recon",
                "research_identity_resolve",
                "research_social_graph",
                "research_whois",
                "research_dns_lookup",
                "research_infra_correlator",
                "research_nmap_scan",
            ],
            "keywords": [
                "osint",
                "recon",
                "identity",
                "person",
                "domain",
                "infrastructure",
                "mapping",
                "relationship",
                "network",
                "correlation",
            ],
            "description": "Open source intelligence gathering and reconnaissance",
        },
        # Dark Web & Tor
        "dark_web": {
            "tools": [
                "research_dark_forum",
                "research_onion_discover",
                "research_darkweb_early_warning",
                "research_tor_status",
                "research_tor_new_identity",
            ],
            "keywords": [
                "dark web",
                "onion",
                "tor",
                "darknet",
                "forum",
                "underground",
                "hidden service",
            ],
            "description": "Access and analyze dark web and Tor network resources",
        },
        # AI Safety & Red Teaming
        "ai_safety": {
            "tools": [
                "research_prompt_injection_test",
                "research_bias_probe",
                "research_safety_filter_map",
                "research_compliance_check",
                "research_hallucination_benchmark",
                "research_adversarial_robustness",
            ],
            "keywords": [
                "safety",
                "bias",
                "injection",
                "compliance",
                "red team",
                "jailbreak",
                "adversarial",
                "filter",
                "hallucination",
                "robustness",
                "eu ai act",
            ],
            "description": "Test AI model safety, bias, and compliance",
        },
        # Text & NLP Analysis
        "nlp": {
            "tools": [
                "research_stylometry",
                "research_deception_detect",
                "research_sentiment_deep",
                "research_persona_profile",
                "research_text_analyze",
                "research_radicalization_detect",
                "research_psycholinguistic",
            ],
            "keywords": [
                "text",
                "analysis",
                "sentiment",
                "author",
                "language",
                "deception",
                "emotion",
                "style",
                "personality",
                "nlp",
                "linguistics",
            ],
            "description": "Analyze text content using NLP and linguistics",
        },
        # Career & Job Intelligence
        "career": {
            "tools": [
                "research_funding_signal",
                "research_career_trajectory",
                "research_market_velocity",
                "research_optimize_resume",
                "research_interview_prep",
                "research_stealth_hire_scanner",
                "research_job_search",
                "research_job_market",
            ],
            "keywords": [
                "job",
                "career",
                "salary",
                "resume",
                "interview",
                "hiring",
                "employment",
                "market",
                "trajectory",
                "signals",
            ],
            "description": "Career path analysis and job market intelligence",
        },
        # Academic & Research
        "academic": {
            "tools": [
                "research_citation_analysis",
                "research_retraction_check",
                "research_predatory_journal_check",
                "research_grant_forensics",
                "research_data_fabrication",
                "research_preprint_manipulation",
            ],
            "keywords": [
                "paper",
                "journal",
                "citation",
                "academic",
                "research",
                "publication",
                "retraction",
                "predatory",
                "grant",
                "scholar",
            ],
            "description": "Academic integrity and research quality analysis",
        },
        # Security & Vulnerability
        "security": {
            "tools": [
                "research_nmap_scan",
                "research_cert_analyze",
                "research_security_headers",
                "research_ip_reputation",
                "research_cve_lookup",
                "research_cve_detail",
                "research_vuln_intel",
                "research_breach_check",
                "research_password_check",
                "research_urlhaus_check",
            ],
            "keywords": [
                "security",
                "vulnerability",
                "scan",
                "port",
                "ssl",
                "certificate",
                "cve",
                "breach",
                "password",
                "exploit",
                "malware",
            ],
            "description": "Security scanning and vulnerability assessment",
        },
        # Cryptocurrency & Blockchain
        "crypto": {
            "tools": [
                "research_crypto_trace",
            ],
            "keywords": [
                "bitcoin",
                "blockchain",
                "crypto",
                "wallet",
                "transaction",
                "ethereum",
                "address",
            ],
            "description": "Blockchain and cryptocurrency analysis",
        },
        # Media & Document Processing
        "media": {
            "tools": [
                "research_screenshot",
                "research_transcribe",
                "research_ocr_extract",
                "research_image_analyze",
                "research_pdf_extract",
                "research_pdf_search",
                "research_exif_extract",
                "research_metadata_forensics",
                "research_convert_document",
            ],
            "keywords": [
                "image",
                "audio",
                "video",
                "screenshot",
                "transcribe",
                "ocr",
                "pdf",
                "document",
                "metadata",
                "exif",
                "media",
            ],
            "description": "Process and analyze media files and documents",
        },
        # Threat Intelligence
        "threat_intel": {
            "tools": [
                "research_threat_profile",
                "research_threat_intel",
                "research_darkweb_early_warning",
                "research_leak_scan",
                "research_dead_drop_scanner",
            ],
            "keywords": [
                "threat",
                "actor",
                "attack",
                "adversary",
                "campaign",
                "infrastructure",
                "malware",
                "early warning",
            ],
            "description": "Threat actor profiling and intelligence",
        },
        # Domain & Infrastructure Intelligence
        "domain_intel": {
            "tools": [
                "research_whois",
                "research_dns_lookup",
                "research_ip_geolocation",
                "research_nmap_scan",
                "research_infra_correlator",
                "research_security_headers",
                "research_cert_analyze",
            ],
            "keywords": [
                "domain",
                "whois",
                "dns",
                "ip",
                "geolocation",
                "infrastructure",
                "server",
                "hosting",
            ],
            "description": "Domain and infrastructure reconnaissance",
        },
        # Supply Chain & Dependencies
        "supply_chain": {
            "tools": [
                "research_supply_chain_risk",
                "research_dependency_audit",
                "research_patent_landscape",
            ],
            "keywords": [
                "supply chain",
                "dependency",
                "risk",
                "license",
                "package",
                "patent",
                "vendor",
            ],
            "description": "Supply chain risk and dependency analysis",
        },
        # Expertise & Skills
        "expertise": {
            "tools": [
                "research_find_experts",
                "research_map_research_to_product",
                "research_translate_academic_skills",
            ],
            "keywords": [
                "expert",
                "skills",
                "expertise",
                "specialist",
                "talent",
                "capability",
            ],
            "description": "Find expertise and capability mapping",
        },
        # Data & Financial Intelligence
        "financial_intel": {
            "tools": [
                "research_salary_intelligence",
                "research_usage_report",
                "research_stripe_balance",
            ],
            "keywords": [
                "salary",
                "financial",
                "billing",
                "revenue",
                "pricing",
                "compensation",
            ],
            "description": "Financial and salary intelligence",
        },
        # Competitive & Market Intelligence
        "competitive_intel": {
            "tools": [
                "research_competitive_intel",
                "research_company_diligence",
            ],
            "keywords": [
                "competitor",
                "market",
                "strategy",
                "competitive",
                "business",
                "company",
            ],
            "description": "Competitive and market analysis",
        },
        # Monitoring & Change Detection
        "monitoring": {
            "tools": [
                "research_change_monitor",
                "research_realtime_monitor",
                "research_rss_fetch",
                "research_rss_search",
            ],
            "keywords": [
                "monitor",
                "watch",
                "track",
                "changes",
                "updates",
                "delta",
                "rss",
            ],
            "description": "Monitor changes and updates in real-time",
        },
        # Social Media & Profiles
        "social_intel": {
            "tools": [
                "research_social_search",
                "research_social_profile",
                "research_community_sentiment",
                "research_network_persona",
            ],
            "keywords": [
                "social media",
                "profile",
                "twitter",
                "reddit",
                "community",
                "sentiment",
                "followers",
            ],
            "description": "Social media intelligence and sentiment analysis",
        },
        # Wayback & Archive
        "archive": {
            "tools": [
                "research_wayback",
                "research_dead_content",
                "research_registry_graveyard",
            ],
            "keywords": [
                "archive",
                "wayback",
                "historical",
                "past",
                "snapshot",
                "dead",
            ],
            "description": "Access archived and historical web content",
        },
        # GitHub & Code Intelligence
        "code_intel": {
            "tools": [
                "research_github",
                "research_github_readme",
                "research_github_releases",
                "research_commit_analyzer",
            ],
            "keywords": [
                "github",
                "code",
                "repository",
                "commit",
                "release",
                "opensource",
            ],
            "description": "GitHub and code repository analysis",
        },
        # Knowledge Graphs & Extraction
        "knowledge_extraction": {
            "tools": [
                "research_knowledge_graph",
                "research_llm_extract",
                "research_llm_classify",
            ],
            "keywords": [
                "knowledge graph",
                "extraction",
                "entities",
                "relationships",
                "semantic",
                "structure",
            ],
            "description": "Extract and structure knowledge from content",
        },
        # Fact Checking & Verification
        "fact_checking": {
            "tools": [
                "research_fact_checker",
                "research_misinfo_check",
            ],
            "keywords": [
                "fact check",
                "verify",
                "claim",
                "misinformation",
                "false",
                "truth",
            ],
            "description": "Verify claims and detect misinformation",
        },
        # Signal Detection & Prediction
        "signal_detection": {
            "tools": [
                "research_ghost_protocol",
                "research_temporal_anomaly",
                "research_sec_tracker",
                "research_trend_predict",
            ],
            "keywords": [
                "signal",
                "anomaly",
                "trend",
                "prediction",
                "forecast",
                "pattern",
            ],
            "description": "Detect signals, anomalies, and predict trends",
        },
        # LLM & Language Services
        "llm_services": {
            "tools": [
                "research_llm_summarize",
                "research_llm_answer",
                "research_llm_translate",
                "research_llm_chat",
                "research_llm_embed",
                "research_llm_query_expand",
            ],
            "keywords": [
                "summarize",
                "translate",
                "question",
                "answer",
                "chat",
                "language",
                "llm",
            ],
            "description": "LLM-powered text processing and chat",
        },
        # Configuration & System
        "system": {
            "tools": [
                "research_config_get",
                "research_config_set",
                "research_health_check",
                "research_cache_stats",
                "research_cache_clear",
            ],
            "keywords": [
                "config",
                "setting",
                "health",
                "status",
                "cache",
                "system",
            ],
            "description": "System configuration and management",
        },
        # Session Management
        "sessions": {
            "tools": [
                "research_session_open",
                "research_session_list",
                "research_session_close",
            ],
            "keywords": [
                "session",
                "browser",
                "persistence",
                "state",
                "login",
            ],
            "description": "Manage persistent browser sessions",
        },
        # Specialized Research Tools
        "specialized": {
            "tools": [
                "research_invisible_web",
                "research_js_intel",
                "research_consensus_ring",
                "research_citation_police",
                "research_evidence_pipeline",
            ],
            "keywords": [
                "specialized",
                "advanced",
                "custom",
                "unique",
            ],
            "description": "Advanced and specialized research tools",
        },
    }

    def __init__(self) -> None:
        """Initialize the tool recommender with catalog."""
        self._build_tool_index()

    def _build_tool_index(self) -> None:
        """Build reverse index of tools to categories for fast lookup."""
        self._tool_to_categories: dict[str, list[str]] = {}
        self._all_tools: set[str] = set()

        for category, data in self.TOOL_CATALOG.items():
            for tool in data["tools"]:
                if tool not in self._tool_to_categories:
                    self._tool_to_categories[tool] = []
                self._tool_to_categories[tool].append(category)
                self._all_tools.add(tool)

    def recommend(
        self,
        query: str,
        max_recommendations: int = 10,
        exclude_used: list[str] | None = None,
    ) -> list[ToolRecommendation]:
        """Recommend tools based on query content.

        Args:
            query: User's research query or task description
            max_recommendations: Maximum number of tools to recommend (default: 10)
            exclude_used: List of tool names to exclude from recommendations

        Returns:
            List of ToolRecommendation objects sorted by relevance score (highest first)
        """
        if not query or not query.strip():
            return []

        exclude_set = set(exclude_used) if exclude_used else set()
        query_lower = query.lower()

        # Score each tool based on keyword matches
        tool_scores: dict[str, tuple[float, str, str]] = {}

        for category, data in self.TOOL_CATALOG.items():
            category_keywords = data["keywords"]
            category_description = data["description"]

            for tool in data["tools"]:
                if tool in exclude_set:
                    continue

                # Calculate keyword match score
                score = self._calculate_relevance(
                    query_lower, category_keywords, category_description
                )

                if score > 0:
                    if tool not in tool_scores or tool_scores[tool][0] < score:
                        tool_scores[tool] = (
                            score,
                            category,
                            self._generate_reason(query_lower, category_keywords),
                        )

        # Sort by score and create recommendations
        sorted_tools = sorted(
            tool_scores.items(), key=lambda x: x[1][0], reverse=True
        )

        recommendations = []
        for tool_name, (score, category, reason) in sorted_tools[
            :max_recommendations
        ]:
            example = self._get_usage_example(tool_name)
            recommendations.append(
                ToolRecommendation(
                    tool_name=tool_name,
                    category=category,
                    relevance_score=round(score, 2),
                    reason=reason,
                    usage_example=example,
                )
            )

        return recommendations

    def _calculate_relevance(
        self, query: str, keywords: list[str], description: str
    ) -> float:
        """Calculate relevance score for a tool based on query matching.

        Args:
            query: Lowercase user query
            keywords: Tool category keywords
            description: Tool category description

        Returns:
            Relevance score between 0 and 1
        """
        score = 0.0

        # Direct keyword matches (high weight)
        for keyword in keywords:
            if keyword in query:
                # Exact phrase match gets higher score
                if f" {keyword} " in f" {query} " or query.startswith(
                    keyword
                ) or query.endswith(keyword):
                    score += 0.3
                else:
                    score += 0.2

        # Partial keyword matches (lower weight)
        for keyword in keywords:
            # Check for word boundaries
            if re.search(rf"\b{re.escape(keyword)}\b", query):
                score += 0.1

        # Description matches
        for word in description.split():
            if word.lower() in query:
                score += 0.05

        # Normalize to 0-1 range
        return min(score, 1.0)

    def _generate_reason(self, query: str, keywords: list[str]) -> str:
        """Generate a human-readable reason for the recommendation.

        Args:
            query: Lowercase user query
            keywords: Tool category keywords

        Returns:
            Reason string explaining why this tool was recommended
        """
        matched_keywords = []
        for keyword in keywords:
            if keyword in query:
                matched_keywords.append(keyword)

        if matched_keywords:
            return f"Matches your mention of: {', '.join(matched_keywords[:3])}"
        return "Relevant to your research query"

    def _get_usage_example(self, tool_name: str) -> str:
        """Get a usage example for a given tool.

        Args:
            tool_name: Name of the tool

        Returns:
            A usage example string
        """
        examples = {
            "research_fetch": "Fetch and analyze content from https://example.com",
            "research_spider": "Crawl multiple URLs in parallel: [url1, url2, url3]",
            "research_search": "Search for 'machine learning papers' across all providers",
            "research_deep": "Deep research on 'supply chain vulnerabilities'",
            "research_passive_recon": "Gather OSINT on domain example.com",
            "research_identity_resolve": "Link social media accounts to person John Doe",
            "research_social_graph": "Map relationships in hacker forums",
            "research_dark_forum": "Search darkweb forums for 'exploit kits'",
            "research_prompt_injection_test": "Test model safety against prompt injection",
            "research_stylometry": "Analyze writing style to identify author",
            "research_sentiment_deep": "Analyze emotions in user reviews",
            "research_career_trajectory": "Track career path of tech executive",
            "research_citation_analysis": "Analyze citation network for a paper",
            "research_nmap_scan": "Port scan and service enumeration on 192.168.1.1",
            "research_cert_analyze": "Inspect SSL certificate chain for example.com",
            "research_crypto_trace": "Trace Bitcoin address 1A1z7agoat...",
            "research_screenshot": "Capture webpage screenshot at 1920x1080",
            "research_transcribe": "Transcribe audio file speech.mp3 to text",
            "research_threat_profile": "Profile threat actor infrastructure",
            "research_whois": "WHOIS lookup for domain example.com",
            "research_supply_chain_risk": "Analyze dependencies in npm package",
            "research_find_experts": "Find experts in 'distributed systems'",
            "research_change_monitor": "Monitor changes to competitor website",
            "research_social_search": "Search for mentions on Twitter and Reddit",
            "research_wayback": "View historical snapshots from Wayback Machine",
            "research_github": "Search GitHub for code related to 'vulnerability'",
            "research_knowledge_graph": "Extract entities and relationships from text",
            "research_fact_checker": "Verify claim about climate change statistics",
            "research_trend_predict": "Forecast AI adoption trends",
            "research_llm_summarize": "Summarize long research paper",
            "research_llm_translate": "Translate Arabic text to English",
            "research_config_get": "View current configuration settings",
            "research_session_open": "Open persistent browser session 'evasion'",
        }

        return examples.get(
            tool_name, f"Use {tool_name} to accomplish your research goal"
        )

    def get_all_tools(self) -> list[str]:
        """Get list of all available tools.

        Returns:
            Sorted list of all tool names
        """
        return sorted(self._all_tools)

    def get_tools_by_category(self, category: str) -> list[str]:
        """Get tools for a specific category.

        Args:
            category: Category name

        Returns:
            List of tool names in the category
        """
        if category not in self.TOOL_CATALOG:
            return []
        return self.TOOL_CATALOG[category]["tools"]

    def get_categories(self) -> list[str]:
        """Get all available tool categories.

        Returns:
            Sorted list of category names
        """
        return sorted(self.TOOL_CATALOG.keys())
