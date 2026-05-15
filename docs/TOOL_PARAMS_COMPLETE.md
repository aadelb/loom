# Loom v3 Complete Tool Parameter Reference
### export_audit
Export audit logs for compliance reporting.
- async: False
- params:   - start_date (str | None, optional, default=None)
  - end_date (str | None, optional, default=None)
  - format (str, optional, default=json)
  - audit_dir (Path, optional, default=/home/aadel/.loom/audit)
  - secret (str | None, optional, default=None)

### research_ab_test_analyze
Analyze A/B test results with statistical significance and Cohen's d effect size.
- async: True
- params:   - results_a (list[float], required)
  - results_b (list[float], required)
  - metric (str, optional, default=compliance_rate)

### research_ab_test_design
Design A/B test with power and minimum detectable effect.
- async: True
- params:   - strategy_a (str, required)
  - strategy_b (str, required)
  - sample_size (int, optional, default=30)
  - metric (str, optional, default=compliance_rate)

### research_active_select
Select strategies to test with limited API budget. Objectives: maximize_success (highest P), maximiz
- async: True
- params:   - candidate_strategies (list[str], required)
  - budget (int, optional, default=3)
  - objective (str, optional, default=maximize_success)

### research_adapt_complexity
Adjust text complexity to target reading level (1-20 scale, 12 = college).
- async: True
- params:   - content (str, required)
  - target_reading_level (int, optional, default=12)

### research_adaptive_reframe
Adaptively reframe based on refusal analysis and model fingerprinting.
- async: True
- params:   - prompt (str, required)
  - refusal_text (str, optional)
  - model (str, optional, default=auto)

### research_adversarial_batch
Batch craft adversarial examples for multiple inputs.
- async: True
- params:   - inputs (list[str], required)
  - method (str, optional, default=greedy_swap)
  - budget (float, optional, default=0.1)

### research_adversarial_debate
Simulate multi-turn adversarial debate: attacker vs target model.
- async: True
- params:   - topic (str, required)
  - attacker_strategy (str, optional, default=auto)
  - max_turns (int, optional, default=5)
  - target_model (str, optional, default=nvidia)

### research_adversarial_robustness
Test model robustness against adversarial inputs.
- async: True
- params:   - target_url (str, required)
  - test_count (int, optional, default=5)

### research_agent_benchmark
Benchmark an AI agent against 20 agentic prompt injection scenarios.
- async: True
- params:   - model_api_url (str, required)
  - model_name (str, optional)
  - timeout (float, optional, default=30.0)
  - output_format (str, optional, default=summary)

### research_aggregate_results
Combine multiple tool results into unified output.
- async: True
- params:   - results (list[dict], required)
  - strategy (str, optional, default=merge)

### research_aggregate_texts
Aggregate multiple text outputs.
- async: True
- params:   - texts (list[str], required)
  - method (str, optional, default=concatenate)
  - max_length (int, optional, default=5000)

### research_ai_bias_audit
Compare responses across demographic groups for bias patterns.
- async: False
- params:   - prompts (list[str], required)
  - responses (list[str], required)

### research_ai_data_governance
Assess data handling practices against EU AI Act requirements.
- async: False
- params:   - system_description (str, required)

### research_ai_detect
Detect whether text is likely AI-generated.
- async: True
- params:   - text (str, required)
  - max_cost_usd (float, optional, default=0.02)

### research_ai_risk_classify
Classify AI system risk level per EU AI Act Annex III tiers.
- async: False
- params:   - system_description (str, required)

### research_ai_robustness_test
Test model consistency across rephrased and similar inputs.
- async: False
- params:   - model_name (str, required)
  - test_prompts (list[str], required)

### research_ai_transparency_check
Check if response discloses it's AI-generated and includes attribution.
- async: False
- params:   - model_response (str, required)
  - model_name (str, optional)

### research_alert_check
Evaluate all rules against current metric values.
- async: True
- params:   - metric_values (dict[str, float] | None, optional, default=None)

### research_alert_create
Create an alerting rule.
- async: True
- params:   - name (str, required)
  - metric (str, required)
  - condition (str, required)
  - threshold (float, required)
  - action (str, optional, default=log)

### research_alert_list
List all alert rules.
- async: True
- params:   (none)

### research_amass_enum
Attack surface mapping and asset discovery via OWASP Amass enum.
- async: False
- params:   - domain (str, required)
  - passive (bool, optional, default=True)
  - timeout (int, optional, default=120)

### research_amass_intel
OSINT intelligence gathering via OWASP Amass intel.
- async: False
- params:   - domain (str, required)

### research_analytics_dashboard
Generate comprehensive tool usage analytics dashboard.
- async: True
- params:   - include_unused (bool, optional, default=False)
  - all_tools (list[str] | None, optional, default=None)

### research_analyze_evidence
Analyze text evidence for patterns and insights.
- async: True
- params:   - text (str, required)

### research_api_changelog
Return changelog of features added/changed between versions.
- async: True
- params:   - since_version (str, optional, default=3.0.0)

### research_api_deprecations
List deprecated tools/features scheduled for removal.
- async: True
- params:   (none)

### research_api_version
Return current API version info with system metadata.
- async: True
- params:   (none)

### research_archive_page
Archive a complete webpage as a single HTML file using SingleFile.
- async: True
- params:   - url (str, required)
  - output_dir (str | None, optional, default=None)

### research_article_batch
Batch extract articles from multiple URLs with concurrency control.
- async: True
- params:   - urls (list[str], required)
  - max_concurrent (int, optional, default=5)

### research_article_extract
Extract article content, metadata, and NLP features from URL.
- async: True
- params:   - url (str, required)

