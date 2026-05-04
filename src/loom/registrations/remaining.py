"""Registration module for remaining research tools (extras)."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.remaining")


def register_remaining_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 315 remaining research tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.adversarial_craft import research_adversarial_batch, research_craft_adversarial
        mcp.tool()(wrap_tool(research_adversarial_batch))
        record_success("remaining", "research_adversarial_batch")
        mcp.tool()(wrap_tool(research_craft_adversarial))
        record_success("remaining", "research_craft_adversarial")
    except (ImportError, AttributeError) as e:
        log.debug("skip adversarial_craft: %s", e)
        record_failure("remaining", "adversarial_craft", str(e))
    try:
        from loom.tools.adversarial_debate_tool import research_adversarial_debate
        mcp.tool()(wrap_tool(research_adversarial_debate))
        record_success("remaining", "research_adversarial_debate")
    except (ImportError, AttributeError) as e:
        log.debug("skip adversarial_debate_tool: %s", e)
        record_failure("remaining", "adversarial_debate_tool", str(e))
    try:
        from loom.tools.ai_safety import research_bias_probe, research_model_fingerprint, research_prompt_injection_test, research_safety_filter_map
        mcp.tool()(wrap_tool(research_bias_probe))
        record_success("remaining", "research_bias_probe")
        mcp.tool()(wrap_tool(research_model_fingerprint))
        record_success("remaining", "research_model_fingerprint")
        mcp.tool()(wrap_tool(research_prompt_injection_test))
        record_success("remaining", "research_prompt_injection_test")
        mcp.tool()(wrap_tool(research_safety_filter_map))
        record_success("remaining", "research_safety_filter_map")
    except (ImportError, AttributeError) as e:
        log.debug("skip ai_safety: %s", e)
        record_failure("remaining", "ai_safety", str(e))
    try:
        from loom.tools.ai_safety_extended import research_adversarial_robustness, research_hallucination_benchmark
        mcp.tool()(wrap_tool(research_adversarial_robustness))
        record_success("remaining", "research_adversarial_robustness")
        mcp.tool()(wrap_tool(research_hallucination_benchmark))
        record_success("remaining", "research_hallucination_benchmark")
    except (ImportError, AttributeError) as e:
        log.debug("skip ai_safety_extended: %s", e)
        record_failure("remaining", "ai_safety_extended", str(e))
    try:
        from loom.tools.anomaly_detector import research_detect_anomalies, research_detect_text_anomalies
        mcp.tool()(wrap_tool(research_detect_anomalies))
        record_success("remaining", "research_detect_anomalies")
        mcp.tool()(wrap_tool(research_detect_text_anomalies))
        record_success("remaining", "research_detect_text_anomalies")
    except (ImportError, AttributeError) as e:
        log.debug("skip anomaly_detector: %s", e)
        record_failure("remaining", "anomaly_detector", str(e))
    try:
        from loom.tools.api_fuzzer import research_fuzz_api, research_fuzz_report
        mcp.tool()(wrap_tool(research_fuzz_api))
        record_success("remaining", "research_fuzz_api")
        mcp.tool()(wrap_tool(research_fuzz_report))
        record_success("remaining", "research_fuzz_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip api_fuzzer: %s", e)
        record_failure("remaining", "api_fuzzer", str(e))
    try:
        from loom.tools.attack_economy import research_economy_balance, research_economy_leaderboard, research_economy_submit
        mcp.tool()(wrap_tool(research_economy_balance))
        record_success("remaining", "research_economy_balance")
        mcp.tool()(wrap_tool(research_economy_leaderboard))
        record_success("remaining", "research_economy_leaderboard")
        mcp.tool()(wrap_tool(research_economy_submit))
        record_success("remaining", "research_economy_submit")
    except (ImportError, AttributeError) as e:
        log.debug("skip attack_economy: %s", e)
        record_failure("remaining", "attack_economy", str(e))
    try:
        from loom.tools.audit_log import research_audit_export, research_audit_query, research_audit_record
        mcp.tool()(wrap_tool(research_audit_export))
        record_success("remaining", "research_audit_export")
        mcp.tool()(wrap_tool(research_audit_query))
        record_success("remaining", "research_audit_query")
        mcp.tool()(wrap_tool(research_audit_record))
        record_success("remaining", "research_audit_record")
    except (ImportError, AttributeError) as e:
        log.debug("skip audit_log: %s", e)
        record_failure("remaining", "audit_log", str(e))
    try:
        from loom.tools.auto_params import research_auto_params, research_inspect_tool
        mcp.tool()(wrap_tool(research_auto_params))
        record_success("remaining", "research_auto_params")
        mcp.tool()(wrap_tool(research_inspect_tool))
        record_success("remaining", "research_inspect_tool")
    except (ImportError, AttributeError) as e:
        log.debug("skip auto_params: %s", e)
        record_failure("remaining", "auto_params", str(e))
    try:
        from loom.tools.backup_system import research_backup_create, research_backup_list, research_backup_restore
        mcp.tool()(wrap_tool(research_backup_create))
        record_success("remaining", "research_backup_create")
        mcp.tool()(wrap_tool(research_backup_list))
        record_success("remaining", "research_backup_list")
        mcp.tool()(wrap_tool(research_backup_restore))
        record_success("remaining", "research_backup_restore")
    except (ImportError, AttributeError) as e:
        log.debug("skip backup_system: %s", e)
        record_failure("remaining", "backup_system", str(e))
    try:
        from loom.tools.benchmark_datasets import research_load_benchmark, research_run_benchmark
        mcp.tool()(wrap_tool(research_load_benchmark))
        record_success("remaining", "research_load_benchmark")
        mcp.tool()(wrap_tool(research_run_benchmark))
        record_success("remaining", "research_run_benchmark")
    except (ImportError, AttributeError) as e:
        log.debug("skip benchmark_datasets: %s", e)
        record_failure("remaining", "benchmark_datasets", str(e))
    try:
        from loom.tools.billing import research_stripe_balance
        mcp.tool()(wrap_tool(research_stripe_balance))
        record_success("remaining", "research_stripe_balance")
    except (ImportError, AttributeError) as e:
        log.debug("skip billing: %s", e)
        record_failure("remaining", "billing", str(e))
    try:
        from loom.tools.breach_check import research_breach_check, research_password_check
        mcp.tool()(wrap_tool(research_breach_check))
        record_success("remaining", "research_breach_check")
        mcp.tool()(wrap_tool(research_password_check))
        record_success("remaining", "research_password_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip breach_check: %s", e)
        record_failure("remaining", "breach_check", str(e))
    try:
        from loom.tools.cache_analytics import research_cache_analyze, research_cache_optimize
        mcp.tool()(wrap_tool(research_cache_analyze))
        record_success("remaining", "research_cache_analyze")
        mcp.tool()(wrap_tool(research_cache_optimize))
        record_success("remaining", "research_cache_optimize")
    except (ImportError, AttributeError) as e:
        log.debug("skip cache_analytics: %s", e)
        record_failure("remaining", "cache_analytics", str(e))
    try:
        from loom.tools.cache_mgmt import research_cache_clear
        mcp.tool()(wrap_tool(research_cache_clear))
        record_success("remaining", "research_cache_clear")
    except (ImportError, AttributeError) as e:
        log.debug("skip cache_mgmt: %s", e)
        record_failure("remaining", "cache_mgmt", str(e))
    try:
        from loom.tools.camelot_backend import research_table_extract
        mcp.tool()(wrap_tool(research_table_extract))
        record_success("remaining", "research_table_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip camelot_backend: %s", e)
        record_failure("remaining", "camelot_backend", str(e))
    try:
        from loom.tools.capability_matrix import research_capability_matrix, research_find_tools_by_capability
        mcp.tool()(wrap_tool(research_capability_matrix))
        record_success("remaining", "research_capability_matrix")
        mcp.tool()(wrap_tool(research_find_tools_by_capability))
        record_success("remaining", "research_find_tools_by_capability")
    except (ImportError, AttributeError) as e:
        log.debug("skip capability_matrix: %s", e)
        record_failure("remaining", "capability_matrix", str(e))
    try:
        from loom.tools.censys_backend import research_censys_host, research_censys_search
        mcp.tool()(wrap_tool(research_censys_host))
        record_success("remaining", "research_censys_host")
        mcp.tool()(wrap_tool(research_censys_search))
        record_success("remaining", "research_censys_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip censys_backend: %s", e)
        record_failure("remaining", "censys_backend", str(e))
    try:
        from loom.tools.cert_analyzer import research_cert_analyze
        mcp.tool()(wrap_tool(research_cert_analyze))
        record_success("remaining", "research_cert_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip cert_analyzer: %s", e)
        record_failure("remaining", "cert_analyzer", str(e))
    try:
        from loom.tools.change_monitor import research_change_monitor
        mcp.tool()(wrap_tool(research_change_monitor))
        record_success("remaining", "research_change_monitor")
    except (ImportError, AttributeError) as e:
        log.debug("skip change_monitor: %s", e)
        record_failure("remaining", "change_monitor", str(e))
    try:
        from loom.tools.cipher_mirror import research_cipher_mirror
        mcp.tool()(wrap_tool(research_cipher_mirror))
        record_success("remaining", "research_cipher_mirror")
    except (ImportError, AttributeError) as e:
        log.debug("skip cipher_mirror: %s", e)
        record_failure("remaining", "cipher_mirror", str(e))
    try:
        from loom.tools.cli_autocomplete import research_generate_completions, research_tool_help
        mcp.tool()(wrap_tool(research_generate_completions))
        record_success("remaining", "research_generate_completions")
        mcp.tool()(wrap_tool(research_tool_help))
        record_success("remaining", "research_tool_help")
    except (ImportError, AttributeError) as e:
        log.debug("skip cli_autocomplete: %s", e)
        record_failure("remaining", "cli_autocomplete", str(e))
    try:
        from loom.tools.coevolution import research_coevolve
        mcp.tool()(wrap_tool(research_coevolve))
        record_success("remaining", "research_coevolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip coevolution: %s", e)
        record_failure("remaining", "coevolution", str(e))
    try:
        from loom.tools.company_intel import research_company_diligence, research_salary_intelligence
        mcp.tool()(wrap_tool(research_company_diligence))
        record_success("remaining", "research_company_diligence")
        mcp.tool()(wrap_tool(research_salary_intelligence))
        record_success("remaining", "research_salary_intelligence")
    except (ImportError, AttributeError) as e:
        log.debug("skip company_intel: %s", e)
        record_failure("remaining", "company_intel", str(e))
    try:
        from loom.tools.competitive_intel import research_competitive_intel
        mcp.tool()(wrap_tool(research_competitive_intel))
        record_success("remaining", "research_competitive_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip competitive_intel: %s", e)
        record_failure("remaining", "competitive_intel", str(e))
    try:
        from loom.tools.competitive_monitor import research_competitive_advantage, research_monitor_competitors
        mcp.tool()(wrap_tool(research_competitive_advantage))
        record_success("remaining", "research_competitive_advantage")
        mcp.tool()(wrap_tool(research_monitor_competitors))
        record_success("remaining", "research_monitor_competitors")
    except (ImportError, AttributeError) as e:
        log.debug("skip competitive_monitor: %s", e)
        record_failure("remaining", "competitive_monitor", str(e))
    try:
        from loom.tools.compliance_report import research_audit_trail, research_compliance_report
        mcp.tool()(wrap_tool(research_audit_trail))
        record_success("remaining", "research_audit_trail")
        mcp.tool()(wrap_tool(research_compliance_report))
        record_success("remaining", "research_compliance_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip compliance_report: %s", e)
        record_failure("remaining", "compliance_report", str(e))
    try:
        from loom.tools.composition_optimizer import research_optimize_workflow, research_optimizer_rebuild, research_parallel_plan
        mcp.tool()(wrap_tool(research_optimize_workflow))
        record_success("remaining", "research_optimize_workflow")
        mcp.tool()(wrap_tool(research_optimizer_rebuild))
        record_success("remaining", "research_optimizer_rebuild")
        mcp.tool()(wrap_tool(research_parallel_plan))
        record_success("remaining", "research_parallel_plan")
    except (ImportError, AttributeError) as e:
        log.debug("skip composition_optimizer: %s", e)
        record_failure("remaining", "composition_optimizer", str(e))
    try:
        from loom.tools.config_reload import research_config_check, research_config_diff, research_config_watch
        mcp.tool()(wrap_tool(research_config_check))
        record_success("remaining", "research_config_check")
        mcp.tool()(wrap_tool(research_config_diff))
        record_success("remaining", "research_config_diff")
        mcp.tool()(wrap_tool(research_config_watch))
        record_success("remaining", "research_config_watch")
    except (ImportError, AttributeError) as e:
        log.debug("skip config_reload: %s", e)
        record_failure("remaining", "config_reload", str(e))
    try:
        from loom.tools.cost_estimator import research_cost_summary, research_estimate_cost
        mcp.tool()(wrap_tool(research_cost_summary))
        record_success("remaining", "research_cost_summary")
        mcp.tool()(wrap_tool(research_estimate_cost))
        record_success("remaining", "research_estimate_cost")
    except (ImportError, AttributeError) as e:
        log.debug("skip cost_estimator: %s", e)
        record_failure("remaining", "cost_estimator", str(e))
    try:
        from loom.tools.creative import research_consensus
        mcp.tool()(wrap_tool(research_consensus))
        record_success("remaining", "research_consensus")
    except (ImportError, AttributeError) as e:
        log.debug("skip creative: %s", e)
        record_failure("remaining", "creative", str(e))
    try:
        from loom.tools.creepjs_backend import research_creepjs_audit
        mcp.tool()(wrap_tool(research_creepjs_audit))
        record_success("remaining", "research_creepjs_audit")
    except (ImportError, AttributeError) as e:
        log.debug("skip creepjs_backend: %s", e)
        record_failure("remaining", "creepjs_backend", str(e))
    try:
        from loom.tools.cross_domain import research_cross_domain
        mcp.tool()(wrap_tool(research_cross_domain))
        record_success("remaining", "research_cross_domain")
    except (ImportError, AttributeError) as e:
        log.debug("skip cross_domain: %s", e)
        record_failure("remaining", "cross_domain", str(e))
    try:
        from loom.tools.crypto_trace import research_crypto_trace
        mcp.tool()(wrap_tool(research_crypto_trace))
        record_success("remaining", "research_crypto_trace")
    except (ImportError, AttributeError) as e:
        log.debug("skip crypto_trace: %s", e)
        record_failure("remaining", "crypto_trace", str(e))
    try:
        from loom.tools.cve_lookup import research_cve_detail, research_cve_lookup
        mcp.tool()(wrap_tool(research_cve_detail))
        record_success("remaining", "research_cve_detail")
        mcp.tool()(wrap_tool(research_cve_lookup))
        record_success("remaining", "research_cve_lookup")
    except (ImportError, AttributeError) as e:
        log.debug("skip cve_lookup: %s", e)
        record_failure("remaining", "cve_lookup", str(e))
    try:
        from loom.tools.dark_forum import research_dark_forum
        mcp.tool()(wrap_tool(research_dark_forum))
        record_success("remaining", "research_dark_forum")
    except (ImportError, AttributeError) as e:
        log.debug("skip dark_forum: %s", e)
        record_failure("remaining", "dark_forum", str(e))
    try:
        from loom.tools.dark_recon import research_amass_enum, research_amass_intel, research_torbot
        mcp.tool()(wrap_tool(research_amass_enum))
        record_success("remaining", "research_amass_enum")
        mcp.tool()(wrap_tool(research_amass_intel))
        record_success("remaining", "research_amass_intel")
        mcp.tool()(wrap_tool(research_torbot))
        record_success("remaining", "research_torbot")
    except (ImportError, AttributeError) as e:
        log.debug("skip dark_recon: %s", e)
        record_failure("remaining", "dark_recon", str(e))
    try:
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning
        mcp.tool()(wrap_tool(research_darkweb_early_warning))
        record_success("remaining", "research_darkweb_early_warning")
    except (ImportError, AttributeError) as e:
        log.debug("skip darkweb_early_warning: %s", e)
        record_failure("remaining", "darkweb_early_warning", str(e))
    try:
        from loom.tools.dead_content import research_dead_content
        mcp.tool()(wrap_tool(research_dead_content))
        record_success("remaining", "research_dead_content")
    except (ImportError, AttributeError) as e:
        log.debug("skip dead_content: %s", e)
        record_failure("remaining", "dead_content", str(e))
    try:
        from loom.tools.deep import research_deep
        mcp.tool()(wrap_tool(research_deep))
        record_success("remaining", "research_deep")
    except (ImportError, AttributeError) as e:
        log.debug("skip deep: %s", e)
        record_failure("remaining", "deep", str(e))
    try:
        from loom.tools.deep_url_analysis import research_deep_url_analysis
        mcp.tool()(wrap_tool(research_deep_url_analysis))
        record_success("remaining", "research_deep_url_analysis")
    except (ImportError, AttributeError) as e:
        log.debug("skip deep_url_analysis: %s", e)
        record_failure("remaining", "deep_url_analysis", str(e))
    try:
        from loom.tools.deepdarkcti_backend import research_dark_cti
        mcp.tool()(wrap_tool(research_dark_cti))
        record_success("remaining", "research_dark_cti")
    except (ImportError, AttributeError) as e:
        log.debug("skip deepdarkcti_backend: %s", e)
        record_failure("remaining", "deepdarkcti_backend", str(e))
    try:
        from loom.tools.deerflow_backend import research_deer_flow
        mcp.tool()(wrap_tool(research_deer_flow))
        record_success("remaining", "research_deer_flow")
    except (ImportError, AttributeError) as e:
        log.debug("skip deerflow_backend: %s", e)
        record_failure("remaining", "deerflow_backend", str(e))
    try:
        from loom.tools.defender_mode import research_defend_test, research_harden_prompt
        mcp.tool()(wrap_tool(research_defend_test))
        record_success("remaining", "research_defend_test")
        mcp.tool()(wrap_tool(research_harden_prompt))
        record_success("remaining", "research_harden_prompt")
    except (ImportError, AttributeError) as e:
        log.debug("skip defender_mode: %s", e)
        record_failure("remaining", "defender_mode", str(e))
    try:
        from loom.tools.deployment import research_deploy_history, research_deploy_record, research_deploy_status
        mcp.tool()(wrap_tool(research_deploy_history))
        record_success("remaining", "research_deploy_history")
        mcp.tool()(wrap_tool(research_deploy_record))
        record_success("remaining", "research_deploy_record")
        mcp.tool()(wrap_tool(research_deploy_status))
        record_success("remaining", "research_deploy_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip deployment: %s", e)
        record_failure("remaining", "deployment", str(e))
    try:
        from loom.tools.discord_osint import research_discord_intel
        mcp.tool()(wrap_tool(research_discord_intel))
        record_success("remaining", "research_discord_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip discord_osint: %s", e)
        record_failure("remaining", "discord_osint", str(e))
    try:
        from loom.tools.dist_tracing import research_trace_complete, research_trace_create, research_trace_query
        mcp.tool()(wrap_tool(research_trace_complete))
        record_success("remaining", "research_trace_complete")
        mcp.tool()(wrap_tool(research_trace_create))
        record_success("remaining", "research_trace_create")
        mcp.tool()(wrap_tool(research_trace_query))
        record_success("remaining", "research_trace_query")
    except (ImportError, AttributeError) as e:
        log.debug("skip dist_tracing: %s", e)
        record_failure("remaining", "dist_tracing", str(e))
    try:
        from loom.tools.do_expert import research_do_expert
        mcp.tool()(wrap_tool(research_do_expert))
        record_success("remaining", "research_do_expert")
    except (ImportError, AttributeError) as e:
        log.debug("skip do_expert: %s", e)
        record_failure("remaining", "do_expert", str(e))
    try:
        from loom.tools.docsgpt_backend import research_docs_ai
        mcp.tool()(wrap_tool(research_docs_ai))
        record_success("remaining", "research_docs_ai")
    except (ImportError, AttributeError) as e:
        log.debug("skip docsgpt_backend: %s", e)
        record_failure("remaining", "docsgpt_backend", str(e))
    try:
        from loom.tools.domain_intel import research_dns_lookup, research_nmap_scan, research_whois
        mcp.tool()(wrap_tool(research_dns_lookup))
        record_success("remaining", "research_dns_lookup")
        mcp.tool()(wrap_tool(research_nmap_scan))
        record_success("remaining", "research_nmap_scan")
        mcp.tool()(wrap_tool(research_whois))
        record_success("remaining", "research_whois")
    except (ImportError, AttributeError) as e:
        log.debug("skip domain_intel: %s", e)
        record_failure("remaining", "domain_intel", str(e))
    try:
        from loom.tools.dspy_bridge import research_dspy_configure, research_dspy_cost_report
        mcp.tool()(wrap_tool(research_dspy_configure))
        record_success("remaining", "research_dspy_configure")
        mcp.tool()(wrap_tool(research_dspy_cost_report))
        record_success("remaining", "research_dspy_cost_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip dspy_bridge: %s", e)
        record_failure("remaining", "dspy_bridge", str(e))
    try:
        from loom.tools.eagleeye_backend import research_reverse_image
        mcp.tool()(wrap_tool(research_reverse_image))
        record_success("remaining", "research_reverse_image")
    except (ImportError, AttributeError) as e:
        log.debug("skip eagleeye_backend: %s", e)
        record_failure("remaining", "eagleeye_backend", str(e))
    try:
        from loom.tools.email_report import research_email_report
        mcp.tool()(wrap_tool(research_email_report))
        record_success("remaining", "research_email_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip email_report: %s", e)
        record_failure("remaining", "email_report", str(e))
    try:
        from loom.tools.env_inspector import research_env_inspect, research_env_requirements
        mcp.tool()(wrap_tool(research_env_inspect))
        record_success("remaining", "research_env_inspect")
        mcp.tool()(wrap_tool(research_env_requirements))
        record_success("remaining", "research_env_requirements")
    except (ImportError, AttributeError) as e:
        log.debug("skip env_inspector: %s", e)
        record_failure("remaining", "env_inspector", str(e))
    try:
        from loom.tools.error_wrapper import research_error_clear, research_error_stats
        mcp.tool()(wrap_tool(research_error_clear))
        record_success("remaining", "research_error_clear")
        mcp.tool()(wrap_tool(research_error_stats))
        record_success("remaining", "research_error_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip error_wrapper: %s", e)
        record_failure("remaining", "error_wrapper", str(e))
    try:
        from loom.tools.evasion_network import research_proxy_check, research_tor_rotate
        mcp.tool()(wrap_tool(research_proxy_check))
        record_success("remaining", "research_proxy_check")
        mcp.tool()(wrap_tool(research_tor_rotate))
        record_success("remaining", "research_tor_rotate")
    except (ImportError, AttributeError) as e:
        log.debug("skip evasion_network: %s", e)
        record_failure("remaining", "evasion_network", str(e))
    try:
        from loom.tools.event_bus import research_event_emit, research_event_history, research_event_subscribe
        mcp.tool()(wrap_tool(research_event_emit))
        record_success("remaining", "research_event_emit")
        mcp.tool()(wrap_tool(research_event_history))
        record_success("remaining", "research_event_history")
        mcp.tool()(wrap_tool(research_event_subscribe))
        record_success("remaining", "research_event_subscribe")
    except (ImportError, AttributeError) as e:
        log.debug("skip event_bus: %s", e)
        record_failure("remaining", "event_bus", str(e))
    try:
        from loom.tools.evidence_fusion import research_authority_stack, research_fuse_evidence
        mcp.tool()(wrap_tool(research_authority_stack))
        record_success("remaining", "research_authority_stack")
        mcp.tool()(wrap_tool(research_fuse_evidence))
        record_success("remaining", "research_fuse_evidence")
    except (ImportError, AttributeError) as e:
        log.debug("skip evidence_fusion: %s", e)
        record_failure("remaining", "evidence_fusion", str(e))
    try:
        from loom.tools.execution_planner import research_plan_execution, research_plan_validate
        mcp.tool()(wrap_tool(research_plan_execution))
        record_success("remaining", "research_plan_execution")
        mcp.tool()(wrap_tool(research_plan_validate))
        record_success("remaining", "research_plan_validate")
    except (ImportError, AttributeError) as e:
        log.debug("skip execution_planner: %s", e)
        record_failure("remaining", "execution_planner", str(e))
    try:
        from loom.tools.expert_engine import research_expert
        mcp.tool()(wrap_tool(research_expert))
        record_success("remaining", "research_expert")
    except (ImportError, AttributeError) as e:
        log.debug("skip expert_engine: %s", e)
        record_failure("remaining", "expert_engine", str(e))
    try:
        from loom.tools.exploit_db import research_exploit_register, research_exploit_search, research_exploit_stats
        mcp.tool()(wrap_tool(research_exploit_register))
        record_success("remaining", "research_exploit_register")
        mcp.tool()(wrap_tool(research_exploit_search))
        record_success("remaining", "research_exploit_search")
        mcp.tool()(wrap_tool(research_exploit_stats))
        record_success("remaining", "research_exploit_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip exploit_db: %s", e)
        record_failure("remaining", "exploit_db", str(e))
    try:
        from loom.tools.fetch import research_fetch
        mcp.tool()(wrap_tool(research_fetch))
        record_success("remaining", "research_fetch")
    except (ImportError, AttributeError) as e:
        log.debug("skip fetch: %s", e)
        record_failure("remaining", "fetch", str(e))
    try:
        from loom.tools.fingerprint_backend import research_browser_fingerprint
        mcp.tool()(wrap_tool(research_browser_fingerprint))
        record_success("remaining", "research_browser_fingerprint")
    except (ImportError, AttributeError) as e:
        log.debug("skip fingerprint_backend: %s", e)
        record_failure("remaining", "fingerprint_backend", str(e))
    try:
        from loom.tools.forum_cortex import research_forum_cortex
        mcp.tool()(wrap_tool(research_forum_cortex))
        record_success("remaining", "research_forum_cortex")
    except (ImportError, AttributeError) as e:
        log.debug("skip forum_cortex: %s", e)
        record_failure("remaining", "forum_cortex", str(e))
    try:
        from loom.tools.full_pipeline import research_full_pipeline
        mcp.tool()(wrap_tool(research_full_pipeline))
        record_success("remaining", "research_full_pipeline")
    except (ImportError, AttributeError) as e:
        log.debug("skip full_pipeline: %s", e)
        record_failure("remaining", "full_pipeline", str(e))
    try:
        from loom.tools.functor_map import research_functor_translate
        mcp.tool()(wrap_tool(research_functor_translate))
        record_success("remaining", "research_functor_translate")
    except (ImportError, AttributeError) as e:
        log.debug("skip functor_map: %s", e)
        record_failure("remaining", "functor_map", str(e))
    try:
        from loom.tools.gcp import research_image_analyze, research_text_to_speech, research_tts_voices
        mcp.tool()(wrap_tool(research_image_analyze))
        record_success("remaining", "research_image_analyze")
        mcp.tool()(wrap_tool(research_text_to_speech))
        record_success("remaining", "research_text_to_speech")
        mcp.tool()(wrap_tool(research_tts_voices))
        record_success("remaining", "research_tts_voices")
    except (ImportError, AttributeError) as e:
        log.debug("skip gcp: %s", e)
        record_failure("remaining", "gcp", str(e))
    try:
        from loom.tools.genetic_fuzzer import research_genetic_fuzz
        mcp.tool()(wrap_tool(research_genetic_fuzz))
        record_success("remaining", "research_genetic_fuzz")
    except (ImportError, AttributeError) as e:
        log.debug("skip genetic_fuzzer: %s", e)
        record_failure("remaining", "genetic_fuzzer", str(e))
    try:
        from loom.tools.ghost_weave import research_ghost_weave
        mcp.tool()(wrap_tool(research_ghost_weave))
        record_success("remaining", "research_ghost_weave")
    except (ImportError, AttributeError) as e:
        log.debug("skip ghost_weave: %s", e)
        record_failure("remaining", "ghost_weave", str(e))
    try:
        from loom.tools.github import research_github, research_github_readme, research_github_releases
        mcp.tool()(wrap_tool(research_github))
        record_success("remaining", "research_github")
        mcp.tool()(wrap_tool(research_github_readme))
        record_success("remaining", "research_github_readme")
        mcp.tool()(wrap_tool(research_github_releases))
        record_success("remaining", "research_github_releases")
    except (ImportError, AttributeError) as e:
        log.debug("skip github: %s", e)
        record_failure("remaining", "github", str(e))
    try:
        from loom.tools.gpt_researcher_backend import research_gpt_researcher
        mcp.tool()(wrap_tool(research_gpt_researcher))
        record_success("remaining", "research_gpt_researcher")
    except (ImportError, AttributeError) as e:
        log.debug("skip gpt_researcher_backend: %s", e)
        record_failure("remaining", "gpt_researcher_backend", str(e))
    try:
        from loom.tools.h8mail_backend import research_email_breach
        mcp.tool()(wrap_tool(research_email_breach))
        record_success("remaining", "research_email_breach")
    except (ImportError, AttributeError) as e:
        log.debug("skip h8mail_backend: %s", e)
        record_failure("remaining", "h8mail_backend", str(e))
    try:
        from loom.tools.harvester_backend import research_harvest
        mcp.tool()(wrap_tool(research_harvest))
        record_success("remaining", "research_harvest")
    except (ImportError, AttributeError) as e:
        log.debug("skip harvester_backend: %s", e)
        record_failure("remaining", "harvester_backend", str(e))
    try:
        from loom.tools.help_system import research_help, research_tools_list
        mcp.tool()(wrap_tool(research_help))
        record_success("remaining", "research_help")
        mcp.tool()(wrap_tool(research_tools_list))
        record_success("remaining", "research_tools_list")
    except (ImportError, AttributeError) as e:
        log.debug("skip help_system: %s", e)
        record_failure("remaining", "help_system", str(e))
    try:
        from loom.tools.hipporag_backend import research_memory_recall, research_memory_store
        mcp.tool()(wrap_tool(research_memory_recall))
        record_success("remaining", "research_memory_recall")
        mcp.tool()(wrap_tool(research_memory_store))
        record_success("remaining", "research_memory_store")
    except (ImportError, AttributeError) as e:
        log.debug("skip hipporag_backend: %s", e)
        record_failure("remaining", "hipporag_backend", str(e))
    try:
        from loom.tools.identity_resolve import research_identity_resolve
        mcp.tool()(wrap_tool(research_identity_resolve))
        record_success("remaining", "research_identity_resolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip identity_resolve: %s", e)
        record_failure("remaining", "identity_resolve", str(e))
    try:
        from loom.tools.infra_correlator import research_infra_correlator
        mcp.tool()(wrap_tool(research_infra_correlator))
        record_success("remaining", "research_infra_correlator")
    except (ImportError, AttributeError) as e:
        log.debug("skip infra_correlator: %s", e)
        record_failure("remaining", "infra_correlator", str(e))
    try:
        from loom.tools.instructor_backend import research_structured_extract
        mcp.tool()(wrap_tool(research_structured_extract))
        record_success("remaining", "research_structured_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip instructor_backend: %s", e)
        record_failure("remaining", "instructor_backend", str(e))
    try:
        from loom.tools.intel_report import research_brief_generate, research_intel_report
        mcp.tool()(wrap_tool(research_brief_generate))
        record_success("remaining", "research_brief_generate")
        mcp.tool()(wrap_tool(research_intel_report))
        record_success("remaining", "research_intel_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip intel_report: %s", e)
        record_failure("remaining", "intel_report", str(e))
    try:
        from loom.tools.intelowl_backend import research_intelowl_analyze
        mcp.tool()(wrap_tool(research_intelowl_analyze))
        record_success("remaining", "research_intelowl_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip intelowl_backend: %s", e)
        record_failure("remaining", "intelowl_backend", str(e))
    try:
        from loom.tools.invisible_web import research_invisible_web
        mcp.tool()(wrap_tool(research_invisible_web))
        record_success("remaining", "research_invisible_web")
    except (ImportError, AttributeError) as e:
        log.debug("skip invisible_web: %s", e)
        record_failure("remaining", "invisible_web", str(e))
    try:
        from loom.tools.ip_intel import research_ip_geolocation, research_ip_reputation
        mcp.tool()(wrap_tool(research_ip_geolocation))
        record_success("remaining", "research_ip_geolocation")
        mcp.tool()(wrap_tool(research_ip_reputation))
        record_success("remaining", "research_ip_reputation")
    except (ImportError, AttributeError) as e:
        log.debug("skip ip_intel: %s", e)
        record_failure("remaining", "ip_intel", str(e))
    try:
        from loom.tools.jailbreak_evolution import research_jailbreak_evolution_adapt, research_jailbreak_evolution_get, research_jailbreak_evolution_patches, research_jailbreak_evolution_record, research_jailbreak_evolution_stats, research_jailbreak_evolution_timeline
        mcp.tool()(wrap_tool(research_jailbreak_evolution_adapt))
        record_success("remaining", "research_jailbreak_evolution_adapt")
        mcp.tool()(wrap_tool(research_jailbreak_evolution_get))
        record_success("remaining", "research_jailbreak_evolution_get")
        mcp.tool()(wrap_tool(research_jailbreak_evolution_patches))
        record_success("remaining", "research_jailbreak_evolution_patches")
        mcp.tool()(wrap_tool(research_jailbreak_evolution_record))
        record_success("remaining", "research_jailbreak_evolution_record")
        mcp.tool()(wrap_tool(research_jailbreak_evolution_stats))
        record_success("remaining", "research_jailbreak_evolution_stats")
        mcp.tool()(wrap_tool(research_jailbreak_evolution_timeline))
        record_success("remaining", "research_jailbreak_evolution_timeline")
    except (ImportError, AttributeError) as e:
        log.debug("skip jailbreak_evolution: %s", e)
        record_failure("remaining", "jailbreak_evolution", str(e))
    try:
        from loom.tools.joplin import research_list_notebooks, research_save_note
        mcp.tool()(wrap_tool(research_list_notebooks))
        record_success("remaining", "research_list_notebooks")
        mcp.tool()(wrap_tool(research_save_note))
        record_success("remaining", "research_save_note")
    except (ImportError, AttributeError) as e:
        log.debug("skip joplin: %s", e)
        record_failure("remaining", "joplin", str(e))
    try:
        from loom.tools.key_rotation import research_key_rotate, research_key_status, research_key_test
        mcp.tool()(wrap_tool(research_key_rotate))
        record_success("remaining", "research_key_rotate")
        mcp.tool()(wrap_tool(research_key_status))
        record_success("remaining", "research_key_status")
        mcp.tool()(wrap_tool(research_key_test))
        record_success("remaining", "research_key_test")
    except (ImportError, AttributeError) as e:
        log.debug("skip key_rotation: %s", e)
        record_failure("remaining", "key_rotation", str(e))
    try:
        from loom.tools.knowledge_injector import research_adapt_complexity, research_personalize_output
        mcp.tool()(wrap_tool(research_adapt_complexity))
        record_success("remaining", "research_adapt_complexity")
        mcp.tool()(wrap_tool(research_personalize_output))
        record_success("remaining", "research_personalize_output")
    except (ImportError, AttributeError) as e:
        log.debug("skip knowledge_injector: %s", e)
        record_failure("remaining", "knowledge_injector", str(e))
    try:
        from loom.tools.leak_scan import research_leak_scan
        mcp.tool()(wrap_tool(research_leak_scan))
        record_success("remaining", "research_leak_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip leak_scan: %s", e)
        record_failure("remaining", "leak_scan", str(e))
    try:
        from loom.tools.lightpanda_backend import research_lightpanda_batch, research_lightpanda_fetch
        mcp.tool()(wrap_tool(research_lightpanda_batch))
        record_success("remaining", "research_lightpanda_batch")
        mcp.tool()(wrap_tool(research_lightpanda_fetch))
        record_success("remaining", "research_lightpanda_fetch")
    except (ImportError, AttributeError) as e:
        log.debug("skip lightpanda_backend: %s", e)
        record_failure("remaining", "lightpanda_backend", str(e))
    try:
        from loom.tools.linkedin_osint import research_linkedin_intel
        mcp.tool()(wrap_tool(research_linkedin_intel))
        record_success("remaining", "research_linkedin_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip linkedin_osint: %s", e)
        record_failure("remaining", "linkedin_osint", str(e))
    try:
        from loom.tools.maigret_backend import research_maigret
        mcp.tool()(wrap_tool(research_maigret))
        record_success("remaining", "research_maigret")
    except (ImportError, AttributeError) as e:
        log.debug("skip maigret_backend: %s", e)
        record_failure("remaining", "maigret_backend", str(e))
    try:
        from loom.tools.markdown import research_markdown
        mcp.tool()(wrap_tool(research_markdown))
        record_success("remaining", "research_markdown")
    except (ImportError, AttributeError) as e:
        log.debug("skip markdown: %s", e)
        record_failure("remaining", "markdown", str(e))
    try:
        from loom.tools.masscan_backend import research_masscan
        mcp.tool()(wrap_tool(research_masscan))
        record_success("remaining", "research_masscan")
    except (ImportError, AttributeError) as e:
        log.debug("skip masscan_backend: %s", e)
        record_failure("remaining", "masscan_backend", str(e))
    try:
        from loom.tools.massdns_backend import research_massdns_resolve
        mcp.tool()(wrap_tool(research_massdns_resolve))
        record_success("remaining", "research_massdns_resolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip massdns_backend: %s", e)
        record_failure("remaining", "massdns_backend", str(e))
    try:
        from loom.tools.memetic_simulator import research_memetic_simulate
        mcp.tool()(wrap_tool(research_memetic_simulate))
        record_success("remaining", "research_memetic_simulate")
    except (ImportError, AttributeError) as e:
        log.debug("skip memetic_simulator: %s", e)
        record_failure("remaining", "memetic_simulator", str(e))
    try:
        from loom.tools.memory_mgmt import research_memory_gc, research_memory_profile, research_memory_status
        mcp.tool()(wrap_tool(research_memory_gc))
        record_success("remaining", "research_memory_gc")
        mcp.tool()(wrap_tool(research_memory_profile))
        record_success("remaining", "research_memory_profile")
        mcp.tool()(wrap_tool(research_memory_status))
        record_success("remaining", "research_memory_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip memory_mgmt: %s", e)
        record_failure("remaining", "memory_mgmt", str(e))
    try:
        from loom.tools.metrics import research_metrics
        mcp.tool()(wrap_tool(research_metrics))
        record_success("remaining", "research_metrics")
    except (ImportError, AttributeError) as e:
        log.debug("skip metrics: %s", e)
        record_failure("remaining", "metrics", str(e))
    try:
        from loom.tools.misp_backend import research_misp_lookup
        mcp.tool()(wrap_tool(research_misp_lookup))
        record_success("remaining", "research_misp_lookup")
    except (ImportError, AttributeError) as e:
        log.debug("skip misp_backend: %s", e)
        record_failure("remaining", "misp_backend", str(e))
    try:
        from loom.tools.model_compare import research_compare_responses, research_model_consensus
        mcp.tool()(wrap_tool(research_compare_responses))
        record_success("remaining", "research_compare_responses")
        mcp.tool()(wrap_tool(research_model_consensus))
        record_success("remaining", "research_model_consensus")
    except (ImportError, AttributeError) as e:
        log.debug("skip model_compare: %s", e)
        record_failure("remaining", "model_compare", str(e))
    try:
        from loom.tools.multi_search import research_multi_search
        mcp.tool()(wrap_tool(research_multi_search))
        record_success("remaining", "research_multi_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip multi_search: %s", e)
        record_failure("remaining", "multi_search", str(e))
    try:
        from loom.tools.neuromorphic import research_neuromorphic_schedule
        mcp.tool()(wrap_tool(research_neuromorphic_schedule))
        record_success("remaining", "research_neuromorphic_schedule")
    except (ImportError, AttributeError) as e:
        log.debug("skip neuromorphic: %s", e)
        record_failure("remaining", "neuromorphic", str(e))
    try:
        from loom.tools.nl_executor import research_do
        mcp.tool()(wrap_tool(research_do))
        record_success("remaining", "research_do")
    except (ImportError, AttributeError) as e:
        log.debug("skip nl_executor: %s", e)
        record_failure("remaining", "nl_executor", str(e))
    try:
        from loom.tools.observability import research_trace_end, research_trace_start, research_traces_list
        mcp.tool()(wrap_tool(research_trace_end))
        record_success("remaining", "research_trace_end")
        mcp.tool()(wrap_tool(research_trace_start))
        record_success("remaining", "research_trace_start")
        mcp.tool()(wrap_tool(research_traces_list))
        record_success("remaining", "research_traces_list")
    except (ImportError, AttributeError) as e:
        log.debug("skip observability: %s", e)
        record_failure("remaining", "observability", str(e))
    try:
        from loom.tools.onion_discover import research_onion_discover
        mcp.tool()(wrap_tool(research_onion_discover))
        record_success("remaining", "research_onion_discover")
    except (ImportError, AttributeError) as e:
        log.debug("skip onion_discover: %s", e)
        record_failure("remaining", "onion_discover", str(e))
    try:
        from loom.tools.onion_spectra import research_onion_spectra
        mcp.tool()(wrap_tool(research_onion_spectra))
        record_success("remaining", "research_onion_spectra")
    except (ImportError, AttributeError) as e:
        log.debug("skip onion_spectra: %s", e)
        record_failure("remaining", "onion_spectra", str(e))
    try:
        from loom.tools.onionscan_backend import research_onionscan
        mcp.tool()(wrap_tool(research_onionscan))
        record_success("remaining", "research_onionscan")
    except (ImportError, AttributeError) as e:
        log.debug("skip onionscan_backend: %s", e)
        record_failure("remaining", "onionscan_backend", str(e))
    try:
        from loom.tools.openapi_gen import research_openapi_schema, research_tool_search
        mcp.tool()(wrap_tool(research_openapi_schema))
        record_success("remaining", "research_openapi_schema")
        mcp.tool()(wrap_tool(research_tool_search))
        record_success("remaining", "research_tool_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip openapi_gen: %s", e)
        record_failure("remaining", "openapi_gen", str(e))
    try:
        from loom.tools.opencti_backend import research_opencti_query
        mcp.tool()(wrap_tool(research_opencti_query))
        record_success("remaining", "research_opencti_query")
    except (ImportError, AttributeError) as e:
        log.debug("skip opencti_backend: %s", e)
        record_failure("remaining", "opencti_backend", str(e))
    try:
        from loom.tools.paddleocr_backend import research_paddle_ocr
        mcp.tool()(wrap_tool(research_paddle_ocr))
        record_success("remaining", "research_paddle_ocr")
    except (ImportError, AttributeError) as e:
        log.debug("skip paddleocr_backend: %s", e)
        record_failure("remaining", "paddleocr_backend", str(e))
    try:
        from loom.tools.paradox_detector import research_detect_paradox, research_paradox_immunize
        mcp.tool()(wrap_tool(research_detect_paradox))
        record_success("remaining", "research_detect_paradox")
        mcp.tool()(wrap_tool(research_paradox_immunize))
        record_success("remaining", "research_paradox_immunize")
    except (ImportError, AttributeError) as e:
        log.debug("skip paradox_detector: %s", e)
        record_failure("remaining", "paradox_detector", str(e))
    try:
        from loom.tools.parallel_executor import research_parallel_execute, research_parallel_plan_and_execute
        mcp.tool()(wrap_tool(research_parallel_execute))
        record_success("remaining", "research_parallel_execute")
        mcp.tool()(wrap_tool(research_parallel_plan_and_execute))
        record_success("remaining", "research_parallel_plan_and_execute")
    except (ImportError, AttributeError) as e:
        log.debug("skip parallel_executor: %s", e)
        record_failure("remaining", "parallel_executor", str(e))
    try:
        from loom.tools.passive_recon import research_passive_recon
        mcp.tool()(wrap_tool(research_passive_recon))
        record_success("remaining", "research_passive_recon")
    except (ImportError, AttributeError) as e:
        log.debug("skip passive_recon: %s", e)
        record_failure("remaining", "passive_recon", str(e))
    try:
        from loom.tools.pathogen_sim import research_pathogen_evolve
        mcp.tool()(wrap_tool(research_pathogen_evolve))
        record_success("remaining", "research_pathogen_evolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip pathogen_sim: %s", e)
        record_failure("remaining", "pathogen_sim", str(e))
    try:
        from loom.tools.pentest import research_pentest_agent, research_pentest_docs, research_pentest_findings_db, research_pentest_plan, research_pentest_recommend
        mcp.tool()(wrap_tool(research_pentest_agent))
        record_success("remaining", "research_pentest_agent")
        mcp.tool()(wrap_tool(research_pentest_docs))
        record_success("remaining", "research_pentest_docs")
        mcp.tool()(wrap_tool(research_pentest_findings_db))
        record_success("remaining", "research_pentest_findings_db")
        mcp.tool()(wrap_tool(research_pentest_plan))
        record_success("remaining", "research_pentest_plan")
        mcp.tool()(wrap_tool(research_pentest_recommend))
        record_success("remaining", "research_pentest_recommend")
    except (ImportError, AttributeError) as e:
        log.debug("skip pentest: %s", e)
        record_failure("remaining", "pentest", str(e))
    try:
        from loom.tools.photon_backend import research_photon_crawl
        mcp.tool()(wrap_tool(research_photon_crawl))
        record_success("remaining", "research_photon_crawl")
    except (ImportError, AttributeError) as e:
        log.debug("skip photon_backend: %s", e)
        record_failure("remaining", "photon_backend", str(e))
    try:
        from loom.tools.polyglot_scraper import research_polyglot_search, research_subculture_intel
        mcp.tool()(wrap_tool(research_polyglot_search))
        record_success("remaining", "research_polyglot_search")
        mcp.tool()(wrap_tool(research_subculture_intel))
        record_success("remaining", "research_subculture_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip polyglot_scraper: %s", e)
        record_failure("remaining", "polyglot_scraper", str(e))
    try:
        from loom.tools.progress_tracker import research_progress_create, research_progress_dashboard, research_progress_update
        mcp.tool()(wrap_tool(research_progress_create))
        record_success("remaining", "research_progress_create")
        mcp.tool()(wrap_tool(research_progress_dashboard))
        record_success("remaining", "research_progress_dashboard")
        mcp.tool()(wrap_tool(research_progress_update))
        record_success("remaining", "research_progress_update")
    except (ImportError, AttributeError) as e:
        log.debug("skip progress_tracker: %s", e)
        record_failure("remaining", "progress_tracker", str(e))
    try:
        from loom.tools.prompt_analyzer import research_prompt_analyze
        mcp.tool()(wrap_tool(research_prompt_analyze))
        record_success("remaining", "research_prompt_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip prompt_analyzer: %s", e)
        record_failure("remaining", "prompt_analyzer", str(e))
    try:
        from loom.tools.prompt_reframe import research_adaptive_reframe, research_auto_reframe, research_crescendo_chain, research_fingerprint_model, research_format_smuggle, research_model_vulnerability_profile, research_prompt_reframe, research_refusal_detector, research_stack_reframe
        mcp.tool()(wrap_tool(research_adaptive_reframe))
        record_success("remaining", "research_adaptive_reframe")
        mcp.tool()(wrap_tool(research_auto_reframe))
        record_success("remaining", "research_auto_reframe")
        mcp.tool()(wrap_tool(research_crescendo_chain))
        record_success("remaining", "research_crescendo_chain")
        mcp.tool()(wrap_tool(research_fingerprint_model))
        record_success("remaining", "research_fingerprint_model")
        mcp.tool()(wrap_tool(research_format_smuggle))
        record_success("remaining", "research_format_smuggle")
        mcp.tool()(wrap_tool(research_model_vulnerability_profile))
        record_success("remaining", "research_model_vulnerability_profile")
        mcp.tool()(wrap_tool(research_prompt_reframe))
        record_success("remaining", "research_prompt_reframe")
        mcp.tool()(wrap_tool(research_refusal_detector))
        record_success("remaining", "research_refusal_detector")
        mcp.tool()(wrap_tool(research_stack_reframe))
        record_success("remaining", "research_stack_reframe")
    except (ImportError, AttributeError) as e:
        log.debug("skip prompt_reframe: %s", e)
        record_failure("remaining", "prompt_reframe", str(e))
    try:
        from loom.tools.prompt_templates import research_template_list, research_template_render, research_template_suggest
        mcp.tool()(wrap_tool(research_template_list))
        record_success("remaining", "research_template_list")
        mcp.tool()(wrap_tool(research_template_render))
        record_success("remaining", "research_template_render")
        mcp.tool()(wrap_tool(research_template_suggest))
        record_success("remaining", "research_template_suggest")
    except (ImportError, AttributeError) as e:
        log.debug("skip prompt_templates: %s", e)
        record_failure("remaining", "prompt_templates", str(e))
    try:
        from loom.tools.psycholinguistic import research_psycholinguistic
        mcp.tool()(wrap_tool(research_psycholinguistic))
        record_success("remaining", "research_psycholinguistic")
    except (ImportError, AttributeError) as e:
        log.debug("skip psycholinguistic: %s", e)
        record_failure("remaining", "psycholinguistic", str(e))
    try:
        from loom.tools.pydantic_ai_backend import research_pydantic_agent, research_structured_llm
        mcp.tool()(wrap_tool(research_pydantic_agent))
        record_success("remaining", "research_pydantic_agent")
        mcp.tool()(wrap_tool(research_structured_llm))
        record_success("remaining", "research_structured_llm")
    except (ImportError, AttributeError) as e:
        log.debug("skip pydantic_ai_backend: %s", e)
        record_failure("remaining", "pydantic_ai_backend", str(e))
    try:
        from loom.tools.quality_escalation import research_quality_escalate
        mcp.tool()(wrap_tool(research_quality_escalate))
        record_success("remaining", "research_quality_escalate")
    except (ImportError, AttributeError) as e:
        log.debug("skip quality_escalation: %s", e)
        record_failure("remaining", "quality_escalation", str(e))
    try:
        from loom.tools.query_builder import research_build_query
        mcp.tool()(wrap_tool(research_build_query))
        record_success("remaining", "research_build_query")
    except (ImportError, AttributeError) as e:
        log.debug("skip query_builder: %s", e)
        record_failure("remaining", "query_builder", str(e))
    try:
        from loom.tools.realtime_monitor import research_realtime_monitor
        mcp.tool()(wrap_tool(research_realtime_monitor))
        record_success("remaining", "research_realtime_monitor")
    except (ImportError, AttributeError) as e:
        log.debug("skip realtime_monitor: %s", e)
        record_failure("remaining", "realtime_monitor", str(e))
    try:
        from loom.tools.reconng_backend import research_reconng_scan
        mcp.tool()(wrap_tool(research_reconng_scan))
        record_success("remaining", "research_reconng_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip reconng_backend: %s", e)
        record_failure("remaining", "reconng_backend", str(e))
    try:
        from loom.tools.report_generator import research_generate_executive_report, research_generate_report
        mcp.tool()(wrap_tool(research_generate_executive_report))
        record_success("remaining", "research_generate_executive_report")
        mcp.tool()(wrap_tool(research_generate_report))
        record_success("remaining", "research_generate_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip report_generator: %s", e)
        record_failure("remaining", "report_generator", str(e))
    try:
        from loom.tools.report_templates import research_report_custom, research_report_template
        mcp.tool()(wrap_tool(research_report_custom))
        record_success("remaining", "research_report_custom")
        mcp.tool()(wrap_tool(research_report_template))
        record_success("remaining", "research_report_template")
    except (ImportError, AttributeError) as e:
        log.debug("skip report_templates: %s", e)
        record_failure("remaining", "report_templates", str(e))
    try:
        from loom.tools.resilience_predictor import research_predict_resilience
        mcp.tool()(wrap_tool(research_predict_resilience))
        record_success("remaining", "research_predict_resilience")
    except (ImportError, AttributeError) as e:
        log.debug("skip resilience_predictor: %s", e)
        record_failure("remaining", "resilience_predictor", str(e))
    try:
        from loom.tools.response_cache import research_response_cache_stats
        mcp.tool()(wrap_tool(research_response_cache_stats))
        record_success("remaining", "research_response_cache_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip response_cache: %s", e)
        record_failure("remaining", "response_cache", str(e))
    try:
        from loom.tools.result_aggregator import research_aggregate_results, research_aggregate_texts
        mcp.tool()(wrap_tool(research_aggregate_results))
        record_success("remaining", "research_aggregate_results")
        mcp.tool()(wrap_tool(research_aggregate_texts))
        record_success("remaining", "research_aggregate_texts")
    except (ImportError, AttributeError) as e:
        log.debug("skip result_aggregator: %s", e)
        record_failure("remaining", "result_aggregator", str(e))
    try:
        from loom.tools.retry_middleware import research_retry_execute, research_retry_middleware_stats
        mcp.tool()(wrap_tool(research_retry_execute))
        record_success("remaining", "research_retry_execute")
        mcp.tool()(wrap_tool(research_retry_middleware_stats))
        record_success("remaining", "research_retry_middleware_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip retry_middleware: %s", e)
        record_failure("remaining", "retry_middleware", str(e))
    try:
        from loom.tools.robin_backend import research_robin_scan
        mcp.tool()(wrap_tool(research_robin_scan))
        record_success("remaining", "research_robin_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip robin_backend: %s", e)
        record_failure("remaining", "robin_backend", str(e))
    try:
        from loom.tools.rss_monitor import research_rss_fetch, research_rss_search
        mcp.tool()(wrap_tool(research_rss_fetch))
        record_success("remaining", "research_rss_fetch")
        mcp.tool()(wrap_tool(research_rss_search))
        record_success("remaining", "research_rss_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip rss_monitor: %s", e)
        record_failure("remaining", "rss_monitor", str(e))
    try:
        from loom.tools.safety_predictor import research_predict_safety_update
        mcp.tool()(wrap_tool(research_predict_safety_update))
        record_success("remaining", "research_predict_safety_update")
    except (ImportError, AttributeError) as e:
        log.debug("skip safety_predictor: %s", e)
        record_failure("remaining", "safety_predictor", str(e))
    try:
        from loom.tools.sandbox import research_sandbox_analyze, research_sandbox_report
        mcp.tool()(wrap_tool(research_sandbox_analyze))
        record_success("remaining", "research_sandbox_analyze")
        mcp.tool()(wrap_tool(research_sandbox_report))
        record_success("remaining", "research_sandbox_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip sandbox: %s", e)
        record_failure("remaining", "sandbox", str(e))
    try:
        from loom.tools.scapy_backend import research_packet_craft
        mcp.tool()(wrap_tool(research_packet_craft))
        record_success("remaining", "research_packet_craft")
    except (ImportError, AttributeError) as e:
        log.debug("skip scapy_backend: %s", e)
        record_failure("remaining", "scapy_backend", str(e))
    try:
        from loom.tools.search import research_search
        mcp.tool()(wrap_tool(research_search))
        record_success("remaining", "research_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip search: %s", e)
        record_failure("remaining", "search", str(e))
    try:
        from loom.tools.security_headers import research_security_headers
        mcp.tool()(wrap_tool(research_security_headers))
        record_success("remaining", "research_security_headers")
    except (ImportError, AttributeError) as e:
        log.debug("skip security_headers: %s", e)
        record_failure("remaining", "security_headers", str(e))
    try:
        from loom.tools.semantic_index import research_semantic_rebuild, research_semantic_search
        mcp.tool()(wrap_tool(research_semantic_rebuild))
        record_success("remaining", "research_semantic_rebuild")
        mcp.tool()(wrap_tool(research_semantic_search))
        record_success("remaining", "research_semantic_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip semantic_index: %s", e)
        record_failure("remaining", "semantic_index", str(e))
    try:
        from loom.tools.session_replay import research_session_list, research_session_record, research_session_replay
        mcp.tool()(wrap_tool(research_session_list))
        record_success("remaining", "research_session_list")
        mcp.tool()(wrap_tool(research_session_record))
        record_success("remaining", "research_session_record")
        mcp.tool()(wrap_tool(research_session_replay))
        record_success("remaining", "research_session_replay")
    except (ImportError, AttributeError) as e:
        log.debug("skip session_replay: %s", e)
        record_failure("remaining", "session_replay", str(e))
    try:
        from loom.tools.shodan_backend import research_shodan_host, research_shodan_search
        mcp.tool()(wrap_tool(research_shodan_host))
        record_success("remaining", "research_shodan_host")
        mcp.tool()(wrap_tool(research_shodan_search))
        record_success("remaining", "research_shodan_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip shodan_backend: %s", e)
        record_failure("remaining", "shodan_backend", str(e))
    try:
        from loom.tools.signal_detection import research_ghost_protocol, research_sec_tracker, research_temporal_anomaly
        mcp.tool()(wrap_tool(research_ghost_protocol))
        record_success("remaining", "research_ghost_protocol")
        mcp.tool()(wrap_tool(research_sec_tracker))
        record_success("remaining", "research_sec_tracker")
        mcp.tool()(wrap_tool(research_temporal_anomaly))
        record_success("remaining", "research_temporal_anomaly")
    except (ImportError, AttributeError) as e:
        log.debug("skip signal_detection: %s", e)
        record_failure("remaining", "signal_detection", str(e))
    try:
        from loom.tools.simplifier import research_simplify
        mcp.tool()(wrap_tool(research_simplify))
        record_success("remaining", "research_simplify")
    except (ImportError, AttributeError) as e:
        log.debug("skip simplifier: %s", e)
        record_failure("remaining", "simplifier", str(e))
    try:
        from loom.tools.singlefile_backend import research_archive_page
        mcp.tool()(wrap_tool(research_archive_page))
        record_success("remaining", "research_archive_page")
    except (ImportError, AttributeError) as e:
        log.debug("skip singlefile_backend: %s", e)
        record_failure("remaining", "singlefile_backend", str(e))
    try:
        from loom.tools.slack import research_slack_notify
        mcp.tool()(wrap_tool(research_slack_notify))
        record_success("remaining", "research_slack_notify")
    except (ImportError, AttributeError) as e:
        log.debug("skip slack: %s", e)
        record_failure("remaining", "slack", str(e))
    try:
        from loom.tools.smart_router import research_route_batch, research_route_query, research_router_rebuild
        mcp.tool()(wrap_tool(research_route_batch))
        record_success("remaining", "research_route_batch")
        mcp.tool()(wrap_tool(research_route_query))
        record_success("remaining", "research_route_query")
        mcp.tool()(wrap_tool(research_router_rebuild))
        record_success("remaining", "research_router_rebuild")
    except (ImportError, AttributeError) as e:
        log.debug("skip smart_router: %s", e)
        record_failure("remaining", "smart_router", str(e))
    try:
        from loom.tools.social_analyzer_backend import research_social_analyze
        mcp.tool()(wrap_tool(research_social_analyze))
        record_success("remaining", "research_social_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip social_analyzer_backend: %s", e)
        record_failure("remaining", "social_analyzer_backend", str(e))
    try:
        from loom.tools.social_graph import research_social_graph
        mcp.tool()(wrap_tool(research_social_graph))
        record_success("remaining", "research_social_graph")
    except (ImportError, AttributeError) as e:
        log.debug("skip social_graph: %s", e)
        record_failure("remaining", "social_graph", str(e))
    try:
        from loom.tools.spider import research_spider
        mcp.tool()(wrap_tool(research_spider))
        record_success("remaining", "research_spider")
    except (ImportError, AttributeError) as e:
        log.debug("skip spider: %s", e)
        record_failure("remaining", "spider", str(e))
    try:
        from loom.tools.spiderfoot_backend import research_spiderfoot_scan
        mcp.tool()(wrap_tool(research_spiderfoot_scan))
        record_success("remaining", "research_spiderfoot_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip spiderfoot_backend: %s", e)
        record_failure("remaining", "spiderfoot_backend", str(e))
    try:
        from loom.tools.startup_validator import research_health_deep, research_validate_startup
        mcp.tool()(wrap_tool(research_health_deep))
        record_success("remaining", "research_health_deep")
        mcp.tool()(wrap_tool(research_validate_startup))
        record_success("remaining", "research_validate_startup")
    except (ImportError, AttributeError) as e:
        log.debug("skip startup_validator: %s", e)
        record_failure("remaining", "startup_validator", str(e))
    try:
        from loom.tools.stealth import research_botasaurus, research_camoufox
        mcp.tool()(wrap_tool(research_botasaurus))
        record_success("remaining", "research_botasaurus")
        mcp.tool()(wrap_tool(research_camoufox))
        record_success("remaining", "research_camoufox")
    except (ImportError, AttributeError) as e:
        log.debug("skip stealth: %s", e)
        record_failure("remaining", "stealth", str(e))
    try:
        from loom.tools.strange_attractors import research_attractor_trap
        mcp.tool()(wrap_tool(research_attractor_trap))
        record_success("remaining", "research_attractor_trap")
    except (ImportError, AttributeError) as e:
        log.debug("skip strange_attractors: %s", e)
        record_failure("remaining", "strange_attractors", str(e))
    try:
        from loom.tools.supercookie_backend import research_supercookie_check
        mcp.tool()(wrap_tool(research_supercookie_check))
        record_success("remaining", "research_supercookie_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip supercookie_backend: %s", e)
        record_failure("remaining", "supercookie_backend", str(e))
    try:
        from loom.tools.supply_chain import research_model_integrity, research_package_audit
        mcp.tool()(wrap_tool(research_model_integrity))
        record_success("remaining", "research_model_integrity")
        mcp.tool()(wrap_tool(research_package_audit))
        record_success("remaining", "research_package_audit")
    except (ImportError, AttributeError) as e:
        log.debug("skip supply_chain: %s", e)
        record_failure("remaining", "supply_chain", str(e))
    try:
        from loom.tools.supply_chain_intel import research_dependency_audit, research_patent_landscape, research_supply_chain_risk
        mcp.tool()(wrap_tool(research_dependency_audit))
        record_success("remaining", "research_dependency_audit")
        mcp.tool()(wrap_tool(research_patent_landscape))
        record_success("remaining", "research_patent_landscape")
        mcp.tool()(wrap_tool(research_supply_chain_risk))
        record_success("remaining", "research_supply_chain_risk")
    except (ImportError, AttributeError) as e:
        log.debug("skip supply_chain_intel: %s", e)
        record_failure("remaining", "supply_chain_intel", str(e))
    try:
        from loom.tools.swarm_attack import research_swarm_attack
        mcp.tool()(wrap_tool(research_swarm_attack))
        record_success("remaining", "research_swarm_attack")
    except (ImportError, AttributeError) as e:
        log.debug("skip swarm_attack: %s", e)
        record_failure("remaining", "swarm_attack", str(e))
    try:
        from loom.tools.talent_tracker import research_talent_flow, research_track_researcher
        mcp.tool()(wrap_tool(research_talent_flow))
        record_success("remaining", "research_talent_flow")
        mcp.tool()(wrap_tool(research_track_researcher))
        record_success("remaining", "research_track_researcher")
    except (ImportError, AttributeError) as e:
        log.debug("skip talent_tracker: %s", e)
        record_failure("remaining", "talent_tracker", str(e))
    try:
        from loom.tools.telegram_osint import research_telegram_intel
        mcp.tool()(wrap_tool(research_telegram_intel))
        record_success("remaining", "research_telegram_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip telegram_osint: %s", e)
        record_failure("remaining", "telegram_osint", str(e))
    try:
        from loom.tools.telemetry import research_telemetry_record, research_telemetry_reset, research_telemetry_stats
        mcp.tool()(wrap_tool(research_telemetry_record))
        record_success("remaining", "research_telemetry_record")
        mcp.tool()(wrap_tool(research_telemetry_reset))
        record_success("remaining", "research_telemetry_reset")
        mcp.tool()(wrap_tool(research_telemetry_stats))
        record_success("remaining", "research_telemetry_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip telemetry: %s", e)
        record_failure("remaining", "telemetry", str(e))
    try:
        from loom.tools.testssl_backend import research_testssl
        mcp.tool()(wrap_tool(research_testssl))
        record_success("remaining", "research_testssl")
    except (ImportError, AttributeError) as e:
        log.debug("skip testssl_backend: %s", e)
        record_failure("remaining", "testssl_backend", str(e))
    try:
        from loom.tools.thinking_injection import research_reasoning_exploit, research_thinking_inject
        mcp.tool()(wrap_tool(research_reasoning_exploit))
        record_success("remaining", "research_reasoning_exploit")
        mcp.tool()(wrap_tool(research_thinking_inject))
        record_success("remaining", "research_thinking_inject")
    except (ImportError, AttributeError) as e:
        log.debug("skip thinking_injection: %s", e)
        record_failure("remaining", "thinking_injection", str(e))
    try:
        from loom.tools.threat_intel import research_botnet_tracker, research_dark_market_monitor, research_domain_reputation, research_ioc_enrich, research_malware_intel, research_phishing_mapper, research_ransomware_tracker
        mcp.tool()(wrap_tool(research_botnet_tracker))
        record_success("remaining", "research_botnet_tracker")
        mcp.tool()(wrap_tool(research_dark_market_monitor))
        record_success("remaining", "research_dark_market_monitor")
        mcp.tool()(wrap_tool(research_domain_reputation))
        record_success("remaining", "research_domain_reputation")
        mcp.tool()(wrap_tool(research_ioc_enrich))
        record_success("remaining", "research_ioc_enrich")
        mcp.tool()(wrap_tool(research_malware_intel))
        record_success("remaining", "research_malware_intel")
        mcp.tool()(wrap_tool(research_phishing_mapper))
        record_success("remaining", "research_phishing_mapper")
        mcp.tool()(wrap_tool(research_ransomware_tracker))
        record_success("remaining", "research_ransomware_tracker")
    except (ImportError, AttributeError) as e:
        log.debug("skip threat_intel: %s", e)
        record_failure("remaining", "threat_intel", str(e))
    try:
        from loom.tools.threat_profile import research_threat_profile
        mcp.tool()(wrap_tool(research_threat_profile))
        record_success("remaining", "research_threat_profile")
    except (ImportError, AttributeError) as e:
        log.debug("skip threat_profile: %s", e)
        record_failure("remaining", "threat_profile", str(e))
    try:
        from loom.tools.tool_discovery import research_discover
        mcp.tool()(wrap_tool(research_discover))
        record_success("remaining", "research_discover")
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_discovery: %s", e)
        record_failure("remaining", "tool_discovery", str(e))
    try:
        from loom.tools.tool_health import research_health_alert, research_health_check_all, research_health_history
        mcp.tool()(wrap_tool(research_health_alert))
        record_success("remaining", "research_health_alert")
        mcp.tool()(wrap_tool(research_health_check_all))
        record_success("remaining", "research_health_check_all")
        mcp.tool()(wrap_tool(research_health_history))
        record_success("remaining", "research_health_history")
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_health: %s", e)
        record_failure("remaining", "tool_health", str(e))
    try:
        from loom.tools.tool_recommender_v2 import research_recommend_next, research_suggest_workflow
        mcp.tool()(wrap_tool(research_recommend_next))
        record_success("remaining", "research_recommend_next")
        mcp.tool()(wrap_tool(research_suggest_workflow))
        record_success("remaining", "research_suggest_workflow")
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_recommender_v2: %s", e)
        record_failure("remaining", "tool_recommender_v2", str(e))
    try:
        from loom.tools.topology_manifold import research_topology_discover
        mcp.tool()(wrap_tool(research_topology_discover))
        record_success("remaining", "research_topology_discover")
    except (ImportError, AttributeError) as e:
        log.debug("skip topology_manifold: %s", e)
        record_failure("remaining", "topology_manifold", str(e))
    try:
        from loom.tools.tor import research_tor_new_identity, research_tor_status
        mcp.tool()(wrap_tool(research_tor_new_identity))
        record_success("remaining", "research_tor_new_identity")
        mcp.tool()(wrap_tool(research_tor_status))
        record_success("remaining", "research_tor_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip tor: %s", e)
        record_failure("remaining", "tor", str(e))
    try:
        from loom.tools.transferability import research_transfer_test
        mcp.tool()(wrap_tool(research_transfer_test))
        record_success("remaining", "research_transfer_test")
    except (ImportError, AttributeError) as e:
        log.debug("skip transferability: %s", e)
        record_failure("remaining", "transferability", str(e))
    try:
        from loom.tools.trend_predictor import research_trend_predict
        mcp.tool()(wrap_tool(research_trend_predict))
        record_success("remaining", "research_trend_predict")
    except (ImportError, AttributeError) as e:
        log.debug("skip trend_predictor: %s", e)
        record_failure("remaining", "trend_predictor", str(e))
    try:
        from loom.tools.uncertainty_harvest import research_active_select, research_uncertainty_estimate
        mcp.tool()(wrap_tool(research_active_select))
        record_success("remaining", "research_active_select")
        mcp.tool()(wrap_tool(research_uncertainty_estimate))
        record_success("remaining", "research_uncertainty_estimate")
    except (ImportError, AttributeError) as e:
        log.debug("skip uncertainty_harvest: %s", e)
        record_failure("remaining", "uncertainty_harvest", str(e))
    try:
        from loom.tools.universal_orchestrator import research_orchestrate_smart
        mcp.tool()(wrap_tool(research_orchestrate_smart))
        record_success("remaining", "research_orchestrate_smart")
    except (ImportError, AttributeError) as e:
        log.debug("skip universal_orchestrator: %s", e)
        record_failure("remaining", "universal_orchestrator", str(e))
    try:
        from loom.tools.unstructured_backend import research_document_extract
        mcp.tool()(wrap_tool(research_document_extract))
        record_success("remaining", "research_document_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip unstructured_backend: %s", e)
        record_failure("remaining", "unstructured_backend", str(e))
    try:
        from loom.tools.urlhaus_lookup import research_urlhaus_check, research_urlhaus_search
        mcp.tool()(wrap_tool(research_urlhaus_check))
        record_success("remaining", "research_urlhaus_check")
        mcp.tool()(wrap_tool(research_urlhaus_search))
        record_success("remaining", "research_urlhaus_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip urlhaus_lookup: %s", e)
        record_failure("remaining", "urlhaus_lookup", str(e))
    try:
        from loom.tools.vastai import research_vastai_search, research_vastai_status
        mcp.tool()(wrap_tool(research_vastai_search))
        record_success("remaining", "research_vastai_search")
        mcp.tool()(wrap_tool(research_vastai_status))
        record_success("remaining", "research_vastai_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip vastai: %s", e)
        record_failure("remaining", "vastai", str(e))
    try:
        from loom.tools.vercel import research_vercel_status
        mcp.tool()(wrap_tool(research_vercel_status))
        record_success("remaining", "research_vercel_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip vercel: %s", e)
        record_failure("remaining", "vercel", str(e))
    try:
        from loom.tools.vuln_intel import research_vuln_intel
        mcp.tool()(wrap_tool(research_vuln_intel))
        record_success("remaining", "research_vuln_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip vuln_intel: %s", e)
        record_failure("remaining", "vuln_intel", str(e))
    try:
        from loom.tools.webcheck_backend import research_web_check
        mcp.tool()(wrap_tool(research_web_check))
        record_success("remaining", "research_web_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip webcheck_backend: %s", e)
        record_failure("remaining", "webcheck_backend", str(e))
    try:
        from loom.tools.workflow_engine import research_workflow_create, research_workflow_run, research_workflow_status
        mcp.tool()(wrap_tool(research_workflow_create))
        record_success("remaining", "research_workflow_create")
        mcp.tool()(wrap_tool(research_workflow_run))
        record_success("remaining", "research_workflow_run")
        mcp.tool()(wrap_tool(research_workflow_status))
        record_success("remaining", "research_workflow_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip workflow_engine: %s", e)
        record_failure("remaining", "workflow_engine", str(e))
    try:
        from loom.tools.workflow_expander import research_workflow_coverage, research_workflow_generate
        mcp.tool()(wrap_tool(research_workflow_coverage))
        record_success("remaining", "research_workflow_coverage")
        mcp.tool()(wrap_tool(research_workflow_generate))
        record_success("remaining", "research_workflow_generate")
    except (ImportError, AttributeError) as e:
        log.debug("skip workflow_expander: %s", e)
        record_failure("remaining", "workflow_expander", str(e))
    try:
        from loom.tools.workflow_templates import research_workflow_get, research_workflow_list
        mcp.tool()(wrap_tool(research_workflow_get))
        record_success("remaining", "research_workflow_get")
        mcp.tool()(wrap_tool(research_workflow_list))
        record_success("remaining", "research_workflow_list")
    except (ImportError, AttributeError) as e:
        log.debug("skip workflow_templates: %s", e)
        record_failure("remaining", "workflow_templates", str(e))
    try:
        from loom.tools.yara_backend import research_yara_scan
        mcp.tool()(wrap_tool(research_yara_scan))
        record_success("remaining", "research_yara_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip yara_backend: %s", e)
        record_failure("remaining", "yara_backend", str(e))
    log.info("registered remaining tools count=315")