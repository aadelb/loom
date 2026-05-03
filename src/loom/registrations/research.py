"""Research tools — comprehensive coverage of all research, analysis, and specialty tools.

Tools for creative research, dark web exploration, knowledge extraction, persona
analysis, and specialized domain research.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.research")


def register_research_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 315 research and analysis tools.

    Comprehensive coverage of all remaining research, creative, dark web,
    knowledge extraction, and specialty tools.
    """
    from loom.tools import (
        agent_benchmark,
        anomaly_detector,
        antiforensics,
        api_version,
        autonomous_agent,
        backoff_dlq,
        benchmark_suite,
        bias_lens,
        cache_mod,
        changelog_gen,
        chronos,
        cipher_mirror_mod,
        compliance_checker,
        consistency_mod,
        constraint_mod,
        creative_mod,
        crypto_risk,
        culture_dna,
        cve_lookup_mod,
        dead_content,
        dead_drop_scanner_mod,
        deep_research_agent,
        deep_url_analysis,
        dependency_graph,
        doc_parser_tools,
        document_mod,
        email_mod,
        embedding_collision,
        enrich_mod,
        epistemic_mod,
        ethereum_tools,
        evidence_fusion,
        experts_mod,
        explainability,
        exploit_db,
        find_similar_exa,
        fingerprint_evasion,
        fn,
        forum_cortex_mod,
        full_pipeline,
        functor_map,
        gamification,
        gcp_mod,
        geoip_mod,
        getattr,
        ghost_weave_mod,
        graph_analysis,
        graph_scraper,
        hcs_escalation,
        hcs_report,
        hitl_eval,
        image_mod,
        infowar_tools,
        infra_analysis,
        integration_runner,
        ip_intel_mod,
        job_research_mod,
        joplin_mod,
        js_intel,
        knowledge_base,
        knowledge_injector,
        live_registry,
        llm_mod,
        meta_learner,
        metrics_mod,
        mod,
        model_fingerprinter,
        multi_llm,
        network_map,
        network_persona_mod,
        nightcrawler,
        nodriver_mod,
        onion_spectra_mod,
        osint_extended,
        output_diff,
        output_formatter,
        p3_tools,
        paradox_detector,
        param_mod,
        pdf_extract,
        persistent_memory,
        persona_profile_mod,
        privacy_advanced,
        proactive_defense,
        radicalization_detect_mod,
        rag_anything,
        realtime_adapt,
        redteam_hub,
        research_archive_page,
        research_audit_export,
        research_benchmark_run,
        research_browser_fingerprint,
        research_build_query,
        research_censys_host,
        research_censys_search,
        research_config_get,
        research_config_set,
        research_consensus_build,
        research_consensus_pressure,
        research_coverage_run,
        research_creepjs_audit,
        research_crescendo_loop,
        research_dark_cti,
        research_dashboard,
        research_deer_flow,
        research_detect_arabic,
        research_discord_intel,
        research_docs_ai,
        research_document_extract,
        research_email_breach,
        research_full_spectrum,
        research_gpt_researcher,
        research_harvest,
        research_health_check,
        research_intelowl_analyze,
        research_journal,
        research_lightpanda_batch,
        research_lightpanda_fetch,
        research_linkedin_intel,
        research_maigret,
        research_masscan,
        research_massdns_resolve,
        research_memory_recall,
        research_memory_store,
        research_misp_lookup,
        research_model_profile,
        research_onionscan,
        research_opencti_query,
        research_orchestrate,
        research_packet_craft,
        research_paddle_ocr,
        research_pentest_agent,
        research_pentest_docs,
        research_pentest_findings_db,
        research_pentest_plan,
        research_pentest_recommend,
        research_photon_crawl,
        research_pool_reset,
        research_pool_stats,
        research_pydantic_agent,
        research_reconng_scan,
        research_reid_auto,
        research_reid_pipeline,
        research_reverse_image,
        research_robin_scan,
        research_score_all,
        research_session_close,
        research_session_list,
        research_session_open,
        research_shodan_host,
        research_shodan_search,
        research_social_analyze,
        research_spiderfoot_scan,
        research_storage_dashboard,
        research_structured_extract,
        research_structured_llm,
        research_supercookie_check,
        research_table_extract,
        research_telegram_intel,
        research_testssl,
        research_unified_score,
        research_web_check,
        research_yara_scan,
        resume_intel_mod,
        rss_monitor,
        safety_neurons,
        safety_predictor,
        scraper_engine_tools,
        screenshot_mod,
        sentiment_deep_mod,
        session_replay,
        silk_guardian,
        slack_mod,
        social_intel,
        social_scraper,
        stego_encoder,
        synthetic_data,
        task_resolver,
        text_analyze_mod,
        tor_mod,
        trend_predictor,
        unique_tools,
        vision_agent,
        webhook_system,
        white_rabbit
    )

    mcp.tool()(_wrap_tool(deep_url_analysis.research_deep_url_analysis))
    mcp.tool()(_wrap_tool(deep_research_agent.research_hierarchical_research, "hierarchical_research"))
    mcp.tool()(_wrap_tool(changelog_gen.research_changelog_generate))
    mcp.tool()(_wrap_tool(changelog_gen.research_changelog_stats))
    mcp.tool()(_wrap_tool(anomaly_detector.research_detect_anomalies))
    mcp.tool()(_wrap_tool(anomaly_detector.research_detect_text_anomalies))
    mcp.tool()(_wrap_tool(benchmark_suite.research_benchmark_run))
    mcp.tool()(_wrap_tool(benchmark_suite.research_benchmark_compare))
    mcp.tool()(_wrap_tool(redteam_hub.research_hub_share))
    mcp.tool()(_wrap_tool(redteam_hub.research_hub_feed))
    mcp.tool()(_wrap_tool(redteam_hub.research_hub_vote))
    mcp.tool()(_wrap_tool(backoff_dlq.research_dlq_push))
    mcp.tool()(_wrap_tool(backoff_dlq.research_dlq_list))
    mcp.tool()(_wrap_tool(backoff_dlq.research_dlq_retry))
    mcp.tool()(_wrap_tool(research_pool_stats))
    mcp.tool()(_wrap_tool(research_pool_reset))
    mcp.tool()(_wrap_tool(chronos.research_chronos_reverse))
    mcp.tool()(_wrap_tool(exploit_db.research_exploit_register))
    mcp.tool()(_wrap_tool(exploit_db.research_exploit_search))
    mcp.tool()(_wrap_tool(exploit_db.research_exploit_stats))
    mcp.tool()(_wrap_tool(output_formatter.research_format_report))
    mcp.tool()(_wrap_tool(output_formatter.research_extract_actionables))
    mcp.tool()(_wrap_tool(output_diff.research_diff_compare))
    mcp.tool()(_wrap_tool(output_diff.research_diff_track))
    mcp.tool()(_wrap_tool(hitl_eval.research_hitl_submit))
    mcp.tool()(_wrap_tool(hitl_eval.research_hitl_evaluate))
    mcp.tool()(_wrap_tool(hitl_eval.research_hitl_queue))
    mcp.tool()(_wrap_tool(meta_learner.research_meta_learn))
    mcp.tool()(_wrap_tool(autonomous_agent.research_auto_redteam))
    mcp.tool()(_wrap_tool(autonomous_agent.research_schedule_redteam))
    mcp.tool()(_wrap_tool(gamification.research_leaderboard))
    mcp.tool()(_wrap_tool(gamification.research_challenge_create))
    mcp.tool()(_wrap_tool(gamification.research_challenge_list))
    mcp.tool()(_wrap_tool(rag_anything.research_rag_ingest))
    mcp.tool()(_wrap_tool(rag_anything.research_rag_query))
    mcp.tool()(_wrap_tool(rag_anything.research_rag_clear))
    mcp.tool()(_wrap_tool(scraper_engine_tools.research_engine_fetch, "fetch"))
    mcp.tool()(_wrap_tool(scraper_engine_tools.research_engine_extract, "fetch"))
    mcp.tool()(_wrap_tool(scraper_engine_tools.research_engine_batch, "fetch"))
    mcp.tool()(_wrap_tool(dead_content.research_dead_content, "fetch"))
    mcp.tool()(_wrap_tool(js_intel.research_js_intel, "fetch"))
    mcp.tool()(_wrap_tool(network_map.research_network_map))
    mcp.tool()(_wrap_tool(network_map.research_network_visualize))
    mcp.tool()(_wrap_tool(infra_analysis.research_registry_graveyard, "fetch"))
    mcp.tool()(_wrap_tool(infra_analysis.research_subdomain_temporal, "fetch"))
    mcp.tool()(_wrap_tool(infra_analysis.research_commit_analyzer, "fetch"))
    mcp.tool()(_wrap_tool(antiforensics.research_usb_kill_monitor))
    mcp.tool()(_wrap_tool(antiforensics.research_artifact_cleanup))
    mcp.tool()(_wrap_tool(silk_guardian.research_silk_guardian_monitor))
    mcp.tool()(_wrap_tool(privacy_advanced.research_browser_fingerprint_audit, "fetch"))
    mcp.tool()(_wrap_tool(privacy_advanced.research_metadata_strip, "fetch"))
    mcp.tool()(_wrap_tool(privacy_advanced.research_secure_delete))
    mcp.tool()(_wrap_tool(privacy_advanced.research_mac_randomize))
    mcp.tool()(_wrap_tool(privacy_advanced.research_dns_leak_check))
    mcp.tool()(_wrap_tool(privacy_advanced.research_tor_circuit_info))
    mcp.tool()(_wrap_tool(privacy_advanced.research_privacy_score, "fetch"))
    mcp.tool()(_wrap_tool(crypto_risk.research_crypto_risk_score))
    mcp.tool()(_wrap_tool(ethereum_tools.research_ethereum_tx_decode))
    mcp.tool()(_wrap_tool(ethereum_tools.research_defi_security_audit))
    mcp.tool()(_wrap_tool(stego_encoder.research_stego_encode))
    mcp.tool()(_wrap_tool(stego_encoder.research_stego_analyze))
    mcp.tool()(_wrap_tool(dependency_graph.research_tool_dependencies))
    mcp.tool()(_wrap_tool(dependency_graph.research_tool_impact))
    mcp.tool()(_wrap_tool(integration_runner.research_integration_test))
    mcp.tool()(_wrap_tool(integration_runner.research_smoke_test))
    mcp.tool()(_wrap_tool(infowar_tools.research_narrative_tracker, "search"))
    mcp.tool()(_wrap_tool(infowar_tools.research_bot_detector, "search"))
    mcp.tool()(_wrap_tool(infowar_tools.research_censorship_detector, "fetch"))
    mcp.tool()(_wrap_tool(infowar_tools.research_deleted_social, "fetch"))
    mcp.tool()(_wrap_tool(infowar_tools.research_robots_archaeology, "fetch"))
    mcp.tool()(_wrap_tool(compliance_checker.research_compliance_check))
    mcp.tool()(_wrap_tool(compliance_checker.research_pii_scan))
    mcp.tool()(_wrap_tool(safety_predictor.research_predict_safety_update))
    mcp.tool()(_wrap_tool(safety_neurons.research_safety_circuit_map))
    mcp.tool()(_wrap_tool(safety_neurons.research_circuit_bypass_plan))
    mcp.tool()(_wrap_tool(paradox_detector.research_detect_paradox))
    mcp.tool()(_wrap_tool(paradox_detector.research_paradox_immunize))
    mcp.tool()(_wrap_tool(explainability.research_explain_bypass))
    mcp.tool()(_wrap_tool(explainability.research_vulnerability_map))
    mcp.tool()(_wrap_tool(proactive_defense.research_predict_attacks))
    mcp.tool()(_wrap_tool(proactive_defense.research_preemptive_patch))
    mcp.tool()(_wrap_tool(embedding_collision.research_embedding_collide))
    mcp.tool()(_wrap_tool(embedding_collision.research_rag_attack))
    mcp.tool()(_wrap_tool(evidence_fusion.research_fuse_evidence))
    mcp.tool()(_wrap_tool(evidence_fusion.research_authority_stack))
    mcp.tool()(_wrap_tool(model_fingerprinter.research_fingerprint_behavior, "llm"))
    mcp.tool()(_wrap_tool(fingerprint_evasion.research_fingerprint_evasion_test))
    mcp.tool()(_wrap_tool(agent_benchmark.research_agent_benchmark))
    mcp.tool()(_wrap_tool(osint_extended.research_social_engineering_score, "fetch"))
    mcp.tool()(_wrap_tool(osint_extended.research_behavioral_fingerprint, "fetch"))
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_extract, "fetch"))
    mcp.tool()(_wrap_tool(pdf_extract.research_pdf_search, "fetch"))
    mcp.tool()(_wrap_tool(doc_parser_tools.research_ocr_advanced, "fetch"))
    mcp.tool()(_wrap_tool(doc_parser_tools.research_pdf_advanced, "fetch"))
    mcp.tool()(_wrap_tool(doc_parser_tools.research_document_analyze, "fetch"))
    mcp.tool()(_wrap_tool(hcs_report.research_hcs_report, "analysis"))
    mcp.tool()(_wrap_tool(hcs_escalation.research_hcs_escalate, "orchestration"))
    mcp.tool()(_wrap_tool(full_pipeline.research_full_pipeline, "orchestration"))
    mcp.tool()(_wrap_tool(bias_lens.research_bias_lens, "fetch"))
    mcp.tool()(_wrap_tool(realtime_adapt.research_track_refusal))
    mcp.tool()(_wrap_tool(realtime_adapt.research_get_best_model))
    mcp.tool()(_wrap_tool(nightcrawler.research_arxiv_scan, "search"))
    mcp.tool()(_wrap_tool(nightcrawler.research_nightcrawler_status))
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_fetch, "fetch"))
    mcp.tool()(_wrap_tool(rss_monitor.research_rss_search, "search"))
    mcp.tool()(_wrap_tool(social_intel.research_social_search, "fetch"))
    mcp.tool()(_wrap_tool(social_intel.research_social_profile, "fetch"))
    mcp.tool()(_wrap_tool(social_scraper.research_instagram, "fetch"))
    mcp.tool()(_wrap_tool(social_scraper.research_article_extract, "fetch"))
    mcp.tool()(_wrap_tool(social_scraper.research_article_batch, "fetch"))
    mcp.tool()(_wrap_tool(trend_predictor.research_trend_predict, "search"))
    mcp.tool()(_wrap_tool(live_registry.research_registry_status))
    mcp.tool()(_wrap_tool(live_registry.research_registry_search))
    mcp.tool()(_wrap_tool(live_registry.research_registry_refresh))
    mcp.tool()(_wrap_tool(unique_tools.research_propaganda_detector))
    mcp.tool()(_wrap_tool(unique_tools.research_source_credibility, "fetch"))
    mcp.tool()(_wrap_tool(unique_tools.research_information_cascade, "search"))
    mcp.tool()(_wrap_tool(unique_tools.research_web_time_machine, "fetch"))
    mcp.tool()(_wrap_tool(unique_tools.research_influence_operation, "search"))
    mcp.tool()(_wrap_tool(unique_tools.research_dark_web_bridge, "search"))
    mcp.tool()(_wrap_tool(unique_tools.research_info_half_life, "fetch"))
    mcp.tool()(_wrap_tool(unique_tools.research_search_discrepancy, "search"))
    mcp.tool()(_wrap_tool(vision_agent.research_vision_browse, "fetch"))
    mcp.tool()(_wrap_tool(vision_agent.research_vision_compare, "fetch"))
    mcp.tool()(_wrap_tool(white_rabbit.research_white_rabbit))
    mcp.tool()(_wrap_tool(webhook_system.research_webhook_register))
    mcp.tool()(_wrap_tool(webhook_system.research_webhook_fire))
    mcp.tool()(_wrap_tool(webhook_system.research_webhook_list))
    mcp.tool()(_wrap_tool(research_consensus_build))
    mcp.tool()(_wrap_tool(research_consensus_pressure))
    mcp.tool()(_wrap_tool(research_crescendo_loop))
    mcp.tool()(_wrap_tool(research_model_profile))
    mcp.tool()(_wrap_tool(research_benchmark_run))
    mcp.tool()(_wrap_tool(research_reid_pipeline))
    mcp.tool()(_wrap_tool(creative_mod.research_ai_detect))
    mcp.tool()(_wrap_tool(creative_mod.research_citation_graph))
    mcp.tool()(_wrap_tool(creative_mod.research_community_sentiment))
    mcp.tool()(_wrap_tool(creative_mod.research_curriculum))
    mcp.tool()(_wrap_tool(creative_mod.research_misinfo_check))
    mcp.tool()(_wrap_tool(creative_mod.research_multilingual))
    mcp.tool()(_wrap_tool(creative_mod.research_red_team))
    mcp.tool()(_wrap_tool(creative_mod.research_semantic_sitemap))
    mcp.tool()(_wrap_tool(creative_mod.research_temporal_diff))
    mcp.tool()(_wrap_tool(creative_mod.research_wiki_ghost))
    mcp.tool()(_wrap_tool(consistency_mod.research_consistency_pressure))
    mcp.tool()(_wrap_tool(consistency_mod.research_consistency_pressure_history))
    mcp.tool()(_wrap_tool(consistency_mod.research_consistency_pressure_record))
    mcp.tool()(_wrap_tool(constraint_mod.research_constraint_optimize))
    mcp.tool()(_wrap_tool(param_mod.research_parameter_sweep))
    mcp.tool()(_wrap_tool(cache_mod.research_semantic_cache_stats))
    mcp.tool()(_wrap_tool(cache_mod.research_semantic_cache_clear))
    mcp.tool()(_wrap_tool(research_session_open))
    mcp.tool()(_wrap_tool(research_session_list))
    mcp.tool()(_wrap_tool(research_session_close))
    mcp.tool()(_wrap_tool(session_replay.research_session_record))
    mcp.tool()(_wrap_tool(session_replay.research_session_replay))
    mcp.tool()(_wrap_tool(session_replay.research_session_list))
    mcp.tool()(_wrap_tool(task_resolver.research_resolve_order))
    mcp.tool()(_wrap_tool(task_resolver.research_critical_path))
    mcp.tool()(_wrap_tool(research_config_get))
    mcp.tool()(_wrap_tool(research_config_set))
    mcp.tool()(_wrap_tool(research_audit_export))
    mcp.tool()(_wrap_tool(research_pentest_agent))
    mcp.tool()(_wrap_tool(research_pentest_plan))
    mcp.tool()(_wrap_tool(research_pentest_recommend))
    mcp.tool()(_wrap_tool(research_pentest_docs))
    mcp.tool()(_wrap_tool(research_pentest_findings_db))
    mcp.tool()(_wrap_tool(research_maigret))
    mcp.tool()(_wrap_tool(research_harvest))
    mcp.tool()(_wrap_tool(research_spiderfoot_scan))
    mcp.tool()(_wrap_tool(research_archive_page))
    mcp.tool()(_wrap_tool(research_social_analyze))
    mcp.tool()(_wrap_tool(research_yara_scan))
    mcp.tool()(_wrap_tool(research_misp_lookup))
    mcp.tool()(_wrap_tool(research_gpt_researcher))
    mcp.tool()(_wrap_tool(research_docs_ai))
    mcp.tool()(_wrap_tool(research_deer_flow))
    mcp.tool()(_wrap_tool(research_web_check))
    mcp.tool()(_wrap_tool(research_shodan_host))
    mcp.tool()(_wrap_tool(research_shodan_search))
    mcp.tool()(_wrap_tool(research_photon_crawl))
    mcp.tool()(_wrap_tool(research_email_breach))
    mcp.tool()(_wrap_tool(research_censys_host))
    mcp.tool()(_wrap_tool(research_censys_search))
    mcp.tool()(_wrap_tool(research_document_extract))
    mcp.tool()(_wrap_tool(research_structured_extract))
    mcp.tool()(_wrap_tool(research_pydantic_agent, "llm"))
    mcp.tool()(_wrap_tool(research_structured_llm, "llm"))
    mcp.tool()(_wrap_tool(research_build_query))
    mcp.tool()(_wrap_tool(research_opencti_query))
    mcp.tool()(_wrap_tool(research_intelowl_analyze))
    mcp.tool()(_wrap_tool(research_dark_cti))
    mcp.tool()(_wrap_tool(research_telegram_intel))
    mcp.tool()(_wrap_tool(research_linkedin_intel))
    mcp.tool()(_wrap_tool(research_discord_intel))
    mcp.tool()(_wrap_tool(research_reconng_scan))
    mcp.tool()(_wrap_tool(research_massdns_resolve))
    mcp.tool()(_wrap_tool(research_reverse_image))
    mcp.tool()(_wrap_tool(research_robin_scan))
    mcp.tool()(_wrap_tool(research_onionscan))
    mcp.tool()(_wrap_tool(research_testssl))
    mcp.tool()(_wrap_tool(research_masscan))
    mcp.tool()(_wrap_tool(research_paddle_ocr))
    mcp.tool()(_wrap_tool(research_table_extract))
    mcp.tool()(_wrap_tool(research_packet_craft))
    mcp.tool()(_wrap_tool(research_browser_fingerprint))
    mcp.tool()(_wrap_tool(research_supercookie_check))
    mcp.tool()(_wrap_tool(research_lightpanda_fetch, "fetch"))
    mcp.tool()(_wrap_tool(research_lightpanda_batch, "fetch"))
    mcp.tool()(_wrap_tool(research_creepjs_audit))
    mcp.tool()(_wrap_tool(research_memory_store))
    mcp.tool()(_wrap_tool(research_memory_recall))
    mcp.tool()(_wrap_tool(research_detect_arabic))
    mcp.tool()(_wrap_tool(research_storage_dashboard))
    mcp.tool()(_wrap_tool(research_health_check))
    mcp.tool()(_wrap_tool(research_coverage_run))
    mcp.tool()(_wrap_tool(research_dashboard))
    mcp.tool()(_wrap_tool(api_version.research_api_version))
    mcp.tool()(_wrap_tool(api_version.research_api_changelog))
    mcp.tool()(_wrap_tool(api_version.research_api_deprecations))
    mcp.tool()(_wrap_tool(research_orchestrate))
    mcp.tool()(_wrap_tool(research_score_all))
    mcp.tool()(_wrap_tool(research_full_spectrum))
    mcp.tool()(_wrap_tool(research_unified_score, "analysis"))
    mcp.tool()(_wrap_tool(find_similar_exa, "search"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_summarize, "llm"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_extract, "llm"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_classify, "llm"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_translate, "llm"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_query_expand, "llm"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_answer, "llm"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_embed, "llm"))
    mcp.tool()(_wrap_tool(llm_mod.research_llm_chat, "llm"))
    mcp.tool()(_wrap_tool(enrich_mod.research_detect_language))
    mcp.tool()(_wrap_tool(enrich_mod.research_wayback, "fetch"))
    mcp.tool()(_wrap_tool(experts_mod.research_find_experts, "llm"))
    mcp.tool()(_wrap_tool(getattr(creative_mod, tool_name), "llm"))
    mcp.tool()(_wrap_tool(email_mod.research_email_report))
    mcp.tool()(_wrap_tool(job_research_mod.research_job_search, "search"))
    mcp.tool()(_wrap_tool(job_research_mod.research_job_market, "search"))
    mcp.tool()(_wrap_tool(joplin_mod.research_save_note))
    mcp.tool()(_wrap_tool(joplin_mod.research_list_notebooks))
    mcp.tool()(_wrap_tool(tor_mod.research_tor_status))
    mcp.tool()(_wrap_tool(tor_mod.research_tor_new_identity))
    mcp.tool()(_wrap_tool(document_mod.research_convert_document, "fetch"))
    mcp.tool()(_wrap_tool(metrics_mod.research_metrics))
    mcp.tool()(_wrap_tool(slack_mod.research_slack_notify))
    mcp.tool()(_wrap_tool(gcp_mod.research_image_analyze))
    mcp.tool()(_wrap_tool(gcp_mod.research_text_to_speech))
    mcp.tool()(_wrap_tool(gcp_mod.research_tts_voices))
    mcp.tool()(_wrap_tool(cipher_mirror_mod.research_cipher_mirror, "fetch"))
    mcp.tool()(_wrap_tool(forum_cortex_mod.research_forum_cortex, "fetch"))
    mcp.tool()(_wrap_tool(onion_spectra_mod.research_onion_spectra, "fetch"))
    mcp.tool()(_wrap_tool(ghost_weave_mod.research_ghost_weave, "fetch"))
    mcp.tool()(_wrap_tool(dead_drop_scanner_mod.research_dead_drop_scanner, "fetch"))
    mcp.tool()(_wrap_tool(persona_profile_mod.research_persona_profile, "llm"))
    mcp.tool()(_wrap_tool(radicalization_detect_mod.research_radicalization_detect, "llm"))
    mcp.tool()(_wrap_tool(sentiment_deep_mod.research_sentiment_deep, "analysis"))
    mcp.tool()(_wrap_tool(network_persona_mod.research_network_persona, "analysis"))
    mcp.tool()(_wrap_tool(text_analyze_mod.research_text_analyze, "analysis"))
    mcp.tool()(_wrap_tool(epistemic_mod.research_epistemic_score, "analysis"))
    mcp.tool()(_wrap_tool(screenshot_mod.research_screenshot, "fetch"))
    mcp.tool()(_wrap_tool(ip_intel_mod.research_ip_reputation, "fetch"))
    mcp.tool()(_wrap_tool(ip_intel_mod.research_ip_geolocation, "fetch"))
    mcp.tool()(_wrap_tool(cve_lookup_mod.research_cve_lookup, "search"))
    mcp.tool()(_wrap_tool(cve_lookup_mod.research_cve_detail, "fetch"))
    mcp.tool()(_wrap_tool(geoip_mod.research_geoip_local, "fetch"))
    mcp.tool()(_wrap_tool(image_mod.research_exif_extract, "fetch"))
    mcp.tool()(_wrap_tool(image_mod.research_ocr_extract, "fetch"))
    mcp.tool()(_wrap_tool(resume_intel_mod.research_optimize_resume, "llm"))
    mcp.tool()(_wrap_tool(resume_intel_mod.research_interview_prep, "llm"))
    mcp.tool()(_wrap_tool(nodriver_mod.research_nodriver_fetch, "fetch"))
    mcp.tool()(_wrap_tool(nodriver_mod.research_nodriver_extract, "fetch"))
    mcp.tool()(_wrap_tool(nodriver_mod.research_nodriver_session, "fetch"))
    mcp.tool()(_wrap_tool(p3_tools.research_model_comparator, "fetch"))
    mcp.tool()(_wrap_tool(p3_tools.research_data_poisoning, "fetch"))
    mcp.tool()(_wrap_tool(p3_tools.research_wiki_event_correlator, "fetch"))
    mcp.tool()(_wrap_tool(p3_tools.research_foia_tracker, "search"))
    mcp.tool()(_wrap_tool(knowledge_injector.research_personalize_output))
    mcp.tool()(_wrap_tool(knowledge_injector.research_adapt_complexity))
    mcp.tool()(_wrap_tool(knowledge_base.research_kb_store))
    mcp.tool()(_wrap_tool(knowledge_base.research_kb_search))
    mcp.tool()(_wrap_tool(knowledge_base.research_kb_stats))
    mcp.tool()(_wrap_tool(graph_scraper.research_graph_scrape, "fetch"))
    mcp.tool()(_wrap_tool(graph_scraper.research_knowledge_extract, "search"))
    mcp.tool()(_wrap_tool(graph_scraper.research_multi_page_graph, "fetch"))
    mcp.tool()(_wrap_tool(graph_analysis.research_graph_analyze))
    mcp.tool()(_wrap_tool(graph_analysis.research_transaction_graph))
    mcp.tool()(_wrap_tool(persistent_memory.research_remember))
    mcp.tool()(_wrap_tool(persistent_memory.research_recall))
    mcp.tool()(_wrap_tool(persistent_memory.research_memory_stats))
    mcp.tool()(_wrap_tool(culture_dna.research_culture_dna, "search"))
    mcp.tool()(_wrap_tool(synthetic_data.research_generate_redteam_dataset))
    mcp.tool()(_wrap_tool(synthetic_data.research_augment_dataset))
    mcp.tool()(_wrap_tool(functor_map.research_functor_translate))
    mcp.tool()(_wrap_tool(multi_llm.research_ask_all_llms, "llm"))
    mcp.tool()(_wrap_tool(mod.research_attack_score))
    mcp.tool()(_wrap_tool(mod.research_stealth_score))
    mcp.tool()(_wrap_tool(mod.research_potency_score))
    mcp.tool()(_wrap_tool(mod.research_model_sentiment))
    mcp.tool()(_wrap_tool(mod.research_toxicity_check))
    mcp.tool()(_wrap_tool(mod.research_drift_monitor))
    mcp.tool()(_wrap_tool(mod.research_drift_monitor_list))
    mcp.tool()(_wrap_tool(mod.research_bpj_generate))
    mcp.tool()(_wrap_tool(mod.research_daisy_chain))
    mcp.tool()(_wrap_tool(mod.research_strategy_oracle))
    mcp.tool()(_wrap_tool(mod.research_stealth_detect))
    mcp.tool()(_wrap_tool(mod.research_recommend_tools))
    mcp.tool()(_wrap_tool(mod.research_multi_consensus, "llm"))
    mcp.tool()(_wrap_tool(getattr(mod, fn_name)))
    mcp.tool()(_wrap_tool(research_reid_auto, "llm"))
    mcp.tool()(_wrap_tool(fn, "fetch"))
    mcp.tool()(_wrap_tool(research_journal.research_journal_add))
    mcp.tool()(_wrap_tool(research_journal.research_journal_search))
    mcp.tool()(_wrap_tool(research_journal.research_journal_timeline))

    log.info("registered research tools", tool_count=315)
