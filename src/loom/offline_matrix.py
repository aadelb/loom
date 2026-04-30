"""Offline capability matrix — which tools work without network.

REQ-095: Document which tools work offline (cache only), which need network
but can fallback, which require live network.

Three capability levels:
  - full_offline: Works completely offline using local/cached data only
  - cache_fallback: Needs network but can serve cached results if down
  - network_required: Requires live network, no offline mode available
"""

from __future__ import annotations

from typing import Any

CAPABILITY_LEVELS = {
    "full_offline": "Works completely offline using cached data",
    "cache_fallback": "Needs network but can serve stale cache if down",
    "network_required": "Requires live network, no offline mode",
}

TOOL_CAPABILITIES: dict[str, str] = {
    # ========== FULL OFFLINE (local computation only) ==========
    # Text analysis & NLP (local)
    "research_text_analyze": "full_offline",
    "research_stylometry": "full_offline",
    "research_deception_detect": "full_offline",
    "research_detect_language": "full_offline",
    "research_geoip_local": "full_offline",
    "research_persona_profile": "full_offline",
    "research_radicalization_detect": "full_offline",
    "research_sentiment_deep": "full_offline",
    "research_network_persona": "full_offline",
    "research_psycholinguistic": "full_offline",
    # Text extraction & processing
    "research_pdf_extract": "full_offline",
    "research_pdf_search": "full_offline",
    "research_exif_extract": "full_offline",
    "research_ocr_extract": "full_offline",
    # HCS (Helpfulness Compliance Score) scoring
    "research_hcs_score": "full_offline",
    # Cache & config management
    "research_cache_stats": "full_offline",
    "research_cache_clear": "full_offline",
    "research_config_get": "full_offline",
    "research_config_set": "full_offline",
    # Session management
    "research_session_list": "full_offline",
    # Server health
    "research_health_check": "full_offline",
    # Utility tools (local computation)
    "research_password_check": "full_offline",
    "research_format_smuggle": "full_offline",
    "research_refusal_detector": "full_offline",
    "research_stack_reframe": "full_offline",
    "research_prompt_reframe": "full_offline",
    "research_fingerprint_model": "full_offline",
    "research_jailbreak_library": "full_offline",
    "research_open_access": "full_offline",
    # Synthesis & generation
    "research_propaganda_detector": "full_offline",
    "research_synth_echo": "full_offline",
    "research_culture_dna": "full_offline",
    # Metrics (local)
    "research_metrics": "full_offline",
    # Salary synthesis (if LLM-agnostic)
    "research_salary_synthesize": "full_offline",
    # Report generation from cached data
    "research_deception_job_scan": "full_offline",
    # Grant forensics (analytical, not live)
    "research_grant_forensics": "full_offline",
    # Academic integrity (local analysis)
    "research_monoculture_detect": "full_offline",
    "research_review_cartel": "full_offline",
    "research_data_fabrication": "full_offline",
    # HCS-10 extended (analytical)
    "research_ideological_drift": "full_offline",
    "research_author_clustering": "full_offline",
    "research_citation_cartography": "full_offline",
    # Infrastructure analysis (offline analysis)
    "research_output_consistency": "full_offline",
    # Utility/helper
    "research_save_note": "full_offline",
    "research_list_notebooks": "full_offline",
    "research_slack_notify": "full_offline",
    "research_email_report": "full_offline",
    "research_usage_report": "full_offline",
    "research_stripe_balance": "full_offline",
    # Stego detection (image analysis, no network)
    "research_stego_detect": "full_offline",
    # Bias lens
    "research_bias_lens": "full_offline",

    # ========== CACHE FALLBACK (prefers network, can use cache) ==========
    # Search tools
    "research_search": "cache_fallback",
    "research_multi_search": "cache_fallback",
    "research_ghost_protocol": "cache_fallback",
    "research_sec_tracker": "cache_fallback",
    "research_knowledge_graph": "cache_fallback",
    "research_fact_check": "cache_fallback",
    "research_trend_predict": "cache_fallback",
    "research_rss_search": "cache_fallback",
    # Fetch-based tools (network preferred, cache fallback)
    "research_fetch": "cache_fallback",
    "research_deep": "cache_fallback",
    "research_markdown": "cache_fallback",
    "research_dead_content": "cache_fallback",
    "research_invisible_web": "cache_fallback",
    "research_js_intel": "cache_fallback",
    "research_infra_correlator": "cache_fallback",
    "research_passive_recon": "cache_fallback",
    "research_metadata_forensics": "cache_fallback",
    "research_crypto_trace": "cache_fallback",
    "research_threat_profile": "cache_fallback",
    "research_leak_scan": "cache_fallback",
    "research_social_graph": "cache_fallback",
    "research_company_diligence": "cache_fallback",
    "research_competitive_intel": "cache_fallback",
    "research_supply_chain_risk": "cache_fallback",
    "research_whois": "cache_fallback",
    "research_dns_lookup": "cache_fallback",
    "research_legal_takedown": "cache_fallback",
    "research_content_authenticity": "cache_fallback",
    "research_credential_monitor": "cache_fallback",
    "research_deepfake_checker": "cache_fallback",
    "research_identity_resolve": "cache_fallback",
    "research_narrative_tracker": "cache_fallback",
    "research_bot_detector": "cache_fallback",
    "research_censorship_detector": "cache_fallback",
    "research_deleted_social": "cache_fallback",
    "research_robots_archaeology": "cache_fallback",
    "research_interviewer_profiler": "cache_fallback",
    "research_cert_analyze": "cache_fallback",
    "research_security_headers": "cache_fallback",
    "research_temporal_anomaly": "cache_fallback",
    "research_breach_check": "cache_fallback",
    "research_prompt_injection_test": "cache_fallback",
    "research_model_fingerprint": "cache_fallback",
    "research_bias_probe": "cache_fallback",
    "research_safety_filter_map": "cache_fallback",
    "research_compliance_check": "cache_fallback",
    "research_hallucination_benchmark": "cache_fallback",
    "research_adversarial_robustness": "cache_fallback",
    "research_social_engineering_score": "cache_fallback",
    "research_behavioral_fingerprint": "cache_fallback",
    "research_citation_analysis": "cache_fallback",
    "research_retraction_check": "cache_fallback",
    "research_predatory_journal_check": "cache_fallback",
    "research_institutional_decay": "cache_fallback",
    "research_shell_funding": "cache_fallback",
    "research_conference_arbitrage": "cache_fallback",
    "research_preprint_manipulation": "cache_fallback",
    "research_darkweb_early_warning": "cache_fallback",
    "research_patch_embargo": "cache_fallback",
    "research_patent_landscape": "cache_fallback",
    "research_dependency_audit": "cache_fallback",
    "research_registry_graveyard": "cache_fallback",
    "research_subdomain_temporal": "cache_fallback",
    "research_commit_analyzer": "cache_fallback",
    "research_change_monitor": "cache_fallback",
    "research_realtime_monitor": "cache_fallback",
    "research_rss_fetch": "cache_fallback",
    "research_social_search": "cache_fallback",
    "research_social_profile": "cache_fallback",
    "research_source_credibility": "cache_fallback",
    "research_information_cascade": "cache_fallback",
    "research_web_time_machine": "cache_fallback",
    "research_influence_operation": "cache_fallback",
    "research_dark_web_bridge": "cache_fallback",
    "research_info_half_life": "cache_fallback",
    "research_search_discrepancy": "cache_fallback",
    "research_funding_signal": "cache_fallback",
    "research_stealth_hire_scanner": "cache_fallback",
    "research_salary_intelligence": "cache_fallback",
    "research_job_search": "cache_fallback",
    "research_job_market": "cache_fallback",
    "research_map_research_to_product": "cache_fallback",
    "research_translate_academic_skills": "cache_fallback",
    "research_career_trajectory": "cache_fallback",
    "research_market_velocity": "cache_fallback",
    "research_optimize_resume": "cache_fallback",
    "research_interview_prep": "cache_fallback",
    "research_capability_mapper": "cache_fallback",
    "research_memorization_scanner": "cache_fallback",
    "research_training_contamination": "cache_fallback",
    "research_model_comparator": "cache_fallback",
    "research_data_poisoning": "cache_fallback",
    "research_wiki_event_correlator": "cache_fallback",
    "research_foia_tracker": "cache_fallback",
    # LLM-based tools (network: API calls)
    "research_llm_summarize": "cache_fallback",
    "research_llm_extract": "cache_fallback",
    "research_llm_classify": "cache_fallback",
    "research_llm_translate": "cache_fallback",
    "research_llm_query_expand": "cache_fallback",
    "research_llm_answer": "cache_fallback",
    "research_llm_embed": "cache_fallback",
    "research_llm_chat": "cache_fallback",
    "research_ask_all_llms": "cache_fallback",
    "research_ask_all_models": "cache_fallback",
    "research_auto_reframe": "cache_fallback",
    "research_find_experts": "cache_fallback",
    "research_generate_report": "cache_fallback",
    # CVE & vulnerability lookups (search API)
    "research_cve_lookup": "cache_fallback",
    "research_cve_detail": "cache_fallback",
    "research_vuln_intel": "cache_fallback",
    "research_urlhaus_search": "cache_fallback",
    "research_urlhaus_check": "cache_fallback",
    # Threat intelligence tools
    "research_domain_reputation": "cache_fallback",
    "research_ioc_enrich": "cache_fallback",
    # Exa find_similar
    "find_similar_exa": "cache_fallback",

    # ========== NETWORK REQUIRED (no offline mode) ==========
    # Spider tools
    "research_spider": "network_required",
    # Stealth/dynamic fetch
    "research_camoufox": "network_required",
    "research_botasaurus": "network_required",
    # Dark web
    "research_dark_forum": "network_required",
    "research_onion_discover": "network_required",
    "research_cipher_mirror": "network_required",
    "research_forum_cortex": "network_required",
    "research_onion_spectra": "network_required",
    "research_ghost_weave": "network_required",
    "research_dead_drop_scanner": "network_required",
    # GitHub
    "research_github": "network_required",
    "research_github_readme": "network_required",
    "research_github_releases": "network_required",
    "research_github_secrets": "network_required",
    "research_cloud_enum": "network_required",
    # Tor network
    "research_tor_status": "network_required",
    "research_tor_new_identity": "network_required",
    # Network scanning
    "research_nmap_scan": "network_required",
    # Screenshot (requires browser)
    "research_screenshot": "network_required",
    # Session management (browser sessions)
    "research_session_open": "network_required",
    "research_session_close": "network_required",
    # Infrastructure/cloud tools
    "research_cloud_enum": "network_required",
    "research_whois_correlator": "network_required",
    "research_talent_migration": "network_required",
    "research_funding_pipeline": "network_required",
    # Media tools
    "research_transcribe": "network_required",
    "research_convert_document": "network_required",
    "research_image_analyze": "network_required",
    "research_text_to_speech": "network_required",
    "research_tts_voices": "network_required",
    # Video
    "fetch_youtube_transcript": "network_required",
    # Infrastructure
    "research_vastai_search": "network_required",
    "research_vastai_status": "network_required",
    "research_vercel_status": "network_required",
    # Audit export
    "research_audit_export": "network_required",
    # Extra tools
    "research_adaptive_reframe": "network_required",
    "research_crescendo_chain": "network_required",
    "research_model_vulnerability_profile": "network_required",
    "research_ip_reputation": "network_required",
    "research_ip_geolocation": "network_required",
    "research_dark_market_monitor": "network_required",
    "research_ransomware_tracker": "network_required",
    "research_phishing_mapper": "network_required",
    "research_botnet_tracker": "network_required",
    "research_malware_intel": "network_required",
    "research_wayback": "network_required",
}


