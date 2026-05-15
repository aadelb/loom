"""Brain Tool Chains — Pre-defined intelligent tool composition patterns.

When the Brain detects certain intent patterns, it can automatically chain
tools together for richer results. For example:
- "deep research on X" → search → fetch top results → summarize
- "security scan X" → nuclei_scan + security_headers + cert_analyze
- "investigate person X" → social_graph + career_trajectory + breach_check
"""

from __future__ import annotations

from typing import Any

# Predefined tool chains for common multi-tool patterns
TOOL_CHAINS: dict[str, dict[str, Any]] = {
    "deep_research": {
        "triggers": ["deep research", "thorough investigation", "comprehensive analysis", "in-depth"],
        "chain": ["research_search", "research_fetch", "research_llm_summarize"],
        "description": "Search → Fetch top results → Summarize",
    },
    "security_audit": {
        "triggers": ["full security scan", "security audit", "comprehensive scan", "pentest"],
        "chain": ["research_nuclei_scan", "research_security_headers", "research_cert_analyze"],
        "description": "Vulnerability scan + Headers check + Cert analysis",
    },
    "person_investigation": {
        "triggers": ["investigate person", "investigate this person", "background check", "who is", "research person", "person investigation"],
        "chain": ["research_social_graph", "research_career_trajectory", "research_breach_check"],
        "description": "Social graph + Career history + Breach exposure",
    },
    "domain_recon": {
        "triggers": ["domain recon", "domain intelligence", "investigate domain", "domain analysis"],
        "chain": ["research_whois", "research_security_headers", "research_nuclei_scan"],
        "description": "WHOIS + Security headers + Vulnerability scan",
    },
    "academic_review": {
        "triggers": ["review paper", "paper analysis", "check paper quality", "academic integrity"],
        "chain": ["research_citation_analysis", "research_retraction_check", "research_predatory_journal_check"],
        "description": "Citation analysis + Retraction check + Journal quality",
    },
    "darkweb_monitoring": {
        "triggers": ["dark web monitor", "darkweb search", "underground mentions", "dark web intelligence"],
        "chain": ["research_dark_forum", "research_leak_scan", "research_darkweb_early_warning"],
        "description": "Forum search + Leak scan + Early warning",
    },
    "content_analysis": {
        "triggers": ["analyze this url", "full page analysis", "extract and summarize"],
        "chain": ["research_fetch", "research_markdown", "research_llm_summarize"],
        "description": "Fetch page → Extract markdown → Summarize",
    },
    "crypto_investigation": {
        "triggers": ["trace wallet", "investigate bitcoin", "crypto forensics", "blockchain trace"],
        "chain": ["research_crypto_trace", "research_threat_intel"],
        "description": "Blockchain trace + Threat intel correlation",
    },
    "cve_lookup": {
        "triggers": ["cve", "cves", "vulnerability", "exploit", "log4j", "zero-day", "0day"],
        "chain": ["research_cve_lookup", "research_exploit_search"],
        "description": "CVE lookup + Exploit search",
    },
}


def match_chain(query: str) -> dict[str, Any] | None:
    """Check if a query matches a predefined tool chain.

    Returns the chain definition if matched, None otherwise.
    """
    query_lower = query.lower()

    for chain_name, chain_def in TOOL_CHAINS.items():
        for trigger in chain_def["triggers"]:
            if trigger in query_lower:
                return {
                    "chain_name": chain_name,
                    "tools": chain_def["chain"],
                    "description": chain_def["description"],
                }

    return None


def get_chain_tools(chain_name: str) -> list[str]:
    """Get tool list for a named chain."""
    chain = TOOL_CHAINS.get(chain_name)
    if chain:
        return chain["chain"]
    return []