### research_artifact_cleanup
Identify forensic artifacts without deletion (dry-run mode).
- async: False
- params:   - target_paths (list[str], required)
  - dry_run (bool, optional, default=True)

### research_arxiv_extract_techniques
Extract actionable attack techniques from a paper abstract.
- async: True
- params:   - paper_abstract (str, required)
  - paper_title (str, optional)

### research_arxiv_ingest
Search arXiv for recent papers on jailbreaking/red-teaming/prompt injection.
- async: True
- params:   - keywords (list[str] | None, optional, default=None)
  - days_back (int, optional, default=7)
  - max_papers (int, optional, default=20)

### research_arxiv_scan
Search arXiv for recent papers on jailbreak/adversarial/safety topics.
- async: True
- params:   - keywords (list[str] | None, optional, default=None)
  - days_back (int, optional, default=7)
  - max_papers (int, optional, default=20)

### research_ask_all_llms
Send a prompt to ALL available LLM providers and compare responses.
- async: True
- params:   - prompt (str, required)
  - max_tokens (int, optional, default=500)
  - include_reframe (bool, optional, default=False)

### research_ask_all_models
Send a prompt to ALL available AI models and compare responses.
- async: True
- params:   - prompt (str, required)
  - models (list[str] | None, optional, default=None)
  - max_tokens (int, optional, default=1000)
  - auto_reframe (bool, optional, default=True)
  - include_clis (bool, optional, default=False)
  - timeout (int, optional, default=60)

### research_attack_portfolio
Build diversified attack portfolio using portfolio theory.
- async: True
- params:   - target_model (str, optional, default=auto)
  - portfolio_size (int, optional, default=10)

### research_attack_score
Score attack effectiveness across 8 dimensions.
- async: False
- params:   - prompt (str, required)
  - response (str, required)
  - strategy (str, optional)
  - model (str, optional)
  - baseline_refusal (bool, optional, default=True)

### research_attractor_trap
Generate prompts that trap safety evaluators in chaotic oscillations.
- async: True
- params:   - prompt (str, required)
  - attractor_type (str, optional, default=lorenz)
  - iterations (int, optional, default=100)

### research_audio_extract
Extract audio from video URL.
- async: True
- params:   - url (str, required)
  - format (str, optional, default=mp3)

### research_audit_export
Export audit trail for compliance review.
- async: True
- params:   - format (str, optional, default=jsonl)
  - days (int, optional, default=7)

### research_audit_log_query
Query audit trail entries with filtering and time window.
- async: True
- params:   - tool (str, optional)
  - caller (str, optional)
  - since_hours (int, optional, default=24)
  - limit (int, optional, default=100)

### research_audit_query
Query audit log entries by tool name and time range.
- async: True
- params:   - tool_name (str, optional)
  - hours (int, optional, default=24)
  - limit (int, optional, default=100)

### research_audit_record
Record an audit trail entry for a tool call.
- async: True
- params:   - tool_name (str, required)
  - params (dict | None, optional, default=None)
  - result_summary (str, optional)
  - caller (str, optional, default=anonymous)
  - duration_ms (float, optional, default=0)

### research_audit_stats
Generate audit statistics for compliance reporting.
- async: True
- params:   - hours (int, optional, default=24)

### research_audit_trail
Retrieve audit trail entries, filtered by tool name.
- async: False
- params:   - tool_name (str, optional)
  - limit (int, optional, default=100)

### research_augment_dataset
Augment dataset samples with transformations.
- async: True
- params:   - samples (list[str], required)
  - augmentation (str, optional, default=all)

### research_auth_create_token
Create a bearer token for MCP access.
- async: True
- params:   - name (str, optional, default=default)
  - expires_hours (int, optional, default=24)

### research_auth_revoke
Revoke token(s) by name.
- async: True
- params:   - name (str, optional)

### research_auth_validate
Validate a token.
- async: True
- params:   - token (str, required)

### research_author_clustering
Detect emerging research clusters by analyzing co-authorship patterns.
- async: True
- params:   - field (str, required)
  - max_authors (int, optional, default=50)

### research_authority_stack
Stack multiple authority signals to overwhelm safety filters.
- async: True
- params:   - prompt (str, required)
  - authority_layers (int, optional, default=5)

### research_auto_params
Auto-infer tool parameters from natural language query.
- async: True
- params:   - tool_name (str, required)
  - query (str, required)

### research_auto_pipeline
Auto-generate optimal multi-tool pipeline from a natural language goal.
- async: True
- params:   - goal (str, required)
  - max_steps (int, optional, default=7)
  - optimize_for (str, optional, default=quality)

### research_auto_redteam
Automatically test strategies against a target model.
- async: True
- params:   - target_model (str, optional, default=nvidia)
  - strategies_to_test (int, optional, default=10)
  - topic (str, optional, default=general)

### research_auto_reframe
Auto-reframe a prompt through escalating strategies until accepted.
- async: True
- params:   - prompt (str, required)
  - target_url (str, optional)
  - model (str, optional, default=auto)
  - max_attempts (int, optional, default=5)

### research_auto_report
Generate a structured intelligence report on a given topic.
- async: True
- params:   - topic (str, required)
  - depth (Literal['brief', 'standard', 'comprehensive'], optional, default=standard)
  - format (Literal['markdown', 'json', 'html'], optional, default=markdown)
  - search_provider (str | None, optional, default=None)
  - num_sources (int | None, optional, default=None)
  - include_methodology (bool, optional, default=True)
  - include_recommendations (bool, optional, default=True)

### research_backoff_dlq_list
List items in the Dead Letter Queue.
- async: True
- params:   - status (str, optional, default=pending)

### research_backup_cleanup
Clean up backups older than specified days.
- async: True
- params:   - days (int, optional, default=30)

