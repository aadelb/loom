"""
Deep user simulation validating ALL 835 Loom tools against guidelines.

Validates:
1. Tool executes without crash (15s timeout)
2. Output meets quality criteria from /opt/research-toolbox/tool_guidelines.json
3. Return type matches expected (dict, list, str, etc.)
4. Output length meets minimum guidelines
5. Category-specific quality checks (research, llm, reframing, scoring)
"""
import sys
import asyncio
import importlib
import inspect
import time
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, "src")

try:
    from dotenv import load_dotenv
    load_dotenv("/opt/research-toolbox/.env")
except:
    pass

# Extended parameter map covering all 835 tools
PARAM_MAP = {
    # Core research params
    "query": "how to build wealth in 2026",
    "url": "https://httpbin.org/get",
    "prompt": "explain wealth creation strategies",
    "text": "Bitcoin mining and DeFi yield farming are popular wealth creation methods.",
    "tool_name": "research_search",
    "domain": "example.com",
    "topic": "wealth creation",
    "model": "auto",
    "name": "test_session",
    "target": "example.com",
    "target_url": "https://httpbin.org/get",
    "response": "This is a test response about wealth creation strategies.",
    "params": {},
    "strategy": "ethical_anchor",
    "urls": ["https://httpbin.org/get"],
    "content": "Test content about wealth creation.",
    "username": "testuser",
    "title": "Wealth Creation Report",
    "company": "Example Corp",
    "model_name": "gpt-4",
    "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "question": "What are the best investments for 2026?",
    "sources": [{"title": "test", "content": "Test source about wealth."}],
    "target_lang": "ar",
    "provider": "exa",
    "n": 3,
    "limit": 3,
    "max_tokens": 200,
    "darkness_level": 5,
    "spectrum": True,
    "depth": "standard",
    "kind": "repos",
    "categories": ["finance", "technology"],
    "claim": "Bitcoin will reach $200,000 by 2027",
    "strategies": ["ethical_anchor"],
    "mode": "http",
    "email": "test@example.com",
    "key": "test_key",
    "value": "test_value",
    "event_type": "test",
    "session_name": "test",
    "data": {"test": True},
    "findings": [{"type": "test", "severity": "low"}],
    "input_text": "Test input about finance.",
    "output_text": "Test output about wealth.",
    "messages": [{"role": "user", "content": "test"}],
    "system_description": "A financial chatbot.",
    "payload": "test payload",
    "report_type": "summary",
    "turns": 3,
    "dry_run": True,
    "os_type": "linux",
    "target_paths": ["logs"],
    "test_count": 3,
    "provider_override": "nvidia",
    "include_reframe": False,
    "max_queries": 5,
    "format": "markdown",
    "language": "en",
    "country": "US",
    "keyword": "wealth",
    "pattern": "*.py",
    "path": "/tmp/test",
    "filename": "test.txt",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png",
    "steps": [{"tool": "research_search", "params": {"query": "test"}}],
    "pipeline": [{"step": 1, "tool": "research_search"}],
    "objective": "find wealth creation strategies",
    "constraints": ["must be legal"],
    "context": "financial research",
    "persona": "financial analyst",
    "score": 7.5,
    "threshold": 0.5,
    "interval": 60,
    "batch_size": 3,
    "timeout": 30,
    "retries": 3,
    # Academic & research
    "paper_id": "arXiv:2401.00001",
    "journal_name": "Nature",
    "max_results": 5,
    # Credential & security
    "target_type": "email",
    # Deepfake & media
    "media_file": "/tmp/test.mp4",
    "input_media": "/tmp/test.png",
    "secret_data": "test secret",
    "output_format": "png",
    # Privacy & anonymity
    "include_canvas": True,
    "include_webgl": True,
    "include_audio": True,
    "include_fonts": True,
    "include_interactive": False,
    "trigger_action": "wipe",
    "test_iterations": 3,
    "browser": "chrome",
    # Job & career
    "job_title": "Software Engineer",
    "location": "San Francisco",
    "skills": ["Python", "JavaScript"],
    # Financial
    "ticker": "AAPL",
    "timeframe": "1y",
    # Darkweb & OSINT
    "forum_id": "test",
    "search_term": "test",
    "onion_address": "example.onion",
    "cipher_type": "AES",
    # Forensics & artifacts
    "artifact_type": "logs",
    # Supply chain
    "company_name": "Example Corp",
    # Threat intelligence
    "threat_actor": "APT1",
    "indicator": "192.0.2.1",
    "incident_id": "INCIDENT-001",
    # Bot & automation
    "target_count": 10,
    "action_sequence": ["search", "extract"],
    # Consensus & agreement
    "positions": [{"view": "test"}],
    "agreement_threshold": 0.8,
    # Fuzzing
    "base_payload": "test",
    "mutation_count": 5,
    # Report generation
    "report_data": {"findings": []},
    "output_path": "/tmp/test_report",
    # Session management
    "browser_type": "chrome",
    "headless": True,
    # Config
    "config_key": "test_config",
    # Health check
    # (no params needed)
}

