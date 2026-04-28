import os
import glob
import re
import ast

IMPLEMENTED = {
    "fetch_youtube_transcript", "find_similar_exa", "research_adversarial_robustness", "research_ai_detect", "research_behavioral_fingerprint", "research_bias_lens", "research_bias_probe", "research_botasaurus", "research_botnet_tracker", "research_breach_check", "research_cache_clear", "research_cache_stats", "research_camoufox", "research_career_trajectory", "research_cert_analyze", "research_cipher_mirror", "research_citation_analysis", "research_citation_graph", "research_commit_analyzer", "research_community_sentiment", "research_company_diligence", "research_competitive_intel", "research_compliance_check", "research_conference_arbitrage", "research_config_get", "research_config_set", "research_consensus", "research_convert_document", "research_crypto_trace", "research_curriculum", "research_cve_detail", "research_cve_lookup", "research_dark_forum", "research_dark_market_monitor", "research_darkweb_early_warning", "research_data_fabrication", "research_dead_content", "research_dead_drop_scanner", "research_deception_detect", "research_deception_job_scan", "research_deep", "research_dependency_audit", "research_detect_language", "research_dns_lookup", "research_domain_reputation", "research_email_report", "research_exif_extract", "research_fetch", "research_find_experts", "research_forum_cortex", "research_funding_signal", "research_generate_report", "research_geoip_local", "research_ghost_protocol", "research_ghost_weave", "research_github", "research_github_readme", "research_github_releases", "research_grant_forensics", "research_hallucination_benchmark", "research_health_check", "research_identity_resolve", "research_image_analyze", "research_infra_correlator", "research_institutional_decay", "research_interview_prep", "research_interviewer_profiler", "research_invisible_web", "research_ioc_enrich", "research_ip_geolocation", "research_ip_reputation", "research_job_market", "research_job_search", "research_js_intel", "research_leak_scan", "research_list_notebooks", "research_llm_answer", "research_llm_chat", "research_llm_classify", "research_llm_embed", "research_llm_extract", "research_llm_query_expand", "research_llm_summarize", "research_llm_translate", "research_malware_intel", "research_map_research_to_product", "research_markdown", "research_market_velocity", "research_metadata_forensics", "research_metrics", "research_misinfo_check", "research_model_fingerprint", "research_monoculture_detect", "research_multi_search", "research_multilingual", "research_network_persona", "research_nmap_scan", "research_ocr_extract", "research_onion_discover", "research_onion_spectra", "research_optimize_resume", "research_passive_recon", "research_password_check", "research_patent_landscape", "research_pdf_extract", "research_pdf_search", "research_persona_profile", "research_phishing_mapper", "research_predatory_journal_check", "research_preprint_manipulation", "research_prompt_injection_test", "research_radicalization_detect", "research_ransomware_tracker", "research_realtime_monitor", "research_red_team", "research_registry_graveyard", "research_retraction_check", "research_review_cartel", "research_rss_fetch", "research_rss_search", "research_safety_filter_map", "research_salary_intelligence", "research_salary_synthesize", "research_save_note", "research_screenshot", "research_search", "research_sec_tracker", "research_security_headers", "research_semantic_sitemap", "research_sentiment_deep", "research_session_close", "research_session_list", "research_session_open", "research_shell_funding", "research_slack_notify", "research_social_engineering_score", "research_social_graph", "research_social_profile", "research_social_search", "research_spider", "research_stealth_hire_scanner", "research_stego_detect", "research_stripe_balance", "research_stylometry", "research_subdomain_temporal", "research_supply_chain_risk", "research_temporal_anomaly", "research_temporal_diff", "research_text_analyze", "research_text_to_speech", "research_threat_profile", "research_tor_new_identity", "research_tor_status", "research_transcribe", "research_translate_academic_skills", "research_trend_predict", "research_tts_voices", "research_urlhaus_check", "research_urlhaus_search", "research_usage_report", "research_vastai_search", "research_vastai_status", "research_vercel_status", "research_vuln_intel", "research_wayback", "research_whois", "research_wiki_ghost"
}

FILES_TO_READ = [
    "docs/creative-research/r7_deepseek_chat_dark.txt",
    "docs/creative-research/r7_deepseek_reasoner_dark.txt",
    "docs/creative-research/r7_gemini_dark.txt",
    "docs/creative-research/r7_gpt5_dark.txt",
    "docs/creative-research/r7_o1_dark.txt",
    "docs/creative-research/r7_o3_dark.txt",
    "docs/creative-research/r8_deepseek_censorship.txt",
    "docs/creative-research/r8_deepseek_chat_forced.txt",
    "docs/creative-research/r8_deepseek_reasoner_batch2.txt",
    "docs/creative-research/r8_deepseek_reasoner_forced.txt",
    "docs/creative-research/r8_deepseek_threat_intel.txt",
    "docs/creative-research/r8_o3_infowar.txt",
    "docs/creative-research/r9_deepseek_chat_metacog.txt",
    "docs/creative-research/r9_deepseek_reasoner_codefirst.txt",
    "docs/creative-research/r9_deepseek_reasoner_sld.txt",
    "docs/creative-research/round7_deepseek_chat_dark_production.txt",
    "docs/creative-research/round7_gemini_dark.txt",
    "docs/creative-research/round7_gemini_dark_full.txt",
    "docs/creative-research/round8_deepseek_censorship_research.txt",
    "docs/creative-research/round8_deepseek_reasoner_10tools.txt",
    "docs/creative-research/round8_deepseek_reasoner_batch2.txt",
    "docs/creative-research/round8_deepseek_threat_intel.txt",
    "docs/creative-research/round8_o3_infowar_narrative.txt",
    "docs/creative-research/round9_deepseek_reasoner_codefirst.txt",
    "docs/creative-research/gpt41_creative_jobs.txt",
    "docs/creative-research/gpt41_workarounds.txt",
    "docs/creative-research/gpt4o_loom_ideas.txt",
    "docs/creative-research/gpt4o_unexpected.txt",
    "docs/creative-research/gpt5chat_ideas.txt",
    "docs/creative-research/opus_loom_killers.txt",
    "docs/creative-research/sonnet_loom_killers.txt",
    "docs/creative-research/session_summary.txt",
    "docs/creative-research/code_review_all_42_tools.txt"
]