def get_tool_capability(tool_name: str) -> str:
    """Get offline capability level for a tool.

    Args:
        tool_name: Name of the tool (e.g., "research_fetch")

    Returns:
        Capability level: "full_offline", "cache_fallback", or "network_required"
    """
    return TOOL_CAPABILITIES.get(tool_name, "network_required")


def get_offline_tools() -> list[str]:
    """Get all tools that work fully offline.

    Returns:
        List of tool names that have full_offline capability
    """
    return sorted([t for t, c in TOOL_CAPABILITIES.items() if c == "full_offline"])


def get_cache_fallback_tools() -> list[str]:
    """Get all tools that can use cache fallback.

    Returns:
        List of tool names that have cache_fallback capability
    """
    return sorted(
        [t for t, c in TOOL_CAPABILITIES.items() if c == "cache_fallback"]
    )


def get_network_required_tools() -> list[str]:
    """Get all tools that require live network.

    Returns:
        List of tool names that require network
    """
    return sorted(
        [t for t, c in TOOL_CAPABILITIES.items() if c == "network_required"]
    )


def get_capability_summary() -> dict[str, int]:
    """Count tools by capability level.

    Returns:
        Dict with counts: {"full_offline": N, "cache_fallback": N, "network_required": N}
    """
    counts: dict[str, int] = {"full_offline": 0, "cache_fallback": 0, "network_required": 0}
    for cap in TOOL_CAPABILITIES.values():
        counts[cap] = counts.get(cap, 0) + 1
    return counts


def is_tool_available_offline(tool_name: str) -> bool:
    """Check if a tool can work without any network access.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool has full_offline capability, False otherwise
    """
    return get_tool_capability(tool_name) == "full_offline"


def can_tool_use_cache_fallback(tool_name: str) -> bool:
    """Check if a tool can fallback to cache on network failure.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is full_offline or cache_fallback, False if network_required
    """
    cap = get_tool_capability(tool_name)
    return cap in ("full_offline", "cache_fallback")