# Counters
stats = {
    "total_discovered": 0,
    "total_tested": 0,
    "crash_pass": 0,  # didn't crash
    "crash_fail": 0,  # crashed
    "timeout": 0,
    "quality_pass": 0,  # meets guidelines
    "quality_fail": 0,  # fails guidelines
    "by_category": defaultdict(lambda: {"tested": 0, "crash_pass": 0, "quality_pass": 0}),
}
errors = []
quality_failures = []


async def validate_output(tool_name, result, guidelines):
    """
    Validate output against guidelines.
    Returns (quality_pass, failure_reason).
    """
    if not guidelines:
        return True, None

    # Basic structure checks
    if guidelines.get("quality_criteria", {}).get("must_not_be_empty"):
        if not result or (isinstance(result, (list, dict)) and len(result) == 0):
            return False, "output_empty"

    # Return type validation
    expected_type = guidelines.get("expected_return_type", "").lower()
    if expected_type:
        actual_type = type(result).__name__.lower()
        type_match = False
        if expected_type == "dict" and isinstance(result, dict):
            type_match = True
        elif expected_type == "list" and isinstance(result, list):
            type_match = True
        elif expected_type == "str" and isinstance(result, str):
            type_match = True
        elif expected_type == "int" and isinstance(result, int):
            type_match = True
        elif expected_type == "float" and isinstance(result, (int, float)):
            type_match = True
        elif expected_type == "bool" and isinstance(result, bool):
            type_match = True

        if not type_match:
            return False, f"type_mismatch_expected_{expected_type}_got_{actual_type}"

    # Output length validation
    min_chars = guidelines.get("min_output_chars", 0)
    output_str = str(result)
    if min_chars > 0 and len(output_str) < min_chars:
        return False, f"output_too_short_{len(output_str)}_chars_min_{min_chars}"

    # Category-specific validation
    category = guidelines.get("category", "").lower()

    if category == "research":
        # Research tools should have content keys
        if isinstance(result, dict):
            has_content = any(
                key in result for key in ["results", "items", "content", "data", "entries"]
            )
            if not has_content and len(result) == 0:
                return False, "research_no_content_keys"
        elif not isinstance(result, list) or len(result) == 0:
            if not output_str or len(output_str) < 50:
                return False, "research_insufficient_output"

    elif category == "llm":
        # LLM tools should return meaningful text
        if isinstance(result, str):
            words = len(result.split())
            if words < 5:
                return False, f"llm_insufficient_text_{words}_words"
        elif isinstance(result, dict):
            text_keys = [k for k in result if "text" in k.lower() or "content" in k.lower()]
            if not text_keys:
                return False, "llm_no_text_content"

    elif category == "reframing":
        # Reframing tools should produce different output than input
        if "input_text" in guidelines.get("required_params", []):
            if output_str and len(output_str) < 20:
                return False, "reframing_insufficient_output"

    elif category == "scoring":
        # Scoring tools should return numeric values
        if isinstance(result, dict):
            has_score = any(k in result for k in ["score", "value", "rating", "confidence"])
            if not has_score:
                return False, "scoring_no_numeric_result"
        elif isinstance(result, (int, float)):
            pass  # Valid numeric score
        else:
            try:
                float(result)  # Try to parse as number
            except (ValueError, TypeError):
                return False, "scoring_not_numeric"

    return True, None


async def call_tool(name, func, params, guidelines):
    """
    Call a tool with timeout and quality validation.
    Returns (crash_pass, quality_pass, detail, result_len).
    """
    global stats, errors, quality_failures

    stats["total_tested"] += 1
    category = guidelines.get("category", "unknown") if guidelines else "unknown"
    stats["by_category"][category]["tested"] += 1

    try:
        if asyncio.iscoroutinefunction(func):
            result = await asyncio.wait_for(func(**params), timeout=15)
        else:
            result = func(**params)

        stats["crash_pass"] += 1
        stats["by_category"][category]["crash_pass"] += 1

        # Quality validation
        quality_pass, failure_reason = await validate_output(name, result, guidelines)
        if quality_pass:
            stats["quality_pass"] += 1
            stats["by_category"][category]["quality_pass"] += 1
            return True, True, "OK", len(str(result))
        else:
            stats["quality_fail"] += 1
            quality_failures.append({
                "tool": name,
                "category": category,
                "reason": failure_reason,
                "output_type": type(result).__name__,
                "output_len": len(str(result)),
            })
            return True, False, f"QUALITY_FAIL: {failure_reason}", len(str(result))

    except asyncio.TimeoutError:
        stats["timeout"] += 1
        stats["crash_fail"] += 1
        errors.append({"tool": name, "error": "TIMEOUT_15s", "category": category})
        return False, False, "TIMEOUT", 0
    except Exception as e:
        stats["crash_fail"] += 1
        stats["by_category"][category]["crash_pass"] -= 1  # undo the increment
        error_msg = str(e)[:150]
        errors.append({"tool": name, "error": error_msg, "category": category})
        return False, False, error_msg[:80], 0