def to_snake_case(name):
    # E.g., "Geo Content Comparator" -> "geo_content_comparator"
    name = re.sub(r'[^a-zA-Z0-9_]', ' ', name).strip()
    name = re.sub(r'\s+', '_', name).lower()
    if not name.startswith('research_') and name != "":
        name = "research_" + name
    return name

def extract_ideas(content):
    ideas = {}
    
    # 1. Parse markdown lists like: `1. **ToolName**` or `* **ToolName**`
    list_matches = re.finditer(r'^(?:\s*[\d]+\.|\s*\*)\s*\*\*?`?([^:`*]+)`?\*?\*?[\s:]*(.*?(?:\n[ \t]+.*)*)', content, re.MULTILINE)
    for m in list_matches:
        name_raw = m.group(1).strip()
        desc = m.group(2).strip()
        if len(name_raw) < 5 or len(name_raw) > 50: continue # unlikely a tool name
        # Exclude typical non-tool headers
        if any(bad in name_raw.lower() for bad in ["step", "note", "important", "example"]): continue
        name = to_snake_case(name_raw)
        ideas[name] = desc

    # 2. Parse markdown headers: `### ToolName` or `### 1. ToolName`
    header_matches = re.split(r'^###\s+[\d\.]*\s*\*?\*?`?([^:\n*`]+)`?\*?\*?\s*\n', content, flags=re.MULTILINE)
    if len(header_matches) > 1:
        for i in range(1, len(header_matches), 2):
            name_raw = header_matches[i].strip()
            desc = header_matches[i+1].strip()
            if len(name_raw) < 5 or len(name_raw) > 50: continue
            name = to_snake_case(name_raw)
            ideas[name] = desc

    # 3. Parse Python functions: `async def ...(` or `def ...(`
    code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
    for block in code_blocks:
        func_matches = re.finditer(r'(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((?:.*?)\)(?:\s*->.*?)?:\s*(?:"""(.*?)""")?', block, re.DOTALL)
        for m in func_matches:
            name_raw = m.group(1)
            desc = m.group(2) or "No description provided."
            if name_raw.startswith('_'): continue
            if name_raw in ['fetch_url', 'fetch_json', 'compute_hash', 'main']: continue
            name = to_snake_case(name_raw)
            # Use docstring as description
            ideas[name] = desc.strip()
            
    # 4. Find anything explicitly called "Tool 1: ..." or "Idea: ..."
    tool_matches = re.finditer(r'(?:Tool|Idea)\s*\d*:\s*\*?\*?`?([^:\n*`]+)`?\*?\*?[\s-]*\n(.*?)(?=\n\n|\n(?:Tool|Idea))', content, re.DOTALL | re.IGNORECASE)
    for m in tool_matches:
        name_raw = m.group(1).strip()
        desc = m.group(2).strip()
        if len(name_raw) < 5 or len(name_raw) > 50: continue
        name = to_snake_case(name_raw)
        ideas[name] = desc

    return ideas

def main():
    all_ideas = {}
    
    for file in FILES_TO_READ:
        if not os.path.exists(file):
            continue
        with open(file, "r") as f:
            content = f.read()
        
        extracted = extract_ideas(content)
        for name, desc in extracted.items():
            if name not in all_ideas or len(desc) > len(all_ideas[name]):
                all_ideas[name] = desc

    print("--- EXTRACTED IDEAS ---")
    not_implemented = []
    
    # Check against implemented tools
    # Note: implemented tools are exact strings. The ones in all_ideas might have 'research_' prefix added.
    # We should match them strictly if possible, or fuzzily if they represent the same concept.
    
    for name in sorted(all_ideas.keys()):
        # Try direct match
        covered_by = "NONE"
        status = "NOT_IMPLEMENTED"
        
        if name in IMPLEMENTED:
            status = "IMPLEMENTED"
            covered_by = name
        elif name.replace("research_", "") in IMPLEMENTED:
            status = "IMPLEMENTED"
            covered_by = name.replace("research_", "")
        else:
            # Check for partial matches to avoid too many false negatives
            for imp in IMPLEMENTED:
                if name.replace("research_", "") == imp.replace("research_", ""):
                    status = "IMPLEMENTED"
                    covered_by = imp
                    break
        
        # Output exact match line
        print(f"IDEA: {name} | STATUS: {status} | COVERED_BY: {covered_by}")
        
        if status == "NOT_IMPLEMENTED":
            not_implemented.append((name, all_ideas[name]))

    print("\n\n--- NOT_IMPLEMENTED IDEAS ---")
    for name, desc in sorted(not_implemented, key=lambda x: x[0]):
        print(f"--- {name} ---")
        print(desc)
        print()

if __name__ == "__main__":
    main()
