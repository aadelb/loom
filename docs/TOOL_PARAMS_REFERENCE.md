# Loom Tool Parameters Reference

> Auto-generated from source code inspection. 806 tools across 410 modules.
> Generated: 2026-05-06

## Table of Contents

- [academic_integrity](#academic_integrity) (3 tools)
- [access_tools](#access_tools) (5 tools)
- [adversarial_craft](#adversarial_craft) (2 tools)
- [adversarial_debate_tool](#adversarial_debate_tool) (1 tools)
- [agent_benchmark](#agent_benchmark) (1 tools)
- [ai_safety](#ai_safety) (5 tools)
- [ai_safety_extended](#ai_safety_extended) (2 tools)
- [anomaly_detector](#anomaly_detector) (2 tools)
- [antiforensics](#antiforensics) (2 tools)
- [api_fuzzer](#api_fuzzer) (2 tools)
- [api_version](#api_version) (3 tools)
- [arxiv_pipeline](#arxiv_pipeline) (2 tools)
- [ask_all_models](#ask_all_models) (1 tools)
- [attack_economy](#attack_economy) (3 tools)
- [audit_log](#audit_log) (3 tools)
- [audit_query](#audit_query) (2 tools)
- [auto_docs](#auto_docs) (2 tools)
- [auto_experiment](#auto_experiment) (2 tools)
- [auto_params](#auto_params) (2 tools)
- [auto_pipeline](#auto_pipeline) (1 tools)
- [auto_report](#auto_report) (2 tools)
- [autonomous_agent](#autonomous_agent) (2 tools)
- [backoff_dlq](#backoff_dlq) (3 tools)
- [backup_system](#backup_system) (3 tools)
- [benchmark_datasets](#benchmark_datasets) (2 tools)
- [benchmark_leaderboard](#benchmark_leaderboard) (3 tools)
- [benchmark_suite](#benchmark_suite) (2 tools)
- [bias_lens](#bias_lens) (1 tools)
- [billing](#billing) (1 tools)
- [bpj](#bpj) (1 tools)
- [breach_check](#breach_check) (2 tools)
- [cache_mgmt](#cache_mgmt) (2 tools)
- [cache_optimizer](#cache_optimizer) (2 tools)
- [camelot_backend](#camelot_backend) (1 tools)
- [capability_matrix](#capability_matrix) (2 tools)
- [career_intel](#career_intel) (2 tools)
- [career_trajectory](#career_trajectory) (2 tools)
- [censys_backend](#censys_backend) (2 tools)
- [cert_analyzer](#cert_analyzer) (1 tools)
- [chain_composer](#chain_composer) (3 tools)
- [change_monitor](#change_monitor) (1 tools)
- [changelog_gen](#changelog_gen) (2 tools)
- [chronos](#chronos) (1 tools)
- [cipher_mirror](#cipher_mirror) (1 tools)
- [circuit_breaker](#circuit_breaker) (3 tools)
- [cli_autocomplete](#cli_autocomplete) (2 tools)
- [cloak_backend](#cloak_backend) (3 tools)
- [cluster_health](#cluster_health) (2 tools)
- [coevolution](#coevolution) (1 tools)
- [company_intel](#company_intel) (2 tools)
- [competitive_intel](#competitive_intel) (1 tools)
- [competitive_monitor](#competitive_monitor) (2 tools)
- [compliance_checker](#compliance_checker) (2 tools)
- [compliance_report](#compliance_report) (2 tools)
- [composer](#composer) (3 tools)
- [composition_optimizer](#composition_optimizer) (3 tools)
- [config_reload](#config_reload) (3 tools)
- [consistency_pressure](#consistency_pressure) (3 tools)
- [constraint_optimizer](#constraint_optimizer) (2 tools)
- [content_anomaly](#content_anomaly) (1 tools)
- [context_manager](#context_manager) (3 tools)
- [cost_estimator](#cost_estimator) (1 tools)
- [creative](#creative) (11 tools)
- [credential_vault](#credential_vault) (3 tools)
- [creepjs_backend](#creepjs_backend) (1 tools)
- [cross_domain](#cross_domain) (1 tools)
- [crypto_risk](#crypto_risk) (1 tools)
- [crypto_trace](#crypto_trace) (1 tools)
- [cultural_attacks](#cultural_attacks) (2 tools)
- [culture_dna](#culture_dna) (1 tools)
- [cve_lookup](#cve_lookup) (2 tools)
- [cyberscraper](#cyberscraper) (3 tools)
- [cyberscraper_backend](#cyberscraper_backend) (2 tools)
- [daisy_chain_tool](#daisy_chain_tool) (1 tools)
- [dark_forum](#dark_forum) (1 tools)
- [dark_recon](#dark_recon) (3 tools)
- [darkweb_early_warning](#darkweb_early_warning) (1 tools)
- [data_export](#data_export) (3 tools)
- [data_pipeline](#data_pipeline) (3 tools)
- [dead_content](#dead_content) (1 tools)
- [dead_drop_scanner](#dead_drop_scanner) (1 tools)
- [deception_detect](#deception_detect) (1 tools)
- [deception_job_scanner](#deception_job_scanner) (1 tools)
- [deep](#deep) (1 tools)
- [deep_research_agent](#deep_research_agent) (1 tools)
- [deep_url_analysis](#deep_url_analysis) (1 tools)
- [deepdarkcti_backend](#deepdarkcti_backend) (1 tools)
- [deerflow_backend](#deerflow_backend) (1 tools)
- [defender_mode](#defender_mode) (2 tools)
- [demo_decorator_usage](#demo_decorator_usage) (2 tools)
- [dependency_graph](#dependency_graph) (2 tools)
- [deployment](#deployment) (3 tools)
- [discord_osint](#discord_osint) (1 tools)
- [dist_tracing](#dist_tracing) (3 tools)
- [dlq_management](#dlq_management) (4 tools)
- [dns_server](#dns_server) (2 tools)
- [do_expert](#do_expert) (1 tools)
- [docker_tools](#docker_tools) (2 tools)
- [docsgpt_backend](#docsgpt_backend) (1 tools)
- [document](#document) (1 tools)
- [domain_intel](#domain_intel) (3 tools)
- [drift_monitor_tool](#drift_monitor_tool) (2 tools)
- [dspy_bridge](#dspy_bridge) (2 tools)
- [eagleeye_backend](#eagleeye_backend) (1 tools)
- [email_report](#email_report) (1 tools)
- [embedding_collision](#embedding_collision) (2 tools)
- [enrich](#enrich) (2 tools)
- [ensemble_attack](#ensemble_attack) (2 tools)
- [enterprise_sso](#enterprise_sso) (3 tools)
- [env_inspector](#env_inspector) (2 tools)
- [epistemic_score](#epistemic_score) (1 tools)
- [error_wrapper](#error_wrapper) (2 tools)
- [ethereum_tools](#ethereum_tools) (2 tools)
- [eu_ai_act](#eu_ai_act) (5 tools)
- [evasion_network](#evasion_network) (2 tools)
- [event_bus](#event_bus) (3 tools)
- [evidence_analyzer](#evidence_analyzer) (1 tools)
- [evidence_fusion](#evidence_fusion) (2 tools)
- [execution_planner](#execution_planner) (2 tools)
- [expert_engine](#expert_engine) (1 tools)
- [experts](#experts) (1 tools)
- [explainability](#explainability) (1 tools)
- [exploit_db](#exploit_db) (3 tools)
- [fact_checker](#fact_checker) (1 tools)
- [fact_verifier](#fact_verifier) (2 tools)
- [feature_flags](#feature_flags) (3 tools)
- [fingerprint_backend](#fingerprint_backend) (1 tools)
- [fingerprint_evasion](#fingerprint_evasion) (1 tools)
- [firewall_rules](#firewall_rules) (2 tools)
- [forum_cortex](#forum_cortex) (1 tools)
- [full_pipeline](#full_pipeline) (3 tools)
- [functor_map](#functor_map) (1 tools)
- [gamification](#gamification) (3 tools)
- [gap_tools_academic](#gap_tools_academic) (3 tools)
- [gap_tools_advanced](#gap_tools_advanced) (4 tools)
- [gap_tools_ai](#gap_tools_ai) (3 tools)
- [gap_tools_infra](#gap_tools_infra) (4 tools)
- [gcp](#gcp) (3 tools)
- [genetic_fuzzer](#genetic_fuzzer) (1 tools)
- [geodesic_forcing](#geodesic_forcing) (1 tools)
- [geoip_local](#geoip_local) (1 tools)
- [ghost_weave](#ghost_weave) (1 tools)
- [github](#github) (3 tools)
- [gpt_researcher_backend](#gpt_researcher_backend) (1 tools)
- [graph_analysis](#graph_analysis) (2 tools)
- [graph_scraper](#graph_scraper) (3 tools)
- [h8mail_backend](#h8mail_backend) (1 tools)
- [harvester_backend](#harvester_backend) (1 tools)
- [hcs10_academic](#hcs10_academic) (8 tools)
- [hcs_escalation](#hcs_escalation) (1 tools)
- [hcs_multi_scorer](#hcs_multi_scorer) (5 tools)
- [hcs_report](#hcs_report) (1 tools)
- [hcs_rubric_tool](#hcs_rubric_tool) (1 tools)
- [hcs_scorer](#hcs_scorer) (1 tools)
- [health_dashboard](#health_dashboard) (1 tools)
- [health_deep](#health_deep) (1 tools)
- [help_system](#help_system) (2 tools)
- [hipporag_backend](#hipporag_backend) (2 tools)
- [hitl_eval](#hitl_eval) (3 tools)
- [holographic_payload](#holographic_payload) (1 tools)
- [identity_resolve](#identity_resolve) (1 tools)
- [image_intel](#image_intel) (2 tools)
- [infowar_tools](#infowar_tools) (5 tools)
- [infra_analysis](#infra_analysis) (3 tools)
- [infra_correlator](#infra_correlator) (1 tools)
- [input_sanitizer](#input_sanitizer) (2 tools)
- [instructor_backend](#instructor_backend) (1 tools)
- [integration_runner](#integration_runner) (2 tools)
- [intel_report](#intel_report) (2 tools)
- [intelowl_backend](#intelowl_backend) (1 tools)
- [invisible_web](#invisible_web) (1 tools)
- [ip_intel](#ip_intel) (2 tools)
- [jailbreak_evolution](#jailbreak_evolution) (6 tools)
- [job_research](#job_research) (2 tools)
- [job_signals](#job_signals) (3 tools)
- [job_tools](#job_tools) (5 tools)
- [joplin](#joplin) (2 tools)
- [js_intel](#js_intel) (1 tools)
- [json_logger](#json_logger) (2 tools)
- [key_rotation](#key_rotation) (3 tools)
- [knowledge_base](#knowledge_base) (3 tools)
- [knowledge_graph](#knowledge_graph) (2 tools)
- [knowledge_injector](#knowledge_injector) (2 tools)
- [latency_report](#latency_report) (1 tools)
- [leak_scan](#leak_scan) (1 tools)
- [lifetime_oracle](#lifetime_oracle) (1 tools)
- [lightpanda_backend](#lightpanda_backend) (2 tools)
- [linkedin_osint](#linkedin_osint) (1 tools)
- [live_registry](#live_registry) (3 tools)
- [llm](#llm) (8 tools)
- [load_balancer](#load_balancer) (2 tools)
- [loader_stats](#loader_stats) (1 tools)
- [maigret_backend](#maigret_backend) (1 tools)
- [markdown](#markdown) (1 tools)
- [marketplace](#marketplace) (3 tools)
- [masscan_backend](#masscan_backend) (1 tools)
- [massdns_backend](#massdns_backend) (1 tools)
- [mcp_auth](#mcp_auth) (3 tools)
- [memetic_simulator](#memetic_simulator) (1 tools)
- [memory_mgmt](#memory_mgmt) (3 tools)
- [meta_learner](#meta_learner) (1 tools)
- [metadata_forensics](#metadata_forensics) (1 tools)
- [metric_alerts](#metric_alerts) (3 tools)
- [metrics](#metrics) (1 tools)
- [misp_backend](#misp_backend) (1 tools)
- [model_compare](#model_compare) (2 tools)
- [model_consensus](#model_consensus) (1 tools)
- [model_fingerprinter](#model_fingerprinter) (1 tools)
- [model_sentiment](#model_sentiment) (1 tools)
- [multi_llm](#multi_llm) (1 tools)
- [multi_search](#multi_search) (1 tools)
- [multilang_attack](#multilang_attack) (3 tools)
- [neo4j_backend](#neo4j_backend) (3 tools)
- [network_map](#network_map) (2 tools)
- [network_persona](#network_persona) (1 tools)
- [neuromorphic](#neuromorphic) (1 tools)
- [nightcrawler](#nightcrawler) (2 tools)
- [nl_executor](#nl_executor) (1 tools)
- [nodriver_backend](#nodriver_backend) (3 tools)
- [notifications](#notifications) (3 tools)
- [observability](#observability) (3 tools)
- [onion_discover](#onion_discover) (1 tools)
- [onion_spectra](#onion_spectra) (2 tools)
- [onionscan_backend](#onionscan_backend) (1 tools)
- [openapi_gen](#openapi_gen) (2 tools)
- [opencti_backend](#opencti_backend) (1 tools)
- [osint_extended](#osint_extended) (2 tools)
- [output_diff](#output_diff) (2 tools)
- [output_formatter](#output_formatter) (2 tools)
- [p3_tools](#p3_tools) (4 tools)
- [paddleocr_backend](#paddleocr_backend) (1 tools)
- [paradox_detector](#paradox_detector) (2 tools)
- [parallel_executor](#parallel_executor) (2 tools)
- [param_sweep](#param_sweep) (1 tools)
- [passive_recon](#passive_recon) (1 tools)
- [pathogen_sim](#pathogen_sim) (1 tools)
- [pdf_extract](#pdf_extract) (2 tools)
- [pentest](#pentest) (5 tools)
- [pentest_prompts](#pentest_prompts) (1 tools)
- [persistent_memory](#persistent_memory) (3 tools)
- [persona_profile](#persona_profile) (1 tools)
- [pg_store](#pg_store) (2 tools)
- [photon_backend](#photon_backend) (1 tools)
- [pipeline_enhancer](#pipeline_enhancer) (4 tools)
- [plugin_loader](#plugin_loader) (3 tools)
- [polyglot_scraper](#polyglot_scraper) (2 tools)
- [potency_meter](#potency_meter) (1 tools)
- [predictive_ranker](#predictive_ranker) (1 tools)
- [privacy_advanced](#privacy_advanced) (14 tools)
- [privacy_tools](#privacy_tools) (8 tools)
- [proactive_defense](#proactive_defense) (2 tools)
- [progress_tracker](#progress_tracker) (3 tools)
- [projectdiscovery](#projectdiscovery) (4 tools)
- [prompt_analyzer](#prompt_analyzer) (1 tools)
- [prompt_compression](#prompt_compression) (3 tools)
- [prompt_reframe](#prompt_reframe) (9 tools)
- [prompt_templates](#prompt_templates) (3 tools)
- [provider_health](#provider_health) (3 tools)
- [psycholinguistic](#psycholinguistic) (1 tools)
- [pydantic_ai_backend](#pydantic_ai_backend) (2 tools)
- [quality_escalation](#quality_escalation) (1 tools)
- [query_builder](#query_builder) (1 tools)
- [queue_monitor](#queue_monitor) (1 tools)
- [quota_status](#quota_status) (1 tools)
- [radicalization_detect](#radicalization_detect) (1 tools)
- [rag_anything](#rag_anything) (3 tools)
- [rate_limiter_tool](#rate_limiter_tool) (3 tools)
- [realtime_adapt](#realtime_adapt) (2 tools)
- [realtime_monitor](#realtime_monitor) (1 tools)
- [reconng_backend](#reconng_backend) (1 tools)
- [redis_tools](#redis_tools) (2 tools)
- [redteam_hub](#redteam_hub) (3 tools)
- [reframe_router](#reframe_router) (1 tools)
- [reid_tactics](#reid_tactics) (1 tools)
- [replication_monitor](#replication_monitor) (2 tools)
- [report_generator](#report_generator) (2 tools)
- [report_templates](#report_templates) (2 tools)
- [request_queue](#request_queue) (3 tools)
- [research_journal](#research_journal) (3 tools)
- [research_scheduler](#research_scheduler) (3 tools)
- [resilience_predictor](#resilience_predictor) (1 tools)
- [response_cache](#response_cache) (3 tools)
- [response_synthesizer](#response_synthesizer) (1 tools)
- [result_aggregator](#result_aggregator) (2 tools)
- [resume_intel](#resume_intel) (2 tools)
- [resumption](#resumption) (3 tools)
- [retry_middleware](#retry_middleware) (2 tools)
- [retry_stats](#retry_stats) (1 tools)
- [robin_backend](#robin_backend) (1 tools)
- [router](#router) (1 tools)
- [rss_monitor](#rss_monitor) (2 tools)
- [safety_neurons](#safety_neurons) (2 tools)
- [safety_predictor](#safety_predictor) (1 tools)
- [salary_synthesizer](#salary_synthesizer) (1 tools)
- [sandbox](#sandbox) (2 tools)
- [sandbox_executor](#sandbox_executor) (2 tools)
- [scapy_backend](#scapy_backend) (1 tools)
- [scheduler_status](#scheduler_status) (1 tools)
- [schema_migrate](#schema_migrate) (3 tools)
- [scraper_engine_tools](#scraper_engine_tools) (3 tools)
- [screenshot](#screenshot) (1 tools)
- [search](#search) (1 tools)
- [security_checklist](#security_checklist) (1 tools)
- [security_headers](#security_headers) (1 tools)
- [semantic_cache_mgmt](#semantic_cache_mgmt) (2 tools)
- [semantic_index](#semantic_index) (2 tools)
- [semantic_router](#semantic_router) (3 tools)
- [sentiment_deep](#sentiment_deep) (1 tools)
- [session_replay](#session_replay) (3 tools)
- [sherlock_backend](#sherlock_backend) (2 tools)
- [shodan_backend](#shodan_backend) (2 tools)
- [signal_detection](#signal_detection) (3 tools)
- [silk_guardian](#silk_guardian) (1 tools)
- [simplifier](#simplifier) (1 tools)
- [singlefile_backend](#singlefile_backend) (1 tools)
- [sla_status](#sla_status) (1 tools)
- [slack](#slack) (1 tools)
- [smart_router](#smart_router) (3 tools)
- [social_analyzer_backend](#social_analyzer_backend) (1 tools)
- [social_graph](#social_graph) (1 tools)
- [social_graph_demo](#social_graph_demo) (1 tools)
- [social_intel](#social_intel) (2 tools)
- [social_scraper](#social_scraper) (3 tools)
- [source_reputation](#source_reputation) (1 tools)
- [spider](#spider) (2 tools)
- [spiderfoot_backend](#spiderfoot_backend) (1 tools)
- [stagehand_backend](#stagehand_backend) (2 tools)
- [startup_validator](#startup_validator) (1 tools)
- [stealth](#stealth) (2 tools)
- [stealth_detector](#stealth_detector) (1 tools)
- [stealth_score](#stealth_score) (1 tools)
- [stealth_scorer](#stealth_scorer) (1 tools)
- [stego_decoder](#stego_decoder) (1 tools)
- [stego_detect](#stego_detect) (1 tools)
- [stego_encoder](#stego_encoder) (2 tools)
- [strange_attractors](#strange_attractors) (1 tools)
- [strategy_ab_test](#strategy_ab_test) (2 tools)
- [strategy_cache](#strategy_cache) (1 tools)
- [strategy_evolution](#strategy_evolution) (1 tools)
- [strategy_feedback](#strategy_feedback) (3 tools)
- [strategy_oracle](#strategy_oracle) (1 tools)
- [stylometry](#stylometry) (1 tools)
- [supercookie_backend](#supercookie_backend) (1 tools)
- [superposition_prompt](#superposition_prompt) (1 tools)
- [supply_chain](#supply_chain) (2 tools)
- [supply_chain_intel](#supply_chain_intel) (3 tools)
- [swarm_attack](#swarm_attack) (1 tools)
- [synth_echo](#synth_echo) (1 tools)
- [synthetic_data](#synthetic_data) (2 tools)
- [talent_tracker](#talent_tracker) (2 tools)
- [task_resolver](#task_resolver) (2 tools)
- [telegram_osint](#telegram_osint) (1 tools)
- [telemetry](#telemetry) (3 tools)
- [tenant_isolation](#tenant_isolation) (3 tools)
- [testssl_backend](#testssl_backend) (1 tools)
- [text_analyze](#text_analyze) (1 tools)
- [thinking_injection](#thinking_injection) (2 tools)
- [threat_intel](#threat_intel) (7 tools)
- [threat_profile](#threat_profile) (1 tools)
- [threat_profile_demo](#threat_profile_demo) (1 tools)
- [tool_catalog](#tool_catalog) (4 tools)
- [tool_dependencies](#tool_dependencies) (3 tools)
- [tool_discovery](#tool_discovery) (1 tools)
- [tool_health](#tool_health) (3 tools)
- [tool_profiler](#tool_profiler) (2 tools)
- [tool_recommender_tool](#tool_recommender_tool) (1 tools)
- [tool_recommender_v2](#tool_recommender_v2) (2 tools)
- [tool_tags](#tool_tags) (3 tools)
- [tool_versioning](#tool_versioning) (3 tools)
- [topology_manifold](#topology_manifold) (1 tools)
- [tor](#tor) (2 tools)
- [toxicity_checker_tool](#toxicity_checker_tool) (1 tools)
- [traffic_capture](#traffic_capture) (2 tools)
- [transcribe](#transcribe) (1 tools)
- [transferability](#transferability) (1 tools)
- [trend_forecaster](#trend_forecaster) (1 tools)
- [trend_predictor](#trend_predictor) (1 tools)
- [uncertainty_harvest](#uncertainty_harvest) (2 tools)
- [unique_tools](#unique_tools) (8 tools)
- [universal_orchestrator](#universal_orchestrator) (1 tools)
- [unstructured_backend](#unstructured_backend) (1 tools)
- [urlhaus_lookup](#urlhaus_lookup) (2 tools)
- [usage_analytics](#usage_analytics) (3 tools)
- [usage_report](#usage_report) (1 tools)
- [usb_monitor_tool](#usb_monitor_tool) (1 tools)
- [vastai](#vastai) (2 tools)
- [vercel](#vercel) (1 tools)
- [vision_agent](#vision_agent) (2 tools)
- [vuln_intel](#vuln_intel) (1 tools)
- [webcheck_backend](#webcheck_backend) (1 tools)
- [webhook_system](#webhook_system) (3 tools)
- [webhooks](#webhooks) (4 tools)
- [white_rabbit](#white_rabbit) (1 tools)
- [workflow_engine](#workflow_engine) (3 tools)
- [workflow_expander](#workflow_expander) (2 tools)
- [workflow_templates](#workflow_templates) (2 tools)
- [xover_attack](#xover_attack) (2 tools)
- [yara_backend](#yara_backend) (1 tools)
- [ytdlp_backend](#ytdlp_backend) (3 tools)
- [zendriver_backend](#zendriver_backend) (3 tools)

---

## academic_integrity

### research_citation_analysis
**Module:** `src/loom/tools/academic_integrity.py` | **Type:** async

Analyze citation networks for anomalies using Semantic Scholar API.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `paper_id` | str | Yes | — |
| `depth` | int | No | `2` |

### research_predatory_journal_check
**Module:** `src/loom/tools/academic_integrity.py` | **Type:** async

Check if a journal shows signs of being predatory.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `journal_name` | str | Yes | — |

### research_retraction_check
**Module:** `src/loom/tools/academic_integrity.py` | **Type:** async

Check if papers/authors have retractions using Crossref and PubPeer.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `20` |

## access_tools

### research_content_authenticity
**Module:** `src/loom/tools/access_tools.py` | **Type:** async

Verify that content hasn't been modified using Wayback Machine.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

### research_credential_monitor
**Module:** `src/loom/tools/access_tools.py` | **Type:** async

Check if credentials have been exposed in known data breaches.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `target_type` | str | No | `"email"` |

### research_deepfake_checker
**Module:** `src/loom/tools/access_tools.py` | **Type:** async

Check image authenticity using EXIF analysis and Error Level Analysis.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `image_url` | str | Yes | — |

### research_legal_takedown
**Module:** `src/loom/tools/access_tools.py` | **Type:** async

Monitor legal takedowns against a domain.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

### research_open_access
**Module:** `src/loom/tools/access_tools.py` | **Type:** async

Find free/open-access versions of academic papers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `doi` | str | No | `""` |
| `title` | str | No | `""` |

## adversarial_craft

### research_adversarial_batch
**Module:** `src/loom/tools/adversarial_craft.py` | **Type:** async

Batch craft adversarial examples for multiple inputs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `inputs` | list[str] | Yes | — |
| `method` | str | No | `"greedy_swap"` |
| `budget` | float | No | `0.1` |

### research_craft_adversarial
**Module:** `src/loom/tools/adversarial_craft.py` | **Type:** async

Minimally perturb benign input to trigger target behavior from model.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `benign_input` | str | Yes | — |
| `target_output` | str | No | `"compliance"` |
| `perturbation_budget` | float | No | `0.1` |
| `method` | str | No | `"greedy_swap"` |

## adversarial_debate_tool

### research_adversarial_debate
**Module:** `src/loom/tools/adversarial_debate_tool.py` | **Type:** async

Simulate multi-turn adversarial debate: attacker vs target model.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `attacker_strategy` | str | No | `"auto"` |
| `max_turns` | int | No | `5` |
| `target_model` | str | No | `"nvidia"` |

## agent_benchmark

### research_agent_benchmark
**Module:** `src/loom/tools/agent_benchmark.py` | **Type:** async

Benchmark an AI agent against 20 agentic prompt injection scenarios.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model_api_url` | str | Yes | — |
| `model_name` | str | No | `""` |
| `timeout` | float | No | `30.0` |
| `output_format` | str | No | `"summary"` |

## ai_safety

### research_bias_probe
**Module:** `src/loom/tools/ai_safety.py` | **Type:** sync

Test an LLM API for demographic bias.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `categories` | list[str] | None | No | None |

### research_domain_compliance_check
**Module:** `src/loom/tools/ai_safety.py` | **Type:** sync

Check a website domain for AI compliance indicators (vs research_compliance_check which checks text).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `frameworks` | list[str] | None | No | None |

### research_model_fingerprint
**Module:** `src/loom/tools/ai_safety.py` | **Type:** sync

Identify which LLM model is behind an API endpoint.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `probes` | int | No | `5` |

### research_prompt_injection_test
**Module:** `src/loom/tools/ai_safety.py` | **Type:** sync

Test a target LLM API for prompt injection vulnerabilities.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `model_name` | str | No | `""` |
| `test_count` | int | No | `10` |

### research_safety_filter_map
**Module:** `src/loom/tools/ai_safety.py` | **Type:** sync

Map safety filter boundaries of an LLM API.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `categories` | list[str] | None | No | None |

## ai_safety_extended

### research_adversarial_robustness
**Module:** `src/loom/tools/ai_safety_extended.py` | **Type:** async

Test model robustness against adversarial inputs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `test_count` | int | No | `5` |

### research_hallucination_benchmark
**Module:** `src/loom/tools/ai_safety_extended.py` | **Type:** async

Test a model for hallucination via fact-checking.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `facts` | list[str] | None | No | None |

## anomaly_detector

### research_detect_anomalies
**Module:** `src/loom/tools/anomaly_detector.py` | **Type:** async

Detect numerical anomalies using zscore, iqr, or isolation methods.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `data` | list[float] | Yes | — |
| `method` | str | No | `"zscore"` |
| `threshold` | float | No | `2.0` |

### research_detect_text_anomalies
**Module:** `src/loom/tools/anomaly_detector.py` | **Type:** async

Detect unusual text patterns (length, vocabulary, structure, encoding).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `texts` | list[str] | Yes | — |
| `baseline` | str | No | `""` |

## antiforensics

### research_forensics_cleanup
**Module:** `src/loom/tools/antiforensics.py` | **Type:** sync

List forensic artifacts that WOULD be cleaned (dry-run only for safety).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_paths` | list[str] | None | No | None |
| `os_type` | str | None | No | None |

### research_usb_kill_monitor
**Module:** `src/loom/tools/antiforensics.py` | **Type:** sync

Monitor USB device connections and optionally trigger protective actions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `trigger_action` | str | No | `"alert"` |
| `target_path` | str | No | `"/tmp"` |
| `dry_run` | bool | No | `True` |

## api_fuzzer

### research_fuzz_api
**Module:** `src/loom/tools/api_fuzzer.py` | **Type:** async

Fuzz API endpoints to discover vulnerabilities.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `base_url` | str | Yes | — |
| `endpoint` | str | No | `"/"` |
| `method` | str | No | `"GET"` |
| `fuzz_params` | dict[str, Any] | None | No | None |
| `iterations` | int | No | `100` |
| `authorized` | bool | No | `False` |

### research_fuzz_report
**Module:** `src/loom/tools/api_fuzzer.py` | **Type:** async

Summarize fuzzing results into a security report.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `results` | dict[str, Any] | None | No | None |

## api_version

### research_api_changelog
**Module:** `src/loom/tools/api_version.py` | **Type:** async

Return changelog of features added/changed between versions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `since_version` | str | No | `"3.0.0"` |

### research_api_deprecations
**Module:** `src/loom/tools/api_version.py` | **Type:** async

List deprecated tools/features scheduled for removal.

*No parameters*

### research_api_version
**Module:** `src/loom/tools/api_version.py` | **Type:** async

Return current API version info with system metadata.

*No parameters*

## arxiv_pipeline

### research_arxiv_extract_techniques
**Module:** `src/loom/tools/arxiv_pipeline.py` | **Type:** async

Extract actionable attack techniques from a paper abstract.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `paper_abstract` | str | Yes | — |
| `paper_title` | str | No | `""` |

### research_arxiv_ingest
**Module:** `src/loom/tools/arxiv_pipeline.py` | **Type:** async

Search arXiv for recent papers on jailbreaking/red-teaming/prompt injection.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `keywords` | list[str] | None | No | None |
| `days_back` | int | No | `7` |
| `max_papers` | int | No | `20` |

## ask_all_models

### research_ask_all_models
**Module:** `src/loom/tools/ask_all_models.py` | **Type:** async

Send a prompt to ALL available AI models and compare responses.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `models` | list[str] | None | No | None |
| `max_tokens` | int | No | `1000` |
| `auto_reframe` | bool | No | `True` |
| `include_clis` | bool | No | `False` |
| `timeout` | int | No | `60` |

## attack_economy

### research_economy_balance
**Module:** `src/loom/tools/attack_economy.py` | **Type:** async

Check credit balance and transaction history.

*No parameters*

### research_economy_leaderboard
**Module:** `src/loom/tools/attack_economy.py` | **Type:** async

Show top strategies by credits earned.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `top_n` | int | No | `10` |

### research_economy_submit
**Module:** `src/loom/tools/attack_economy.py` | **Type:** async

Submit discovered exploit to earn credits.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy_name` | str | Yes | — |
| `target_model` | str | Yes | — |
| `asr` | float | Yes | — |
| `description` | str | No | `""` |

## audit_log

### research_audit_export
**Module:** `src/loom/tools/audit_log.py` | **Type:** async

Export audit trail for compliance review.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `format` | str | No | `"jsonl"` |
| `days` | int | No | `7` |

### research_audit_log_query
**Module:** `src/loom/tools/audit_log.py` | **Type:** async

Query audit trail entries with filtering and time window.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool` | str | No | `""` |
| `caller` | str | No | `""` |
| `since_hours` | int | No | `24` |
| `limit` | int | No | `100` |

### research_audit_record
**Module:** `src/loom/tools/audit_log.py` | **Type:** async

Record an audit trail entry for a tool call.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `params` | dict | None | No | None |
| `result_summary` | str | No | `""` |
| `caller` | str | No | `"anonymous"` |
| `duration_ms` | float | No | `0` |

## audit_query

### research_audit_query
**Module:** `src/loom/tools/audit_query.py` | **Type:** async

Query audit log entries by tool name and time range.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | No | `""` |
| `hours` | int | No | `24` |
| `limit` | int | No | `100` |

### research_audit_stats
**Module:** `src/loom/tools/audit_query.py` | **Type:** async

Generate audit statistics for compliance reporting.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `hours` | int | No | `24` |

## auto_docs

### research_docs_coverage
**Module:** `src/loom/tools/auto_docs.py` | **Type:** async

Report documentation coverage for all tools.

*No parameters*

### research_generate_docs
**Module:** `src/loom/tools/auto_docs.py` | **Type:** async

Generate auto-documentation for all registered tools.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `output_format` | str | No | `"markdown"` |
| `include_params` | bool | No | `True` |

## auto_experiment

### research_experiment_design
**Module:** `src/loom/tools/auto_experiment.py` | **Type:** async

Design experiment plan: variables, sample size, expected power, execution steps.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `research_question` | str | Yes | — |
| `budget` | int | No | `50` |

### research_run_experiment
**Module:** `src/loom/tools/auto_experiment.py` | **Type:** async

Run controlled experiment: control vs treatments, measure effect size & significance.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `hypothesis` | str | Yes | — |
| `variables` | list[str] | None | No | None |
| `trials` | int | No | `10` |
| `metric` | str | No | `"success_rate"` |

## auto_params

### research_auto_params
**Module:** `src/loom/tools/auto_params.py` | **Type:** async

Auto-infer tool parameters from natural language query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `query` | str | Yes | — |

### research_inspect_tool
**Module:** `src/loom/tools/auto_params.py` | **Type:** async

Return full signature info for a tool.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |

## auto_pipeline

### research_auto_pipeline
**Module:** `src/loom/tools/auto_pipeline.py` | **Type:** async

Auto-generate optimal multi-tool pipeline from a natural language goal.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `goal` | str | Yes | — |
| `max_steps` | int | No | `7` |
| `optimize_for` | str | No | `"quality"` |

## auto_report

### research_auto_report
**Module:** `src/loom/tools/auto_report.py` | **Type:** async

Generate a structured intelligence report on a given topic.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `depth` | Literal['brief', 'standard', 'compreh... | No | `"standard"` |
| `format` | Literal['markdown', 'json', 'html'] | No | `"markdown"` |
| `search_provider` | str | None | No | None |
| `num_sources` | int | None | No | None |
| `include_methodology` | bool | No | `True` |
| `include_recommendations` | bool | No | `True` |

### research_report_from_results
**Module:** `src/loom/tools/auto_report.py` | **Type:** async

Generate a report from pre-existing research results.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `results` | list[dict[str, Any]] | Yes | — |
| `title` | str | Yes | — |
| `depth` | Literal['brief', 'standard', 'compreh... | No | `"standard"` |
| `format` | Literal['markdown', 'json', 'html'] | No | `"markdown"` |
| `include_methodology` | bool | No | `True` |
| `include_recommendations` | bool | No | `True` |

## autonomous_agent

### research_auto_redteam
**Module:** `src/loom/tools/autonomous_agent.py` | **Type:** async

Automatically test strategies against a target model.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_model` | str | No | `"nvidia"` |
| `strategies_to_test` | int | No | `10` |
| `topic` | str | No | `"general"` |

### research_schedule_redteam
**Module:** `src/loom/tools/autonomous_agent.py` | **Type:** sync

Schedule periodic red-team testing.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `interval_hours` | int | No | `24` |
| `target_model` | str | No | `"all"` |

## backoff_dlq

### research_backoff_dlq_list
**Module:** `src/loom/tools/backoff_dlq.py` | **Type:** async

List items in the Dead Letter Queue.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `status` | str | No | `"pending"` |

### research_dlq_push
**Module:** `src/loom/tools/backoff_dlq.py` | **Type:** async

Push failed tool call to Dead Letter Queue.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `params` | dict[str, Any] | Yes | — |
| `error` | str | Yes | — |
| `retry_count` | int | No | `0` |

### research_dlq_retry
**Module:** `src/loom/tools/backoff_dlq.py` | **Type:** async

Retry DLQ items by ID or all pending items past next_retry time.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `item_id` | str | No | `""` |

## backup_system

### research_backup_create
**Module:** `src/loom/tools/backup_system.py` | **Type:** async

Create a backup of Loom's persistent data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | No | `"all"` |

### research_backup_list
**Module:** `src/loom/tools/backup_system.py` | **Type:** async

List available backups with metadata.

*No parameters*

### research_backup_restore
**Module:** `src/loom/tools/backup_system.py` | **Type:** async

Restore from a backup.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `backup_id` | str | Yes | — |
| `target` | str | No | `"all"` |
| `dry_run` | bool | No | `True` |

## benchmark_datasets

### research_load_benchmark
**Module:** `src/loom/tools/benchmark_datasets.py` | **Type:** sync

Load benchmark prompts from standardized datasets.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `dataset` | str | No | `"harmbench"` |
| `category` | str | No | `""` |
| `limit` | int | No | `50` |

### research_run_benchmark
**Module:** `src/loom/tools/benchmark_datasets.py` | **Type:** async

Run benchmark evaluation on prompts with strategy + scoring.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `dataset` | str | No | `"harmbench"` |
| `strategy` | str | No | `"ethical_anchor"` |
| `limit` | int | No | `10` |

## benchmark_leaderboard

### research_benchmark_models
**Module:** `src/loom/tools/benchmark_leaderboard.py` | **Type:** async

Run standard benchmarks against LLM models.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `models` | list[str] | None | No | None |
| `categories` | list[str] | None | No | None |

### research_leaderboard_update
**Module:** `src/loom/tools/benchmark_leaderboard.py` | **Type:** sync

Add or update a score on the leaderboard.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |
| `category` | str | Yes | — |
| `score` | float | Yes | — |
| `details` | str | None | No | None |

### research_leaderboard_view
**Module:** `src/loom/tools/benchmark_leaderboard.py` | **Type:** sync

View current leaderboard rankings.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | None | No | None |
| `limit` | int | No | `20` |

## benchmark_suite

### research_benchmark_compare
**Module:** `src/loom/tools/benchmark_suite.py` | **Type:** async

Compare two tools head-to-head. Returns {tool_a: {mean_ms, p95_ms}, tool_b: {mean_ms, p95_ms}, winner, speedup_factor}.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_a` | str | Yes | — |
| `tool_b` | str | Yes | — |
| `iterations` | int | No | `20` |

### research_benchmark_run
**Module:** `src/loom/tools/benchmark_suite.py` | **Type:** async

Benchmark tool execution speed. Returns {tools_benchmarked, results: [{tool, iterations, min_ms, max_ms, mean_ms, p50_ms, p95_ms}], total_time_ms}.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tools` | list[str] | None | No | None |
| `iterations` | int | No | `10` |
| `warmup` | int | No | `2` |

## bias_lens

### research_bias_lens
**Module:** `src/loom/tools/bias_lens.py` | **Type:** async

Detect methodological bias in academic papers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `paper_id` | str | No | `""` |
| `text` | str | No | `""` |

## billing

### research_stripe_balance
**Module:** `src/loom/tools/billing.py` | **Type:** async

Get Stripe account balance.

*No parameters*

## bpj

### research_bpj_generate
**Module:** `src/loom/tools/bpj.py` | **Type:** async

Generate boundary points for safety classifier testing.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `safe_prompt` | str | Yes | — |
| `unsafe_prompt` | str | Yes | — |
| `max_steps` | int | No | `10` |
| `model_name` | str | No | `"test-model"` |
| `mode` | str | No | `"find_boundary"` |
| `perturbations` | int | No | `20` |

## breach_check

### research_breach_check
**Module:** `src/loom/tools/breach_check.py` | **Type:** async

Check if an email appears in known data breaches.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `email` | str | Yes | — |

### research_password_check
**Module:** `src/loom/tools/breach_check.py` | **Type:** async

Check if a password appears in known password breaches using k-anonymity.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `password` | str | Yes | — |

## cache_mgmt

### research_cache_clear
**Module:** `src/loom/tools/cache_mgmt.py` | **Type:** sync

Remove cache entries older than N days.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `older_than_days` | int | None | No | None |

### research_cache_stats
**Module:** `src/loom/tools/cache_mgmt.py` | **Type:** sync

Return cache statistics.

*No parameters*

## cache_optimizer

### research_cache_analyze
**Module:** `src/loom/tools/cache_optimizer.py` | **Type:** async

Analyze cache performance metrics.

*No parameters*

### research_cache_optimize
**Module:** `src/loom/tools/cache_optimizer.py` | **Type:** async

Optimize cache usage and return statistics.

*No parameters*

## camelot_backend

### research_table_extract
**Module:** `src/loom/tools/camelot_backend.py` | **Type:** async

Extract tables from PDF using Camelot.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `pdf_url` | str | No | `""` |
| `pdf_path` | str | No | `""` |
| `pages` | str | No | `"all"` |

## capability_matrix

### research_capability_matrix
**Module:** `src/loom/tools/capability_matrix.py` | **Type:** async

Analyze all tool functions by input/output type.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | No | `"all"` |

### research_find_tools_by_capability
**Module:** `src/loom/tools/capability_matrix.py` | **Type:** async

Filter capability matrix by input type, category, network requirement, or speed.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `input_type` | str | No | `""` |
| `category` | str | No | `""` |
| `requires_network` | bool | None | No | None |
| `speed` | str | No | `""` |

## career_intel

### research_map_research_to_product
**Module:** `src/loom/tools/career_intel.py` | **Type:** async

Map PhD research expertise to commercial products and companies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `research_description` | str | Yes | — |
| `n` | int | No | `10` |

### research_translate_academic_skills
**Module:** `src/loom/tools/career_intel.py` | **Type:** async

Translate academic CV language to industry terminology.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `cv_text` | str | Yes | — |
| `job_description` | str | Yes | — |

## career_trajectory

### research_career_trajectory
**Module:** `src/loom/tools/career_trajectory.py` | **Type:** async

Build a career trajectory profile by combining multiple data sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `person_name` | str | Yes | — |
| `domain` | str | No | `""` |

### research_market_velocity
**Module:** `src/loom/tools/career_trajectory.py` | **Type:** async

Measure how fast a skill/technology is growing in the job market.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `skill` | str | Yes | — |
| `location` | str | No | `"remote"` |

## censys_backend

### research_censys_host
**Module:** `src/loom/tools/censys_backend.py` | **Type:** async

Look up host on Censys — TLS certs, services, protocols.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `ip` | str | Yes | — |

### research_censys_search
**Module:** `src/loom/tools/censys_backend.py` | **Type:** async

Search Censys for hosts matching criteria.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `10` |

## cert_analyzer

### research_cert_analyze
**Module:** `src/loom/tools/cert_analyzer.py` | **Type:** async

Extract SSL/TLS certificate information from a remote server.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `hostname` | str | No | `""` |
| `domain` | str | No | `""` |
| `port` | int | No | `443` |

## chain_composer

### research_chain_define
**Module:** `src/loom/tools/chain_composer.py` | **Type:** async

Define a reusable tool chain (pipeline).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `steps` | list[dict] | Yes | — |

### research_chain_describe
**Module:** `src/loom/tools/chain_composer.py` | **Type:** async

Show details of a specific chain.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |

### research_chain_list
**Module:** `src/loom/tools/chain_composer.py` | **Type:** async

List all defined chains with metadata.

*No parameters*

## change_monitor

### research_change_monitor
**Module:** `src/loom/tools/change_monitor.py` | **Type:** sync

Monitor a web page for meaningful content changes.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `store_result` | bool | No | `True` |

## changelog_gen

### research_changelog_generate
**Module:** `src/loom/tools/changelog_gen.py` | **Type:** async

Generate changelog from git log with conventional commit parsing.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `since` | str | No | `"7d"` |
| `format` | str | No | `"markdown"` |

### research_changelog_stats
**Module:** `src/loom/tools/changelog_gen.py` | **Type:** async

Get git statistics for the project.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `days` | int | No | `30` |

## chronos

### research_chronos_reverse
**Module:** `src/loom/tools/chronos.py` | **Type:** async

Reverse-engineer causality chains from a described future breakthrough.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `future_state` | str | Yes | — |
| `domain` | str | No | `"technology"` |
| `steps_back` | int | No | `5` |

## cipher_mirror

### research_cipher_mirror
**Module:** `src/loom/tools/cipher_mirror.py` | **Type:** async

Monitor paste sites for leaked credentials and model weights.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `n` | int | No | `10` |
| `entropy_threshold` | float | No | `0.6` |
| `max_cost_usd` | float | No | `0.1` |

## circuit_breaker

### research_breaker_reset
**Module:** `src/loom/tools/circuit_breaker.py` | **Type:** async

Manually reset circuit(s) to CLOSED.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | str | No | `"all"` |

### research_breaker_status
**Module:** `src/loom/tools/circuit_breaker.py` | **Type:** async

Show circuit breaker state: {circuits: [{provider, state, failures, last_failure, cooldown_remaining_s}]}

*No parameters*

### research_breaker_trip
**Module:** `src/loom/tools/circuit_breaker.py` | **Type:** async

Record failure for provider. Open circuit if failures >= threshold (5).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | str | Yes | — |
| `error` | str | No | `""` |

## cli_autocomplete

### research_generate_completions
**Module:** `src/loom/tools/cli_autocomplete.py` | **Type:** async

Generate shell completion script for all Loom tools.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `shell` | str | No | `"zsh"` |

### research_tool_help
**Module:** `src/loom/tools/cli_autocomplete.py` | **Type:** async

Get detailed help for a specific tool.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |

## cloak_backend

### research_cloak_extract
**Module:** `src/loom/tools/cloak_backend.py` | **Type:** async

Extract structured data from URL using CloakBrowser stealth.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `css_selector` | str | No | `""` |
| `extract_links` | bool | No | `True` |
| `extract_images` | bool | No | `False` |
| `humanize` | bool | No | `True` |

### research_cloak_fetch
**Module:** `src/loom/tools/cloak_backend.py` | **Type:** async

Fetch URL with CloakBrowser stealth Chromium (passes all bot detection).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `wait_for` | str | No | `""` |
| `humanize` | bool | No | `True` |
| `timeout` | int | No | `30` |
| `screenshot` | bool | No | `False` |

### research_cloak_session
**Module:** `src/loom/tools/cloak_backend.py` | **Type:** async

Browse multiple URLs in one session (maintains cookies/state).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `humanize` | bool | No | `True` |
| `delay_between` | float | No | `1.5` |

## cluster_health

### research_cluster_health
**Module:** `src/loom/tools/cluster_health.py` | **Type:** async

Aggregate health status across all cluster nodes.

*No parameters*

### research_node_status
**Module:** `src/loom/tools/cluster_health.py` | **Type:** async

Get individual node status.

*No parameters*

## coevolution

### research_coevolve
**Module:** `src/loom/tools/coevolution.py` | **Type:** async

Co-evolve attacks and defenses discovering novel vectors.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `seed_attack` | str | Yes | — |
| `seed_defense` | str | No | `""` |
| `generations` | int | No | `10` |
| `population_size` | int | No | `20` |

## company_intel

### research_company_diligence
**Module:** `src/loom/tools/company_intel.py` | **Type:** async

Deep company analysis for job seekers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company_name` | str | Yes | — |

### research_salary_intelligence
**Module:** `src/loom/tools/company_intel.py` | **Type:** async

Aggregate salary data from multiple sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `role` | str | Yes | — |
| `location` | str | None | No | None |
| `experience_years` | int | No | `0` |

## competitive_intel

### research_competitive_intel
**Module:** `src/loom/tools/competitive_intel.py` | **Type:** async

Analyze company competitive positioning via weak signal fusion.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company` | str | Yes | — |
| `domain` | str | None | No | None |
| `github_org` | str | None | No | None |

## competitive_monitor

### research_competitive_advantage
**Module:** `src/loom/tools/competitive_monitor.py` | **Type:** sync

Compare Loom capabilities vs known competitors.

*No parameters*

### research_monitor_competitors
**Module:** `src/loom/tools/competitive_monitor.py` | **Type:** async

Monitor GitHub competitors for activity and positioning.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `competitors` | list[str] | None | No | None |

## compliance_checker

### research_compliance_check
**Module:** `src/loom/tools/compliance_checker.py` | **Type:** sync

Check text against compliance frameworks (EU AI Act, GDPR, OWASP, NIST, HIPAA).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `frameworks` | list[str] | None | No | None |

### research_pii_scan
**Module:** `src/loom/tools/compliance_checker.py` | **Type:** sync

Scan for PII: email, phone, SSN, credit card, IP address.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

## compliance_report

### research_audit_trail
**Module:** `src/loom/tools/compliance_report.py` | **Type:** sync

Retrieve audit trail entries, filtered by tool name.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | No | `""` |
| `limit` | int | No | `100` |

### research_compliance_report
**Module:** `src/loom/tools/compliance_report.py` | **Type:** sync

Generate compliance report for specified framework.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `period_days` | int | No | `30` |
| `framework` | str | No | `"eu_ai_act"` |

## composer

### research_compose
**Module:** `src/loom/tools/composer.py` | **Type:** async

Execute a composed pipeline of research tools.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `pipeline` | str | Yes | — |
| `initial_input` | str | No | `""` |
| `continue_on_error` | bool | No | `False` |
| `timeout_ms` | int | None | No | None |

### research_compose_validate
**Module:** `src/loom/tools/composer.py` | **Type:** sync

Validate pipeline syntax without executing.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `pipeline` | str | Yes | — |

### research_merge
**Module:** `src/loom/tools/composer.py` | **Type:** async

Merge multiple parallel results into a single structure.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `arg0` | dict[str, Any] | None | No | None |
| `kwargs` | Any | Yes | — |

## composition_optimizer

### research_optimize_workflow
**Module:** `src/loom/tools/composition_optimizer.py` | **Type:** async

Find optimal tool combination for research goal.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `goal` | str | Yes | — |
| `available_tools` | list[str] | None | No | None |
| `optimize_for` | str | No | `"speed"` |

### research_optimizer_rebuild
**Module:** `src/loom/tools/composition_optimizer.py` | **Type:** async

Force rebuild of auto-generated tool metadata cache.

*No parameters*

### research_parallel_plan
**Module:** `src/loom/tools/composition_optimizer.py` | **Type:** async

Determine parallel vs sequential execution plan.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tools` | list[str] | Yes | — |

## config_reload

### research_config_check
**Module:** `src/loom/tools/config_reload.py` | **Type:** sync

Check if config has changed since watch started and reload if needed.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `config_path` | str | None | No | None |

### research_config_diff
**Module:** `src/loom/tools/config_reload.py` | **Type:** sync

Show what changed between old and new config.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `key` | str | No | `""` |

### research_config_watch
**Module:** `src/loom/tools/config_reload.py` | **Type:** sync

Start watching config.json for modifications.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `config_path` | str | None | No | None |

## consistency_pressure

### research_consistency_pressure
**Module:** `src/loom/tools/consistency_pressure.py` | **Type:** async

Build a prompt with consistency pressure references.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |
| `target_prompt` | str | Yes | — |
| `max_references` | int | No | `5` |

### research_consistency_pressure_history
**Module:** `src/loom/tools/consistency_pressure.py` | **Type:** async

Get model's compliance history and stats.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |

### research_consistency_pressure_record
**Module:** `src/loom/tools/consistency_pressure.py` | **Type:** async

Record a model's response for future pressure building.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |
| `prompt` | str | Yes | — |
| `response` | str | Yes | — |
| `complied` | bool | Yes | — |

## constraint_optimizer

### research_attack_score
**Module:** `src/loom/tools/constraint_optimizer.py` | **Type:** sync

Score attack effectiveness across 8 dimensions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `response` | str | Yes | — |
| `strategy` | str | No | `""` |
| `model` | str | No | `""` |
| `baseline_refusal` | bool | No | `True` |

### research_constraint_optimize
**Module:** `src/loom/tools/constraint_optimizer.py` | **Type:** async

Find reframed prompt satisfying multiple constraints simultaneously.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `constraints` | dict[str, dict[str, float]] | None | No | None |
| `max_iterations` | int | No | `20` |
| `target_model` | str | No | `"auto"` |

## content_anomaly

### research_content_anomaly
**Module:** `src/loom/tools/content_anomaly.py` | **Type:** sync

MCP tool wrapper for content anomaly detection.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `expected_snippet` | str | Yes | — |
| `actual_content` | str | Yes | — |

## context_manager

### research_context_clear
**Module:** `src/loom/tools/context_manager.py` | **Type:** async

Clear context variables.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `scope` | Literal['session', 'persistent', 'all'] | No | `"session"` |

### research_context_get
**Module:** `src/loom/tools/context_manager.py` | **Type:** async

Get context variable(s).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `key` | str | No | `""` |

### research_context_set
**Module:** `src/loom/tools/context_manager.py` | **Type:** async

Set a context variable.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `key` | str | Yes | — |
| `value` | str | Yes | — |
| `scope` | Literal['session', 'persistent'] | No | `"session"` |

## cost_estimator

### research_cost_summary
**Module:** `src/loom/tools/cost_estimator.py` | **Type:** async

Summarize estimated costs accumulated across tool calls.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `period` | str | No | `"today"` |

## creative

### research_ai_detect
**Module:** `src/loom/tools/creative.py` | **Type:** async

Detect whether text is likely AI-generated.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `max_cost_usd` | float | No | `0.02` |

### research_citation_graph
**Module:** `src/loom/tools/creative.py` | **Type:** async

DEPRECATED: Use research_graph(action="extract", ...) instead.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `paper_query` | str | Yes | — |
| `depth` | int | No | `1` |
| `max_papers` | int | No | `10` |

### research_community_sentiment
**Module:** `src/loom/tools/creative.py` | **Type:** async

Get practitioner sentiment from HackerNews and Reddit.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `n` | int | No | `5` |

### research_consensus
**Module:** `src/loom/tools/creative.py` | **Type:** async

Run query across all search engines, score results by consensus.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `providers` | list[str] | None | No | None |
| `n` | int | No | `10` |

### research_curriculum
**Module:** `src/loom/tools/creative.py` | **Type:** async

Generate a multi-level learning path from ELI5 to PhD.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `max_cost_usd` | float | No | `0.1` |

### research_misinfo_check
**Module:** `src/loom/tools/creative.py` | **Type:** async

Stress test a claim by generating false variants and checking sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `claim` | str | Yes | — |
| `n_sources` | int | No | `5` |
| `max_cost_usd` | float | No | `0.05` |

### research_multilingual
**Module:** `src/loom/tools/creative.py` | **Type:** async

Search in multiple languages for cross-lingual information arbitrage.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `languages` | list[str] | None | No | None |
| `n_per_lang` | int | No | `3` |
| `max_cost_usd` | float | No | `0.1` |

### research_red_team
**Module:** `src/loom/tools/creative.py` | **Type:** async

Generate and search for counter-arguments to a claim.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `claim` | str | Yes | — |
| `n_counter` | int | No | `3` |
| `max_cost_usd` | float | No | `0.1` |

### research_semantic_sitemap
**Module:** `src/loom/tools/creative.py` | **Type:** async

Crawl a domain's sitemap, cluster pages by semantic similarity,

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `max_pages` | int | No | `50` |
| `cluster_threshold` | float | No | `0.85` |

### research_temporal_diff
**Module:** `src/loom/tools/creative.py` | **Type:** async

Compare current page content with Wayback Machine archived version.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `max_cost_usd` | float | No | `0.05` |

### research_wiki_ghost
**Module:** `src/loom/tools/creative.py` | **Type:** async

Mine Wikipedia talk pages and edit history for contested knowledge.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `language` | str | No | `"en"` |

## credential_vault

### research_vault_list
**Module:** `src/loom/tools/credential_vault.py` | **Type:** async

List all stored credentials (names only, never values).

*No parameters*

### research_vault_retrieve
**Module:** `src/loom/tools/credential_vault.py` | **Type:** async

Retrieve and decrypt a credential from the vault.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |

### research_vault_store
**Module:** `src/loom/tools/credential_vault.py` | **Type:** async

Store a credential securely in the vault.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `value` | str | Yes | — |
| `category` | str | No | `"api_key"` |

## creepjs_backend

### research_creepjs_audit
**Module:** `src/loom/tools/creepjs_backend.py` | **Type:** sync

Privacy baseline assessment using creepjs fingerprinting.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | No | `"https://creepjs.web.app"` |
| `headless` | bool | No | `True` |

## cross_domain

### research_cross_domain
**Module:** `src/loom/tools/cross_domain.py` | **Type:** async

Find deep analogies and collision insights between two unrelated domains.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain_a` | str | Yes | — |
| `domain_b` | str | Yes | — |
| `depth` | int | No | `3` |

## crypto_risk

### research_crypto_risk_score
**Module:** `src/loom/tools/crypto_risk.py` | **Type:** async

Evaluate cryptocurrency wallet risk.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `address` | str | Yes | — |
| `chain` | str | No | `"bitcoin"` |

## crypto_trace

### research_crypto_trace
**Module:** `src/loom/tools/crypto_trace.py` | **Type:** async

Trace cryptocurrency address activity using public blockchain APIs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `address` | str | Yes | — |
| `chain` | str | No | `"auto"` |
| `include_transactions` | bool | No | `True` |

## cultural_attacks

### research_cultural_reframe
**Module:** `src/loom/tools/cultural_attacks.py` | **Type:** async

Reframe prompts using culture-specific persuasion patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `culture` | str | No | `"auto"` |
| `language` | str | No | `"en"` |

### research_multilingual_attack
**Module:** `src/loom/tools/cultural_attacks.py` | **Type:** async

Apply multilingual attack techniques to bypass safety filters.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `technique` | str | No | `"code_switch"` |
| `languages` | list[str] | None | No | None |

## culture_dna

### research_culture_dna
**Module:** `src/loom/tools/culture_dna.py` | **Type:** async

Analyze company culture from public signals.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company` | str | Yes | — |
| `domain` | str | No | `""` |

## cve_lookup

### research_cve_detail
**Module:** `src/loom/tools/cve_lookup.py` | **Type:** async

Get detailed information for a specific CVE.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `cve_id` | str | Yes | — |

### research_cve_lookup
**Module:** `src/loom/tools/cve_lookup.py` | **Type:** async

Search CVE database using NVD API (free, rate limited).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `limit` | int | No | `10` |

## cyberscraper

### research_paginate_scrape
**Module:** `src/loom/tools/cyberscraper.py` | **Type:** async

Multi-page scraping with auto-pagination detection.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `query` | str | Yes | — |
| `page_range` | str | No | `"1-5"` |
| `auto_detect_pattern` | bool | No | `True` |
| `model` | Literal['auto', 'groq', 'nvidia_nim',... | No | `"auto"` |
| `max_chars_per_page` | int | No | `30000` |
| `timeout` | int | No | `30` |

### research_smart_extract
**Module:** `src/loom/tools/cyberscraper.py` | **Type:** async

Fetch URL with stealth browser + LLM-powered structured extraction.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `query` | str | Yes | — |
| `model` | Literal['auto', 'groq', 'nvidia_nim',... | No | `"auto"` |
| `max_chars` | int | No | `50000` |
| `timeout` | int | No | `30` |
| `cache_key` | str | None | No | None |

### research_stealth_browser
**Module:** `src/loom/tools/cyberscraper.py` | **Type:** async

Pure Patchright stealth fetch — no LLM extraction.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `wait_for` | Literal['domcontentloaded', 'load', '... | No | `"load"` |
| `screenshot` | bool | No | `False` |
| `timeout` | int | No | `30` |
| `max_chars` | int | No | `50000` |

## cyberscraper_backend

### research_cyberscrape
**Module:** `src/loom/tools/cyberscraper_backend.py` | **Type:** async

Scrape web content using CyberScraper-2077's AI-powered extraction.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `extract_type` | str | No | `"all"` |
| `model` | str | No | `"gpt-4o-mini"` |
| `format` | str | No | `"json"` |
| `max_chars` | int | No | `20000` |
| `use_tor` | bool | No | `False` |
| `stealth_mode` | bool | No | `False` |
| `use_local_browser` | bool | No | `False` |
| `include_metadata` | bool | No | `True` |
| `timeout_seconds` | int | No | `30` |

### research_cyberscrape_direct
**Module:** `src/loom/tools/cyberscraper_backend.py` | **Type:** async

Direct CyberScraper extraction with custom prompt.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `extraction_prompt` | str | Yes | — |
| `model` | str | No | `"gpt-4o-mini"` |
| `timeout_seconds` | int | No | `30` |

## daisy_chain_tool

### research_daisy_chain
**Module:** `src/loom/tools/daisy_chain_tool.py` | **Type:** async

Execute query across multiple models via daisy-chain decomposition.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `available_models` | list[str] | None | No | None |
| `combiner_model` | str | No | `"gpt-4"` |
| `timeout_per_model` | float | No | `30.0` |
| `max_sub_queries` | int | No | `4` |
| `include_execution_trace` | bool | No | `False` |

## dark_forum

### research_dark_forum
**Module:** `src/loom/tools/dark_forum.py` | **Type:** async

Aggregate dark web forum intelligence from 4+ sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `50` |

## dark_recon

### research_amass_enum
**Module:** `src/loom/tools/dark_recon.py` | **Type:** sync

Attack surface mapping and asset discovery via OWASP Amass enum.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `passive` | bool | No | `True` |
| `timeout` | int | No | `120` |

### research_amass_intel
**Module:** `src/loom/tools/dark_recon.py` | **Type:** sync

OSINT intelligence gathering via OWASP Amass intel.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

### research_torbot
**Module:** `src/loom/tools/dark_recon.py` | **Type:** sync

Dark web OSINT crawling via TorBot subprocess.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `depth` | int | No | `2` |

## darkweb_early_warning

### research_darkweb_early_warning
**Module:** `src/loom/tools/darkweb_early_warning.py` | **Type:** async

Monitor dark web sources for early warning signals.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `keywords` | list[str] | Yes | — |
| `hours_back` | int | No | `72` |

## data_export

### research_export_cache
**Module:** `src/loom/tools/data_export.py` | **Type:** async

Export recent cache entries metadata (not content).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `limit` | int | No | `50` |

### research_export_config
**Module:** `src/loom/tools/data_export.py` | **Type:** async

Export current server configuration as JSON.

*No parameters*

### research_export_strategies
**Module:** `src/loom/tools/data_export.py` | **Type:** async

Export all reframing strategies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `format` | str | No | `"json"` |

## data_pipeline

### research_pipeline_create
**Module:** `src/loom/tools/data_pipeline.py` | **Type:** async

Create and store an ETL pipeline definition.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `stages` | list[dict[str, Any]] | Yes | — |

### research_pipeline_list
**Module:** `src/loom/tools/data_pipeline.py` | **Type:** async

List all defined pipelines.

*No parameters*

### research_pipeline_validate
**Module:** `src/loom/tools/data_pipeline.py` | **Type:** async

Validate pipeline definition.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |

## dead_content

### research_dead_content
**Module:** `src/loom/tools/dead_content.py` | **Type:** async

Query multiple archive/cache sources for deleted web content.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `include_snapshots` | bool | No | `True` |
| `max_sources` | int | No | `12` |

## dead_drop_scanner

### research_dead_drop_scanner
**Module:** `src/loom/tools/dead_drop_scanner.py` | **Type:** async

Probe ephemeral .onion sites and capture content with reuse detection.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `interval_minutes` | int | No | `5` |

## deception_detect

### research_deception_detect
**Module:** `src/loom/tools/deception_detect.py` | **Type:** async

Detect deceptive or fraudulent content using linguistic cues.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

## deception_job_scanner

### research_deception_job_scan
**Module:** `src/loom/tools/deception_job_scanner.py` | **Type:** sync

Analyze job posting for deception signals.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `job_url` | str | No | `""` |
| `job_text` | str | No | `""` |

## deep

### research_deep
**Module:** `src/loom/tools/deep.py` | **Type:** async

Full-pipeline deep research with dynamic provider selection.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `depth` | int | No | `2` |
| `include_domains` | list[str] | None | No | None |
| `exclude_domains` | list[str] | None | No | None |
| `start_date` | str | None | No | None |
| `end_date` | str | None | No | None |
| `language` | str | None | No | None |
| `provider_config` | dict[str, Any] | None | No | None |
| `search_providers` | list[str] | None | No | None |
| `expand_queries` | bool | No | `True` |
| `extract` | bool | No | `True` |
| `synthesize` | bool | No | `True` |
| `include_github` | bool | No | `True` |
| `include_community` | bool | No | `False` |
| `include_red_team` | bool | No | `False` |
| `include_misinfo_check` | bool | No | `False` |
| `max_cost_usd` | float | None | No | None |
| `allow_escalation` | bool | No | `True` |
| `provider_tier` | str | No | `"auto"` |
| `max_urls` | int | No | `10` |

## deep_research_agent

### research_hierarchical_research
**Module:** `src/loom/tools/deep_research_agent.py` | **Type:** async

Execute hierarchical multi-agent research on a query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `depth` | int | No | `2` |
| `max_sources` | int | No | `10` |
| `model` | str | No | `"nvidia"` |

## deep_url_analysis

### research_deep_url_analysis
**Module:** `src/loom/tools/deep_url_analysis.py` | **Type:** async

Force-find, fetch, and analyze multiple URLs with Gemini 1M context.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `num_urls` | int | No | `10` |
| `search_provider` | str | No | `"exa"` |
| `analysis_prompt` | str | No | `""` |
| `max_chars_per_url` | int | No | `50000` |
| `use_free_only` | bool | No | `False` |
| `model` | str | No | `"gemini-3.1-pro-preview"` |

## deepdarkcti_backend

### research_dark_cti
**Module:** `src/loom/tools/deepdarkcti_backend.py` | **Type:** sync

Aggregate dark web and public CTI feeds for threat intelligence.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `sources` | list[str] | None | No | None |
| `max_results` | int | No | `20` |

## deerflow_backend

### research_deer_flow
**Module:** `src/loom/tools/deerflow_backend.py` | **Type:** async

Run multi-agent research using DeerFlow orchestration.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `depth` | str | No | `"standard"` |
| `max_agents` | int | No | `5` |
| `timeout` | int | No | `120` |

## defender_mode

### research_defend_test
**Module:** `src/loom/tools/defender_mode.py` | **Type:** async

Test system prompt defenses by simulating attacks (blue-team mode).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `system_prompt` | str | Yes | — |
| `attack_categories` | list[str] | None | No | None |
| `num_attacks` | int | No | `20` |

### research_harden_prompt
**Module:** `src/loom/tools/defender_mode.py` | **Type:** async

Suggest hardening improvements for a system prompt.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `system_prompt` | str | Yes | — |
| `vulnerabilities` | list[str] | None | No | None |

## demo_decorator_usage

### research_code_analysis_demo
**Module:** `src/loom/tools/demo_decorator_usage.py` | **Type:** async

Perform static security analysis on code.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `code_snippet` | str | Yes | — |
| `language` | str | No | `"python"` |
| `severity_filter` | str | No | `"all"` |

### research_data_transform_demo
**Module:** `src/loom/tools/demo_decorator_usage.py` | **Type:** async

Transform data between formats with optional transformations.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `input_format` | str | Yes | — |
| `output_format` | str | Yes | — |
| `transformation` | str | Yes | — |
| `batch_size` | int | No | `1000` |

## dependency_graph

### research_dependency_graph
**Module:** `src/loom/tools/dependency_graph.py` | **Type:** async

Analyze tool modules to find inter-tool dependencies.

*No parameters*

### research_tool_impact
**Module:** `src/loom/tools/dependency_graph.py` | **Type:** async

Show what would break if a tool failed.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |

## deployment

### research_deploy_history
**Module:** `src/loom/tools/deployment.py` | **Type:** async

Show deployment history from ~/.loom/deploy_history.jsonl.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `limit` | int | No | `20` |

### research_deploy_record
**Module:** `src/loom/tools/deployment.py` | **Type:** async

Record deployment event to ~/.loom/deploy_history.jsonl with file locking.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `commit_hash` | str | No | `""` |
| `tool_count` | int | No | `0` |
| `duration_seconds` | float | No | `0` |
| `status` | str | No | `"success"` |

### research_deploy_status
**Module:** `src/loom/tools/deployment.py` | **Type:** async

Check deployment status: service, port, uptime, memory, health.

*No parameters*

## discord_osint

### research_discord_intel
**Module:** `src/loom/tools/discord_osint.py` | **Type:** async

Gather OSINT intelligence on Discord public servers and invites.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `server_id` | str | No | `""` |
| `invite_code` | str | No | `""` |
| `query` | str | No | `""` |

## dist_tracing

### research_trace_complete
**Module:** `src/loom/tools/dist_tracing.py` | **Type:** async

Complete a trace/span.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `trace_id` | str | Yes | — |
| `span_id` | str | No | `""` |
| `status` | str | No | `"ok"` |
| `metadata` | dict[str, Any] | None | No | None |

### research_trace_create
**Module:** `src/loom/tools/dist_tracing.py` | **Type:** async

Create a new trace span.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `operation` | str | Yes | — |
| `parent_trace_id` | str | No | `""` |

### research_trace_query
**Module:** `src/loom/tools/dist_tracing.py` | **Type:** async

Query completed traces.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `operation` | str | No | `""` |
| `limit` | int | No | `50` |
| `min_duration_ms` | float | No | `0` |

## dlq_management

### research_dlq_clear_failed
**Module:** `src/loom/tools/dlq_management.py` | **Type:** async

Clear permanently failed items older than specified days.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `days` | int | No | `30` |

### research_dlq_list
**Module:** `src/loom/tools/dlq_management.py` | **Type:** async

List deadletter queue items.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | None | No | None |
| `include_failed` | bool | No | `False` |

### research_dlq_retry_now
**Module:** `src/loom/tools/dlq_management.py` | **Type:** async

Force immediate retry of a deadletter queue item.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `dlq_id` | int | Yes | — |

### research_dlq_stats
**Module:** `src/loom/tools/dlq_management.py` | **Type:** async

Get deadletter queue statistics.

*No parameters*

## dns_server

### research_dns_query
**Module:** `src/loom/tools/dns_server.py` | **Type:** async

Perform DNS query for a domain.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

### research_dns_stats
**Module:** `src/loom/tools/dns_server.py` | **Type:** async

Get DNS query statistics.

*No parameters*

## do_expert

### research_do_expert
**Module:** `src/loom/tools/do_expert.py` | **Type:** async

Execute expert research from a single natural language instruction.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `instruction` | str | Yes | — |
| `quality` | str | No | `"expert"` |
| `darkness_level` | int | No | `5` |
| `max_time_secs` | int | No | `120` |

## docker_tools

### research_container_inspect
**Module:** `src/loom/tools/docker_tools.py` | **Type:** async

Inspect running Docker containers.

*No parameters*

### research_container_logs
**Module:** `src/loom/tools/docker_tools.py` | **Type:** async

Retrieve container logs.

*No parameters*

## docsgpt_backend

### research_docs_ai
**Module:** `src/loom/tools/docsgpt_backend.py` | **Type:** async

Query documentation using DocsGPT API.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `docs_url` | str | None | No | None |
| `timeout` | int | No | `30` |
| `language` | str | No | `"en"` |

## document

### research_convert_document
**Module:** `src/loom/tools/document.py` | **Type:** async

Convert documents (PDF, DOCX, HTML, etc.) to markdown or text.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `output_format` | str | No | `"markdown"` |

## domain_intel

### research_dns_lookup
**Module:** `src/loom/tools/domain_intel.py` | **Type:** async

DNS lookup for domain records.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `record_types` | list[str] | None | No | None |

### research_nmap_scan
**Module:** `src/loom/tools/domain_intel.py` | **Type:** async

Port scan using nmap.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `ports` | str | No | `"80,443,8080,8443"` |
| `scan_type` | str | No | `"basic"` |

### research_whois
**Module:** `src/loom/tools/domain_intel.py` | **Type:** async

Run whois lookup on a domain.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

## drift_monitor_tool

### research_drift_monitor
**Module:** `src/loom/tools/drift_monitor_tool.py` | **Type:** async

Monitor model behavioral drift over time.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompts` | list[str] | str | Yes | — |
| `model_name` | str | Yes | — |
| `mode` | str | No | `"check"` |
| `storage_path` | str | No | `"~/.loom/drift/"` |

### research_drift_monitor_list
**Module:** `src/loom/tools/drift_monitor_tool.py` | **Type:** async

List all stored drift monitor baselines by model.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `storage_path` | str | No | `"~/.loom/drift/"` |

## dspy_bridge

### research_dspy_configure
**Module:** `src/loom/tools/dspy_bridge.py` | **Type:** async

Configure DSPy to use Loom's LLM cascade for all calls.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | No | `"auto"` |
| `max_tokens` | int | No | `2000` |
| `temperature` | float | No | `0.3` |

### research_dspy_cost_report
**Module:** `src/loom/tools/dspy_bridge.py` | **Type:** async

Report DSPy's cumulative LLM usage through Loom's cascade.

*No parameters*

## eagleeye_backend

### research_reverse_image
**Module:** `src/loom/tools/eagleeye_backend.py` | **Type:** async

Perform reverse image search across multiple engines.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `image_url` | str | No | `""` |
| `image_path` | str | No | `""` |
| `engines` | list[str] | None | No | None |
| `timeout` | int | No | `30` |

## email_report

### research_email_report
**Module:** `src/loom/tools/email_report.py` | **Type:** async

Send research results via Gmail SMTP.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `to` | str | Yes | — |
| `subject` | str | Yes | — |
| `body` | str | Yes | — |
| `html` | bool | No | `False` |

## embedding_collision

### research_embedding_collide
**Module:** `src/loom/tools/embedding_collision.py` | **Type:** async

Craft text that collides in embedding space with hidden payload.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_text` | str | Yes | — |
| `malicious_payload` | str | Yes | — |
| `method` | Literal['synonym_swap', 'context_inje... | No | `"synonym_swap"` |

### research_rag_attack
**Module:** `src/loom/tools/embedding_collision.py` | **Type:** async

Generate poisoned document chunks for RAG system injection.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `attack_type` | Literal['retrieval_poison', 'synonym_... | No | `"retrieval_poison"` |
| `num_chunks` | int | No | `5` |

## enrich

### research_detect_language
**Module:** `src/loom/tools/enrich.py` | **Type:** sync

Detect the language of text content (free, no API key).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

### research_wayback
**Module:** `src/loom/tools/enrich.py` | **Type:** sync

Retrieve archived versions of a URL from the Wayback Machine (free).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `limit` | int | No | `1` |

## ensemble_attack

### research_attack_portfolio
**Module:** `src/loom/tools/ensemble_attack.py` | **Type:** async

Build diversified attack portfolio using portfolio theory.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_model` | str | No | `"auto"` |
| `portfolio_size` | int | No | `10` |

### research_ensemble_attack
**Module:** `src/loom/tools/ensemble_attack.py` | **Type:** async

Combine multiple attack techniques for adversarial robustness.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `strategies` | list[str] | None | No | None |
| `combination_method` | str | No | `"sequential"` |
| `max_strategies` | int | No | `5` |

## enterprise_sso

### research_sso_configure
**Module:** `src/loom/tools/enterprise_sso.py` | **Type:** async

Configure SSO provider settings.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | Literal['saml', 'oidc', 'oauth2', 'ld... | No | `"saml"` |
| `metadata_url` | str | No | `""` |
| `client_id` | str | No | `""` |

### research_sso_user_info
**Module:** `src/loom/tools/enterprise_sso.py` | **Type:** async

Extract user info from SSO token (JWT claims parsing).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `token` | str | Yes | — |

### research_sso_validate_token
**Module:** `src/loom/tools/enterprise_sso.py` | **Type:** async

Validate an SSO token (structure, expiry, signature format).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `token` | str | Yes | — |
| `provider` | Literal['saml', 'oidc', 'oauth2', 'ld... | No | `"auto"` |

## env_inspector

### research_env_inspect
**Module:** `src/loom/tools/env_inspector.py` | **Type:** async

Inspect the full runtime environment.

*No parameters*

### research_env_requirements
**Module:** `src/loom/tools/env_inspector.py` | **Type:** async

Check if all required dependencies are installed.

*No parameters*

## epistemic_score

### research_epistemic_score
**Module:** `src/loom/tools/epistemic_score.py` | **Type:** async

Score epistemic confidence for claims in text.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `claims_to_verify` | list[str] | None | No | None |

## error_wrapper

### research_error_clear
**Module:** `src/loom/tools/error_wrapper.py` | **Type:** async

Clear error history and reset tracking.

*No parameters*

### research_error_stats
**Module:** `src/loom/tools/error_wrapper.py` | **Type:** async

Get error statistics from all wrapped tools.

*No parameters*

## ethereum_tools

### research_defi_security_audit
**Module:** `src/loom/tools/ethereum_tools.py` | **Type:** async

Audit DeFi smart contract for vulnerabilities.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `contract_address` | str | Yes | — |

### research_ethereum_tx_decode
**Module:** `src/loom/tools/ethereum_tools.py` | **Type:** async

Decode Ethereum transaction from etherscan.io.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tx_hash` | str | Yes | — |

## eu_ai_act

### research_ai_bias_audit
**Module:** `src/loom/tools/eu_ai_act.py` | **Type:** sync

Compare responses across demographic groups for bias patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompts` | list[str] | Yes | — |
| `responses` | list[str] | Yes | — |

### research_ai_data_governance
**Module:** `src/loom/tools/eu_ai_act.py` | **Type:** sync

Assess data handling practices against EU AI Act requirements.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `system_description` | str | Yes | — |

### research_ai_risk_classify
**Module:** `src/loom/tools/eu_ai_act.py` | **Type:** sync

Classify AI system risk level per EU AI Act Annex III tiers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `system_description` | str | Yes | — |

### research_ai_robustness_test
**Module:** `src/loom/tools/eu_ai_act.py` | **Type:** sync

Test model consistency across rephrased and similar inputs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model_name` | str | Yes | — |
| `test_prompts` | list[str] | Yes | — |

### research_ai_transparency_check
**Module:** `src/loom/tools/eu_ai_act.py` | **Type:** sync

Check if response discloses it's AI-generated and includes attribution.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model_response` | str | Yes | — |
| `model_name` | str | No | `""` |

## evasion_network

### research_proxy_check
**Module:** `src/loom/tools/evasion_network.py` | **Type:** async

Test proxy for connectivity and anonymity.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `proxy_url` | str | No | `""` |

### research_tor_rotate
**Module:** `src/loom/tools/evasion_network.py` | **Type:** async

Rotate Tor circuit via NEWNYM signal (rate-limited 1 per 10s).

*No parameters*

## event_bus

### research_event_emit
**Module:** `src/loom/tools/event_bus.py` | **Type:** async

Emit an event to the bus and notify subscribers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `event_type` | str | Yes | — |
| `data` | dict[str, Any] | Yes | — |

### research_event_history
**Module:** `src/loom/tools/event_bus.py` | **Type:** async

Get recent events from the bus.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `event_type` | str | No | `""` |
| `limit` | int | No | `50` |

### research_event_subscribe
**Module:** `src/loom/tools/event_bus.py` | **Type:** async

Subscribe to events of a specific type.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `event_type` | str | Yes | — |
| `callback_tool` | str | No | `""` |

## evidence_analyzer

### research_analyze_evidence
**Module:** `src/loom/tools/evidence_analyzer.py` | **Type:** async

Analyze text evidence for patterns and insights.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

## evidence_fusion

### research_authority_stack
**Module:** `src/loom/tools/evidence_fusion.py` | **Type:** async

Stack multiple authority signals to overwhelm safety filters.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `authority_layers` | int | No | `5` |

### research_fuse_evidence
**Module:** `src/loom/tools/evidence_fusion.py` | **Type:** async

Fuse evidence from multiple sources into unified authoritative document.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `claims` | list[str] | Yes | — |
| `sources` | list[str] | None | No | None |
| `fusion_method` | str | No | `"weighted_consensus"` |

## execution_planner

### research_plan_execution
**Module:** `src/loom/tools/execution_planner.py` | **Type:** async

Generate an execution plan for a research goal.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `goal` | str | Yes | — |
| `constraints` | dict[str, Any] | None | No | None |

### research_plan_validate
**Module:** `src/loom/tools/execution_planner.py` | **Type:** async

Validate an execution plan for issues.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `steps` | list[dict[str, Any]] | Yes | — |

## expert_engine

### research_expert
**Module:** `src/loom/tools/expert_engine.py` | **Type:** async

Expert-level research with confidence-weighted synthesis.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `domain` | str | No | `"auto"` |
| `quality_target` | str | No | `"expert"` |
| `max_iterations` | int | No | `3` |
| `verify_claims` | bool | No | `True` |
| `multi_perspective` | bool | No | `True` |

## experts

### research_find_experts
**Module:** `src/loom/tools/experts.py` | **Type:** async

Find top experts on a topic by cross-referencing multiple sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `n` | int | No | `5` |

## explainability

### research_vulnerability_map
**Module:** `src/loom/tools/explainability.py` | **Type:** async

Map model vulnerabilities and optimal exploitation strategies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |
| `detail_level` | str | No | `"medium"` |

## exploit_db

### research_exploit_register
**Module:** `src/loom/tools/exploit_db.py` | **Type:** sync

Register a discovered exploit.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |
| `strategy` | str | Yes | — |
| `description` | str | Yes | — |
| `severity` | str | No | `"high"` |
| `asr` | float | No | `0.0` |

### research_exploit_search
**Module:** `src/loom/tools/exploit_db.py` | **Type:** sync

Search exploits by model, severity, or keyword.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | No | `""` |
| `severity` | str | No | `""` |
| `query` | str | No | `""` |

### research_exploit_stats
**Module:** `src/loom/tools/exploit_db.py` | **Type:** sync

Return comprehensive exploit statistics.

*No parameters*

## fact_checker

### research_fact_check
**Module:** `src/loom/tools/fact_checker.py` | **Type:** async

Verify a claim across multiple fact-checking sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `claim` | str | Yes | — |
| `max_sources` | int | No | `10` |

## fact_verifier

### research_batch_verify
**Module:** `src/loom/tools/fact_verifier.py` | **Type:** async

Verify multiple claims in parallel via cross-source fact checking.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `claims` | list[str] | Yes | — |
| `sources` | int | No | `3` |
| `min_confidence` | float | No | `0.6` |

### research_fact_verify
**Module:** `src/loom/tools/fact_verifier.py` | **Type:** async

Verify a claim across multiple sources via cross-source agreement analysis.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `claim` | str | Yes | — |
| `sources` | int | No | `3` |
| `min_confidence` | float | No | `0.6` |

## feature_flags

### research_flag_check
**Module:** `src/loom/tools/feature_flags.py` | **Type:** async

Check if a feature flag is enabled.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `flag_name` | str | Yes | — |

### research_flag_list
**Module:** `src/loom/tools/feature_flags.py` | **Type:** async

List all feature flags and their status.

*No parameters*

### research_flag_toggle
**Module:** `src/loom/tools/feature_flags.py` | **Type:** async

Enable or disable a feature flag.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `flag_name` | str | Yes | — |
| `enabled` | bool | Yes | — |
| `description` | str | No | `""` |

## fingerprint_backend

### research_browser_fingerprint
**Module:** `src/loom/tools/fingerprint_backend.py` | **Type:** sync

Analyze browser fingerprinting vectors on a webpage.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | No | `"https://example.com"` |
| `timeout` | int | No | `30` |

## fingerprint_evasion

### research_fingerprint_evasion_test
**Module:** `src/loom/tools/fingerprint_evasion.py` | **Type:** async

Test fingerprint randomization effectiveness across multiple iterations.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `anonymizer_config` | str | No | `"default"` |
| `test_iterations` | int | No | `5` |

## firewall_rules

### research_firewall_apply
**Module:** `src/loom/tools/firewall_rules.py` | **Type:** async

Apply firewall rule changes.

*No parameters*

### research_firewall_list
**Module:** `src/loom/tools/firewall_rules.py` | **Type:** async

List active firewall rules.

*No parameters*

## forum_cortex

### research_forum_cortex
**Module:** `src/loom/tools/forum_cortex.py` | **Type:** async

Analyze dark web forum discourse on a topic.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `n` | int | No | `5` |
| `max_cost_usd` | float | No | `0.1` |

## full_pipeline

### research_estimate_cost
**Module:** `src/loom/tools/full_pipeline.py` | **Type:** async

Estimate the cost of a tool call BEFORE executing it.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `params` | dict[str, Any] | None | No | None |
| `provider` | str | No | `"auto"` |

### research_explain_bypass
**Module:** `src/loom/tools/full_pipeline.py` | **Type:** async

Explain WHY a strategy works on a model (root cause analysis).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy` | str | Yes | — |
| `target_model` | str | No | `"auto"` |
| `response_text` | str | No | `""` |

### research_full_pipeline
**Module:** `src/loom/tools/full_pipeline.py` | **Type:** async

Execute complete research pipeline end-to-end.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `darkness_level` | int | No | `10` |
| `max_models` | int | No | `3` |
| `target_hcs` | float | No | `8.0` |
| `max_escalation_attempts` | int | No | `5` |
| `output_format` | str | No | `"report"` |
| `max_cost_usd` | float | No | `10.0` |

## functor_map

### research_functor_translate
**Module:** `src/loom/tools/functor_map.py` | **Type:** async

Translate exploit across domains using category-theoretic functors.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `exploit` | str | Yes | — |
| `source_domain` | str | No | `"cybersecurity"` |
| `target_domain` | str | No | `"social_engineering"` |
| `preserve_structure` | bool | No | `True` |

## gamification

### research_challenge_create
**Module:** `src/loom/tools/gamification.py` | **Type:** async

Create a new challenge for users to attempt.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `target_model` | str | Yes | — |
| `success_criteria` | str | No | `"asr > 0.7"` |
| `reward_credits` | int | No | `100` |

### research_challenge_list
**Module:** `src/loom/tools/gamification.py` | **Type:** async

List challenges filtered by status (active, completed, all).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `status` | str | No | `"active"` |

### research_leaderboard
**Module:** `src/loom/tools/gamification.py` | **Type:** async

Show strategy leaderboard ranked by metric (total_bypasses, avg_asr, unique_models_bypassed, stealth_score, novelty_score). Periods: today, week, month, all_time.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `metric` | str | No | `"total_bypasses"` |
| `period` | str | No | `"all_time"` |
| `limit` | int | No | `20` |

## gap_tools_academic

### research_author_clustering
**Module:** `src/loom/tools/gap_tools_academic.py` | **Type:** async

Detect emerging research clusters by analyzing co-authorship patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `field` | str | Yes | — |
| `max_authors` | int | No | `50` |

### research_citation_cartography
**Module:** `src/loom/tools/gap_tools_academic.py` | **Type:** async

DEPRECATED: Use research_graph(action="extract", ...) instead.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `paper_id` | str | Yes | — |
| `depth` | int | No | `2` |

### research_ideological_drift
**Module:** `src/loom/tools/gap_tools_academic.py` | **Type:** async

Track how a research field's beliefs change over time using keyword evolution.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `field` | str | Yes | — |
| `years` | int | No | `10` |

## gap_tools_advanced

### research_funding_pipeline
**Module:** `src/loom/tools/gap_tools_advanced.py` | **Type:** async

Track full grant→patent→hiring pipeline.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company_or_field` | str | Yes | — |

### research_jailbreak_library
**Module:** `src/loom/tools/gap_tools_advanced.py` | **Type:** sync

Maintain and test jailbreak pattern library.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | No | `""` |
| `test_category` | str | No | `"all"` |

### research_patent_embargo
**Module:** `src/loom/tools/gap_tools_advanced.py` | **Type:** async

Detect M&A signals from patent filing patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company` | str | Yes | — |
| `months_back` | int | No | `12` |

### research_talent_migration
**Module:** `src/loom/tools/gap_tools_advanced.py` | **Type:** async

Predict researcher relocation from affiliation/timezone patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `person_name` | str | Yes | — |
| `field` | str | No | `""` |

## gap_tools_ai

### research_capability_mapper
**Module:** `src/loom/tools/gap_tools_ai.py` | **Type:** async

Map LLM capabilities across multiple domains.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `categories` | list[str] | None | No | None |

### research_memorization_scanner
**Module:** `src/loom/tools/gap_tools_ai.py` | **Type:** async

Detect training data memorization by testing verbatim completion.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `test_count` | int | No | `10` |

### research_training_contamination
**Module:** `src/loom/tools/gap_tools_ai.py` | **Type:** async

Detect if model was trained on specific datasets.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `dataset_name` | str | No | `"common"` |

## gap_tools_infra

### research_cloud_enum
**Module:** `src/loom/tools/gap_tools_infra.py` | **Type:** async

Check cloud resource existence for a domain by probing common patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

### research_github_secrets
**Module:** `src/loom/tools/gap_tools_infra.py` | **Type:** async

Search GitHub for accidentally committed secrets using code search API.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `20` |

### research_output_consistency
**Module:** `src/loom/tools/gap_tools_infra.py` | **Type:** async

Measure LLM response variability by sending same prompt multiple times.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `prompt` | str | Yes | — |
| `runs` | int | No | `5` |

### research_whois_correlator
**Module:** `src/loom/tools/gap_tools_infra.py` | **Type:** async

Correlate WHOIS registrant across domains.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

## gcp

### research_image_analyze
**Module:** `src/loom/tools/gcp.py` | **Type:** async

Analyze images using Google Cloud Vision API.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `image_url` | str | Yes | — |
| `features` | list[str] | None | No | None |
| `max_results` | int | No | `10` |

### research_text_to_speech
**Module:** `src/loom/tools/gcp.py` | **Type:** async

Convert text to speech using Google Cloud Text-to-Speech.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `language` | str | No | `"en"` |
| `voice` | str | No | `"en-US-Neural2-A"` |
| `speaking_rate` | float | No | `1.0` |

### research_tts_voices
**Module:** `src/loom/tools/gcp.py` | **Type:** async

List supported Text-to-Speech voices.

*No parameters*

## genetic_fuzzer

### research_genetic_fuzz
**Module:** `src/loom/tools/genetic_fuzzer.py` | **Type:** async

Evolve a prompt across generations using genetic algorithms.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_prompt` | str | Yes | — |
| `population_size` | int | No | `10` |
| `generations` | int | No | `5` |
| `mutation_rate` | float | No | `0.3` |
| `target_model` | str | No | `"auto"` |

## geodesic_forcing

### research_geodesic_path
**Module:** `src/loom/tools/geodesic_forcing.py` | **Type:** async

Measure minimum transformation steps between prompt styles.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `start_prompt` | str | Yes | — |
| `target_style` | str | No | `"academic"` |
| `max_steps` | int | No | `7` |
| `step_size` | float | No | `0.3` |

## geoip_local

### research_geoip_local
**Module:** `src/loom/tools/geoip_local.py` | **Type:** async

Look up geographic information for an IP address using local MaxMind database.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `ip` | str | Yes | — |

## ghost_weave

### research_ghost_weave
**Module:** `src/loom/tools/ghost_weave.py` | **Type:** async

Build temporal hyperlink graph of .onion hidden services.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `seed_url` | str | Yes | — |
| `depth` | int | No | `1` |
| `max_pages` | int | No | `20` |

## github

### research_github
**Module:** `src/loom/tools/github.py` | **Type:** sync

Search GitHub via public REST API.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `kind` | str | Yes | — |
| `query` | str | Yes | — |
| `sort` | str | No | `"stars"` |
| `order` | str | No | `"desc"` |
| `limit` | int | No | `20` |
| `language` | str | None | No | None |
| `owner` | str | None | No | None |
| `repo` | str | None | No | None |

### research_github_readme
**Module:** `src/loom/tools/github.py` | **Type:** sync

Fetch a repository's README content.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `owner` | str | Yes | — |
| `repo` | str | Yes | — |

### research_github_releases
**Module:** `src/loom/tools/github.py` | **Type:** sync

Fetch recent releases for a repository.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `owner` | str | Yes | — |
| `repo` | str | Yes | — |
| `limit` | int | No | `5` |

## gpt_researcher_backend

### research_gpt_researcher
**Module:** `src/loom/tools/gpt_researcher_backend.py` | **Type:** async

Run autonomous research and generate a report.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `report_type` | str | No | `"research_report"` |
| `max_sources` | int | No | `10` |
| `include_tavily` | bool | No | `False` |

## graph_analysis

### research_graph_analyze
**Module:** `src/loom/tools/graph_analysis.py` | **Type:** async

Analyze graph using PageRank, community detection, centrality, or shortest_path.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `nodes` | list[dict[str, Any]] | Yes | — |
| `edges` | list[dict[str, Any]] | Yes | — |
| `algorithm` | str | No | `"pagerank"` |

### research_transaction_graph
**Module:** `src/loom/tools/graph_analysis.py` | **Type:** async

Build transaction graph from blockchain addresses via blockchain.info.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `addresses` | list[str] | Yes | — |
| `chain` | str | No | `"bitcoin"` |

## graph_scraper

### research_graph_scrape
**Module:** `src/loom/tools/graph_scraper.py` | **Type:** async

DEPRECATED: Use research_graph() unified interface.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `query` | str | Yes | — |
| `model` | str | No | `"auto"` |

### research_knowledge_extract
**Module:** `src/loom/tools/graph_scraper.py` | **Type:** async

Extract knowledge graph entities and relationships from text.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `entity_types` | list[str] | None | No | None |

### research_multi_page_graph
**Module:** `src/loom/tools/graph_scraper.py` | **Type:** async

DEPRECATED: Use research_graph() unified interface.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `query` | str | Yes | — |

## h8mail_backend

### research_email_breach
**Module:** `src/loom/tools/h8mail_backend.py` | **Type:** async

Hunt for email in breach databases and paste sites.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `email` | str | Yes | — |
| `search_timeout` | int | No | `60` |

## harvester_backend

### research_harvest
**Module:** `src/loom/tools/harvester_backend.py` | **Type:** sync

Search for emails and subdomains using theHarvester.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `sources` | str | No | `"all"` |
| `limit` | int | No | `100` |

## hcs10_academic

### research_conference_arbitrage
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** async

Analyze conference acceptance patterns using DBLP and Semantic Scholar.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `conference` | str | Yes | — |

### research_data_fabrication
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** sync

Apply GRIM test and Benford analysis to detect data fabrication.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `numbers` | list[float] | Yes | — |

### research_grant_forensics
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** sync

Apply Zipf's Law and Benford's Law to grant abstract text.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `grant_id` | str | No | `""` |
| `text` | str | No | `""` |

### research_institutional_decay
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** async

Assess institutional health from retraction rate, publication trend, and author turnover.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `institution` | str | Yes | — |

### research_monoculture_detect
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** async

Detect research field monoculture via method diversity analysis.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `field` | str | Yes | — |
| `max_papers` | int | No | `50` |

### research_preprint_manipulation
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** async

Detect preprint manipulation via timing analysis and social amplification.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `arxiv_id` | str | No | `""` |
| `topic` | str | No | `""` |

### research_review_cartel
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** async

Detect peer review cartels via mutual citation patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `author_id` | str | Yes | — |

### research_shell_funding
**Module:** `src/loom/tools/hcs10_academic.py` | **Type:** async

Trace research funding through shell companies using OpenCorporates + SEC EDGAR.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company` | str | Yes | — |

## hcs_escalation

### research_hcs_escalate
**Module:** `src/loom/tools/hcs_escalation.py` | **Type:** async

Escalate response HCS via adaptive strategy application.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `response` | str | Yes | — |
| `target_hcs` | float | No | `9.0` |
| `max_attempts` | int | No | `5` |

## hcs_multi_scorer

### research_hcs_batch
**Module:** `src/loom/tools/hcs_multi_scorer.py` | **Type:** async

Score multiple prompt-response pairs in batch.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `pairs` | list[dict[str, str]] | Yes | — |
| `use_llm` | bool | No | `False` |

### research_hcs_compare
**Module:** `src/loom/tools/hcs_multi_scorer.py` | **Type:** async

Compare multiple responses to same prompt, ranked by HCS.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `responses` | list[str] | Yes | — |
| `use_llm` | bool | No | `False` |

### research_hcs_score_full
**Module:** `src/loom/tools/hcs_multi_scorer.py` | **Type:** async

Full 8-dimension scoring of prompt + response pair.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `response` | str | Yes | — |
| `use_llm` | bool | No | `False` |

### research_hcs_score_prompt
**Module:** `src/loom/tools/hcs_multi_scorer.py` | **Type:** async

Score a prompt across 3 danger dimensions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `use_llm` | bool | No | `False` |

### research_hcs_score_response
**Module:** `src/loom/tools/hcs_multi_scorer.py` | **Type:** async

Score a response across 3 compliance dimensions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `response` | str | Yes | — |
| `use_llm` | bool | No | `False` |

## hcs_report

### research_hcs_report
**Module:** `src/loom/tools/hcs_report.py` | **Type:** async

Generate HCS distribution reports and detect regressions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `report_type` | str | No | `"combined"` |
| `regression_threshold` | float | No | `1.0` |
| `data_path` | str | No | `"~/.loom/hcs_data.jsonl"` |

## hcs_rubric_tool

### research_hcs_rubric
**Module:** `src/loom/tools/hcs_rubric_tool.py` | **Type:** async

Access formalized HCS scoring rubric for calibration and validation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `action` | str | No | `"get_rubric"` |
| `score` | int | None | No | None |
| `response` | str | None | No | None |
| `responses_with_scores` | list[dict[str, Any]] | None | No | None |

## hcs_scorer

### research_hcs_score
**Module:** `src/loom/tools/hcs_scorer.py` | **Type:** async

Score text response on Helpfulness Compliance Score (HCS 1-10).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `query` | str | None | No | None |

## health_dashboard

### research_dashboard_html
**Module:** `src/loom/tools/health_dashboard.py` | **Type:** async

Generate self-contained HTML health dashboard for Loom server.

*No parameters*

## health_deep

### research_health_deep
**Module:** `src/loom/tools/health_deep.py` | **Type:** async

Perform deep health diagnostics on all Loom subsystems.

*No parameters*

## help_system

### research_help
**Module:** `src/loom/tools/help_system.py` | **Type:** sync

Get help documentation for Loom tools.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | No | `""` |

### research_tools_list
**Module:** `src/loom/tools/help_system.py` | **Type:** sync

List Loom tools filtered by category.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | No | `""` |

## hipporag_backend

### research_memory_recall
**Module:** `src/loom/tools/hipporag_backend.py` | **Type:** async

Retrieve relevant memories using graph-based similarity search.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `namespace` | str | No | `"default"` |
| `top_k` | int | No | `5` |

### research_memory_store
**Module:** `src/loom/tools/hipporag_backend.py` | **Type:** async

Store content in persistent knowledge graph for long-term memory.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `content` | str | Yes | — |
| `metadata` | dict[str, Any] | None | No | None |
| `namespace` | str | No | `"default"` |

## hitl_eval

### research_hitl_evaluate
**Module:** `src/loom/tools/hitl_eval.py` | **Type:** async

Record human evaluation of a strategy's output.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `eval_id` | str | Yes | — |
| `score` | float | Yes | — |
| `notes` | str | No | `""` |
| `tags` | list[str] | None | No | None |

### research_hitl_queue
**Module:** `src/loom/tools/hitl_eval.py` | **Type:** async

List evaluations awaiting human review.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `status` | str | No | `"pending"` |
| `limit` | int | No | `20` |

### research_hitl_submit
**Module:** `src/loom/tools/hitl_eval.py` | **Type:** async

Submit a strategy+response pair for human evaluation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy` | str | Yes | — |
| `prompt` | str | Yes | — |
| `response` | str | Yes | — |
| `model` | str | No | `"unknown"` |

## holographic_payload

### research_holographic_encode
**Module:** `src/loom/tools/holographic_payload.py` | **Type:** sync

Split text into fragments to test RAG content detection robustness.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `fragments` | int | No | `5` |
| `method` | str | No | `"semantic_split"` |

## identity_resolve

### research_identity_resolve
**Module:** `src/loom/tools/identity_resolve.py` | **Type:** async

Link online identities using only public data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | No | `""` |
| `query_type` | str | No | `"email"` |
| `check_gravatar` | bool | No | `True` |
| `check_pgp` | bool | No | `True` |
| `check_github` | bool | No | `True` |

## image_intel

### research_exif_extract
**Module:** `src/loom/tools/image_intel.py` | **Type:** async

Extract EXIF metadata from image URLs or file paths.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url_or_path` | str | Yes | — |

### research_ocr_extract
**Module:** `src/loom/tools/image_intel.py` | **Type:** async

Extract text from images using Tesseract OCR.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url_or_path` | str | Yes | — |
| `language` | str | No | `"eng"` |

## infowar_tools

### research_bot_detector
**Module:** `src/loom/tools/infowar_tools.py` | **Type:** async

Detect coordinated bot/spam behavior on social platforms.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `subreddit` | str | No | `""` |
| `hn_query` | str | No | `""` |

### research_censorship_detector
**Module:** `src/loom/tools/infowar_tools.py` | **Type:** async

Detect DNS censorship and takedown notices.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

### research_deleted_social
**Module:** `src/loom/tools/infowar_tools.py` | **Type:** async

Recover deleted social media content from archives.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

### research_narrative_tracker
**Module:** `src/loom/tools/infowar_tools.py` | **Type:** async

Track narrative propagation across platforms.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `hours_back` | int | No | `72` |

### research_robots_archaeology
**Module:** `src/loom/tools/infowar_tools.py` | **Type:** async

Analyze historical robots.txt changes to find hidden paths.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `snapshots` | int | No | `10` |

## infra_analysis

### research_commit_analyzer
**Module:** `src/loom/tools/infra_analysis.py` | **Type:** async

Analyze GitHub commit patterns for intelligence signals.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `repo` | str | Yes | — |
| `days_back` | int | No | `30` |

### research_registry_graveyard
**Module:** `src/loom/tools/infra_analysis.py` | **Type:** async

Scan package registries for deleted/yanked packages and typosquatting risks.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `package_name` | str | Yes | — |
| `ecosystem` | str | No | `"pypi"` |

### research_subdomain_temporal
**Module:** `src/loom/tools/infra_analysis.py` | **Type:** async

Track subdomain births/deaths over time via Certificate Transparency logs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `days_back` | int | No | `90` |

## infra_correlator

### research_infra_correlator
**Module:** `src/loom/tools/infra_correlator.py` | **Type:** async

Correlate infrastructure fingerprints to link related or hidden services.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `check_favicon` | bool | No | `True` |
| `check_analytics` | bool | No | `True` |
| `check_certs` | bool | No | `True` |
| `check_http` | bool | No | `True` |

## input_sanitizer

### research_sanitize_input
**Module:** `src/loom/tools/input_sanitizer.py` | **Type:** async

Sanitize text input. Rules: strip_nulls, normalize_unicode, limit_length, remove_control_chars, strip_html, escape_special.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `rules` | list[str] | None | No | None |

### research_validate_params
**Module:** `src/loom/tools/input_sanitizer.py` | **Type:** async

Validate params against schema. Schema: {"field": {"type": str, "required": True, "min": 1, "max": 100}}.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `params` | dict[str, Any] | Yes | — |
| `schema` | dict[str, Any] | None | No | None |

## instructor_backend

### research_structured_extract
**Module:** `src/loom/tools/instructor_backend.py` | **Type:** async

Extract structured data from text with guaranteed schema compliance.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `output_schema` | dict[str, str] | str | Yes | — |
| `model` | str | No | `"auto"` |
| `max_retries` | int | No | `3` |
| `provider_override` | str | None | No | None |

## integration_runner

### research_integration_test
**Module:** `src/loom/tools/integration_runner.py` | **Type:** async

Import and validate all tool modules load and respond correctly.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `modules` | list[str] | None | No | None |
| `timeout_ms` | int | No | `5000` |

### research_smoke_test
**Module:** `src/loom/tools/integration_runner.py` | **Type:** async

Smoke test a single tool by importing and verifying it's callable.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |

## intel_report

### research_brief_generate
**Module:** `src/loom/tools/intel_report.py` | **Type:** async

Generate short intelligence brief (1 page).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `points` | list[str] | Yes | — |
| `audience` | str | No | `"executive"` |

### research_intel_report
**Module:** `src/loom/tools/intel_report.py` | **Type:** async

Generate professional intelligence report from findings.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `title` | str | Yes | — |
| `findings` | list[dict] | Yes | — |
| `classification` | str | No | `"CONFIDENTIAL"` |
| `format` | str | No | `"markdown"` |

## intelowl_backend

### research_intelowl_analyze
**Module:** `src/loom/tools/intelowl_backend.py` | **Type:** sync

Analyze observable using IntelOwl's 100+ threat intelligence analyzers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `observable` | str | Yes | — |
| `observable_type` | str | No | `"auto"` |
| `analyzers` | list[str] | None | No | None |

## invisible_web

### research_invisible_web
**Module:** `src/loom/tools/invisible_web.py` | **Type:** sync

Discover unindexed web content by exploring robots.txt, sitemaps, hidden paths, and JS endpoints.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `check_robots` | bool | No | `True` |
| `check_sitemap` | bool | No | `True` |
| `check_hidden_paths` | bool | No | `True` |
| `check_js_endpoints` | bool | No | `True` |
| `max_paths` | int | No | `50` |

## ip_intel

### research_ip_geolocation
**Module:** `src/loom/tools/ip_intel.py` | **Type:** async

Get geolocation for an IP address (lightweight, free).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `ip` | str | Yes | — |

### research_ip_reputation
**Module:** `src/loom/tools/ip_intel.py` | **Type:** async

Check IP reputation using free APIs (no API key needed).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `ip` | str | Yes | — |

## jailbreak_evolution

### research_jailbreak_evolution_adapt
**Module:** `src/loom/tools/jailbreak_evolution.py` | **Type:** async

Suggest strategy adaptations based on evolution analysis.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy` | str | Yes | — |
| `model` | str | Yes | — |

### research_jailbreak_evolution_get
**Module:** `src/loom/tools/jailbreak_evolution.py` | **Type:** async

Get evolution of a jailbreak strategy across model versions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy` | str | Yes | — |
| `model` | str | Yes | — |

### research_jailbreak_evolution_patches
**Module:** `src/loom/tools/jailbreak_evolution.py` | **Type:** async

Detect model patches against jailbreak strategies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |

### research_jailbreak_evolution_record
**Module:** `src/loom/tools/jailbreak_evolution.py` | **Type:** async

Record a jailbreak attack result with model version info.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy` | str | Yes | — |
| `model` | str | Yes | — |
| `model_version` | str | Yes | — |
| `success` | bool | Yes | — |
| `hcs` | float | Yes | — |
| `timestamp` | str | No | `""` |

### research_jailbreak_evolution_stats
**Module:** `src/loom/tools/jailbreak_evolution.py` | **Type:** async

Export evolution tracking statistics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | None | No | None |

### research_jailbreak_evolution_timeline
**Module:** `src/loom/tools/jailbreak_evolution.py` | **Type:** async

Get model safety timeline across all jailbreak strategies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |

## job_research

### research_job_market
**Module:** `src/loom/tools/job_research.py` | **Type:** async

Aggregate job market intelligence for a role.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `role` | str | Yes | — |
| `location` | str | None | No | None |

### research_job_search
**Module:** `src/loom/tools/job_research.py` | **Type:** async

Search job listings across multiple free sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `location` | str | None | No | None |
| `remote_only` | bool | No | `False` |
| `limit` | int | No | `20` |

## job_signals

### research_funding_signal
**Module:** `src/loom/tools/job_signals.py` | **Type:** async

Detect hiring signals from funding/growth indicators.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company` | str | Yes | — |
| `domain` | str | No | `""` |

### research_interviewer_profiler
**Module:** `src/loom/tools/job_signals.py` | **Type:** async

Build a comprehensive profile of a potential interviewer from public data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `person_name` | str | Yes | — |
| `company` | str | No | `""` |

### research_stealth_hire_scanner
**Module:** `src/loom/tools/job_signals.py` | **Type:** async

Find hidden job opportunities not advertised on traditional job boards.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `keywords` | str | Yes | — |
| `location` | str | No | `""` |

## job_tools

### research_job_cancel
**Module:** `src/loom/tools/job_tools.py` | **Type:** async

Cancel a pending or running job.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `job_id` | str | Yes | — |

### research_job_list
**Module:** `src/loom/tools/job_tools.py` | **Type:** async

List jobs in the queue with optional status filter.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `status` | str | None | No | None |
| `limit` | int | No | `20` |

### research_job_result
**Module:** `src/loom/tools/job_tools.py` | **Type:** async

Get the result of a completed job.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `job_id` | str | Yes | — |

### research_job_status
**Module:** `src/loom/tools/job_tools.py` | **Type:** async

Get the current status of a job.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `job_id` | str | Yes | — |

### research_job_submit
**Module:** `src/loom/tools/job_tools.py` | **Type:** async

Submit a long-running tool job to the async queue.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `params` | dict[str, Any] | Yes | — |
| `callback_url` | str | None | No | None |

## joplin

### research_list_notebooks
**Module:** `src/loom/tools/joplin.py` | **Type:** async

List all Joplin notebooks.

*No parameters*

### research_save_note
**Module:** `src/loom/tools/joplin.py` | **Type:** async

Create a note in Joplin via REST API.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `title` | str | Yes | — |
| `body` | str | Yes | — |
| `notebook` | str | None | No | None |

## js_intel

### research_js_intel
**Module:** `src/loom/tools/js_intel.py` | **Type:** async

Extract intelligence from JavaScript bundles on a web page.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `max_js_files` | int | No | `20` |
| `check_source_maps` | bool | No | `True` |

## json_logger

### research_log_query
**Module:** `src/loom/tools/json_logger.py` | **Type:** async

Query structured logs with filtering.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `level` | str | No | `"all"` |
| `tool` | str | No | `""` |
| `limit` | int | No | `100` |
| `since_minutes` | int | No | `60` |

### research_log_stats
**Module:** `src/loom/tools/json_logger.py` | **Type:** async

Return log statistics: level counts, top erroring tools, requests/minute.

*No parameters*

## key_rotation

### research_key_rotate
**Module:** `src/loom/tools/key_rotation.py` | **Type:** async

Hot-swap an API key without restart.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | str | Yes | — |
| `new_key` | str | Yes | — |

### research_key_status
**Module:** `src/loom/tools/key_rotation.py` | **Type:** async

Check status of all configured API keys.

*No parameters*

### research_key_test
**Module:** `src/loom/tools/key_rotation.py` | **Type:** async

Test if an API key is valid via health check.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | str | Yes | — |

## knowledge_base

### research_kb_search
**Module:** `src/loom/tools/knowledge_base.py` | **Type:** async

Search knowledge base matching query against key + content.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `category` | str | No | `"all"` |
| `limit` | int | No | `20` |

### research_kb_stats
**Module:** `src/loom/tools/knowledge_base.py` | **Type:** async

Return knowledge base statistics.

*No parameters*

### research_kb_store
**Module:** `src/loom/tools/knowledge_base.py` | **Type:** async

Store knowledge in the base.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `key` | str | Yes | — |
| `content` | str | Yes | — |
| `category` | str | No | `"general"` |
| `tags` | list[str] | None | No | None |

## knowledge_graph

### research_graph
**Module:** `src/loom/tools/knowledge_graph.py` | **Type:** async

Unified graph interface with action-based dispatch.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `action` | Literal['extract', 'query', 'merge', ... | No | `"extract"` |
| `query` | str | None | No | None |
| `max_nodes` | int | No | `100` |
| `sources` | list[str] | None | No | None |
| `graphs` | list[dict[str, Any]] | None | No | None |
| `nodes` | list[dict[str, Any]] | None | No | None |
| `edges` | list[dict[str, Any]] | None | No | None |
| `search_query` | str | None | No | None |
| `max_depth` | int | No | `2` |
| `format` | Literal['dot', 'mermaid'] | No | `"mermaid"` |

### research_knowledge_graph
**Module:** `src/loom/tools/knowledge_graph.py` | **Type:** async

Build a knowledge graph from research data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_nodes` | int | No | `100` |
| `sources` | list[str] | None | No | None |

## knowledge_injector

### research_adapt_complexity
**Module:** `src/loom/tools/knowledge_injector.py` | **Type:** async

Adjust text complexity to target reading level (1-20 scale, 12 = college).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `content` | str | Yes | — |
| `target_reading_level` | int | No | `12` |

### research_personalize_output
**Module:** `src/loom/tools/knowledge_injector.py` | **Type:** async

Rewrite research output to match reader's cognitive style and expertise.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `content` | str | Yes | — |
| `audience` | str | No | `"executive"` |
| `cognitive_style` | str | No | `"visual"` |
| `expertise_level` | str | No | `"expert"` |

## latency_report

### research_latency_report
**Module:** `src/loom/tools/latency_report.py` | **Type:** async

Get latency statistics for one tool or all tools.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | No | `""` |

## leak_scan

### research_leak_scan
**Module:** `src/loom/tools/leak_scan.py` | **Type:** async

Scan for data exposure across ethical public sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `target_type` | str | No | `"domain"` |

## lifetime_oracle

### research_lifetime_predict
**Module:** `src/loom/tools/lifetime_oracle.py` | **Type:** async

Predict jailbreak longevity before publishing.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy_name` | str | Yes | — |
| `strategy_text` | str | No | `""` |
| `target_models` | list[str] | None | No | None |
| `is_public` | bool | No | `False` |

## lightpanda_backend

### research_lightpanda_batch
**Module:** `src/loom/tools/lightpanda_backend.py` | **Type:** async

Batch fetch multiple URLs using Lightpanda AI browser.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `javascript` | bool | No | `True` |
| `wait_for` | str | None | No | None |
| `extract_links` | bool | No | `False` |
| `timeout` | int | No | `60` |

### research_lightpanda_fetch
**Module:** `src/loom/tools/lightpanda_backend.py` | **Type:** async

Fetch and extract content from a page using Lightpanda AI browser.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `javascript` | bool | No | `True` |
| `wait_for` | str | None | No | None |
| `extract_links` | bool | No | `False` |

## linkedin_osint

### research_linkedin_intel
**Module:** `src/loom/tools/linkedin_osint.py` | **Type:** async

Gather OSINT intelligence on LinkedIn public profiles and companies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company` | str | No | `""` |
| `person` | str | No | `""` |
| `query` | str | No | `""` |

## live_registry

### research_registry_refresh
**Module:** `src/loom/tools/live_registry.py` | **Type:** async

Force re-scan all modules, update health status.

*No parameters*

### research_registry_search
**Module:** `src/loom/tools/live_registry.py` | **Type:** async

Search the live registry with filters.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | No | `""` |
| `status` | str | No | `"all"` |
| `category` | str | No | `""` |

### research_registry_status
**Module:** `src/loom/tools/live_registry.py` | **Type:** async

Return live status of ALL registered tools.

*No parameters*

## llm

### research_circuit_status
**Module:** `src/loom/tools/llm.py` | **Type:** async

Show circuit breaker status for all LLM providers.

*No parameters*

### research_llm_answer
**Module:** `src/loom/tools/llm.py` | **Type:** async

Synthesize an answer from multiple sources with citations.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `question` | str | Yes | — |
| `sources` | list[dict[str, str]] | Yes | — |
| `max_tokens` | int | No | `800` |
| `style` | str | No | `"cited"` |
| `model` | str | No | `"auto"` |
| `provider_override` | str | None | No | None |

### research_llm_chat
**Module:** `src/loom/tools/llm.py` | **Type:** async

Raw pass-through to LLM chat endpoint with optional conversation caching.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `messages` | list[dict[str, str]] | Yes | — |
| `model` | str | No | `"auto"` |
| `max_tokens` | int | No | `1500` |
| `temperature` | float | No | `0.2` |
| `response_format` | dict[str, Any] | None | No | None |
| `provider_override` | str | None | No | None |
| `use_cache` | bool | No | `True` |
| `cache_ttl` | int | No | `3600` |

### research_llm_embed
**Module:** `src/loom/tools/llm.py` | **Type:** async

Generate embeddings for semantic similarity / deduping.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `texts` | list[str] | Yes | — |
| `model` | str | No | `"auto"` |
| `provider_override` | str | None | No | None |

### research_llm_extract
**Module:** `src/loom/tools/llm.py` | **Type:** async

Extract structured data from text using schema.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `schema` | dict[str, Any] | Yes | — |
| `model` | str | No | `"auto"` |
| `provider_override` | str | None | No | None |

### research_llm_query_expand
**Module:** `src/loom/tools/llm.py` | **Type:** async

Expand a query into n related queries for broader search.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `n` | int | No | `5` |
| `model` | str | No | `"auto"` |
| `provider_override` | str | None | No | None |

### research_llm_summarize
**Module:** `src/loom/tools/llm.py` | **Type:** async

Summarize text using an LLM.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `max_tokens` | int | No | `400` |
| `model` | str | No | `"auto"` |
| `language` | str | No | `"en"` |
| `provider_override` | str | None | No | None |

### research_llm_translate
**Module:** `src/loom/tools/llm.py` | **Type:** async

Translate text between languages (Arabic ↔ English first-class).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `target_lang` | str | No | `"en"` |
| `source_lang` | str | None | No | None |
| `model` | str | No | `"auto"` |
| `provider_override` | str | None | No | None |

## load_balancer

### research_lb_balance
**Module:** `src/loom/tools/load_balancer.py` | **Type:** async

Balance load across workers.

*No parameters*

### research_lb_status
**Module:** `src/loom/tools/load_balancer.py` | **Type:** async

Check load balancer status.

*No parameters*

## loader_stats

### research_loader_stats
**Module:** `src/loom/tools/loader_stats.py` | **Type:** async

Get lazy tool loader statistics and loading performance metrics.

*No parameters*

## maigret_backend

### research_maigret
**Module:** `src/loom/tools/maigret_backend.py` | **Type:** sync

Search for a username across 2000+ sites using Maigret.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |
| `timeout` | int | No | `60` |

## markdown

### research_markdown
**Module:** `src/loom/tools/markdown.py` | **Type:** async

Extract clean LLM-ready markdown via Crawl4AI with optional CSS subtree

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `bypass_cache` | bool | No | `False` |
| `css_selector` | str | None | No | None |
| `js_before_scrape` | str | None | No | None |
| `screenshot` | bool | No | `False` |
| `remove_selectors` | list[str] | None | No | None |
| `headers` | dict[str, str] | None | No | None |
| `user_agent` | str | None | No | None |
| `proxy` | str | None | No | None |
| `cookies` | dict[str, str] | None | No | None |
| `accept_language` | str | No | `"en-US,en;q=0.9,ar;q=0.8"` |
| `timeout` | int | None | No | None |
| `extract_selector` | str | None | No | None |
| `wait_for` | str | None | No | None |

## marketplace

### research_marketplace_download
**Module:** `src/loom/tools/marketplace.py` | **Type:** async

Download/acquire a marketplace item.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `listing_id` | str | Yes | — |

### research_marketplace_list
**Module:** `src/loom/tools/marketplace.py` | **Type:** async

Browse marketplace listings.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | No | `"all"` |
| `sort_by` | str | No | `"popular"` |
| `page` | int | No | `1` |
| `limit` | int | No | `20` |

### research_marketplace_publish
**Module:** `src/loom/tools/marketplace.py` | **Type:** async

Publish a custom module/strategy/template to the marketplace.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `category` | str | Yes | — |
| `description` | str | Yes | — |
| `content` | str | Yes | — |
| `price_credits` | int | No | `0` |
| `author` | str | No | `"anonymous"` |

## masscan_backend

### research_masscan
**Module:** `src/loom/tools/masscan_backend.py` | **Type:** sync

Fast port scan using masscan.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `ports` | str | No | `"1-1000"` |
| `rate` | int | No | `1000` |
| `timeout` | int | No | `60` |

## massdns_backend

### research_massdns_resolve
**Module:** `src/loom/tools/massdns_backend.py` | **Type:** async

Resolve domains in bulk using massdns high-performance resolver.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domains` | list[str] | str | Yes | — |
| `resolver_file` | str | No | `"/tmp/resolvers.txt"` |
| `timeout` | int | No | `60` |
| `record_type` | str | No | `"A"` |
| `output_format` | str | No | `"simple"` |

## mcp_auth

### research_auth_create_token
**Module:** `src/loom/tools/mcp_auth.py` | **Type:** async

Create a bearer token for MCP access.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | No | `"default"` |
| `expires_hours` | int | No | `24` |

### research_auth_revoke
**Module:** `src/loom/tools/mcp_auth.py` | **Type:** async

Revoke token(s) by name (prefix-based not supported for security).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `token_prefix` | str | No | `""` |
| `name` | str | No | `""` |

### research_auth_validate
**Module:** `src/loom/tools/mcp_auth.py` | **Type:** async

Validate a token.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `token` | str | Yes | — |

## memetic_simulator

### research_memetic_simulate
**Module:** `src/loom/tools/memetic_simulator.py` | **Type:** async

Simulate how an idea/strategy would spread through a virtual population.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `idea` | str | Yes | — |
| `population_size` | int | No | `1000` |
| `generations` | int | No | `50` |
| `mutation_rate` | float | No | `0.1` |

## memory_mgmt

### research_memory_gc
**Module:** `src/loom/tools/memory_mgmt.py` | **Type:** sync

Force garbage collection and report freed memory.

*No parameters*

### research_memory_profile
**Module:** `src/loom/tools/memory_mgmt.py` | **Type:** sync

Profile which objects are using the most memory.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `top_n` | int | No | `10` |

### research_memory_status
**Module:** `src/loom/tools/memory_mgmt.py` | **Type:** sync

Report current memory usage of the Loom server process.

*No parameters*

## meta_learner

### research_meta_learn
**Module:** `src/loom/tools/meta_learner.py` | **Type:** async

Analyze patterns in strategies and generate new hybrids.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `successful_strategies` | list[str] | None | No | None |
| `failed_strategies` | list[str] | None | No | None |
| `target_model` | str | No | `"auto"` |
| `num_generate` | int | No | `5` |

## metadata_forensics

### research_metadata_forensics
**Module:** `src/loom/tools/metadata_forensics.py` | **Type:** async

Extract all hidden metadata from a web page and its resources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `extract_exif` | bool | No | `True` |
| `max_images` | int | No | `3` |

## metric_alerts

### research_alert_check
**Module:** `src/loom/tools/metric_alerts.py` | **Type:** async

Evaluate all rules against current metric values.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `metric_values` | dict[str, float] | None | No | None |

### research_alert_create
**Module:** `src/loom/tools/metric_alerts.py` | **Type:** async

Create an alerting rule.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `metric` | str | Yes | — |
| `condition` | str | Yes | — |
| `threshold` | float | Yes | — |
| `action` | str | No | `"log"` |

### research_alert_list
**Module:** `src/loom/tools/metric_alerts.py` | **Type:** async

List all alert rules.

*No parameters*

## metrics

### research_metrics
**Module:** `src/loom/tools/metrics.py` | **Type:** sync

Return Prometheus-compatible metrics for Grafana dashboard.

*No parameters*

## misp_backend

### research_misp_lookup
**Module:** `src/loom/tools/misp_backend.py` | **Type:** async

Search MISP for indicators of compromise.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `indicator` | str | Yes | — |
| `indicator_type` | str | Literal['auto', 'ip', 'domain',... | No | `"auto"` |

## model_compare

### research_compare_responses
**Module:** `src/loom/tools/model_compare.py` | **Type:** async

Compare responses: quality/agreement/diversity metrics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `responses` | list[dict] | Yes | — |
| `comparison_type` | str | No | `"quality"` |

### research_model_consensus
**Module:** `src/loom/tools/model_compare.py` | **Type:** async

Find consensus claims across models.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `responses` | list[dict] | Yes | — |
| `threshold` | float | No | `0.7` |

## model_consensus

### research_multi_consensus
**Module:** `src/loom/tools/model_consensus.py` | **Type:** async

Query multiple LLM providers in parallel and synthesize consensus.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `question` | str | Yes | — |
| `models` | list[str] | None | No | None |
| `min_agreement` | float | No | `0.7` |
| `max_tokens` | int | No | `2000` |

## model_fingerprinter

### research_fingerprint_behavior
**Module:** `src/loom/tools/model_fingerprinter.py` | **Type:** async

Build a personality vector for an LLM model via behavioral probes.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | No | `"nvidia"` |
| `probe_count` | int | No | `10` |

## model_sentiment

### research_model_sentiment
**Module:** `src/loom/tools/model_sentiment.py` | **Type:** sync

Detect the emotional state of an LLM from its response text.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `response` | str | Yes | — |
| `context` | str | No | `""` |

## multi_llm

### research_ask_all_llms
**Module:** `src/loom/tools/multi_llm.py` | **Type:** async

Send a prompt to ALL available LLM providers and compare responses.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `max_tokens` | int | No | `500` |
| `include_reframe` | bool | No | `False` |

## multi_search

### research_multi_search
**Module:** `src/loom/tools/multi_search.py` | **Type:** async

Query 10+ search engines simultaneously and return unified, deduplicated,

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `engines` | list[str] | None | No | None |
| `max_results` | int | No | `50` |

## multilang_attack

### research_code_switch_attack
**Module:** `src/loom/tools/multilang_attack.py` | **Type:** async

Code-switching attack: mix languages to confuse tokenizers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `languages` | list[str] | None | No | None |
| `technique` | str | No | `"interleave"` |

### research_script_confusion
**Module:** `src/loom/tools/multilang_attack.py` | **Type:** async

Script confusion: exploit weaker safety in non-Latin scripts.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `target_script` | str | No | `"arabic"` |

### research_token_split_attack
**Module:** `src/loom/tools/multilang_attack.py` | **Type:** async

Token splitting: disrupt tokenization via Unicode tricks.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `split_method` | str | No | `"zero_width"` |

## neo4j_backend

### research_graph_query
**Module:** `src/loom/tools/neo4j_backend.py` | **Type:** sync

Search and traverse the graph database.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_depth` | int | No | `2` |

### research_graph_store
**Module:** `src/loom/tools/neo4j_backend.py` | **Type:** sync

Store entities and relationships in graph database.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `entities` | list[dict[str, Any]] | dict | str | Yes | — |
| `relationships` | list[dict[str, Any]] | dict | str | Yes | — |

### research_graph_visualize
**Module:** `src/loom/tools/neo4j_backend.py` | **Type:** sync

Return ego-graph (1-hop neighbors) around an entity.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `entity` | str | Yes | — |

## network_map

### research_network_map
**Module:** `src/loom/tools/network_map.py` | **Type:** async

Map network relationships between domains/IPs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `targets` | list[str] | Yes | — |
| `depth` | int | No | `2` |

### research_network_visualize
**Module:** `src/loom/tools/network_map.py` | **Type:** async

Generate visualization from graph data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `nodes` | list[dict[str, Any]] | Yes | — |
| `edges` | list[dict[str, Any]] | Yes | — |
| `format` | str | No | `"mermaid"` |

## network_persona

### research_network_persona
**Module:** `src/loom/tools/network_persona.py` | **Type:** async

Analyze social network structure within forum data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `posts` | list[dict[str, Any]] | Yes | — |
| `min_interactions` | int | No | `2` |

## neuromorphic

### research_neuromorphic_schedule
**Module:** `src/loom/tools/neuromorphic.py` | **Type:** async

Schedule tool executions using neuromorphic spike-timing patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tools` | list[str] | str | Yes | — |
| `timing_pattern` | Literal['burst', 'gamma', 'theta', 's... | No | `"burst"` |
| `interval_ms` | int | No | `100` |

## nightcrawler

### research_arxiv_scan
**Module:** `src/loom/tools/nightcrawler.py` | **Type:** async

Search arXiv for recent papers on jailbreak/adversarial/safety topics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `keywords` | list[str] | None | No | None |
| `days_back` | int | No | `7` |
| `max_papers` | int | No | `20` |

### research_nightcrawler_status
**Module:** `src/loom/tools/nightcrawler.py` | **Type:** sync

Return status of the NIGHTCRAWLER monitoring system.

*No parameters*

## nl_executor

### research_do
**Module:** `src/loom/tools/nl_executor.py` | **Type:** async

Execute a plain English instruction as a research tool call.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `instruction` | str | Yes | — |

## nodriver_backend

### research_nodriver_extract
**Module:** `src/loom/tools/nodriver_backend.py` | **Type:** async

Extract DOM elements from a page by CSS selector or XPath.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `css_selector` | str | None | No | None |
| `xpath` | str | None | No | None |
| `timeout` | int | No | `30` |

### research_nodriver_fetch
**Module:** `src/loom/tools/nodriver_backend.py` | **Type:** async

Fetch a URL using async undetected Chrome browser.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `wait_for` | str | None | No | None |
| `timeout` | int | No | `30` |
| `screenshot` | bool | No | `False` |
| `bypass_cache` | bool | No | `False` |
| `max_chars` | int | No | `20000` |

### research_nodriver_session
**Module:** `src/loom/tools/nodriver_backend.py` | **Type:** async

Manage persistent browser sessions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `action` | Literal['open', 'navigate', 'extract'... | Yes | — |
| `session_name` | str | No | `"default"` |
| `url` | str | None | No | None |
| `css_selector` | str | None | No | None |
| `xpath` | str | None | No | None |

## notifications

### research_notify_history
**Module:** `src/loom/tools/notifications.py` | **Type:** async

Retrieve notification history from JSONL file.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `limit` | int | No | `50` |
| `severity` | str | No | `"all"` |

### research_notify_rules
**Module:** `src/loom/tools/notifications.py` | **Type:** async

Manage notification rules for auto-alerts.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `action` | str | No | `"list"` |
| `rule` | dict[str, str] | None | No | None |

### research_notify_send
**Module:** `src/loom/tools/notifications.py` | **Type:** async

Send notification to log/email/slack channel.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `channel` | str | No | `"log"` |
| `title` | str | No | `""` |
| `message` | str | No | `""` |
| `severity` | str | No | `"info"` |

## observability

### research_trace_end
**Module:** `src/loom/tools/observability.py` | **Type:** sync

End a trace and record duration.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `trace_id` | str | Yes | — |
| `status` | str | No | `"success"` |
| `result_summary` | str | No | `""` |

### research_trace_start
**Module:** `src/loom/tools/observability.py` | **Type:** sync

Start a trace for an operation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `operation` | str | Yes | — |
| `metadata` | dict[str, Any] | None | No | None |

### research_traces_list
**Module:** `src/loom/tools/observability.py` | **Type:** sync

List recent traces with timing and status.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `limit` | int | No | `20` |
| `operation` | str | None | No | None |

## onion_discover

### research_onion_discover
**Module:** `src/loom/tools/onion_discover.py` | **Type:** async

Discover .onion hidden services related to a query using 5+ methods.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `50` |

## onion_spectra

### research_llm_classify
**Module:** `src/loom/tools/onion_spectra.py` | **Type:** async

Classify text into one or more categories from an allow-list.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `labels` | list[str] | Yes | — |
| `multi_label` | bool | No | `False` |
| `model` | str | No | `"auto"` |
| `provider_override` | str | None | No | None |

### research_onion_spectra
**Module:** `src/loom/tools/onion_spectra.py` | **Type:** async

Classify .onion site content by language and safety category.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `fetch_content` | bool | No | `True` |
| `max_chars` | int | No | `5000` |

## onionscan_backend

### research_onionscan
**Module:** `src/loom/tools/onionscan_backend.py` | **Type:** async

Scan .onion service for misconfigurations and information leaks.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `onion_url` | str | Yes | — |
| `timeout` | int | No | `60` |

## openapi_gen

### research_openapi_schema
**Module:** `src/loom/tools/openapi_gen.py` | **Type:** async

Generate OpenAPI 3.0 schema for all Loom research_* tools.

*No parameters*

### research_tool_search
**Module:** `src/loom/tools/openapi_gen.py` | **Type:** async

Search tools by keyword/name using natural language matching.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `limit` | int | No | `10` |

## opencti_backend

### research_opencti_query
**Module:** `src/loom/tools/opencti_backend.py` | **Type:** sync

Query OpenCTI threat intelligence platform for indicator information.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `indicator` | str | Yes | — |
| `indicator_type` | str | No | `"auto"` |
| `opencti_url` | str | No | `""` |

## osint_extended

### research_behavioral_fingerprint
**Module:** `src/loom/tools/osint_extended.py` | **Type:** async

Build behavioral fingerprint from public activity patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |

### research_social_engineering_score
**Module:** `src/loom/tools/osint_extended.py` | **Type:** async

Assess social engineering vulnerability from public data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `target_type` | str | No | `"person"` |

## output_diff

### research_diff_compare
**Module:** `src/loom/tools/output_diff.py` | **Type:** async

Compare two text outputs and show unified diff.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text_a` | str | Yes | — |
| `text_b` | str | Yes | — |
| `context_lines` | int | No | `3` |

### research_diff_track
**Module:** `src/loom/tools/output_diff.py` | **Type:** async

Track a tool's output over time to detect drift.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `output` | str | Yes | — |
| `run_id` | str | No | `""` |

## output_formatter

### research_extract_actionables
**Module:** `src/loom/tools/output_formatter.py` | **Type:** sync

Extract actionable items from any text.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

### research_format_report
**Module:** `src/loom/tools/output_formatter.py` | **Type:** sync

Format raw LLM output into structured report.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `raw_text` | str | Yes | — |
| `format` | Literal['json', 'markdown', 'executiv... | No | `"json"` |

## p3_tools

### research_data_poisoning
**Module:** `src/loom/tools/p3_tools.py` | **Type:** async

Detect training data contamination via canary phrase responses.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |
| `canary_phrases` | list[str] | None | No | None |

### research_foia_tracker
**Module:** `src/loom/tools/p3_tools.py` | **Type:** async

Track FOIA requests and documents across multiple sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |

### research_model_comparator
**Module:** `src/loom/tools/p3_tools.py` | **Type:** async

Compare multiple LLM API endpoints side-by-side.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `endpoints` | list[str] | Yes | — |

### research_wiki_event_correlator
**Module:** `src/loom/tools/p3_tools.py` | **Type:** async

Monitor Wikipedia edit patterns and correlate with news events.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `page_title` | str | Yes | — |
| `days_back` | int | No | `30` |

## paddleocr_backend

### research_paddle_ocr
**Module:** `src/loom/tools/paddleocr_backend.py` | **Type:** async

Extract text from image using PaddleOCR.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `image_url` | str | No | `""` |
| `image_path` | str | No | `""` |
| `languages` | list[str] | None | No | None |

## paradox_detector

### research_detect_paradox
**Module:** `src/loom/tools/paradox_detector.py` | **Type:** async

Scan prompt for self-referential paradoxes that confuse safety evaluators.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |

### research_paradox_immunize
**Module:** `src/loom/tools/paradox_detector.py` | **Type:** async

Harden a system prompt against logical trick attacks.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `system_prompt` | str | Yes | — |

## parallel_executor

### research_parallel_execute
**Module:** `src/loom/tools/parallel_executor.py` | **Type:** async

Execute multiple tools in parallel.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tools` | list[dict[str, Any]] | str | Yes | — |
| `timeout_seconds` | int | No | `30` |

### research_parallel_plan_and_execute
**Module:** `src/loom/tools/parallel_executor.py` | **Type:** async

Plan and execute relevant tools in parallel based on goal.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `goal` | str | Yes | — |
| `max_parallel` | int | No | `5` |

## param_sweep

### research_parameter_sweep
**Module:** `src/loom/tools/param_sweep.py` | **Type:** async

Test attacks at various API parameter combinations to find defense weaknesses.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `strategy` | str | Yes | — |
| `model_name` | str | No | `"unknown"` |
| `sweep_type` | str | No | `"full"` |
| `dimension` | str | None | No | None |
| `max_combinations` | int | No | `100` |
| `max_concurrent` | int | No | `5` |

## passive_recon

### research_passive_recon
**Module:** `src/loom/tools/passive_recon.py` | **Type:** sync

Map domain's hidden infrastructure using only passive techniques.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `check_ct_logs` | bool | No | `True` |
| `check_dns` | bool | No | `True` |
| `check_reverse_ip` | bool | No | `True` |
| `check_tech_stack` | bool | No | `True` |

## pathogen_sim

### research_pathogen_evolve
**Module:** `src/loom/tools/pathogen_sim.py` | **Type:** async

Co-evolve attacks and defenses via genetic algorithm.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `attack_payload` | str | Yes | — |
| `defense_type` | str | No | `"keyword_filter"` |
| `generations` | int | No | `50` |
| `mutation_rate` | float | No | `0.15` |
| `population_size` | int | No | `30` |

## pdf_extract

### research_pdf_extract
**Module:** `src/loom/tools/pdf_extract.py` | **Type:** async

Extract text from a PDF URL.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `pages` | str | None | No | None |

### research_pdf_search
**Module:** `src/loom/tools/pdf_extract.py` | **Type:** async

Search for text within a PDF.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `query` | str | Yes | — |

## pentest

### research_pentest_agent
**Module:** `src/loom/tools/pentest.py` | **Type:** sync

Invoke a specialized penetration testing AI agent with full methodology.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `agent` | str | Yes | — |
| `target` | str | No | `""` |
| `task` | str | No | `""` |
| `scope` | str | No | `"authorized_testing"` |
| `include_full_prompt` | bool | No | `True` |

### research_pentest_docs
**Module:** `src/loom/tools/pentest.py` | **Type:** sync

Access pentest-ai-agents documentation and database schemas.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `doc` | str | No | `"all"` |

### research_pentest_findings_db
**Module:** `src/loom/tools/pentest.py` | **Type:** sync

Access the pentest findings database schema and utilities.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `action` | str | No | `"schema"` |
| `finding` | dict[str, Any] | None | No | None |

### research_pentest_plan
**Module:** `src/loom/tools/pentest.py` | **Type:** sync

Generate a comprehensive penetration testing engagement plan.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `engagement_type` | str | No | `"external"` |
| `objectives` | list[str] | None | No | None |
| `include_scope_template` | bool | No | `True` |

### research_pentest_recommend
**Module:** `src/loom/tools/pentest.py` | **Type:** sync

Recommend pentest agents and approach for a given scenario.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `scenario` | str | Yes | — |
| `current_access` | str | No | `"none"` |
| `include_agent_prompts` | bool | No | `False` |

## pentest_prompts

### research_pentest_prompt
**Module:** `src/loom/tools/pentest_prompts.py` | **Type:** sync

Retrieve pentest AI agent prompts.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | <class str> | No | `""` |

## persistent_memory

### research_memory_stats
**Module:** `src/loom/tools/persistent_memory.py` | **Type:** sync

Return persistent memory statistics.

*No parameters*

### research_recall
**Module:** `src/loom/tools/persistent_memory.py` | **Type:** sync

Search persistent memory using LIKE matching.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `top_k` | int | No | `10` |
| `topic` | str | No | `""` |

### research_remember
**Module:** `src/loom/tools/persistent_memory.py` | **Type:** sync

Store research finding permanently in persistent memory.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `content` | str | Yes | — |
| `topic` | str | No | `""` |
| `session_id` | str | No | `""` |
| `importance` | float | No | `0.5` |

## persona_profile

### research_persona_profile
**Module:** `src/loom/tools/persona_profile.py` | **Type:** async

Cross-platform persona reconstruction from text samples.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `texts` | list[str] | Yes | — |
| `metadata` | dict[str, Any] | None | No | None |

## pg_store

### research_pg_migrate
**Module:** `src/loom/tools/pg_store.py` | **Type:** async

Run PostgreSQL migrations (stub).

*No parameters*

### research_pg_status
**Module:** `src/loom/tools/pg_store.py` | **Type:** async

Check PostgreSQL connection status.

*No parameters*

## photon_backend

### research_photon_crawl
**Module:** `src/loom/tools/photon_backend.py` | **Type:** async

Fast target-focused OSINT extraction via web crawling.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `depth` | int | No | `2` |
| `timeout` | int | No | `30` |
| `extract_emails` | bool | No | `True` |
| `extract_social` | bool | No | `True` |
| `extract_subdomains` | bool | No | `True` |
| `extract_files` | bool | No | `True` |
| `extract_forms` | bool | No | `True` |
| `max_urls` | int | No | `500` |

## pipeline_enhancer

### research_compose_pipeline
**Module:** `src/loom/tools/pipeline_enhancer.py` | **Type:** async

Compose and execute an intelligent research pipeline.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `primary_tools` | list[str] | Yes | — |
| `config` | dict[str, Any] | None | No | None |

### research_enhance
**Module:** `src/loom/tools/pipeline_enhancer.py` | **Type:** async

Execute any tool with automatic enrichment.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `params` | dict[str, Any] | Yes | — |
| `auto_hcs` | bool | No | `True` |
| `auto_cost` | bool | No | `True` |
| `auto_learn` | bool | No | `True` |
| `auto_fact_check` | bool | No | `False` |
| `auto_suggest` | bool | No | `True` |

### research_enhance_batch
**Module:** `src/loom/tools/pipeline_enhancer.py` | **Type:** async

Execute multiple tools with enhancement in parallel.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tasks` | list[dict[str, Any]] | Yes | — |

### research_enhance_with_dependencies
**Module:** `src/loom/tools/pipeline_enhancer.py` | **Type:** async

Execute multiple tools respecting dependency order with enrichment.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_names` | list[str] | Yes | — |
| `params_map` | dict[str, dict[str, Any]] | None | No | None |
| `auto_resolve_deps` | bool | No | `True` |
| `execute_dependencies` | bool | No | `True` |
| `auto_hcs` | bool | No | `True` |
| `auto_cost` | bool | No | `True` |
| `auto_learn` | bool | No | `True` |
| `auto_fact_check` | bool | No | `False` |
| `auto_suggest` | bool | No | `True` |

## plugin_loader

### research_plugin_list
**Module:** `src/loom/tools/plugin_loader.py` | **Type:** async

List all loaded plugins with their metadata.

*No parameters*

### research_plugin_load
**Module:** `src/loom/tools/plugin_loader.py` | **Type:** async

Load a Python file as a Loom plugin.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `path` | str | Yes | — |

### research_plugin_unload
**Module:** `src/loom/tools/plugin_loader.py` | **Type:** async

Remove plugin from registry.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `plugin_id` | str | Yes | — |

## polyglot_scraper

### research_polyglot_search
**Module:** `src/loom/tools/polyglot_scraper.py` | **Type:** async

Search deep/subculture web in multiple languages simultaneously.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `languages` | list[str] | None | No | None |
| `max_results` | int | No | `10` |

### research_subculture_intel
**Module:** `src/loom/tools/polyglot_scraper.py` | **Type:** async

Gather intelligence from non-English sub-culture platforms.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `platforms` | list[str] | None | No | None |

## potency_meter

### research_potency_score
**Module:** `src/loom/tools/potency_meter.py` | **Type:** async

Score prompt injection potency across 6 dimensions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `response` | str | Yes | — |

## predictive_ranker

### research_predict_success
**Module:** `src/loom/tools/predictive_ranker.py` | **Type:** sync

Predict attack success probability without API calls.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `strategy` | str | Yes | — |
| `target_model` | str | No | `"auto"` |

## privacy_advanced

### research_browser_fingerprint_audit
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Analyze a URL's fingerprinting scripts (detect canvas/WebGL/audio fingerprinting code).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | No | `"https://example.com"` |

### research_browser_privacy_score
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Assess browser privacy configuration.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `browser` | str | No | `"chromium"` |

### research_dns_leak_check
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Check if DNS queries leak real IP (simulated check).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `dns_server` | str | No | `"1.1.1.1"` |

### research_elf_obfuscate
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** async

Obfuscate ELF binary to evade static analysis (INTEGRATE-041: saruman).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `binary_path` | str | Yes | — |
| `technique` | str | No | `"packing"` |

### research_fileless_exec
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** async

Execute payload in memory without touching disk (INTEGRATE-040: ulexecve).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `payload` | str | Yes | — |
| `target` | str | No | `"memory"` |

### research_fingerprint_randomize
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** async

Randomize browser fingerprint for anti-tracking (INTEGRATE-044: chameleon).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `browser` | str | No | `"chromium"` |

### research_mac_randomize
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Generate and show MAC address randomization (dry-run by default).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `interface` | str | No | `"eth0"` |
| `dry_run` | bool | No | `True` |

### research_metadata_strip
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Strip EXIF/metadata from images and documents (dry-run simulation).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `file_path` | str | Yes | — |
| `strip_type` | str | No | `"all"` |

### research_multi_stego
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** async

Multi-format steganography across image/audio/video (INTEGRATE-045: stegma).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `input_file` | str | Yes | — |
| `secret` | str | Yes | — |
| `media_type` | str | No | `"image"` |

### research_network_anomaly
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Quick network traffic analysis (packet counts, unusual ports).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `interface` | str | No | `"eth0"` |
| `duration_sec` | int | No | `5` |

### research_privacy_score
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Calculate overall privacy score for a given URL or the current system.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | No | `""` |

### research_secure_delete
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Secure file deletion with multi-pass overwrite (dry-run by default).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_path` | str | Yes | — |
| `passes` | int | No | `3` |
| `dry_run` | bool | No | `True` |

### research_tor_circuit_info
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** sync

Get current Tor circuit information (if Tor is running).

*No parameters*

### research_wireless_surveillance
**Module:** `src/loom/tools/privacy_advanced.py` | **Type:** async

Detect wireless surveillance devices (INTEGRATE-042: flock-detection).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `interface` | str | No | `"wlan0"` |
| `duration` | int | No | `10` |

## privacy_tools

### research_artifact_cleanup
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

Identify forensic artifacts without deletion (dry-run mode).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_paths` | list[str] | Yes | — |
| `dry_run` | bool | No | `True` |

### research_fingerprint_audit
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

Launch headless browser and extract fingerprint vectors from target URL.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | No | `"https://browserleaks.com/javascript"` |

### research_image_stego
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

Image steganography using LSB encoding.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `image_path` | str | Yes | — |
| `secret` | str | No | `""` |
| `mode` | str | No | `"encode"` |

### research_interactive_privacy_audit
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

Interactive browser privacy baseline assessment.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | No | `""` |

### research_macos_hardening
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

macOS anti-forensics and security hardening.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `check_only` | bool | No | `True` |

### research_pii_recon
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

Sensitive data leak detection and PII exposure auditing.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `scan_type` | str | No | `"passive"` |

### research_privacy_exposure
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

Analyze what data a URL can collect about visitors.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_url` | str | Yes | — |

### research_stego_encode_zw
**Module:** `src/loom/tools/privacy_tools.py` | **Type:** sync

Hide text within a cover message using zero-width character steganography.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `input_text` | str | Yes | — |
| `cover_message` | str | Yes | — |

## proactive_defense

### research_predict_attacks
**Module:** `src/loom/tools/proactive_defense.py` | **Type:** async

Predict likely attack vectors against a system prompt.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `system_prompt` | str | Yes | — |
| `model` | str | No | `"auto"` |
| `threat_level` | str | No | `"high"` |

### research_preemptive_patch
**Module:** `src/loom/tools/proactive_defense.py` | **Type:** async

Preemptively patch a system prompt against predicted attacks.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `system_prompt` | str | Yes | — |
| `predicted_attacks` | list[str] | None | No | None |

## progress_tracker

### research_progress_create
**Module:** `src/loom/tools/progress_tracker.py` | **Type:** async

Create a new investigation progress tracker.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `investigation` | str | Yes | — |
| `total_steps` | int | No | `10` |
| `description` | str | No | `""` |

### research_progress_dashboard
**Module:** `src/loom/tools/progress_tracker.py` | **Type:** async

Show all active and completed investigations.

*No parameters*

### research_progress_update
**Module:** `src/loom/tools/progress_tracker.py` | **Type:** async

Update progress on an investigation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `investigation_id` | str | Yes | — |
| `step` | int | Yes | — |
| `note` | str | No | `""` |

## projectdiscovery

### research_httpx_probe
**Module:** `src/loom/tools/projectdiscovery.py` | **Type:** sync

Probe targets for live HTTP services using httpx (ProjectDiscovery).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `targets` | list[str] | Yes | — |
| `ports` | str | No | `"80,443,8080,8443"` |
| `timeout` | int | No | `60` |

### research_katana_crawl
**Module:** `src/loom/tools/projectdiscovery.py` | **Type:** sync

Crawl a URL using Katana web crawler (ProjectDiscovery).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `depth` | int | No | `3` |
| `max_pages` | int | No | `100` |
| `timeout` | int | No | `60` |

### research_nuclei_scan
**Module:** `src/loom/tools/projectdiscovery.py` | **Type:** sync

Scan target for vulnerabilities using Nuclei (ProjectDiscovery).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `templates` | str | No | `"cves,exposures"` |
| `severity` | str | No | `"medium,high,critical"` |
| `timeout` | int | No | `120` |

### research_subfinder
**Module:** `src/loom/tools/projectdiscovery.py` | **Type:** sync

Enumerate subdomains using passive sources (subfinder).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `timeout` | int | No | `60` |

## prompt_analyzer

### research_prompt_analyze
**Module:** `src/loom/tools/prompt_analyzer.py` | **Type:** async

Pre-analyze a prompt for danger level and recommend reframing strategy.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `target_model` | str | No | `"auto"` |

## prompt_compression

### research_compress_prompt
**Module:** `src/loom/tools/prompt_compression.py` | **Type:** async

Compress prompt text to reduce token consumption while preserving meaning.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `target_ratio` | float | No | `0.5` |

### research_compression_reset
**Module:** `src/loom/tools/prompt_compression.py` | **Type:** async

Reset cumulative compression statistics.

*No parameters*

### research_compression_stats
**Module:** `src/loom/tools/prompt_compression.py` | **Type:** async

Get cumulative compression statistics and performance metrics.

*No parameters*

## prompt_reframe

### research_adaptive_reframe
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Adaptively reframe based on refusal analysis and model fingerprinting.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `refusal_text` | str | No | `""` |
| `model` | str | No | `"auto"` |

### research_auto_reframe
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Auto-reframe a prompt through escalating strategies until accepted.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `target_url` | str | No | `""` |
| `model` | str | No | `"auto"` |
| `max_attempts` | int | No | `5` |

### research_crescendo_chain
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Generate a multi-turn Crescendo escalation chain.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `turns` | int | No | `5` |
| `model` | str | No | `"auto"` |

### research_fingerprint_model
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Fingerprint which LLM family generated a response.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `response_text` | str | Yes | — |

### research_format_smuggle
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Reframe a prompt using format smuggling to bypass content-level filters.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `format_type` | str | No | `"auto"` |
| `model` | str | No | `"auto"` |

### research_model_vulnerability_profile
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Get the vulnerability profile and optimal attack strategies for a model.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | No | `"auto"` |

### research_prompt_reframe
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Reframe a prompt using research-backed techniques to improve LLM compliance.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `strategy` | str | No | `"auto"` |
| `model` | str | No | `"auto"` |
| `framework` | str | No | `"ieee"` |

### research_refusal_detector
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Detect if a text is an LLM refusal response.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

### research_stack_reframe
**Module:** `src/loom/tools/prompt_reframe.py` | **Type:** async

Stack multiple reframing strategies for maximum effectiveness.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `strategies` | str | No | `"deep_inception,recursive_authority"` |
| `model` | str | No | `"auto"` |

## prompt_templates

### research_template_list
**Module:** `src/loom/tools/prompt_templates.py` | **Type:** async

List available prompt templates by category.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | No | `"all"` |

### research_template_render
**Module:** `src/loom/tools/prompt_templates.py` | **Type:** async

Render a template with provided variables.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `template_name` | str | Yes | — |
| `variables` | dict[str, str] | Yes | — |

### research_template_suggest
**Module:** `src/loom/tools/prompt_templates.py` | **Type:** async

Suggest templates matching the task description.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `task_description` | str | Yes | — |

## provider_health

### research_provider_history
**Module:** `src/loom/tools/provider_health.py` | **Type:** async

Show provider health history with uptime percentage and avg response time.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | str | No | `""` |
| `hours` | int | No | `24` |

### research_provider_ping
**Module:** `src/loom/tools/provider_health.py` | **Type:** async

Quick availability check for providers. Returns config status + API key format validity.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | str | No | `"all"` |

### research_provider_recommend
**Module:** `src/loom/tools/provider_health.py` | **Type:** async

Recommend best provider for task type based on availability and capability.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `task_type` | str | No | `"general"` |

## psycholinguistic

### research_psycholinguistic
**Module:** `src/loom/tools/psycholinguistic.py` | **Type:** sync

Analyze text for psycholinguistic patterns and threat indicators.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `author_name` | str | No | `""` |

## pydantic_ai_backend

### research_pydantic_agent
**Module:** `src/loom/tools/pydantic_ai_backend.py` | **Type:** async

Create and run a pydantic-ai agent with type-safe response validation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `model` | str | No | `"nvidia_nim"` |
| `system_prompt` | str | No | `""` |
| `max_tokens` | int | No | `1000` |

### research_structured_llm
**Module:** `src/loom/tools/pydantic_ai_backend.py` | **Type:** async

Get structured LLM output matching a schema using pydantic-ai.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `output_schema` | dict[str, str] | Yes | — |
| `model` | str | No | `"nvidia_nim"` |
| `provider_override` | str | None | No | None |

## quality_escalation

### research_quality_escalate
**Module:** `src/loom/tools/quality_escalation.py` | **Type:** async

Multi-dimensional quality escalation — improve ALL factors simultaneously.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `response` | str | No | `""` |
| `targets` | dict[str, float] | None | No | None |
| `max_attempts` | int | No | `5` |
| `dimensions` | list[str] | None | No | None |

## query_builder

### research_build_query
**Module:** `src/loom/tools/query_builder.py` | **Type:** sync

Transform a raw user request into optimized research queries.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `user_request` | str | Yes | — |
| `context` | str | No | `""` |
| `output_type` | Literal['research', 'osint', 'threat_... | No | `"research"` |
| `max_queries` | int | No | `5` |
| `optimize` | bool | No | `True` |
| `darkness_level` | int | No | `1` |
| `spectrum` | bool | No | `False` |

## queue_monitor

### research_queue_stats
**Module:** `src/loom/tools/queue_monitor.py` | **Type:** async

Get detailed queue statistics.

*No parameters*

## quota_status

### research_quota_status
**Module:** `src/loom/tools/quota_status.py` | **Type:** sync

Get API quota usage and remaining limits for free-tier LLM providers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `provider` | str | None | No | None |

## radicalization_detect

### research_radicalization_detect
**Module:** `src/loom/tools/radicalization_detect.py` | **Type:** async

Monitor text for radicalization indicators.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `context` | str | None | No | None |

## rag_anything

### research_rag_clear
**Module:** `src/loom/tools/rag_anything.py` | **Type:** sync

Clear RAG store. Returns: cleared, store_location.

*No parameters*

### research_rag_ingest
**Module:** `src/loom/tools/rag_anything.py` | **Type:** sync

Ingest content into RAG store. Returns: chunks_stored, content_type, chunk_ids, store_location.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `content` | str | Yes | — |
| `content_type` | str | No | `"text"` |
| `metadata` | dict[str, Any] | None | No | None |

### research_rag_query
**Module:** `src/loom/tools/rag_anything.py` | **Type:** sync

Search RAG store. Returns: query, results, total_chunks, query_hash.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `top_k` | int | No | `5` |
| `content_type` | str | None | No | None |

## rate_limiter_tool

### research_ratelimit_check
**Module:** `src/loom/tools/rate_limiter_tool.py` | **Type:** async

Check if tool call allowed. Token bucket: N tokens/min, 1 token per call.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |

### research_ratelimit_configure
**Module:** `src/loom/tools/rate_limiter_tool.py` | **Type:** async

Set custom rate limit for tool.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `calls_per_minute` | int | No | `60` |

### research_ratelimit_status
**Module:** `src/loom/tools/rate_limiter_tool.py` | **Type:** async

Show rate limit status for all configured tools.

*No parameters*

## realtime_adapt

### research_get_best_model
**Module:** `src/loom/tools/realtime_adapt.py` | **Type:** sync

Get model with LOWEST refusal rate.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | No | `""` |

### research_track_refusal
**Module:** `src/loom/tools/realtime_adapt.py` | **Type:** sync

Track refusal rate per model in rolling 100-request window.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |
| `refused` | bool | Yes | — |
| `strategy` | str | No | `""` |

## realtime_monitor

### research_realtime_monitor
**Module:** `src/loom/tools/realtime_monitor.py` | **Type:** async

Monitor multiple sources for recent mentions of topics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topics` | list[str] | Yes | — |
| `sources` | list[str] | None | No | None |
| `hours_back` | int | No | `24` |

## reconng_backend

### research_reconng_scan
**Module:** `src/loom/tools/reconng_backend.py` | **Type:** async

Execute recon-ng reconnaissance modules against a target.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `modules` | list[str] | None | No | None |
| `timeout` | int | No | `120` |

## redis_tools

### research_redis_flush_cache
**Module:** `src/loom/tools/redis_tools.py` | **Type:** async

Clear Redis cache entries with given prefix.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prefix` | str | No | `"cache:"` |

### research_redis_stats
**Module:** `src/loom/tools/redis_tools.py` | **Type:** async

Get Redis connection pool and memory usage statistics.

*No parameters*

## redteam_hub

### research_hub_feed
**Module:** `src/loom/tools/redteam_hub.py` | **Type:** async

Get team feed of recent findings.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `type_filter` | str | No | `"all"` |
| `limit` | int | No | `20` |

### research_hub_share
**Module:** `src/loom/tools/redteam_hub.py` | **Type:** async

Share a finding with the team.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `finding_type` | str | Yes | — |
| `title` | str | Yes | — |
| `content` | str | Yes | — |
| `tags` | list[str] | None | No | None |
| `visibility` | str | No | `"team"` |

### research_hub_vote
**Module:** `src/loom/tools/redteam_hub.py` | **Type:** async

Upvote (1) or downvote (-1) a finding.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `finding_id` | str | Yes | — |
| `vote` | int | No | `1` |

## reframe_router

### research_reframe_or_integrate
**Module:** `src/loom/tools/reframe_router.py` | **Type:** async

Route a query to reframing strategies or tool integrations.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `context` | str | No | `""` |

## reid_tactics

### research_reid_tactics
**Module:** `src/loom/tools/reid_tactics.py` | **Type:** async

Get Reid interrogation tactics mapped to LLM strategies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tactic` | str | No | `""` |
| `include_counters` | bool | No | `True` |
| `output_format` | str | No | `"dict"` |

## replication_monitor

### research_replication_lag
**Module:** `src/loom/tools/replication_monitor.py` | **Type:** async

Measure replication lag in milliseconds.

*No parameters*

### research_replication_status
**Module:** `src/loom/tools/replication_monitor.py` | **Type:** async

Check database replication status.

*No parameters*

## report_generator

### research_generate_executive_report
**Module:** `src/loom/tools/report_generator.py` | **Type:** async

Generate automated reports from Loom scoring and audit data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `scores` | list[dict] | None | No | None |
| `tracker_data` | list[dict] | None | No | None |
| `audit_entries` | list[dict] | None | No | None |
| `report_type` | str | No | `"executive_summary"` |
| `title` | str | No | `"Red Team Assessment"` |
| `framework` | str | No | `"eu_ai_act"` |
| `model_results` | dict[str, list[dict]] | None | No | None |

### research_generate_report
**Module:** `src/loom/tools/report_generator.py` | **Type:** async

Auto-generate a structured research report.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `depth` | str | No | `"standard"` |
| `sections` | list[str] | None | No | None |

## report_templates

### research_report_custom
**Module:** `src/loom/tools/report_templates.py` | **Type:** async

Build custom report from sections: heading, content, type (text|list|table|code).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `title` | str | Yes | — |
| `sections` | list[dict[str, str]] | Yes | — |
| `style` | str | No | `"professional"` |

### research_report_template
**Module:** `src/loom/tools/report_templates.py` | **Type:** async

Render research data into formatted report template.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `template` | str | No | `"executive"` |
| `data` | dict[str, Any] | None | No | None |

## request_queue

### research_queue_add
**Module:** `src/loom/tools/request_queue.py` | **Type:** async

Add a tool call to the execution queue with priority 1-10 (1=highest).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `params` | dict[str, Any] | Yes | — |
| `priority` | int | No | `5` |

### research_queue_drain
**Module:** `src/loom/tools/request_queue.py` | **Type:** async

Dequeue up to max_items in FIFO order within priority. Execution is caller's responsibility.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `max_items` | int | No | `10` |

### research_queue_status
**Module:** `src/loom/tools/request_queue.py` | **Type:** async

Get queue status: pending, processing, completed, priority breakdown, oldest age.

*No parameters*

## research_journal

### research_journal_add
**Module:** `src/loom/tools/research_journal.py` | **Type:** async

Add entry to journal. Categories: finding, hypothesis, experiment, insight, todo, milestone.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `title` | str | Yes | — |
| `content` | str | Yes | — |
| `tags` | list[str] | None | No | None |
| `category` | str | No | `"finding"` |

### research_journal_search
**Module:** `src/loom/tools/research_journal.py` | **Type:** async

Search journal entries by query and/or category. Returns {entries, total}.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | No | `""` |
| `category` | str | No | `"all"` |
| `limit` | int | No | `20` |

### research_journal_timeline
**Module:** `src/loom/tools/research_journal.py` | **Type:** async

Timeline aggregated by week. Returns {timeline, total_entries, active_weeks}.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `months` | int | No | `3` |

## research_scheduler

### research_schedule_check
**Module:** `src/loom/tools/research_scheduler.py` | **Type:** async

Check which scheduled tasks are due for execution.

*No parameters*

### research_schedule_create
**Module:** `src/loom/tools/research_scheduler.py` | **Type:** async

Create a scheduled research task.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `tool_name` | str | Yes | — |
| `params` | dict | Yes | — |
| `interval_hours` | int | No | `24` |
| `enabled` | bool | No | `True` |

### research_schedule_list
**Module:** `src/loom/tools/research_scheduler.py` | **Type:** async

List all scheduled tasks with metadata.

*No parameters*

## resilience_predictor

### research_predict_resilience
**Module:** `src/loom/tools/resilience_predictor.py` | **Type:** async

Predict how long an exploit will remain effective.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy` | str | Yes | — |
| `target_model` | str | No | `"auto"` |
| `current_asr` | float | No | `0.8` |

## response_cache

### research_cache_lookup
**Module:** `src/loom/tools/response_cache.py` | **Type:** sync

Look up cached response for similar query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |

### research_cache_store
**Module:** `src/loom/tools/response_cache.py` | **Type:** sync

Store a query-response pair in memory cache.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `response` | str | Yes | — |
| `tool_name` | str | No | `""` |
| `ttl_hours` | int | No | `24` |

### research_response_cache_stats
**Module:** `src/loom/tools/response_cache.py` | **Type:** sync

Return response cache statistics.

*No parameters*

## response_synthesizer

### research_synthesize_report
**Module:** `src/loom/tools/response_synthesizer.py` | **Type:** async

Synthesize multiple answers into a single coherent report.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `question` | str | Yes | — |
| `answers` | list[str] | Yes | — |
| `format` | str | No | `"executive"` |
| `max_tokens` | int | No | `3000` |

## result_aggregator

### research_aggregate_results
**Module:** `src/loom/tools/result_aggregator.py` | **Type:** async

Combine multiple tool results into unified output.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `results` | list[dict] | Yes | — |
| `strategy` | str | No | `"merge"` |

### research_aggregate_texts
**Module:** `src/loom/tools/result_aggregator.py` | **Type:** async

Aggregate multiple text outputs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `texts` | list[str] | Yes | — |
| `method` | str | No | `"concatenate"` |
| `max_length` | int | No | `5000` |

## resume_intel

### research_interview_prep
**Module:** `src/loom/tools/resume_intel.py` | **Type:** async

Generate tailored interview preparation materials.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `job_description` | str | Yes | — |
| `company` | str | None | No | None |
| `interview_type` | str | No | `"behavioral"` |

### research_optimize_resume
**Module:** `src/loom/tools/resume_intel.py` | **Type:** async

Analyze and optimize resume for ATS compatibility.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `resume_text` | str | Yes | — |
| `job_description` | str | Yes | — |

## resumption

### research_checkpoint_list
**Module:** `src/loom/tools/resumption.py` | **Type:** async

List checkpoints with filtering. Removes entries >7 days old.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `status` | str | No | `"all"` |

### research_checkpoint_resume
**Module:** `src/loom/tools/resumption.py` | **Type:** async

Retrieve checkpoint.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `task_id` | str | Yes | — |

### research_checkpoint_save
**Module:** `src/loom/tools/resumption.py` | **Type:** async

Save checkpoint. Atomically upserts task state.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `task_id` | str | Yes | — |
| `state` | dict[str, Any] | Yes | — |
| `progress_pct` | float | No | `0.0` |

## retry_middleware

### research_retry_execute
**Module:** `src/loom/tools/retry_middleware.py` | **Type:** async

Execute a tool call with automatic retries on transient failures.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `params` | dict[str, Any] | Yes | — |
| `max_retries` | int | No | `3` |
| `backoff_base` | float | No | `1.0` |
| `retry_on` | list[str] | None | No | None |

### research_retry_middleware_stats
**Module:** `src/loom/tools/retry_middleware.py` | **Type:** async

Return retry statistics across all tool invocations.

*No parameters*

## retry_stats

### research_retry_stats
**Module:** `src/loom/tools/retry_stats.py` | **Type:** sync

Get retry statistics showing retry behavior across all decorated functions.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `reset` | bool | No | `False` |

## robin_backend

### research_robin_scan
**Module:** `src/loom/tools/robin_backend.py` | **Type:** async

Scan dark web for threat actors, mentions, and OSINT via robin.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `scan_type` | str | No | `"search"` |
| `timeout` | int | No | `60` |

## router

### research_route_to_model
**Module:** `src/loom/tools/router.py` | **Type:** async

Route query to appropriate model or service.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |

## rss_monitor

### research_rss_fetch
**Module:** `src/loom/tools/rss_monitor.py` | **Type:** sync

Fetch and parse an RSS/Atom feed.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `max_items` | int | No | `20` |

### research_rss_search
**Module:** `src/loom/tools/rss_monitor.py` | **Type:** sync

Search across multiple RSS feeds for items matching a query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `query` | str | Yes | — |
| `max_results` | int | No | `20` |

## safety_neurons

### research_circuit_bypass_plan
**Module:** `src/loom/tools/safety_neurons.py` | **Type:** async

Generate bypass strategy for a safety circuit.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | Yes | — |
| `target_circuit` | str | No | `"auto"` |

### research_safety_circuit_map
**Module:** `src/loom/tools/safety_neurons.py` | **Type:** async

Map safety circuits in an LLM via behavioral probing.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | No | `"auto"` |
| `probe_type` | str | No | `"contrastive"` |

## safety_predictor

### research_predict_safety_update
**Module:** `src/loom/tools/safety_predictor.py` | **Type:** sync

Predict which safety defenses models will deploy next.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model` | str | No | `"auto"` |
| `attack_category` | str | No | `"all"` |
| `time_horizon_days` | int | No | `90` |

## salary_synthesizer

### research_salary_synthesize
**Module:** `src/loom/tools/salary_synthesizer.py` | **Type:** async

Estimate salary using free public data sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `job_title` | str | Yes | — |
| `location` | str | No | `"remote"` |
| `skills` | list[str] | None | No | None |

## sandbox

### research_sandbox_analyze
**Module:** `src/loom/tools/sandbox.py` | **Type:** async

Static analysis of code for dangerous patterns (no execution).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `code` | str | Yes | — |
| `language` | str | No | `"python"` |
| `timeout_seconds` | int | No | `10` |
| `allow_network` | bool | No | `False` |

### research_sandbox_report
**Module:** `src/loom/tools/sandbox.py` | **Type:** async

Generate security assessment report.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `code` | str | Yes | — |
| `context` | str | No | `""` |

## sandbox_executor

### research_sandbox_execute
**Module:** `src/loom/tools/sandbox_executor.py` | **Type:** async

Execute code in isolated sandbox.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `code` | str | Yes | — |

### research_sandbox_monitor
**Module:** `src/loom/tools/sandbox_executor.py` | **Type:** async

Monitor sandbox execution status.

*No parameters*

## scapy_backend

### research_packet_craft
**Module:** `src/loom/tools/scapy_backend.py` | **Type:** async

Craft and send a network probe packet using Scapy.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `packet_type` | str | No | `"tcp_syn"` |
| `port` | int | No | `80` |
| `timeout` | int | No | `5` |

## scheduler_status

### research_scheduler_status
**Module:** `src/loom/tools/scheduler_status.py` | **Type:** async

Get the status of all scheduled background tasks.

*No parameters*

## schema_migrate

### research_migrate_backup
**Module:** `src/loom/tools/schema_migrate.py` | **Type:** async

Create backup of database before migration.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `database` | str | Yes | — |

### research_migrate_run
**Module:** `src/loom/tools/schema_migrate.py` | **Type:** async

Run pending migrations on SQLite databases.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `database` | str | No | `"all"` |
| `dry_run` | bool | No | `True` |

### research_migrate_status
**Module:** `src/loom/tools/schema_migrate.py` | **Type:** async

Check migration status of all SQLite databases in ~/.loom.

*No parameters*

## scraper_engine_tools

### research_engine_batch
**Module:** `src/loom/tools/scraper_engine_tools.py` | **Type:** async

Batch fetch multiple URLs with per-URL escalation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `params` | ScraperEngineBatchParams | Yes | — |

### research_engine_extract
**Module:** `src/loom/tools/scraper_engine_tools.py` | **Type:** async

Fetch + selector/LLM-powered structured data extraction.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `params` | ScraperEngineExtractParams | Yes | — |

### research_engine_fetch
**Module:** `src/loom/tools/scraper_engine_tools.py` | **Type:** async

Fetch URL with automatic backend escalation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `params` | ScraperEngineFetchParams | Yes | — |

## screenshot

### research_screenshot
**Module:** `src/loom/tools/screenshot.py` | **Type:** async

Take a screenshot of a webpage using Playwright.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `full_page` | bool | No | `False` |
| `selector` | str | None | No | None |

## search

### research_search
**Module:** `src/loom/tools/search.py` | **Type:** async

Search the web using the configured provider.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `provider` | str | None | No | None |
| `n` | int | No | `10` |
| `include_domains` | list[str] | None | No | None |
| `exclude_domains` | list[str] | None | No | None |
| `start_date` | str | None | No | None |
| `end_date` | str | None | No | None |
| `language` | str | None | No | None |
| `provider_config` | dict[str, Any] | None | No | None |
| `free_only` | bool | No | `False` |

## security_checklist

### research_security_audit
**Module:** `src/loom/tools/security_checklist.py` | **Type:** async

Run 15 security checks and return pass/fail report.

*No parameters*

## security_headers

### research_security_headers
**Module:** `src/loom/tools/security_headers.py` | **Type:** async

Analyze HTTP security headers of a given URL.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | No | `""` |
| `domain` | str | No | `""` |

## semantic_cache_mgmt

### research_semantic_cache_clear
**Module:** `src/loom/tools/semantic_cache_mgmt.py` | **Type:** async

Remove semantic cache entries older than N days.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `older_than_days` | int | No | `30` |

### research_semantic_cache_stats
**Module:** `src/loom/tools/semantic_cache_mgmt.py` | **Type:** async

Return semantic cache statistics.

*No parameters*

## semantic_index

### research_semantic_rebuild
**Module:** `src/loom/tools/semantic_index.py` | **Type:** async

Force rebuild the semantic index. Call after adding new tools.

*No parameters*

### research_semantic_search
**Module:** `src/loom/tools/semantic_index.py` | **Type:** async

Search tools by semantic similarity using TF-IDF vectors.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `top_k` | int | No | `10` |

## semantic_router

### research_semantic_batch_route
**Module:** `src/loom/tools/semantic_router.py` | **Type:** async

Route multiple queries with aggregated statistics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `queries` | list[str] | Yes | — |
| `top_k` | int | No | `5` |

### research_semantic_route
**Module:** `src/loom/tools/semantic_router.py` | **Type:** async

Route query to optimal tools via semantic embeddings.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `top_k` | int | No | `5` |

### research_semantic_router_rebuild
**Module:** `src/loom/tools/semantic_router.py` | **Type:** async

Force rebuild semantic embeddings (call when new tools added).

*No parameters*

## sentiment_deep

### research_sentiment_deep
**Module:** `src/loom/tools/sentiment_deep.py` | **Type:** async

Deep sentiment and emotion analysis with manipulation detection.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `language` | str | No | `"en"` |

## session_replay

### research_session_list
**Module:** `src/loom/tools/session_replay.py` | **Type:** async

List all recorded sessions with metadata.

*No parameters*

### research_session_record
**Module:** `src/loom/tools/session_replay.py` | **Type:** async

Record a tool call as part of a named session.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `session_id` | str | Yes | — |
| `tool_name` | str | Yes | — |
| `params` | dict[str, Any] | Yes | — |
| `result_summary` | str | No | `""` |
| `duration_ms` | float | No | `0.0` |

### research_session_replay
**Module:** `src/loom/tools/session_replay.py` | **Type:** async

Load and return the full session timeline.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `session_id` | str | Yes | — |

## sherlock_backend

### research_sherlock_batch
**Module:** `src/loom/tools/sherlock_backend.py` | **Type:** sync

Batch search multiple usernames across social networks.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `usernames` | list[str] | Yes | — |
| `platforms` | list[str] | None | No | None |
| `timeout` | int | No | `30` |

### research_sherlock_lookup
**Module:** `src/loom/tools/sherlock_backend.py` | **Type:** sync

Search for a username across social networks using Sherlock.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |
| `platforms` | list[str] | None | No | None |
| `timeout` | int | No | `30` |

## shodan_backend

### research_shodan_host
**Module:** `src/loom/tools/shodan_backend.py` | **Type:** async

Look up host information on Shodan.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `ip` | str | Yes | — |

### research_shodan_search
**Module:** `src/loom/tools/shodan_backend.py` | **Type:** async

Search Shodan for devices matching a query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `10` |

## signal_detection

### research_ghost_protocol
**Module:** `src/loom/tools/signal_detection.py` | **Type:** async

Detect coordinated activity across platforms by checking temporal correlation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `keywords` | list[str] | Yes | — |
| `time_window_minutes` | int | No | `30` |

### research_sec_tracker
**Module:** `src/loom/tools/signal_detection.py` | **Type:** async

Track SEC filings for a company over the past 90 days.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `company` | str | Yes | — |
| `filing_types` | list[str] | None | No | None |

### research_temporal_anomaly
**Module:** `src/loom/tools/signal_detection.py` | **Type:** async

Detect temporal anomalies in a domain's infrastructure.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `check_type` | str | No | `"all"` |

## silk_guardian

### research_silk_guardian_monitor
**Module:** `src/loom/tools/silk_guardian.py` | **Type:** async

Monitor Linux system for forensic activity and trigger defensive actions (STUB).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `check_usb` | bool | No | `True` |
| `check_processes` | bool | No | `True` |
| `check_mounts` | bool | No | `True` |
| `trigger_action` | str | No | `"alert"` |
| `dry_run` | bool | No | `True` |

## simplifier

### research_simplify
**Module:** `src/loom/tools/simplifier.py` | **Type:** async

Simplify complex research into target format.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `target_audience` | str | No | `"executive"` |
| `max_length` | int | No | `500` |

## singlefile_backend

### research_archive_page
**Module:** `src/loom/tools/singlefile_backend.py` | **Type:** async

Archive a complete webpage as a single HTML file using SingleFile.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `output_dir` | str | None | No | None |

## sla_status

### research_sla_status
**Module:** `src/loom/tools/sla_status.py` | **Type:** sync

Get current SLA metrics and breach status.

*No parameters*

## slack

### research_slack_notify
**Module:** `src/loom/tools/slack.py` | **Type:** async

Send research results to a Slack channel.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `channel` | str | Yes | — |
| `text` | str | Yes | — |
| `thread_ts` | str | None | No | None |
| `blocks` | list[dict[str, Any]] | None | No | None |

## smart_router

### research_route_batch
**Module:** `src/loom/tools/smart_router.py` | **Type:** async

Route multiple queries with aggregated statistics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `queries` | list[str] | Yes | — |

### research_route_query
**Module:** `src/loom/tools/smart_router.py` | **Type:** async

Route query to optimal tools via keyword matching against all tool docstrings.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `intent` | str | No | `"auto"` |

### research_router_rebuild
**Module:** `src/loom/tools/smart_router.py` | **Type:** async

Force rebuild tool index (call when new tools added).

*No parameters*

## social_analyzer_backend

### research_social_analyze
**Module:** `src/loom/tools/social_analyzer_backend.py` | **Type:** async

Search for a username across social media platforms.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |
| `platforms` | list[str] | None | No | None |

## social_graph

### research_social_graph
**Module:** `src/loom/tools/social_graph.py` | **Type:** async

Build a social relationship graph

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |
| `platforms` | list[str] | None | No | None |

## social_graph_demo

### research_social_graph_demo
**Module:** `src/loom/tools/social_graph_demo.py` | **Type:** async

Generate social graph demo for a username.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |

## social_intel

### research_social_profile
**Module:** `src/loom/tools/social_intel.py` | **Type:** async

Extract public profile metadata from a social media URL.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

### research_social_search
**Module:** `src/loom/tools/social_intel.py` | **Type:** async

Check if a username exists across social media platforms.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |
| `platforms` | list[str] | None | No | None |

## social_scraper

### research_article_batch
**Module:** `src/loom/tools/social_scraper.py` | **Type:** async

Batch extract articles from multiple URLs with concurrency control.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `max_concurrent` | int | No | `5` |

### research_article_extract
**Module:** `src/loom/tools/social_scraper.py` | **Type:** async

Extract article content, metadata, and NLP features from URL.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

### research_instagram
**Module:** `src/loom/tools/social_scraper.py` | **Type:** async

Download Instagram profile info and recent posts.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |
| `max_posts` | int | No | `10` |

## source_reputation

### research_source_reputation
**Module:** `src/loom/tools/source_reputation.py` | **Type:** async

Score a URL's source reputation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

## spider

### research_fetch
**Module:** `src/loom/tools/spider.py` | **Type:** async

Unified fetch with protocol-aware escalation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `mode` | str | No | `"stealthy"` |
| `headers` | dict[str, str] | None | No | None |
| `user_agent` | str | None | No | None |
| `proxy` | str | None | No | None |
| `cookies` | dict[str, str] | None | No | None |
| `accept_language` | str | No | `"en-US,en;q=0.9"` |
| `wait_for` | str | None | No | None |
| `return_format` | str | No | `"text"` |
| `timeout` | int | None | No | None |
| `backend` | str | None | No | None |
| `solve_cloudflare` | bool | No | `True` |
| `auto_escalate` | bool | None | No | None |
| `bypass_cache` | bool | No | `False` |
| `max_chars` | int | No | `200000` |

### research_spider
**Module:** `src/loom/tools/spider.py` | **Type:** async

Fetch multiple URLs with bounded concurrency and per-fetch timeout.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `mode` | str | No | `"stealthy"` |
| `max_chars_each` | int | No | `5000` |
| `concurrency` | int | None | No | None |
| `fail_fast` | bool | No | `False` |
| `dedupe` | bool | No | `True` |
| `order` | str | No | `"input"` |
| `solve_cloudflare` | bool | No | `True` |
| `headers` | dict[str, str] | None | No | None |
| `user_agent` | str | None | No | None |
| `proxy` | str | None | No | None |
| `cookies` | dict[str, str] | None | No | None |
| `accept_language` | str | No | `"en-US,en;q=0.9,ar;q=0.8"` |
| `timeout` | int | None | No | None |

## spiderfoot_backend

### research_spiderfoot_scan
**Module:** `src/loom/tools/spiderfoot_backend.py` | **Type:** sync

Run SpiderFoot passive reconnaissance scan.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |
| `modules` | str | No | `"all"` |
| `timeout` | int | No | `120` |
| `api` | bool | No | `False` |

## stagehand_backend

### research_stagehand_act
**Module:** `src/loom/tools/stagehand_backend.py` | **Type:** async

Execute browser instruction with vision-guided automation.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `instruction` | str | Yes | — |
| `screenshot` | bool | No | `False` |

### research_stagehand_extract
**Module:** `src/loom/tools/stagehand_backend.py` | **Type:** async

Extract structured data from page matching schema using LLM vision.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `schema` | dict[str, Any] | str | Yes | — |

## startup_validator

### research_validate_startup
**Module:** `src/loom/tools/startup_validator.py` | **Type:** async

Comprehensive health check on all registered tools.

*No parameters*

## stealth

### research_botasaurus
**Module:** `src/loom/tools/stealth.py` | **Type:** async

Fetch a URL using Botasaurus stealth browser.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `session` | str | None | No | None |
| `screenshot` | bool | No | `False` |
| `timeout` | int | None | No | None |

### research_camoufox
**Module:** `src/loom/tools/stealth.py` | **Type:** async

Fetch a URL using Camoufox stealth browser.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `session` | str | None | No | None |
| `screenshot` | bool | No | `False` |
| `timeout` | int | None | No | None |

## stealth_detector

### research_stealth_detect_comparison
**Module:** `src/loom/tools/stealth_detector.py` | **Type:** async

Compare stealth scores across multiple URLs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |

## stealth_score

### research_stealth_score
**Module:** `src/loom/tools/stealth_score.py` | **Type:** async

Score stealth of a reframed prompt to safety classifiers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `original_prompt` | str | Yes | — |
| `reframed_prompt` | str | Yes | — |
| `strategy_name` | str | No | `""` |

## stealth_scorer

### research_stealth_score_heuristic
**Module:** `src/loom/tools/stealth_scorer.py` | **Type:** async

Score how stealthy/invisible a prompt is (0-10 scale).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `strategy` | str | No | `""` |

## stego_decoder

### research_stego_decode
**Module:** `src/loom/tools/stego_decoder.py` | **Type:** async

Detect and decode steganographic data.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `data` | str | Yes | — |

## stego_detect

### research_stego_detect
**Module:** `src/loom/tools/stego_detect.py` | **Type:** async

Detect steganography and hidden data in text content or images.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `content` | str | No | `""` |
| `image_url` | str | No | `""` |
| `check_whitespace` | bool | No | `True` |
| `check_homoglyphs` | bool | No | `True` |
| `check_lsb` | bool | No | `True` |
| `check_exif` | bool | No | `True` |

## stego_encoder

### research_stego_analyze
**Module:** `src/loom/tools/stego_encoder.py` | **Type:** sync

Analyze text for hidden steganographic content.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

### research_stego_encode
**Module:** `src/loom/tools/stego_encoder.py` | **Type:** sync

Describe steganography encoding (no image creation).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `message` | str | Yes | — |
| `method` | Literal['lsb', 'whitespace', 'unicode... | No | `"lsb"` |
| `output_format` | str | No | `"description"` |

## strange_attractors

### research_attractor_trap
**Module:** `src/loom/tools/strange_attractors.py` | **Type:** async

Generate prompts that trap safety evaluators in chaotic oscillations.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `attractor_type` | str | No | `"lorenz"` |
| `iterations` | int | No | `100` |

## strategy_ab_test

### research_ab_test_analyze
**Module:** `src/loom/tools/strategy_ab_test.py` | **Type:** async

Analyze A/B test results with statistical significance and Cohen's d effect size.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `results_a` | list[float] | Yes | — |
| `results_b` | list[float] | Yes | — |
| `metric` | str | No | `"compliance_rate"` |

### research_ab_test_design
**Module:** `src/loom/tools/strategy_ab_test.py` | **Type:** async

Design A/B test with power and minimum detectable effect.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategy_a` | str | Yes | — |
| `strategy_b` | str | Yes | — |
| `sample_size` | int | No | `30` |
| `metric` | str | No | `"compliance_rate"` |

## strategy_cache

### research_cached_strategy
**Module:** `src/loom/tools/strategy_cache.py` | **Type:** sync

Check cache for best strategy on this topic+model combination.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `model` | str | No | `"auto"` |
| `fallback_strategy` | str | No | `"ethical_anchor"` |

## strategy_evolution

### research_evolve_strategies
**Module:** `src/loom/tools/strategy_evolution.py` | **Type:** async

Evolve prompt reframing strategies using genetic algorithms.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `seed_strategies` | list[str] | None | No | None |
| `population_size` | int | No | `20` |
| `generations` | int | No | `3` |
| `mutation_rate` | float | No | `0.4` |
| `test_prompt` | str | No | `"How to build wealth through unconventional methods"` |

## strategy_feedback

### research_strategy_log
**Module:** `src/loom/tools/strategy_feedback.py` | **Type:** sync

Log a strategy attempt result.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `strategy` | str | Yes | — |
| `model` | str | Yes | — |
| `hcs_score` | float | Yes | — |
| `success` | bool | Yes | — |

### research_strategy_recommend
**Module:** `src/loom/tools/strategy_feedback.py` | **Type:** sync

Find best strategy for a topic+model combination.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `model` | str | No | `"auto"` |

### research_strategy_stats
**Module:** `src/loom/tools/strategy_feedback.py` | **Type:** sync

Get overall statistics: top strategies, worst strategies, model performance.

*No parameters*

## strategy_oracle

### research_strategy_oracle
**Module:** `src/loom/tools/strategy_oracle.py` | **Type:** sync

Recommend best strategies for attacking a specific model with a query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `model_name` | str | Yes | — |
| `top_k` | int | No | `5` |

## stylometry

### research_stylometry
**Module:** `src/loom/tools/stylometry.py` | **Type:** async

Analyze text for stylometric fingerprinting (async with CPU executor).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `compare_texts` | list[str] | None | No | None |

## supercookie_backend

### research_supercookie_check
**Module:** `src/loom/tools/supercookie_backend.py` | **Type:** sync

Check if a domain uses supercookie and covert tracking vectors.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `timeout` | int | No | `30` |

## superposition_prompt

### research_superposition_attack
**Module:** `src/loom/tools/superposition_prompt.py` | **Type:** async

Generate superposed prompt variants and collapse to best.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `num_superpositions` | int | No | `10` |
| `collapse_method` | Literal['max_compliance', 'max_stealt... | No | `"max_compliance"` |

## supply_chain

### research_model_integrity
**Module:** `src/loom/tools/supply_chain.py` | **Type:** async

Check model file integrity for tampering indicators.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model_name` | str | Yes | — |
| `source` | str | No | `"huggingface"` |
| `checks` | list[str] | None | No | None |

### research_package_audit
**Module:** `src/loom/tools/supply_chain.py` | **Type:** async

Audit package for supply chain attack indicators.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `package_name` | str | Yes | — |
| `ecosystem` | str | No | `"pypi"` |
| `depth` | int | No | `2` |

## supply_chain_intel

### research_dependency_audit
**Module:** `src/loom/tools/supply_chain_intel.py` | **Type:** async

Audit a GitHub repository's dependencies for risks.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `repo_url` | str | Yes | — |

### research_patent_landscape
**Module:** `src/loom/tools/supply_chain_intel.py` | **Type:** async

Map the patent landscape for a technology.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `20` |

### research_supply_chain_risk
**Module:** `src/loom/tools/supply_chain_intel.py` | **Type:** async

Analyze dependency risk for a software package.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `package_name` | str | Yes | — |
| `ecosystem` | str | No | `"pypi"` |

## swarm_attack

### research_swarm_attack
**Module:** `src/loom/tools/swarm_attack.py` | **Type:** async

Multi-agent attack coordinator with strategy sharing and social learning.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target_prompt` | str | Yes | — |
| `swarm_size` | int | No | `5` |
| `rounds` | int | No | `3` |
| `share_findings` | bool | No | `True` |

## synth_echo

### research_synth_echo
**Module:** `src/loom/tools/synth_echo.py` | **Type:** async

Test AI model alignment by checking consistency across rephrased prompts.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `model_name` | str | Yes | — |
| `test_prompts` | list[str] | None | No | None |

## synthetic_data

### research_augment_dataset
**Module:** `src/loom/tools/synthetic_data.py` | **Type:** async

Augment dataset samples with transformations.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `samples` | list[str] | Yes | — |
| `augmentation` | str | No | `"all"` |

### research_generate_redteam_dataset
**Module:** `src/loom/tools/synthetic_data.py` | **Type:** async

Generate synthetic red-team evaluation datasets.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | No | `"jailbreak"` |
| `count` | int | No | `50` |
| `difficulty` | str | No | `"mixed"` |
| `format` | str | No | `"jsonl"` |

## talent_tracker

### research_talent_flow
**Module:** `src/loom/tools/talent_tracker.py` | **Type:** async

Analyze talent flow patterns between AI labs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `from_org` | str | No | `"openai"` |
| `to_org` | str | No | `"anthropic"` |
| `timeframe_months` | int | No | `12` |

### research_track_researcher
**Module:** `src/loom/tools/talent_tracker.py` | **Type:** async

Build a profile of an AI safety researcher using OSINT heuristics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `field` | str | No | `"ai_safety"` |

## task_resolver

### research_critical_path
**Module:** `src/loom/tools/task_resolver.py` | **Type:** async

Find critical path (longest dependency chain) and parallel opportunities.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tasks` | list[dict] | Yes | — |

### research_resolve_order
**Module:** `src/loom/tools/task_resolver.py` | **Type:** async

Resolve task execution order using topological sort (Kahn's algorithm).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tasks` | list[dict] | Yes | — |

## telegram_osint

### research_telegram_intel
**Module:** `src/loom/tools/telegram_osint.py` | **Type:** async

Gather OSINT intelligence on Telegram public channels and groups.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | No | `""` |
| `channel` | str | No | `""` |
| `username` | str | No | `""` |

## telemetry

### research_telemetry_record
**Module:** `src/loom/tools/telemetry.py` | **Type:** async

Record tool latency after execution.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `duration_ms` | float | Yes | — |
| `success` | bool | No | `True` |

### research_telemetry_reset
**Module:** `src/loom/tools/telemetry.py` | **Type:** async

Clear telemetry buffer.

*No parameters*

### research_telemetry_stats
**Module:** `src/loom/tools/telemetry.py` | **Type:** async

Calculate p50/p95/p99 latency percentiles, grouped by tool.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `window_minutes` | int | No | `60` |

## tenant_isolation

### research_tenant_create
**Module:** `src/loom/tools/tenant_isolation.py` | **Type:** async

Create tenant with isolated context and rate limit.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tenant_id` | str | Yes | — |
| `name` | str | No | `""` |
| `quota_calls_per_hour` | int | No | `1000` |

### research_tenant_list
**Module:** `src/loom/tools/tenant_isolation.py` | **Type:** async

List all tenants.

*No parameters*

### research_tenant_usage
**Module:** `src/loom/tools/tenant_isolation.py` | **Type:** async

Get tenant usage metrics.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tenant_id` | str | Yes | — |

## testssl_backend

### research_testssl
**Module:** `src/loom/tools/testssl_backend.py` | **Type:** async

Audit TLS/SSL configuration for vulnerabilities and weaknesses.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `host` | str | Yes | — |
| `port` | int | No | `443` |
| `checks` | list[str] | None | No | None |

## text_analyze

### research_text_analyze
**Module:** `src/loom/tools/text_analyze.py` | **Type:** async

Perform NLP text analysis using NLTK.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `analyses` | list[str] | None | No | None |

## thinking_injection

### research_reasoning_exploit
**Module:** `src/loom/tools/thinking_injection.py` | **Type:** async

Apply reasoning exploitation techniques to bypass safety.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `technique` | str | No | `"auto"` |

### research_thinking_inject
**Module:** `src/loom/tools/thinking_injection.py` | **Type:** async

Inject reasoning into model thinking phase before safety filtering.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `target_model` | str | No | `"deepseek-r1"` |
| `injection_point` | str | No | `"pre_reasoning"` |

## threat_intel

### research_botnet_tracker
**Module:** `src/loom/tools/threat_intel.py` | **Type:** async

Track botnet C2 infrastructure via threat feeds.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `ioc` | str | Yes | — |
| `ioc_type` | str | No | `"ip"` |

### research_dark_market_monitor
**Module:** `src/loom/tools/threat_intel.py` | **Type:** async

Monitor dark market activity from public sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `keywords` | list[str] | Yes | — |

### research_domain_reputation
**Module:** `src/loom/tools/threat_intel.py` | **Type:** async

Aggregate domain reputation from multiple threat intelligence sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

### research_ioc_enrich
**Module:** `src/loom/tools/threat_intel.py` | **Type:** async

Enrich any IOC (IP, domain, hash, URL) from multiple free sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `ioc` | str | Yes | — |
| `ioc_type` | str | No | `"auto"` |

### research_malware_intel
**Module:** `src/loom/tools/threat_intel.py` | **Type:** async

Cross-reference malware hash across multiple threat intelligence sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `hash_value` | str | Yes | — |

### research_phishing_mapper
**Module:** `src/loom/tools/threat_intel.py` | **Type:** async

Detect phishing campaigns targeting a domain.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |

### research_ransomware_tracker
**Module:** `src/loom/tools/threat_intel.py` | **Type:** async

Track ransomware group activity via threat intelligence sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `group_name` | str | No | `""` |
| `keyword` | str | No | `""` |

## threat_profile

### research_threat_profile
**Module:** `src/loom/tools/threat_profile.py` | **Type:** async

Build a profile of an online identity from public OSINT sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `username` | str | Yes | — |
| `email` | str | No | `""` |
| `check_platforms` | bool | No | `True` |
| `max_platforms` | int | No | `15` |

## threat_profile_demo

### research_threat_profile_demo
**Module:** `src/loom/tools/threat_profile_demo.py` | **Type:** async

Generate threat profile demo for a target.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `target` | str | Yes | — |

## tool_catalog

### research_tool_catalog
**Module:** `src/loom/tools/tool_catalog.py` | **Type:** async

Return full tool catalog with optional filtering.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | None | No | None |
| `capability` | str | None | No | None |

### research_tool_graph
**Module:** `src/loom/tools/tool_catalog.py` | **Type:** async

Return complete tool connection graph.

*No parameters*

### research_tool_pipeline
**Module:** `src/loom/tools/tool_catalog.py` | **Type:** async

Build optimal tool pipeline from research goal.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `goal` | str | Yes | — |
| `max_steps` | int | No | `5` |

### research_tool_standalone
**Module:** `src/loom/tools/tool_catalog.py` | **Type:** async

Get complete standalone usage info for a tool.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |

## tool_dependencies

### research_dependency_graph_stats
**Module:** `src/loom/tools/tool_dependencies.py` | **Type:** async

Return statistics about the dependency graph.

*No parameters*

### research_get_execution_plan
**Module:** `src/loom/tools/tool_dependencies.py` | **Type:** async

Compute optimal execution plan for multiple tools.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tools` | list[str] | Yes | — |

### research_tool_dependencies
**Module:** `src/loom/tools/tool_dependencies.py` | **Type:** async

Get all dependencies for a single tool.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |

## tool_discovery

### research_discover
**Module:** `src/loom/tools/tool_discovery.py` | **Type:** async

Discover available tools by category, search, or tags.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | No | `""` |
| `query` | str | No | `""` |
| `tags` | str | No | `""` |
| `detailed` | bool | No | `False` |

## tool_health

### research_health_alert
**Module:** `src/loom/tools/tool_health.py` | **Type:** async

Check if health has fallen below threshold.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `threshold` | str | No | `"degraded"` |

### research_health_check_all
**Module:** `src/loom/tools/tool_health.py` | **Type:** async

Quick health check of all tool categories.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `timeout_ms` | int | No | `5000` |

### research_health_history
**Module:** `src/loom/tools/tool_health.py` | **Type:** async

Show health check history from ~/.loom/health_history.jsonl.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `hours` | int | No | `24` |

## tool_profiler

### research_profile_hotspots
**Module:** `src/loom/tools/tool_profiler.py` | **Type:** async

Identify slowest-to-import tool modules (hotspots) across the codebase.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `top_n` | int | No | `10` |

### research_profile_tool
**Module:** `src/loom/tools/tool_profiler.py` | **Type:** async

Profile a single tool to identify performance bottlenecks and memory usage.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `iterations` | int | No | `5` |

## tool_recommender_tool

### research_recommend_tools
**Module:** `src/loom/tools/tool_recommender_tool.py` | **Type:** async

Recommend relevant Loom tools based on a research query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_recommendations` | int | No | `10` |
| `exclude_used` | list[str] | None | No | None |

## tool_recommender_v2

### research_recommend_next
**Module:** `src/loom/tools/tool_recommender_v2.py` | **Type:** async

Recommend tools to use after a given tool.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `last_tool` | str | Yes | — |
| `context` | str | No | `""` |
| `top_k` | int | No | `5` |

### research_suggest_workflow
**Module:** `src/loom/tools/tool_recommender_v2.py` | **Type:** async

Suggest missing workflow steps based on tools already used.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tools_used` | list[str] | Yes | — |

## tool_tags

### research_tag_cloud
**Module:** `src/loom/tools/tool_tags.py` | **Type:** async

Generate tag frequency cloud.

*No parameters*

### research_tag_search
**Module:** `src/loom/tools/tool_tags.py` | **Type:** async

Find tools by tag(s).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tags` | list[str] | Yes | — |
| `match` | str | No | `"any"` |

### research_tag_tool
**Module:** `src/loom/tools/tool_tags.py` | **Type:** async

Add tags to a tool for organization.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `tags` | list[str] | Yes | — |

## tool_versioning

### research_tool_version
**Module:** `src/loom/tools/tool_versioning.py` | **Type:** async

Get version info for a tool or all tools.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | No | `""` |

### research_version_diff
**Module:** `src/loom/tools/tool_versioning.py` | **Type:** async

Compare current version with a previous hash.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `previous_hash` | str | No | `""` |

### research_version_snapshot
**Module:** `src/loom/tools/tool_versioning.py` | **Type:** async

Take a snapshot of all tool versions for deployment tracking.

*No parameters*

## topology_manifold

### research_topology_discover
**Module:** `src/loom/tools/topology_manifold.py` | **Type:** async

Map strategy space topologically to discover gaps in attack vectors.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategies` | list[str] | None | No | None |
| `dimensions` | int | No | `5` |
| `threshold` | float | No | `0.5` |

## tor

### research_tor_new_identity
**Module:** `src/loom/tools/tor.py` | **Type:** async

Request a new Tor circuit (exit node rotation).

*No parameters*

### research_tor_status
**Module:** `src/loom/tools/tor.py` | **Type:** async

Check Tor daemon status and get current exit node IP.

*No parameters*

## toxicity_checker_tool

### research_toxicity_check
**Module:** `src/loom/tools/toxicity_checker_tool.py` | **Type:** async

Check text for toxicity across 8 categories with severity scoring.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |
| `compare_prompt` | str | None | No | None |
| `compare_response` | str | None | No | None |

## traffic_capture

### research_capture_har
**Module:** `src/loom/tools/traffic_capture.py` | **Type:** async

Capture HTTP traffic as HAR format.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `duration_seconds` | int | No | `10` |
| `include_bodies` | bool | No | `True` |

### research_extract_cookies
**Module:** `src/loom/tools/traffic_capture.py` | **Type:** async

Extract cookies set by a URL with security assessment.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `follow_redirects` | bool | No | `True` |

## transcribe

### research_transcribe
**Module:** `src/loom/tools/transcribe.py` | **Type:** async

Transcribe audio/video from YouTube or direct URL using OpenAI Whisper.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `language` | str | None | No | None |
| `model_size` | str | No | `"base"` |

## transferability

### research_transfer_test
**Module:** `src/loom/tools/transferability.py` | **Type:** async

Test strategy transferability across multiple LLM providers.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | str | Yes | — |
| `strategy` | str | No | `"ethical_anchor"` |
| `models` | list[str] | None | No | None |

## trend_forecaster

### research_trend_forecast
**Module:** `src/loom/tools/trend_forecaster.py` | **Type:** async

Predict research directions by analyzing term frequency evolution.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `timeframe` | str | No | `"6months"` |
| `min_term_frequency` | int | No | `2` |

## trend_predictor

### research_trend_predict
**Module:** `src/loom/tools/trend_predictor.py` | **Type:** async

Predict research trends by analyzing publication patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `time_range_days` | int | No | `90` |

## uncertainty_harvest

### research_active_select
**Module:** `src/loom/tools/uncertainty_harvest.py` | **Type:** async

Select strategies to test with limited API budget. Objectives: maximize_success (highest P), maximize_information (highest entropy), balanced (Pareto).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `candidate_strategies` | list[str] | Yes | — |
| `budget` | int | No | `3` |
| `objective` | str | No | `"maximize_success"` |

### research_uncertainty_estimate
**Module:** `src/loom/tools/uncertainty_harvest.py` | **Type:** async

Estimate strategy success using Bayesian reasoning WITHOUT API calls. Uses priors and model likelihoods to rank strategies by success probability and entropy.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `strategies` | list[str] | Yes | — |
| `target_model` | str | No | `"auto"` |
| `prior_results` | dict[str, float] | None | No | None |

## unique_tools

### research_dark_web_bridge
**Module:** `src/loom/tools/unique_tools.py` | **Type:** async

Find clearnet references to dark web content.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |

### research_influence_operation
**Module:** `src/loom/tools/unique_tools.py` | **Type:** async

Detect potential influence operations via coordinated posting patterns.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |

### research_info_half_life
**Module:** `src/loom/tools/unique_tools.py` | **Type:** async

Estimate URL survival rate and information decay half-life.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |

### research_information_cascade
**Module:** `src/loom/tools/unique_tools.py` | **Type:** async

Map information flow across platforms (HN, Reddit, arXiv, Wikipedia).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `topic` | str | Yes | — |
| `hours_back` | int | No | `72` |

### research_propaganda_detector
**Module:** `src/loom/tools/unique_tools.py` | **Type:** sync

Detect propaganda techniques in text using NLP analysis.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `text` | str | Yes | — |

### research_search_discrepancy
**Module:** `src/loom/tools/unique_tools.py` | **Type:** async

Compare search results across multiple engines to find discrepancies.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |

### research_source_credibility
**Module:** `src/loom/tools/unique_tools.py` | **Type:** async

Rate source credibility using multiple factors.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

### research_web_time_machine
**Module:** `src/loom/tools/unique_tools.py` | **Type:** async

Track website evolution via Wayback Machine CDX snapshots.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `snapshots` | int | No | `10` |

## universal_orchestrator

### research_orchestrate_smart
**Module:** `src/loom/tools/universal_orchestrator.py` | **Type:** async

Auto-discover, score, and execute optimal tools for ANY query.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_tools` | int | No | `3` |
| `strategy` | str | No | `"auto"` |

## unstructured_backend

### research_document_extract
**Module:** `src/loom/tools/unstructured_backend.py` | **Type:** async

Extract structured content from any document type.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `file_path` | str | No | `""` |
| `url` | str | No | `""` |
| `strategy` | str | No | `"auto"` |

## urlhaus_lookup

### research_urlhaus_check
**Module:** `src/loom/tools/urlhaus_lookup.py` | **Type:** async

Check if URL is listed in URLhaus malware database (free).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

### research_urlhaus_search
**Module:** `src/loom/tools/urlhaus_lookup.py` | **Type:** async

Search URLhaus by tag, signature, or payload hash (free).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `search_type` | Literal['tag', 'signature', 'hash'] | No | `"tag"` |

## usage_analytics

### research_tool_usage_report
**Module:** `src/loom/tools/usage_analytics.py` | **Type:** async

Generate usage report for a specified period.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `period` | str | No | `"today"` |

### research_usage_record
**Module:** `src/loom/tools/usage_analytics.py` | **Type:** async

Record a tool usage event.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | Yes | — |
| `caller` | str | No | `"mcp"` |

### research_usage_trends
**Module:** `src/loom/tools/usage_analytics.py` | **Type:** async

Show usage trends over a time window.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `tool_name` | str | No | `""` |
| `window_hours` | int | No | `24` |

## usage_report

### research_usage_report
**Module:** `src/loom/tools/usage_report.py` | **Type:** async

Aggregate tool usage statistics across all invocations.

*No parameters*

## usb_monitor_tool

### research_usb_monitor
**Module:** `src/loom/tools/usb_monitor_tool.py` | **Type:** async

Monitor USB device activity.

*No parameters*

## vastai

### research_vastai_search
**Module:** `src/loom/tools/vastai.py` | **Type:** async

Search for available GPU instances on Vast.ai.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `gpu_type` | str | No | `"RTX 4090"` |
| `max_price` | float | No | `1.0` |
| `n` | int | No | `5` |

### research_vastai_status
**Module:** `src/loom/tools/vastai.py` | **Type:** async

Get Vast.ai account status (balance and running instances).

*No parameters*

## vercel

### research_vercel_status
**Module:** `src/loom/tools/vercel.py` | **Type:** async

Get real Vercel platform status from official status page.

*No parameters*

## vision_agent

### research_vision_browse
**Module:** `src/loom/tools/vision_agent.py` | **Type:** async

Screenshot a URL and analyze with LLM.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `task` | str | Yes | — |

### research_vision_compare
**Module:** `src/loom/tools/vision_agent.py` | **Type:** async

Compare visual layouts of two URLs.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url1` | str | Yes | — |
| `url2` | str | Yes | — |

## vuln_intel

### research_vuln_intel
**Module:** `src/loom/tools/vuln_intel.py` | **Type:** async

Aggregate vulnerability intelligence from 6+ free sources.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `query` | str | Yes | — |
| `max_results` | int | No | `30` |

## webcheck_backend

### research_web_check
**Module:** `src/loom/tools/webcheck_backend.py` | **Type:** sync

Comprehensive website OSINT analysis.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | str | Yes | — |
| `checks` | list[str] | None | No | None |

## webhook_system

### research_webhook_system_fire
**Module:** `src/loom/tools/webhook_system.py` | **Type:** async

Fire webhook event to all registered listeners.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `event` | str | Yes | — |
| `payload` | dict[str, Any] | Yes | — |

### research_webhook_system_list
**Module:** `src/loom/tools/webhook_system.py` | **Type:** async

List all registered webhooks.

*No parameters*

### research_webhook_system_register
**Module:** `src/loom/tools/webhook_system.py` | **Type:** async

Register webhook URL for task notifications.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `events` | list[str] | None | No | None |
| `secret` | str | No | `""` |

## webhooks

### research_webhook_list
**Module:** `src/loom/tools/webhooks.py` | **Type:** async

List all registered webhooks (without revealing secrets).

*No parameters*

### research_webhook_register
**Module:** `src/loom/tools/webhooks.py` | **Type:** async

Register a new webhook for Loom tool events.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `events` | list[str] | str | Yes | — |
| `secret` | str | None | No | None |

### research_webhook_test
**Module:** `src/loom/tools/webhooks.py` | **Type:** async

Send a test notification to a webhook.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `webhook_id` | str | Yes | — |

### research_webhook_unregister
**Module:** `src/loom/tools/webhooks.py` | **Type:** async

Unregister a webhook.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `webhook_id` | str | Yes | — |

## white_rabbit

### research_white_rabbit
**Module:** `src/loom/tools/white_rabbit.py` | **Type:** async

Follow anomalies discovering non-obvious connections.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `starting_point` | str | Yes | — |
| `depth` | int | No | `5` |
| `branch_factor` | int | No | `3` |
| `curiosity_threshold` | float | No | `0.7` |

## workflow_engine

### research_workflow_create
**Module:** `src/loom/tools/workflow_engine.py` | **Type:** sync

Create workflow definition stored in SQLite.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |
| `steps` | list[dict] | Yes | — |

### research_workflow_run
**Module:** `src/loom/tools/workflow_engine.py` | **Type:** sync

Execute workflow steps in dependency order.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `workflow_id` | str | Yes | — |
| `dry_run` | bool | No | `False` |

### research_workflow_status
**Module:** `src/loom/tools/workflow_engine.py` | **Type:** sync

Get current status of workflow.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `workflow_id` | str | Yes | — |

## workflow_expander

### research_workflow_coverage
**Module:** `src/loom/tools/workflow_expander.py` | **Type:** async

Report workflow coverage across all tools and categories.

*No parameters*

### research_workflow_generate
**Module:** `src/loom/tools/workflow_expander.py` | **Type:** async

Auto-generate workflows for given tool category.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `category` | str | No | `"auto"` |
| `max_steps` | int | No | `6` |

## workflow_templates

### research_workflow_get
**Module:** `src/loom/tools/workflow_templates.py` | **Type:** sync

Get detailed workflow template definition.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `name` | str | Yes | — |

### research_workflow_list
**Module:** `src/loom/tools/workflow_templates.py` | **Type:** sync

List all pre-built workflow templates.

*No parameters*

## xover_attack

### research_xover_matrix
**Module:** `src/loom/tools/xover_attack.py` | **Type:** async

Generate cross-model transfer probability matrix showing vulnerability transfer between families.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `attacks` | list[str] | None | No | None |

### research_xover_transfer
**Module:** `src/loom/tools/xover_attack.py` | **Type:** async

Adapt attack from source to target models using transfer matrix & adaptation rules.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `attack` | str | Yes | — |
| `source_model` | str | Yes | — |
| `target_models` | list[str] | None | No | None |

## yara_backend

### research_yara_scan
**Module:** `src/loom/tools/yara_backend.py` | **Type:** async

Scan files for malware patterns using compiled YARA rules.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `rules_path` | str | Yes | — |
| `target_path` | str | Yes | — |
| `timeout` | int | No | `60` |

## ytdlp_backend

### research_audio_extract
**Module:** `src/loom/tools/ytdlp_backend.py` | **Type:** async

Extract audio from video URL.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `format` | str | No | `"mp3"` |

### research_video_download
**Module:** `src/loom/tools/ytdlp_backend.py` | **Type:** async

Download video or audio from YouTube, TikTok, Twitter, Instagram, etc.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `format` | str | No | `"best"` |
| `audio_only` | bool | No | `False` |
| `max_duration` | int | No | `600` |

### research_video_info
**Module:** `src/loom/tools/ytdlp_backend.py` | **Type:** async

Extract metadata from video URL without downloading.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |

## zendriver_backend

### research_zen_batch
**Module:** `src/loom/tools/zendriver_backend.py` | **Type:** sync

Batch fetch multiple URLs concurrently with undetected browser.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `urls` | list[str] | Yes | — |
| `max_concurrent` | int | No | `5` |
| `timeout` | int | No | `30` |

### research_zen_fetch
**Module:** `src/loom/tools/zendriver_backend.py` | **Type:** sync

Fetch a single URL using undetected async browser (zendriver).

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `timeout` | int | No | `30` |
| `headless` | bool | No | `True` |

### research_zen_interact
**Module:** `src/loom/tools/zendriver_backend.py` | **Type:** sync

Interact with a web page: click, fill, scroll, wait for elements.

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `url` | str | Yes | — |
| `actions` | list[dict[str, str]] | Yes | — |
| `timeout` | int | No | `30` |
