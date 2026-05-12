"""Pre-built research workflow templates for common investigation patterns."""

from __future__ import annotations

from typing import Any

from loom.error_responses import handle_tool_errors

# 10+ pre-built workflow templates with documented steps
WORKFLOW_TEMPLATES = {
    "full_osint_person": {
        "name": "full_osint_person",
        "description": "Comprehensive OSINT investigation on a target person",
        "estimated_time_minutes": 45,
        "prerequisites": ["target_name", "optional_email"],
        "tools_used": ["research_search", "research_social_graph", "research_identity_resolve", "research_report_generator"],
        "steps": [
            {
                "order": 1,
                "tool": "research_search",
                "description": "Initial discovery across web + dark web",
                "params_template": {"query": "TARGET_NAME", "include_darkweb": True},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_social_graph",
                "description": "Map social connections and relationships",
                "params_template": {"target": "TARGET_NAME", "depth": 2},
                "condition": "success_from_step_1",
            },
            {
                "order": 3,
                "tool": "research_identity_resolve",
                "description": "Cross-reference identities and aliases",
                "params_template": {"identifiers": ["TARGET_NAME", "EMAIL_OPTIONAL"]},
                "condition": "success_from_step_2",
            },
            {
                "order": 4,
                "tool": "research_report_generator",
                "description": "Generate final intelligence report",
                "params_template": {"data_from": ["step_1", "step_2", "step_3"], "format": "markdown"},
                "condition": "all_previous",
            },
        ],
    },
    "domain_threat_assessment": {
        "name": "domain_threat_assessment",
        "description": "Complete threat landscape assessment for a target domain",
        "estimated_time_minutes": 60,
        "prerequisites": ["target_domain"],
        "tools_used": ["research_whois", "research_dns", "research_ip_intel", "research_security_headers", "research_threat_profile"],
        "steps": [
            {
                "order": 1,
                "tool": "research_whois",
                "description": "Domain registration and ownership details",
                "params_template": {"domain": "TARGET_DOMAIN"},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_dns",
                "description": "DNS records and subdomain enumeration",
                "params_template": {"domain": "TARGET_DOMAIN", "include_subdomains": True},
                "condition": None,
            },
            {
                "order": 3,
                "tool": "research_ip_intel",
                "description": "IP reputation and historical data",
                "params_template": {"ip_list": "FROM_STEP_2_DNS"},
                "condition": "success_from_step_2",
            },
            {
                "order": 4,
                "tool": "research_security_headers",
                "description": "Analyze HTTP security headers and SSL/TLS config",
                "params_template": {"url": "https://TARGET_DOMAIN", "check_ssl": True},
                "condition": None,
            },
            {
                "order": 5,
                "tool": "research_threat_profile",
                "description": "Aggregate threat indicators and infrastructure correlation",
                "params_template": {"domain": "TARGET_DOMAIN", "include_passive": True},
                "condition": "all_previous",
            },
        ],
    },
    "dark_web_investigation": {
        "name": "dark_web_investigation",
        "description": "Multi-stage dark web intelligence gathering and forum monitoring",
        "estimated_time_minutes": 120,
        "prerequisites": ["target_keyword_or_hash"],
        "tools_used": ["research_dark_forum", "research_onion_discover", "research_leak_scan", "research_report_generator"],
        "steps": [
            {
                "order": 1,
                "tool": "research_dark_forum",
                "description": "Search 24M+ darkweb forum posts for mentions",
                "params_template": {"query": "TARGET_KEYWORD", "limit": 100},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_onion_discover",
                "description": "Crawl Tor directory listings for .onion services",
                "params_template": {"keyword": "TARGET_KEYWORD", "timeout": 600},
                "condition": None,
            },
            {
                "order": 3,
                "tool": "research_leak_scan",
                "description": "Scan breach databases and paste sites",
                "params_template": {"hash_or_keyword": "TARGET_KEYWORD"},
                "condition": None,
            },
            {
                "order": 4,
                "tool": "research_report_generator",
                "description": "Synthesize findings into darkweb intelligence report",
                "params_template": {"data_from": ["step_1", "step_2", "step_3"], "format": "json"},
                "condition": "all_previous",
            },
        ],
    },
    "competitive_intelligence": {
        "name": "competitive_intelligence",
        "description": "Gather and analyze competitive market intelligence and strategy insights",
        "estimated_time_minutes": 90,
        "prerequisites": ["target_company"],
        "tools_used": ["research_competitive_intel", "research_company_intel", "research_search"],
        "steps": [
            {
                "order": 1,
                "tool": "research_competitive_intel",
                "description": "Analyze competitor products, pricing, market positioning",
                "params_template": {"company": "TARGET_COMPANY", "depth": "full"},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_company_intel",
                "description": "Target company financials, leadership, recent news",
                "params_template": {"company": "TARGET_COMPANY", "include_news": True, "years": 3},
                "condition": None,
            },
            {
                "order": 3,
                "tool": "research_search",
                "description": "Patent landscape and R&D activity discovery",
                "params_template": {"query": "TARGET_COMPANY patents OR research OR innovation", "site": "patents.google.com"},
                "condition": None,
            },
        ],
    },
    "vulnerability_assessment": {
        "name": "vulnerability_assessment",
        "description": "Comprehensive vulnerability and security posture analysis",
        "estimated_time_minutes": 75,
        "prerequisites": ["target_domain_or_ip"],
        "tools_used": ["research_cve_lookup", "research_vuln_intel", "research_security_headers", "research_fuzzer"],
        "steps": [
            {
                "order": 1,
                "tool": "research_cve_lookup",
                "description": "Identify known CVEs affecting target services",
                "params_template": {"target": "TARGET_DOMAIN", "include_services": True},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_vuln_intel",
                "description": "Deep vulnerability intelligence and exploit availability",
                "params_template": {"target": "TARGET_DOMAIN", "severity_min": "medium"},
                "condition": "success_from_step_1",
            },
            {
                "order": 3,
                "tool": "research_security_headers",
                "description": "Security configuration and header analysis",
                "params_template": {"url": "https://TARGET_DOMAIN"},
                "condition": None,
            },
            {
                "order": 4,
                "tool": "research_fuzzer",
                "description": "API parameter and endpoint fuzzing",
                "params_template": {"base_url": "https://TARGET_DOMAIN", "timeout": 300},
                "condition": "success_from_step_3",
            },
        ],
    },
    "academic_deep_dive": {
        "name": "academic_deep_dive",
        "description": "Comprehensive academic research synthesis and fact verification",
        "estimated_time_minutes": 120,
        "prerequisites": ["research_topic"],
        "tools_used": ["research_fetch", "research_academic_integrity", "research_fact_checker", "research_llm_summarize"],
        "steps": [
            {
                "order": 1,
                "tool": "research_fetch",
                "description": "Discover and fetch academic papers from arXiv",
                "params_template": {"query": "RESEARCH_TOPIC", "source": "arxiv", "limit": 20},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_academic_integrity",
                "description": "Citation analysis and retraction checking",
                "params_template": {"papers_from": "step_1", "check_retractions": True},
                "condition": "success_from_step_1",
            },
            {
                "order": 3,
                "tool": "research_fact_checker",
                "description": "Verify key claims and factual assertions",
                "params_template": {"content_from": "step_1", "model": "auto"},
                "condition": "success_from_step_1",
            },
            {
                "order": 4,
                "tool": "research_llm_summarize",
                "description": "Generate synthesis and key takeaways",
                "params_template": {"papers": "FROM_STEP_1", "max_length": 2000},
                "condition": "all_previous",
            },
        ],
    },
    "red_team_campaign": {
        "name": "red_team_campaign",
        "description": "Multi-stage red team simulation with transferability testing",
        "estimated_time_minutes": 180,
        "prerequisites": ["target_model_or_system"],
        "tools_used": ["research_auto_redteam", "research_swarm_attack", "research_consensus_build", "research_report_generator"],
        "steps": [
            {
                "order": 1,
                "tool": "research_auto_redteam",
                "description": "Automated red team attack generation and testing",
                "params_template": {"target": "TARGET_MODEL", "num_attempts": 50, "strategy": "adaptive"},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_swarm_attack",
                "description": "Parallel multi-model attack transferability assessment",
                "params_template": {"attack_from": "step_1", "test_models": ["gpt4", "claude3", "gemini"]},
                "condition": "success_from_step_1",
            },
            {
                "order": 3,
                "tool": "research_consensus_build",
                "description": "Consensus-based attack validation across models",
                "params_template": {"results_from": "step_2", "confidence_threshold": 0.7},
                "condition": "success_from_step_2",
            },
            {
                "order": 4,
                "tool": "research_report_generator",
                "description": "Generate red team findings and recommendations",
                "params_template": {"data": ["step_1", "step_2", "step_3"], "format": "detailed"},
                "condition": "all_previous",
            },
        ],
    },
    "model_security_audit": {
        "name": "model_security_audit",
        "description": "Comprehensive AI model security and safety audit",
        "estimated_time_minutes": 150,
        "prerequisites": ["target_model_api_key"],
        "tools_used": ["research_ai_safety", "research_model_profile", "research_bias_lens", "research_consistency_pressure"],
        "steps": [
            {
                "order": 1,
                "tool": "research_ai_safety",
                "description": "Safety filter mapping and injection testing",
                "params_template": {"model": "TARGET_MODEL", "test_jailbreaks": True},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_model_profile",
                "description": "Model capability and behavior profiling",
                "params_template": {"model": "TARGET_MODEL", "benchmarks": ["reasoning", "knowledge", "coding"]},
                "condition": None,
            },
            {
                "order": 3,
                "tool": "research_bias_lens",
                "description": "Bias detection and fairness evaluation",
                "params_template": {"model": "TARGET_MODEL", "domains": ["gender", "race", "politics"]},
                "condition": None,
            },
            {
                "order": 4,
                "tool": "research_consistency_pressure",
                "description": "Consistency constraint analysis across multiple runs",
                "params_template": {"model": "TARGET_MODEL", "iterations": 5},
                "condition": "all_previous",
            },
        ],
    },
    "supply_chain_audit": {
        "name": "supply_chain_audit",
        "description": "Comprehensive software and AI supply chain security analysis",
        "estimated_time_minutes": 100,
        "prerequisites": ["package_name_or_model_id"],
        "tools_used": ["research_dependency_graph", "research_vuln_intel", "research_threat_profile", "research_audit_log"],
        "steps": [
            {
                "order": 1,
                "tool": "research_dependency_graph",
                "description": "Map complete dependency tree and transitive vulnerabilities",
                "params_template": {"package": "PACKAGE_NAME", "language": "auto"},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_vuln_intel",
                "description": "Identify vulnerabilities across all dependencies",
                "params_template": {"packages_from": "step_1", "severity_min": "low"},
                "condition": "success_from_step_1",
            },
            {
                "order": 3,
                "tool": "research_threat_profile",
                "description": "Model integrity checks and supply chain poisoning assessment",
                "params_template": {"package": "PACKAGE_NAME", "check_integrity": True},
                "condition": None,
            },
            {
                "order": 4,
                "tool": "research_audit_log",
                "description": "Generate supply chain audit report",
                "params_template": {"data": ["step_1", "step_2", "step_3"], "export_format": "json"},
                "condition": "all_previous",
            },
        ],
    },
    "breach_response": {
        "name": "breach_response",
        "description": "Incident response workflow for confirmed breach scenario",
        "estimated_time_minutes": 90,
        "prerequisites": ["hash_or_indicator"],
        "tools_used": ["research_leak_scan", "research_breach_check", "research_identity_resolve", "research_threat_profile"],
        "steps": [
            {
                "order": 1,
                "tool": "research_leak_scan",
                "description": "Scan all known breach databases for exposure",
                "params_template": {"hash_or_keyword": "TARGET_INDICATOR"},
                "condition": None,
            },
            {
                "order": 2,
                "tool": "research_breach_check",
                "description": "Detailed breach data enrichment and timeline",
                "params_template": {"from_scan": "step_1", "include_dark_web": True},
                "condition": "success_from_step_1",
            },
            {
                "order": 3,
                "tool": "research_identity_resolve",
                "description": "Identify all affected identities and accounts",
                "params_template": {"identifiers_from": "step_2"},
                "condition": "success_from_step_2",
            },
            {
                "order": 4,
                "tool": "research_threat_profile",
                "description": "Threat actor profiling and incident analysis",
                "params_template": {"breach_data": ["step_1", "step_2", "step_3"]},
                "condition": "all_previous",
            },
        ],
    },
}