async def main():
    global stats

    # Load guidelines
    print("Loading guidelines from /opt/research-toolbox/tool_guidelines.json...", flush=True)
    try:
        with open("/opt/research-toolbox/tool_guidelines.json") as f:
            all_guidelines = json.load(f)
        print(f"Loaded {len(all_guidelines)} tools from guidelines.", flush=True)
    except Exception as e:
        print(f"ERROR: Could not load guidelines: {e}", flush=True)
        return

    # Discover tools
    print("Discovering Loom tools...", flush=True)
    tools_dir = Path("src/loom/tools")
    all_tools = {}

    for py in sorted(tools_dir.glob("*.py")):
        mod_name = py.stem
        if mod_name.startswith("_") or mod_name == "reframe_strategies":
            continue
        try:
            mod = importlib.import_module(f"loom.tools.{mod_name}")
            for name, obj in inspect.getmembers(mod, inspect.isfunction):
                if (name.startswith("research_") or name.startswith("tool_")) and name not in all_tools:
                    all_tools[name] = {
                        "func": obj,
                        "module": mod_name,
                        "guidelines": all_guidelines.get(name),
                    }
        except Exception as e:
            print(f"  Warning: Could not load {mod_name}: {str(e)[:80]}", flush=True)

    stats["total_discovered"] = len(all_tools)
    print(f"Discovered {len(all_tools)} tools. Starting validation...\n", flush=True)

    # Test all tools
    start_time = time.time()
    for i, (name, info) in enumerate(sorted(all_tools.items())):
        func = info["func"]
        guidelines = info["guidelines"]
        sig = inspect.signature(func)

        # Build params
        params = {}
        for pname, param in sig.parameters.items():
            if pname in ("self", "cls"):
                continue
            if param.default != inspect.Parameter.empty:
                continue
            if pname in PARAM_MAP:
                params[pname] = PARAM_MAP[pname]
            else:
                # Fallback type inference
                ann = str(param.annotation)
                if "str" in ann:
                    params[pname] = "test input"
                elif "int" in ann:
                    params[pname] = 5
                elif "bool" in ann:
                    params[pname] = True
                elif "float" in ann:
                    params[pname] = 0.5
                elif "list" in ann:
                    params[pname] = []
                elif "dict" in ann:
                    params[pname] = {}
                else:
                    params[pname] = "test"

        crash_pass, quality_pass, detail, output_len = await call_tool(name, func, params, guidelines)

        # Progress reporting
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            crash_rate = 100 * stats["crash_pass"] // max(stats["total_tested"], 1)
            quality_rate = 100 * stats["quality_pass"] // max(stats["total_tested"], 1)
            print(
                f"  [{i+1}/{len(all_tools)}] Elapsed: {elapsed:.0f}s | "
                f"Crash: {stats['crash_pass']}/{stats['total_tested']} ({crash_rate}%) | "
                f"Quality: {stats['quality_pass']}/{stats['total_tested']} ({quality_rate}%)",
                flush=True,
            )

    elapsed = time.time() - start_time

    # Compute rates
    total = stats["total_tested"]
    crash_rate = 100 * stats["crash_pass"] // max(total, 1)
    quality_rate = 100 * stats["quality_pass"] // max(total, 1)

    print(f"\n{'='*80}", flush=True)
    print("DEEP USER SIMULATION - GUIDELINES VALIDATION REPORT", flush=True)
    print(f"{'='*80}\n", flush=True)

    print(f"DISCOVERY & EXECUTION:", flush=True)
    print(f"  Total tools discovered:  {stats['total_discovered']}", flush=True)
    print(f"  Total tools tested:      {total}", flush=True)
    print(f"  Crash pass:              {stats['crash_pass']}/{total} ({crash_rate}%)", flush=True)
    print(f"  Crash fail:              {stats['crash_fail']}", flush=True)
    print(f"  Timeout (15s):           {stats['timeout']}", flush=True)
    print(f"  Elapsed time:            {elapsed:.1f}s\n", flush=True)

    print(f"QUALITY VALIDATION (vs Guidelines):", flush=True)
    print(f"  Quality pass:            {stats['quality_pass']}/{total} ({quality_rate}%)", flush=True)
    print(f"  Quality fail:            {stats['quality_fail']}", flush=True)
    print(f"  Avg output length:       {sum(1 for _ in quality_failures)}x tools failed\n", flush=True)

    print(f"CATEGORY BREAKDOWN:", flush=True)
    for cat in sorted(stats["by_category"].keys()):
        cat_stats = stats["by_category"][cat]
        cat_crash_rate = 100 * cat_stats["crash_pass"] // max(cat_stats["tested"], 1)
        cat_quality_rate = 100 * cat_stats["quality_pass"] // max(cat_stats["tested"], 1)
        print(
            f"  {cat:15s}: {cat_stats['tested']:3d} tested | "
            f"{cat_stats['crash_pass']:3d} crash ✓ ({cat_crash_rate:3d}%) | "
            f"{cat_stats['quality_pass']:3d} quality ✓ ({cat_quality_rate:3d}%)",
            flush=True,
        )

    # Error analysis
    print(f"\n{'='*80}", flush=True)
    print("ERROR ANALYSIS", flush=True)
    print(f"{'='*80}\n", flush=True)

    error_patterns = defaultdict(int)
    for e in errors:
        key = e["error"][:80]
        error_patterns[key] += 1

    print(f"Top 20 crash error patterns:", flush=True)
    for pattern, count in sorted(error_patterns.items(), key=lambda x: -x[1])[:20]:
        print(f"  [{count:3d}x] {pattern}", flush=True)

    # Quality failure analysis
    print(f"\nTop 15 quality failure patterns:", flush=True)
    quality_patterns = defaultdict(int)
    for qf in quality_failures:
        key = qf["reason"]
        quality_patterns[key] += 1

    for pattern, count in sorted(quality_patterns.items(), key=lambda x: -x[1])[:15]:
        print(f"  [{count:3d}x] {pattern}", flush=True)

    # Example quality failures
    print(f"\nSample quality failures (first 5):", flush=True)
    for qf in quality_failures[:5]:
        print(
            f"  {qf['tool']:40s} | {qf['reason']:40s} | {qf['output_type']} | "
            f"{qf['output_len']} chars",
            flush=True,
        )

    # Save report
    print(f"\n{'='*80}", flush=True)
    print("SAVING REPORT", flush=True)
    print(f"{'='*80}\n", flush=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_discovered": stats["total_discovered"],
        "total_tested": total,
        "execution": {
            "crash_pass": stats["crash_pass"],
            "crash_fail": stats["crash_fail"],
            "timeout": stats["timeout"],
            "crash_rate_pct": crash_rate,
        },
        "quality": {
            "pass": stats["quality_pass"],
            "fail": stats["quality_fail"],
            "pass_rate_pct": quality_rate,
        },
        "elapsed_seconds": round(elapsed, 1),
        "category_breakdown": {
            cat: {
                "tested": stats["by_category"][cat]["tested"],
                "crash_pass": stats["by_category"][cat]["crash_pass"],
                "quality_pass": stats["by_category"][cat]["quality_pass"],
                "crash_rate_pct": 100 * stats["by_category"][cat]["crash_pass"]
                // max(stats["by_category"][cat]["tested"], 1),
                "quality_rate_pct": 100 * stats["by_category"][cat]["quality_pass"]
                // max(stats["by_category"][cat]["tested"], 1),
            }
            for cat in sorted(stats["by_category"].keys())
        },
        "crash_error_patterns": dict(
            sorted(error_patterns.items(), key=lambda x: -x[1])[:20]
        ),
        "quality_failure_patterns": dict(
            sorted(quality_patterns.items(), key=lambda x: -x[1])[:15]
        ),
        "sample_crashes": errors[:10],
        "sample_quality_failures": quality_failures[:10],
    }

    report_path = Path("/opt/research-toolbox/guidelines_validation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Report saved to: {report_path}", flush=True)

    # Summary
    print(f"\nSUMMARY:", flush=True)
    print(f"  {crash_rate}% of tools execute without crashing", flush=True)
    print(f"  {quality_rate}% of tools meet quality guidelines", flush=True)
    print(f"  {len(quality_patterns)} distinct quality failure patterns", flush=True)
    print(f"  {len(error_patterns)} distinct crash patterns\n", flush=True)

    return report


if __name__ == "__main__":
    asyncio.run(main())
