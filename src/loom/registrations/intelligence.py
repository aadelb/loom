"""Registration module for intelligence tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.intelligence")


def register_intelligence_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 95 intelligence tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.anomaly_detector import research_detect_anomalies, research_detect_text_anomalies
        mcp.tool()(wrap_tool(research_detect_anomalies))
        record_success("intelligence", "research_detect_anomalies")
        mcp.tool()(wrap_tool(research_detect_text_anomalies))
        record_success("intelligence", "research_detect_text_anomalies")
    except (ImportError, AttributeError) as e:
        log.debug("skip anomaly_detector: %s", e)
        record_failure("intelligence", "anomaly_detector", str(e))
    try:
        from loom.tools.breach_check import research_breach_check, research_password_check
        mcp.tool()(wrap_tool(research_breach_check))
        record_success("intelligence", "research_breach_check")
        mcp.tool()(wrap_tool(research_password_check))
        record_success("intelligence", "research_password_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip breach_check: %s", e)
        record_failure("intelligence", "breach_check", str(e))
    try:
        from loom.tools.cert_analyzer import research_cert_analyze
        mcp.tool()(wrap_tool(research_cert_analyze))
        record_success("intelligence", "research_cert_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip cert_analyzer: %s", e)
        record_failure("intelligence", "cert_analyzer", str(e))
    try:
        from loom.tools.change_monitor import research_change_monitor
        mcp.tool()(wrap_tool(research_change_monitor))
        record_success("intelligence", "research_change_monitor")
    except (ImportError, AttributeError) as e:
        log.debug("skip change_monitor: %s", e)
        record_failure("intelligence", "change_monitor", str(e))
    try:
        from loom.tools.cipher_mirror import research_cipher_mirror
        mcp.tool()(wrap_tool(research_cipher_mirror))
        record_success("intelligence", "research_cipher_mirror")
    except (ImportError, AttributeError) as e:
        log.debug("skip cipher_mirror_mod: %s", e)
        record_failure("intelligence", "cipher_mirror", str(e))
    try:
        from loom.tools.company_intel import research_company_diligence, research_salary_intelligence
        mcp.tool()(wrap_tool(research_company_diligence))
        record_success("intelligence", "research_company_diligence")
        mcp.tool()(wrap_tool(research_salary_intelligence))
        record_success("intelligence", "research_salary_intelligence")
    except (ImportError, AttributeError) as e:
        log.debug("skip company_intel: %s", e)
        record_failure("intelligence", "company_intel", str(e))
    try:
        from loom.tools.competitive_intel import research_competitive_intel
        mcp.tool()(wrap_tool(research_competitive_intel))
        record_success("intelligence", "research_competitive_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip competitive_intel: %s", e)
        record_failure("intelligence", "competitive_intel", str(e))
    try:
        from loom.tools.crypto_trace import research_crypto_trace
        mcp.tool()(wrap_tool(research_crypto_trace))
        record_success("intelligence", "research_crypto_trace")
    except (ImportError, AttributeError) as e:
        log.debug("skip crypto_trace: %s", e)
        record_failure("intelligence", "crypto_trace", str(e))
    try:
        from loom.tools.cve_lookup import research_cve_lookup, research_cve_detail
        mcp.tool()(wrap_tool(research_cve_lookup))
        record_success("intelligence", "research_cve_lookup")
        mcp.tool()(wrap_tool(research_cve_detail))
        record_success("intelligence", "research_cve_detail")
    except (ImportError, AttributeError) as e:
        log.debug("skip cve_lookup_mod: %s", e)
        record_failure("intelligence", "cve_lookup", str(e))
    try:
        from loom.tools.dark_forum import research_dark_forum
        mcp.tool()(wrap_tool(research_dark_forum))
        record_success("intelligence", "research_dark_forum")
    except (ImportError, AttributeError) as e:
        log.debug("skip dark_forum: %s", e)
        record_failure("intelligence", "dark_forum", str(e))
    try:
        from loom.tools.dark_recon import research_torbot, research_amass_enum, research_amass_intel
        mcp.tool()(wrap_tool(research_torbot))
        record_success("intelligence", "research_torbot")
        mcp.tool()(wrap_tool(research_amass_enum))
        record_success("intelligence", "research_amass_enum")
        mcp.tool()(wrap_tool(research_amass_intel))
        record_success("intelligence", "research_amass_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip dark_recon_mod: %s", e)
        record_failure("intelligence", "dark_recon", str(e))
    try:
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning
        mcp.tool()(wrap_tool(research_darkweb_early_warning))
        record_success("intelligence", "research_darkweb_early_warning")
    except (ImportError, AttributeError) as e:
        log.debug("skip darkweb_early_warning_mod: %s", e)
        record_failure("intelligence", "darkweb_early_warning", str(e))
    try:
        from loom.tools.domain_intel import research_whois
        mcp.tool()(wrap_tool(research_whois))
        record_success("intelligence", "research_whois")
    except (ImportError, AttributeError) as e:
        log.debug("skip domain_intel: %s", e)
        record_failure("intelligence", "domain_intel", str(e))
    try:
        from loom.tools.evidence_analyzer import research_analyze_evidence
        mcp.tool()(wrap_tool(research_analyze_evidence))
        record_success("intelligence", "research_analyze_evidence")
    except (ImportError, AttributeError) as e:
        log.debug("skip evidence_analyzer: %s", e)
        record_failure("intelligence", "evidence_analyzer", str(e))
    try:
        from loom.tools.fact_checker import research_fact_check
        mcp.tool()(wrap_tool(research_fact_check))
        record_success("intelligence", "research_fact_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip fact_checker: %s", e)
        record_failure("intelligence", "fact_checker", str(e))
    try:
        from loom.tools.infra_analysis import research_registry_graveyard, research_subdomain_temporal, research_commit_analyzer
        mcp.tool()(wrap_tool(research_registry_graveyard))
        record_success("intelligence", "research_registry_graveyard")
        mcp.tool()(wrap_tool(research_subdomain_temporal))
        record_success("intelligence", "research_subdomain_temporal")
        mcp.tool()(wrap_tool(research_commit_analyzer))
        record_success("intelligence", "research_commit_analyzer")
    except (ImportError, AttributeError) as e:
        log.debug("skip infra_analysis_mod: %s", e)
        record_failure("intelligence", "infra_analysis", str(e))
    try:
        from loom.tools.infra_correlator import research_infra_correlator
        mcp.tool()(wrap_tool(research_infra_correlator))
        record_success("intelligence", "research_infra_correlator")
    except (ImportError, AttributeError) as e:
        log.debug("skip infra_correlator: %s", e)
        record_failure("intelligence", "infra_correlator", str(e))
    try:
        from loom.tools.ip_intel import research_ip_reputation
        mcp.tool()(wrap_tool(research_ip_reputation))
        record_success("intelligence", "research_ip_reputation")
    except (ImportError, AttributeError) as e:
        log.debug("skip ip_intel: %s", e)
        record_failure("intelligence", "ip_intel", str(e))
    try:
        from loom.tools.knowledge_graph import research_knowledge_graph
        mcp.tool()(wrap_tool(research_knowledge_graph))
        record_success("intelligence", "research_knowledge_graph")
    except (ImportError, AttributeError) as e:
        log.debug("skip knowledge_graph: %s", e)
        record_failure("intelligence", "knowledge_graph", str(e))
    try:
        from loom.tools.leak_scan import research_leak_scan
        mcp.tool()(wrap_tool(research_leak_scan))
        record_success("intelligence", "research_leak_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip leak_scan: %s", e)
        record_failure("intelligence", "leak_scan", str(e))
    try:
        from loom.tools.metadata_forensics import research_metadata_forensics
        mcp.tool()(wrap_tool(research_metadata_forensics))
        record_success("intelligence", "research_metadata_forensics")
    except (ImportError, AttributeError) as e:
        log.debug("skip metadata_forensics: %s", e)
        record_failure("intelligence", "metadata_forensics", str(e))
    try:
        from loom.tools.model_sentiment import research_model_sentiment
        mcp.tool()(wrap_tool(research_model_sentiment))
        record_success("intelligence", "research_model_sentiment")
    except (ImportError, AttributeError) as e:
        log.debug("skip model_sentiment: %s", e)
        record_failure("intelligence", "model_sentiment", str(e))
    try:
        from loom.tools.onion_discover import research_onion_discover
        mcp.tool()(wrap_tool(research_onion_discover))
        record_success("intelligence", "research_onion_discover")
    except (ImportError, AttributeError) as e:
        log.debug("skip onion_discover: %s", e)
        record_failure("intelligence", "onion_discover", str(e))
    try:
        from loom.tools.passive_recon import research_passive_recon
        mcp.tool()(wrap_tool(research_passive_recon))
        record_success("intelligence", "research_passive_recon")
    except (ImportError, AttributeError) as e:
        log.debug("skip passive_recon: %s", e)
        record_failure("intelligence", "passive_recon", str(e))
    try:
        from loom.tools.social_graph import research_social_graph
        mcp.tool()(wrap_tool(research_social_graph))
        record_success("intelligence", "research_social_graph")
    except (ImportError, AttributeError) as e:
        log.debug("skip social_graph: %s", e)
        record_failure("intelligence", "social_graph", str(e))
    try:
        from loom.tools.stego_detect import research_stego_detect
        mcp.tool()(wrap_tool(research_stego_detect))
        record_success("intelligence", "research_stego_detect")
    except (ImportError, AttributeError) as e:
        log.debug("skip stego_detect: %s", e)
        record_failure("intelligence", "stego_detect", str(e))
    try:
        from loom.tools.threat_intel import research_dark_market_monitor, research_malware_bazaar
        mcp.tool()(wrap_tool(research_dark_market_monitor))
        record_success("intelligence", "research_dark_market_monitor")
        mcp.tool()(wrap_tool(research_malware_bazaar))
        record_success("intelligence", "research_malware_bazaar")
    except (ImportError, AttributeError) as e:
        log.debug("skip threat_intel_mod: %s", e)
        record_failure("intelligence", "threat_intel", str(e))
    try:
        from loom.tools.threat_profile import research_threat_profile
        mcp.tool()(wrap_tool(research_threat_profile))
        record_success("intelligence", "research_threat_profile")
    except (ImportError, AttributeError) as e:
        log.debug("skip threat_profile: %s", e)
        record_failure("intelligence", "threat_profile", str(e))
    try:
        from loom.tools.tor import research_tor_status, research_tor_new_identity
        mcp.tool()(wrap_tool(research_tor_status))
        record_success("intelligence", "research_tor_status")
        mcp.tool()(wrap_tool(research_tor_new_identity))
        record_success("intelligence", "research_tor_new_identity")
    except (ImportError, AttributeError) as e:
        log.debug("skip tor_mod: %s", e)
        record_failure("intelligence", "tor", str(e))
    try:
        from loom.tools.trend_predictor import research_trend_predict
        mcp.tool()(wrap_tool(research_trend_predict))
        record_success("intelligence", "research_trend_predict")
    except (ImportError, AttributeError) as e:
        log.debug("skip trend_predictor: %s", e)
        record_failure("intelligence", "trend_predictor", str(e))
    try:
        from loom.tools.trend_forecaster import research_trend_forecast
        mcp.tool()(wrap_tool(research_trend_forecast))
        record_success("intelligence", "research_trend_forecast")
    except (ImportError, AttributeError) as e:
        log.debug("skip trend_forecaster: %s", e)
        record_failure("intelligence", "trend_forecaster", str(e))
    try:
        from loom.tools.universal_orchestrator import research_orchestrate_smart
        mcp.tool()(wrap_tool(research_orchestrate_smart))
        record_success("intelligence", "research_orchestrate_smart")
    except (ImportError, AttributeError) as e:
        log.debug("skip universal_orchestrator: %s", e)
        record_failure("intelligence", "universal_orchestrator", str(e))
    try:
        from loom.tools.semantic_router import research_semantic_route, research_semantic_batch_route, research_semantic_router_rebuild
        mcp.tool()(wrap_tool(research_semantic_route))
        record_success("intelligence", "research_semantic_route")
        mcp.tool()(wrap_tool(research_semantic_batch_route))
        record_success("intelligence", "research_semantic_batch_route")
        mcp.tool()(wrap_tool(research_semantic_router_rebuild))
        record_success("intelligence", "research_semantic_router_rebuild")
    except (ImportError, AttributeError) as e:
        log.debug("skip semantic_router: %s", e)
        record_failure("intelligence", "semantic_router", str(e))
    try:
        from loom.tools.urlhaus_lookup import research_urlhaus_check, research_urlhaus_search
        mcp.tool()(wrap_tool(research_urlhaus_check))
        record_success("intelligence", "research_urlhaus_check")
        mcp.tool()(wrap_tool(research_urlhaus_search))
        record_success("intelligence", "research_urlhaus_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip urlhaus_lookup_mod: %s", e)
        record_failure("intelligence", "urlhaus_lookup", str(e))
    try:
        from loom.tools.vuln_intel import research_vuln_intel
        mcp.tool()(wrap_tool(research_vuln_intel))
        record_success("intelligence", "research_vuln_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip vuln_intel_mod: %s", e)
        record_failure("intelligence", "vuln_intel", str(e))
    try:
        from loom.tools.geoip_local import research_geoip_local
        mcp.tool()(wrap_tool(research_geoip_local))
        record_success("intelligence", "research_geoip_local")
    except (ImportError, AttributeError) as e:
        log.debug("skip geoip_local: %s", e)
        record_failure("intelligence", "geoip_local", str(e))
    try:
        from loom.tools.image_intel import research_exif_extract
        mcp.tool()(wrap_tool(research_exif_extract))
        record_success("intelligence", "research_exif_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip image_intel: %s", e)
        record_failure("intelligence", "image_intel", str(e))
    try:
        from loom.tools.epistemic_score import research_epistemic_score
        mcp.tool()(wrap_tool(research_epistemic_score))
        record_success("intelligence", "research_epistemic_score")
    except (ImportError, AttributeError) as e:
        log.debug("skip epistemic_score: %s", e)
        record_failure("intelligence", "epistemic_score", str(e))
    try:
        from loom.tools.singlefile_backend import research_archive_page
        mcp.tool()(wrap_tool(research_archive_page))
        record_success("intelligence", "research_archive_page")
    except (ImportError, AttributeError) as e:
        log.debug("skip singlefile_backend: %s", e)
        record_failure("intelligence", "singlefile_backend", str(e))
    try:
        from loom.tools.yara_backend import research_yara_scan
        mcp.tool()(wrap_tool(research_yara_scan))
        record_success("intelligence", "research_yara_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip yara_backend: %s", e)
        record_failure("intelligence", "yara_backend", str(e))
    try:
        from loom.tools.spiderfoot_backend import research_spiderfoot_scan
        mcp.tool()(wrap_tool(research_spiderfoot_scan))
        record_success("intelligence", "research_spiderfoot_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip spiderfoot_backend: %s", e)
        record_failure("intelligence", "spiderfoot_backend", str(e))
    try:
        from loom.tools.misp_backend import research_misp_lookup
        mcp.tool()(wrap_tool(research_misp_lookup))
        record_success("intelligence", "research_misp_lookup")
    except (ImportError, AttributeError) as e:
        log.debug("skip misp_backend: %s", e)
        record_failure("intelligence", "misp_backend", str(e))
    try:
        from loom.tools.social_analyzer_backend import research_social_analyze
        mcp.tool()(wrap_tool(research_social_analyze))
        record_success("intelligence", "research_social_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip social_analyzer_backend: %s", e)
        record_failure("intelligence", "social_analyzer_backend", str(e))
    try:
        from loom.tools.maigret_backend import research_maigret
        mcp.tool()(wrap_tool(research_maigret))
        record_success("intelligence", "research_maigret")
    except (ImportError, AttributeError) as e:
        log.debug("skip maigret_backend: %s", e)
        record_failure("intelligence", "maigret_backend", str(e))
    # ── Trend & Content Analysis Tools ──
    try:
        from loom.tools.content_anomaly import research_content_anomaly
        mcp.tool()(wrap_tool(research_content_anomaly))
        record_success("intelligence", "research_content_anomaly")
    except (ImportError, AttributeError) as e:
        log.debug("skip content_anomaly: %s", e)
        record_failure("intelligence", "content_anomaly", str(e))

    # ── Privacy & Fingerprinting Tools ──
    try:
        from loom.tools.privacy_advanced import research_browser_privacy_score, research_network_anomaly, research_metadata_strip
        mcp.tool()(wrap_tool(research_browser_privacy_score))
        record_success("intelligence", "research_browser_privacy_score")
        mcp.tool()(wrap_tool(research_network_anomaly))
        record_success("intelligence", "research_network_anomaly")
        mcp.tool()(wrap_tool(research_metadata_strip))
        record_success("intelligence", "research_metadata_strip")
    except (ImportError, AttributeError) as e:
        log.debug("skip privacy_advanced: %s", e)
        record_failure("intelligence", "privacy_advanced", str(e))
    try:
        from loom.tools.privacy_tools import research_fingerprint_audit, research_privacy_exposure
        mcp.tool()(wrap_tool(research_fingerprint_audit))
        record_success("intelligence", "research_fingerprint_audit")
        mcp.tool()(wrap_tool(research_privacy_exposure))
        record_success("intelligence", "research_privacy_exposure")
    except (ImportError, AttributeError) as e:
        log.debug("skip privacy_tools: %s", e)
        record_failure("intelligence", "privacy_tools", str(e))

    # ── USB & Hardware Monitoring Tools ──
    try:
        from loom.tools.usb_monitor_tool import research_usb_monitor
        mcp.tool()(wrap_tool(research_usb_monitor))
        record_success("intelligence", "research_usb_monitor")
    except (ImportError, AttributeError) as e:
        log.debug("skip usb_monitor_tool: %s", e)
        record_failure("intelligence", "usb_monitor_tool", str(e))

    # ── Intelligence & Reputation Tools ──
    try:
        from loom.tools.reputation_scorer import research_source_reputation
        mcp.tool()(wrap_tool(research_source_reputation))
        record_success("intelligence", "research_source_reputation")
    except (ImportError, AttributeError) as e:
        log.debug("skip reputation_scorer: %s", e)
        record_failure("intelligence", "reputation_scorer", str(e))

    # ── Compliance & Compliance Tools ──
    try:
        from loom.tools.ai_safety import research_domain_compliance_check
        mcp.tool()(wrap_tool(research_domain_compliance_check))
        record_success("intelligence", "research_domain_compliance_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip ai_safety compliance: %s", e)
        record_failure("intelligence", "ai_safety", str(e))

    log.info("registered intelligence tools count=116")
