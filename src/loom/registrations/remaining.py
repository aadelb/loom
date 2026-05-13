"""Registration module for remaining research tools (extras)."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.remaining")


def register_remaining_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 150 remaining research tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.infrastructure.api_fuzzer import research_fuzz_api, research_fuzz_report
        mcp.tool()(wrap_tool(research_fuzz_api))
        record_success("remaining", "research_fuzz_api")
        mcp.tool()(wrap_tool(research_fuzz_report))
        record_success("remaining", "research_fuzz_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip api_fuzzer: %s", e)
        record_failure("remaining", "api_fuzzer", str(e))
    try:
        from loom.tools.adversarial.attack_economy import research_economy_balance, research_economy_leaderboard, research_economy_submit
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
        from loom.tools.research.benchmark_datasets import research_load_benchmark, research_run_benchmark
        mcp.tool()(wrap_tool(research_load_benchmark))
        record_success("remaining", "research_load_benchmark")
        mcp.tool()(wrap_tool(research_run_benchmark))
        record_success("remaining", "research_run_benchmark")
    except (ImportError, AttributeError) as e:
        log.debug("skip benchmark_datasets: %s", e)
        record_failure("remaining", "benchmark_datasets", str(e))
    try:
        from loom.tools.core.cache_analytics import research_cache_analyze, research_cache_optimize
        mcp.tool()(wrap_tool(research_cache_analyze))
        record_success("remaining", "research_cache_analyze")
        mcp.tool()(wrap_tool(research_cache_optimize))
        record_success("remaining", "research_cache_optimize")
    except (ImportError, AttributeError) as e:
        log.debug("skip cache_analytics: %s", e)
        record_failure("remaining", "cache_analytics", str(e))
    try:
        from loom.tools.backends.camelot_backend import research_table_extract
        mcp.tool()(wrap_tool(research_table_extract))
        record_success("remaining", "research_table_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip camelot_backend: %s", e)
        record_failure("remaining", "camelot_backend", str(e))
    try:
        from loom.tools.backends.censys_backend import research_censys_host, research_censys_search
        mcp.tool()(wrap_tool(research_censys_host))
        record_success("remaining", "research_censys_host")
        mcp.tool()(wrap_tool(research_censys_search))
        record_success("remaining", "research_censys_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip censys_backend: %s", e)
        record_failure("remaining", "censys_backend", str(e))
    try:
        from loom.tools.core.cli_autocomplete import research_generate_completions, research_tool_help
        mcp.tool()(wrap_tool(research_generate_completions))
        record_success("remaining", "research_generate_completions")
        mcp.tool()(wrap_tool(research_tool_help))
        record_success("remaining", "research_tool_help")
    except (ImportError, AttributeError) as e:
        log.debug("skip cli_autocomplete: %s", e)
        record_failure("remaining", "cli_autocomplete", str(e))
    try:
        from loom.tools.intelligence.competitive_monitor import research_competitive_advantage, research_monitor_competitors
        mcp.tool()(wrap_tool(research_competitive_advantage))
        record_success("remaining", "research_competitive_advantage")
        mcp.tool()(wrap_tool(research_monitor_competitors))
        record_success("remaining", "research_monitor_competitors")
    except (ImportError, AttributeError) as e:
        log.debug("skip competitive_monitor: %s", e)
        record_failure("remaining", "competitive_monitor", str(e))
    try:
        from loom.tools.security.compliance_report import research_audit_trail, research_compliance_report
        mcp.tool()(wrap_tool(research_audit_trail))
        record_success("remaining", "research_audit_trail")
        mcp.tool()(wrap_tool(research_compliance_report))
        record_success("remaining", "research_compliance_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip compliance_report: %s", e)
        record_failure("remaining", "compliance_report", str(e))
    try:
        from loom.tools.infrastructure.cost_estimator import research_cost_summary, research_estimate_cost
        mcp.tool()(wrap_tool(research_cost_summary))
        record_success("remaining", "research_cost_summary")
        mcp.tool()(wrap_tool(research_estimate_cost))
        record_success("remaining", "research_estimate_cost")
    except (ImportError, AttributeError) as e:
        log.debug("skip cost_estimator: %s", e)
        record_failure("remaining", "cost_estimator", str(e))
    try:
        from loom.tools.llm.creative import research_consensus
        mcp.tool()(wrap_tool(research_consensus))
        record_success("remaining", "research_consensus")
    except (ImportError, AttributeError) as e:
        log.debug("skip creative: %s", e)
        record_failure("remaining", "creative", str(e))
    try:
        from loom.tools.backends.creepjs_backend import research_creepjs_audit
        mcp.tool()(wrap_tool(research_creepjs_audit))
        record_success("remaining", "research_creepjs_audit")
    except (ImportError, AttributeError) as e:
        log.debug("skip creepjs_backend: %s", e)
        record_failure("remaining", "creepjs_backend", str(e))
    try:
        from loom.tools.adversarial.cross_domain import research_cross_domain
        mcp.tool()(wrap_tool(research_cross_domain))
        record_success("remaining", "research_cross_domain")
    except (ImportError, AttributeError) as e:
        log.debug("skip cross_domain: %s", e)
        record_failure("remaining", "cross_domain", str(e))
    try:
        from loom.tools.core.dead_content import research_dead_content
        mcp.tool()(wrap_tool(research_dead_content))
        record_success("remaining", "research_dead_content")
    except (ImportError, AttributeError) as e:
        log.debug("skip dead_content: %s", e)
        record_failure("remaining", "dead_content", str(e))
    try:
        from loom.tools.backends.deepdarkcti_backend import research_dark_cti
        mcp.tool()(wrap_tool(research_dark_cti))
        record_success("remaining", "research_dark_cti")
    except (ImportError, AttributeError) as e:
        log.debug("skip deepdarkcti_backend: %s", e)
        record_failure("remaining", "deepdarkcti_backend", str(e))
    try:
        from loom.tools.backends.deerflow_backend import research_deer_flow
        mcp.tool()(wrap_tool(research_deer_flow))
        record_success("remaining", "research_deer_flow")
    except (ImportError, AttributeError) as e:
        log.debug("skip deerflow_backend: %s", e)
        record_failure("remaining", "deerflow_backend", str(e))
    try:
        from loom.tools.intelligence.discord_osint import research_discord_intel
        mcp.tool()(wrap_tool(research_discord_intel))
        record_success("remaining", "research_discord_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip discord_osint: %s", e)
        record_failure("remaining", "discord_osint", str(e))
    try:
        from loom.tools.monitoring.dist_tracing import research_trace_complete, research_trace_create, research_trace_query
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
        from loom.tools.backends.docsgpt_backend import research_docs_ai
        mcp.tool()(wrap_tool(research_docs_ai))
        record_success("remaining", "research_docs_ai")
    except (ImportError, AttributeError) as e:
        log.debug("skip docsgpt_backend: %s", e)
        record_failure("remaining", "docsgpt_backend", str(e))
    try:
        from loom.tools.llm.dspy_bridge import research_dspy_configure, research_dspy_cost_report
        mcp.tool()(wrap_tool(research_dspy_configure))
        record_success("remaining", "research_dspy_configure")
        mcp.tool()(wrap_tool(research_dspy_cost_report))
        record_success("remaining", "research_dspy_cost_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip dspy_bridge: %s", e)
        record_failure("remaining", "dspy_bridge", str(e))
    try:
        from loom.tools.backends.eagleeye_backend import research_reverse_image
        mcp.tool()(wrap_tool(research_reverse_image))
        record_success("remaining", "research_reverse_image")
    except (ImportError, AttributeError) as e:
        log.debug("skip eagleeye_backend: %s", e)
        record_failure("remaining", "eagleeye_backend", str(e))
    try:
        from loom.tools.infrastructure.env_inspector import research_env_inspect, research_env_requirements
        mcp.tool()(wrap_tool(research_env_inspect))
        record_success("remaining", "research_env_inspect")
        mcp.tool()(wrap_tool(research_env_requirements))
        record_success("remaining", "research_env_requirements")
    except (ImportError, AttributeError) as e:
        log.debug("skip env_inspector: %s", e)
        record_failure("remaining", "env_inspector", str(e))
    try:
        from loom.tools.adversarial.evasion_network import research_proxy_check, research_tor_rotate
        mcp.tool()(wrap_tool(research_proxy_check))
        record_success("remaining", "research_proxy_check")
        mcp.tool()(wrap_tool(research_tor_rotate))
        record_success("remaining", "research_tor_rotate")
    except (ImportError, AttributeError) as e:
        log.debug("skip evasion_network: %s", e)
        record_failure("remaining", "evasion_network", str(e))
    try:
        from loom.tools.infrastructure.event_bus import research_event_emit, research_event_history, research_event_subscribe
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
        from loom.tools.backends.fingerprint_backend import research_browser_fingerprint
        mcp.tool()(wrap_tool(research_browser_fingerprint))
        record_success("remaining", "research_browser_fingerprint")
    except (ImportError, AttributeError) as e:
        log.debug("skip fingerprint_backend: %s", e)
        record_failure("remaining", "fingerprint_backend", str(e))
    try:
        from loom.tools.intelligence.forum_cortex import research_forum_cortex
        mcp.tool()(wrap_tool(research_forum_cortex))
        record_success("remaining", "research_forum_cortex")
    except (ImportError, AttributeError) as e:
        log.debug("skip forum_cortex: %s", e)
        record_failure("remaining", "forum_cortex", str(e))
    try:
        from loom.tools.infrastructure.functor_map import research_functor_translate
        mcp.tool()(wrap_tool(research_functor_translate))
        record_success("remaining", "research_functor_translate")
    except (ImportError, AttributeError) as e:
        log.debug("skip functor_map: %s", e)
        record_failure("remaining", "functor_map", str(e))
    try:
        from loom.tools.adversarial.genetic_fuzzer import research_genetic_fuzz
        mcp.tool()(wrap_tool(research_genetic_fuzz))
        record_success("remaining", "research_genetic_fuzz")
    except (ImportError, AttributeError) as e:
        log.debug("skip genetic_fuzzer: %s", e)
        record_failure("remaining", "genetic_fuzzer", str(e))
    try:
        from loom.tools.adversarial.ghost_weave import research_ghost_weave
        mcp.tool()(wrap_tool(research_ghost_weave))
        record_success("remaining", "research_ghost_weave")
    except (ImportError, AttributeError) as e:
        log.debug("skip ghost_weave: %s", e)
        record_failure("remaining", "ghost_weave", str(e))
    try:
        from loom.tools.backends.gpt_researcher_backend import research_gpt_researcher
        mcp.tool()(wrap_tool(research_gpt_researcher))
        record_success("remaining", "research_gpt_researcher")
    except (ImportError, AttributeError) as e:
        log.debug("skip gpt_researcher_backend: %s", e)
        record_failure("remaining", "gpt_researcher_backend", str(e))
    try:
        from loom.tools.backends.h8mail_backend import research_email_breach
        mcp.tool()(wrap_tool(research_email_breach))
        record_success("remaining", "research_email_breach")
    except (ImportError, AttributeError) as e:
        log.debug("skip h8mail_backend: %s", e)
        record_failure("remaining", "h8mail_backend", str(e))
    try:
        from loom.tools.backends.harvester_backend import research_harvest
        mcp.tool()(wrap_tool(research_harvest))
        record_success("remaining", "research_harvest")
    except (ImportError, AttributeError) as e:
        log.debug("skip harvester_backend: %s", e)
        record_failure("remaining", "harvester_backend", str(e))
    try:
        from loom.tools.backends.hipporag_backend import research_memory_recall, research_memory_store
        mcp.tool()(wrap_tool(research_memory_recall))
        record_success("remaining", "research_memory_recall")
        mcp.tool()(wrap_tool(research_memory_store))
        record_success("remaining", "research_memory_store")
    except (ImportError, AttributeError) as e:
        log.debug("skip hipporag_backend: %s", e)
        record_failure("remaining", "hipporag_backend", str(e))
    try:
        from loom.tools.intelligence.identity_resolve import research_identity_resolve
        mcp.tool()(wrap_tool(research_identity_resolve))
        record_success("remaining", "research_identity_resolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip identity_resolve: %s", e)
        record_failure("remaining", "identity_resolve", str(e))
    try:
        from loom.tools.backends.instructor_backend import research_structured_extract
        mcp.tool()(wrap_tool(research_structured_extract))
        record_success("remaining", "research_structured_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip instructor_backend: %s", e)
        record_failure("remaining", "instructor_backend", str(e))
    try:
        from loom.tools.research.intel_report import research_brief_generate, research_intel_report
        mcp.tool()(wrap_tool(research_brief_generate))
        record_success("remaining", "research_brief_generate")
        mcp.tool()(wrap_tool(research_intel_report))
        record_success("remaining", "research_intel_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip intel_report: %s", e)
        record_failure("remaining", "intel_report", str(e))
    try:
        from loom.tools.backends.intelowl_backend import research_intelowl_analyze
        mcp.tool()(wrap_tool(research_intelowl_analyze))
        record_success("remaining", "research_intelowl_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip intelowl_backend: %s", e)
        record_failure("remaining", "intelowl_backend", str(e))
    try:
        from loom.tools.intelligence.invisible_web import research_invisible_web
        mcp.tool()(wrap_tool(research_invisible_web))
        record_success("remaining", "research_invisible_web")
    except (ImportError, AttributeError) as e:
        log.debug("skip invisible_web: %s", e)
        record_failure("remaining", "invisible_web", str(e))
    try:
        from loom.tools.adversarial.jailbreak_evolution import research_jailbreak_evolution_adapt, research_jailbreak_evolution_get, research_jailbreak_evolution_patches, research_jailbreak_evolution_record, research_jailbreak_evolution_stats, research_jailbreak_evolution_timeline
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
        from loom.tools.llm.knowledge_injector import research_adapt_complexity, research_personalize_output
        mcp.tool()(wrap_tool(research_adapt_complexity))
        record_success("remaining", "research_adapt_complexity")
        mcp.tool()(wrap_tool(research_personalize_output))
        record_success("remaining", "research_personalize_output")
    except (ImportError, AttributeError) as e:
        log.debug("skip knowledge_injector: %s", e)
        record_failure("remaining", "knowledge_injector", str(e))
    try:
        from loom.tools.backends.lightpanda_backend import research_lightpanda_batch, research_lightpanda_fetch
        mcp.tool()(wrap_tool(research_lightpanda_batch))
        record_success("remaining", "research_lightpanda_batch")
        mcp.tool()(wrap_tool(research_lightpanda_fetch))
        record_success("remaining", "research_lightpanda_fetch")
    except (ImportError, AttributeError) as e:
        log.debug("skip lightpanda_backend: %s", e)
        record_failure("remaining", "lightpanda_backend", str(e))
    try:
        from loom.tools.intelligence.linkedin_osint import research_linkedin_intel
        mcp.tool()(wrap_tool(research_linkedin_intel))
        record_success("remaining", "research_linkedin_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip linkedin_osint: %s", e)
        record_failure("remaining", "linkedin_osint", str(e))
    try:
        from loom.tools.backends.masscan_backend import research_masscan
        mcp.tool()(wrap_tool(research_masscan))
        record_success("remaining", "research_masscan")
    except (ImportError, AttributeError) as e:
        log.debug("skip masscan_backend: %s", e)
        record_failure("remaining", "masscan_backend", str(e))
    try:
        from loom.tools.backends.massdns_backend import research_massdns_resolve
        mcp.tool()(wrap_tool(research_massdns_resolve))
        record_success("remaining", "research_massdns_resolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip massdns_backend: %s", e)
        record_failure("remaining", "massdns_backend", str(e))
    try:
        from loom.tools.adversarial.memetic_simulator import research_memetic_simulate
        mcp.tool()(wrap_tool(research_memetic_simulate))
        record_success("remaining", "research_memetic_simulate")
    except (ImportError, AttributeError) as e:
        log.debug("skip memetic_simulator: %s", e)
        record_failure("remaining", "memetic_simulator", str(e))
    try:
        from loom.tools.llm.model_compare import research_compare_responses, research_model_consensus
        mcp.tool()(wrap_tool(research_compare_responses))
        record_success("remaining", "research_compare_responses")
        mcp.tool()(wrap_tool(research_model_consensus))
        record_success("remaining", "research_model_consensus")
    except (ImportError, AttributeError) as e:
        log.debug("skip model_compare: %s", e)
        record_failure("remaining", "model_compare", str(e))
    try:
        from loom.tools.research.neuromorphic import research_neuromorphic_schedule
        mcp.tool()(wrap_tool(research_neuromorphic_schedule))
        record_success("remaining", "research_neuromorphic_schedule")
    except (ImportError, AttributeError) as e:
        log.debug("skip neuromorphic: %s", e)
        record_failure("remaining", "neuromorphic", str(e))
    try:
        from loom.tools.llm.nl_executor import research_do
        mcp.tool()(wrap_tool(research_do))
        record_success("remaining", "research_do")
    except (ImportError, AttributeError) as e:
        log.debug("skip nl_executor: %s", e)
        record_failure("remaining", "nl_executor", str(e))
    try:
        from loom.tools.intelligence.onion_spectra import research_onion_spectra
        mcp.tool()(wrap_tool(research_onion_spectra))
        record_success("remaining", "research_onion_spectra")
    except (ImportError, AttributeError) as e:
        log.debug("skip onion_spectra: %s", e)
        record_failure("remaining", "onion_spectra", str(e))
    try:
        from loom.tools.backends.onionscan_backend import research_onionscan
        mcp.tool()(wrap_tool(research_onionscan))
        record_success("remaining", "research_onionscan")
    except (ImportError, AttributeError) as e:
        log.debug("skip onionscan_backend: %s", e)
        record_failure("remaining", "onionscan_backend", str(e))
    try:
        from loom.tools.infrastructure.openapi_gen import research_openapi_schema, research_tool_search
        mcp.tool()(wrap_tool(research_openapi_schema))
        record_success("remaining", "research_openapi_schema")
        mcp.tool()(wrap_tool(research_tool_search))
        record_success("remaining", "research_tool_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip openapi_gen: %s", e)
        record_failure("remaining", "openapi_gen", str(e))
    try:
        from loom.tools.backends.opencti_backend import research_opencti_query
        mcp.tool()(wrap_tool(research_opencti_query))
        record_success("remaining", "research_opencti_query")
    except (ImportError, AttributeError) as e:
        log.debug("skip opencti_backend: %s", e)
        record_failure("remaining", "opencti_backend", str(e))
    try:
        from loom.tools.backends.paddleocr_backend import research_paddle_ocr
        mcp.tool()(wrap_tool(research_paddle_ocr))
        record_success("remaining", "research_paddle_ocr")
    except (ImportError, AttributeError) as e:
        log.debug("skip paddleocr_backend: %s", e)
        record_failure("remaining", "paddleocr_backend", str(e))
    try:
        from loom.tools.research.paradox_detector import research_detect_paradox, research_paradox_immunize
        mcp.tool()(wrap_tool(research_detect_paradox))
        record_success("remaining", "research_detect_paradox")
        mcp.tool()(wrap_tool(research_paradox_immunize))
        record_success("remaining", "research_paradox_immunize")
    except (ImportError, AttributeError) as e:
        log.debug("skip paradox_detector: %s", e)
        record_failure("remaining", "paradox_detector", str(e))
    try:
        from loom.tools.infrastructure.parallel_executor import research_parallel_execute, research_parallel_plan_and_execute
        mcp.tool()(wrap_tool(research_parallel_execute))
        record_success("remaining", "research_parallel_execute")
        mcp.tool()(wrap_tool(research_parallel_plan_and_execute))
        record_success("remaining", "research_parallel_plan_and_execute")
    except (ImportError, AttributeError) as e:
        log.debug("skip parallel_executor: %s", e)
        record_failure("remaining", "parallel_executor", str(e))
    try:
        from loom.tools.adversarial.pathogen_sim import research_pathogen_evolve
        mcp.tool()(wrap_tool(research_pathogen_evolve))
        record_success("remaining", "research_pathogen_evolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip pathogen_sim: %s", e)
        record_failure("remaining", "pathogen_sim", str(e))
    try:
        from loom.tools.security.pentest import research_pentest_agent, research_pentest_docs, research_pentest_findings_db, research_pentest_plan, research_pentest_recommend
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
        from loom.tools.backends.photon_backend import research_photon_crawl
        mcp.tool()(wrap_tool(research_photon_crawl))
        record_success("remaining", "research_photon_crawl")
    except (ImportError, AttributeError) as e:
        log.debug("skip photon_backend: %s", e)
        record_failure("remaining", "photon_backend", str(e))
    try:
        from loom.tools.intelligence.polyglot_scraper import research_polyglot_search, research_subculture_intel
        mcp.tool()(wrap_tool(research_polyglot_search))
        record_success("remaining", "research_polyglot_search")
        mcp.tool()(wrap_tool(research_subculture_intel))
        record_success("remaining", "research_subculture_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip polyglot_scraper: %s", e)
        record_failure("remaining", "polyglot_scraper", str(e))
    try:
        from loom.tools.infrastructure.progress_tracker import research_progress_create, research_progress_dashboard, research_progress_update
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
        from loom.tools.llm.prompt_templates import research_template_list, research_template_render, research_template_suggest
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
        from loom.tools.backends.pydantic_ai_backend import research_pydantic_agent, research_structured_llm
        mcp.tool()(wrap_tool(research_pydantic_agent))
        record_success("remaining", "research_pydantic_agent")
        mcp.tool()(wrap_tool(research_structured_llm))
        record_success("remaining", "research_structured_llm")
    except (ImportError, AttributeError) as e:
        log.debug("skip pydantic_ai_backend: %s", e)
        record_failure("remaining", "pydantic_ai_backend", str(e))
    try:
        from loom.tools.llm.quality_escalation import research_quality_escalate
        mcp.tool()(wrap_tool(research_quality_escalate))
        record_success("remaining", "research_quality_escalate")
    except (ImportError, AttributeError) as e:
        log.debug("skip quality_escalation: %s", e)
        record_failure("remaining", "quality_escalation", str(e))
    try:
        from loom.tools.llm.query_builder import research_build_query
        mcp.tool()(wrap_tool(research_build_query))
        record_success("remaining", "research_build_query")
    except (ImportError, AttributeError) as e:
        log.debug("skip query_builder: %s", e)
        record_failure("remaining", "query_builder", str(e))
    try:
        from loom.tools.monitoring.realtime_monitor import research_realtime_monitor
        mcp.tool()(wrap_tool(research_realtime_monitor))
        record_success("remaining", "research_realtime_monitor")
    except (ImportError, AttributeError) as e:
        log.debug("skip realtime_monitor: %s", e)
        record_failure("remaining", "realtime_monitor", str(e))
    try:
        from loom.tools.backends.reconng_backend import research_reconng_scan
        mcp.tool()(wrap_tool(research_reconng_scan))
        record_success("remaining", "research_reconng_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip reconng_backend: %s", e)
        record_failure("remaining", "reconng_backend", str(e))
    try:
        from loom.tools.infrastructure.report_generator import research_generate_executive_report, research_generate_report
        mcp.tool()(wrap_tool(research_generate_executive_report))
        record_success("remaining", "research_generate_executive_report")
        mcp.tool()(wrap_tool(research_generate_report))
        record_success("remaining", "research_generate_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip report_generator: %s", e)
        record_failure("remaining", "report_generator", str(e))
    try:
        from loom.tools.infrastructure.report_templates import research_report_custom, research_report_template
        mcp.tool()(wrap_tool(research_report_custom))
        record_success("remaining", "research_report_custom")
        mcp.tool()(wrap_tool(research_report_template))
        record_success("remaining", "research_report_template")
    except (ImportError, AttributeError) as e:
        log.debug("skip report_templates: %s", e)
        record_failure("remaining", "report_templates", str(e))
    try:
        from loom.tools.llm.resilience_predictor import research_predict_resilience
        mcp.tool()(wrap_tool(research_predict_resilience))
        record_success("remaining", "research_predict_resilience")
    except (ImportError, AttributeError) as e:
        log.debug("skip resilience_predictor: %s", e)
        record_failure("remaining", "resilience_predictor", str(e))
    try:
        from loom.tools.core.response_cache import research_response_cache_stats
        mcp.tool()(wrap_tool(research_response_cache_stats))
        record_success("remaining", "research_response_cache_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip response_cache: %s", e)
        record_failure("remaining", "response_cache", str(e))
    try:
        from loom.tools.infrastructure.result_aggregator import research_aggregate_results, research_aggregate_texts
        mcp.tool()(wrap_tool(research_aggregate_results))
        record_success("remaining", "research_aggregate_results")
        mcp.tool()(wrap_tool(research_aggregate_texts))
        record_success("remaining", "research_aggregate_texts")
    except (ImportError, AttributeError) as e:
        log.debug("skip result_aggregator: %s", e)
        record_failure("remaining", "result_aggregator", str(e))
    try:
        from loom.tools.infrastructure.retry_middleware import research_retry_execute, research_retry_middleware_stats
        mcp.tool()(wrap_tool(research_retry_execute))
        record_success("remaining", "research_retry_execute")
        mcp.tool()(wrap_tool(research_retry_middleware_stats))
        record_success("remaining", "research_retry_middleware_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip retry_middleware: %s", e)
        record_failure("remaining", "retry_middleware", str(e))
    try:
        from loom.tools.backends.robin_backend import research_robin_scan
        mcp.tool()(wrap_tool(research_robin_scan))
        record_success("remaining", "research_robin_scan")
    except (ImportError, AttributeError) as e:
        log.debug("skip robin_backend: %s", e)
        record_failure("remaining", "robin_backend", str(e))
    try:
        from loom.tools.core.rss_monitor import research_rss_fetch, research_rss_search
        mcp.tool()(wrap_tool(research_rss_fetch))
        record_success("remaining", "research_rss_fetch")
        mcp.tool()(wrap_tool(research_rss_search))
        record_success("remaining", "research_rss_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip rss_monitor: %s", e)
        record_failure("remaining", "rss_monitor", str(e))
    try:
        from loom.tools.security.safety_predictor import research_predict_safety_update
        mcp.tool()(wrap_tool(research_predict_safety_update))
        record_success("remaining", "research_predict_safety_update")
    except (ImportError, AttributeError) as e:
        log.debug("skip safety_predictor: %s", e)
        record_failure("remaining", "safety_predictor", str(e))
    try:
        from loom.tools.security.sandbox import research_sandbox_analyze, research_sandbox_report
        mcp.tool()(wrap_tool(research_sandbox_analyze))
        record_success("remaining", "research_sandbox_analyze")
        mcp.tool()(wrap_tool(research_sandbox_report))
        record_success("remaining", "research_sandbox_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip sandbox: %s", e)
        record_failure("remaining", "sandbox", str(e))
    try:
        from loom.tools.backends.scapy_backend import research_packet_craft
        mcp.tool()(wrap_tool(research_packet_craft))
        record_success("remaining", "research_packet_craft")
    except (ImportError, AttributeError) as e:
        log.debug("skip scapy_backend: %s", e)
        record_failure("remaining", "scapy_backend", str(e))
    try:
        from loom.tools.security.security_headers import research_security_headers
        mcp.tool()(wrap_tool(research_security_headers))
        record_success("remaining", "research_security_headers")
    except (ImportError, AttributeError) as e:
        log.debug("skip security_headers: %s", e)
        record_failure("remaining", "security_headers", str(e))
    try:
        from loom.tools.backends.shodan_backend import research_shodan_host, research_shodan_search
        mcp.tool()(wrap_tool(research_shodan_host))
        record_success("remaining", "research_shodan_host")
        mcp.tool()(wrap_tool(research_shodan_search))
        record_success("remaining", "research_shodan_search")
    except (ImportError, AttributeError) as e:
        log.debug("skip shodan_backend: %s", e)
        record_failure("remaining", "shodan_backend", str(e))
    try:
        from loom.tools.monitoring.signal_detection import research_ghost_protocol, research_sec_tracker, research_temporal_anomaly
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
        from loom.tools.llm.simplifier import research_simplify
        mcp.tool()(wrap_tool(research_simplify))
        record_success("remaining", "research_simplify")
    except (ImportError, AttributeError) as e:
        log.debug("skip simplifier: %s", e)
        record_failure("remaining", "simplifier", str(e))
    try:
        from loom.tools.research.strange_attractors import research_attractor_trap
        mcp.tool()(wrap_tool(research_attractor_trap))
        record_success("remaining", "research_attractor_trap")
    except (ImportError, AttributeError) as e:
        log.debug("skip strange_attractors: %s", e)
        record_failure("remaining", "strange_attractors", str(e))
    try:
        from loom.tools.backends.supercookie_backend import research_supercookie_check
        mcp.tool()(wrap_tool(research_supercookie_check))
        record_success("remaining", "research_supercookie_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip supercookie_backend: %s", e)
        record_failure("remaining", "supercookie_backend", str(e))
    try:
        from loom.tools.intelligence.supply_chain import research_model_integrity, research_package_audit
        mcp.tool()(wrap_tool(research_model_integrity))
        record_success("remaining", "research_model_integrity")
        mcp.tool()(wrap_tool(research_package_audit))
        record_success("remaining", "research_package_audit")
    except (ImportError, AttributeError) as e:
        log.debug("skip supply_chain: %s", e)
        record_failure("remaining", "supply_chain", str(e))
    try:
        from loom.tools.intelligence.supply_chain_intel import research_dependency_audit, research_patent_landscape, research_supply_chain_risk
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
        from loom.tools.career.talent_tracker import research_talent_flow, research_track_researcher
        mcp.tool()(wrap_tool(research_talent_flow))
        record_success("remaining", "research_talent_flow")
        mcp.tool()(wrap_tool(research_track_researcher))
        record_success("remaining", "research_track_researcher")
    except (ImportError, AttributeError) as e:
        log.debug("skip talent_tracker: %s", e)
        record_failure("remaining", "talent_tracker", str(e))
    try:
        from loom.tools.intelligence.telegram_osint import research_telegram_intel
        mcp.tool()(wrap_tool(research_telegram_intel))
        record_success("remaining", "research_telegram_intel")
    except (ImportError, AttributeError) as e:
        log.debug("skip telegram_osint: %s", e)
        record_failure("remaining", "telegram_osint", str(e))
    try:
        from loom.tools.backends.testssl_backend import research_testssl
        mcp.tool()(wrap_tool(research_testssl))
        record_success("remaining", "research_testssl")
    except (ImportError, AttributeError) as e:
        log.debug("skip testssl_backend: %s", e)
        record_failure("remaining", "testssl_backend", str(e))
    try:
        from loom.tools.infrastructure.tool_health import research_health_alert, research_health_check_all, research_health_history
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
        from loom.tools.research.topology_manifold import research_topology_discover
        mcp.tool()(wrap_tool(research_topology_discover))
        record_success("remaining", "research_topology_discover")
    except (ImportError, AttributeError) as e:
        log.debug("skip topology_manifold: %s", e)
        record_failure("remaining", "topology_manifold", str(e))
    try:
        from loom.tools.research.transferability import research_transfer_test
        mcp.tool()(wrap_tool(research_transfer_test))
        record_success("remaining", "research_transfer_test")
    except (ImportError, AttributeError) as e:
        log.debug("skip transferability: %s", e)
        record_failure("remaining", "transferability", str(e))
    try:
        from loom.tools.research.uncertainty_harvest import research_active_select, research_uncertainty_estimate
        mcp.tool()(wrap_tool(research_active_select))
        record_success("remaining", "research_active_select")
        mcp.tool()(wrap_tool(research_uncertainty_estimate))
        record_success("remaining", "research_uncertainty_estimate")
    except (ImportError, AttributeError) as e:
        log.debug("skip uncertainty_harvest: %s", e)
        record_failure("remaining", "uncertainty_harvest", str(e))
    try:
        from loom.tools.backends.unstructured_backend import research_document_extract
        mcp.tool()(wrap_tool(research_document_extract))
        record_success("remaining", "research_document_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip unstructured_backend: %s", e)
        record_failure("remaining", "unstructured_backend", str(e))
    try:
        from loom.tools.backends.webcheck_backend import research_web_check
        mcp.tool()(wrap_tool(research_web_check))
        record_success("remaining", "research_web_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip webcheck_backend: %s", e)
        record_failure("remaining", "webcheck_backend", str(e))
    # ── Restored missing tools ──
    try:
        from loom.tools.research.synthetic_data import research_augment_dataset
        mcp.tool()(wrap_tool(research_augment_dataset))
        record_success("remaining", "research_augment_dataset")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "augment_dataset", str(e))
    try:
        from loom.tools.privacy.privacy_advanced import research_fileless_exec
        mcp.tool()(wrap_tool(research_fileless_exec))
        record_success("remaining", "research_fileless_exec")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "fileless_exec", str(e))
    try:
        from loom.tools.backends.neo4j_backend import research_graph_store
        mcp.tool()(wrap_tool(research_graph_store))
        record_success("remaining", "research_graph_store")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "graph_store", str(e))
    try:
        from loom.tools.llm.embedding_collision import research_rag_attack
        mcp.tool()(wrap_tool(research_rag_attack))
        record_success("remaining", "research_rag_attack")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "rag_attack", str(e))
    try:
        from loom.tools.research.auto_experiment import research_run_experiment
        mcp.tool()(wrap_tool(research_run_experiment))
        record_success("remaining", "research_run_experiment")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "run_experiment", str(e))
    try:
        from loom.tools.adversarial.hcs10_academic import research_shell_funding
        mcp.tool()(wrap_tool(research_shell_funding))
        record_success("remaining", "research_shell_funding")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "shell_funding", str(e))
    try:
        from loom.tools.intelligence.social_intel import research_social_profile
        mcp.tool()(wrap_tool(research_social_profile))
        record_success("remaining", "research_social_profile")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "social_profile", str(e))
    try:
        from loom.tools.security.enterprise_sso import research_sso_configure
        mcp.tool()(wrap_tool(research_sso_configure))
        record_success("remaining", "research_sso_configure")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "sso_configure", str(e))
    try:
        from loom.tools.privacy.stego_encoder import research_stego_encode
        mcp.tool()(wrap_tool(research_stego_encode))
        record_success("remaining", "research_stego_encode")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "stego_encode", str(e))
    try:
        from loom.tools.adversarial.multilang_attack import research_token_split_attack
        mcp.tool()(wrap_tool(research_token_split_attack))
        record_success("remaining", "research_token_split_attack")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "token_split_attack", str(e))
    try:
        from loom.tools.security.input_sanitizer import research_validate_params
        mcp.tool()(wrap_tool(research_validate_params))
        record_success("remaining", "research_validate_params")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "validate_params", str(e))
    try:
        from loom.tools.security.security_checklist import research_security_checklist as research_security_audit
        mcp.tool(name="research_security_audit")(wrap_tool(research_security_audit))
        record_success("remaining", "research_security_audit")
    except (ImportError, AttributeError) as e:
        record_failure("remaining", "security_audit", str(e))
    log.info("registered remaining tools")