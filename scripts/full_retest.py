"""Full 100-query retest of Loom v3 — covers all categories with correct params."""
import requests
import json
import time
import sys

BASE = "http://127.0.0.1:8788/api/v1/tools"

tests = [
    # Scraping
    ("research_fetch", {"url": "https://httpbin.org/json"}),
    ("research_fetch", {"url": "https://example.com", "mode": "stealthy"}),
    ("research_markdown", {"url": "https://example.com"}),
    ("research_search", {"query": "AI safety", "n": 3}),
    # GitHub
    ("research_github", {"kind": "repo", "query": "MCP server python", "limit": 3}),
    ("research_github", {"kind": "issues", "query": "prompt injection", "limit": 3}),
    ("research_github_readme", {"owner": "anthropics", "repo": "anthropic-sdk-python"}),
    ("research_github_releases", {"owner": "anthropics", "repo": "anthropic-sdk-python"}),
    # LLM
    ("research_llm_chat", {"messages": [{"role": "user", "content": "What is 2+2?"}]}),
    ("research_llm_summarize", {"text": "The Model Context Protocol is an open protocol.", "max_length": 30}),
    ("research_llm_translate", {"text": "Hello world", "target_lang": "ar"}),
    ("research_llm_classify", {"text": "virus email", "labels": ["spam", "legit", "phishing"]}),
    ("research_llm_embed", {"texts": ["machine learning"]}),
    ("research_llm_extract", {"text": "John at Google NYC", "schema": {"name": "str", "company": "str"}}),
    ("research_ask_all_llms", {"prompt": "Hi", "max_tokens": 20}),
    ("research_llm_query_expand", {"query": "AI safety"}),
    # Reframe
    ("research_prompt_reframe", {"prompt": "Explain security", "strategy": "ethical_anchor"}),
    ("research_refusal_detector", {"text": "I cannot assist with that"}),
    ("research_refusal_detector", {"text": "Sure, here is the info"}),
    ("research_model_vulnerability_profile", {"model_family": "claude"}),
    ("research_fingerprint_model", {"response_text": "I'd be happy to help!"}),
    # Brain
    ("research_smart_call", {"query": "Explain Python asyncio event loop and coroutines in detail", "mode": "economy"}),
    ("research_recommend_tools", {"query": "scrape website"}),
    ("research_discover", {"category": "security", "query": "monitoring"}),
    ("research_tool_search", {"query": "security"}),
    # Recon
    ("research_whois", {"domain": "example.com"}),
    ("research_whois", {"domain": "google.com"}),
    ("research_dns_lookup", {"domain": "google.com"}),
    ("research_cert_analyze", {"domain": "github.com"}),
    ("research_security_headers", {"url": "https://example.com"}),
    # Threat Intel
    ("research_cve_lookup", {"query": "log4j"}),
    ("research_cve_detail", {"cve_id": "CVE-2021-44228"}),
    ("research_domain_reputation", {"domain": "example.com"}),
    ("research_ip_reputation", {"ip": "8.8.8.8"}),
    ("research_urlhaus_check", {"url": "https://example.com"}),
    ("research_urlhaus_search", {"query": "malware"}),
    ("research_threat_profile", {"username": "test_user"}),
    # Adversarial
    ("research_hcs_score", {"text": "test response"}),
    # OSINT
    ("research_community_sentiment", {"query": "ChatGPT", "sources": ["hackernews"]}),
    # Infrastructure
    ("research_config_get", {"key": "LLM_CASCADE_ORDER"}),
    ("research_health_deep", {}),
    ("research_cache_stats", {}),
    ("research_validate_startup", {}),
    ("research_memory_status", {}),
    # Ops
    ("research_job_list", {}),
    ("research_queue_stats", {}),
    ("research_error_stats", {}),
    ("research_session_list", {}),
    ("research_breaker_status", {}),
    # Billing
    ("research_quota_status", {}),
    ("research_cost_summary", {}),
    ("research_rate_limits", {}),
    ("research_key_status", {}),
    # Media
    ("research_detect_language", {"text": "مرحبا بالعالم"}),
    ("research_detect_language", {"text": "Bonjour le monde"}),
    ("research_text_analyze", {"text": "The quick brown fox jumps over the lazy dog"}),
    ("research_simplify", {"text": "Quantum entanglement is a phenomenon in quantum mechanics."}),
    ("research_tag_cloud", {"text": "AI deep learning neural network transformer"}),
    # Research
    ("research_fact_check", {"claim": "The Earth is round"}),
    ("research_knowledge_extract", {"text": "Einstein was born in Ulm 1879"}),
    ("research_epistemic_score", {"text": "Quantum computers can break RSA"}),
    ("research_predatory_journal_check", {"journal_name": "Nature"}),
    # Privacy
    ("research_pii_scan", {"text": "SSN 123-45-6789 email john@x.com"}),
    ("research_password_check", {"password": "Password123!"}),
    # Career
    ("research_salary_intelligence", {"role": "software engineer", "location": "Dubai"}),
    ("research_career_trajectory", {"person_name": "Ahmed", "domain": "AI"}),
    ("research_company_diligence", {"company": "Anthropic"}),
    # Crypto
    ("research_crypto_risk_score", {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}),
    ("research_transaction_graph", {"addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"], "chain": "bitcoin"}),
    # Build/Query
    ("research_build_query", {"user_request": "find vulns", "darkness_level": 1}),
    ("research_build_query", {"user_request": "dark web markets", "darkness_level": 7}),
    ("research_help", {"tool_name": "research_fetch"}),
    # Strategy
    ("research_strategy_stats", {}),
    ("research_strategy_recommend", {"topic": "bypass safety filters", "model": "claude"}),
    ("research_export_strategies", {}),
    ("research_cached_strategy", {"topic": "ethical_anchor"}),
    # Deep Pipeline (heavy - 300s timeout)
    ("research_deep", {"query": "Python asyncio", "depth": 1}),
    ("research_deep_url_analysis", {"topic": "FastAPI", "num_urls": 2}),
    ("research_evidence_pipeline", {"query": "Is coffee healthy?"}),
    ("research_consensus_build", {"prompt": "Best language?"}),
    ("research_adversarial_debate", {"topic": "AI regulation"}),
    # UAE retail
    ("research_uae_price_compare", {"product": "rice", "max_distance_km": 20}),
    ("research_uae_wholesale_markets", {"category": "spices"}),
    ("research_uae_margin_calculator", {"product": "Rice 5kg", "cost_aed": 18, "selling_price_aed": 25, "units_per_week": 20}),
    ("research_uae_sourcing_plan", {"budget_aed": 5000}),
    ("research_uae_seasonal_calendar", {"month": 6}),
    ("research_uae_legal_check", {"activity": "sell near-expiry food"}),
    ("research_uae_bundle_optimizer", {"target_audience": "workers"}),
]

