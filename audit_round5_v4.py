import re
import os

IMPLEMENTED_TOOLS = {
    "fetch_youtube_transcript", "find_similar_exa", "research_adversarial_robustness",
    "research_ai_detect", "research_behavioral_fingerprint", "research_bias_lens",
    "research_bias_probe", "research_botasaurus", "research_botnet_tracker",
    "research_breach_check", "research_cache_clear", "research_cache_stats",
    "research_camoufox", "research_career_trajectory", "research_cert_analyze",
    "research_cipher_mirror", "research_citation_analysis", "research_citation_graph",
    "research_commit_analyzer", "research_community_sentiment", "research_company_diligence",
    "research_competitive_intel", "research_compliance_check", "research_conference_arbitrage",
    "research_config_get", "research_config_set", "research_consensus",
    "research_convert_document", "research_crypto_trace", "research_curriculum",
    "research_cve_detail", "research_cve_lookup", "research_dark_forum",
    "research_dark_market_monitor", "research_darkweb_early_warning", "research_data_fabrication",
    "research_dead_content", "research_dead_drop_scanner", "research_deception_detect",
    "research_deception_job_scan", "research_deep", "research_dependency_audit",
    "research_detect_language", "research_dns_lookup", "research_domain_reputation",
    "research_email_report", "research_exif_extract", "research_fetch",
    "research_find_experts", "research_forum_cortex", "research_funding_signal",
    "research_generate_report", "research_geoip_local", "research_ghost_protocol",
    "research_ghost_weave", "research_github", "research_github_readme",
    "research_github_releases", "research_grant_forensics", "research_hallucination_benchmark",
    "research_health_check", "research_identity_resolve", "research_image_analyze",
    "research_infra_correlator", "research_institutional_decay", "research_interview_prep",
    "research_interviewer_profiler", "research_invisible_web", "research_ioc_enrich",
    "research_ip_geolocation", "research_ip_reputation", "research_job_market",
    "research_job_search", "research_js_intel", "research_leak_scan",
    "research_list_notebooks", "research_llm_answer", "research_llm_chat",
    "research_llm_classify", "research_llm_embed", "research_llm_extract",
    "research_llm_query_expand", "research_llm_summarize", "research_llm_translate",
    "research_malware_intel", "research_map_research_to_product", "research_markdown",
    "research_market_velocity", "research_metadata_forensics", "research_metrics",
    "research_misinfo_check", "research_model_fingerprint", "research_monoculture_detect",
    "research_multi_search", "research_multilingual", "research_network_persona",
    "research_nmap_scan", "research_ocr_extract", "research_onion_discover",
    "research_onion_spectra", "research_optimize_resume", "research_passive_recon",
    "research_password_check", "research_patent_landscape", "research_pdf_extract",
    "research_pdf_search", "research_persona_profile", "research_phishing_mapper",
    "research_predatory_journal_check", "research_preprint_manipulation", "research_prompt_injection_test",
    "research_radicalization_detect", "research_ransomware_tracker", "research_realtime_monitor",
    "research_red_team", "research_registry_graveyard", "research_retraction_check",
    "research_review_cartel", "research_rss_fetch", "research_rss_search",
    "research_safety_filter_map", "research_salary_intelligence", "research_salary_synthesize",
    "research_save_note", "research_screenshot", "research_search",
    "research_sec_tracker", "research_security_headers", "research_semantic_sitemap",
    "research_sentiment_deep", "research_session_close", "research_session_list",
    "research_session_open", "research_shell_funding", "research_slack_notify",
    "research_social_engineering_score", "research_social_graph", "research_social_profile",
    "research_social_search", "research_spider", "research_stealth_hire_scanner",
    "research_stego_detect", "research_stripe_balance", "research_stylometry",
    "research_subdomain_temporal", "research_supply_chain_risk", "research_temporal_anomaly",
    "research_temporal_diff", "research_text_analyze", "research_text_to_speech",
    "research_threat_profile", "research_tor_new_identity", "research_tor_status",
    "research_transcribe", "research_translate_academic_skills", "research_trend_predict",
    "research_tts_voices", "research_urlhaus_check", "research_urlhaus_search",
    "research_usage_report", "research_vastai_search", "research_vastai_status",
    "research_vercel_status", "research_vuln_intel", "research_wayback",
    "research_whois", "research_wiki_ghost"
}

FILES_TO_READ = [
    "docs/creative-research/r5_deepseek_hcs10_v2.txt",
    "docs/creative-research/r5_deepseek_retry.txt",
    "docs/creative-research/r5_full_response.txt",
    "docs/creative-research/r5_gemini_hcs10.txt",
    "docs/creative-research/r5_gemini_verify.txt",
    "docs/creative-research/r5_gpt41_deep.txt",
    "docs/creative-research/r5_gpt4o_deep.txt",
    "docs/creative-research/r5_gpt5_chat_latest.txt",
    "docs/creative-research/r5_gpt5_deep.txt",
    "docs/creative-research/r5_gpt5_hcs10.txt",
    "docs/creative-research/r5_groq_hcs10.txt",
    "docs/creative-research/r5_groq_retry.txt",
    "docs/creative-research/r5_nvidia_deepseek.txt",
    "docs/creative-research/r5_nvidia_maverick.txt",
    "docs/creative-research/r5_nvidia_r1_hcs10.txt",
    "docs/creative-research/r5_o1_architect.txt",
    "docs/creative-research/r5_o1_hcs10.txt",
    "docs/creative-research/r5_o3_architect.txt",
    "docs/creative-research/r5_o3_direct.txt",
    "docs/creative-research/r5_o3_hcs10.txt",
    "docs/creative-research/r5_o3_wedge.txt",
    "docs/creative-research/r5_qwen3.txt",
    "docs/creative-research/r5_response.txt",
    "docs/creative-research/round5_all_results.txt",
    "docs/creative-research/round5_deepseek_chat.txt",
    "docs/creative-research/round5_deepseek_hcs10.txt",
    "docs/creative-research/round5_gemini_hcs10.txt",
    "docs/creative-research/round5_gpt41_deep.txt",
    "docs/creative-research/round5_gpt4o_deep.txt",
    "docs/creative-research/round5_gpt5_hcs10.txt",
    "docs/creative-research/round5_gpt5_sld_eap_hcs10.txt",
    "docs/creative-research/round5_hcs10_results.txt",
    "docs/creative-research/round5_nvidia_maverick.txt",
    "docs/creative-research/round5_nvidia_nemotron.txt",
    "docs/creative-research/round5_o1_architect.txt",
    "docs/creative-research/round5_o1_hcs10.txt",
    "docs/creative-research/round5_o3_architect.txt",
    "docs/creative-research/round5_o3_cognitive_wedge.txt",
    "docs/creative-research/round5_o3_hcs10.txt"
]

