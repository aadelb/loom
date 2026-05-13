# AUTO-GENERATED: Register all missing tools
def register_missing_tools(mcp, wrap_tool):
    import logging
    log = logging.getLogger('loom.registrations.auto')
    count = 0
    try:
        from loom.tools.llm.strategy_ab_test import research_ab_test_analyze
        mcp.tool()(wrap_tool(research_ab_test_analyze))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.strategy_ab_test import research_ab_test_design
        mcp.tool()(wrap_tool(research_ab_test_design))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.eu_ai_act import research_ai_bias_audit
        mcp.tool()(wrap_tool(research_ai_bias_audit))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.eu_ai_act import research_ai_data_governance
        mcp.tool()(wrap_tool(research_ai_data_governance))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.eu_ai_act import research_ai_risk_classify
        mcp.tool()(wrap_tool(research_ai_risk_classify))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.eu_ai_act import research_ai_robustness_test
        mcp.tool()(wrap_tool(research_ai_robustness_test))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.eu_ai_act import research_ai_transparency_check
        mcp.tool()(wrap_tool(research_ai_transparency_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.metric_alerts import research_alert_check
        mcp.tool()(wrap_tool(research_alert_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.metric_alerts import research_alert_create
        mcp.tool()(wrap_tool(research_alert_create))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.metric_alerts import research_alert_list
        mcp.tool()(wrap_tool(research_alert_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.api_version import research_api_changelog
        mcp.tool()(wrap_tool(research_api_changelog))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.api_version import research_api_deprecations
        mcp.tool()(wrap_tool(research_api_deprecations))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.api_version import research_api_version
        mcp.tool()(wrap_tool(research_api_version))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.social_scraper import research_article_batch
        mcp.tool()(wrap_tool(research_article_batch))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.social_scraper import research_article_extract
        mcp.tool()(wrap_tool(research_article_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_tools import research_artifact_cleanup
        mcp.tool()(wrap_tool(research_artifact_cleanup))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.arxiv_pipeline import research_arxiv_extract_techniques
        mcp.tool()(wrap_tool(research_arxiv_extract_techniques))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.arxiv_pipeline import research_arxiv_ingest
        mcp.tool()(wrap_tool(research_arxiv_ingest))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.nightcrawler import research_arxiv_scan
        mcp.tool()(wrap_tool(research_arxiv_scan))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.ensemble_attack import research_attack_portfolio
        mcp.tool()(wrap_tool(research_attack_portfolio))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.audit_log import research_audit_export
        mcp.tool()(wrap_tool(research_audit_export))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.audit_log import research_audit_log_query
        mcp.tool()(wrap_tool(research_audit_log_query))
        count += 1
    except Exception:
        pass
        from loom.tools.research.synthetic_data import research_augment_dataset
        mcp.tool()(wrap_tool(research_augment_dataset))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_academic import research_author_clustering
        mcp.tool()(wrap_tool(research_author_clustering))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.auto_pipeline import research_auto_pipeline
        mcp.tool()(wrap_tool(research_auto_pipeline))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.autonomous_agent import research_auto_redteam
        mcp.tool()(wrap_tool(research_auto_redteam))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.auto_report import research_auto_report
        mcp.tool()(wrap_tool(research_auto_report))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.backoff_dlq import research_backoff_dlq_list
        mcp.tool()(wrap_tool(research_backoff_dlq_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.fact_verifier import research_batch_verify
        mcp.tool()(wrap_tool(research_batch_verify))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.osint_extended import research_behavioral_fingerprint
        mcp.tool()(wrap_tool(research_behavioral_fingerprint))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.benchmark_suite import research_benchmark_compare
        mcp.tool()(wrap_tool(research_benchmark_compare))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.benchmark_leaderboard import research_benchmark_models
        mcp.tool()(wrap_tool(research_benchmark_models))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.bias_lens import research_bias_lens
        mcp.tool()(wrap_tool(research_bias_lens))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.infowar_tools import research_bot_detector
        mcp.tool()(wrap_tool(research_bot_detector))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.circuit_breaker import research_breaker_reset
        mcp.tool()(wrap_tool(research_breaker_reset))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.circuit_breaker import research_breaker_status
        mcp.tool()(wrap_tool(research_breaker_status))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.circuit_breaker import research_breaker_trip
        mcp.tool()(wrap_tool(research_breaker_trip))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_browser_fingerprint_audit
        mcp.tool()(wrap_tool(research_browser_fingerprint_audit))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.response_cache import research_cache_lookup
        mcp.tool()(wrap_tool(research_cache_lookup))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.response_cache import research_cache_store
        mcp.tool()(wrap_tool(research_cache_store))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.strategy_cache import research_cached_strategy
        mcp.tool()(wrap_tool(research_cached_strategy))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_ai import research_capability_mapper
        mcp.tool()(wrap_tool(research_capability_mapper))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.traffic_capture import research_capture_har
        mcp.tool()(wrap_tool(research_capture_har))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.infowar_tools import research_censorship_detector
        mcp.tool()(wrap_tool(research_censorship_detector))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.chain_composer import research_chain_define
        mcp.tool()(wrap_tool(research_chain_define))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.chain_composer import research_chain_describe
        mcp.tool()(wrap_tool(research_chain_describe))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.chain_composer import research_chain_list
        mcp.tool()(wrap_tool(research_chain_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.gamification import research_challenge_create
        mcp.tool()(wrap_tool(research_challenge_create))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.gamification import research_challenge_list
        mcp.tool()(wrap_tool(research_challenge_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.changelog_gen import research_changelog_generate
        mcp.tool()(wrap_tool(research_changelog_generate))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.changelog_gen import research_changelog_stats
        mcp.tool()(wrap_tool(research_changelog_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.resumption import research_checkpoint_list
        mcp.tool()(wrap_tool(research_checkpoint_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.resumption import research_checkpoint_resume
        mcp.tool()(wrap_tool(research_checkpoint_resume))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.resumption import research_checkpoint_save
        mcp.tool()(wrap_tool(research_checkpoint_save))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.chronos import research_chronos_reverse
        mcp.tool()(wrap_tool(research_chronos_reverse))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.safety_neurons import research_circuit_bypass_plan
        mcp.tool()(wrap_tool(research_circuit_bypass_plan))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_academic import research_citation_cartography
        mcp.tool()(wrap_tool(research_citation_cartography))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_infra import research_cloud_enum
        mcp.tool()(wrap_tool(research_cloud_enum))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.multilang_attack import research_code_switch_attack
        mcp.tool()(wrap_tool(research_code_switch_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.compliance_checker import research_compliance_check
        mcp.tool()(wrap_tool(research_compliance_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_conference_arbitrage
        mcp.tool()(wrap_tool(research_conference_arbitrage))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.context_manager import research_context_clear
        mcp.tool()(wrap_tool(research_context_clear))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.context_manager import research_context_get
        mcp.tool()(wrap_tool(research_context_get))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.context_manager import research_context_set
        mcp.tool()(wrap_tool(research_context_set))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.task_resolver import research_critical_path
        mcp.tool()(wrap_tool(research_critical_path))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.crypto_risk import research_crypto_risk_score
        mcp.tool()(wrap_tool(research_crypto_risk_score))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.cultural_attacks import research_cultural_reframe
        mcp.tool()(wrap_tool(research_cultural_reframe))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.culture_dna import research_culture_dna
        mcp.tool()(wrap_tool(research_culture_dna))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.cyberscraper_backend import research_cyberscrape
        mcp.tool()(wrap_tool(research_cyberscrape))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.cyberscraper_backend import research_cyberscrape_direct
        mcp.tool()(wrap_tool(research_cyberscrape_direct))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_dark_web_bridge
        mcp.tool()(wrap_tool(research_dark_web_bridge))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.health_dashboard import research_dashboard_html
        mcp.tool()(wrap_tool(research_dashboard_html))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_data_fabrication
        mcp.tool()(wrap_tool(research_data_fabrication))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.p3_tools import research_data_poisoning
        mcp.tool()(wrap_tool(research_data_poisoning))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.deception_detect import research_deception_detect
        mcp.tool()(wrap_tool(research_deception_detect))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.deception_job_scanner import research_deception_job_scan
        mcp.tool()(wrap_tool(research_deception_job_scan))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.infowar_tools import research_deleted_social
        mcp.tool()(wrap_tool(research_deleted_social))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.dependency_graph import research_dependency_graph
        mcp.tool()(wrap_tool(research_dependency_graph))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_dependencies import research_dependency_graph_stats
        mcp.tool()(wrap_tool(research_dependency_graph_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.output_diff import research_diff_compare
        mcp.tool()(wrap_tool(research_diff_compare))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.output_diff import research_diff_track
        mcp.tool()(wrap_tool(research_diff_track))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.dlq_management import research_dlq_list
        mcp.tool()(wrap_tool(research_dlq_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.backoff_dlq import research_dlq_push
        mcp.tool()(wrap_tool(research_dlq_push))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.backoff_dlq import research_dlq_retry
        mcp.tool()(wrap_tool(research_dlq_retry))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_dns_leak_check
        mcp.tool()(wrap_tool(research_dns_leak_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.auto_docs import research_docs_coverage
        mcp.tool()(wrap_tool(research_docs_coverage))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_elf_obfuscate
        mcp.tool()(wrap_tool(research_elf_obfuscate))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.embedding_collision import research_embedding_collide
        mcp.tool()(wrap_tool(research_embedding_collide))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.scraper_engine_tools import research_engine_batch
        mcp.tool()(wrap_tool(research_engine_batch))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.scraper_engine_tools import research_engine_extract
        mcp.tool()(wrap_tool(research_engine_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.scraper_engine_tools import research_engine_fetch
        mcp.tool()(wrap_tool(research_engine_fetch))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.ensemble_attack import research_ensemble_attack
        mcp.tool()(wrap_tool(research_ensemble_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.strategy_evolution import research_evolve_strategies
        mcp.tool()(wrap_tool(research_evolve_strategies))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.auto_experiment import research_experiment_design
        mcp.tool()(wrap_tool(research_experiment_design))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.explainability import research_explain_bypass
        mcp.tool()(wrap_tool(research_explain_bypass))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.output_formatter import research_extract_actionables
        mcp.tool()(wrap_tool(research_extract_actionables))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.traffic_capture import research_extract_cookies
        mcp.tool()(wrap_tool(research_extract_cookies))
        count += 1
    except Exception:
        pass
        from loom.tools.privacy.privacy_advanced import research_fileless_exec
        mcp.tool()(wrap_tool(research_fileless_exec))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.model_fingerprinter import research_fingerprint_behavior
        mcp.tool()(wrap_tool(research_fingerprint_behavior))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.fingerprint_evasion import research_fingerprint_evasion_test
        mcp.tool()(wrap_tool(research_fingerprint_evasion_test))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_fingerprint_randomize
        mcp.tool()(wrap_tool(research_fingerprint_randomize))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.feature_flags import research_flag_check
        mcp.tool()(wrap_tool(research_flag_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.feature_flags import research_flag_list
        mcp.tool()(wrap_tool(research_flag_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.feature_flags import research_flag_toggle
        mcp.tool()(wrap_tool(research_flag_toggle))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.p3_tools import research_foia_tracker
        mcp.tool()(wrap_tool(research_foia_tracker))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.antiforensics import research_forensics_cleanup
        mcp.tool()(wrap_tool(research_forensics_cleanup))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.output_formatter import research_format_report
        mcp.tool()(wrap_tool(research_format_report))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_advanced import research_funding_pipeline
        mcp.tool()(wrap_tool(research_funding_pipeline))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.job_signals import research_funding_signal
        mcp.tool()(wrap_tool(research_funding_signal))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.auto_docs import research_generate_docs
        mcp.tool()(wrap_tool(research_generate_docs))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.synthetic_data import research_generate_redteam_dataset
        mcp.tool()(wrap_tool(research_generate_redteam_dataset))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.geodesic_forcing import research_geodesic_path
        mcp.tool()(wrap_tool(research_geodesic_path))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.realtime_adapt import research_get_best_model
        mcp.tool()(wrap_tool(research_get_best_model))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_dependencies import research_get_execution_plan
        mcp.tool()(wrap_tool(research_get_execution_plan))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_infra import research_github_secrets
        mcp.tool()(wrap_tool(research_github_secrets))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_grant_forensics
        mcp.tool()(wrap_tool(research_grant_forensics))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.knowledge_graph import research_graph
        mcp.tool()(wrap_tool(research_graph))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.graph_analysis import research_graph_analyze
        mcp.tool()(wrap_tool(research_graph_analyze))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.neo4j_backend import research_graph_query
        mcp.tool()(wrap_tool(research_graph_query))
        count += 1
    except Exception:
        pass
        from loom.tools.backends.neo4j_backend import research_graph_store
        mcp.tool()(wrap_tool(research_graph_store))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.neo4j_backend import research_graph_visualize
        mcp.tool()(wrap_tool(research_graph_visualize))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_batch
        mcp.tool()(wrap_tool(research_hcs_batch))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_compare
        mcp.tool()(wrap_tool(research_hcs_compare))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_escalation import research_hcs_escalate
        mcp.tool()(wrap_tool(research_hcs_escalate))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_report import research_hcs_report
        mcp.tool()(wrap_tool(research_hcs_report))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_rubric
        mcp.tool()(wrap_tool(research_hcs_rubric))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_score_full
        mcp.tool()(wrap_tool(research_hcs_score_full))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_score_prompt
        mcp.tool()(wrap_tool(research_hcs_score_prompt))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_score_response
        mcp.tool()(wrap_tool(research_hcs_score_response))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.health_deep import research_health_deep
        mcp.tool()(wrap_tool(research_health_deep))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.deep_research_agent import research_hierarchical_research
        mcp.tool()(wrap_tool(research_hierarchical_research))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.hitl_eval import research_hitl_evaluate
        mcp.tool()(wrap_tool(research_hitl_evaluate))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.hitl_eval import research_hitl_queue
        mcp.tool()(wrap_tool(research_hitl_queue))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.hitl_eval import research_hitl_submit
        mcp.tool()(wrap_tool(research_hitl_submit))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.holographic_payload import research_holographic_encode
        mcp.tool()(wrap_tool(research_holographic_encode))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.projectdiscovery import research_httpx_probe
        mcp.tool()(wrap_tool(research_httpx_probe))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.redteam_hub import research_hub_feed
        mcp.tool()(wrap_tool(research_hub_feed))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.redteam_hub import research_hub_share
        mcp.tool()(wrap_tool(research_hub_share))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.redteam_hub import research_hub_vote
        mcp.tool()(wrap_tool(research_hub_vote))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_academic import research_ideological_drift
        mcp.tool()(wrap_tool(research_ideological_drift))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_tools import research_image_stego
        mcp.tool()(wrap_tool(research_image_stego))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_influence_operation
        mcp.tool()(wrap_tool(research_influence_operation))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_info_half_life
        mcp.tool()(wrap_tool(research_info_half_life))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_information_cascade
        mcp.tool()(wrap_tool(research_information_cascade))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.social_scraper import research_instagram
        mcp.tool()(wrap_tool(research_instagram))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_institutional_decay
        mcp.tool()(wrap_tool(research_institutional_decay))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.integration_runner import research_integration_test
        mcp.tool()(wrap_tool(research_integration_test))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_tools import research_interactive_privacy_audit
        mcp.tool()(wrap_tool(research_interactive_privacy_audit))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.job_signals import research_interviewer_profiler
        mcp.tool()(wrap_tool(research_interviewer_profiler))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_advanced import research_jailbreak_library
        mcp.tool()(wrap_tool(research_jailbreak_library))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.research_journal import research_journal_add
        mcp.tool()(wrap_tool(research_journal_add))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.research_journal import research_journal_search
        mcp.tool()(wrap_tool(research_journal_search))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.research_journal import research_journal_timeline
        mcp.tool()(wrap_tool(research_journal_timeline))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.js_intel import research_js_intel
        mcp.tool()(wrap_tool(research_js_intel))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.projectdiscovery import research_katana_crawl
        mcp.tool()(wrap_tool(research_katana_crawl))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.knowledge_base import research_kb_search
        mcp.tool()(wrap_tool(research_kb_search))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.knowledge_base import research_kb_stats
        mcp.tool()(wrap_tool(research_kb_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.knowledge_base import research_kb_store
        mcp.tool()(wrap_tool(research_kb_store))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.graph_scraper import research_knowledge_extract
        mcp.tool()(wrap_tool(research_knowledge_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.gamification import research_leaderboard
        mcp.tool()(wrap_tool(research_leaderboard))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.benchmark_leaderboard import research_leaderboard_update
        mcp.tool()(wrap_tool(research_leaderboard_update))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.benchmark_leaderboard import research_leaderboard_view
        mcp.tool()(wrap_tool(research_leaderboard_view))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.lifetime_oracle import research_lifetime_predict
        mcp.tool()(wrap_tool(research_lifetime_predict))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.json_logger import research_log_query
        mcp.tool()(wrap_tool(research_log_query))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.json_logger import research_log_stats
        mcp.tool()(wrap_tool(research_log_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_mac_randomize
        mcp.tool()(wrap_tool(research_mac_randomize))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_tools import research_macos_hardening
        mcp.tool()(wrap_tool(research_macos_hardening))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.marketplace import research_marketplace_download
        mcp.tool()(wrap_tool(research_marketplace_download))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.marketplace import research_marketplace_list
        mcp.tool()(wrap_tool(research_marketplace_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.marketplace import research_marketplace_publish
        mcp.tool()(wrap_tool(research_marketplace_publish))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_ai import research_memorization_scanner
        mcp.tool()(wrap_tool(research_memorization_scanner))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.persistent_memory import research_memory_stats
        mcp.tool()(wrap_tool(research_memory_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.meta_learner import research_meta_learn
        mcp.tool()(wrap_tool(research_meta_learn))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.schema_migrate import research_migrate_backup
        mcp.tool()(wrap_tool(research_migrate_backup))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.schema_migrate import research_migrate_run
        mcp.tool()(wrap_tool(research_migrate_run))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.schema_migrate import research_migrate_status
        mcp.tool()(wrap_tool(research_migrate_status))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.p3_tools import research_model_comparator
        mcp.tool()(wrap_tool(research_model_comparator))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_monoculture_detect
        mcp.tool()(wrap_tool(research_monoculture_detect))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.graph_scraper import research_multi_page_graph
        mcp.tool()(wrap_tool(research_multi_page_graph))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_multi_stego
        mcp.tool()(wrap_tool(research_multi_stego))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.cultural_attacks import research_multilingual_attack
        mcp.tool()(wrap_tool(research_multilingual_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.infowar_tools import research_narrative_tracker
        mcp.tool()(wrap_tool(research_narrative_tracker))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.network_map import research_network_map
        mcp.tool()(wrap_tool(research_network_map))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.network_map import research_network_visualize
        mcp.tool()(wrap_tool(research_network_visualize))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.nightcrawler import research_nightcrawler_status
        mcp.tool()(wrap_tool(research_nightcrawler_status))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.notifications import research_notify_history
        mcp.tool()(wrap_tool(research_notify_history))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.notifications import research_notify_rules
        mcp.tool()(wrap_tool(research_notify_rules))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.notifications import research_notify_send
        mcp.tool()(wrap_tool(research_notify_send))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.projectdiscovery import research_nuclei_scan
        mcp.tool()(wrap_tool(research_nuclei_scan))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_infra import research_output_consistency
        mcp.tool()(wrap_tool(research_output_consistency))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.cyberscraper import research_paginate_scrape
        mcp.tool()(wrap_tool(research_paginate_scrape))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_advanced import research_patent_embargo
        mcp.tool()(wrap_tool(research_patent_embargo))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.pdf_extract import research_pdf_extract
        mcp.tool()(wrap_tool(research_pdf_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.pdf_extract import research_pdf_search
        mcp.tool()(wrap_tool(research_pdf_search))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.pentest_prompts import research_pentest_prompt
        mcp.tool()(wrap_tool(research_pentest_prompt))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_tools import research_pii_recon
        mcp.tool()(wrap_tool(research_pii_recon))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.compliance_checker import research_pii_scan
        mcp.tool()(wrap_tool(research_pii_scan))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.data_pipeline import research_pipeline_create
        mcp.tool()(wrap_tool(research_pipeline_create))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.data_pipeline import research_pipeline_list
        mcp.tool()(wrap_tool(research_pipeline_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.data_pipeline import research_pipeline_validate
        mcp.tool()(wrap_tool(research_pipeline_validate))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.plugin_loader import research_plugin_list
        mcp.tool()(wrap_tool(research_plugin_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.plugin_loader import research_plugin_load
        mcp.tool()(wrap_tool(research_plugin_load))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.plugin_loader import research_plugin_unload
        mcp.tool()(wrap_tool(research_plugin_unload))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.proactive_defense import research_predict_attacks
        mcp.tool()(wrap_tool(research_predict_attacks))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.predictive_ranker import research_predict_success
        mcp.tool()(wrap_tool(research_predict_success))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.proactive_defense import research_preemptive_patch
        mcp.tool()(wrap_tool(research_preemptive_patch))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_preprint_manipulation
        mcp.tool()(wrap_tool(research_preprint_manipulation))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_privacy_score
        mcp.tool()(wrap_tool(research_privacy_score))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_profiler import research_profile_hotspots
        mcp.tool()(wrap_tool(research_profile_hotspots))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_profiler import research_profile_tool
        mcp.tool()(wrap_tool(research_profile_tool))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_propaganda_detector
        mcp.tool()(wrap_tool(research_propaganda_detector))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.provider_health import research_provider_history
        mcp.tool()(wrap_tool(research_provider_history))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.provider_health import research_provider_ping
        mcp.tool()(wrap_tool(research_provider_ping))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.provider_health import research_provider_recommend
        mcp.tool()(wrap_tool(research_provider_recommend))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.request_queue import research_queue_add
        mcp.tool()(wrap_tool(research_queue_add))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.request_queue import research_queue_drain
        mcp.tool()(wrap_tool(research_queue_drain))
        count += 1
    except Exception:
        pass
        from loom.tools.llm.embedding_collision import research_rag_attack
        mcp.tool()(wrap_tool(research_rag_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.rag_anything import research_rag_clear
        mcp.tool()(wrap_tool(research_rag_clear))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.rag_anything import research_rag_ingest
        mcp.tool()(wrap_tool(research_rag_ingest))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.rag_anything import research_rag_query
        mcp.tool()(wrap_tool(research_rag_query))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.rate_limiter_tool import research_ratelimit_check
        mcp.tool()(wrap_tool(research_ratelimit_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.rate_limiter_tool import research_ratelimit_configure
        mcp.tool()(wrap_tool(research_ratelimit_configure))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.monitoring.rate_limiter_tool import research_ratelimit_status
        mcp.tool()(wrap_tool(research_ratelimit_status))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.persistent_memory import research_recall
        mcp.tool()(wrap_tool(research_recall))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.live_registry import research_registry_refresh
        mcp.tool()(wrap_tool(research_registry_refresh))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.live_registry import research_registry_search
        mcp.tool()(wrap_tool(research_registry_search))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.live_registry import research_registry_status
        mcp.tool()(wrap_tool(research_registry_status))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.reid_tactics import research_reid_tactics
        mcp.tool()(wrap_tool(research_reid_tactics))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.persistent_memory import research_remember
        mcp.tool()(wrap_tool(research_remember))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.auto_report import research_report_from_results
        mcp.tool()(wrap_tool(research_report_from_results))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.task_resolver import research_resolve_order
        mcp.tool()(wrap_tool(research_resolve_order))
        count += 1
    except Exception:
        pass
        from loom.tools.infrastructure.retry_middleware import research_retry_middleware_stats
        mcp.tool()(wrap_tool(research_retry_middleware_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_review_cartel
        mcp.tool()(wrap_tool(research_review_cartel))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.infowar_tools import research_robots_archaeology
        mcp.tool()(wrap_tool(research_robots_archaeology))
        count += 1
    except Exception:
        pass
        from loom.tools.research.auto_experiment import research_run_experiment
        mcp.tool()(wrap_tool(research_run_experiment))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.safety_neurons import research_safety_circuit_map
        mcp.tool()(wrap_tool(research_safety_circuit_map))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.salary_synthesizer import research_salary_synthesize
        mcp.tool()(wrap_tool(research_salary_synthesize))
        count += 1
    except Exception:
        pass
        from loom.tools.security.sandbox import research_sandbox_monitor
        mcp.tool()(wrap_tool(research_sandbox_monitor))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.input_sanitizer import research_sanitize_input
        mcp.tool()(wrap_tool(research_sanitize_input))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.research_scheduler import research_schedule_check
        mcp.tool()(wrap_tool(research_schedule_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.research_scheduler import research_schedule_create
        mcp.tool()(wrap_tool(research_schedule_create))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.research_scheduler import research_schedule_list
        mcp.tool()(wrap_tool(research_schedule_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.autonomous_agent import research_schedule_redteam
        mcp.tool()(wrap_tool(research_schedule_redteam))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.multilang_attack import research_script_confusion
        mcp.tool()(wrap_tool(research_script_confusion))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_search_discrepancy
        mcp.tool()(wrap_tool(research_search_discrepancy))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_secure_delete
        mcp.tool()(wrap_tool(research_secure_delete))
        count += 1
    except Exception:
        pass
        from loom.tools.adversarial.hcs10_academic import research_shell_funding
        mcp.tool()(wrap_tool(research_shell_funding))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.sherlock_backend import research_sherlock_batch
        mcp.tool()(wrap_tool(research_sherlock_batch))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.sherlock_backend import research_sherlock_lookup
        mcp.tool()(wrap_tool(research_sherlock_lookup))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.silk_guardian import research_silk_guardian_monitor
        mcp.tool()(wrap_tool(research_silk_guardian_monitor))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.cyberscraper import research_smart_extract
        mcp.tool()(wrap_tool(research_smart_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.integration_runner import research_smoke_test
        mcp.tool()(wrap_tool(research_smoke_test))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.osint_extended import research_social_engineering_score
        mcp.tool()(wrap_tool(research_social_engineering_score))
        count += 1
    except Exception:
        pass
        from loom.tools.intelligence.social_intel import research_social_profile
        mcp.tool()(wrap_tool(research_social_profile))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.social_intel import research_social_search
        mcp.tool()(wrap_tool(research_social_search))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_source_credibility
        mcp.tool()(wrap_tool(research_source_credibility))
        count += 1
    except Exception:
        pass
        from loom.tools.security.enterprise_sso import research_sso_configure
        mcp.tool()(wrap_tool(research_sso_configure))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.enterprise_sso import research_sso_user_info
        mcp.tool()(wrap_tool(research_sso_user_info))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.enterprise_sso import research_sso_validate_token
        mcp.tool()(wrap_tool(research_sso_validate_token))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.stagehand_backend import research_stagehand_act
        mcp.tool()(wrap_tool(research_stagehand_act))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.stagehand_backend import research_stagehand_extract
        mcp.tool()(wrap_tool(research_stagehand_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.cyberscraper import research_stealth_browser
        mcp.tool()(wrap_tool(research_stealth_browser))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.job_signals import research_stealth_hire_scanner
        mcp.tool()(wrap_tool(research_stealth_hire_scanner))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.stego_encoder import research_stego_analyze
        mcp.tool()(wrap_tool(research_stego_analyze))
        count += 1
    except Exception:
        pass
        from loom.tools.privacy.stego_encoder import research_stego_encode
        mcp.tool()(wrap_tool(research_stego_encode))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_tools import research_stego_encode_zw
        mcp.tool()(wrap_tool(research_stego_encode_zw))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.strategy_feedback import research_strategy_log
        mcp.tool()(wrap_tool(research_strategy_log))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.strategy_feedback import research_strategy_recommend
        mcp.tool()(wrap_tool(research_strategy_recommend))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.strategy_feedback import research_strategy_stats
        mcp.tool()(wrap_tool(research_strategy_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.stylometry import research_stylometry
        mcp.tool()(wrap_tool(research_stylometry))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.projectdiscovery import research_subfinder
        mcp.tool()(wrap_tool(research_subfinder))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.superposition_prompt import research_superposition_attack
        mcp.tool()(wrap_tool(research_superposition_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.synth_echo import research_synth_echo
        mcp.tool()(wrap_tool(research_synth_echo))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.response_synthesizer import research_synthesize_report
        mcp.tool()(wrap_tool(research_synthesize_report))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_tags import research_tag_cloud
        mcp.tool()(wrap_tool(research_tag_cloud))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_tags import research_tag_search
        mcp.tool()(wrap_tool(research_tag_search))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_tags import research_tag_tool
        mcp.tool()(wrap_tool(research_tag_tool))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_advanced import research_talent_migration
        mcp.tool()(wrap_tool(research_talent_migration))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.tenant_isolation import research_tenant_create
        mcp.tool()(wrap_tool(research_tenant_create))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.tenant_isolation import research_tenant_list
        mcp.tool()(wrap_tool(research_tenant_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.tenant_isolation import research_tenant_usage
        mcp.tool()(wrap_tool(research_tenant_usage))
        count += 1
    except Exception:
        pass
        from loom.tools.adversarial.multilang_attack import research_token_split_attack
        mcp.tool()(wrap_tool(research_token_split_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_catalog import research_tool_catalog
        mcp.tool()(wrap_tool(research_tool_catalog))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_dependencies import research_tool_dependencies
        mcp.tool()(wrap_tool(research_tool_dependencies))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_catalog import research_tool_graph
        mcp.tool()(wrap_tool(research_tool_graph))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.dependency_graph import research_tool_impact
        mcp.tool()(wrap_tool(research_tool_impact))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_catalog import research_tool_pipeline
        mcp.tool()(wrap_tool(research_tool_pipeline))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_catalog import research_tool_standalone
        mcp.tool()(wrap_tool(research_tool_standalone))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.usage_analytics import research_tool_usage_report
        mcp.tool()(wrap_tool(research_tool_usage_report))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_versioning import research_tool_version
        mcp.tool()(wrap_tool(research_tool_version))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_tor_circuit_info
        mcp.tool()(wrap_tool(research_tor_circuit_info))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.realtime_adapt import research_track_refusal
        mcp.tool()(wrap_tool(research_track_refusal))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_ai import research_training_contamination
        mcp.tool()(wrap_tool(research_training_contamination))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.graph_analysis import research_transaction_graph
        mcp.tool()(wrap_tool(research_transaction_graph))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.usage_analytics import research_usage_record
        mcp.tool()(wrap_tool(research_usage_record))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.usage_analytics import research_usage_trends
        mcp.tool()(wrap_tool(research_usage_trends))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.antiforensics import research_usb_kill_monitor
        mcp.tool()(wrap_tool(research_usb_kill_monitor))
        count += 1
    except Exception:
        pass
        from loom.tools.security.input_sanitizer import research_validate_params
        mcp.tool()(wrap_tool(research_validate_params))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.credential_vault import research_vault_list
        mcp.tool()(wrap_tool(research_vault_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.credential_vault import research_vault_retrieve
        mcp.tool()(wrap_tool(research_vault_retrieve))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.credential_vault import research_vault_store
        mcp.tool()(wrap_tool(research_vault_store))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_versioning import research_version_diff
        mcp.tool()(wrap_tool(research_version_diff))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.tool_versioning import research_version_snapshot
        mcp.tool()(wrap_tool(research_version_snapshot))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.vision_agent import research_vision_browse
        mcp.tool()(wrap_tool(research_vision_browse))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.vision_agent import research_vision_compare
        mcp.tool()(wrap_tool(research_vision_compare))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.explainability import research_vulnerability_map
        mcp.tool()(wrap_tool(research_vulnerability_map))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.unique_tools import research_web_time_machine
        mcp.tool()(wrap_tool(research_web_time_machine))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.webhook_system import research_webhook_system_fire
        mcp.tool()(wrap_tool(research_webhook_system_fire))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.webhook_system import research_webhook_system_list
        mcp.tool()(wrap_tool(research_webhook_system_list))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.webhook_system import research_webhook_system_register
        mcp.tool()(wrap_tool(research_webhook_system_register))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.white_rabbit import research_white_rabbit
        mcp.tool()(wrap_tool(research_white_rabbit))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.gap_tools_infra import research_whois_correlator
        mcp.tool()(wrap_tool(research_whois_correlator))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.p3_tools import research_wiki_event_correlator
        mcp.tool()(wrap_tool(research_wiki_event_correlator))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_wireless_surveillance
        mcp.tool()(wrap_tool(research_wireless_surveillance))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.xover_attack import research_xover_matrix
        mcp.tool()(wrap_tool(research_xover_matrix))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.xover_attack import research_xover_transfer
        mcp.tool()(wrap_tool(research_xover_transfer))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_ai_detect
        mcp.tool()(wrap_tool(research_ai_detect))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.ytdlp_backend import research_audio_extract
        mcp.tool()(wrap_tool(research_audio_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.audit_query import research_audit_query
        mcp.tool()(wrap_tool(research_audit_query))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.synthetic_data import research_augment_dataset
        mcp.tool()(wrap_tool(research_augment_dataset))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.career_trajectory import research_career_trajectory
        mcp.tool()(wrap_tool(research_career_trajectory))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_citation_graph
        mcp.tool()(wrap_tool(research_citation_graph))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_community_sentiment
        mcp.tool()(wrap_tool(research_community_sentiment))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.document import research_convert_document
        mcp.tool()(wrap_tool(research_convert_document))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_curriculum
        mcp.tool()(wrap_tool(research_curriculum))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.dead_drop_scanner import research_dead_drop_scanner
        mcp.tool()(wrap_tool(research_dead_drop_scanner))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.enrich import research_detect_language
        mcp.tool()(wrap_tool(research_detect_language))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.privacy_advanced import research_fileless_exec
        mcp.tool()(wrap_tool(research_fileless_exec))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.experts import research_find_experts
        mcp.tool()(wrap_tool(research_find_experts))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.neo4j_backend import research_graph_store
        mcp.tool()(wrap_tool(research_graph_store))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs_scorer import research_hcs_score
        mcp.tool()(wrap_tool(research_hcs_score))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.resume_intel import research_interview_prep
        mcp.tool()(wrap_tool(research_interview_prep))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.ip_intel import research_ip_geolocation
        mcp.tool()(wrap_tool(research_ip_geolocation))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.job_research import research_job_market
        mcp.tool()(wrap_tool(research_job_market))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.job_research import research_job_search
        mcp.tool()(wrap_tool(research_job_search))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_answer
        mcp.tool()(wrap_tool(research_llm_answer))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_chat
        mcp.tool()(wrap_tool(research_llm_chat))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_classify
        mcp.tool()(wrap_tool(research_llm_classify))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_embed
        mcp.tool()(wrap_tool(research_llm_embed))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_extract
        mcp.tool()(wrap_tool(research_llm_extract))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_query_expand
        mcp.tool()(wrap_tool(research_llm_query_expand))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_summarize
        mcp.tool()(wrap_tool(research_llm_summarize))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.llm import research_llm_translate
        mcp.tool()(wrap_tool(research_llm_translate))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.career_intel import research_map_research_to_product
        mcp.tool()(wrap_tool(research_map_research_to_product))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.career_trajectory import research_market_velocity
        mcp.tool()(wrap_tool(research_market_velocity))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_misinfo_check
        mcp.tool()(wrap_tool(research_misinfo_check))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_multilingual
        mcp.tool()(wrap_tool(research_multilingual))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.network_persona import research_network_persona
        mcp.tool()(wrap_tool(research_network_persona))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.resume_intel import research_optimize_resume
        mcp.tool()(wrap_tool(research_optimize_resume))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.param_sweep import research_parameter_sweep
        mcp.tool()(wrap_tool(research_parameter_sweep))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.persona_profile import research_persona_profile
        mcp.tool()(wrap_tool(research_persona_profile))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.radicalization_detect import research_radicalization_detect
        mcp.tool()(wrap_tool(research_radicalization_detect))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.embedding_collision import research_rag_attack
        mcp.tool()(wrap_tool(research_rag_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_red_team
        mcp.tool()(wrap_tool(research_red_team))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.reframe_router import research_reframe_or_integrate
        mcp.tool()(wrap_tool(research_reframe_or_integrate))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.infrastructure.retry_stats import research_retry_stats
        mcp.tool()(wrap_tool(research_retry_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.auto_experiment import research_run_experiment
        mcp.tool()(wrap_tool(research_run_experiment))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.screenshot import research_screenshot
        mcp.tool()(wrap_tool(research_screenshot))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.semantic_cache_mgmt import research_semantic_cache_clear
        mcp.tool()(wrap_tool(research_semantic_cache_clear))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.semantic_cache_mgmt import research_semantic_cache_stats
        mcp.tool()(wrap_tool(research_semantic_cache_stats))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_semantic_sitemap
        mcp.tool()(wrap_tool(research_semantic_sitemap))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.sentiment_deep import research_sentiment_deep
        mcp.tool()(wrap_tool(research_sentiment_deep))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.hcs10_academic import research_shell_funding
        mcp.tool()(wrap_tool(research_shell_funding))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.intelligence.social_intel import research_social_profile
        mcp.tool()(wrap_tool(research_social_profile))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.enterprise_sso import research_sso_configure
        mcp.tool()(wrap_tool(research_sso_configure))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.privacy.stego_encoder import research_stego_encode
        mcp.tool()(wrap_tool(research_stego_encode))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_temporal_diff
        mcp.tool()(wrap_tool(research_temporal_diff))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.research.text_analyze import research_text_analyze
        mcp.tool()(wrap_tool(research_text_analyze))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.adversarial.multilang_attack import research_token_split_attack
        mcp.tool()(wrap_tool(research_token_split_attack))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.transcribe import research_transcribe
        mcp.tool()(wrap_tool(research_transcribe))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.career.career_intel import research_translate_academic_skills
        mcp.tool()(wrap_tool(research_translate_academic_skills))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.security.input_sanitizer import research_validate_params
        mcp.tool()(wrap_tool(research_validate_params))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.ytdlp_backend import research_video_download
        mcp.tool()(wrap_tool(research_video_download))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.backends.ytdlp_backend import research_video_info
        mcp.tool()(wrap_tool(research_video_info))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.core.enrich import research_wayback
        mcp.tool()(wrap_tool(research_wayback))
        count += 1
    except Exception:
        pass
    try:
        from loom.tools.llm.creative import research_wiki_ghost
        mcp.tool()(wrap_tool(research_wiki_ghost))
        count += 1
    except Exception:
        pass
    try:
        from loom.encrypted_db import research_db_encryption_status
        mcp.tool()(wrap_tool(research_db_encryption_status))
        count += 1
    except Exception:
        pass
    try:
        from loom.doc_parser import research_document_analyze
        mcp.tool()(wrap_tool(research_document_analyze))
        count += 1
    except Exception:
        pass
    try:
        from loom.doc_parser import research_ocr_advanced
        mcp.tool()(wrap_tool(research_ocr_advanced))
        count += 1
    except Exception:
        pass
    try:
        from loom.doc_parser import research_pdf_advanced
        mcp.tool()(wrap_tool(research_pdf_advanced))
        count += 1
    except Exception:
        pass
    try:
        from loom.mcp_security import research_mcp_security_scan
        mcp.tool()(wrap_tool(research_mcp_security_scan))
        count += 1
    except Exception:
        pass
    log.info('auto_registered_missing count=%d', count)
    return count