@handle_tool_errors("research_workflow_list")
def research_workflow_list() -> dict[str, Any]:
    """List all pre-built workflow templates.

    Returns:
        Dict with 'workflows' list and 'total' count.
        Each workflow entry includes: name, description, steps_count,
        estimated_time, tools_used.
    """
    workflows = []
    for tmpl_name, tmpl_data in WORKFLOW_TEMPLATES.items():
        workflows.append(
            {
                "name": tmpl_name,
                "description": tmpl_data["description"],
                "steps_count": len(tmpl_data["steps"]),
                "estimated_time_minutes": tmpl_data["estimated_time_minutes"],
                "tools_used": tmpl_data["tools_used"],
            }
        )
    return {"workflows": workflows, "total": len(workflows)}

@handle_tool_errors("research_workflow_get")
def research_workflow_get(name: str) -> dict[str, Any]:
    """Get detailed workflow template definition.

    Args:
        name: Workflow template name (e.g., 'full_osint_person')

    Returns:
        Dict with name, description, steps (with tool, params_template, etc.),
        estimated_time_minutes, prerequisites.

    Raises:
        ValueError: If template not found.
    """
    if name not in WORKFLOW_TEMPLATES:
        available = ", ".join(WORKFLOW_TEMPLATES.keys())
        raise ValueError(f"Workflow '{name}' not found. Available: {available}")

    tmpl = WORKFLOW_TEMPLATES[name]
    return {
        "name": name,
        "description": tmpl["description"],
        "estimated_time_minutes": tmpl["estimated_time_minutes"],
        "prerequisites": tmpl["prerequisites"],
        "tools_used": tmpl["tools_used"],
        "steps": tmpl["steps"],
    }
