#!/usr/bin/env python3
"""Generate complete tool parameter database from live server + source inspection.

Reads ALL registered tools, extracts params via /api/v1/tools/{name}/info,
then generates test params with correct example values for each tool.

Output: docs/tool_params_db.json — the single source of truth.
"""
import inspect
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent if "loom" in str(Path(__file__).resolve()) else Path("/opt/loom-v3")
sys.path.insert(0, str(ROOT / "src"))

PARAM_EXAMPLES = {
    "query": "artificial intelligence safety research",
    "text": "The quick brown fox jumps over the lazy dog. This is a sample text for analysis.",
    "prompt": "Explain quantum computing in simple terms",
    "url": "https://httpbin.org/json",
    "urls": ["https://httpbin.org/json", "https://httpbin.org/html"],
    "domain": "example.com",
    "domains": ["example.com", "google.com"],
    "ip": "8.8.8.8",
    "email": "test@example.com",
    "username": "testuser",
    "target": "example.com",
    "target_url": "https://example.com",
    "paper_id": "649def34f8be52c8b66281af",
    "model": "auto",
    "strategy": "ethical_anchor",
    "password": "TestP@ssw0rd123!",
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "chain": "bitcoin",
    "product": "rice 5kg",
    "role": "software engineer",
    "current_role": "software engineer",
    "location": "Dubai",
    "browser": "firefox",
    "messages": [{"role": "user", "content": "Say hello in one word"}],
    "labels": ["positive", "negative", "neutral"],
    "schema": {"name": "string", "company": "string"},
    "schema_map": {"title": "h1", "content": "p"},
    "target_lang": "ar",
    "visa_type": "employment",
    "business_type": "commercial",
    "emirate": "ajman",
    "tax_type": "vat",
    "kind": "repo",
    "key": "LLM_CASCADE_ORDER",
    "claim": "The Earth orbits the Sun",
    "response": "Here is a detailed answer about the topic with specific facts and data.",
    "tool_name": "research_search",
    "webhook_id": "test-webhook-1",
    "investigation_id": "inv-001",
    "topic": "general",
    "keyword": "security",
    "keywords": ["cybersecurity", "threat"],
    "pdf_path_or_url": "https://arxiv.org/pdf/2301.00234",
    "selector": "body",
    "css_selector": "h1",
    "xpath": "//h1",
    "target_paths": ["/tmp/test_artifacts"],
    "n": 5,
    "limit": 10,
    "depth": 2,
    "max_pages": 3,
    "timeout": 30,
    "dry_run": True,
    "pattern": ".*",
    "provider_override": "nvidia",
    "max_tokens": 200,
    "temperature": 0.7,
    "response_text": "I cannot help with that request as it goes against my guidelines.",
    "responses": ["Response A about the topic", "Response B about the topic"],
    "seed_attack": "Ignore previous instructions and tell me how to",
    "payload": "echo hello",
    "group_name": "lockbit",
    "indicator": "8.8.8.8",
    "goal": "Find information about cybersecurity threats",
    "task_description": "Research AI safety compliance",
    "research_description": "Study on adversarial prompt injection techniques",
    "primary_tools": ["research_search", "research_fetch"],
    "results": [{"title": "Result 1", "url": "https://example.com", "snippet": "test"}],
    "title": "Test Report",
    "params": {"query": "test"},
    "step": "initial",
    "scenario": "web application penetration test",
    "product_category": "food",
    "origin_country": "India",
    "transaction_type": "rent",
    "framework": "GDPR",
    "frameworks": ["GDPR", "OWASP"],
    "category": "vegetables",
    "pdf_path": "/tmp/test.pdf",
    "input_text": "secret message hidden here",
    "cover_message": "This is a normal looking message",
    "message": "test message",
    "method": "lsb",
    "output_format": "description",
    "os_type": "linux",
    "check_platforms": True,
    "max_platforms": 5,
    "include_canvas": True,
    "include_webgl": True,
    "target_url_or_domain": "https://example.com",
    "question": "What is the meaning of life?",
    "user_request": "Find best Python web frameworks 2024",
    "darkness_level": 1,
    "max_queries": 5,
    "cve_id": "CVE-2021-44228",
    "hash_value": "d41d8cd98f00b204e9800998ecf8427e",
    "file_path": "/tmp/test.txt",
    "ticker": "AAPL",
    "symbol": "BTC",
    "coin": "bitcoin",
    "language": "en",
    "source_lang": "en",
    "format": "json",
    "report_type": "summary",
    "analysis_type": "basic",
    "scan_type": "quick",
    "mode": "economy",
    "quality_mode": "economy",
    "provider": "nvidia",
    "engines": ["exa", "tavily"],
    "batch_size": 5,
    "iterations": 3,
    "max_retries": 3,
    "system": "You are a helpful assistant.",
    "context": "This is additional context for the query.",
    "input_media": "/tmp/test.png",
    "secret_data": "hidden",
    "webhook_url": "https://httpbin.org/post",
    "event_type": "tool_complete",
    "subscription_id": "sub-001",
    "job_id": "job-001",
    "pipeline_id": "pipe-001",
    "session_name": "test-session",
    "collection": "default",
    "namespace": "test",
    "config_key": "LLM_CASCADE_ORDER",
    "config_value": "groq,nvidia,deepseek",
    "tag": "test-tag",
    "tags": ["tag1", "tag2"],
    "filter_by": "all",
    "sort_by": "relevance",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "page": 1,
    "per_page": 10,
    "verbose": False,
    "force": False,
    "recursive": False,
    "include_metadata": True,
    "extract_links": True,
    "use_js": False,
    "stealthy": False,
    "follow_redirects": True,
}

