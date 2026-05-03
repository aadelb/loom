"""Intelligence and OSINT tools — threat intel, social graphs, breach scanning, etc.

Tools for open-source intelligence, threat profiling, security analysis, and
research infrastructure intelligence.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.intelligence")


def register_intelligence_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 87 intelligence and OSINT tools.

    Includes threat intelligence, social graph analysis, breach scanning,
    domain intelligence, academic integrity, and security research.
    """
    from loom.tools import (
        academic_integrity,
        access_tools,
        breach_check,
        career_intel_mod,
        career_traj_mod,
        cert_analyzer,
        company_intel,
        competitive_intel,
        crypto_trace,
        dark_forum,
        dark_recon,
        darkweb_early_warning,
        deception_detect,
        deception_job_scanner,
        domain_intel,
        gap_tools_academic,
        gap_tools_advanced,
        gap_tools_ai,
        gap_tools_infra,
        hcs10_academic,
        hcs_rubric_tool,
        hcs_scorer,
        identity_resolve,
        infra_correlator,
        invisible_web,
        job_signals,
        leak_scan,
        metadata_forensics,
        onion_discover,
        passive_recon,
        salary_synthesizer,
        security_headers,
        signal_detection,
        social_graph,
        stego_detect,
        stylometry,
        supply_chain,
        supply_chain_intel,
        threat_intel,
        threat_profile,
        urlhaus_lookup_mod,
        vuln_intel_mod,
    )

    # Infrastructure intelligence
    mcp.tool()(wrap_tool(invisible_web.research_invisible_web, "fetch"))
    mcp.tool()(wrap_tool(dark_forum.research_dark_forum, "search"))
    mcp.tool()(wrap_tool(infra_correlator.research_infra_correlator, "fetch"))
    mcp.tool()(wrap_tool(passive_recon.research_passive_recon, "fetch"))
    mcp.tool()(wrap_tool(gap_tools_infra.research_cloud_enum, "fetch"))
    mcp.tool()(wrap_tool(gap_tools_infra.research_github_secrets, "search"))
    mcp.tool()(wrap_tool(gap_tools_infra.research_whois_correlator, "fetch"))
    mcp.tool()(wrap_tool(gap_tools_infra.research_output_consistency, "fetch"))

    # Advanced intelligence
    mcp.tool()(wrap_tool(gap_tools_advanced.research_talent_migration, "fetch"))
    mcp.tool()(wrap_tool(gap_tools_advanced.research_funding_pipeline, "search"))
    mcp.tool()(wrap_tool(gap_tools_advanced.research_jailbreak_library))
    mcp.tool()(wrap_tool(gap_tools_advanced.research_patent_embargo, "fetch"))

    # Academic integrity
    mcp.tool()(wrap_tool(gap_tools_academic.research_ideological_drift))
    mcp.tool()(wrap_tool(gap_tools_academic.research_author_clustering))
    mcp.tool()(wrap_tool(gap_tools_academic.research_citation_cartography))

    # AI capabilities
    mcp.tool()(wrap_tool(gap_tools_ai.research_capability_mapper, "fetch"))
    mcp.tool()(wrap_tool(gap_tools_ai.research_memorization_scanner, "fetch"))
    mcp.tool()(wrap_tool(gap_tools_ai.research_training_contamination, "fetch"))

    # Cryptography and forensics
    mcp.tool()(wrap_tool(onion_discover.research_onion_discover, "fetch"))
    mcp.tool()(wrap_tool(metadata_forensics.research_metadata_forensics, "fetch"))
    mcp.tool()(wrap_tool(crypto_trace.research_crypto_trace, "fetch"))
    mcp.tool()(wrap_tool(stego_detect.research_stego_detect))

    # Threat profiling and tracking
    mcp.tool()(wrap_tool(threat_profile.research_threat_profile, "fetch"))
    mcp.tool()(wrap_tool(threat_intel.research_dark_market_monitor))
    mcp.tool()(wrap_tool(threat_intel.research_ransomware_tracker))
    mcp.tool()(wrap_tool(threat_intel.research_phishing_mapper))
    mcp.tool()(wrap_tool(threat_intel.research_botnet_tracker))
    mcp.tool()(wrap_tool(threat_intel.research_malware_intel))
    mcp.tool()(wrap_tool(threat_intel.research_domain_reputation))
    mcp.tool()(wrap_tool(threat_intel.research_ioc_enrich))

    # Breach and leak detection
    mcp.tool()(wrap_tool(leak_scan.research_leak_scan, "fetch"))

    # Social analysis
    mcp.tool()(wrap_tool(social_graph.research_social_graph, "fetch"))
    mcp.tool()(wrap_tool(stylometry.research_stylometry))
    mcp.tool()(wrap_tool(deception_detect.research_deception_detect))

    # Company and competitive intelligence
    mcp.tool()(wrap_tool(company_intel.research_company_diligence, "search"))
    mcp.tool()(wrap_tool(company_intel.research_salary_intelligence, "search"))
    mcp.tool()(wrap_tool(competitive_intel.research_competitive_intel, "search"))
    mcp.tool()(wrap_tool(supply_chain_intel.research_supply_chain_risk, "fetch"))
    mcp.tool()(wrap_tool(supply_chain_intel.research_patent_landscape, "search"))
    mcp.tool()(wrap_tool(supply_chain_intel.research_dependency_audit, "fetch"))
    mcp.tool()(wrap_tool(supply_chain.research_package_audit))
    mcp.tool()(wrap_tool(supply_chain.research_model_integrity))

    # Domain and infrastructure intelligence
    mcp.tool()(wrap_tool(domain_intel.research_whois, "fetch"))
    mcp.tool()(wrap_tool(domain_intel.research_dns_lookup, "fetch"))
    mcp.tool()(wrap_tool(domain_intel.research_nmap_scan, "fetch"))

    # Dark web reconnaissance
    mcp.tool()(wrap_tool(dark_recon.research_torbot, "fetch"))
    mcp.tool()(wrap_tool(dark_recon.research_amass_enum, "fetch"))
    mcp.tool()(wrap_tool(dark_recon.research_amass_intel, "fetch"))

    # Access and content verification
    mcp.tool()(wrap_tool(access_tools.research_legal_takedown, "fetch"))
    mcp.tool()(wrap_tool(access_tools.research_open_access))
    mcp.tool()(wrap_tool(access_tools.research_content_authenticity, "fetch"))
    mcp.tool()(wrap_tool(access_tools.research_credential_monitor, "fetch"))
    mcp.tool()(wrap_tool(access_tools.research_deepfake_checker, "fetch"))

    # Identity and employment intelligence
    mcp.tool()(wrap_tool(identity_resolve.research_identity_resolve, "fetch"))
    mcp.tool()(wrap_tool(job_signals.research_funding_signal, "search"))
    mcp.tool()(wrap_tool(job_signals.research_stealth_hire_scanner, "search"))
    mcp.tool()(wrap_tool(job_signals.research_interviewer_profiler, "fetch"))

    # Security and vulnerability intelligence
    mcp.tool()(wrap_tool(cert_analyzer.research_cert_analyze, "fetch"))
    mcp.tool()(wrap_tool(security_headers.research_security_headers, "fetch"))
    mcp.tool()(wrap_tool(signal_detection.research_ghost_protocol, "search"))
    mcp.tool()(wrap_tool(signal_detection.research_temporal_anomaly, "fetch"))
    mcp.tool()(wrap_tool(signal_detection.research_sec_tracker, "search"))
    mcp.tool()(wrap_tool(breach_check.research_breach_check, "fetch"))
    mcp.tool()(wrap_tool(breach_check.research_password_check))

    # Academic and research integrity
    mcp.tool()(wrap_tool(academic_integrity.research_citation_analysis, "fetch"))
    mcp.tool()(wrap_tool(academic_integrity.research_retraction_check, "fetch"))
    mcp.tool()(wrap_tool(academic_integrity.research_predatory_journal_check, "fetch"))
    mcp.tool()(wrap_tool(hcs10_academic.research_grant_forensics))
    mcp.tool()(wrap_tool(hcs10_academic.research_monoculture_detect))
    mcp.tool()(wrap_tool(hcs10_academic.research_review_cartel, "fetch"))
    mcp.tool()(wrap_tool(hcs10_academic.research_data_fabrication))
    mcp.tool()(wrap_tool(hcs10_academic.research_institutional_decay, "fetch"))
    mcp.tool()(wrap_tool(hcs10_academic.research_shell_funding, "fetch"))
    mcp.tool()(wrap_tool(hcs10_academic.research_conference_arbitrage, "fetch"))
    mcp.tool()(wrap_tool(hcs10_academic.research_preprint_manipulation, "fetch"))
    mcp.tool()(wrap_tool(hcs_scorer.research_hcs_score, "analysis"))
    mcp.tool()(wrap_tool(hcs_rubric_tool.research_hcs_rubric, "analysis"))

    # Dark web and deception detection
    mcp.tool()(wrap_tool(darkweb_early_warning.research_darkweb_early_warning, "search"))
    mcp.tool()(wrap_tool(deception_job_scanner.research_deception_job_scan))

    # Career and salary intelligence
    mcp.tool()(wrap_tool(salary_synthesizer.research_salary_synthesize, "search"))
    mcp.tool()(wrap_tool(career_intel_mod.research_map_research_to_product, "llm"))
    mcp.tool()(wrap_tool(career_intel_mod.research_translate_academic_skills, "llm"))
    mcp.tool()(wrap_tool(career_traj_mod.research_career_trajectory, "fetch"))
    mcp.tool()(wrap_tool(career_traj_mod.research_market_velocity, "search"))

    # Vulnerability and URL intelligence
    mcp.tool()(wrap_tool(vuln_intel_mod.research_vuln_intel, "search"))
    mcp.tool()(wrap_tool(urlhaus_lookup_mod.research_urlhaus_check, "fetch"))
    mcp.tool()(wrap_tool(urlhaus_lookup_mod.research_urlhaus_search, "search"))

    log.info("registered intelligence tools count=87")
