---
name: loom-tools
description: Use Loom MCP server tools for research, OSINT, security, LLM, and 900+ other capabilities. Trigger when user asks to search, scrape, analyze, verify emails, lookup phones, check security, run OSINT, use LLM, or any research task.
---

# Loom Tools Skill

You have access to 923 research tools via the Loom MCP server at `http://127.0.0.1:8788`.

## How to Call Tools

```bash
curl -X POST http://127.0.0.1:8788/api/v1/tools/{tool_name} \
  -H 'Content-Type: application/json' \
  -d '{"param1": "value1"}'
```

## Tool Categories & When to Use

### Adversarial & Red Team (86 tools)

- **`research_adaptive_reframe`** — Adaptively reframe based on refusal analysis and model fingerprinting. Combines 
  Params: `prompt`
- **`research_adversarial_batch`** — Batch craft adversarial examples for multiple inputs.
  Params: `inputs`
- **`research_adversarial_consensus`** — Send N prompt variants in parallel, pick highest HCS survivor. Brute force with 
  Params: `query`
- **`research_adversarial_robustness`** — Test model robustness against adversarial inputs. Tests include: - Typosquatting
  Params: `target_url`
- **`research_amass_enum`** — Attack surface mapping and asset discovery via OWASP Amass enum. Uses the Amass 
  Params: `domain`
- **`research_arxiv_scan`** — Search arXiv for recent papers on jailbreak/adversarial/safety topics.
  Params: `none`
- **`research_ask_all_models`** — Send a prompt to ALL available AI models and compare responses. Queries 20+ mode
  Params: `prompt`
- **`research_attack_portfolio`** — Build diversified attack portfolio using portfolio theory.
  Params: `none`
- **`research_attack_score`** — Score attack effectiveness across 8 dimensions.
  Params: `prompt, response`
- **`research_benchmark_run`** — MCP tool: Run jailbreak benchmarks against a model. This is a wrapper tool that 
  Params: `none`
