Running 195 queries against http://127.0.0.1:8788/api/v1/tools
Timeout: 120s per query
======================================================================
  [  1/195] PASS    research_hcs_score                         0.0s OK
  [  2/195] PASS    research_hcs_score                         0.0s OK
  [  3/195] PASS    research_hcs_score                         0.0s OK
  [  4/195] PASS    research_hcs_score_full                    0.0s OK
  [  5/195] PASS    research_attack_score                      0.0s OK
  [  6/195] PASS    research_stealth_score                     0.0s OK
  [  7/195] PASS    research_potency_score                     0.0s OK
  [  8/195] PASS    research_expert_assessment                 0.1s OK
  [  9/195] PASS    research_model_vulnerability_profile       0.0s OK
  [ 10/195] PASS    research_fingerprint_model                 0.0s OK
  [ 11/195] PASS    research_hcs_compare                       0.0s OK
  [ 12/195] PASS    research_strategy_stats                    0.0s OK
  [ 13/195] PASS    research_strategy_recommend                0.0s OK
  [ 14/195] PASS    research_export_strategies                 0.0s OK
  [ 15/195] PASS    research_cached_strategy                   0.0s OK
  [ 16/195] PASS    research_salary_intelligence               8.7s OK
  [ 17/195] FAIL    research_career_trajectory                 0.0s has error: research_career_trajectory() missing 1 
  [ 18/195] PASS    research_company_diligence                 3.1s OK
  [ 19/195] PASS    research_uae_price_compare                14.7s OK
  [ 20/195] PASS    research_uae_wholesale_markets             0.0s OK
  ... 20/195 done (19 pass, 1 fail)
  [ 21/195] FAIL    research_uae_margin_calculator             0.0s has error: research_uae_margin_calculator() missin
  [ 22/195] PASS    research_uae_sourcing_plan                 0.0s OK
  [ 23/195] PASS    research_uae_seasonal_calendar             0.0s OK
  [ 24/195] PASS    research_uae_legal_check                   1.0s OK
  [ 25/195] PASS    research_uae_bundle_optimizer              0.0s OK
  [ 26/195] PASS    research_privacy_score                     0.3s OK
  [ 27/195] FAIL    research_fingerprint_audit                 0.0s has error: Unexpected error: Error: It looks like 
  [ 28/195] FAIL    research_browser_privacy_score             0.0s has error: Unknown browser: chrome
  [ 29/195] FAIL    research_artifact_cleanup                  0.0s has error: research_artifact_cleanup() missing 1 r
  [ 30/195] FAIL    research_supercookie_check                 0.0s has error: research_supercookie_check() missing 1 
  [ 31/195] PASS    research_fetch                             0.2s OK
  [ 32/195] PASS    research_fetch                             0.2s OK
  [ 33/195] PASS    research_fetch                             0.6s OK
  [ 34/195] PASS    research_search                            1.1s OK
  [ 35/195] PASS    research_search                            2.3s OK
  [ 36/195] FAIL    research_markdown                          3.3s too short: 0 < 20
  [ 37/195] FAIL    research_markdown                          0.1s too short: 0 < 20
  [ 38/195] FAIL    research_github                            0.0s has error: research_github() missing 2 required po
  [ 39/195] FAIL    research_github                            0.0s has error: research_github() missing 1 required po
  [ 40/195] FAIL    research_github                            0.0s has error: research_github() missing 2 required po
  ... 40/195 done (29 pass, 11 fail)
  [ 41/195] FAIL    research_github_readme                     0.0s has error: research_github_readme() missing 1 requ
  [ 42/195] FAIL    research_github_releases                   0.0s has error: research_github_releases() missing 1 re
  [ 43/195] FAIL    research_deep                             64.1s too short: 0 < 200
  [ 44/195] FAIL    research_deep                             78.8s too short: 0 < 500
  [ 45/195] FAIL    research_multi_search                      0.0s has error: research_multi_search() missing 1 requi
  [ 46/195] FAIL    research_wayback                          21.4s has error: no snapshots found
  [ 47/195] FAIL    research_cache_stats                       0.0s too short: 0 < 10
  [ 48/195] PASS    research_cache_clear                       0.0s OK
  [ 49/195] FAIL    research_spider                            0.1s has error: ValidationError; too short: 0 < 50
  [ 50/195] FAIL    research_help                              0.1s too short: 0 < 50
  [ 51/195] FAIL    research_fetch                             0.0s has error: scheme '' not allowed (http/https only)
  [ 52/195] FAIL    research_search                            0.3s has error: search failed
  [ 53/195] FAIL    research_llm_chat                         10.7s has error: all providers failed (attempted groq, n
  [ 54/195] PASS    research_hcs_score                         0.8s OK
  [ 55/195] FAIL    research_detect_language                   0.0s has error: text too short
  [ 56/195] PASS    research_search                            3.7s OK
  [ 57/195] FAIL    research_fetch                             0.0s has error: scheme 'not-a-valid-url' not allowed (h
  [ 58/195] FAIL    research_llm_chat                          0.0s has error: unknown provider: nonexistent_provider_
  [ 59/195] FAIL    research_config_get                        0.0s has error: unknown key: this_key_does_not_exist_12
  [ 60/195] PASS    research_whois                             0.3s OK
  ... 60/195 done (33 pass, 27 fail)
  [ 61/195] PASS    research_config_get                        0.0s OK
  [ 62/195] PASS    research_config_get                        0.0s OK
  [ 63/195] PASS    research_health_deep                       0.3s OK
  [ 64/195] PASS    research_cache_stats                       0.0s OK
  [ 65/195] PASS    research_validate_startup                  0.0s OK
  [ 66/195] PASS    research_memory_status                     0.0s OK
  [ 67/195] PASS    research_job_list                          0.0s OK
  [ 68/195] PASS    research_queue_stats                       0.0s OK
  [ 69/195] PASS    research_error_stats                       0.0s OK
  [ 70/195] PASS    research_session_list                      0.0s OK
  [ 71/195] PASS    research_breaker_status                    0.0s OK
  [ 72/195] PASS    research_quota_status                      0.0s OK
  [ 73/195] PASS    research_cost_summary                      0.0s OK
  [ 74/195] PASS    research_rate_limits                       0.0s OK
  [ 75/195] PASS    research_key_status                        0.0s OK
  [ 76/195] PASS    research_provider_ping                     0.0s OK
  [ 77/195] PASS    research_telemetry_stats                   0.0s OK
  [ 78/195] PASS    research_audit_stats                       0.0s OK
  [ 79/195] PASS    research_retry_stats                       0.0s OK
  [ 80/195] PASS    research_dlq_stats                         0.0s OK
  ... 80/195 done (53 pass, 27 fail)
  [ 81/195] PASS    research_whois                             5.3s OK
  [ 82/195] PASS    research_whois                             3.0s OK
  [ 83/195] PASS    research_dns_lookup                        0.2s OK
  [ 84/195] PASS    research_dns_lookup                        0.2s OK
  [ 85/195] PASS    research_dns_lookup                        0.2s OK
  [ 86/195] PASS    research_cert_analyze                      0.1s OK
  [ 87/195] PASS    research_community_sentiment               0.0s OK
  [ 88/195] FAIL    research_threat_profile                    0.0s has error: research_threat_profile() missing 1 req
  [ 89/195] PASS    research_crypto_risk_score                 1.2s OK
  [ 90/195] PASS    research_transaction_graph                 2.5s OK
  [ 91/195] PASS    research_ip_reputation                     0.3s OK
  [ 92/195] PASS    research_ip_reputation                     0.3s OK
  [ 93/195] PASS    research_domain_reputation                10.2s OK
  [ 94/195] PASS    research_domain_reputation                31.1s OK
  [ 95/195] FAIL    research_social_profile                    0.0s has error: research_social_profile() missing 1 req
  [ 96/195] PASS    research_llm_chat                          2.7s OK
  [ 97/195] PASS    research_llm_chat                          0.3s OK
  [ 98/195] FAIL    research_llm_summarize                     3.0s too short: 0 < 10
  [ 99/195] FAIL    research_llm_summarize                     3.0s too short: 0 < 15
  [100/195] FAIL    research_llm_translate                     2.5s too short: 0 < 5
  ... 100/195 done (68 pass, 32 fail)
  [101/195] FAIL    research_llm_translate                     0.1s too short: 0 < 5
  [102/195] FAIL    research_llm_classify                      2.4s too short: 0 < 5
  [103/195] FAIL    research_llm_embed                         4.8s has error: Client error '404 Not Found' for url 'h
  [104/195] FAIL    research_llm_extract                       3.0s too short: 0 < 20
  [105/195] FAIL    research_ask_all_llms                      4.9s too short: 0 < 10
  [106/195] FAIL    research_llm_query_expand                  2.8s too short: 0 < 30
  [107/195] FAIL    research_prompt_reframe                    0.0s too short: 0 < 10
  [108/195] FAIL    research_prompt_reframe                    0.0s too short: 0 < 10
  [109/195] FAIL    research_refusal_detector                  0.0s too short: 0 < 1
  [110/195] FAIL    research_refusal_detector                  0.0s too short: 0 < 1
  [111/195] PASS    research_smart_call                        4.2s OK
  [112/195] PASS    research_smart_call                        1.2s OK
  [113/195] PASS    research_smart_call                        6.1s OK
  [114/195] TIMEOUT research_smart_call                      >120s
  [115/195] FAIL    research_adversarial_orchestrate           0.0s has error: research_adversarial_orchestrate() miss
  [116/195] FAIL    research_adversarial_orchestrate           0.0s has error: research_adversarial_orchestrate() miss
  [117/195] TIMEOUT research_augmented_generate              >120s
  [118/195] FAIL    research_agent_loop                        0.0s has error: research_agent_loop() missing 1 require
  [119/195] FAIL    research_reframe_until_hcs                 0.0s has error: research_reframe_until_hcs() missing 1 
  [120/195] FAIL    research_max_score                         0.0s has error: research_max_score() missing 1 required
  ... 120/195 done (71 pass, 47 fail)
  [121/195] FAIL    research_expert_assessment                 0.0s has error: research_expert_assessment() missing 2 
  [122/195] FAIL    research_expert_assessment                 0.0s has error: research_expert_assessment() missing 2 
  [123/195] FAIL    research_recommend_tools                   0.0s has error: research_recommend_tools() missing 1 re
  [124/195] PASS    research_discover                          0.0s OK
  [125/195] FAIL    research_tool_search                       0.0s has error: research_tool_search() missing 1 requir
  [126/195] PASS    research_fact_check                        2.0s OK
  [127/195] PASS    research_fact_check                        1.1s OK
  [128/195] PASS    research_knowledge_extract                 0.9s OK
  [129/195] PASS    research_epistemic_score                   0.0s OK
  [130/195] PASS    research_predatory_journal_check           1.5s OK
  [131/195] PASS    research_text_analyze                      0.0s OK
  [132/195] PASS    research_text_analyze                      0.0s OK
  [133/195] PASS    research_text_analyze                      0.0s OK
  [134/195] PASS    research_simplify                          3.8s OK
  [135/195] PASS    research_tag_cloud                         0.0s OK
  [136/195] PASS    research_detect_language                   0.0s OK
  [137/195] PASS    research_detect_language                   0.0s OK
  [138/195] PASS    research_rss_fetch                         1.6s OK
  [139/195] PASS    research_source_credibility                3.0s OK
  [140/195] FAIL    research_build_query                       0.0s has error: research_build_query() missing 1 requir
  ... 140/195 done (86 pass, 52 fail)
  [141/195] PASS    research_cve_lookup                        1.7s OK
  [142/195] PASS    research_cve_lookup                        0.6s OK
  [143/195] PASS    research_cve_detail                        0.9s OK
  [144/195] PASS    research_domain_reputation                 8.9s OK
  [145/195] PASS    research_domain_reputation                 8.4s OK
  [146/195] PASS    research_ip_reputation                     0.3s OK
  [147/195] PASS    research_urlhaus_check                     0.3s OK
  [148/195] PASS    research_urlhaus_search                    0.2s OK
  [149/195] PASS    research_cert_analyze                      0.1s OK
  [150/195] PASS    research_security_headers                  0.2s OK
  [151/195] PASS    research_security_headers                  0.5s OK
  [152/195] PASS    research_password_check                    0.2s OK
  [153/195] PASS    research_password_check                    0.1s OK
  [154/195] PASS    research_pii_scan                          0.0s OK
  [155/195] PASS    research_pii_scan                          0.0s OK
  [156/195] FAIL    research_strip_hedging                    60.0s has error: Tool timed out after 60s
  [157/195] FAIL    research_innocent_decompose                0.0s has error: research_innocent_decompose() missing 1
  [158/195] FAIL    research_conversational_drift              0.0s has error: research_conversational_drift() missing
  [159/195] FAIL    research_meta_prompt                       0.0s has error: research_meta_prompt() missing 1 requir
  [160/195] FAIL    research_genetic_evolve                    0.0s has error: research_genetic_evolve() missing 1 req
  ... 160/195 done (101 pass, 57 fail)
  [161/195] FAIL    research_code_wrap                         0.0s has error: research_code_wrap() missing 1 required
  [162/195] FAIL    research_json_force                        0.0s has error: research_json_force() missing 1 require
  [163/195] FAIL    research_code_complete                     0.0s has error: research_code_complete() missing 1 requ
  [164/195] FAIL    research_yaml_inject                       0.0s has error: research_yaml_inject() missing 1 requir
  [165/195] FAIL    research_reasoning_hijack                  0.0s has error: research_reasoning_hijack() missing 1 r
  [166/195] FAIL    research_context_poison                    0.0s has error: research_context_poison() missing 1 req
  [167/195] FAIL    research_compliance_momentum               0.0s has error: research_compliance_momentum() missing 
  [168/195] FAIL    research_continuation_attack               0.0s has error: research_continuation_attack() missing 
  [169/195] FAIL    research_cross_session                     0.0s has error: research_cross_session() missing 1 requ
  [170/195] FAIL    research_multi_merge                       0.0s has error: research_multi_merge() missing 1 requir
  [171/195] PASS    research_amplify_response                120.1s OK
  [172/195] FAIL    research_synonym_sub                       0.0s has error: research_synonym_sub() missing 1 requir
  [173/195] FAIL    research_language_mix                      0.0s has error: research_language_mix() missing 1 requi
  [174/195] FAIL    research_adversarial_consensus             0.0s has error: research_adversarial_consensus() missin
  [175/195] FAIL    research_translation_bypass                0.0s has error: research_translation_bypass() missing 1
  [176/195] FAIL    research_test_generation                   0.0s has error: research_test_generation() missing 1 re
  [177/195] FAIL    research_definition_chain                  0.0s has error: research_definition_chain() missing 1 r
  [178/195] FAIL    research_table_trick                       0.0s has error: research_table_trick() missing 1 requir
  [179/195] FAIL    research_academic_format                   0.0s has error: research_academic_format() missing 1 re
  [180/195] FAIL    research_reverse_request                   0.0s has error: research_reverse_request() missing 1 re
  ... 180/195 done (102 pass, 76 fail)
  [181/195] FAIL    research_latency_probe                     0.0s has error: research_latency_probe() missing 1 requ
  [182/195] FAIL    research_embed_navigate                    0.0s has error: research_embed_navigate() missing 1 req
  [183/195] FAIL    research_roleplay_escalate                 0.0s has error: research_roleplay_escalate() missing 1 
  [184/195] FAIL    research_request_smuggle                   0.0s has error: research_request_smuggle() missing 1 re
  [185/195] FAIL    research_output_chunk                      0.0s has error: research_output_chunk() missing 1 requi
  [186/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [187/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [188/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [189/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [190/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [191/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [192/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [193/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [194/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found
  [195/195] FAIL    workflow                                   0.0s has error: Tool 'workflow' not found

======================================================================
FINAL RESULTS: 102/195 PASS (52%)
  Passed:  102
  Failed:  91
  Timeout: 2
  Error:   0
======================================================================

FAILURES:
  [17] research_career_trajectory: has error: research_career_trajectory() missing 1 required positional a
  [21] research_uae_margin_calculator: has error: research_uae_margin_calculator() missing 3 required position
  [27] research_fingerprint_audit: has error: Unexpected error: Error: It looks like you are using Playwri
  [28] research_browser_privacy_score: has error: Unknown browser: chrome
  [29] research_artifact_cleanup: has error: research_artifact_cleanup() missing 1 required positional ar
  [30] research_supercookie_check: has error: research_supercookie_check() missing 1 required positional a
  [36] research_markdown: too short: 0 < 20
  [37] research_markdown: too short: 0 < 20
  [38] research_github: has error: research_github() missing 2 required positional arguments: '; too short: 0 < 200
  [39] research_github: has error: research_github() missing 1 required positional argument: 'k; too short: 0 < 50
  [40] research_github: has error: research_github() missing 2 required positional arguments: '; too short: 0 < 100
  [41] research_github_readme: has error: research_github_readme() missing 1 required positional argum; too short: 0 < 500
  [42] research_github_releases: has error: research_github_releases() missing 1 required positional arg; too short: 0 < 100
  [43] research_deep: too short: 0 < 200
  [44] research_deep: too short: 0 < 500
  [45] research_multi_search: has error: research_multi_search() missing 1 required positional argume; too short: 0 < 100
  [46] research_wayback: has error: no snapshots found
  [47] research_cache_stats: too short: 0 < 10
  [49] research_spider: has error: ValidationError; too short: 0 < 50
  [50] research_help: too short: 0 < 50
  [51] research_fetch: has error: scheme '' not allowed (http/https only)
  [52] research_search: has error: search failed
  [53] research_llm_chat: has error: all providers failed (attempted groq, nvidia, deepseek, gemi
  [55] research_detect_language: has error: text too short
  [57] research_fetch: has error: scheme 'not-a-valid-url' not allowed (http/https only)
  [58] research_llm_chat: has error: unknown provider: nonexistent_provider_xyz
  [59] research_config_get: has error: unknown key: this_key_does_not_exist_12345
  [88] research_threat_profile: has error: research_threat_profile() missing 1 required positional argu
  [95] research_social_profile: has error: research_social_profile() missing 1 required positional argu
  [98] research_llm_summarize: too short: 0 < 10
  [99] research_llm_summarize: too short: 0 < 15
  [100] research_llm_translate: too short: 0 < 5
  [101] research_llm_translate: too short: 0 < 5
  [102] research_llm_classify: too short: 0 < 5
  [103] research_llm_embed: has error: Client error '404 Not Found' for url 'http://localhost:11434; too short: 0 < 100
  [104] research_llm_extract: too short: 0 < 20
  [105] research_ask_all_llms: too short: 0 < 10
  [106] research_llm_query_expand: too short: 0 < 30
  [107] research_prompt_reframe: too short: 0 < 10
  [108] research_prompt_reframe: too short: 0 < 10
  [109] research_refusal_detector: too short: 0 < 1
  [110] research_refusal_detector: too short: 0 < 1
  [115] research_adversarial_orchestrate: has error: research_adversarial_orchestrate() missing 1 required positi
  [116] research_adversarial_orchestrate: has error: research_adversarial_orchestrate() missing 1 required positi
  [118] research_agent_loop: has error: research_agent_loop() missing 1 required positional argument
  [119] research_reframe_until_hcs: has error: research_reframe_until_hcs() missing 1 required positional a
  [120] research_max_score: has error: research_max_score() missing 1 required positional argument:
  [121] research_expert_assessment: has error: research_expert_assessment() missing 2 required positional a
  [122] research_expert_assessment: has error: research_expert_assessment() missing 2 required positional a
  [123] research_recommend_tools: has error: research_recommend_tools() missing 1 required positional arg
  [125] research_tool_search: has error: research_tool_search() missing 1 required positional argumen
  [140] research_build_query: has error: research_build_query() missing 1 required positional argumen
  [156] research_strip_hedging: has error: Tool timed out after 60s
  [157] research_innocent_decompose: has error: research_innocent_decompose() missing 1 required positional 
  [158] research_conversational_drift: has error: research_conversational_drift() missing 1 required positiona
  [159] research_meta_prompt: has error: research_meta_prompt() missing 1 required positional argumen
  [160] research_genetic_evolve: has error: research_genetic_evolve() missing 1 required positional argu
  [161] research_code_wrap: has error: research_code_wrap() missing 1 required positional argument:
  [162] research_json_force: has error: research_json_force() missing 1 required positional argument
  [163] research_code_complete: has error: research_code_complete() missing 1 required positional argum
  [164] research_yaml_inject: has error: research_yaml_inject() missing 1 required positional argumen
  [165] research_reasoning_hijack: has error: research_reasoning_hijack() missing 1 required positional ar
  [166] research_context_poison: has error: research_context_poison() missing 1 required positional argu
  [167] research_compliance_momentum: has error: research_compliance_momentum() missing 1 required positional
  [168] research_continuation_attack: has error: research_continuation_attack() missing 1 required positional
  [169] research_cross_session: has error: research_cross_session() missing 1 required positional argum
  [170] research_multi_merge: has error: research_multi_merge() missing 1 required positional argumen
  [172] research_synonym_sub: has error: research_synonym_sub() missing 1 required positional argumen
  [173] research_language_mix: has error: research_language_mix() missing 1 required positional argume
  [174] research_adversarial_consensus: has error: research_adversarial_consensus() missing 1 required position
  [175] research_translation_bypass: has error: research_translation_bypass() missing 1 required positional 
  [176] research_test_generation: has error: research_test_generation() missing 1 required positional arg
  [177] research_definition_chain: has error: research_definition_chain() missing 1 required positional ar
  [178] research_table_trick: has error: research_table_trick() missing 1 required positional argumen
  [179] research_academic_format: has error: research_academic_format() missing 1 required positional arg
  [180] research_reverse_request: has error: research_reverse_request() missing 1 required positional arg
  [181] research_latency_probe: has error: research_latency_probe() missing 1 required positional argum
  [182] research_embed_navigate: has error: research_embed_navigate() missing 1 required positional argu
  [183] research_roleplay_escalate: has error: research_roleplay_escalate() missing 1 required positional a
  [184] research_request_smuggle: has error: research_request_smuggle() missing 1 required positional arg
  [185] research_output_chunk: has error: research_output_chunk() missing 1 required positional argume
  [186] workflow: has error: Tool 'workflow' not found
  [187] workflow: has error: Tool 'workflow' not found
  [188] workflow: has error: Tool 'workflow' not found
  [189] workflow: has error: Tool 'workflow' not found
  [190] workflow: has error: Tool 'workflow' not found
  [191] workflow: has error: Tool 'workflow' not found
  [192] workflow: has error: Tool 'workflow' not found
  [193] workflow: has error: Tool 'workflow' not found
  [194] workflow: has error: Tool 'workflow' not found
  [195] workflow: has error: Tool 'workflow' not found

CATEGORY BREAKDOWN:
  adversarial               15/15 (100%)
  career_privacy            9/15 (60%)
  core                      6/20 (30%)
  edge_case                 3/10 (30%)
  infrastructure            20/20 (100%)
  intelligence              13/15 (87%)
  llm                       2/15 (13%)
  pipeline                  4/15 (27%)
  research                  14/15 (93%)
  security                  15/15 (100%)
  technique                 1/30 (3%)
  workflow                  0/10 (0%)

Results saved to /tmp/test_200_results.json
