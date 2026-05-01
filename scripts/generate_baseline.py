#!/usr/bin/env python3
"""Generate expected outcome baseline for all Loom MCP tools."""
import sys
import json
import logging
from collections import Counter

logging.disable(logging.CRITICAL)
sys.path.insert(0, "src")

from loom.server import create_app

app = create_app()
tools = app._tool_manager._tools

baseline = {}
for name, tool in tools.items():
    schema = {}
    if hasattr(tool, "parameters"):
        schema = tool.parameters
    elif hasattr(tool, "inputSchema"):
        schema = tool.inputSchema

    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = schema.get("required", []) if isinstance(schema, dict) else []

    n = name.lower()
    if any(x in n for x in ["llm_summarize", "llm_extract", "llm_classify", "llm_translate", "llm_expand", "llm_answer", "llm_embed", "llm_chat"]):
        cat = "llm_core"
    elif "ask_all" in n or "multi_llm" in n or "model_comparator" in n:
        cat = "llm_multi"
    elif "reframe" in n or "strategy" in n:
        cat = "creative_reframe"
    elif any(x in n for x in ["fetch", "spider", "markdown", "nodriver", "zen", "crawl", "camoufox", "botasaurus"]):
        cat = "scraping"
    elif any(x in n for x in ["multi_search"]):
        cat = "search_multi"
    elif "search" in n:
        cat = "search"
    elif "deep" in n and "dark" not in n:
        cat = "deep_research"
    elif any(x in n for x in ["crypto", "blockchain", "wallet", "defi"]):
        cat = "crypto"
    elif any(x in n for x in ["dark", "onion", "tor", "forum_cortex", "ghost", "dead_drop"]):
        cat = "darkweb"
    elif any(x in n for x in ["career", "job", "resume", "salary", "interview", "funding"]):
        cat = "career"
    elif any(x in n for x in ["academic", "citation", "retraction", "predatory", "grant", "paper"]):
        cat = "academic"
    elif any(x in n for x in ["social", "profile", "telegram", "linkedin", "discord", "instagram"]):
        cat = "social"
    elif any(x in n for x in ["threat", "phishing", "cve", "vuln", "breach", "urlhaus", "misp", "yara"]):
        cat = "threat_intel"
    elif any(x in n for x in ["domain", "dns", "cert", "ip_", "whois", "subdomain", "security_header"]):
        cat = "infrastructure"
    elif any(x in n for x in ["session", "config", "health", "cache", "audit"]):
        cat = "system"
    elif any(x in n for x in ["ocr", "pdf", "document", "transcribe", "unstructured", "camelot"]):
        cat = "document"
    elif any(x in n for x in ["rss", "monitor", "change_monitor", "early_warning"]):
        cat = "monitoring"
    elif any(x in n for x in ["knowledge_graph", "fact_check", "trend", "report_gen"]):
        cat = "revolutionary"
    elif any(x in n for x in ["pentest", "agent"]):
        cat = "pentest"
    elif any(x in n for x in ["hcs", "score", "quality"]):
        cat = "scoring"
    elif "build_query" in n:
        cat = "query_builder"
    else:
        cat = "research_general"

    baseline[name] = {
        "category": cat,
        "required_params": required,
        "param_count": len(props),
        "validation": {
            "returns_dict": True,
            "min_response_bytes": 20,
            "must_not_crash": True,
        },
    }

cats = Counter(b["category"] for b in baseline.values())
print("=== EXPECTED BASELINE (GRANULAR) ===")
print(f"Total tools: {len(baseline)}\n")
for cat, count in cats.most_common():
    print(f"  {cat:25s}: {count}")

with open("tmp/expected_baseline_v2.json", "w") as f:
    json.dump(baseline, f, indent=2)
print("\nSaved to tmp/expected_baseline_v2.json")