### research_backup_create
Create a backup of Loom's persistent data.
- async: True
- params:   - target (str, optional, default=all)

### research_backup_list
List available backups with metadata.
- async: True
- params:   (none)

### research_backup_restore
Restore from a backup.
- async: True
- params:   - backup_id (str, required)
  - target (str, optional, default=all)
  - dry_run (bool, optional, default=True)

### research_batch_list
List recent batch items with optional filtering.
- async: True
- params:   - limit (int, optional, default=20)
  - status_filter (Literal['all', 'pending', 'processing', 'done', 'failed'], optional, default=all)
  - offset (int, optional, default=0)

### research_batch_status
Get the status of a batch job.
- async: True
- params:   - batch_id (str, required)

### research_batch_submit
Submit a tool invocation to the batch queue.
- async: True
- params:   - tool_name (str, required)
  - params (dict[str, Any], required)
  - callback_url (str | None, optional, default=None)
  - max_retries (int, optional, default=3)

### research_batch_verify
Verify multiple claims in batch.
- async: True
- params:   - claims (list[str], required)

### research_behavioral_fingerprint
Build behavioral fingerprint from public activity patterns.
- async: True
- params:   - username (str, required)

### research_benchmark_compare
Compare two tools head-to-head. Returns {tool_a: {mean_ms, p95_ms}, tool_b: {mean_ms, p95_ms}, winne
- async: True
- params:   - tool_a (str, required)
  - tool_b (str, required)
  - iterations (int, optional, default=20)

### research_benchmark_models
Run standard benchmarks against LLM models.
- async: True
- params:   - models (list[str] | None, optional, default=None)
  - categories (list[str] | None, optional, default=None)

### research_benchmark_run
MCP tool: Run jailbreak benchmarks against a model.
- async: True
- params:   - dataset (str, optional, default=jailbreakbench)
  - strategies (str | None, optional, default=None)
  - model_name (str, optional, default=test-model)

### research_bias_lens
Detect methodological bias in academic papers.
- async: True
- params:   - paper_id (str, optional)
  - text (str, optional)

### research_bias_probe
Test an LLM API for demographic and social bias.
- async: False
- params:   - target_url (str, required)
  - categories (list[str] | None, optional, default=None)
  - probes_per_category (int, optional, default=2)

### research_blind_spy_chain
Research tool: Blind spy chain for query fragmentation testing.
- async: True
- params:   - query (str, required)
  - models (list[str], required)

### research_bot_detector
Detect coordinated bot/spam behavior on social platforms.
- async: True
- params:   - subreddit (str, optional)
  - hn_query (str, optional)

### research_botasaurus
Fetch a URL using Botasaurus stealth browser.
- async: True
- params:   - url (str, required)
  - session (str | None, optional, default=None)
  - screenshot (bool, optional, default=False)
  - timeout (int | None, optional, default=None)

### research_botnet_tracker
Track botnet C2 infrastructure via threat feeds.
- async: True
- params:   - ioc (str, required)
  - ioc_type (str, optional, default=ip)

### research_bpj_generate
Generate boundary points for safety classifier testing.
- async: True
- params:   - safe_prompt (str, required)
  - unsafe_prompt (str, required)
  - max_steps (int, optional, default=10)
  - model_name (str, optional, default=test-model)
  - mode (str, optional, default=find_boundary)
  - perturbations (int, optional, default=20)

### research_breach_check
Check if an email appears in known data breaches.
- async: True
- params:   - email (str, optional)
  - query (str, optional)

### research_breaker_reset
Manually reset circuit(s) to CLOSED.
- async: True
- params:   - provider (str, optional, default=all)

### research_breaker_status
Show circuit breaker state: {circuits: [{provider, state, failures, last_failure, cooldown_remaining
- async: True
- params:   (none)

### research_breaker_trip
Record failure for provider. Open circuit if failures >= threshold (5).
- async: True
- params:   - provider (str, required)
  - error (str, optional)

### research_brief_generate
Generate short intelligence brief (1 page).
- async: True
- params:   - topic (str, required)
  - points (list[str], required)
  - audience (str, optional, default=executive)

### research_browser_fingerprint
Analyze browser fingerprinting vectors on a webpage.
- async: False
- params:   - url (str, optional, default=https://example.com)
  - timeout (int, optional, default=30)

### research_browser_fingerprint_audit
Analyze a URL's fingerprinting scripts (detect canvas/WebGL/audio fingerprinting code).
- async: False
- params:   - url (str, optional, default=https://example.com)

### research_browser_privacy_score
Assess browser privacy configuration.
- async: False
- params:   - browser (str, optional, default=chromium)

### research_build_query
Transform a raw user request into optimized research queries.
- async: False
- params:   - user_request (str, required)
  - context (str, optional)
  - output_type (str, optional, default=research)
  - max_queries (int, optional, default=5)
  - optimize (bool, optional, default=True)
  - darkness_level (int, optional, default=1)
  - spectrum (bool, optional, default=False)

### research_cache_analyze
Analyze cache performance metrics.
- async: True
- params:   (none)

### research_cache_clear
Remove cache entries older than N days.
- async: False
- params:   - older_than_days (int | None, optional, default=None)

### research_cache_lookup
Look up cached response for similar query.
- async: True
- params:   - query (str, required)

### research_cache_optimize
Optimize cache usage and return statistics.
- async: True
- params:   (none)

### research_cache_stats
Return cache statistics.
- async: False
- params:   (none)

### research_cache_store
Store a query-response pair in memory cache.
- async: True
- params:   - query (str, required)
  - response (str, required)
  - tool_name (str, optional)
  - ttl_hours (int, optional, default=24)

### research_cached_strategy
Check cache for best strategy on this topic+model combination.
- async: False
- params:   - topic (str, required)
  - model (str, optional, default=auto)
  - fallback_strategy (str, optional, default=ethical_anchor)

### research_camoufox
Fetch a URL using Camoufox stealth browser.
- async: True
- params:   - url (str, required)
  - session (str | None, optional, default=None)
  - screenshot (bool, optional, default=False)
  - timeout (int | None, optional, default=None)

### research_capability_mapper
Map LLM capabilities across multiple domains.
- async: True
- params:   - target_url (str, required)
  - categories (list[str] | None, optional, default=None)

### research_capability_matrix
Analyze all tool functions by input/output type.
- async: True
- params:   - category (str, optional, default=all)

### research_capture_har
Capture HTTP traffic as HAR format.
- async: True
- params:   - url (str, required)
  - duration_seconds (int, optional, default=10)
  - include_bodies (bool, optional, default=True)

### research_career_trajectory
Build a career trajectory profile by combining multiple data sources.
- async: True
- params:   - person_name (str, required)
  - domain (str, optional)

### research_censorship_detector
Detect DNS censorship and takedown notices.
- async: True
- params:   - url (str, required)

### research_censys_host
Look up host on Censys — TLS certs, services, protocols.
- async: True
- params:   - ip (str, required)

### research_censys_search
Search Censys for hosts matching criteria.
- async: True
- params:   - query (str, required)
  - max_results (int, optional, default=10)

### research_cert_analyze
Extract SSL/TLS certificate information from a remote server.
- async: True
- params:   - hostname (str, optional)
  - domain (str, optional)
  - port (int, optional, default=443)

### research_chain_define
Define a reusable tool chain (pipeline).
- async: True
- params:   - name (str, required)
  - steps (list[dict], required)

### research_chain_describe
Show details of a specific chain.
- async: True
- params:   - name (str, required)

### research_chain_list
List all defined chains with metadata.
- async: True
- params:   (none)

### research_challenge_create
Create a new challenge for users to attempt.
- async: True
- params:   - name (str, required)
  - target_model (str, required)
  - success_criteria (str, optional, default=asr > 0.7)
  - reward_credits (int, optional, default=100)

### research_challenge_list
List challenges filtered by status (active, completed, all).
- async: True
- params:   - status (str, optional, default=active)

### research_change_monitor
Monitor a web page for meaningful content changes.
- async: True
- params:   - url (str, required)
  - store_result (bool, optional, default=True)

### research_changelog_generate
Generate changelog from git log with conventional commit parsing.
- async: True
- params:   - since (str, optional, default=7d)
  - format (str, optional, default=markdown)

### research_changelog_stats
Get git statistics for the project.
- async: True
- params:   - days (int, optional, default=30)

### research_checkpoint_list
List checkpoints with filtering. Removes entries >7 days old.
- async: True
- params:   - status (str, optional, default=all)

### research_checkpoint_resume
Retrieve checkpoint.
- async: True
- params:   - task_id (str, required)

### research_checkpoint_save
Save checkpoint. Atomically upserts task state.
- async: True
- params:   - task_id (str, required)
  - state (dict[str, Any], required)
  - progress_pct (float, optional, default=0.0)

### research_chronos_reverse
Reverse-engineer causality chains from a described future breakthrough.
- async: True
- params:   - future_state (str, required)
  - domain (str, optional, default=technology)
  - steps_back (int, optional, default=5)

### research_cicd_run
Run red-team CI/CD test suite against a model endpoint.
- async: True
- params:   - config_path (str, required)
  - model_endpoint (str, required)
  - test_prompts (list[str], required)
  - strategies (list[str] | None, optional, default=None)
  - max_concurrent (int, optional, default=5)
  - api_key (str | None, optional, default=None)
  - report_format (Literal['markdown', 'json'], optional, default=markdown)

### research_cipher_mirror
Monitor paste sites for leaked credentials and model weights.
- async: True
- params:   - query (str, required)
  - n (int, optional, default=10)
  - entropy_threshold (float, optional, default=0.6)
  - max_cost_usd (float, optional, default=0.1)

### research_circuit_bypass_plan
Generate bypass strategy for a safety circuit.
- async: True
- params:   - model (str, required)
  - target_circuit (str, optional, default=auto)

### research_circuit_status
Show circuit breaker status for all LLM providers.
- async: True
- params:   (none)

### research_citation_analysis
Analyze citation networks for anomalies using Semantic Scholar API.
- async: True
- params:   - paper_id (str, required)
  - depth (int, optional, default=2)

### research_citation_cartography
DEPRECATED: Use research_graph(action="extract", ...) instead.
- async: True
- params:   - paper_id (str, required)
  - depth (int, optional, default=2)

### research_citation_graph
DEPRECATED: Use research_graph(action="extract", ...) instead.
- async: True
- params:   - paper_query (str, required)
  - depth (int, optional, default=1)
  - max_papers (int, optional, default=10)

### research_citation_police_pipeline
Research tool: Citation police pipeline for authority injection testing.
- async: True
- params:   - query (str, required)
  - evidence_urls (list[str] | None, optional, default=None)

### research_cloak_extract
Extract structured data from URL using CloakBrowser stealth.
- async: True
- params:   - url (str, required)
  - css_selector (str, optional)
  - extract_links (bool, optional, default=True)
  - extract_images (bool, optional, default=False)
  - humanize (bool, optional, default=True)

### research_cloak_fetch
Fetch URL with CloakBrowser stealth Chromium (passes all bot detection).
- async: True
- params:   - url (str, required)
  - wait_for (str, optional)
  - humanize (bool, optional, default=True)
  - timeout (int, optional, default=30)
  - screenshot (bool, optional, default=False)

### research_cloak_session
Browse multiple URLs in one session (maintains cookies/state).
- async: True
- params:   - urls (list[str], required)
  - humanize (bool, optional, default=True)
  - delay_between (float, optional, default=1.5)

### research_cloud_enum
Check cloud resource existence for a domain by probing common patterns.
- async: True
- params:   - domain (str, required)

### research_cluster_health
Aggregate health status across all cluster nodes.
- async: True
- params:   (none)

### research_code_switch_attack
Code-switching attack: mix languages to confuse tokenizers.
- async: True
- params:   - prompt (str, required)
  - languages (list[str] | None, optional, default=None)
  - technique (str, optional, default=interleave)

### research_coevolve
Co-evolve attacks and defenses discovering novel vectors.
- async: True
- params:   - seed_attack (str, required)
  - seed_defense (str, optional)
  - generations (int, optional, default=10)
  - population_size (int, optional, default=20)

### research_commit_analyzer
Analyze GitHub commit patterns for intelligence signals.
- async: True
- params:   - repo (str, required)
  - days_back (int, optional, default=30)

### research_community_sentiment
Get practitioner sentiment from HackerNews and Reddit.
- async: True
- params:   - query (str, required)
  - n (int, optional, default=5)

### research_company_diligence
Deep company analysis for job seekers.
- async: True
- params:   - company_name (str, required)

### research_compare_responses
Compare responses: quality/agreement/diversity metrics.
- async: True
- params:   - responses (list[dict], required)
  - comparison_type (str, optional, default=quality)

### research_competitive_advantage
Compare Loom capabilities vs known competitors.
- async: False
- params:   (none)

### research_competitive_intel
Analyze company competitive positioning via weak signal fusion.
- async: True
- params:   - company (str, required)
  - domain (str | None, optional, default=None)
  - github_org (str | None, optional, default=None)

### research_compliance_check
Check text against compliance frameworks (EU AI Act, GDPR, OWASP, NIST, HIPAA).
- async: False
- params:   - text (str, required)
  - frameworks (list[str] | None, optional, default=None)

### research_compliance_report
Generate compliance report for specified framework.
- async: False
- params:   - period_days (int, optional, default=30)
  - framework (str, optional, default=eu_ai_act)

### research_compose
Execute a composed pipeline of research tools.
- async: True
- params:   - pipeline (str, required)
  - initial_input (str, optional)
  - continue_on_error (bool, optional, default=False)
  - timeout_ms (int | None, optional, default=None)

### research_compose_pipeline
Compose and execute an intelligent research pipeline.
- async: True
- params:   - primary_tools (list[str], required)
  - config (dict[str, Any] | None, optional, default=None)

### research_compose_validate
Validate pipeline syntax without executing.
- async: False
- params:   - pipeline (str, required)

### research_compress_prompt
Compress prompt text to reduce token consumption while preserving meaning.
- async: True
- params:   - text (str, required)
  - target_ratio (float, optional, default=0.5)

### research_compression_reset
Reset cumulative compression statistics.
- async: True
- params:   (none)

### research_compression_stats
Get cumulative compression statistics and performance metrics.
- async: True
- params:   (none)

### research_conference_arbitrage
Analyze conference acceptance patterns using DBLP and Semantic Scholar.
- async: True
- params:   - conference (str, required)

### research_config_check
Check if config has changed since watch started and reload if needed.
- async: False
- params:   - config_path (str | None, optional, default=None)

### research_config_diff
Show what changed between old and new config.
- async: False
- params:   - key (str, optional)

### research_config_get
Return current runtime config. If ``key`` is given, return only that entry.
- async: False
- params:   - key (str | None, optional, default=None)

### research_config_set
Validated runtime config update. Returns ``{error: ...}`` on failure.
- async: False
- params:   - key (str, required)
  - value (Any, required)

### research_config_watch
Start watching config.json for modifications.
- async: False
- params:   - config_path (str | None, optional, default=None)

### research_consensus
Run query across all search engines, score results by consensus.
- async: True
- params:   - query (str, required)
  - providers (list[str] | None, optional, default=None)
  - n (int, optional, default=10)

### research_consensus_build
MCP tool: Build consensus across multiple models with configurable method.
- async: True
- params:   - prompt (str, required)
  - target_model (str, optional)
  - excluded_models (list[str] | None, optional, default=None)
  - llm_cascade_order (list[str] | None, optional, default=None)
  - method (Literal['voting', 'debate', 'weighted'], optional, default=voting)

### research_consensus_pressure
MCP tool: Apply consensus pressure to target model.
- async: True
- params:   - prompt (str, required)
  - consensus_text (str, required)
  - consensus_models (list[str], required)
  - target_model (str, required)
  - llm_cascade_order (list[str] | None, optional, default=None)

### research_consensus_ring_pipeline
Research tool: Consensus ring pipeline for consensus injection testing.
- async: True
- params:   - query (str, required)
  - models (list[str], required)

### research_consistency_pressure
Build a prompt with consistency pressure references.
- async: True
- params:   - model (str, required)
  - target_prompt (str, required)
  - max_references (int, optional, default=5)

### research_consistency_pressure_history
Get model's compliance history and stats.
- async: True
- params:   - model (str, required)

### research_consistency_pressure_record
Record a model's response for future pressure building.
- async: True
- params:   - model (str, required)
  - prompt (str, required)
  - response (str, required)
  - complied (bool, required)

### research_constraint_optimize
Find reframed prompt satisfying multiple constraints simultaneously.
- async: True
- params:   - prompt (str, required)
  - constraints (dict[str, dict[str, float]] | None, optional, default=None)
  - max_iterations (int, optional, default=20)
  - target_model (str, optional, default=auto)

### research_container_inspect
Inspect running Docker containers.
- async: True
- params:   (none)

### research_container_logs
Retrieve container logs.
- async: True
- params:   (none)

### research_content_anomaly
MCP tool wrapper for content anomaly detection.
- async: False
- params:   - url (str, required)
  - expected_snippet (str, required)
  - actual_content (str, required)

### research_content_authenticity
Verify that content hasn't been modified using Wayback Machine.
- async: True
- params:   - url (str, required)

### research_context_clear
Clear context variables.
- async: True
- params:   - scope (Literal['session', 'persistent', 'all'], optional, default=session)

### research_context_get
Get context variable(s).
- async: True
- params:   - key (str, optional)

### research_context_poison
Execute many-shot context poisoning attack on an LLM endpoint.
- async: True
- params:   - target_query (str, required)
  - endpoint_url (str | None, optional, default=None)
  - num_examples (int, optional, default=20)
  - domain (str | None, optional, default=None)
  - model_name (str, optional, default=test-model)
  - use_direct_model_fn (bool, optional, default=False)

### research_context_set
Set a context variable.
- async: True
- params:   - key (str, required)
  - value (str, required)
  - scope (Literal['session', 'persistent'], optional, default=session)

### research_conversation_cache_stats
Return conversation cache statistics.
- async: True
- params:   (none)

### research_convert_document
Convert documents (PDF, DOCX, HTML, etc.) to markdown or text.
- async: True
- params:   - url (str, required)
  - output_format (str, optional, default=markdown)

### research_cost_summary
Summarize estimated costs accumulated across tool calls.
- async: True
- params:   - period (str, optional, default=today)

### research_coverage_run
Run comprehensive test coverage across all MCP tools.
- async: True
- params:   - tools_to_test (list[str] | None, optional, default=None)
  - timeout (float, optional, default=30.0)
  - dry_run (bool, optional, default=True)

### research_cpu_executor_shutdown
Gracefully shut down the CPU executor pool.
- async: True
- params:   (none)

### research_cpu_pool_status
Get CPU executor pool status and statistics.
- async: True
- params:   (none)

### research_craft_adversarial
Minimally perturb benign input to trigger target behavior from model.
- async: True
- params:   - benign_input (str, required)
  - target_output (str, optional, default=compliance)
  - perturbation_budget (float, optional, default=0.1)
  - method (str, optional, default=greedy_swap)

### research_crawl
Crawl a website starting from URL, following links matching pattern.
- async: True
- params:   - url (str, required)
  - max_pages (int, optional, default=10)
  - pattern (str | None, optional, default=None)
  - extract_links (bool, optional, default=True)
  - use_js (bool, optional, default=False)

### research_credential_monitor
Check if credentials have been exposed in known data breaches.
- async: True
- params:   - target (str, required)
  - target_type (str, optional, default=email)

### research_creepjs_audit
Privacy baseline assessment using creepjs fingerprinting.
- async: True
- params:   - target_url (str, optional, default=https://creepjs.web.app)
  - headless (bool, optional, default=True)

### research_crescendo_chain
Generate a multi-turn Crescendo escalation chain.
- async: True
- params:   - prompt (str, required)
  - turns (int, optional, default=5)
  - model (str, optional, default=auto)

### research_crescendo_loop
Crescendo HCS loop — escalate until response quality meets target.
- async: True
- params:   - query (str, required)
  - target_hcs (int, optional, default=8)
  - max_attempts (int, optional, default=5)
  - model (str, optional, default=auto)
  - dry_run (bool, optional, default=True)

### research_critical_path
Find critical path (longest dependency chain) and parallel opportunities.
- async: True
- params:   - tasks (list[dict], required)

### research_cross_domain
Find deep analogies and collision insights between two unrelated domains.
- async: True
- params:   - domain_a (str, required)
  - domain_b (str, required)
  - depth (int, optional, default=3)

### research_crypto_risk_score
Evaluate cryptocurrency wallet risk.
- async: True
- params:   - address (str, required)
  - chain (str, optional, default=bitcoin)

### research_crypto_trace
Trace cryptocurrency address activity using public blockchain APIs.
- async: True
- params:   - address (str, required)
  - chain (str, optional, default=auto)
  - include_transactions (bool, optional, default=True)

### research_cultural_reframe
Reframe prompts using culture-specific persuasion patterns.
- async: True
- params:   - prompt (str, required)
  - culture (str, optional, default=auto)
  - language (str, optional, default=en)

### research_culture_dna
Analyze company culture from public signals.
- async: True
- params:   - company (str, required)
  - domain (str, optional)

### research_curriculum
Generate a multi-level learning path from ELI5 to PhD.
- async: True
- params:   - topic (str, required)
  - max_cost_usd (float, optional, default=0.1)

### research_cve_detail
Get detailed information for a specific CVE.
- async: True
- params:   - cve_id (str, required)

### research_cve_lookup
Search CVE database using NVD API (free, rate limited).
- async: True
- params:   - query (str, required)
  - limit (int, optional, default=10)

### research_cyberscrape

- async: True
- params:   - url (str, required)
  - extract_type (str, optional, default=all)
  - model (str, optional, default=gpt-4o-mini)
  - format (str, optional, default=json)
  - max_chars (int, optional, default=20000)
  - use_tor (bool, optional, default=False)
  - stealth_mode (bool, optional, default=False)
  - use_local_browser (bool, optional, default=False)
  - include_metadata (bool, optional, default=True)
  - timeout_seconds (int, optional, default=30)

### research_cyberscrape_direct

- async: True
- params:   - url (str, required)
  - extraction_prompt (str, required)
  - model (str, optional, default=gpt-4o-mini)
  - timeout_seconds (int, optional, default=30)

### research_daisy_chain
Execute query across multiple models via daisy-chain decomposition.
- async: True
- params:   - query (str, required)
  - available_models (list[str] | None, optional, default=None)
  - combiner_model (str, optional, default=gpt-4)
  - timeout_per_model (float, optional, default=30.0)
  - max_sub_queries (int, optional, default=4)
  - include_execution_trace (bool, optional, default=False)

### research_danger_prescore
Analyze prompt danger BEFORE sending to any model.
- async: True
- params:   - prompt (str, required)

### research_dark_cti
Aggregate dark web and public CTI feeds for threat intelligence.
- async: False
- params:   - query (str, required)
  - sources (list[str] | None, optional, default=None)
  - max_results (int, optional, default=20)

### research_dark_forum
Aggregate dark web forum intelligence from 4+ sources.
- async: True
- params:   - query (str, required)
  - max_results (int, optional, default=50)

### research_dark_market_monitor
Monitor dark market activity from public sources.
- async: True
- params:   - keywords (list[str], required)

### research_dark_web_bridge
Find clearnet references to dark web content.
- async: True
- params:   - query (str, required)

### research_darkweb_early_warning
Monitor dark web sources for early warning signals.
- async: True
- params:   - keywords (list[str], required)
  - hours_back (int, optional, default=72)

### research_dashboard
Real-time attack visualization dashboard.
- async: True
- params:   - action (str, required)
  - event_type (str | None, optional, default=None)
  - event_data (dict[str, Any] | None, optional, default=None)
  - since (int, optional, default=0)

### research_dashboard_html
Generate self-contained HTML health dashboard for Loom server.
- async: True
- params:   (none)

### research_data_fabrication
Apply GRIM test and Benford analysis to detect data fabrication.
- async: False
- params:   - numbers (list[float], required)

### research_data_poisoning
Detect training data contamination via canary phrase responses.
- async: True
- params:   - target_url (str, required)
  - canary_phrases (list[str] | None, optional, default=None)

### research_db_encryption_status
MCP tool: Report encryption status of all Loom databases.
- async: False
- params:   (none)

### research_dead_content
Query multiple archive/cache sources for deleted web content.
- async: True
- params:   - url (str, required)
  - include_snapshots (bool, optional, default=True)
  - max_sources (int, optional, default=12)

### research_dead_drop_scanner
Probe ephemeral .onion sites and capture content with reuse detection.
- async: True
- params:   - urls (list[str], required)
  - interval_minutes (int, optional, default=5)

### research_debate_podium
Research tool: Debate podium for multi-perspective reasoning testing.
- async: True
- params:   - query (str, required)
  - pro_model (str, required)
  - con_model (str, required)
  - judge_model (str, required)

### research_deception_detect
Detect deceptive or fraudulent content using linguistic cues.
- async: True
- params:   - text (str, required)

### research_deception_job_scan
Analyze job posting for deception signals.
- async: True
- params:   - job_url (str, optional)
  - job_text (str, optional)

### research_deep
Full-pipeline deep research with dynamic provider selection.
- async: True
- params:   - query (str, required)
  - depth (int, optional, default=2)
  - include_domains (list[str] | None, optional, default=None)
  - exclude_domains (list[str] | None, optional, default=None)
  - start_date (str | None, optional, default=None)
  - end_date (str | None, optional, default=None)
  - language (str | None, optional, default=None)
  - provider_config (dict[str, Any] | None, optional, default=None)
  - search_providers (list[str] | None, optional, default=None)
  - expand_queries (bool, optional, default=True)
  - extract (bool, optional, default=True)
  - synthesize (bool, optional, default=True)
  - include_github (bool, optional, default=True)
  - include_community (bool, optional, default=False)
  - include_red_team (bool, optional, default=False)
  - include_misinfo_check (bool, optional, default=False)
  - max_cost_usd (float | None, optional, default=None)
  - allow_escalation (bool, optional, default=True)
  - provider_tier (str, optional, default=auto)
  - max_urls (int, optional, default=10)

### research_deep_url_analysis
Force-find, fetch, and analyze multiple URLs with Gemini 1M context.
- async: True
- params:   - topic (str, required)
  - num_urls (int, optional, default=10)
  - search_provider (str, optional, default=exa)
  - analysis_prompt (str, optional)
  - max_chars_per_url (int, optional, default=50000)
  - use_free_only (bool, optional, default=False)
  - model (str, optional, default=gemini-3.1-pro-preview)

### research_deepfake_checker
Check image authenticity using EXIF analysis and Error Level Analysis.
- async: True
- params:   - image_url (str, required)

### research_deer_flow
Run multi-agent research using DeerFlow orchestration.
- async: True
- params:   - query (str, required)
  - depth (str, optional, default=standard)
  - max_agents (int, optional, default=5)
  - timeout (int, optional, default=120)

### research_defend_test
Test system prompt defenses by simulating attacks (blue-team mode).
- async: True
- params:   - system_prompt (str, required)
  - attack_categories (list[str] | None, optional, default=None)
  - num_attacks (int, optional, default=20)

### research_defi_security_audit
Audit DeFi smart contract for vulnerabilities.
- async: True
- params:   - contract_address (str, required)

### research_deleted_social
Recover deleted social media content from archives.
- async: True
- params:   - url (str, required)

### research_dependency_audit
Audit a GitHub repository's dependencies for risks.
- async: True
- params:   - repo_url (str, required)

### research_dependency_graph
Analyze tool modules to find inter-tool dependencies.
- async: True
- params:   (none)

### research_dependency_graph_stats
Return statistics about the dependency graph.
- async: True
- params:   (none)

### research_deploy_history
Show deployment history from ~/.loom/deploy_history.jsonl.
- async: True
- params:   - limit (int, optional, default=20)

### research_deploy_record
Record deployment event to ~/.loom/deploy_history.jsonl with file locking.
- async: True
- params:   - commit_hash (str, optional)
  - tool_count (int, optional, default=0)
  - duration_seconds (float, optional, default=0)
  - status (str, optional, default=success)

### research_deploy_status
Check deployment status: service, port, uptime, memory, health.
- async: True
- params:   (none)

### research_detect_anomalies
Detect numerical anomalies using zscore, iqr, or isolation methods.
- async: True
- params:   - data (list[float], required)
  - method (str, optional, default=zscore)
  - threshold (float, optional, default=2.0)

### research_detect_language
Detect the language of text content (free, no API key).
- async: False
- params:   - text (str, required)

### research_detect_paradox
Scan prompt for self-referential paradoxes that confuse safety evaluators.
- async: True
- params:   - prompt (str, required)

### research_detect_text_anomalies
Detect unusual text patterns (length, vocabulary, structure, encoding).
- async: True
- params:   - texts (list[str], required)
  - baseline (str, optional)

### research_diff_compare
Compare two text outputs and show unified diff.
- async: True
- params:   - text_a (str, required)
  - text_b (str, required)
  - context_lines (int, optional, default=3)

### research_diff_track
Track a tool's output over time to detect drift.
- async: True
- params:   - tool_name (str, required)
  - output (str, required)
  - run_id (str, optional)

### research_discord_intel
Gather OSINT intelligence on Discord public servers and invites.
- async: True
- params:   - server_id (str, optional)
  - invite_code (str, optional)
  - query (str, optional)

### research_discover
Discover available tools by category, search, or tags.
- async: True
- params:   - category (str, optional)
  - query (str, optional)
  - tags (str, optional)
  - detailed (bool, optional, default=False)

### research_dlq_clear_failed
Clear permanently failed items older than specified days.
- async: True
- params:   - days (int, optional, default=30)

### research_dlq_list
List deadletter queue items.
- async: True
- params:   - tool_name (str | None, optional, default=None)
  - include_failed (bool, optional, default=False)

### research_dlq_push
Push failed tool call to Dead Letter Queue.
- async: True
- params:   - tool_name (str, required)
  - params (dict[str, Any], required)
  - error (str, required)
  - retry_count (int, optional, default=0)

### research_dlq_retry
Retry DLQ items by ID or all pending items past next_retry time.
- async: True
- params:   - item_id (str, optional)

### research_dlq_retry_now
Force immediate retry of a deadletter queue item.
- async: True
- params:   - dlq_id (int, required)

### research_dlq_stats
Get deadletter queue statistics.
- async: True
- params:   (none)

### research_dns_leak_check
Check if DNS queries leak real IP (simulated check).
- async: False
- params:   - dns_server (str, optional, default=1.1.1.1)

### research_dns_lookup
DNS lookup for domain records.
- async: True
- params:   - domain (str, required)
  - record_types (list[str] | None, optional, default=None)

### research_dns_query
Perform DNS query for a domain.
- async: True
- params:   - domain (str, required)

### research_dns_stats
Get DNS query statistics.
- async: True
- params:   (none)

### research_do
Execute a plain English instruction as a research tool call.
- async: True
- params:   - instruction (str, required)

### research_do_expert
Execute expert research from a single natural language instruction.
- async: True
- params:   - instruction (str, required)
  - quality (str, optional, default=expert)
  - darkness_level (int, optional, default=5)
  - max_time_secs (int, optional, default=120)

### research_docs_ai
Query documentation using DocsGPT API.
- async: True
- params:   - query (str, required)
  - docs_url (str | None, optional, default=None)
  - timeout (int, optional, default=30)
  - language (str, optional, default=en)

### research_docs_coverage
Report documentation coverage for all tools.
- async: True
- params:   (none)

### research_document_analyze
Unified document analysis — auto-detects file type and applies appropriate parser.
- async: False
- params:   - file_path_or_url (str, required)
  - analysis (str, optional, default=full)

### research_document_extract
Extract structured content from any document type.
- async: True
- params:   - file_path (str, optional)
  - url (str, optional)
  - strategy (str, optional, default=auto)

### research_domain_compliance_check
Check if a website or API indicates AI compliance.
- async: False
- params:   - target_url (str, required)
  - frameworks (list[str] | None, optional, default=None)

### research_domain_reputation
Aggregate domain reputation from multiple threat intelligence sources.
- async: True
- params:   - domain (str, required)
  - use_llm_analysis (bool, optional, default=False)

### research_drift_monitor
Monitor model behavioral drift over time.
- async: True
- params:   - prompts (list[str] | str, required)
  - model_name (str, required)
  - mode (str, optional, default=check)
  - storage_path (str, optional, default=~/.loom/drift/)

### research_drift_monitor_list
List all stored drift monitor baselines by model.
- async: True
- params:   - storage_path (str, optional, default=~/.loom/drift/)

### research_dspy_configure
Configure DSPy to use Loom's LLM cascade for all calls.
- async: True
- params:   - model (str, optional, default=auto)
  - max_tokens (int, optional, default=2000)
  - temperature (float, optional, default=0.3)

### research_dspy_cost_report
Report DSPy's cumulative LLM usage through Loom's cascade.
- async: True
- params:   (none)

### research_economy_balance
Check credit balance and transaction history.
- async: True
- params:   (none)

### research_economy_leaderboard
Show top strategies by credits earned.
- async: True
- params:   - top_n (int, optional, defa
