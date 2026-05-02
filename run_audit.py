import os
import ast
import glob
import re
import json

def check_file(path):
    if not os.path.exists(path):
        return {"exists": False}
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.splitlines()
    num_lines = len(lines)
    head_3 = lines[:3]
    async_def_count = content.count('async def ')
    return {
        "exists": True,
        "num_lines": num_lines,
        "head_3": head_3,
        "async_def_count": async_def_count,
        "content": content
    }

report = {"cat1": {}, "cat2": {}, "cat3": {}, "cat4": {}}

# Cat 1
cat1_files = {
    "full_pipeline.py": ["research_full_pipeline"],
    "hcs_escalation.py": ["research_hcs_escalate"],
    "response_synthesizer.py": ["research_synthesize_report"],
    "strategy_feedback.py": ["research_strategy_log", "research_strategy_recommend", "research_strategy_stats"],
    "model_consensus.py": [],
    "strategy_cache.py": ["sqlite3", "dict"],
    "realtime_adapt.py": ["refusal"],
    "output_formatter.py": ["json", "markdown"]
}
for f, keys in cat1_files.items():
    path = f"src/loom/tools/{f}"
    res = check_file(path)
    res['keys_found'] = {k: k.lower() in res.get('content', '').lower() for k in keys} if res['exists'] else {}
    if res['exists']:
        del res['content']
    report["cat1"][f] = res

# Cat 2
cat2_files = {
    "universal_orchestrator.py": ["ast.parse", "glob", "importlib"],
    "smart_router.py": ["glob", "ast", "_INTENTS"],
    "auto_params.py": ["importlib", "inspect"],
    "semantic_index.py": ["tf-idf", "tfidf"],
    "nl_executor.py": ["research_do"],
    "parallel_executor.py": ["asyncio.gather"],
    "live_registry.py": ["importlib", "scan", "module"],
    "capability_matrix.py": ["input", "output"],
    "auto_pipeline.py": ["decompose", "step"],
    "composition_optimizer.py": ["TOOL_METADATA", "ast", "importlib"],
    "tool_recommender_v2.py": ["CO_OCCURRENCE_MAP"],
    "workflow_expander.py": ["workflow"]
}
for f, keys in cat2_files.items():
    path = f"src/loom/tools/{f}"
    res = check_file(path)
    res['keys_found'] = {k: k.lower() in res.get('content', '').lower() for k in keys} if res['exists'] else {}
    if f == "tool_recommender_v2.py" and res['exists']:
        res['co_occurrence_count'] = len(re.findall(r'["\']?\w+["\']?\s*:\s*\{', res.get('content', '')))
    if res['exists']:
        del res['content']
    report["cat2"][f] = res

# Cat 3
cat3_files = {
    "error_wrapper.py": ["safe_tool_call"],
    "key_rotation.py": ["os.environ"],
    "json_logger.py": ["jsonl"],
    "startup_validator.py": ["import"],
    "backoff_dlq.py": ["aiosqlite", "backoff"],
    "telemetry.py": ["percentile"],
    "mcp_auth.py": ["sha256", "hashlib"],
    "audit_log.py": ["jsonl"],
    "deployment.py": ["systemctl"],
    "memory_mgmt.py": ["psutil", "rss"],
    "dist_tracing.py": ["trace", "span"],
    "backup_system.py": ["backup"]
}
for f, keys in cat3_files.items():
    path = f"src/loom/tools/{f}"
    res = check_file(path)
    res['keys_found'] = {k: k.lower() in res.get('content', '').lower() for k in keys} if res['exists'] else {}
    if res['exists']:
        del res['content']
    report["cat3"][f] = res

# Cat 4
server_path = "src/loom/server.py"
server_exists = os.path.exists(server_path)
if server_exists:
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    mcp_tool_count = content.count('@mcp.tool') + content.count('mcp.tool()')
    try:
        ast.parse(content)
        syntax_ok = True
    except Exception as e:
        syntax_ok = str(e)
else:
    mcp_tool_count = 0
    syntax_ok = False

tools_files = glob.glob("src/loom/tools/*.py")
report["cat4"] = {
    "server_exists": server_exists,
    "mcp_tool_count": mcp_tool_count,
    "syntax_ok": syntax_ok,
    "tools_py_count": len(tools_files)
}

print(json.dumps(report, indent=2))