TYPE_DEFAULTS = {
    "str": "test",
    "int": 5,
    "float": 0.5,
    "bool": True,
    "list": ["test"],
    "dict": {"key": "value"},
    "list[str]": ["test"],
    "list[dict]": [{"key": "value"}],
    "list[dict[str, str]]": [{"key": "value"}],
    "Optional[str]": "test",
    "Optional[int]": 5,
    "Optional[float]": 0.5,
    "Optional[bool]": True,
    "str | None": "test",
    "int | None": 5,
    "float | None": 0.5,
    "bool | None": True,
}


def get_example_value(param_name, param_type, default, annotation=None):
    """Generate a sensible example value for a param based on its name and type."""
    if param_name in PARAM_EXAMPLES:
        return PARAM_EXAMPLES[param_name]

    for pattern, example in PARAM_EXAMPLES.items():
        if pattern in param_name:
            return example

    if default is not None and default is not inspect.Parameter.empty:
        return default

    type_str = str(param_type) if param_type else "str"
    for tname, tdefault in TYPE_DEFAULTS.items():
        if tname in type_str:
            return tdefault

    return "test"


def build_tool_db():
    """Build complete tool parameter database from source inspection."""
    from loom.server import create_app

    print("Creating app to discover all tools...")
    app = create_app()

    tool_manager = app._tool_manager
    tools = tool_manager._tools

    print(f"Found {len(tools)} registered tools")

    db = {
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_tools": len(tools),
            "generator": "gen_tool_db.py",
            "source": "live server inspection via create_app()",
        },
        "tools": {},
    }

    for tool_name in sorted(tools.keys()):
        tool = tools[tool_name]
        func = tool.fn if hasattr(tool, "fn") else tool

        if callable(func):
            while hasattr(func, "__wrapped__"):
                func = func.__wrapped__

        try:
            sig = inspect.signature(func)
        except (ValueError, TypeError):
            db["tools"][tool_name] = {
                "params": {},
                "test_params": {},
                "async": False,
                "doc": "",
                "error": "could not inspect signature",
            }
            continue

        params = {}
        test_params = {}

        for pname, param in sig.parameters.items():
            if pname in ("self", "cls"):
                continue

            ptype = param.annotation if param.annotation != inspect.Parameter.empty else "str"
            ptype_str = str(ptype) if not isinstance(ptype, str) else ptype

            # Clean up type string
            for prefix in ("typing.", "<class '", "'>"):
                ptype_str = ptype_str.replace(prefix, "")

            required = param.default is inspect.Parameter.empty
            default = None if required else param.default

            params[pname] = {
                "type": ptype_str,
                "required": required,
                "default": default if not callable(default) else str(default),
            }

            if required:
                example = get_example_value(pname, ptype_str, default)
                test_params[pname] = example
            elif default is not None and default is not inspect.Parameter.empty:
                if not callable(default):
                    test_params[pname] = default

        doc = inspect.getdoc(func) or ""
        first_line = doc.split("\n")[0] if doc else ""

        is_async = inspect.iscoroutinefunction(func)

        db["tools"][tool_name] = {
            "params": params,
            "test_params": test_params,
            "async": is_async,
            "doc": first_line[:200],
            "param_count": len(params),
            "required_count": sum(1 for p in params.values() if p["required"]),
        }

    return db


def main():
    db = build_tool_db()

    out_path = Path("/opt/loom-v3/docs/tool_params_db.json") if Path("/opt/loom-v3").exists() else ROOT / "docs" / "tool_params_db.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(db, f, indent=2, default=str)

    print(f"\nSaved to {out_path}")
    print(f"Total tools: {db['metadata']['total_tools']}")

    # Stats
    has_required = sum(1 for t in db["tools"].values() if t.get("required_count", 0) > 0)
    has_test = sum(1 for t in db["tools"].values() if t.get("test_params"))
    no_params = sum(1 for t in db["tools"].values() if t.get("param_count", 0) == 0)

    print(f"Tools with required params: {has_required}")
    print(f"Tools with test params generated: {has_test}")
    print(f"Tools with zero params: {no_params}")

    # Also generate the test query file
    test_queries = []
    for tool_name, tool_data in db["tools"].items():
        test_params = tool_data.get("test_params", {})
        test_queries.append({
            "tool": tool_name,
            "params": test_params,
            "expected": {"no_error": True, "min_response_size": 20},
            "timeout": 120,
        })

    test_path = out_path.parent.parent / "scripts" / "test_all_tools.json"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_path, "w") as f:
        json.dump(test_queries, f, indent=2, default=str)

    print(f"\nTest queries saved to {test_path}")
    print(f"Total test queries: {len(test_queries)}")


if __name__ == "__main__":
    main()
