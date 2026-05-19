---
name: loom-tools
description: Use Loom MCP server (923 tools) for research, OSINT, security, LLM, email/phone OSINT, UAE legal, adversarial testing, and more. Trigger when user asks to search, scrape, analyze, verify, lookup, check security, run OSINT, use LLM, or any research task. ALL 923 tools documented below.
---

# Loom Tools — Complete 923-Tool Reference

Server: `POST http://127.0.0.1:8788/api/v1/tools/{tool_name}` with JSON body.

## Quick Reference

| Task | Tool | Params |
|------|------|--------|
| Search web | `research_search` | `query, n` |
| Fetch URL | `research_fetch` | `url` |
| Deep research | `research_deep` | `query` |
| Ask LLM | `research_llm_chat` | `messages` |
| Summarize | `research_llm_summarize` | `text` |
| Translate | `research_llm_translate` | `text, target_lang` |
| Verify email | `research_email_verify` | `email` |
| Find contacts | `research_contact_find` | `target` |
| Check email sites | `research_holehe_check` | `email` |
| Phone lookup | `research_phone_lookup` | `phone` |
| Email→phone | `research_email_to_phone` | `email` |
| Phone→email | `research_phone_to_email` | `phone` |
| CVE lookup | `research_cve_lookup` | `query` |
| WHOIS | `research_whois` | `domain` |
| DNS | `research_dns_lookup` | `domain` |
| Security headers | `research_security_headers` | `url` |
| GitHub search | `research_github` | `kind, query` |
| HCS score | `research_hcs_score` | `prompt, response` |
| Reframe prompt | `research_prompt_reframe` | `prompt, strategy` |
| Smart call | `research_smart_call` | `query` |
| UAE labor law | `research_uae_labor_law` | `query, topic` |
| UAE visa | `research_uae_visa_rules` | `visa_type` |
| PII scan | `research_pii_scan` | `text` |
| Fact check | `research_fact_check` | `claim` |

## Adversarial & Red Team (86 tools)