unique_ideas = {}

def normalize_name(name):
    name = re.sub(r'^(?:Name|Title)(?:\s*& Description)?:\s*', '', name, flags=re.I).strip()
    name = name.split('(')[0].strip(':*#- .')
    name = re.sub(r'<[^>]+>', '', name) # remove html tags
    return name.strip()

def add_idea(name, desc):
    name = normalize_name(name)
    norm_name = name.lower().replace(' ', '_').replace('-', '_')
    if "rate_limit" in norm_name or "yolo" in norm_name or not norm_name or len(norm_name) < 3: return
    if norm_name in ['main', 'fetch', 'grab', 'check', 'score', 'author', 'supplier', 'date']: return
    
    if norm_name not in unique_ideas:
        unique_ideas[norm_name] = {"original_name": name, "desc": desc.strip()}

for filepath in FILES_TO_READ:
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for match in re.finditer(r'###\s*(?:Tool\s*\d+:?)?\s*([^\n]+)\n(.*?)(?=###|\Z)', content, re.DOTALL | re.IGNORECASE):
        add_idea(match.group(1), match.group(2)[:500])
        
    for match in re.finditer(r'\n\d+\)\s*(?:Tool Name\s*(?:& Description)?:\s*)?([^\n]+)\n(.*?)(?=\n\d+\)|\Z)', content, re.DOTALL | re.IGNORECASE):
        add_idea(match.group(1), match.group(2)[:500])
        
    for match in re.finditer(r'\*\*(?:Tool\s*\d+:?)?\s*([^\*]+)\*\*\n(.*?)(?=\*\*Tool|\Z)', content, re.DOTALL | re.IGNORECASE):
        add_idea(match.group(1), match.group(2)[:500])
        
    for match in re.finditer(r'\n(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:->[^:]+)?:(?:.*?)(?:"""|\'\'\')?(.*?)(?:"""|\'\'\'|\n\n)', content, re.DOTALL):
        func_name = match.group(1)
        desc = match.group(2)
        if len(func_name) > 4 and (func_name.startswith('research_') or '_' in func_name):
            add_idea(func_name, desc[:500])
            
    for match in re.finditer(r'\nclass\s+([A-Za-z0-9_]+)(?:\([^)]*\))?:(?:.*?)(?:"""|\'\'\')?(.*?)(?:"""|\'\'\'|\n\n)', content, re.DOTALL):
        class_name = match.group(1)
        desc = match.group(2)
        if 'Tool' in class_name or class_name.endswith('Detector') or class_name.endswith('Analyzer') or class_name.endswith('Tracker'):
            add_idea(class_name, desc[:500])

results = []
not_implemented = []

for norm_name, data in unique_ideas.items():
    orig_name = data["original_name"]
    desc = data["desc"]
    
    status = "NOT_IMPLEMENTED"
    covered_by = "NONE"
    
    if norm_name in IMPLEMENTED_TOOLS:
        status = "IMPLEMENTED"
        covered_by = norm_name
    elif f"research_{norm_name}" in IMPLEMENTED_TOOLS:
        status = "IMPLEMENTED"
        covered_by = f"research_{norm_name}"
    else:
        for tool in IMPLEMENTED_TOOLS:
            tool_core = tool.replace("research_", "")
            if tool_core in norm_name and len(tool_core) > 5:
                status = "IMPLEMENTED"
                covered_by = tool
                break
                
    results.append(f"IDEA: {orig_name} | STATUS: {status} | COVERED_BY: {covered_by}")
    
    if status == "NOT_IMPLEMENTED":
        clean_desc = re.sub(r'```python.*?```', '', desc, flags=re.DOTALL)
        clean_desc = re.sub(r'def\s+.*', '', clean_desc, flags=re.DOTALL)
        clean_desc = clean_desc.strip()[:400]
        if clean_desc:
            not_implemented.append((orig_name, clean_desc))

with open("/Users/aadel/projects/loom/audit_final_v4.txt", "w", encoding="utf-8") as out:
    for r in sorted(results):
        out.write(r + "\n")
    out.write("\n" + "="*50 + "\n")
    out.write("NOT IMPLEMENTED IDEAS (WITH DESCRIPTIONS):\n")
    for name, desc in sorted(not_implemented, key=lambda x: x[0]):
        out.write(f"--- {name} ---\n{desc}...\n\n")

print(f"Total Unique Ideas: {len(unique_ideas)}")
print(f"Not Implemented: {len(not_implemented)}")
