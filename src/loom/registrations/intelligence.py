"""Registration module for intelligence tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.intelligence")


def register_intelligence_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 86 intelligence tools."""
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
        log.debug("skip dark_recon: %s", e)
        record_failure("intelligence", "dark_recon", str(e))
    try:
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning
        mcp.tool()(wrap_tool(research_darkweb_early_warning))
        record_success("intelligence", "research_darkweb_early_warning")
    except (ImportError, AttributeError) as e:
        log.debug("skip darkweb_early_warning: %s", e)
        record_failure("intelligence", "darkweb_early_warning", str(e))
    try:
        from loom.tools.dead_content import research_dead_content
        mcp.tool()(wrap_tool(research_dead_content))
        record_success("intelligence", "research_dead_content")
    except (ImportError, AttributeError) as e:
        log.debug("skip dead_content: %s", e)
        record_failure("intelligence", "dead_content", str(e))
    try:
        from loom.tools.domain_intel import research_whois, research_dns_lookup, research_nmap_scan
        mcp.tool()(wrap_tool(research_whois))
        record_success("intelligence", "research_whois")
        mcp.tool()(wrap_tool(research_dns_lookup))
        record_success("intelligence", "research_dns_lookup")
        mcp.tool()(wrap_tool(research_nmap_scan))
        record_success("intelligence", "research_nmap_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip domain_intel: %s", e)
        record_failure("intelligence", "domain_intel", str(e))
    try:
        from loom.tools.env_inspector import research_env_inspect, research_env_requirements
        mcp.tool()(wrap_tool(research_env_inspect))
        record_success("intelligence", "research_env_inspect")
        mcp.tool()(wrap_tool(research_env_requirements))
        record_success("intelligence", "research_env_requirements")
    except (ImportError, AttributeError) as e:
        log.debug("skip env_inspector: %s", e)
        record_failure("intelligence", "env_inspector", str(e))
    try:
        from loom.tools.forum_cortex import research_forum_cortex
        mcp.tool()(wrap_tool(research_forum_cortex))
        record_success("intelligence", "research_forum_cortex")
    except (ImportError, AttributeError) as e:
        log.debug("skip forum_cortex_mod: %s", e)
        record_failure("intelligence", "forum_cortex", str(e))
    try:
        from loom.tools.functor_map import research_functor_translate
        mcp.tool()(wrap_tool(research_functor_translate))
        record_success("intelligence", "research_functor_translate")
    except (ImportError, AttributeError) as e:
        log.debug("skip functor_map: %s", e)
        record_failure("intelligence", "functor_map", str(e))
    try:
        from loom.tools.ghost_weave import research_ghost_weave
        mcp.tool()(wrap_tool(research_ghost_weave))
        record_success("intelligence", "research_ghost_weave")
    except (ImportError, AttributeError) as e:
        log.debug("skip ghost_weave_mod: %s", e)
        record_failure("intelligence", "ghost_weave", str(e))
    try:
        from loom.tools.identity_resolve import research_identity_resolve
        mcp.tool()(wrap_tool(research_identity_resolve))
        record_success("intelligence", "research_identity_resolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip identity_resolve: %s", e)
        record_failure("intelligence", "identity_resolve", str(e))
    try:
        from loom.tools.infra_correlator import research_infra_correlator
        mcp.tool()(wrap_tool(research_infra_correlator))
        record_success("intelligence", "research_infra_correlator")
    except (ImportError, AttributeError) as e:
        log.debug("skip infra_correlator: %s", e)
        record_failure("intelligence", "infra_correlator", str(e))
    try:
        from loom.tools.invisible_web import research_invisible_web
        mcp.tool()(wrap_tool(research_invisible_web))
        record_success("intelligence", "research_invisible_web")
    except (ImportError, AttributeError) as e:
        log.debug("skip invisible_web: %s", e)
        record_failure("intelligence", "invisible_web", str(e))
    try:
        from loom.tools.ip_intel import research_ip_reputation, research_ip_geolocation
        mcp.tool()(wrap_tool(research_ip_reputation))
        record_success("intelligence", "research_ip_reputation")
        mcp.tool()(wrap_tool(research_ip_geolocation))
        record_success("intelligence", "research_ip_geolocation")
    except (ImportError, AttributeError) as e:
        log.debug("skip ip_intel_mod: %s", e)
        record_failure("intelligence", "ip_intel", str(e))
    try:
        from loom.tools.knowledge_injector import research_personalize_output, research_adapt_complexity
        mcp.tool()(wrap_tool(research_personalize_output))
        record_success("intelligence", "research_personalize_output")
        mcp.tool()(wrap_tool(research_adapt_complexity))
        record_success("intelligence", "research_adapt_complexity")
    except (ImportError, AttributeError) as e:
        log.debug("skip knowledge_injector: %s", e)
        record_failure("intelligence", "knowledge_injector", str(e))
    try:
        from loom.tools.leak_scan import research_leak_scan
        mcp.tool()(wrap_tool(research_leak_scan))
        record_success("intelligence", "research_leak_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip leak_scan: %s", e)
        record_failure("intelligence", "leak_scan", str(e))
    try:
        from loom.tools.memetic_simulator import research_memetic_simulate
        mcp.tool()(wrap_tool(research_memetic_simulate))
        record_success("intelligence", "research_memetic_simulate")
    except (ImportError, AttributeError) as e:
        log.debug("skip memetic_simulator: %s", e)
        record_failure("intelligence", "memetic_simulator", str(e))
    try:
        from loom.tools.nl_executor import research_do
        mcp.tool()(wrap_tool(research_do))
        record_success("intelligence", "research_do")
    except (ImportError, AttributeError) as e:
        log.debug("skip nl_executor: %s", e)
        record_failure("intelligence", "nl_executor", str(e))
    try:
        from loom.tools.onion_discover import research_onion_discover
        mcp.tool()(wrap_tool(research_onion_discover))
        record_success("intelligence", "research_onion_discover")
    except (ImportError, AttributeError) as e:
        log.debug("skip onion_discover: %s", e)
        record_failure("intelligence", "onion_discover", str(e))
    try:
        from loom.tools.onion_spectra import research_onion_spectra
        mcp.tool()(wrap_tool(research_onion_spectra))
        record_success("intelligence", "research_onion_spectra")
    except (ImportError, AttributeError) as e:
        log.debug("skip onion_spectra_mod: %s", e)
        record_failure("intelligence", "onion_spectra", str(e))
    try:
        from loom.tools.paradox_detector import research_detect_paradox, research_paradox_immunize
        mcp.tool()(wrap_tool(research_detect_paradox))
        record_success("intelligence", "research_detect_paradox")
        mcp.tool()(wrap_tool(research_paradox_immunize))
        record_success("intelligence", "research_paradox_immunize")
    except (ImportError, AttributeError) as e:
        log.debug("skip paradox_detector: %s", e)
        record_failure("intelligence", "paradox_detector", str(e))
    try:
        from loom.tools.parallel_executor import research_parallel_execute, research_parallel_plan_and_execute
        mcp.tool()(wrap_tool(research_parallel_execute))
        record_success("intelligence", "research_parallel_execute")
        mcp.tool()(wrap_tool(research_parallel_plan_and_execute))
        record_success("intelligence", "research_parallel_plan_and_execute")
    except (ImportError, AttributeError) as e:
        log.debug("skip parallel_executor: %s", e)
        record_failure("intelligence", "parallel_executor", str(e))
    try:
        from loom.tools.passive_recon import research_passive_recon
        mcp.tool()(wrap_tool(research_passive_recon))
        record_success("intelligence", "research_passive_recon")
    except (ImportError, AttributeError) as e:
        log.debug("skip passive_recon: %s", e)
        record_failure("intelligence", "passive_recon", str(e))
    try:
        from loom.tools.realtime_monitor import research_realtime_monitor
        mcp.tool()(wrap_tool(research_realtime_monitor))
        record_success("intelligence", "research_realtime_monitor")
    except (ImportError, AttributeError) as e:
        log.debug("skip realtime_monitor: %s", e)
        record_failure("intelligence", "realtime_monitor", str(e))
    try:
        from loom.tools.report_generator import research_generate_report
        mcp.tool()(wrap_tool(research_generate_report))
        record_success("intelligence", "research_generate_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip report_generator: %s", e)
        record_failure("intelligence", "report_generator", str(e))
    try:
        from loom.tools.resilience_predictor import research_predict_resilience
        mcp.tool()(wrap_tool(research_predict_resilience))
        record_success("intelligence", "research_predict_resilience")
    except (ImportError, AttributeError) as e:
        log.debug("skip resilience_predictor: %s", e)
        record_failure("intelligence", "resilience_predictor", str(e))
    try:
        from loom.tools.result_aggregator import research_aggregate_results, research_aggregate_texts
        mcp.tool()(wrap_tool(research_aggregate_results))
        record_success("intelligence", "research_aggregate_results")
        mcp.tool()(wrap_tool(research_aggregate_texts))
        record_success("intelligence", "research_aggregate_texts")
    except (ImportError, AttributeError) as e:
        log.debug("skip result_aggregator: %s", e)
        record_failure("intelligence", "result_aggregator", str(e))
    try:
        from loom.tools.rss_monitor import research_rss_fetch, research_rss_search
        mcp.tool()(wrap_tool(research_rss_fetch))
        record_success("intelligence", "research_rss_fetch")
        mcp.tool()(wrap_tool(research_rss_search))
        record_success("intelligence", "research_rss_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip rss_monitor: %s", e)
        record_failure("intelligence", "rss_monitor", str(e))
    try:
        from loom.tools.safety_predictor import research_predict_safety_update
        mcp.tool()(wrap_tool(research_predict_safety_update))
        record_success("intelligence", "research_predict_safety_update")
    except (ImportError, AttributeError) as e:
        log.debug("skip safety_predictor: %s", e)
        record_failure("intelligence", "safety_predictor", str(e))
    try:
        from loom.tools.security_headers import research_security_headers
        mcp.tool()(wrap_tool(research_security_headers))
        record_success("intelligence", "research_security_headers")
    except (ImportError, AttributeError) as e:
        log.debug("skip security_headers: %s", e)
        record_failure("intelligence", "security_headers", str(e))
    try:
        from loom.tools.signal_detection import research_ghost_protocol, research_temporal_anomaly, research_sec_tracker
        mcp.tool()(wrap_tool(research_ghost_protocol))
        record_success("intelligence", "research_ghost_protocol")
        mcp.tool()(wrap_tool(research_temporal_anomaly))
        record_success("intelligence", "research_temporal_anomaly")
        mcp.tool()(wrap_tool(research_sec_tracker))
        record_success("intelligence", "research_sec_tracker")
    except (ImportError, AttributeError) as e:
        log.debug("skip signal_detection: %s", e)
        record_failure("intelligence", "signal_detection", str(e))
    try:
        from loom.tools.social_graph import research_social_graph
        mcp.tool()(wrap_tool(research_social_graph))
        record_success("intelligence", "research_social_graph")
    except (ImportError, AttributeError) as e:
        log.debug("skip social_graph: %s", e)
        record_failure("intelligence", "social_graph", str(e))
    try:
        from loom.tools.startup_validator import research_validate_startup, research_health_deep
        mcp.tool()(wrap_tool(research_validate_startup))
        record_success("intelligence", "research_validate_startup")
        mcp.tool()(wrap_tool(research_health_deep))
        record_success("intelligence", "research_health_deep")
    except (ImportError, AttributeError) as e:
        log.debug("skip startup_validator: %s", e)
        record_failure("intelligence", "startup_validator", str(e))
    try:
        from loom.tools.strange_attractors import research_attractor_trap
        mcp.tool()(wrap_tool(research_attractor_trap))
        record_success("intelligence", "research_attractor_trap")
    except (ImportError, AttributeError) as e:
        log.debug("skip strange_attractors: %s", e)
        record_failure("intelligence", "strange_attractors", str(e))
    try:
        from loom.tools.supply_chain import research_package_audit, research_model_integrity
        mcp.tool()(wrap_tool(research_package_audit))
        record_success("intelligence", "research_package_audit")
        mcp.tool()(wrap_tool(research_model_integrity))
        record_success("intelligence", "research_model_integrity")
    except (ImportError, AttributeError) as e:
        log.debug("skip supply_chain: %s", e)
        record_failure("intelligence", "supply_chain", str(e))
    try:
        from loom.tools.supply_chain_intel import research_supply_chain_risk, research_patent_landscape, research_dependency_audit
        mcp.tool()(wrap_tool(research_supply_chain_risk))
        record_success("intelligence", "research_supply_chain_risk")
        mcp.tool()(wrap_tool(research_patent_landscape))
        record_success("intelligence", "research_patent_landscape")
        mcp.tool()(wrap_tool(research_dependency_audit))
        record_success("intelligence", "research_dependency_audit")
    except (ImportError, AttributeError) as e:
        log.debug("skip supply_chain_intel: %s", e)
        record_failure("intelligence", "supply_chain_intel", str(e))
    try:
        from loom.tools.threat_intel import research_dark_market_monitor, research_ransomware_tracker, research_phishing_mapper, research_botnet_tracker, research_malware_intel, research_domain_reputation, research_ioc_enrich
        mcp.tool()(wrap_tool(research_dark_market_monitor))
        record_success("intelligence", "research_dark_market_monitor")
        mcp.tool()(wrap_tool(research_ransomware_tracker))
        record_success("intelligence", "research_ransomware_tracker")
        mcp.tool()(wrap_tool(research_phishing_mapper))
        record_success("intelligence", "research_phishing_mapper")
        mcp.tool()(wrap_tool(research_botnet_tracker))
        record_success("intelligence", "research_botnet_tracker")
        mcp.tool()(wrap_tool(research_malware_intel))
        record_success("intelligence", "research_malware_intel")
        mcp.tool()(wrap_tool(research_domain_reputation))
        record_success("intelligence", "research_domain_reputation")
        mcp.tool()(wrap_tool(research_ioc_enrich))
        record_success("intelligence", "research_ioc_enrich")
    except (ImportError, AttributeError) as e:
        log.debug("skip threat_intel: %s", e)
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
    log.info("registered intelligence tools count=89")