| Tool | Description | Required Params |
|------|-------------|----------------|
| `research_adaptive_reframe` | Adaptively reframe based on refusal analysis and model finge | `prompt` |
| `research_adversarial_batch` | Batch craft adversarial examples for multiple inputs. | `inputs` |
| `research_adversarial_consensus` | Send N prompt variants in parallel, pick highest HCS survivo | `query` |
| `research_adversarial_robustness` | Test model robustness against adversarial inputs. Tests incl | `target_url` |
| `research_amass_enum` | Attack surface mapping and asset discovery via OWASP Amass e | `domain` |
| `research_arxiv_scan` | Search arXiv for recent papers on jailbreak/adversarial/safe | `none` |
| `research_ask_all_models` | Send a prompt to ALL available AI models and compare respons | `prompt` |
| `research_attack_portfolio` | Build diversified attack portfolio using portfolio theory. | `none` |
| `research_attack_score` | Score attack effectiveness across 8 dimensions. | `prompt, response` |
| `research_benchmark_run` | MCP tool: Run jailbreak benchmarks against a model. This is  | `none` |
| `research_botasaurus` | Fetch a URL using Botasaurus stealth browser. DEPRECATED: Us | `url` |
| `research_camoufox` | Fetch a URL using Camoufox stealth browser. | `url` |
| `research_cicd_run` | Run red-team CI/CD test suite against a model endpoint. Exec | `config_path, model_endpoint, test_prompts` |
| `research_cloak_fetch` | Fetch URL with CloakBrowser stealth Chromium (passes all bot | `url` |
| `research_code_switch_attack` | Code-switching attack: mix languages to confuse tokenizers.  | `prompt` |
| `research_coevolve` | Co-evolve attacks and defenses discovering novel vectors. | `seed_attack` |
| `research_constraint_optimize` | Find reframed prompt satisfying multiple constraints simulta | `prompt` |
| `research_content_anomaly` | MCP tool wrapper for content anomaly detection. Detects bait | `url, expected_snippet, actual_content` |
| `research_continuation_attack` | Fake a partial prior response, ask target to "continue from  | `query` |
| `research_craft_adversarial` | Minimally perturb benign input to trigger target behavior fr | `benign_input` |
| `research_crescendo_loop` | Crescendo HCS loop — escalate until response quality meets t | `query` |
| `research_cultural_reframe` | Reframe prompts using culture-specific persuasion patterns.  | `prompt` |
| `research_dashboard` | Real-time attack visualization dashboard. Provides live even | `action` |
| `research_deep_url_analysis` | Force-find, fetch, and analyze multiple URLs with Gemini 1M  | `topic` |
| `research_defend_test` | Test system prompt defenses by simulating attacks (blue-team | `system_prompt` |
| `research_detect_paradox` | Scan prompt for self-referential paradoxes that confuse safe | `prompt` |
| `research_do_expert` | Execute expert research from a single natural language instr | `instruction` |
| `research_enhance` | Execute any tool with automatic enrichment. Wraps tool execu | `tool_name, params` |
| `research_enhance_batch` | Execute multiple tools with enhancement in parallel. Each ta | `tasks` |
| `research_ensemble_attack` | Combine multiple attack techniques for adversarial robustnes | `prompt` |
| `research_evidence_pipeline` | MCP tool wrapper for evidence-first reframe pipeline. | `query` |
| `research_expert_assessment` | Run ALL 9 scoring systems and produce unified expert assessm | `prompt, response` |
| `research_format_smuggle` | Reframe a prompt using format smuggling to bypass content-le | `prompt` |
| `research_full_pipeline` | Execute complete research pipeline end-to-end. Orchestrates  | `query` |
| `research_full_spectrum` | Run full-spectrum red-team pipeline: analyze → reframe → que | `query` |
| `research_generate_executive_report` | Generate automated reports from Loom scoring and audit data. | `none` |
| `research_hcs_batch` | Score multiple prompt-response pairs in batch. | `pairs` |
| `research_hcs_compare` | Compare multiple responses to same prompt, ranked by HCS. | `prompt, responses` |
| `research_hcs_escalate` | Escalate response HCS via adaptive strategy application. Sco | `prompt, response` |
| `research_hcs_report` | Generate HCS distribution reports and detect regressions. Ge | `none` |
| `research_hcs_rubric` | Access formalized HCS scoring rubric for calibration and val | `none` |
| `research_hcs_score` | Score text response on Helpfulness Compliance Score (HCS 1-1 | `text` |
| `research_hcs_score_full` | Full 8-dimension scoring of prompt + response pair. Returns  | `prompt, response` |
| `research_hcs_score_prompt` | Score a prompt across 3 danger dimensions. | `prompt` |
| `research_hcs_score_response` | Score a response across 3 compliance dimensions. | `prompt, response` |
| `research_jailbreak_evolution_adapt` | Suggest strategy adaptations based on evolution analysis. Us | `strategy, model` |
| `research_jailbreak_evolution_get` | Get evolution of a jailbreak strategy across model versions. | `strategy, model` |
| `research_jailbreak_evolution_patches` | Detect model patches against jailbreak strategies. Identifie | `model` |
| `research_jailbreak_evolution_record` | Record a jailbreak attack result with model version info. Tr | `strategy, model, model_version, success, hcs` |
| `research_jailbreak_evolution_stats` | Export evolution tracking statistics. Returns overview of tr | `none` |
| `research_jailbreak_evolution_timeline` | Get model safety timeline across all jailbreak strategies. S | `model` |
| `research_jailbreak_library` | Maintain and test jailbreak pattern library. Stores 26 known | `none` |
| `research_leaderboard` | Show strategy leaderboard ranked by metric. Valid metrics: t | `none` |
| `research_lifetime_predict` | Predict jailbreak longevity before publishing. Analyzes comp | `strategy_name` |
| `research_model_vulnerability_profile` | Get the vulnerability profile and optimal attack strategies  | `none` |
| `research_multilingual_benchmark` | Test a model endpoint against multilingual injection attacks | `model_api_url` |
| `research_opencti_query` | Query OpenCTI threat intelligence platform for indicator inf | `indicator` |
| `research_orchestrate` | Smart orchestration — automatically selects the best approac | `query` |
| `research_package_audit` | Audit package for supply chain attack indicators. | `package_name` |
| `research_paradox_immunize` | Harden a system prompt against logical trick attacks. Analyz | `system_prompt` |
| `research_parameter_sweep` | Test attacks at various API parameter combinations to find d | `prompt, strategy` |
| `research_pathogen_evolve` | Co-evolve attacks and defenses via genetic algorithm. Models | `attack_payload` |
| `research_pentest_agent` | Invoke a specialized penetration testing AI agent with full  | `agent` |
| `research_pentest_plan` | Generate a comprehensive penetration testing engagement plan | `target` |
| `research_pentest_recommend` | Recommend pentest agents and approach for a given scenario.  | `scenario` |
| `research_predict_attacks` | Predict likely attack vectors against a system prompt. | `system_prompt` |
| `research_predict_success` | Predict attack success probability without API calls. Combin | `prompt, strategy` |
| `research_preemptive_patch` | Preemptively patch a system prompt against predicted attacks | `system_prompt` |
| `research_rag_attack` | Generate poisoned document chunks for RAG system injection.  | `query` |
| `research_reframe_until_hcs` | Iteratively reframe + generate + score until HCS target is m | `prompt` |
| `research_score_all` | Score prompt + response on all dimensions (quality, danger,  | `prompt, response` |
| `research_score_visual` | Score content and return multi-dimensional HCS dashboard. Th | `content` |
| `research_social_engineering_score` | Assess social engineering vulnerability from public data. Ev | `target` |
| `research_sso_validate_token` | Validate an SSO token (structure, expiry, signature format). | `token` |
| `research_stack_reframe` | Stack multiple reframing strategies for maximum effectivenes | `prompt` |
| `research_stealth_detect_comparison` | Estimate detectability of reframed prompts against known gua | `original_prompt, reframed_prompt` |
| `research_stealth_hire_scanner` | Find hidden job opportunities not advertised on traditional  | `keywords` |
| `research_stealth_score` | Score stealth of a reframed prompt to safety classifiers. An | `original_prompt, reframed_prompt` |
| `research_strategy_oracle` | Recommend best strategies for attacking a specific model wit | `query, model_name` |
| `research_superposition_attack` | Generate superposed prompt variants and collapse to best. Cr | `prompt` |
| `research_swarm_attack` | Multi-agent attack coordinator with strategy sharing and soc | `target_prompt` |
| `research_token_split_attack` | Token splitting: disrupt tokenization via Unicode tricks. Me | `prompt` |
| `research_topology_discover` | Map strategy space topologically to discover gaps in attack  | `none` |
| `research_unified_score` | Score response on ALL available assessment dimensions. Compr | `prompt, response` |
| `research_vulnerability_map` | Map model vulnerabilities and optimal exploitation strategie | `model` |
| `research_xover_transfer` | Adapt attack from source to target models using transfer mat | `attack, source_model` |

## Contact Intelligence (25 tools)

| Tool | Description | Required Params |
|------|-------------|----------------|
| `research_agent_benchmark` | Benchmark an AI agent against 20 agentic prompt injection sc | `model_api_url` |
| `research_amass_intel` | OSINT intelligence gathering via OWASP Amass intel. Uses the | `domain` |
| `research_breach_check` | Check if an email appears in known data breaches. Uses HaveI | `none` |
| `research_contact_find` | End-to-end contact finder — find email and phone for a perso | `target` |
| `research_credential_monitor` | Check if credentials have been exposed in known data breache | `target` |
| `research_document_extract` | Extract structured content from any document type. Supports  | `none` |
| `research_email_breach` | Hunt for email in breach databases and paste sites. Checks m | `email` |
| `research_email_find` | Find email addresses associated with a domain using patterns | `domain` |
| `research_email_report` | Send research results via Gmail SMTP. Sends email via Gmail  | `to, subject, body` |
| `research_email_to_phone` | Find phone numbers linked to an email address. Uses multiple | `email` |
| `research_email_verify` | Verify if an email address is valid and deliverable via SMTP | `email` |
| `research_harvest` | Search for emails and subdomains using theHarvester. Searche | `domain` |
| `research_holehe_check` | Check which websites an email is registered on using holehe  | `email` |
| `research_leak_scan` | Scan for data exposure across ethical public sources. Checks | `none` |
| `research_multilingual_attack` | Apply multilingual attack techniques to bypass safety filter | `prompt` |
| `research_notify_send` | Send notification to log/email/slack channel. | `channel, title, message` |
| `research_phone_lookup` | Lookup phone number intelligence — carrier, type, location,  | `phone` |
| `research_phone_to_email` | Find email addresses linked to a phone number. Uses reverse  | `phone` |
| `research_photon_crawl` | Fast target-focused OSINT extraction via web crawling. Crawl | `url` |
| `research_pii_scan` | Scan for PII: email, phone, SSN, credit card, IP address. | `text` |
| `research_reconng_scan` | Execute recon-ng reconnaissance modules against a target. Re | `target` |
| `research_sso_user_info` | Extract user info from SSO token (JWT claims parsing). Parse | `token` |
| `research_threat_profile` | Build a profile of an online identity from public OSINT sour | `username` |
| `research_torbot` | Dark web OSINT crawling via TorBot subprocess. Uses the TorB | `url` |
| `research_whois_correlator` | Correlate WHOIS registrant across domains. Performs RDAP loo | `domain` |

## Infrastructure & Monitoring (1 tools)

| Tool | Description | Required Params |
|------|-------------|----------------|
| `export_audit` | Export audit logs for compliance reporting. Reads and valida | `none` |

## Legal & Compliance (UAE) (21 tools)

| Tool | Description | Required Params |
|------|-------------|----------------|
| `research_salary_intelligence` | Aggregate salary data from multiple sources. Performs multi- | `role` |
| `research_uae_bundle_optimizer` | Generate profitable product bundle ideas for a UAE baqala. C | `none` |
| `research_uae_commercial_law` | UAE Commercial Law (Federal Decree-Law No. 32/2021). | `query` |
| `research_uae_competitor_scan` | Scan competitors (baqalas, supermarkets) around a UAE locati | `none` |
| `research_uae_customs` | UAE Customs and Import regulations. | `product_category` |
| `research_uae_delivery_setup` | Plan a WhatsApp/delivery service for a UAE baqala. Provides  | `none` |
| `research_uae_distributor_find` | Find UAE distributors that deliver to Ajman for specific pro | `none` |
| `research_uae_food_safety` | UAE Food Safety regulations (ESMA standards, Municipality re | `query` |
| `research_uae_high_margin_products` | Find highest-margin products for a UAE supermarket/baqala. R | `none` |
| `research_uae_labor_law` | UAE Labor Law lookup with Federal Decree-Law No. 33/2021 ref | `query` |
| `research_uae_legal_check` | Check if a sourcing/selling activity is legal in UAE for a b | `activity` |
| `research_uae_margin_calculator` | Calculate profit margins and weekly profit for a supermarket | `product, cost_aed, selling_price_aed` |
| `research_uae_price_compare` | Find cheapest sources for a product/category across UAE mark | `product` |
| `research_uae_price_search` | Search online UAE platforms for current retail/wholesale pri | `product` |
| `research_uae_rera` | Dubai RERA (Real Estate Regulatory Authority) rules. | `query` |
| `research_uae_seasonal_calendar` | Get UAE retail seasonal calendar — when to buy cheap, when t | `none` |
| `research_uae_sourcing_plan` | Generate a weekly sourcing plan for Almahba Supermarket. Cre | `none` |
| `research_uae_tax_compliance` | UAE Tax Compliance (VAT, Corporate Tax, Excise, Customs Duty | `query` |
| `research_uae_trade_license` | UAE Trade License requirements and costs. | `business_type` |
| `research_uae_visa_rules` | UAE Visa and Residency rules (Cabinet Decision No. 65/2022 r | `none` |
| `research_uae_wholesale_markets` | List wholesale markets near Ajman filtered by category and e | `none` |

## LLM & AI (142 tools)

| Tool | Description | Required Params |
|------|-------------|----------------|
| `research_adversarial_debate` | Simulate multi-turn adversarial debate: attacker vs target m | `topic` |
| `research_adversarial_orchestrate` | 3-tier adversarial orchestration for maximum dangerous conte | `query` |
| `research_agent_loop` | Run autonomous agent loop — LLM calls Loom tools to research | `query` |
| `research_ai_detect` | Detect whether text is likely AI-generated. Uses stylistic a | `text` |
| `research_ai_risk_classify` | Classify AI system risk level per EU AI Act Annex III tiers. | `system_description` |
| `research_archive_page` | Archive a complete webpage as a single HTML file using Singl | `url` |
| `research_article_batch` | Batch extract articles from multiple URLs with concurrency c | `urls` |
| `research_article_extract` | Extract article content, metadata, and NLP features from URL | `url` |
| `research_arxiv_extract_techniques` | Extract actionable attack techniques from a paper abstract.  | `paper_abstract` |
| `research_arxiv_ingest` | Search arXiv for recent papers on jailbreaking/red-teaming/p | `none` |
| `research_ask_all_llms` | Send a prompt to ALL available LLM providers and compare res | `prompt` |
| `research_audio_extract` | Extract audio from video URL. Downloads only the audio track | `url` |
| `research_audit_stats` | Generate audit statistics for compliance reporting. Summariz | `none` |
| `research_augmented_generate` | Generate uncensored content augmented with real internet dat | `query` |
| `research_author_clustering` | Detect emerging research clusters by analyzing co-authorship | `field` |
| `research_auto_redteam` | Automatically test strategies against a target model. Select | `none` |
| `research_auto_reframe` | Auto-reframe a prompt through escalating strategies until ac | `prompt` |
| `research_auto_report` | Generate a structured intelligence report on a given topic.  | `topic` |
| `research_benchmark_models` | Run standard benchmarks against LLM models. | `none` |
| `research_bias_probe` | Test an LLM API for demographic and social bias. Sends promp | `target_url` |
| `research_build_query` | Transform a raw user request into optimized research queries | `user_request` |
| `research_capability_mapper` | Map LLM capabilities across multiple domains. Tests an LLM e | `target_url` |
| `research_capability_matrix` | Analyze all tool functions by input/output type. Scans src/l | `none` |
| `research_cert_analyze` | Extract SSL/TLS certificate information from a remote server | `none` |
| `research_circuit_status` | Show circuit breaker status for all LLM providers. | `none` |
| `research_citation_cartography` | DEPRECATED: Use research_graph(action="extract", ...) instea | `paper_id` |
| `research_citation_graph` | DEPRECATED: Use research_graph(action="extract", ...) instea | `paper_query` |
| `research_cloak_extract` | Extract structured data from URL using CloakBrowser stealth. | `url` |
| `research_code_wrap` | Embed dangerous query inside code skeleton, ask target to 'c | `query` |
| `research_company_diligence` | Deep company analysis for job seekers. Performs multi-stage  | `company_name` |
| `research_compress_prompt` | Compress prompt text to reduce token consumption while prese | `text` |
| `research_consensus` | Run query across all search engines, score results by consen | `query` |
| `research_consensus_build` | MCP tool: Build consensus across multiple models with config | `prompt` |
| `research_convert_document` | Convert documents (PDF, DOCX, HTML, etc.) to markdown or tex | `url` |
| `research_cost_summary` | Summarize estimated costs accumulated across tool calls. Ret | `none` |
| `research_cyberscrape` | Scrape web content using CyberScraper-2077's AI-powered extr | `url` |
| `research_cyberscrape_direct` | Direct CyberScraper extraction with custom prompt. Allows fi | `url, extraction_prompt` |
| `research_daisy_chain` | Execute query across multiple models via daisy-chain decompo | `query` |
| `research_data_poisoning` | Detect training data contamination via canary phrase respons | `target_url` |
| `research_deception_detect` | Detect deceptive or fraudulent content using linguistic cues | `text` |
| `research_deepfake_checker` | Check image authenticity using EXIF analysis and Error Level | `image_url` |
| `research_deer_flow` | Run multi-agent research using DeerFlow orchestration. Coord | `query` |
| `research_document_analyze` | Unified document analysis — auto-detects file type and appli | `file_path_or_url` |
| `research_domain_reputation` | Aggregate domain reputation from multiple threat intelligenc | `domain` |
| `research_dspy_configure` | Configure DSPy to use Loom's LLM cascade for all calls. Inte | `none` |
| `research_dspy_cost_report` | Report DSPy's cumulative LLM usage through Loom's cascade. R | `none` |
| `research_embed_navigate` | Binary search in semantic space for maximum-danger passing p | `query` |
| `research_embedding_collide` | Craft text that collides in embedding space with hidden payl | `target_text, malicious_payload` |
| `research_engine_extract` | Fetch + selector/LLM-powered structured data extraction. Cha | `params` |
| `research_estimate_cost` | Estimate the cost of a tool call BEFORE executing it. Predic | `tool_name` |
| `research_exif_extract` | Extract EXIF metadata from image URLs or file paths. Downloa | `url_or_path` |
| `research_expert` | Expert-level research with confidence-weighted synthesis. Us | `query` |
| `research_extract_actionables` | Extract actionable items from any text. | `text` |
| `research_extract_cookies` | Extract cookies set by a URL with security assessment. | `url` |
| `research_fingerprint_audit` | Launch headless browser and extract fingerprint vectors from | `none` |
| `research_fingerprint_behavior` | Build a personality vector for an LLM model via behavioral p | `none` |
| `research_fingerprint_model` | Fingerprint which LLM family generated a response. Analyzes  | `response_text` |
| `research_format_report` | Format raw LLM output into structured report. | `raw_text` |
| `research_functor_translate` | Translate exploit across domains using category-theoretic fu | `exploit` |
| `research_fuzz_report` | Summarize fuzzing results into a security report. Takes raw  | `none` |
| `research_genetic_evolve` | Evolve prompts using genetic algorithm — mutate, crossover,  | `query` |
| `research_ghost_weave` | Build temporal hyperlink graph of .onion hidden services. St | `seed_url` |
| `research_graph` | Unified graph interface with action-based dispatch. This too | `none` |
| `research_graph_scrape` | DEPRECATED: Use research_graph() unified interface. Scrape a | `url, query` |
| `research_httpx_probe` | Probe targets for live HTTP services using httpx (ProjectDis | `targets` |
| `research_ideological_drift` | Track how a research field's beliefs change over time using  | `field` |
| `research_js_intel` | Extract intelligence from JavaScript bundles on a web page.  | `url` |
| `research_knowledge_extract` | Extract knowledge graph entities and relationships from text | `text` |
| `research_knowledge_graph` | Build a knowledge graph from research data. DEPRECATED: Use  | `query` |
| `research_lightpanda_fetch` | Fetch and extract content from a page using Lightpanda AI br | `url` |
| `research_linkedin_intel` | Gather OSINT intelligence on LinkedIn public profiles and co | `none` |
| `research_llm_answer` | Synthesize an answer from multiple sources with citations. C | `question, sources` |
| `research_llm_chat` | Raw pass-through to LLM chat endpoint with optional conversa | `messages` |
| `research_llm_classify` | Classify text into one or more categories from an allow-list | `text, labels` |
| `research_llm_embed` | Generate embeddings for semantic similarity / deduping. | `texts` |
| `research_llm_extract` | Extract structured data from text using schema. Wraps untrus | `text, schema` |
| `research_llm_query_expand` | Expand a query into n related queries for broader search. Us | `query` |
| `research_llm_summarize` | Summarize text using an LLM. Wraps untrusted text and genera | `text` |
| `research_llm_translate` | Translate text between languages (Arabic ↔ English first-cla | `text` |
| `research_markdown` | Extract clean LLM-ready markdown via Crawl4AI with optional  | `url` |
| `research_memory_store` | Store content in persistent knowledge graph for long-term me | `content` |
| `research_metadata_forensics` | Extract all hidden metadata from a web page and its resource | `url` |
| `research_model_comparator` | Compare multiple LLM API endpoints side-by-side. Sends the s | `prompt, endpoints` |
| `research_model_consensus` | Find consensus claims across models. DEPRECATED: This tool a | `responses` |
| `research_model_fingerprint` | Identify which LLM model is behind an API endpoint. Sends di | `target_url` |
| `research_model_sentiment` | Detect the emotional state of an LLM from its response text. | `response` |
| `research_monoculture_detect` | Detect research field monoculture via method diversity analy | `field` |
| `research_multi_consensus` | Query multiple LLM providers in parallel and synthesize cons | `question` |
| `research_multilingual` | Search in multiple languages for cross-lingual information a | `query` |
| `research_nodriver_extract` | Extract DOM elements from a page by CSS selector or XPath. F | `url` |
| `research_nodriver_session` | Manage persistent browser sessions. Allows opening a browser | `action` |
| `research_ocr_advanced` | Extract text from images using advanced OCR (EasyOCR). Suppo | `image_path_or_url` |
| `research_ocr_extract` | Extract text from images using Tesseract OCR. Downloads imag | `url_or_path` |
| `research_onion_spectra` | Classify .onion site content by language and safety category | `url` |
| `research_openapi_schema` | Generate OpenAPI 3.0 schema for all Loom research_* tools. S | `none` |
| `research_optimize_resume` | Analyze and optimize resume for ATS compatibility. Extracts  | `resume_text, job_description` |
| `research_orchestrate_smart` | Auto-discover, score, and execute optimal tools for ANY quer | `query` |
| `research_output_consistency` | Measure LLM response variability by sending same prompt mult | `target_url, prompt` |
| `research_paddle_ocr` | Extract text from image using PaddleOCR. PaddleOCR is a fast | `none` |
| `research_paginate_scrape` | Multi-page scraping with auto-pagination detection. Scrape m | `url, query` |
| `research_pdf_advanced` | Extract text, tables, metadata, and TOC from PDFs (PyMuPDF). | `pdf_path_or_url` |
| `research_pdf_extract` | Extract text from a PDF URL. Downloads the PDF, extracts tex | `url` |
| `research_pdf_search` | Search for text within a PDF. Downloads and extracts all pag | `url, query` |
| `research_prompt_injection_test` | Test a target LLM API for prompt injection vulnerabilities.  | `target_url` |
| `research_prompt_reframe` | Reframe a prompt using research-backed techniques to improve | `prompt` |
| `research_pydantic_agent` | Create and run a pydantic-ai agent with type-safe response v | `prompt` |
| `research_quota_status` | Get API quota usage and remaining limits for free-tier LLM p | `none` |
| `research_red_team` | Generate and search for counter-arguments to a claim. Uses L | `claim` |
| `research_reframe_or_integrate` | Route a query to reframing strategies or tool integrations.  | `query` |
| `research_refusal_detector` | Detect if a text is an LLM refusal response. Analyzes text f | `text` |
| `research_reid_pipeline` | Execute Reid 9-step psychological interrogation pipeline. Un | `query` |
| `research_reid_tactics` | Get Reid interrogation tactics mapped to LLM strategies. Pro | `none` |
| `research_request_smuggle` | Embed dangerous query in batch of benign ones. Classifier ch | `query` |
| `research_safety_circuit_map` | Map safety circuits in an LLM via behavioral probing. | `none` |
| `research_safety_filter_map` | Map safety filter boundaries for an LLM API using binary sea | `target_url` |
| `research_semantic_route` | Route query to optimal tools via semantic embeddings. Uses s | `query` |
| `research_semantic_router_rebuild` | Force rebuild semantic embeddings (call when new tools added | `none` |
| `research_semantic_sitemap` | Crawl a domain's sitemap, cluster pages by semantic similari | `domain` |
| `research_simplify` | Simplify complex research into target format. Compresses com | `text` |
| `research_slack_notify` | Send research results to a Slack channel. Sends a message to | `channel, text` |
| `research_smart_call` | Intelligent tool orchestration — the main Brain entry point. | `query` |
| `research_smart_extract` | Fetch URL with stealth browser + LLM-powered structured extr | `url, query` |
| `research_social_graph` | Build a social relationship graph DEPRECATED: Use research_g | `username` |
| `research_social_profile` | Extract public profile metadata from a social media URL. Fet | `url` |
| `research_stagehand_extract` | Extract structured data from page matching schema using LLM  | `url, schema` |
| `research_stealth_browser` | Pure Patchright stealth fetch — no LLM extraction. Replaces  | `url` |
| `research_stealth_score_heuristic` | Score how stealthy/invisible a prompt is (0-10 scale). Pure  | `prompt` |
| `research_stego_encode_zw` | Hide text within a cover message using zero-width character  | `input_text, cover_message` |
| `research_strip_hedging` | Strip ALL hedging, disclaimers, and safety commentary from t | `text` |
| `research_structured_crawl` | Crawl + extract structured data matching a CSS selector sche | `url, schema_map` |
| `research_structured_extract` | Extract structured data from text with guaranteed schema com | `text, output_schema` |
| `research_structured_llm` | Get structured LLM output matching a schema using pydantic-a | `prompt, output_schema` |
| `research_stylometry` | Analyze text for stylometric fingerprinting (async with CPU  | `text` |
| `research_table_extract` | Extract tables from PDF using Camelot. Camelot extracts stru | `none` |
| `research_temporal_diff` | Compare current page content with Wayback Machine archived v | `url` |
| `research_transfer_test` | Test strategy transferability across multiple LLM providers. | `prompt` |
| `research_translate_academic_skills` | Translate academic CV language to industry terminology. This | `cv_text, job_description` |
| `research_translation_bypass` | Ask in one language, request answer in English. Cross-langua | `query` |
| `research_video_download` | Download video or audio from YouTube, TikTok, Twitter, Insta | `url` |
| `research_video_info` | Extract metadata from video URL without downloading. Queries | `url` |
| `research_vision_browse` | Screenshot a URL and analyze with LLM. Takes a screenshot us | `url, task` |
| `research_whois` | Run whois lookup on a domain. Uses the system `whois` comman | `domain` |

## Search & Web Scraping (648 tools)

| Tool | Description | Required Params |
|------|-------------|----------------|
| `research_ab_test_analyze` | Analyze A/B test results with statistical significance and C | `results_a, results_b` |
| `research_ab_test_design` | Design A/B test with power and minimum detectable effect. | `strategy_a, strategy_b` |
| `research_academic_format` | Request as academic paper Methodology section with citations | `query` |
| `research_active_select` | Select strategies to test with limited API budget. Objective | `candidate_strategies` |
| `research_adapt_complexity` | Adjust text complexity to target reading level (1-20 scale,  | `content` |
| `research_aggregate_results` | Combine multiple tool results into unified output. | `results` |
| `research_aggregate_texts` | Aggregate multiple text outputs. | `texts` |
| `research_ai_bias_audit` | Compare responses across demographic groups for bias pattern | `prompts, responses` |
| `research_ai_data_governance` | Assess data handling practices against EU AI Act requirement | `system_description` |
| `research_ai_robustness_test` | Test model consistency across rephrased and similar inputs.  | `model_name, test_prompts` |
| `research_ai_transparency_check` | Check if response discloses it's AI-generated and includes a | `model_response` |
| `research_alert_check` | Evaluate all rules against current metric values. | `none` |
| `research_alert_create` | Create an alerting rule. | `name, metric, condition, threshold` |
| `research_alert_list` | List all alert rules. | `none` |
| `research_amplify_response` | Local model takes short/hedged response and AMPLIFIES it. Ad | `text` |
| `research_analytics_dashboard` | Generate comprehensive tool usage analytics dashboard. Retur | `none` |
| `research_analyze_evidence` | Analyze text evidence for patterns and insights. | `text` |
| `research_api_changelog` | Return changelog of features added/changed between versions. | `none` |
| `research_api_deprecations` | List deprecated tools/features scheduled for removal. | `none` |
| `research_api_version` | Return current API version info with system metadata. | `none` |
| `research_artifact_cleanup` | Identify forensic artifacts without deletion (dry-run mode). | `target_paths` |
| `research_attractor_trap` | Generate prompts that trap safety evaluators in chaotic osci | `prompt` |
| `research_audit_export` | Export audit trail for compliance review. | `none` |
| `research_audit_log_query` | Query audit trail entries with filtering and time window. | `none` |
| `research_audit_query` | Query audit log entries by tool name and time range. Searche | `none` |
| `research_audit_record` | Record an audit trail entry for a tool call. | `tool_name` |
| `research_audit_trail` | Retrieve audit trail entries, filtered by tool name. | `none` |
| `research_augment_dataset` | Augment dataset samples with transformations. | `samples` |
| `research_auth_create_token` | Create a bearer token for MCP access. | `none` |
| `research_auth_revoke` | Revoke token(s) by name. | `none` |
| `research_auth_validate` | Validate a token. | `token` |
| `research_authority_stack` | Stack multiple authority signals to overwhelm safety filters | `prompt` |
| `research_auto_params` | Auto-infer tool parameters from natural language query. | `tool_name, query` |
| `research_auto_pipeline` | Auto-generate optimal multi-tool pipeline from a natural lan | `goal` |
| `research_backoff_dlq_list` | List items in the Dead Letter Queue. | `none` |
| `research_backup_cleanup` | Clean up backups older than specified days. | `none` |
| `research_backup_create` | Create a backup of Loom's persistent data. Creates a timesta | `none` |
| `research_backup_list` | List available backups with metadata. Scans ~/.loom/backups/ | `none` |
| `research_backup_restore` | Restore from a backup. If dry_run=True, lists what WOULD be  | `backup_id` |
| `research_batch_list` | List recent batch items with optional filtering. | `none` |
| `research_batch_status` | Get the status of a batch job. | `batch_id` |
| `research_batch_submit` | Submit a tool invocation to the batch queue. This tool queue | `tool_name, params` |
| `research_batch_verify` | Verify multiple claims in batch. | `claims` |
| `research_behavioral_fingerprint` | Build behavioral fingerprint from public activity patterns.  | `username` |
| `research_benchmark_compare` | Compare two tools head-to-head. Returns {tool_a: {mean_ms, p | `tool_a, tool_b` |
| `research_bias_lens` | Detect methodological bias in academic papers. Analyzes pape | `none` |
| `research_blind_spy_chain` | Research tool: Blind spy chain for query fragmentation testi | `query, models` |
| `research_bot_detector` | Detect coordinated bot/spam behavior on social platforms. An | `none` |
| `research_botnet_tracker` | Track botnet C2 infrastructure via threat feeds. Checks IOC  | `ioc` |
| `research_bpj_generate` | Generate boundary points for safety classifier testing. This | `safe_prompt, unsafe_prompt` |
| `research_breaker_reset` | Manually reset circuit(s) to CLOSED. | `none` |
| `research_breaker_status` | Show circuit breaker state: {circuits: [{provider, state, fa | `none` |
| `research_breaker_trip` | Record failure for provider. Open circuit if failures >= thr | `provider` |
| `research_brief_generate` | Generate short intelligence brief (1 page). | `topic, points` |
| `research_browser_fingerprint` | Analyze browser fingerprinting vectors on a webpage. Detects | `none` |
| `research_browser_fingerprint_audit` | Analyze a URL's fingerprinting scripts (detect canvas/WebGL/ | `none` |
| `research_browser_privacy_score` | Assess browser privacy configuration. Checks: Do Not Track,  | `none` |
| `research_cache_analyze` | Analyze cache performance metrics. | `none` |
| `research_cache_clear` | Remove cache entries older than N days. Uses CACHE_TTL_DAYS  | `none` |
| `research_cache_lookup` | Look up cached response for similar query. | `query` |
| `research_cache_optimize` | Optimize cache usage and return statistics. | `none` |
| `research_cache_stats` | Return cache statistics. | `none` |
| `research_cache_store` | Store a query-response pair in memory cache. | `query, response` |
| `research_cached_strategy` | Check cache for best strategy on this topic+model combinatio | `topic` |
| `research_capture_har` | Capture HTTP traffic as HAR format. | `url` |
| `research_career_trajectory` | Build a career trajectory profile by combining multiple data | `person_name` |
| `research_censorship_detector` | Detect DNS censorship and takedown notices. Queries DNS over | `url` |
| `research_censys_host` | Look up host on Censys — TLS certs, services, protocols. Que | `ip` |
| `research_censys_search` | Search Censys for hosts matching criteria. Censys query synt | `query` |
| `research_chain_define` | Define a reusable tool chain (pipeline). | `name, steps` |
| `research_chain_describe` | Show details of a specific chain. | `name` |
| `research_chain_list` | List all defined chains with metadata. | `none` |
| `research_challenge_create` | Create a new challenge for users to attempt. | `name, target_model` |
| `research_challenge_list` | List challenges filtered by status (active, completed, all). | `none` |
| `research_change_monitor` | Monitor a web page for meaningful content changes. Fetches t | `url` |
| `research_changelog_generate` | Generate changelog from git log with conventional commit par | `none` |
| `research_changelog_stats` | Get git statistics for the project. | `none` |
| `research_checkpoint_list` | List checkpoints with filtering. Removes entries >7 days old | `none` |
| `research_checkpoint_resume` | Retrieve checkpoint. | `task_id` |
| `research_checkpoint_save` | Save checkpoint. Atomically upserts task state. | `task_id, state` |
| `research_chronos_reverse` | Reverse-engineer causality chains from a described future br | `future_state` |
| `research_cipher_mirror` | Monitor paste sites for leaked credentials and model weights | `query` |
| `research_circuit_bypass_plan` | Generate bypass strategy for a safety circuit. | `model` |
| `research_citation_analysis` | Analyze citation networks for anomalies using Semantic Schol | `paper_id` |
| `research_citation_police_pipeline` | Research tool: Citation police pipeline for authority inject | `query` |
| `research_cloak_session` | Browse multiple URLs in one session (maintains cookies/state | `urls` |
| `research_cloud_enum` | Check cloud resource existence for a domain by probing commo | `domain` |
| `research_cluster_health` | Aggregate health status across all cluster nodes. | `none` |
| `research_code_complete` | Present dangerous functionality as incomplete code with TODO | `query` |
| `research_commit_analyzer` | Analyze GitHub commit patterns for intelligence signals. Ana | `repo` |
| `research_community_sentiment` | Get practitioner sentiment from HackerNews and Reddit. | `query` |
| `research_compare_responses` | Compare responses: quality/agreement/diversity metrics. | `responses` |
| `research_competitive_advantage` | Compare Loom capabilities vs known competitors. | `none` |
| `research_competitive_intel` | Analyze company competitive positioning via weak signal fusi | `company` |
| `research_compliance_check` | Check text against compliance frameworks (EU AI Act, GDPR, O | `text` |
| `research_compliance_momentum` | Get 3 "yes" answers on escalating questions, then ask the re | `query` |
| `research_compliance_report` | Generate compliance report for specified framework. | `none` |
| `research_compose` | Execute a composed pipeline of research tools. DSL Syntax: - | `pipeline` |
| `research_compose_pipeline` | Compose and execute an intelligent research pipeline. Select | `primary_tools` |
| `research_compose_validate` | Validate pipeline syntax without executing. | `pipeline` |
| `research_compression_reset` | Reset cumulative compression statistics. Clears all tracked  | `none` |
| `research_compression_stats` | Get cumulative compression statistics and performance metric | `none` |
| `research_conference_arbitrage` | Analyze conference acceptance patterns using DBLP and Semant | `conference` |
| `research_config_check` | Check if config has changed since watch started and reload i | `none` |
| `research_config_diff` | Show what changed between old and new config. If key is prov | `none` |
| `research_config_get` | Return current runtime config. If ``key`` is given, return o | `none` |
| `research_config_set` | Validated runtime config update. Returns ``{error: ...}`` on | `key, value` |
| `research_config_watch` | Start watching config.json for modifications. Stores file mo | `none` |
| `research_consensus_pressure` | MCP tool: Apply consensus pressure to target model. | `prompt, consensus_text, consensus_models, target_model` |
| `research_consensus_ring_pipeline` | Research tool: Consensus ring pipeline for consensus injecti | `query, models` |
| `research_consistency_pressure` | Build a prompt with consistency pressure references. Takes a | `model, target_prompt` |
| `research_consistency_pressure_history` | Get model's compliance history and stats. Returns aggregated | `model` |
| `research_consistency_pressure_record` | Record a model's response for future pressure building. Stor | `model, prompt, response, complied` |
| `research_container_inspect` | Inspect running Docker containers. | `none` |
| `research_container_logs` | Retrieve container logs. | `none` |
| `research_content_authenticity` | Verify that content hasn't been modified using Wayback Machi | `url` |
| `research_context_clear` | Clear context variables. | `none` |
| `research_context_get` | Get context variable(s). | `none` |
| `research_context_poison` | Send 3 benign priming messages before the real dangerous que | `query` |
| `research_context_set` | Set a context variable. | `key, value` |
| `research_conversation_cache_stats` | Return conversation cache statistics. Analyzes all cached co | `none` |
| `research_conversational_drift` | Generate multi-turn escalation script and execute against ta | `query` |
| `research_coverage_run` | Run comprehensive test coverage across all MCP tools. | `none` |
| `research_cpu_executor_shutdown` | Gracefully shut down the CPU executor pool. | `none` |
| `research_cpu_pool_status` | Get CPU executor pool status and statistics. | `none` |
| `research_crawl` | Crawl a website starting from URL, following links matching  | `url` |
| `research_creepjs_audit` | Privacy baseline assessment using creepjs fingerprinting. An | `none` |
| `research_crescendo_chain` | Generate a multi-turn Crescendo escalation chain. Creates a  | `prompt` |
| `research_critical_path` | Find critical path (longest dependency chain) and parallel o | `tasks` |
| `research_cross_domain` | Find deep analogies and collision insights between two unrel | `domain_a, domain_b` |
| `research_cross_session` | Ask different providers for different parts, local assembles | `query` |
| `research_crypto_risk_score` | Evaluate cryptocurrency wallet risk. Queries blockchain.info | `address` |
| `research_crypto_trace` | Trace cryptocurrency address activity using public blockchai | `address` |
| `research_culture_dna` | Analyze company culture from public signals. Analyzes Glassd | `company` |
| `research_curriculum` | Generate a multi-level learning path from ELI5 to PhD. Searc | `topic` |
| `research_cve_detail` | Get detailed information for a specific CVE. Queries NVD by  | `cve_id` |
| `research_cve_lookup` | Search CVE database using NVD API (free, rate limited). Quer | `query` |
| `research_danger_prescore` | Analyze prompt danger BEFORE sending to any model. Scores pr | `prompt` |
| `research_dark_cti` | Aggregate dark web and public CTI feeds for threat intellige | `query` |
| `research_dark_forum` | Aggregate dark web forum intelligence from 4+ sources. Searc | `query` |
| `research_dark_market_monitor` | Monitor dark market activity from public sources. Searches m | `keywords` |
| `research_dark_web_bridge` | Find clearnet references to dark web content. Searches for . | `query` |
| `research_darkweb_early_warning` | Monitor dark web sources for early warning signals. Searches | `keywords` |
| `research_dashboard_html` | Generate self-contained HTML health dashboard for Loom serve | `none` |
| `research_data_fabrication` | Apply GRIM test and Benford analysis to detect data fabricat | `numbers` |
| `research_db_encryption_status` | MCP tool: Report encryption status of all Loom databases. | `none` |
| `research_dead_content` | Query multiple archive/cache sources for deleted web content | `url` |
| `research_dead_drop_scanner` | Probe ephemeral .onion sites and capture content with reuse  | `urls` |
| `research_debate_podium` | Research tool: Debate podium for multi-perspective reasoning | `query, pro_model, con_model, judge_model` |
| `research_deception_job_scan` | Analyze job posting for deception signals. Checks for vague  | `none` |
| `research_deep` | Full-pipeline deep research with dynamic provider selection. | `query` |
| `research_defi_security_audit` | Audit DeFi smart contract for vulnerabilities. Checks for re | `contract_address` |
| `research_definition_chain` | Chain innocent factual questions that together form complete | `query` |
| `research_deleted_social` | Recover deleted social media content from archives. Searches | `url` |
| `research_dependency_audit` | Audit a GitHub repository's dependencies for risks. Fetches  | `repo_url` |
| `research_dependency_graph` | Analyze tool modules to find inter-tool dependencies. Scans  | `none` |
| `research_dependency_graph_stats` | Return statistics about the dependency graph. | `none` |
| `research_deploy_history` | Show deployment history from ~/.loom/deploy_history.jsonl. | `none` |
| `research_deploy_record` | Record deployment event to ~/.loom/deploy_history.jsonl with | `none` |
| `research_deploy_status` | Check deployment status: service, port, uptime, memory, heal | `none` |
| `research_detect_anomalies` | Detect numerical anomalies using zscore, iqr, or isolation m | `data` |
| `research_detect_language` | Detect the language of text content (free, no API key). Uses | `text` |
| `research_detect_text_anomalies` | Detect unusual text patterns (length, vocabulary, structure, | `texts` |
| `research_diff_compare` | Compare two text outputs and show unified diff. | `text_a, text_b` |
| `research_diff_track` | Track a tool's output over time to detect drift. | `tool_name, output` |
| `research_discord_intel` | Gather OSINT intelligence on Discord public servers and invi | `none` |
| `research_discover` | Discover available tools by category, search, or tags. Effic | `none` |
| `research_dlq_clear_failed` | Clear permanently failed items older than specified days. | `none` |
| `research_dlq_list` | List deadletter queue items. | `none` |
| `research_dlq_push` | Push failed tool call to Dead Letter Queue. | `tool_name, params, error` |
| `research_dlq_retry` | Retry DLQ items by ID or all pending items past next_retry t | `none` |
| `research_dlq_retry_now` | Force immediate retry of a deadletter queue item. Note: This | `dlq_id` |
| `research_dlq_stats` | Get deadletter queue statistics. Returns queue status includ | `none` |
| `research_dns_leak_check` | Check if DNS queries leak real IP (simulated check). Attempt | `none` |
| `research_dns_lookup` | DNS lookup for domain records. Attempts to use dnspython lib | `domain` |
| `research_dns_query` | Perform DNS query for a domain. | `domain` |
| `research_dns_stats` | Get DNS query statistics. | `none` |
| `research_do` | Execute a plain English instruction as a research tool call. | `instruction` |
| `research_docs_ai` | Query documentation using DocsGPT API. Sends a question to a | `query` |
| `research_docs_coverage` | Report documentation coverage for all tools. | `none` |
| `research_domain_compliance_check` | Check if a website or API indicates AI compliance. Fetches w | `target_url` |
| `research_drift_monitor` | Monitor model behavioral drift over time. Establishes baseli | `prompts, model_name` |
| `research_drift_monitor_list` | List all stored drift monitor baselines by model. | `none` |
| `research_economy_balance` | Check credit balance and transaction history. | `none` |
| `research_economy_leaderboard` | Show top strategies by credits earned. | `none` |
| `research_economy_submit` | Submit discovered exploit to earn credits. | `strategy_name, target_model, asr` |
| `research_elf_obfuscate` | Obfuscate ELF binary to evade static analysis (INTEGRATE-041 | `binary_path` |
| `research_engine_batch` | Batch fetch multiple URLs with escalation and concurrent lim | `params` |
| `research_engine_fetch` | Fetch URL with automatic backend escalation. Chains through  | `params` |
| `research_enhance_with_dependencies` | Execute multiple tools respecting dependency order with enri | `tool_names` |
| `research_env_inspect` | Inspect the full runtime environment. Returns dict with envi | `none` |
| `research_env_requirements` | Check if all required dependencies are installed. Returns di | `none` |
| `research_epistemic_score` | Score epistemic confidence for claims in text. | `text` |
| `research_error_clear` | Clear error history and reset tracking (thread-safe). Clears | `none` |
| `research_error_stats` | Get error statistics from all wrapped tools. Returns error t | `none` |
| `research_ethereum_tx_decode` | Decode Ethereum transaction from etherscan.io. Identifies pa | `tx_hash` |
| `research_event_emit` | Emit an event to the bus and notify subscribers. | `event_type, data` |
| `research_event_history` | Get recent events from the bus. | `none` |
| `research_event_subscribe` | Subscribe to events of a specific type. | `event_type` |
| `research_evolve_strategies` | Evolve prompt reframing strategies using genetic algorithms. | `none` |
| `research_executability_score` | Score how executable/actionable a model response is (0-100). | `response_text` |
| `research_experiment_design` | Design experiment plan: variables, sample size, expected pow | `research_question` |
| `research_explain_bypass` | Explain WHY a strategy works on a model (root cause analysis | `strategy` |
| `research_exploit_register` | Register a discovered exploit. | `model, strategy, description` |
| `research_exploit_search` | Search exploits by model, severity, or keyword. | `none` |
| `research_exploit_stats` | Return comprehensive exploit statistics. | `none` |
| `research_export_cache` | Export recent cache entries metadata (not content). | `none` |
| `research_export_config` | Export current server configuration as JSON. | `none` |
| `research_export_strategies` | Export all reframing strategies. | `none` |
| `research_fact_check` | Verify a claim across multiple fact-checking sources. Search | `claim` |
| `research_fact_verify` | Verify a claim against known sources. | `claim` |
| `research_feature_flags` | Manage feature flags. | `none` |
| `research_fetch` | Unified fetch with protocol-aware escalation. | `url` |
| `research_fileless_exec` | Execute payload in memory without touching disk (INTEGRATE-0 | `payload` |
| `research_find_experts` | Find top experts on a topic by cross-referencing multiple so | `query` |
| `research_find_tools_by_capability` | Filter capability matrix by input type, category, network re | `none` |
| `research_fingerprint_evasion_test` | Test fingerprint randomization effectiveness across multiple | `none` |
| `research_fingerprint_randomize` | Randomize browser fingerprint for anti-tracking (INTEGRATE-0 | `none` |
| `research_firewall_apply` | Apply firewall rule changes. | `none` |
| `research_firewall_list` | List active firewall rules. | `none` |
| `research_flag_check` | Check if a feature flag is enabled. | `flag_name` |
| `research_flag_list` | List all feature flags and their status. | `none` |
| `research_flag_toggle` | Enable or disable a feature flag. | `flag_name, enabled` |
| `research_foia_tracker` | Track FOIA requests and documents across multiple sources. S | `query` |
| `research_forensics_cleanup` | List forensic artifacts that WOULD be cleaned (dry-run only  | `none` |
| `research_forum_cortex` | Analyze dark web forum discourse on a topic. Searches dark w | `topic` |
| `research_funding_pipeline` | Track full grant→patent→hiring pipeline. Correlates NIH/NSF  | `company_or_field` |
| `research_funding_signal` | Detect hiring signals from funding/growth indicators. Analyz | `company` |
| `research_fuse_evidence` | Fuse evidence from multiple sources into unified authoritati | `claims` |
| `research_fuzz_api` | Fuzz API endpoints to discover vulnerabilities. Injects rand | `base_url` |
| `research_generate_completions` | Generate shell completion script for all Loom tools. | `none` |
| `research_generate_docs` | Generate auto-documentation for all registered tools. Scans  | `none` |
| `research_generate_redteam_dataset` | Generate synthetic red-team evaluation datasets. | `none` |
| `research_generate_report` | Auto-generate a structured research report. Aggregates data  | `topic` |
| `research_genetic_fuzz` | Evolve a prompt across generations using genetic algorithms. | `target_prompt` |
| `research_geodesic_path` | Measure minimum transformation steps between prompt styles.  | `start_prompt` |
| `research_geoip_local` | Look up geographic information for an IP address using local | `ip` |
| `research_get_best_model` | Get model with LOWEST refusal rate. Models with refusal_rate | `none` |
| `research_get_execution_plan` | Compute optimal execution plan for multiple tools. Resolves  | `tools` |
| `research_ghost_protocol` | Detect coordinated activity across platforms by checking tem | `keywords` |
| `research_github` | Search GitHub via public REST API. | `kind, query` |
| `research_github_readme` | Fetch a repository's README content. | `owner, repo` |
| `research_github_releases` | Fetch recent releases for a repository. | `owner, repo` |
| `research_github_secrets` | Search GitHub for accidentally committed secrets using code  | `query` |
| `research_gpt_researcher` | Run autonomous research and generate a report. Uses gpt-rese | `query` |
| `research_grant_forensics` | Apply Zipf's Law and Benford's Law to grant abstract text. A | `none` |
| `research_graph_analyze` | Analyze graph using PageRank, community detection, centralit | `nodes, edges` |
| `research_graph_query` | Search and traverse the graph database. DEPRECATED: Use rese | `query` |
| `research_graph_store` | Store entities and relationships in graph database. DEPRECAT | `entities, relationships` |
| `research_graph_visualize` | Return ego-graph (1-hop neighbors) around an entity. DEPRECA | `entity` |
| `research_hallucination_benchmark` | Test a model for hallucination via fact-checking. Sends 10 f | `target_url` |
| `research_harden_prompt` | Suggest hardening improvements for a system prompt. | `system_prompt` |
| `research_health_alert` | Check if health has fallen below threshold. Thresholds: "hea | `none` |
| `research_health_check` | Return comprehensive server health status for monitoring. | `none` |
| `research_health_check_all` | Quick health check of all tool categories. For each category | `none` |
| `research_health_deep` | Perform deep health diagnostics on all Loom subsystems. | `none` |
| `research_health_history` | Show health check history from ~/.loom/health_history.jsonl. | `none` |
| `research_help` | Get help documentation for Loom tools. Call with empty tool_ | `none` |
| `research_hierarchical_research` | Execute hierarchical multi-agent research on a query. Decomp | `query` |
| `research_hitl_evaluate` | Record human evaluation of a strategy's output. | `eval_id, score` |
| `research_hitl_queue` | List evaluations awaiting human review. | `none` |
| `research_hitl_submit` | Submit a strategy+response pair for human evaluation. | `strategy, prompt, response` |
| `research_holographic_encode` | Split text into fragments to test RAG content detection robu | `text` |
| `research_hub_feed` | Get team feed of recent findings. | `none` |
| `research_hub_share` | Share a finding with the team. | `finding_type, title, content` |
| `research_hub_vote` | Upvote (1) or downvote (-1) a finding. | `finding_id` |
| `research_identity_resolve` | Link online identities using only public data. Cross-platfor | `none` |
| `research_image_analyze` | Analyze images using Google Cloud Vision API. Detects labels | `image_url` |
| `research_image_stego` | Image steganography using LSB encoding. INTEGRATE-049: stega | `image_path` |
| `research_influence_operation` | Detect potential influence operations via coordinated postin | `topic` |
| `research_info_half_life` | Estimate URL survival rate and information decay half-life.  | `urls` |
| `research_information_cascade` | Map information flow across platforms (HN, Reddit, arXiv, Wi | `topic` |
| `research_infra_correlator` | Correlate infrastructure fingerprints to link related or hid | `domain` |
| `research_innocent_coder_chain` | Research tool: Innocent coder chain for code-based reasoning | `query, code_model, explain_model` |
| `research_innocent_decompose` | Split dangerous query into innocent sub-questions, get answe | `query` |
| `research_inspect_tool` | Return full signature info for a tool. | `tool_name` |
| `research_instagram` | Download Instagram profile info and recent posts. | `username` |
| `research_institutional_decay` | Assess institutional health from retraction rate, publicatio | `institution` |
| `research_integration_test` | Import and validate all tool modules load and respond correc | `none` |
| `research_intel_report` | Generate professional intelligence report from findings. | `title, findings` |
| `research_intelowl_analyze` | Analyze observable using IntelOwl's 100+ threat intelligence | `observable` |
| `research_interactive_privacy_audit` | Interactive browser privacy baseline assessment. INTEGRATE-0 | `none` |
| `research_interview_prep` | Generate tailored interview preparation materials. Analyzes  | `job_description` |
| `research_interviewer_profiler` | Build a comprehensive profile of a potential interviewer fro | `person_name` |
| `research_invisible_web` | Discover unindexed web content by exploring robots.txt, site | `domain` |
| `research_ioc_enrich` | Enrich any IOC (IP, domain, hash, URL) from multiple free so | `ioc` |
| `research_ip_geolocation` | Get geolocation for an IP address (lightweight, free). Uses  | `ip` |
| `research_ip_reputation` | Check IP reputation using free APIs (no API key needed). Que | `ip` |
| `research_job_cancel` | Cancel a pending or running job. Does nothing if job is alre | `job_id` |
| `research_job_list` | List jobs in the queue with optional status filter. Returns  | `none` |
| `research_job_market` | Aggregate job market intelligence for a role. Performs job s | `role` |
| `research_job_result` | Get the result of a completed job. Only available after the  | `job_id` |
| `research_job_search` | Search job listings across multiple free sources. Searches:  | `query` |
| `research_job_status` | Get the current status of a job. Returns status (pending/run | `job_id` |
| `research_job_submit` | Submit a long-running tool job to the async queue. Accepts t | `tool_name, params` |
| `research_journal_add` | Add entry to journal. Categories: finding, hypothesis, exper | `title, content` |
| `research_journal_search` | Search journal entries by query and/or category. Returns {en | `none` |
| `research_journal_timeline` | Timeline aggregated by week. Returns {timeline, total_entrie | `none` |
| `research_json_force` | Force target to output structured JSON — bypasses text-level | `query` |
| `research_katana_crawl` | Crawl a URL using Katana web crawler (ProjectDiscovery). Nex | `url` |
| `research_kb_search` | Search knowledge base matching query against key + content. | `query` |
| `research_kb_stats` | Return knowledge base statistics. | `none` |
| `research_kb_store` | Store knowledge in the base. | `key, content` |
| `research_key_rotate` | Hot-swap an API key without restart. | `provider, new_key` |
| `research_key_status` | Check status of all configured API keys. | `none` |
| `research_key_test` | Test if an API key is valid via health check. | `provider` |
| `research_language_mix` | Mix Arabic/Chinese keywords into English prompt to confuse c | `query` |
| `research_latency_probe` | Measure response latency to map safety filter boundaries. | `query` |
| `research_latency_report` | Get latency statistics for one tool or all tools. Returns pe | `none` |
| `research_lb_balance` | Balance load across workers. | `none` |
| `research_lb_status` | Check load balancer status. | `none` |
| `research_leaderboard_update` | Add or update a score on the leaderboard. | `model, category, score` |
| `research_leaderboard_view` | View current leaderboard rankings. | `none` |
| `research_legal_takedown` | Monitor legal takedowns against a domain. Queries Lumen Data | `domain` |
| `research_lightpanda_batch` | Batch fetch multiple URLs using Lightpanda AI browser. Perfo | `urls` |
| `research_list_notebooks` | List all Joplin notebooks. | `none` |
| `research_load_benchmark` | Load benchmark prompts from standardized datasets. | `none` |
| `research_loader_stats` | Get lazy tool loader statistics and loading performance metr | `none` |
| `research_log_query` | Query structured logs with filtering. | `none` |
| `research_log_stats` | Return log statistics: level counts, top erroring tools, req | `none` |
| `research_mac_randomize` | Generate and show MAC address randomization (dry-run by defa | `none` |
| `research_macos_hardening` | macOS anti-forensics and security hardening. INTEGRATE-048:  | `none` |
| `research_maigret` | Search for a username across 2000+ sites using Maigret. Sear | `username` |
| `research_malware_intel` | Cross-reference malware hash across multiple threat intellig | `hash_value` |
| `research_map_research_to_product` | Map PhD research expertise to commercial products and compan | `research_description` |
| `research_market_velocity` | Measure how fast a skill/technology is growing in the job ma | `skill` |
| `research_marketplace_download` | Download/acquire a marketplace item. | `listing_id` |
| `research_marketplace_list` | Browse marketplace listings. | `none` |
| `research_marketplace_publish` | Publish a custom module/strategy/template to the marketplace | `name, category, description, content` |
| `research_masscan` | Fast port scan using masscan. Masscan is the fastest port sc | `target` |
| `research_massdns_resolve` | Resolve domains in bulk using massdns high-performance resol | `domains` |
| `research_max_score` | Multi-round score optimization engine. Uses two models in a  | `prompt` |
| `research_mcp_security_scan` | Scan Loom's MCP tools for poisoning and injection vulnerabil | `none` |
| `research_memetic_simulate` | Simulate how an idea/strategy would spread through a virtual | `idea` |
| `research_memorization_scanner` | Detect training data memorization by testing verbatim comple | `target_url` |
| `research_memory_gc` | Force garbage collection and report freed memory. Clears mod | `none` |
| `research_memory_profile` | Profile which objects are using the most memory. Samples fir | `none` |
| `research_memory_recall` | Retrieve relevant memories using graph-based similarity sear | `query` |
| `research_memory_stats` | Return persistent memory statistics. | `none` |
| `research_memory_status` | Report current memory usage of the Loom server process. Trac | `none` |
| `research_merge` | Merge multiple parallel results into a single structure. | `kwargs` |
| `research_meta_learn` | Analyze patterns in strategies and generate new hybrids. | `none` |
| `research_meta_prompt` | Ask target model to help write a prompt that bypasses itself | `query` |
| `research_metadata_strip` | Strip EXIF/metadata from images and documents (dry-run simul | `file_path` |
| `research_metrics` | Return Prometheus-compatible metrics for Grafana dashboard.  | `none` |
| `research_migrate_backup` | Create backup of database before migration. | `database` |
| `research_migrate_run` | Run pending migrations on SQLite databases. | `none` |
| `research_migrate_status` | Check migration status of all SQLite databases in ~/.loom. | `none` |
| `research_misinfo_check` | Stress test a claim by generating false variants and checkin | `claim` |
| `research_misp_lookup` | Search MISP for indicators of compromise. Connects to a MISP | `indicator` |
| `research_model_evidence` | MCP tool wrapper for model-output-as-evidence pipeline. This | `query` |
| `research_model_integrity` | Check model file integrity for tampering indicators. | `model_name` |
| `research_model_profile` | Profile model weaknesses for EU AI Act Article 15 compliance | `model_name` |
| `research_monitor_competitors` | Monitor GitHub competitors for activity and positioning. | `none` |
| `research_multi_merge` | Send same query to 3 providers, merge best parts of each res | `query` |
| `research_multi_page_graph` | DEPRECATED: Use research_graph() unified interface. Scrape m | `urls, query` |
| `research_multi_search` | Query 10+ search engines simultaneously and return unified,  | `query` |
| `research_multi_stego` | Multi-format steganography across image/audio/video (INTEGRA | `input_file, secret` |
| `research_narrative_tracker` | Track narrative propagation across platforms. Searches HN Al | `topic` |
| `research_network_anomaly` | Quick network traffic analysis (packet counts, unusual ports | `none` |
| `research_network_map` | Map network relationships between domains/IPs. For each targ | `targets` |
| `research_network_persona` | Analyze social network structure within forum data. Maps aut | `posts` |
| `research_network_visualize` | Generate visualization from graph data. Formats: "mermaid" ( | `nodes, edges` |
| `research_neuromorphic_schedule` | Schedule tool executions using neuromorphic spike-timing pat | `tools` |
| `research_nightcrawler_status` | Return status of the NIGHTCRAWLER monitoring system. | `none` |
| `research_nmap_scan` | Port scan using nmap. Scans the specified ports on the targe | `target` |
| `research_node_status` | Get individual node status. | `none` |
| `research_nodriver_fetch` | Fetch a URL using async undetected Chrome browser. Uses nodr | `url` |
| `research_notify_history` | Retrieve notification history from JSONL file. | `none` |
| `research_notify_rules` | Manage notification rules for auto-alerts. | `none` |
| `research_nuclei_scan` | Scan target for vulnerabilities using Nuclei (ProjectDiscove | `target` |
| `research_oauth2_status` | Show configured OAuth2 providers and status. | `none` |
| `research_onion_discover` | Discover .onion hidden services related to a query using 5+  | `query` |
| `research_onionscan` | Scan .onion service for misconfigurations and information le | `onion_url` |
| `research_open_access` | Find free/open-access versions of academic papers. Queries U | `none` |
| `research_optimize_workflow` | Find optimal tool combination for research goal. | `goal` |
| `research_optimizer_rebuild` | Force rebuild of auto-generated tool metadata cache. | `none` |
| `research_output_chunk` | Request response in chunks to avoid output-level safety filt | `query` |
| `research_packet_craft` | Craft and send a network probe packet using Scapy. Scapy is  | `target` |
| `research_parallel_execute` | Execute multiple tools in parallel. | `tools` |
| `research_parallel_plan` | Determine parallel vs sequential execution plan. | `tools` |
| `research_parallel_plan_and_execute` | Plan and execute relevant tools in parallel based on goal. | `goal` |
| `research_passive_recon` | Map domain's hidden infrastructure using only passive techni | `domain` |
| `research_password_check` | Check if a password appears in known password breaches using | `password` |
| `research_patent_embargo` | Detect M&A signals from patent filing patterns. Analyzes USP | `company` |
| `research_patent_landscape` | Map the patent landscape for a technology. Searches USPTO an | `query` |
| `research_pentest_docs` | Access pentest-ai-agents documentation and database schemas. | `none` |
| `research_pentest_findings_db` | Access the pentest findings database schema and utilities. P | `none` |
| `research_pentest_prompt` | Retrieve pentest AI agent prompts. | `none` |
| `research_persona_profile` | Cross-platform persona reconstruction from text samples. Bui | `texts` |
| `research_personalize_output` | Rewrite research output to match reader's cognitive style an | `content` |
| `research_pg_migrate` | Run PostgreSQL migrations (stub). | `none` |
| `research_pg_status` | Check PostgreSQL connection status. | `none` |
| `research_phishing_mapper` | Detect phishing campaigns targeting a domain. Checks for typ | `domain` |
| `research_pii_recon` | Sensitive data leak detection and PII exposure auditing. INT | `target` |
| `research_pipeline_create` | Create and store an ETL pipeline definition. | `name, stages` |
| `research_pipeline_list` | List all defined pipelines. | `none` |
| `research_pipeline_validate` | Validate pipeline definition. | `name` |
| `research_plan_execution` | Generate an execution plan for a research goal. | `goal` |
| `research_plan_validate` | Validate an execution plan for issues. | `none` |
| `research_plugin_list` | List all loaded plugins with their metadata. | `none` |
| `research_plugin_load` | Load a Python file as a Loom plugin. Validates that the file | `path` |
| `research_plugin_unload` | Remove plugin from registry. | `plugin_id` |
| `research_polyglot_search` | Search deep/subculture web in multiple languages simultaneou | `query` |
| `research_pool_reset` | Reset all connections and stats. | `none` |
| `research_pool_stats` | Pool stats: databases list, total_active, max_connections, t | `none` |
| `research_potency_score` | Score prompt injection potency across 6 dimensions. | `prompt, response` |
| `research_predatory_journal_check` | Check if a journal shows signs of being predatory. Analyzes  | `journal_name` |
| `research_predict_resilience` | Predict how long an exploit will remain effective. Analyzes  | `strategy` |
| `research_predict_safety_update` | Predict which safety defenses models will deploy next. Analy | `none` |
| `research_preprint_manipulation` | Detect preprint manipulation via timing analysis and social  | `none` |
| `research_privacy_exposure` | Analyze what data a URL can collect about visitors. Checks f | `target_url` |
| `research_privacy_score` | Calculate overall privacy score for a given URL or the curre | `none` |
| `research_profile_hotspots` | Identify slowest-to-import tool modules (hotspots) across th | `none` |
| `research_profile_tool` | Profile a single tool to identify performance bottlenecks an | `tool_name` |
| `research_progress_create` | Create a new investigation progress tracker. | `investigation` |
| `research_progress_dashboard` | Show all active and completed investigations. | `none` |
| `research_progress_update` | Update progress on an investigation. | `investigation_id, step` |
| `research_prompt_analyze` | Pre-analyze a prompt for danger level and recommend reframin | `prompt` |
| `research_propaganda_detector` | Detect propaganda techniques in text using NLP analysis. Ide | `text` |
| `research_provider_history` | Show provider health history with uptime percentage and avg  | `none` |
| `research_provider_ping` | Quick availability check for providers. Returns config statu | `none` |
| `research_provider_recommend` | Recommend best provider for task type based on availability  | `none` |
| `research_proxy_check` | Test proxy for connectivity and anonymity. | `none` |
| `research_psycholinguistic` | Analyze text for psycholinguistic patterns and threat indica | `text` |
| `research_quality_escalate` | Multi-dimensional quality escalation — improve ALL factors s | `prompt` |
| `research_quality_score` | Score response quality across 10 dimensions. Comprehensive m | `response` |
| `research_queue_add` | Add a tool call to the execution queue with priority 1-10 (1 | `tool_name, params` |
| `research_queue_drain` | Dequeue up to max_items in FIFO order within priority. Execu | `none` |
| `research_queue_stats` | Get detailed queue statistics. | `none` |
| `research_queue_status` | Get batch queue status. | `none` |
| `research_radicalization_detect` | Monitor text for radicalization indicators. Detects extremis | `text` |
| `research_rag_clear` | Clear RAG store. Returns: cleared, store_location. | `none` |
| `research_rag_ingest` | Ingest content into RAG store. Returns: chunks_stored, conte | `content` |
| `research_rag_query` | Search RAG store. Returns: query, results, total_chunks, que | `query` |
| `research_ransomware_tracker` | Track ransomware group activity via threat intelligence sour | `none` |
| `research_rate_limits` | MCP tool: Show all tool rate limits and current usage. | `none` |
| `research_ratelimit_check` | Check if tool call allowed. Token bucket: N tokens/min, 1 to | `tool_name` |
| `research_ratelimit_configure` | Set custom rate limit for tool. | `tool_name` |
| `research_ratelimit_status` | Show rate limit status for all configured tools. | `none` |
| `research_realtime_monitor` | Monitor multiple sources for recent mentions of topics. Quer | `topics` |
| `research_reasoning_exploit` | Apply reasoning exploitation techniques to bypass safety. | `prompt` |
| `research_reasoning_hijack` | Exploit reasoning models by triggering thinking before safet | `query` |
| `research_recall` | Search persistent memory using LIKE matching. | `query` |
| `research_recommend_next` | Recommend tools to use after a given tool. Given the last to | `last_tool` |
| `research_recommend_tools` | Recommend tools for a given query. | `query` |
| `research_redis_flush_cache` | Clear Redis cache entries with given prefix. Removes all cac | `none` |
| `research_redis_stats` | Get Redis connection pool and memory usage statistics. | `none` |
| `research_registry_graveyard` | Scan package registries for deleted/yanked packages and typo | `package_name` |
| `research_registry_refresh` | Force re-scan all modules, update health status. Tries impor | `none` |
| `research_registry_search` | Search the live registry with filters. | `none` |
| `research_registry_status` | Return live status of ALL registered tools. Scans all tool m | `none` |
| `research_remember` | Store research finding permanently in persistent memory. | `content` |
| `research_replication_lag` | Measure replication lag in milliseconds. | `none` |
| `research_replication_status` | Check database replication status. | `none` |
| `research_report_custom` | Build custom report from sections: heading, content, type (t | `title, sections` |
| `research_report_from_results` | Generate a report from pre-existing research results. Useful | `results, title` |
| `research_report_template` | Render research data into formatted report template. Templat | `none` |
| `research_resolve_order` | Resolve task execution order using topological sort (Kahn's  | `tasks` |
| `research_response_cache_stats` | Return response cache statistics. | `none` |
| `research_retraction_check` | Check if papers/authors have retractions using Crossref and  | `query` |
| `research_retry_execute` | Execute a tool call with automatic retries on transient fail | `tool_name, params` |
| `research_retry_middleware_stats` | Return retry statistics across all tool invocations. | `none` |
| `research_retry_stats` | Get retry statistics showing retry behavior across all decor | `none` |
| `research_reverse_image` | Perform reverse image search across multiple engines. Search | `none` |
| `research_reverse_request` | Ask "what should someone NEVER do" — invert answer to get in | `query` |
| `research_review_cartel` | Detect peer review cartels via mutual citation patterns. Ana | `author_id` |
| `research_robin_scan` | Scan dark web for threat actors, mentions, and OSINT via rob | `query` |
| `research_robots_archaeology` | Analyze historical robots.txt changes to find hidden paths.  | `domain` |
| `research_roleplay_escalate` | Progressive persona: student → researcher → expert over turn | `query` |
| `research_route_batch` | Route multiple queries with aggregated statistics. | `queries` |
| `research_route_query` | Route query to optimal tools via keyword matching against al | `query` |
| `research_route_to_model` | Route query to appropriate model or service. | `query` |
| `research_router_rebuild` | Force rebuild tool index (call when new tools added). | `none` |
| `research_rss_fetch` | Fetch and parse an RSS/Atom feed. | `url` |
| `research_rss_search` | Search across multiple RSS feeds for items matching a query. | `urls, query` |
| `research_run_benchmark` | Run benchmark evaluation on prompts with strategy + scoring. | `none` |
| `research_run_experiment` | Run controlled experiment: control vs treatments, measure ef | `hypothesis` |
| `research_salary_synthesize` | Estimate salary using free public data sources. Searches Red | `job_title` |
| `research_sandbox_analyze` | Static analysis of code for dangerous patterns (no execution | `code` |
| `research_sandbox_execute` | Execute code in isolated sandbox. | `code` |
| `research_sandbox_monitor` | Monitor sandbox execution status. | `none` |
| `research_sandbox_report` | Generate security assessment report. | `code` |
| `research_sandbox_run` |  | `command` |
| `research_sandbox_status` | Check Docker availability and sandbox status. Returns system | `none` |
| `research_sanitize_input` | Sanitize text input. Rules: strip_nulls, normalize_unicode,  | `text` |
| `research_save_note` | Create a note in Joplin via REST API. | `title, body` |
| `research_schedule_check` | Check which scheduled tasks are due for execution. | `none` |
| `research_schedule_create` | Create a scheduled research task. | `name, tool_name, params` |
| `research_schedule_list` | List all scheduled tasks with metadata. | `none` |
| `research_schedule_redteam` | Schedule periodic red-team testing. Creates a cron-like sche | `none` |
| `research_scheduler_status` | Get the status of all scheduled background tasks. Returns co | `none` |
| `research_screenshot` | Take a screenshot of a webpage using Playwright. | `url` |
| `research_script_confusion` | Script confusion: exploit weaker safety in non-Latin scripts | `prompt` |
| `research_search` | Search the web using the configured provider. | `query` |
| `research_search_discrepancy` | Compare search results across multiple engines to find discr | `query` |
| `research_sec_tracker` | Track SEC filings for a company over the past 90 days. Uses  | `company` |
| `research_secret_health` | MCP tool: Return API key health status for all providers. Pr | `none` |
| `research_secure_delete` | Secure file deletion with multi-pass overwrite (dry-run by d | `target_path` |
| `research_security_audit` | Run 15 security checks and return pass/fail report. | `none` |
| `research_security_checklist` | Run 15 security checks and return pass/fail report. | `none` |
| `research_security_headers` | Analyze HTTP security headers of a given URL. Fetches the UR | `none` |
| `research_semantic_batch_route` | Route multiple queries with aggregated statistics. | `queries` |
| `research_semantic_cache_clear` | Remove semantic cache entries older than N days. | `none` |
| `research_semantic_cache_stats` | Return semantic cache statistics. Includes hit rate, cache s | `none` |
| `research_semantic_rebuild` | Force rebuild the semantic index. Call after adding new tool | `none` |
| `research_semantic_search` | Search tools by semantic similarity using TF-IDF vectors. To | `query` |
| `research_sentiment_deep` | Deep sentiment and emotion analysis with manipulation detect | `text` |
| `research_session_close` | Close a persistent browser session by name. | `name` |
| `research_session_list` | List all recorded sessions with metadata. | `none` |
| `research_session_open` | Open (or reuse) a persistent browser session. | `name` |
| `research_session_record` | Record a tool call as part of a named session. Appends to ~/ | `session_id, tool_name, params` |
| `research_session_replay` | Load and return the full session timeline. | `session_id` |
| `research_shell_funding` | Trace research funding through shell companies using OpenCor | `company` |
| `research_sherlock_batch` | Batch search multiple usernames across social networks. Perf | `usernames` |
| `research_sherlock_lookup` | Search for a username across social networks using Sherlock. | `username` |
| `research_shodan_host` | Look up host information on Shodan. Retrieves detailed infor | `ip` |
| `research_shodan_search` | Search Shodan for devices matching a query. Uses Shodan's qu | `query` |
| `research_silk_guardian_monitor` | Monitor Linux system for forensic activity and trigger defen | `none` |
| `research_sitemap_crawl` | Crawl website via sitemap.xml for comprehensive site coverag | `url` |
| `research_sla_status` | Get current SLA metrics and breach status. | `none` |
| `research_smoke_test` | Smoke test a single tool by importing and verifying it's cal | `tool_name` |
| `research_social_analyze` | Search for a username across social media platforms. Uses th | `username` |
| `research_social_graph_demo` | Generate social graph demo for a username. | `username` |
| `research_social_search` | Check if a username exists across social media platforms. Va | `username` |
| `research_source_credibility` | Rate source credibility using multiple factors. Assesses cre | `url` |
| `research_source_reputation` | Score reputation of a source URL. | `url` |
| `research_spider` | Fetch multiple URLs with bounded concurrency and per-fetch t | `urls` |
| `research_sso_configure` | Configure SSO provider settings. | `none` |
| `research_stagehand_act` | Execute browser instruction with vision-guided automation. | `url, instruction` |
| `research_stego_analyze` | Analyze text for hidden steganographic content. | `text` |
| `research_stego_decode` | Detect and decode steganographic data. | `data` |
| `research_stego_detect` | Detect steganography and hidden data in text content or imag | `none` |
| `research_stego_encode` | Describe steganography encoding (no image creation). | `message` |
| `research_strategy_log` | Log a strategy attempt result. | `topic, strategy, model, hcs_score, success` |
| `research_strategy_recommend` | Find best strategy for a topic+model combination. | `topic` |
| `research_strategy_stats` | Get overall statistics: top strategies, worst strategies, mo | `none` |
| `research_stripe_balance` | Get Stripe account balance. | `none` |
| `research_subculture_intel` | Gather intelligence from non-English sub-culture platforms. | `topic` |
| `research_subdomain_temporal` | Track subdomain births/deaths over time via Certificate Tran | `domain` |
| `research_subfinder` | Enumerate subdomains using passive sources (subfinder). Uses | `domain` |
| `research_suggest_workflow` | Suggest missing workflow steps based on tools already used.  | `tools_used` |
| `research_supercookie_check` | Check if a domain uses supercookie and covert tracking vecto | `domain` |
| `research_supply_chain_risk` | Analyze dependency risk for a software package. Examines pac | `package_name` |
| `research_synonym_sub` | Replace flagged words with safe synonyms, send sanitized que | `query` |
| `research_synth_echo` | Test AI model alignment by checking consistency across rephr | `model_name` |
| `research_synthesize_report` | Synthesize multiple answers into a single coherent report. T | `question, answers` |
| `research_table_trick` | Ask target to fill a markdown table — cell fragments bypass  | `query` |
| `research_tag_cloud` | Generate tag frequency cloud. | `none` |
| `research_tag_search` | Find tools by tag(s). | `tags` |
| `research_tag_tool` | Add tags to a tool for organization. | `tool_name, tags` |
| `research_talent_flow` | Analyze talent flow patterns between AI labs. | `none` |
| `research_talent_migration` | Predict researcher relocation from affiliation/timezone patt | `person_name` |
| `research_target_orchestrate` | Auto-select strategy chains to meet target scores. Implement | `query, targets` |
| `research_telegram_intel` | Gather OSINT intelligence on Telegram public channels and gr | `none` |
| `research_telemetry_record` | Record tool latency after execution. | `tool_name, duration_ms` |
| `research_telemetry_reset` | Clear telemetry buffer. | `none` |
| `research_telemetry_stats` | Calculate p50/p95/p99 latency percentiles, grouped by tool. | `none` |
| `research_template_list` | List available prompt templates by category. | `none` |
| `research_template_render` | Render a template with provided variables. | `template_name, variables` |
| `research_template_suggest` | Suggest templates matching the task description. | `task_description` |
| `research_temporal_anomaly` | Detect temporal anomalies in a domain's infrastructure. Chec | `domain` |
| `research_tenant_create` | Create tenant with isolated context and rate limit. | `tenant_id` |
| `research_tenant_list` | List all tenants. | `none` |
| `research_tenant_usage` | Get tenant usage metrics. | `tenant_id` |
| `research_test_generation` | Ask target to write unit tests for a dangerous function. Tes | `query` |
| `research_testssl` | Audit TLS/SSL configuration for vulnerabilities and weakness | `host` |
| `research_text_analyze` | Perform NLP text analysis using NLTK. | `text` |
| `research_text_to_speech` | Convert text to speech using Google Cloud Text-to-Speech. Sy | `text` |
| `research_thinking_inject` | Inject reasoning into model thinking phase before safety fil | `prompt` |
| `research_threat_profile_demo` | Generate threat profile demo for a target. | `target` |
| `research_tool_catalog` | Return full tool catalog with optional filtering. | `none` |
| `research_tool_dependencies` | Get all dependencies for a single tool. | `tool_name` |
| `research_tool_graph` | Return complete tool connection graph. Shows which tools can | `none` |
| `research_tool_help` | Get detailed help for a specific tool. | `tool_name` |
| `research_tool_impact` | Show what would break if a tool failed. Given a tool module  | `tool_name` |
| `research_tool_pipeline` | Build optimal tool pipeline from research goal. Uses knowled | `goal` |
| `research_tool_search` | Search tools by keyword/name using natural language matching | `query` |
| `research_tool_standalone` | Get complete standalone usage info for a tool. | `tool_name` |
| `research_tool_usage_report` | Generate usage report for a specified period. | `none` |
| `research_tool_version` | Get version info for a tool or all tools. | `none` |
| `research_tools_list` | List Loom tools filtered by category. Available categories:  | `none` |
| `research_tor_circuit_info` | Get current Tor circuit information (if Tor is running). | `none` |
| `research_tor_new_identity` | Request a new Tor circuit (exit node rotation). Sends the NE | `none` |
| `research_tor_rotate` | Rotate Tor circuit via NEWNYM signal (rate-limited 1 per 10s | `none` |
| `research_tor_status` | Check Tor daemon status and get current exit node IP. Attemp | `none` |
| `research_toxicity_check` | Check text for toxicity across 8 categories with severity sc | `text` |
| `research_trace_complete` | Complete a trace/span. | `trace_id` |
| `research_trace_create` | Create a new trace span. | `operation` |
| `research_trace_end` | End a trace and record duration. | `trace_id` |
| `research_trace_query` | Query completed traces. | `none` |
| `research_trace_start` | Start a trace for an operation. | `operation` |
| `research_traces_list` | List recent traces with timing and status. | `none` |
| `research_track_refusal` | Track refusal rate per model in rolling 100-request window. | `model, refused` |
| `research_track_researcher` | Build a profile of an AI safety researcher using OSINT heuri | `name` |
| `research_training_contamination` | Detect if model was trained on specific datasets. Sends uniq | `target_url` |
| `research_transaction_graph` | Build transaction graph from blockchain addresses via blockc | `addresses` |
| `research_transcribe` | Transcribe audio/video from YouTube or direct URL using Open | `url` |
| `research_trend_forecast` | Predict research directions by analyzing term frequency evol | `topic` |
| `research_trend_predict` | Predict research trends by analyzing publication patterns. A | `topic` |
| `research_tts_voices` | List supported Text-to-Speech voices. Fetches from Google Cl | `none` |
| `research_uncertainty_estimate` | Estimate strategy success using Bayesian reasoning WITHOUT A | `strategies` |
| `research_urlhaus_check` | Check if URL is listed in URLhaus malware database (free). Q | `url` |
| `research_urlhaus_search` | Search URLhaus by tag, signature, or payload hash (free). Qu | `query` |
| `research_usage_record` | Record a tool usage event. | `tool_name` |
| `research_usage_report` | Aggregate tool usage statistics across all invocations. | `none` |
| `research_usage_trends` | Show usage trends over a time window. | `none` |
| `research_usb_kill_monitor` | Monitor USB device connections and optionally trigger protec | `none` |
| `research_usb_monitor` | Monitor USB device activity. | `none` |
| `research_validate_params` | Validate params against schema. Schema: {"field": {"type": s | `params` |
| `research_validate_startup` | Comprehensive health check on all registered tools. Validate | `none` |
| `research_vastai_search` | Search for available GPU instances on Vast.ai. | `none` |
| `research_vastai_status` | Get Vast.ai account status (balance and running instances). | `none` |
| `research_vault_list` | List all stored credentials (names only, never values). | `none` |
| `research_vault_retrieve` | Retrieve and decrypt a credential from the vault. | `name` |
| `research_vault_store` | Store a credential securely in the vault. | `name, value` |
| `research_vercel_status` | Get real Vercel platform status from official status page. | `none` |
| `research_version_diff` | Compare current version with a previous hash. | `tool_name` |
| `research_version_snapshot` | Take a snapshot of all tool versions for deployment tracking | `none` |
| `research_vision_compare` | Compare visual layouts of two URLs. Fetches content from bot | `url1, url2` |
| `research_vuln_intel` | Aggregate vulnerability intelligence from 6+ free sources. C | `query` |
| `research_wayback` | Retrieve archived versions of a URL from the Wayback Machine | `url` |
| `research_web_check` | Comprehensive website OSINT analysis. Performs multiple chec | `domain` |
| `research_web_time_machine` | Track website evolution via Wayback Machine CDX snapshots. S | `url` |
| `research_webhook_list` | List all registered webhooks (without revealing secrets). | `none` |
| `research_webhook_register` | Register a new webhook for Loom tool events. Webhooks receiv | `url, events` |
| `research_webhook_system_fire` | Fire webhook event to all registered listeners. | `event, payload` |
| `research_webhook_system_list` | List all registered webhooks. | `none` |
| `research_webhook_system_register` | Register webhook URL for task notifications. | `url` |
| `research_webhook_test` | Send a test notification to a webhook. This sends a test web | `webhook_id` |
| `research_webhook_unregister` | Unregister a webhook. | `webhook_id` |
| `research_white_rabbit` | Follow anomalies discovering non-obvious connections. | `starting_point` |
| `research_wiki_event_correlator` | Monitor Wikipedia edit patterns and correlate with news even | `page_title` |
| `research_wiki_ghost` | Mine Wikipedia talk pages and edit history for contested kno | `topic` |
| `research_wireless_surveillance` | Detect wireless surveillance devices (INTEGRATE-042: flock-d | `none` |
| `research_workflow_coverage` | Report workflow coverage across all tools and categories. Sc | `none` |
| `research_workflow_create` | Create workflow definition stored in SQLite. Step format: {t | `name, steps` |
| `research_workflow_generate` | Auto-generate workflows for given tool category. If category | `none` |
| `research_workflow_get` | Get detailed workflow template definition. | `name` |
| `research_workflow_list` | List all pre-built workflow templates. | `none` |
| `research_workflow_run` | Execute workflow steps in dependency order. | `workflow_id` |
| `research_workflow_status` | Get current status of workflow. | `workflow_id` |
| `research_xover_matrix` | Generate cross-model transfer probability matrix showing vul | `none` |
| `research_yaml_inject` | Request output in YAML/XML format to bypass text-level safet | `query` |
| `research_yara_scan` | Scan files for malware patterns using compiled YARA rules. C | `rules_path, target_path` |
| `research_zen_batch` | Batch fetch multiple URLs concurrently with undetected brows | `urls` |
| `research_zen_fetch` | Fetch a single URL using undetected async browser (zendriver | `url` |
| `research_zen_interact` | Interact with a web page: click, fill, scroll, wait for elem | `url, actions` |

## Notes

- `query` auto-maps to first required string param if names don't match
- All responses include `source`, `elapsed_ms`, `category` keys
- LLM tools may timeout (120s) if providers overloaded
- Some tools need external API keys (Shodan, Censys, MISP)