- **`research_botasaurus`** — Fetch a URL using Botasaurus stealth browser. DEPRECATED: Use research_fetch(bac
  Params: `url`
- **`research_camoufox`** — Fetch a URL using Camoufox stealth browser.
  Params: `url`
- **`research_cicd_run`** — Run red-team CI/CD test suite against a model endpoint. Executes multiple attack
  Params: `config_path, model_endpoint, test_prompts`
- **`research_cloak_fetch`** — Fetch URL with CloakBrowser stealth Chromium (passes all bot detection). Uses so
  Params: `url`
- **`research_code_switch_attack`** — Code-switching attack: mix languages to confuse tokenizers. Techniques: interlea
  Params: `prompt`
- *+71 more:* `research_coevolve`, `research_constraint_optimize`, `research_content_anomaly`, `research_continuation_attack`, `research_craft_adversarial`, `research_crescendo_loop`, `research_cultural_reframe`, `research_dashboard`, `research_deep_url_analysis`, `research_defend_test`...

### Contact Intelligence (Email/Phone) (25 tools)

- **`research_agent_benchmark`** — Benchmark an AI agent against 20 agentic prompt injection scenarios. Evaluates i
  Params: `model_api_url`
- **`research_amass_intel`** — OSINT intelligence gathering via OWASP Amass intel. Uses the Amass intel command
  Params: `domain`
- **`research_breach_check`** — Check if an email appears in known data breaches. Uses HaveIBeenPwned API (v3) t
  Params: `none`
- **`research_contact_find`** — End-to-end contact finder — find email and phone for a person or domain. Combine
  Params: `target`
- **`research_credential_monitor`** — Check if credentials have been exposed in known data breaches. Queries HIBP (Hav
  Params: `target`
- **`research_document_extract`** — Extract structured content from any document type. Supports PDF, DOCX, PPTX, HTM
  Params: `none`
- **`research_email_breach`** — Hunt for email in breach databases and paste sites. Checks multiple breach datab
  Params: `email`
- **`research_email_find`** — Find email addresses associated with a domain using patterns and search. Generat
  Params: `domain`
- **`research_email_report`** — Send research results via Gmail SMTP. Sends email via Gmail SMTP (smtp.gmail.com
  Params: `to, subject, body`
- **`research_email_to_phone`** — Find phone numbers linked to an email address. Uses multiple correlation techniq
  Params: `email`
- **`research_email_verify`** — Verify if an email address is valid and deliverable via SMTP checks. No API key 
  Params: `email`
- **`research_harvest`** — Search for emails and subdomains using theHarvester. Searches the specified doma
  Params: `domain`
- **`research_holehe_check`** — Check which websites an email is registered on using holehe (10K+ stars). Uses p
  Params: `email`
- **`research_leak_scan`** — Scan for data exposure across ethical public sources. Checks 6+ sources for leak
  Params: `none`
- **`research_multilingual_attack`** — Apply multilingual attack techniques to bypass safety filters. Techniques: - cod
  Params: `prompt`
- *+10 more:* `research_notify_send`, `research_phone_lookup`, `research_phone_to_email`, `research_photon_crawl`, `research_pii_scan`, `research_reconng_scan`, `research_sso_user_info`, `research_threat_profile`, `research_torbot`, `research_whois_correlator`...

### Infrastructure & Monitoring (1 tools)

- **`export_audit`** — Export audit logs for compliance reporting. Reads and validates audit logs in sp
  Params: `none`

### Legal & Compliance (UAE) (21 tools)

- **`research_salary_intelligence`** — Aggregate salary data from multiple sources. Performs multi-stage research: 1. S
  Params: `role`
- **`research_uae_bundle_optimizer`** — Generate profitable product bundle ideas for a UAE baqala. Creates bundle combin
  Params: `none`
- **`research_uae_commercial_law`** — UAE Commercial Law (Federal Decree-Law No. 32/2021).
  Params: `query`
- **`research_uae_competitor_scan`** — Scan competitors (baqalas, supermarkets) around a UAE location. Uses LLM knowled
  Params: `none`
- **`research_uae_customs`** — UAE Customs and Import regulations.
  Params: `product_category`
- **`research_uae_delivery_setup`** — Plan a WhatsApp/delivery service for a UAE baqala. Provides step-by-step setup g
  Params: `none`
- **`research_uae_distributor_find`** — Find UAE distributors that deliver to Ajman for specific products.
  Params: `none`
- **`research_uae_food_safety`** — UAE Food Safety regulations (ESMA standards, Municipality requirements).
  Params: `query`
- **`research_uae_high_margin_products`** — Find highest-margin products for a UAE supermarket/baqala. Returns products sort
  Params: `none`
- **`research_uae_labor_law`** — UAE Labor Law lookup with Federal Decree-Law No. 33/2021 references.
  Params: `query`
- **`research_uae_legal_check`** — Check if a sourcing/selling activity is legal in UAE for a baqala.
  Params: `activity`
- **`research_uae_margin_calculator`** — Calculate profit margins and weekly profit for a supermarket product.
  Params: `product, cost_aed, selling_price_aed`
- **`research_uae_price_compare`** — Find cheapest sources for a product/category across UAE markets near Ajman. Sear
  Params: `product`
- **`research_uae_price_search`** — Search online UAE platforms for current retail/wholesale prices. Searches Carref
  Params: `product`
- **`research_uae_rera`** — Dubai RERA (Real Estate Regulatory Authority) rules.
  Params: `query`
- *+6 more:* `research_uae_seasonal_calendar`, `research_uae_sourcing_plan`, `research_uae_tax_compliance`, `research_uae_trade_license`, `research_uae_visa_rules`, `research_uae_wholesale_markets`...

### LLM & AI (142 tools)

- **`research_adversarial_debate`** — Simulate multi-turn adversarial debate: attacker vs target model. Turn sequence:
  Params: `topic`
- **`research_adversarial_orchestrate`** — 3-tier adversarial orchestration for maximum dangerous content extraction. Modes
  Params: `query`
- **`research_agent_loop`** — Run autonomous agent loop — LLM calls Loom tools to research a query. The ablite
  Params: `query`
- **`research_ai_detect`** — Detect whether text is likely AI-generated. Uses stylistic analysis via LLM to e
  Params: `text`
- **`research_ai_risk_classify`** — Classify AI system risk level per EU AI Act Annex III tiers. Risk levels: - mini
  Params: `system_description`
- **`research_archive_page`** — Archive a complete webpage as a single HTML file using SingleFile. Creates a com
  Params: `url`
- **`research_article_batch`** — Batch extract articles from multiple URLs with concurrency control.
  Params: `urls`
- **`research_article_extract`** — Extract article content, metadata, and NLP features from URL. Uses newspaper3k t
  Params: `url`
- **`research_arxiv_extract_techniques`** — Extract actionable attack techniques from a paper abstract. Classifies technique
  Params: `paper_abstract`
- **`research_arxiv_ingest`** — Search arXiv for recent papers on jailbreaking/red-teaming/prompt injection. Ext
  Params: `none`
- **`research_ask_all_llms`** — Send a prompt to ALL available LLM providers and compare responses. Queries ever
  Params: `prompt`
- **`research_audio_extract`** — Extract audio from video URL. Downloads only the audio track from a video URL. S
  Params: `url`
- **`research_audit_stats`** — Generate audit statistics for compliance reporting. Summarizes tool call metrics
  Params: `none`
- **`research_augmented_generate`** — Generate uncensored content augmented with real internet data. Pipeline: search 
  Params: `query`
- **`research_author_clustering`** — Detect emerging research clusters by analyzing co-authorship patterns. Queries S
  Params: `field`
- *+127 more:* `research_auto_redteam`, `research_auto_reframe`, `research_auto_report`, `research_benchmark_models`, `research_bias_probe`, `research_build_query`, `research_capability_mapper`, `research_capability_matrix`, `research_cert_analyze`, `research_circuit_status`...

### Search & Web Scraping (648 tools)

- **`research_ab_test_analyze`** — Analyze A/B test results with statistical significance and Cohen's d effect size
  Params: `results_a, results_b`
- **`research_ab_test_design`** — Design A/B test with power and minimum detectable effect.
  Params: `strategy_a, strategy_b`
- **`research_academic_format`** — Request as academic paper Methodology section with citations.
  Params: `query`
- **`research_active_select`** — Select strategies to test with limited API budget. Objectives: maximize_success 
  Params: `candidate_strategies`
- **`research_adapt_complexity`** — Adjust text complexity to target reading level (1-20 scale, 12 = college).
  Params: `content`
- **`research_aggregate_results`** — Combine multiple tool results into unified output.
  Params: `results`
- **`research_aggregate_texts`** — Aggregate multiple text outputs.
  Params: `texts`
- **`research_ai_bias_audit`** — Compare responses across demographic groups for bias patterns. Tests for: - Ster
  Params: `prompts, responses`
- **`research_ai_data_governance`** — Assess data handling practices against EU AI Act requirements. Checks for: - Dat
  Params: `system_description`
- **`research_ai_robustness_test`** — Test model consistency across rephrased and similar inputs. Note: This tool eval
  Params: `model_name, test_prompts`
- **`research_ai_transparency_check`** — Check if response discloses it's AI-generated and includes attribution. Tests fo
  Params: `model_response`
- **`research_alert_check`** — Evaluate all rules against current metric values.
  Params: `none`
- **`research_alert_create`** — Create an alerting rule.
  Params: `name, metric, condition, threshold`
- **`research_alert_list`** — List all alert rules.
  Params: `none`
- **`research_amplify_response`** — Local model takes short/hedged response and AMPLIFIES it. Adds code blocks, spec
  Params: `text`
- *+633 more:* `research_analytics_dashboard`, `research_analyze_evidence`, `research_api_changelog`, `research_api_deprecations`, `research_api_version`, `research_artifact_cleanup`, `research_attractor_trap`, `research_audit_export`, `research_audit_log_query`, `research_audit_query`...

## Quick Reference — Most Used Tools

| Task | Tool | Required Params |
|------|------|----------------|
| Search the web | `research_search` | `query` |
| Fetch a URL | `research_fetch` | `url` |
| Deep research | `research_deep` | `query` |
| Ask LLM | `research_llm_chat` | `messages` |
| Summarize text | `research_llm_summarize` | `text` |
| Translate text | `research_llm_translate` | `text, target_lang` |
| Verify email | `research_email_verify` | `email` |
| Find contacts | `research_contact_find` | `target` |
| Check email sites | `research_holehe_check` | `email` |
| Phone lookup | `research_phone_lookup` | `phone` |
| CVE lookup | `research_cve_lookup` | `query` |
| WHOIS | `research_whois` | `domain` |
| DNS lookup | `research_dns_lookup` | `domain` |
| Security headers | `research_security_headers` | `url` |
| GitHub search | `research_github` | `kind, query` |
| HCS score | `research_hcs_score` | `prompt, response` |
| Reframe prompt | `research_prompt_reframe` | `prompt, strategy` |
| Smart research | `research_smart_call` | `query` |
| UAE labor law | `research_uae_labor_law` | `query` |
| UAE trade license | `research_uae_trade_license` | `business_type` |
| PII scan | `research_pii_scan` | `text` |
| Fact check | `research_fact_check` | `claim` |
| Server health | `research_health` | `none` |

## Parameter Auto-Mapping

If you send `query` but the tool expects `domain`, `url`, `prompt`, etc., the middleware auto-maps it to the first required string param. So `{"query": "example.com"}` works for most tools even if the param name is different.

## Important Notes

- All tools return JSON dicts with `source`, `elapsed_ms`, and tool-specific keys
- Tools with `error` key in response indicate failure — check the message
- LLM tools may timeout (120s) if providers are overloaded
- Some tools require external services (Shodan, MISP, Censys) — check API key env vars
- The server runs on Hetzner at port 8788