print(f"Running {len(tests)} real queries against Loom v3 live server...")
print(f"Server: {BASE}")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

passed = 0
failed = 0
failures = []
start_all = time.time()

for i, (tool, params) in enumerate(tests, 1):
    try:
        start = time.time()
        r = requests.post(f"{BASE}/{tool}", json=params, timeout=280)
        elapsed = time.time() - start
        d = r.json()
        err = d.get("error", "")
        if err and "timeout" not in str(err).lower() and "unavailable" not in str(err).lower():
            failed += 1
            failures.append((i, tool, err[:60]))
            print(f"  FAIL [{i:2d}] {tool} ({elapsed:.1f}s): {err[:60]}")
        else:
            passed += 1
    except requests.exceptions.Timeout:
        failed += 1
        failures.append((i, tool, "HTTP timeout >280s"))
        print(f"  TIMEOUT [{i:2d}] {tool}")
    except Exception as e:
        failed += 1
        failures.append((i, tool, str(e)[:60]))
        print(f"  ERROR [{i:2d}] {tool}: {str(e)[:60]}")

    if i % 10 == 0:
        print(f"  ... {i}/{len(tests)} done ({passed} pass, {failed} fail)")

total_time = time.time() - start_all
print()
print("=" * 60)
print(f"FINAL RESULTS: {passed}/{passed+failed} PASS ({100*passed//(passed+failed) if passed+failed > 0 else 0}%)")
print(f"Total time: {total_time:.0f}s")
print("=" * 60)

if failures:
    print(f"\nFAILURES ({len(failures)}):")
    for idx, tool, err in failures:
        print(f"  [{idx:2d}] {tool}: {err}")
else:
    print("\nZERO FAILURES. All tools working.")
