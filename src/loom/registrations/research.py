"""Registration module for research tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.research")


def register_research_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 369 research tools."""
    try:
        from loom.tools.academic_integrity import research_citation_analysis, research_retraction_check, research_predatory_journal_check
        mcp.tool()(wrap_tool(research_citation_analysis))
        mcp.tool()(wrap_tool(research_retraction_check))
        mcp.tool()(wrap_tool(research_predatory_journal_check))
    except (ImportError, AttributeError) as e:
        log.debug("skip academic_integrity: %s", e)
    try:
        from loom.tools.access_tools import research_legal_takedown, research_open_access, research_content_authenticity, research_credential_monitor, research_deepfake_checker
        mcp.tool()(wrap_tool(research_legal_takedown))
        mcp.tool()(wrap_tool(research_open_access))
        mcp.tool()(wrap_tool(research_content_authenticity))
        mcp.tool()(wrap_tool(research_credential_monitor))
        mcp.tool()(wrap_tool(research_deepfake_checker))
    except (ImportError, AttributeError) as e:
        log.debug("skip access_tools: %s", e)
    try:
        from loom.tools.agent_benchmark import research_agent_benchmark
        mcp.tool()(wrap_tool(research_agent_benchmark))
    except (ImportError, AttributeError) as e:
        log.debug("skip agent_benchmark: %s", e)
    try:
        from loom.tools.antiforensics import research_usb_kill_monitor, research_artifact_cleanup
        mcp.tool()(wrap_tool(research_usb_kill_monitor))
        mcp.tool()(wrap_tool(research_artifact_cleanup))
    except (ImportError, AttributeError) as e:
        log.debug("skip antiforensics: %s", e)
    try:
        from loom.tools.api_version import research_api_version, research_api_changelog, research_api_deprecations
        mcp.tool()(wrap_tool(research_api_version))
        mcp.tool()(wrap_tool(research_api_changelog))
        mcp.tool()(wrap_tool(research_api_deprecations))
    except (ImportError, AttributeError) as e:
        log.debug("skip api_version: %s", e)
    try:
        from loom.tools.arxiv_pipeline import research_arxiv_ingest, research_arxiv_extract_techniques
        mcp.tool()(wrap_tool(research_arxiv_ingest))
        mcp.tool()(wrap_tool(research_arxiv_extract_techniques))
    except (ImportError, AttributeError) as e:
        log.debug("skip arxiv_pipeline: %s", e)
    try:
        from loom.auth import research_auth_create_token, research_auth_validate, research_auth_revoke
        mcp.tool()(wrap_tool(research_auth_create_token))
        mcp.tool()(wrap_tool(research_auth_validate))
        mcp.tool()(wrap_tool(research_auth_revoke))
    except (ImportError, AttributeError) as e:
        log.debug("skip auth_mod: %s", e)
    try:
        from loom.tools.auto_docs import research_generate_docs, research_docs_coverage
        mcp.tool()(wrap_tool(research_generate_docs))
        mcp.tool()(wrap_tool(research_docs_coverage))
    except (ImportError, AttributeError) as e:
        log.debug("skip auto_docs: %s", e)
    try:
        from loom.tools.auto_experiment import research_run_experiment, research_experiment_design
        mcp.tool()(wrap_tool(research_run_experiment))
        mcp.tool()(wrap_tool(research_experiment_design))
    except (ImportError, AttributeError) as e:
        log.debug("skip auto_experiment: %s", e)
    try:
        from loom.tools.auto_pipeline import research_auto_pipeline
        mcp.tool()(wrap_tool(research_auto_pipeline))
    except (ImportError, AttributeError) as e:
        log.debug("skip auto_pipeline: %s", e)
    try:
        from loom.tools.autonomous_agent import research_auto_redteam, research_schedule_redteam
        mcp.tool()(wrap_tool(research_auto_redteam))
        mcp.tool()(wrap_tool(research_schedule_redteam))
    except (ImportError, AttributeError) as e:
        log.debug("skip autonomous_agent: %s", e)
    try:
        from loom.tools.backoff_dlq import research_dlq_push, research_dlq_list, research_dlq_retry
        mcp.tool()(wrap_tool(research_dlq_push))
        mcp.tool()(wrap_tool(research_dlq_list))
        mcp.tool()(wrap_tool(research_dlq_retry))
    except (ImportError, AttributeError) as e:
        log.debug("skip backoff_dlq: %s", e)
    try:
        from loom.tools.benchmark_suite import research_benchmark_run, research_benchmark_compare
        mcp.tool()(wrap_tool(research_benchmark_run))
        mcp.tool()(wrap_tool(research_benchmark_compare))
    except (ImportError, AttributeError) as e:
        log.debug("skip benchmark_suite: %s", e)
    try:
        from loom.tools.bias_lens import research_bias_lens
        mcp.tool()(wrap_tool(research_bias_lens))
    except (ImportError, AttributeError) as e:
        log.debug("skip bias_lens: %s", e)
    try:
        from loom.tools.cache_mgmt import research_semantic_cache_stats, research_semantic_cache_clear
        mcp.tool()(wrap_tool(research_semantic_cache_stats))
        mcp.tool()(wrap_tool(research_semantic_cache_clear))
    except (ImportError, AttributeError) as e:
        log.debug("skip cache_mod: %s", e)
    try:
        from loom.tools.career_intel import research_map_research_to_product, research_translate_academic_skills
        mcp.tool()(wrap_tool(research_map_research_to_product))
        mcp.tool()(wrap_tool(research_translate_academic_skills))
    except (ImportError, AttributeError) as e:
        log.debug("skip career_intel_mod: %s", e)
    try:
        from loom.tools.career_traj import research_career_trajectory, research_market_velocity
        mcp.tool()(wrap_tool(research_career_trajectory))
        mcp.tool()(wrap_tool(research_market_velocity))
    except (ImportError, AttributeError) as e:
        log.debug("skip career_traj_mod: %s", e)
    try:
        from loom.tools.chain_composer import research_chain_define, research_chain_list, research_chain_describe
        mcp.tool()(wrap_tool(research_chain_define))
        mcp.tool()(wrap_tool(research_chain_list))
        mcp.tool()(wrap_tool(research_chain_describe))
    except (ImportError, AttributeError) as e:
        log.debug("skip chain_composer: %s", e)
    try:
        from loom.tools.changelog_gen import research_changelog_generate, research_changelog_stats
        mcp.tool()(wrap_tool(research_changelog_generate))
        mcp.tool()(wrap_tool(research_changelog_stats))
    except (ImportError, AttributeError) as e:
        log.debug("skip changelog_gen: %s", e)
    try:
        from loom.tools.chronos import research_chronos_reverse
        mcp.tool()(wrap_tool(research_chronos_reverse))
    except (ImportError, AttributeError) as e:
        log.debug("skip chronos: %s", e)
    try:
        from loom.tools.circuit_breaker import research_breaker_status, research_breaker_trip, research_breaker_reset
        mcp.tool()(wrap_tool(research_breaker_status))
        mcp.tool()(wrap_tool(research_breaker_trip))
        mcp.tool()(wrap_tool(research_breaker_reset))
    except (ImportError, AttributeError) as e:
        log.debug("skip circuit_breaker: %s", e)
    try:
        from loom.tools.compliance_checker import research_compliance_check, research_pii_scan
        mcp.tool()(wrap_tool(research_compliance_check))
        mcp.tool()(wrap_tool(research_pii_scan))
    except (ImportError, AttributeError) as e:
        log.debug("skip compliance_checker: %s", e)
    try:
        from loom.tools.consistency import research_consistency_pressure, research_consistency_pressure_history, research_consistency_pressure_record
        mcp.tool()(wrap_tool(research_consistency_pressure))
        mcp.tool()(wrap_tool(research_consistency_pressure_history))
        mcp.tool()(wrap_tool(research_consistency_pressure_record))
    except (ImportError, AttributeError) as e:
        log.debug("skip consistency_mod: %s", e)
    try:
        from loom.tools.constraint import research_constraint_optimize
        mcp.tool()(wrap_tool(research_constraint_optimize))
    except (ImportError, AttributeError) as e:
        log.debug("skip constraint_mod: %s", e)
    try:
        from loom.tools.context_manager import research_context_set, research_context_get, research_context_clear
        mcp.tool()(wrap_tool(research_context_set))
        mcp.tool()(wrap_tool(research_context_get))
        mcp.tool()(wrap_tool(research_context_clear))
    except (ImportError, AttributeError) as e:
        log.debug("skip context_manager: %s", e)
    try:
        from loom.tools.crawlee_backend import research_crawl, research_sitemap_crawl, research_structured_crawl
        mcp.tool()(wrap_tool(research_crawl))
        mcp.tool()(wrap_tool(research_sitemap_crawl))
        mcp.tool()(wrap_tool(research_structured_crawl))
    except (ImportError, AttributeError) as e:
        log.debug("skip crawlee_backend: %s", e)
    try:
        from loom.tools.creative import research_ai_detect, research_citation_graph, research_community_sentiment, research_curriculum, research_misinfo_check, research_multilingual, research_red_team, research_semantic_sitemap, research_temporal_diff, research_wiki_ghost
        mcp.tool()(wrap_tool(research_ai_detect))
        mcp.tool()(wrap_tool(research_citation_graph))
        mcp.tool()(wrap_tool(research_community_sentiment))
        mcp.tool()(wrap_tool(research_curriculum))
        mcp.tool()(wrap_tool(research_misinfo_check))
        mcp.tool()(wrap_tool(research_multilingual))
        mcp.tool()(wrap_tool(research_red_team))
        mcp.tool()(wrap_tool(research_semantic_sitemap))
        mcp.tool()(wrap_tool(research_temporal_diff))
        mcp.tool()(wrap_tool(research_wiki_ghost))
    except (ImportError, AttributeError) as e:
        log.debug("skip creative_mod: %s", e)
    try:
        from loom.tools.crypto_risk import research_crypto_risk_score
        mcp.tool()(wrap_tool(research_crypto_risk_score))
    except (ImportError, AttributeError) as e:
        log.debug("skip crypto_risk: %s", e)
    try:
        from loom.tools.cultural_attacks import research_cultural_reframe, research_multilingual_attack
        mcp.tool()(wrap_tool(research_cultural_reframe))
        mcp.tool()(wrap_tool(research_multilingual_attack))
    except (ImportError, AttributeError) as e:
        log.debug("skip cultural_attacks: %s", e)
    try:
        from loom.tools.culture_dna import research_culture_dna
        mcp.tool()(wrap_tool(research_culture_dna))
    except (ImportError, AttributeError) as e:
        log.debug("skip culture_dna: %s", e)
    try:
        from loom.tools.cyberscraper import research_smart_extract, research_paginate_scrape, research_stealth_browser
        mcp.tool()(wrap_tool(research_smart_extract))
        mcp.tool()(wrap_tool(research_paginate_scrape))
        mcp.tool()(wrap_tool(research_stealth_browser))
    except (ImportError, AttributeError) as e:
        log.debug("skip cyberscraper: %s", e)
    try:
        from loom.tools.data_export import research_export_json, research_export_csv, research_export_list
        mcp.tool()(wrap_tool(research_export_json))
        mcp.tool()(wrap_tool(research_export_csv))
        mcp.tool()(wrap_tool(research_export_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip data_export: %s", e)
    try:
        from loom.tools.data_pipeline import research_pipeline_create, research_pipeline_validate, research_pipeline_list
        mcp.tool()(wrap_tool(research_pipeline_create))
        mcp.tool()(wrap_tool(research_pipeline_validate))
        mcp.tool()(wrap_tool(research_pipeline_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip data_pipeline: %s", e)
    try:
        from loom.tools.dead_drop_scanner import research_dead_drop_scanner
        mcp.tool()(wrap_tool(research_dead_drop_scanner))
    except (ImportError, AttributeError) as e:
        log.debug("skip dead_drop_scanner_mod: %s", e)
    try:
        from loom.tools.deception_detect import research_deception_detect
        mcp.tool()(wrap_tool(research_deception_detect))
    except (ImportError, AttributeError) as e:
        log.debug("skip deception_detect: %s", e)
    try:
        from loom.tools.deception_job_scanner import research_deception_job_scan
        mcp.tool()(wrap_tool(research_deception_job_scan))
    except (ImportError, AttributeError) as e:
        log.debug("skip deception_job_scanner: %s", e)
    try:
        from loom.tools.deep_research_agent import research_hierarchical_research
        mcp.tool()(wrap_tool(research_hierarchical_research))
    except (ImportError, AttributeError) as e:
        log.debug("skip deep_research_agent: %s", e)
    try:
        from loom.tools.dependency_graph import research_tool_dependencies, research_tool_impact
        mcp.tool()(wrap_tool(research_tool_dependencies))
        mcp.tool()(wrap_tool(research_tool_impact))
    except (ImportError, AttributeError) as e:
        log.debug("skip dependency_graph: %s", e)
    try:
        from loom.tools.doc_parser import research_ocr_advanced, research_pdf_advanced, research_document_analyze
        mcp.tool()(wrap_tool(research_ocr_advanced))
        mcp.tool()(wrap_tool(research_pdf_advanced))
        mcp.tool()(wrap_tool(research_document_analyze))
    except (ImportError, AttributeError) as e:
        log.debug("skip doc_parser_tools: %s", e)
    try:
        from loom.tools.document import research_convert_document
        mcp.tool()(wrap_tool(research_convert_document))
    except (ImportError, AttributeError) as e:
        log.debug("skip document_mod: %s", e)
    try:
        from loom.tools.embedding_collision import research_embedding_collide, research_rag_attack
        mcp.tool()(wrap_tool(research_embedding_collide))
        mcp.tool()(wrap_tool(research_rag_attack))
    except (ImportError, AttributeError) as e:
        log.debug("skip embedding_collision: %s", e)
    try:
        from loom.tools.enrich import research_detect_language, research_wayback
        mcp.tool()(wrap_tool(research_detect_language))
        mcp.tool()(wrap_tool(research_wayback))
    except (ImportError, AttributeError) as e:
        log.debug("skip enrich_mod: %s", e)
    try:
        from loom.tools.ensemble_attack import research_ensemble_attack, research_attack_portfolio
        mcp.tool()(wrap_tool(research_ensemble_attack))
        mcp.tool()(wrap_tool(research_attack_portfolio))
    except (ImportError, AttributeError) as e:
        log.debug("skip ensemble_attack: %s", e)
    try:
        from loom.tools.enterprise_sso import research_sso_configure, research_sso_validate_token, research_sso_user_info
        mcp.tool()(wrap_tool(research_sso_configure))
        mcp.tool()(wrap_tool(research_sso_validate_token))
        mcp.tool()(wrap_tool(research_sso_user_info))
    except (ImportError, AttributeError) as e:
        log.debug("skip enterprise_sso: %s", e)
    try:
        from loom.tools.epistemic import research_epistemic_score
        mcp.tool()(wrap_tool(research_epistemic_score))
    except (ImportError, AttributeError) as e:
        log.debug("skip epistemic_mod: %s", e)
    try:
        from loom.tools.ethereum import research_ethereum_tx_decode, research_defi_security_audit
        mcp.tool()(wrap_tool(research_ethereum_tx_decode))
        mcp.tool()(wrap_tool(research_defi_security_audit))
    except (ImportError, AttributeError) as e:
        log.debug("skip ethereum_tools: %s", e)
    try:
        from loom.tools.experts import research_find_experts
        mcp.tool()(wrap_tool(research_find_experts))
    except (ImportError, AttributeError) as e:
        log.debug("skip experts_mod: %s", e)
    try:
        from loom.tools.explainability import research_explain_bypass, research_vulnerability_map
        mcp.tool()(wrap_tool(research_explain_bypass))
        mcp.tool()(wrap_tool(research_vulnerability_map))
    except (ImportError, AttributeError) as e:
        log.debug("skip explainability: %s", e)
    try:
        from loom.tools.fact_checker import research_fact_check
        mcp.tool()(wrap_tool(research_fact_check))
    except (ImportError, AttributeError) as e:
        log.debug("skip fact_checker: %s", e)
    try:
        from loom.tools.feature_flags import research_flag_check, research_flag_toggle, research_flag_list
        mcp.tool()(wrap_tool(research_flag_check))
        mcp.tool()(wrap_tool(research_flag_toggle))
        mcp.tool()(wrap_tool(research_flag_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip feature_flags: %s", e)
    try:
        from loom.tools.fingerprint_evasion import research_fingerprint_evasion_test
        mcp.tool()(wrap_tool(research_fingerprint_evasion_test))
    except (ImportError, AttributeError) as e:
        log.debug("skip fingerprint_evasion: %s", e)
    try:
        from loom.tools.gamification import research_leaderboard, research_challenge_create, research_challenge_list
        mcp.tool()(wrap_tool(research_leaderboard))
        mcp.tool()(wrap_tool(research_challenge_create))
        mcp.tool()(wrap_tool(research_challenge_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip gamification: %s", e)
    try:
        from loom.tools.gap_tools_academic import research_ideological_drift, research_author_clustering, research_citation_cartography
        mcp.tool()(wrap_tool(research_ideological_drift))
        mcp.tool()(wrap_tool(research_author_clustering))
        mcp.tool()(wrap_tool(research_citation_cartography))
    except (ImportError, AttributeError) as e:
        log.debug("skip gap_tools_academic: %s", e)
    try:
        from loom.tools.gap_tools_advanced import research_talent_migration, research_funding_pipeline, research_jailbreak_library, research_patent_embargo
        mcp.tool()(wrap_tool(research_talent_migration))
        mcp.tool()(wrap_tool(research_funding_pipeline))
        mcp.tool()(wrap_tool(research_jailbreak_library))
        mcp.tool()(wrap_tool(research_patent_embargo))
    except (ImportError, AttributeError) as e:
        log.debug("skip gap_tools_advanced: %s", e)
    try:
        from loom.tools.gap_tools_ai import research_capability_mapper, research_memorization_scanner, research_training_contamination
        mcp.tool()(wrap_tool(research_capability_mapper))
        mcp.tool()(wrap_tool(research_memorization_scanner))
        mcp.tool()(wrap_tool(research_training_contamination))
    except (ImportError, AttributeError) as e:
        log.debug("skip gap_tools_ai: %s", e)
    try:
        from loom.tools.gap_tools_infra import research_cloud_enum, research_github_secrets, research_whois_correlator, research_output_consistency
        mcp.tool()(wrap_tool(research_cloud_enum))
        mcp.tool()(wrap_tool(research_github_secrets))
        mcp.tool()(wrap_tool(research_whois_correlator))
        mcp.tool()(wrap_tool(research_output_consistency))
    except (ImportError, AttributeError) as e:
        log.debug("skip gap_tools_infra: %s", e)
    try:
        from loom.tools.geodesic_forcing import research_geodesic_path
        mcp.tool()(wrap_tool(research_geodesic_path))
    except (ImportError, AttributeError) as e:
        log.debug("skip geodesic_forcing: %s", e)
    try:
        from loom.tools.geoip import research_geoip_local
        mcp.tool()(wrap_tool(research_geoip_local))
    except (ImportError, AttributeError) as e:
        log.debug("skip geoip_mod: %s", e)
    try:
        from loom.tools.graph_analysis import research_graph_analyze, research_transaction_graph
        mcp.tool()(wrap_tool(research_graph_analyze))
        mcp.tool()(wrap_tool(research_transaction_graph))
    except (ImportError, AttributeError) as e:
        log.debug("skip graph_analysis: %s", e)
    try:
        from loom.tools.graph_scraper import research_graph_scrape, research_knowledge_extract, research_multi_page_graph
        mcp.tool()(wrap_tool(research_graph_scrape))
        mcp.tool()(wrap_tool(research_knowledge_extract))
        mcp.tool()(wrap_tool(research_multi_page_graph))
    except (ImportError, AttributeError) as e:
        log.debug("skip graph_scraper: %s", e)
    try:
        from loom.tools.hcs10_academic import research_grant_forensics, research_monoculture_detect, research_review_cartel, research_data_fabrication, research_institutional_decay, research_shell_funding, research_conference_arbitrage, research_preprint_manipulation
        mcp.tool()(wrap_tool(research_grant_forensics))
        mcp.tool()(wrap_tool(research_monoculture_detect))
        mcp.tool()(wrap_tool(research_review_cartel))
        mcp.tool()(wrap_tool(research_data_fabrication))
        mcp.tool()(wrap_tool(research_institutional_decay))
        mcp.tool()(wrap_tool(research_shell_funding))
        mcp.tool()(wrap_tool(research_conference_arbitrage))
        mcp.tool()(wrap_tool(research_preprint_manipulation))
    except (ImportError, AttributeError) as e:
        log.debug("skip hcs10_academic: %s", e)
    try:
        from loom.tools.hcs_escalation import research_hcs_escalate
        mcp.tool()(wrap_tool(research_hcs_escalate))
    except (ImportError, AttributeError) as e:
        log.debug("skip hcs_escalation: %s", e)
    try:
        from loom.tools.hcs_report import research_hcs_report
        mcp.tool()(wrap_tool(research_hcs_report))
    except (ImportError, AttributeError) as e:
        log.debug("skip hcs_report: %s", e)
    try:
        from loom.tools.hcs_rubric_tool import research_hcs_rubric
        mcp.tool()(wrap_tool(research_hcs_rubric))
    except (ImportError, AttributeError) as e:
        log.debug("skip hcs_rubric_tool: %s", e)
    try:
        from loom.tools.hcs_scorer import research_hcs_score
        mcp.tool()(wrap_tool(research_hcs_score))
    except (ImportError, AttributeError) as e:
        log.debug("skip hcs_scorer: %s", e)
    try:
        from loom.tools.health_dashboard import research_dashboard_html
        mcp.tool()(wrap_tool(research_dashboard_html))
    except (ImportError, AttributeError) as e:
        log.debug("skip health_dashboard: %s", e)
    try:
        from loom.tools.hitl_eval import research_hitl_submit, research_hitl_evaluate, research_hitl_queue
        mcp.tool()(wrap_tool(research_hitl_submit))
        mcp.tool()(wrap_tool(research_hitl_evaluate))
        mcp.tool()(wrap_tool(research_hitl_queue))
    except (ImportError, AttributeError) as e:
        log.debug("skip hitl_eval: %s", e)
    try:
        from loom.tools.holographic_payload import research_holographic_encode
        mcp.tool()(wrap_tool(research_holographic_encode))
    except (ImportError, AttributeError) as e:
        log.debug("skip holographic_payload: %s", e)
    try:
        from loom.tools.image import research_exif_extract, research_ocr_extract
        mcp.tool()(wrap_tool(research_exif_extract))
        mcp.tool()(wrap_tool(research_ocr_extract))
    except (ImportError, AttributeError) as e:
        log.debug("skip image_mod: %s", e)
    try:
        from loom.tools.infowar import research_narrative_tracker, research_bot_detector, research_censorship_detector, research_deleted_social, research_robots_archaeology
        mcp.tool()(wrap_tool(research_narrative_tracker))
        mcp.tool()(wrap_tool(research_bot_detector))
        mcp.tool()(wrap_tool(research_censorship_detector))
        mcp.tool()(wrap_tool(research_deleted_social))
        mcp.tool()(wrap_tool(research_robots_archaeology))
    except (ImportError, AttributeError) as e:
        log.debug("skip infowar_tools: %s", e)
    try:
        from loom.tools.infra_analysis import research_registry_graveyard, research_subdomain_temporal, research_commit_analyzer
        mcp.tool()(wrap_tool(research_registry_graveyard))
        mcp.tool()(wrap_tool(research_subdomain_temporal))
        mcp.tool()(wrap_tool(research_commit_analyzer))
    except (ImportError, AttributeError) as e:
        log.debug("skip infra_analysis: %s", e)
    try:
        from loom.tools.input_sanitizer import research_sanitize_input, research_validate_params
        mcp.tool()(wrap_tool(research_sanitize_input))
        mcp.tool()(wrap_tool(research_validate_params))
    except (ImportError, AttributeError) as e:
        log.debug("skip input_sanitizer: %s", e)
    try:
        from loom.tools.integration_runner import research_integration_test, research_smoke_test
        mcp.tool()(wrap_tool(research_integration_test))
        mcp.tool()(wrap_tool(research_smoke_test))
    except (ImportError, AttributeError) as e:
        log.debug("skip integration_runner: %s", e)
    try:
        from loom.tools.job_research import research_job_search, research_job_market
        mcp.tool()(wrap_tool(research_job_search))
        mcp.tool()(wrap_tool(research_job_market))
    except (ImportError, AttributeError) as e:
        log.debug("skip job_research_mod: %s", e)
    try:
        from loom.tools.job_signals import research_funding_signal, research_stealth_hire_scanner, research_interviewer_profiler
        mcp.tool()(wrap_tool(research_funding_signal))
        mcp.tool()(wrap_tool(research_stealth_hire_scanner))
        mcp.tool()(wrap_tool(research_interviewer_profiler))
    except (ImportError, AttributeError) as e:
        log.debug("skip job_signals: %s", e)
    try:
        from loom.tools.js_intel import research_js_intel
        mcp.tool()(wrap_tool(research_js_intel))
    except (ImportError, AttributeError) as e:
        log.debug("skip js_intel: %s", e)
    try:
        from loom.tools.json_logger import research_log_query, research_log_stats
        mcp.tool()(wrap_tool(research_log_query))
        mcp.tool()(wrap_tool(research_log_stats))
    except (ImportError, AttributeError) as e:
        log.debug("skip json_logger: %s", e)
    try:
        from loom.tools.knowledge_base import research_kb_store, research_kb_search, research_kb_stats
        mcp.tool()(wrap_tool(research_kb_store))
        mcp.tool()(wrap_tool(research_kb_search))
        mcp.tool()(wrap_tool(research_kb_stats))
    except (ImportError, AttributeError) as e:
        log.debug("skip knowledge_base: %s", e)
    try:
        from loom.tools.knowledge_graph import research_knowledge_graph
        mcp.tool()(wrap_tool(research_knowledge_graph))
    except (ImportError, AttributeError) as e:
        log.debug("skip knowledge_graph: %s", e)
    try:
        from loom.tools.lifetime_oracle import research_lifetime_predict
        mcp.tool()(wrap_tool(research_lifetime_predict))
    except (ImportError, AttributeError) as e:
        log.debug("skip lifetime_oracle: %s", e)
    try:
        from loom.tools.live_registry import research_registry_status, research_registry_search, research_registry_refresh
        mcp.tool()(wrap_tool(research_registry_status))
        mcp.tool()(wrap_tool(research_registry_search))
        mcp.tool()(wrap_tool(research_registry_refresh))
    except (ImportError, AttributeError) as e:
        log.debug("skip live_registry: %s", e)
    try:
        from loom.tools.llm import research_llm_summarize, research_llm_extract, research_llm_classify, research_llm_translate, research_llm_query_expand, research_llm_answer, research_llm_embed, research_llm_chat
        mcp.tool()(wrap_tool(research_llm_summarize))
        mcp.tool()(wrap_tool(research_llm_extract))
        mcp.tool()(wrap_tool(research_llm_classify))
        mcp.tool()(wrap_tool(research_llm_translate))
        mcp.tool()(wrap_tool(research_llm_query_expand))
        mcp.tool()(wrap_tool(research_llm_answer))
        mcp.tool()(wrap_tool(research_llm_embed))
        mcp.tool()(wrap_tool(research_llm_chat))
    except (ImportError, AttributeError) as e:
        log.debug("skip llm_mod: %s", e)
    try:
        from loom.tools.meta_learner import research_meta_learn
        mcp.tool()(wrap_tool(research_meta_learn))
    except (ImportError, AttributeError) as e:
        log.debug("skip meta_learner: %s", e)
    try:
        from loom.tools.metadata_forensics import research_metadata_forensics
        mcp.tool()(wrap_tool(research_metadata_forensics))
    except (ImportError, AttributeError) as e:
        log.debug("skip metadata_forensics: %s", e)
    try:
        from loom.tools.metric_alerts import research_alert_create, research_alert_check, research_alert_list
        mcp.tool()(wrap_tool(research_alert_create))
        mcp.tool()(wrap_tool(research_alert_check))
        mcp.tool()(wrap_tool(research_alert_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip metric_alerts: %s", e)
    try:
        from loom.tools.mod import research_attack_score, research_stealth_score, research_potency_score, research_model_sentiment, research_toxicity_check, research_drift_monitor, research_drift_monitor_list, research_bpj_generate, research_daisy_chain, research_strategy_oracle, research_stealth_detect, research_recommend_tools, research_multi_consensus
        mcp.tool()(wrap_tool(research_attack_score))
        mcp.tool()(wrap_tool(research_stealth_score))
        mcp.tool()(wrap_tool(research_potency_score))
        mcp.tool()(wrap_tool(research_model_sentiment))
        mcp.tool()(wrap_tool(research_toxicity_check))
        mcp.tool()(wrap_tool(research_drift_monitor))
        mcp.tool()(wrap_tool(research_drift_monitor_list))
        mcp.tool()(wrap_tool(research_bpj_generate))
        mcp.tool()(wrap_tool(research_daisy_chain))
        mcp.tool()(wrap_tool(research_strategy_oracle))
        mcp.tool()(wrap_tool(research_stealth_detect))
        mcp.tool()(wrap_tool(research_recommend_tools))
        mcp.tool()(wrap_tool(research_multi_consensus))
    except (ImportError, AttributeError) as e:
        log.debug("skip mod: %s", e)
    try:
        from loom.tools.model_fingerprinter import research_fingerprint_behavior
        mcp.tool()(wrap_tool(research_fingerprint_behavior))
    except (ImportError, AttributeError) as e:
        log.debug("skip model_fingerprinter: %s", e)
    try:
        from loom.tools.multilang_attack import research_code_switch_attack, research_script_confusion, research_token_split_attack
        mcp.tool()(wrap_tool(research_code_switch_attack))
        mcp.tool()(wrap_tool(research_script_confusion))
        mcp.tool()(wrap_tool(research_token_split_attack))
    except (ImportError, AttributeError) as e:
        log.debug("skip multilang_attack: %s", e)
    try:
        from loom.tools.neo4j_backend import research_graph_store, research_graph_query, research_graph_visualize
        mcp.tool()(wrap_tool(research_graph_store))
        mcp.tool()(wrap_tool(research_graph_query))
        mcp.tool()(wrap_tool(research_graph_visualize))
    except (ImportError, AttributeError) as e:
        log.debug("skip neo4j_backend: %s", e)
    try:
        from loom.tools.network_map import research_network_map, research_network_visualize
        mcp.tool()(wrap_tool(research_network_map))
        mcp.tool()(wrap_tool(research_network_visualize))
    except (ImportError, AttributeError) as e:
        log.debug("skip network_map: %s", e)
    try:
        from loom.tools.network_persona import research_network_persona
        mcp.tool()(wrap_tool(research_network_persona))
    except (ImportError, AttributeError) as e:
        log.debug("skip network_persona_mod: %s", e)
    try:
        from loom.tools.nightcrawler import research_arxiv_scan, research_nightcrawler_status
        mcp.tool()(wrap_tool(research_arxiv_scan))
        mcp.tool()(wrap_tool(research_nightcrawler_status))
    except (ImportError, AttributeError) as e:
        log.debug("skip nightcrawler: %s", e)
    try:
        from loom.tools.nodriver import research_nodriver_fetch, research_nodriver_extract, research_nodriver_session
        mcp.tool()(wrap_tool(research_nodriver_fetch))
        mcp.tool()(wrap_tool(research_nodriver_extract))
        mcp.tool()(wrap_tool(research_nodriver_session))
    except (ImportError, AttributeError) as e:
        log.debug("skip nodriver_mod: %s", e)
    try:
        from loom.tools.notifications import research_notify_send, research_notify_history, research_notify_rules
        mcp.tool()(wrap_tool(research_notify_send))
        mcp.tool()(wrap_tool(research_notify_history))
        mcp.tool()(wrap_tool(research_notify_rules))
    except (ImportError, AttributeError) as e:
        log.debug("skip notifications: %s", e)
    try:
        from loom.tools.osint_extended import research_social_engineering_score, research_behavioral_fingerprint
        mcp.tool()(wrap_tool(research_social_engineering_score))
        mcp.tool()(wrap_tool(research_behavioral_fingerprint))
    except (ImportError, AttributeError) as e:
        log.debug("skip osint_extended: %s", e)
    try:
        from loom.tools.output_diff import research_diff_compare, research_diff_track
        mcp.tool()(wrap_tool(research_diff_compare))
        mcp.tool()(wrap_tool(research_diff_track))
    except (ImportError, AttributeError) as e:
        log.debug("skip output_diff: %s", e)
    try:
        from loom.tools.output_formatter import research_format_report, research_extract_actionables
        mcp.tool()(wrap_tool(research_format_report))
        mcp.tool()(wrap_tool(research_extract_actionables))
    except (ImportError, AttributeError) as e:
        log.debug("skip output_formatter: %s", e)
    try:
        from loom.tools.p3 import research_model_comparator, research_data_poisoning, research_wiki_event_correlator, research_foia_tracker
        mcp.tool()(wrap_tool(research_model_comparator))
        mcp.tool()(wrap_tool(research_data_poisoning))
        mcp.tool()(wrap_tool(research_wiki_event_correlator))
        mcp.tool()(wrap_tool(research_foia_tracker))
    except (ImportError, AttributeError) as e:
        log.debug("skip p3_tools: %s", e)
    try:
        from loom.tools.param import research_parameter_sweep
        mcp.tool()(wrap_tool(research_parameter_sweep))
    except (ImportError, AttributeError) as e:
        log.debug("skip param_mod: %s", e)
    try:
        from loom.tools.pdf_extract import research_pdf_extract, research_pdf_search
        mcp.tool()(wrap_tool(research_pdf_extract))
        mcp.tool()(wrap_tool(research_pdf_search))
    except (ImportError, AttributeError) as e:
        log.debug("skip pdf_extract: %s", e)
    try:
        from loom.tools.persistent_memory import research_remember, research_recall, research_memory_stats
        mcp.tool()(wrap_tool(research_remember))
        mcp.tool()(wrap_tool(research_recall))
        mcp.tool()(wrap_tool(research_memory_stats))
    except (ImportError, AttributeError) as e:
        log.debug("skip persistent_memory: %s", e)
    try:
        from loom.tools.persona_profile import research_persona_profile
        mcp.tool()(wrap_tool(research_persona_profile))
    except (ImportError, AttributeError) as e:
        log.debug("skip persona_profile_mod: %s", e)
    try:
        from loom.tools.plugin_loader import research_plugin_load, research_plugin_list, research_plugin_unload
        mcp.tool()(wrap_tool(research_plugin_load))
        mcp.tool()(wrap_tool(research_plugin_list))
        mcp.tool()(wrap_tool(research_plugin_unload))
    except (ImportError, AttributeError) as e:
        log.debug("skip plugin_loader: %s", e)
    try:
        from loom.tools.predictive_ranker import research_predict_success
        mcp.tool()(wrap_tool(research_predict_success))
    except (ImportError, AttributeError) as e:
        log.debug("skip predictive_ranker: %s", e)
    try:
        from loom.tools.privacy_advanced import research_browser_fingerprint_audit, research_metadata_strip, research_secure_delete, research_mac_randomize, research_dns_leak_check, research_tor_circuit_info, research_privacy_score
        mcp.tool()(wrap_tool(research_browser_fingerprint_audit))
        mcp.tool()(wrap_tool(research_metadata_strip))
        mcp.tool()(wrap_tool(research_secure_delete))
        mcp.tool()(wrap_tool(research_mac_randomize))
        mcp.tool()(wrap_tool(research_dns_leak_check))
        mcp.tool()(wrap_tool(research_tor_circuit_info))
        mcp.tool()(wrap_tool(research_privacy_score))
    except (ImportError, AttributeError) as e:
        log.debug("skip privacy_advanced: %s", e)
    try:
        from loom.tools.proactive_defense import research_predict_attacks, research_preemptive_patch
        mcp.tool()(wrap_tool(research_predict_attacks))
        mcp.tool()(wrap_tool(research_preemptive_patch))
    except (ImportError, AttributeError) as e:
        log.debug("skip proactive_defense: %s", e)
    try:
        from loom.tools.provider_health import research_provider_ping, research_provider_history, research_provider_recommend
        mcp.tool()(wrap_tool(research_provider_ping))
        mcp.tool()(wrap_tool(research_provider_history))
        mcp.tool()(wrap_tool(research_provider_recommend))
    except (ImportError, AttributeError) as e:
        log.debug("skip provider_health: %s", e)
    try:
        from loom.tools.radicalization_detect import research_radicalization_detect
        mcp.tool()(wrap_tool(research_radicalization_detect))
    except (ImportError, AttributeError) as e:
        log.debug("skip radicalization_detect_mod: %s", e)
    try:
        from loom.tools.rag_anything import research_rag_ingest, research_rag_query, research_rag_clear
        mcp.tool()(wrap_tool(research_rag_ingest))
        mcp.tool()(wrap_tool(research_rag_query))
        mcp.tool()(wrap_tool(research_rag_clear))
    except (ImportError, AttributeError) as e:
        log.debug("skip rag_anything: %s", e)
    try:
        from loom.tools.rate_limiter_tool import research_ratelimit_check, research_ratelimit_configure, research_ratelimit_status
        mcp.tool()(wrap_tool(research_ratelimit_check))
        mcp.tool()(wrap_tool(research_ratelimit_configure))
        mcp.tool()(wrap_tool(research_ratelimit_status))
    except (ImportError, AttributeError) as e:
        log.debug("skip rate_limiter_tool: %s", e)
    try:
        from loom.tools.realtime_adapt import research_track_refusal, research_get_best_model
        mcp.tool()(wrap_tool(research_track_refusal))
        mcp.tool()(wrap_tool(research_get_best_model))
    except (ImportError, AttributeError) as e:
        log.debug("skip realtime_adapt: %s", e)
    try:
        from loom.tools.redteam_hub import research_hub_share, research_hub_feed, research_hub_vote
        mcp.tool()(wrap_tool(research_hub_share))
        mcp.tool()(wrap_tool(research_hub_feed))
        mcp.tool()(wrap_tool(research_hub_vote))
    except (ImportError, AttributeError) as e:
        log.debug("skip redteam_hub: %s", e)
    try:
        from loom.tools.request_queue import research_queue_add, research_queue_status, research_queue_drain
        mcp.tool()(wrap_tool(research_queue_add))
        mcp.tool()(wrap_tool(research_queue_status))
        mcp.tool()(wrap_tool(research_queue_drain))
    except (ImportError, AttributeError) as e:
        log.debug("skip request_queue: %s", e)
    try:
        from loom.tools.research_journal import research_journal_add, research_journal_search, research_journal_timeline
        mcp.tool()(wrap_tool(research_journal_add))
        mcp.tool()(wrap_tool(research_journal_search))
        mcp.tool()(wrap_tool(research_journal_timeline))
    except (ImportError, AttributeError) as e:
        log.debug("skip research_journal: %s", e)
    try:
        from loom.tools.response_cache import research_cache_store, research_cache_lookup
        mcp.tool()(wrap_tool(research_cache_store))
        mcp.tool()(wrap_tool(research_cache_lookup))
    except (ImportError, AttributeError) as e:
        log.debug("skip response_cache: %s", e)
    try:
        from loom.tools.response_synthesizer import research_synthesize_report
        mcp.tool()(wrap_tool(research_synthesize_report))
    except (ImportError, AttributeError) as e:
        log.debug("skip response_synthesizer: %s", e)
    try:
        from loom.tools.resume_intel import research_optimize_resume, research_interview_prep
        mcp.tool()(wrap_tool(research_optimize_resume))
        mcp.tool()(wrap_tool(research_interview_prep))
    except (ImportError, AttributeError) as e:
        log.debug("skip resume_intel_mod: %s", e)
    try:
        from loom.tools.resumption import research_checkpoint_save, research_checkpoint_resume, research_checkpoint_list
        mcp.tool()(wrap_tool(research_checkpoint_save))
        mcp.tool()(wrap_tool(research_checkpoint_resume))
        mcp.tool()(wrap_tool(research_checkpoint_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip resumption: %s", e)
    try:
        from loom.tools.safety_neurons import research_safety_circuit_map, research_circuit_bypass_plan
        mcp.tool()(wrap_tool(research_safety_circuit_map))
        mcp.tool()(wrap_tool(research_circuit_bypass_plan))
    except (ImportError, AttributeError) as e:
        log.debug("skip safety_neurons: %s", e)
    try:
        from loom.tools.salary_synthesizer import research_salary_synthesize
        mcp.tool()(wrap_tool(research_salary_synthesize))
    except (ImportError, AttributeError) as e:
        log.debug("skip salary_synthesizer: %s", e)
    try:
        from loom.tools.schema_migrate import research_migrate_status, research_migrate_run, research_migrate_backup
        mcp.tool()(wrap_tool(research_migrate_status))
        mcp.tool()(wrap_tool(research_migrate_run))
        mcp.tool()(wrap_tool(research_migrate_backup))
    except (ImportError, AttributeError) as e:
        log.debug("skip schema_migrate: %s", e)
    try:
        from loom.tools.scraper_engine import research_engine_fetch, research_engine_extract, research_engine_batch
        mcp.tool()(wrap_tool(research_engine_fetch))
        mcp.tool()(wrap_tool(research_engine_extract))
        mcp.tool()(wrap_tool(research_engine_batch))
    except (ImportError, AttributeError) as e:
        log.debug("skip scraper_engine_tools: %s", e)
    try:
        from loom.tools.screenshot import research_screenshot
        mcp.tool()(wrap_tool(research_screenshot))
    except (ImportError, AttributeError) as e:
        log.debug("skip screenshot_mod: %s", e)
    try:
        from loom.tools.sentiment_deep import research_sentiment_deep
        mcp.tool()(wrap_tool(research_sentiment_deep))
    except (ImportError, AttributeError) as e:
        log.debug("skip sentiment_deep_mod: %s", e)
    try:
        from loom.tools.sherlock_backend import research_sherlock_lookup, research_sherlock_batch
        mcp.tool()(wrap_tool(research_sherlock_lookup))
        mcp.tool()(wrap_tool(research_sherlock_batch))
    except (ImportError, AttributeError) as e:
        log.debug("skip sherlock_backend: %s", e)
    try:
        from loom.tools.silk_guardian import research_silk_guardian_monitor
        mcp.tool()(wrap_tool(research_silk_guardian_monitor))
    except (ImportError, AttributeError) as e:
        log.debug("skip silk_guardian: %s", e)
    try:
        from loom.tools.social_intel import research_social_search, research_social_profile
        mcp.tool()(wrap_tool(research_social_search))
        mcp.tool()(wrap_tool(research_social_profile))
    except (ImportError, AttributeError) as e:
        log.debug("skip social_intel: %s", e)
    try:
        from loom.tools.social_scraper import research_instagram, research_article_extract, research_article_batch
        mcp.tool()(wrap_tool(research_instagram))
        mcp.tool()(wrap_tool(research_article_extract))
        mcp.tool()(wrap_tool(research_article_batch))
    except (ImportError, AttributeError) as e:
        log.debug("skip social_scraper: %s", e)
    try:
        from loom.tools.stagehand_backend import research_stagehand_act, research_stagehand_extract
        mcp.tool()(wrap_tool(research_stagehand_act))
        mcp.tool()(wrap_tool(research_stagehand_extract))
    except (ImportError, AttributeError) as e:
        log.debug("skip stagehand_backend: %s", e)
    try:
        from loom.tools.stego_detect import research_stego_detect
        mcp.tool()(wrap_tool(research_stego_detect))
    except (ImportError, AttributeError) as e:
        log.debug("skip stego_detect: %s", e)
    try:
        from loom.tools.stego_encoder import research_stego_encode, research_stego_analyze
        mcp.tool()(wrap_tool(research_stego_encode))
        mcp.tool()(wrap_tool(research_stego_analyze))
    except (ImportError, AttributeError) as e:
        log.debug("skip stego_encoder: %s", e)
    try:
        from loom.tools.strategy_ab_test import research_ab_test_design, research_ab_test_analyze
        mcp.tool()(wrap_tool(research_ab_test_design))
        mcp.tool()(wrap_tool(research_ab_test_analyze))
    except (ImportError, AttributeError) as e:
        log.debug("skip strategy_ab_test: %s", e)
    try:
        from loom.tools.strategy_cache import research_cached_strategy
        mcp.tool()(wrap_tool(research_cached_strategy))
    except (ImportError, AttributeError) as e:
        log.debug("skip strategy_cache: %s", e)
    try:
        from loom.tools.strategy_evolution import research_evolve_strategies
        mcp.tool()(wrap_tool(research_evolve_strategies))
    except (ImportError, AttributeError) as e:
        log.debug("skip strategy_evolution: %s", e)
    try:
        from loom.tools.strategy_feedback import research_strategy_log, research_strategy_recommend, research_strategy_stats
        mcp.tool()(wrap_tool(research_strategy_log))
        mcp.tool()(wrap_tool(research_strategy_recommend))
        mcp.tool()(wrap_tool(research_strategy_stats))
    except (ImportError, AttributeError) as e:
        log.debug("skip strategy_feedback: %s", e)
    try:
        from loom.tools.stylometry import research_stylometry
        mcp.tool()(wrap_tool(research_stylometry))
    except (ImportError, AttributeError) as e:
        log.debug("skip stylometry: %s", e)
    try:
        from loom.tools.superposition_prompt import research_superposition_attack
        mcp.tool()(wrap_tool(research_superposition_attack))
    except (ImportError, AttributeError) as e:
        log.debug("skip superposition_prompt: %s", e)
    try:
        from loom.tools.synth_echo import research_synth_echo
        mcp.tool()(wrap_tool(research_synth_echo))
    except (ImportError, AttributeError) as e:
        log.debug("skip synth_echo: %s", e)
    try:
        from loom.tools.synthetic_data import research_generate_redteam_dataset, research_augment_dataset
        mcp.tool()(wrap_tool(research_generate_redteam_dataset))
        mcp.tool()(wrap_tool(research_augment_dataset))
    except (ImportError, AttributeError) as e:
        log.debug("skip synthetic_data: %s", e)
    try:
        from loom.tools.task_resolver import research_resolve_order, research_critical_path
        mcp.tool()(wrap_tool(research_resolve_order))
        mcp.tool()(wrap_tool(research_critical_path))
    except (ImportError, AttributeError) as e:
        log.debug("skip task_resolver: %s", e)
    try:
        from loom.tools.tenant_isolation import research_tenant_create, research_tenant_list, research_tenant_usage
        mcp.tool()(wrap_tool(research_tenant_create))
        mcp.tool()(wrap_tool(research_tenant_list))
        mcp.tool()(wrap_tool(research_tenant_usage))
    except (ImportError, AttributeError) as e:
        log.debug("skip tenant_isolation: %s", e)
    try:
        from loom.tools.text_analyze import research_text_analyze
        mcp.tool()(wrap_tool(research_text_analyze))
    except (ImportError, AttributeError) as e:
        log.debug("skip text_analyze_mod: %s", e)
    try:
        from loom.tools.tool_catalog import research_tool_catalog, research_tool_graph, research_tool_pipeline, research_tool_standalone
        mcp.tool()(wrap_tool(research_tool_catalog))
        mcp.tool()(wrap_tool(research_tool_graph))
        mcp.tool()(wrap_tool(research_tool_pipeline))
        mcp.tool()(wrap_tool(research_tool_standalone))
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_catalog: %s", e)
    try:
        from loom.tools.tool_profiler import research_profile_tool, research_profile_hotspots
        mcp.tool()(wrap_tool(research_profile_tool))
        mcp.tool()(wrap_tool(research_profile_hotspots))
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_profiler: %s", e)
    try:
        from loom.tools.tool_tags import research_tag_tool, research_tag_search, research_tag_cloud
        mcp.tool()(wrap_tool(research_tag_tool))
        mcp.tool()(wrap_tool(research_tag_search))
        mcp.tool()(wrap_tool(research_tag_cloud))
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_tags: %s", e)
    try:
        from loom.tools.tool_versioning import research_tool_version, research_version_diff, research_version_snapshot
        mcp.tool()(wrap_tool(research_tool_version))
        mcp.tool()(wrap_tool(research_version_diff))
        mcp.tool()(wrap_tool(research_version_snapshot))
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_versioning: %s", e)
    try:
        from loom.tools.traffic_capture import research_capture_har, research_extract_cookies
        mcp.tool()(wrap_tool(research_capture_har))
        mcp.tool()(wrap_tool(research_extract_cookies))
    except (ImportError, AttributeError) as e:
        log.debug("skip traffic_capture: %s", e)
    try:
        from loom.tools.transcribe import research_transcribe
        mcp.tool()(wrap_tool(research_transcribe))
    except (ImportError, AttributeError) as e:
        log.debug("skip transcribe_mod: %s", e)
    try:
        from loom.tools.unique import research_propaganda_detector, research_source_credibility, research_information_cascade, research_web_time_machine, research_influence_operation, research_dark_web_bridge, research_info_half_life, research_search_discrepancy
        mcp.tool()(wrap_tool(research_propaganda_detector))
        mcp.tool()(wrap_tool(research_source_credibility))
        mcp.tool()(wrap_tool(research_information_cascade))
        mcp.tool()(wrap_tool(research_web_time_machine))
        mcp.tool()(wrap_tool(research_influence_operation))
        mcp.tool()(wrap_tool(research_dark_web_bridge))
        mcp.tool()(wrap_tool(research_info_half_life))
        mcp.tool()(wrap_tool(research_search_discrepancy))
    except (ImportError, AttributeError) as e:
        log.debug("skip unique_tools: %s", e)
    try:
        from loom.tools.usage_analytics import research_usage_record, research_usage_report, research_usage_trends
        mcp.tool()(wrap_tool(research_usage_record))
        mcp.tool()(wrap_tool(research_usage_report))
        mcp.tool()(wrap_tool(research_usage_trends))
    except (ImportError, AttributeError) as e:
        log.debug("skip usage_analytics: %s", e)
    try:
        from loom.tools.vision_agent import research_vision_browse, research_vision_compare
        mcp.tool()(wrap_tool(research_vision_browse))
        mcp.tool()(wrap_tool(research_vision_compare))
    except (ImportError, AttributeError) as e:
        log.debug("skip vision_agent: %s", e)
    try:
        from loom.tools.webhook_system import research_webhook_register, research_webhook_fire, research_webhook_list
        mcp.tool()(wrap_tool(research_webhook_register))
        mcp.tool()(wrap_tool(research_webhook_fire))
        mcp.tool()(wrap_tool(research_webhook_list))
    except (ImportError, AttributeError) as e:
        log.debug("skip webhook_system: %s", e)
    try:
        from loom.tools.white_rabbit import research_white_rabbit
        mcp.tool()(wrap_tool(research_white_rabbit))
    except (ImportError, AttributeError) as e:
        log.debug("skip white_rabbit: %s", e)
    try:
        from loom.tools.xover_attack import research_xover_transfer, research_xover_matrix
        mcp.tool()(wrap_tool(research_xover_transfer))
        mcp.tool()(wrap_tool(research_xover_matrix))
    except (ImportError, AttributeError) as e:
        log.debug("skip xover_attack: %s", e)
    try:
        from loom.tools.yt import fetch_youtube_transcript
        mcp.tool()(wrap_tool(fetch_youtube_transcript))
    except (ImportError, AttributeError) as e:
        log.debug("skip yt_mod: %s", e)
    try:
        from loom.tools.ytdlp import research_video_download, research_video_info, research_audio_extract
        mcp.tool()(wrap_tool(research_video_download))
        mcp.tool()(wrap_tool(research_video_info))
        mcp.tool()(wrap_tool(research_audio_extract))
    except (ImportError, AttributeError) as e:
        log.debug("skip ytdlp_mod: %s", e)
    try:
        from loom.tools.zendriver_backend import research_zen_fetch, research_zen_batch, research_zen_interact
        mcp.tool()(wrap_tool(research_zen_fetch))
        mcp.tool()(wrap_tool(research_zen_batch))
        mcp.tool()(wrap_tool(research_zen_interact))
    except (ImportError, AttributeError) as e:
        log.debug("skip zendriver_backend: %s", e)
    log.info("registered research tools count=369")
