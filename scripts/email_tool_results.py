#!/usr/bin/env python3
"""Run top tools on Hetzner and email results."""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

# Load environment variables from resources.env if available
resources_env = os.path.expanduser("~/.claude/resources.env")
if os.path.exists(resources_env):
    with open(resources_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip('"').strip("'")
                os.environ[key] = value

# Add project to path - try Hetzner location first, then local
hetzner_path = "/opt/research-toolbox/src"
local_path = "/Users/aadel/projects/loom/src"

if os.path.exists(hetzner_path):
    sys.path.insert(0, hetzner_path)
    loom_root = "/opt/research-toolbox"
elif os.path.exists(local_path):
    sys.path.insert(0, local_path)
    loom_root = "/Users/aadel/projects/loom"
else:
    print("ERROR: Could not find loom installation")
    sys.exit(1)


async def run_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Run a single tool and return result."""
    try:
        # Map tool names to modules and functions
        tool_map = {
            "research_cache_stats": ("loom.tools.cache_mgmt", "research_cache_stats"),
            "research_circuit_status": ("loom.tools.llm", "research_circuit_status"),
            "research_quota_status": ("loom.tools.quota_status", "research_quota_status"),
            "research_registry_status": ("loom.tools.live_registry", "research_registry_status"),
            "research_breaker_status": ("loom.tools.circuit_breaker", "research_breaker_status"),
            "research_memory_status": ("loom.tools.memory_mgmt", "research_memory_status"),
            "research_ratelimit_status": ("loom.tools.rate_limiter_tool", "research_ratelimit_status"),
            "research_queue_status": ("loom.tools.request_queue", "research_queue_status"),
            "research_scheduler_status": ("loom.tools.scheduler_status", "research_scheduler_status"),
            "research_key_status": ("loom.tools.key_rotation", "research_key_status"),
            "research_deploy_status": ("loom.tools.deployment", "research_deploy_status"),
            "research_log_stats": ("loom.tools.json_logger", "research_log_stats"),
            "research_tor_status": ("loom.tools.tor", "research_tor_status"),
        }

        if tool_name not in tool_map:
            return {
                "tool": tool_name,
                "status": "not_found",
                "ms": 0,
                "error": "Tool not in map",
            }

        module_name, func_name = tool_map[tool_name]

        # Dynamically import and call
        module = __import__(module_name, fromlist=[func_name])
        if not hasattr(module, func_name):
            return {
                "tool": tool_name,
                "status": "not_found",
                "ms": 0,
                "error": f"Function {func_name} not found in {module_name}",
            }

        func = getattr(module, func_name)
        start = time.time()

        # Call function (may be async or sync)
        if asyncio.iscoroutinefunction(func):
            # For tools requiring parameters
            if params:
                result = await func(**params)
            else:
                result = await func()
        else:
            if params:
                result = func(**params)
            else:
                result = func()

        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "tool": tool_name,
            "status": "ok",
            "ms": elapsed_ms,
            "result_type": type(result).__name__,
        }

    except ImportError as e:
        return {
            "tool": tool_name,
            "status": "import_error",
            "ms": 0,
            "error": str(e),
        }
    except TypeError as e:
        # Handle parameter mismatch
        return {
            "tool": tool_name,
            "status": "param_error",
            "ms": 0,
            "error": str(e),
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "tool": tool_name,
            "status": "error",
            "ms": elapsed_ms,
            "error": str(e),
        }


async def main() -> None:
    """Main entry point."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Starting Loom tool results collection...")

    # Define tools to test
    tools_to_test = [
        ("research_cache_stats", {}),
        ("research_circuit_status", {}),
        ("research_quota_status", {}),
        ("research_registry_status", {}),
        ("research_breaker_status", {}),
        ("research_memory_status", {}),
        ("research_ratelimit_status", {}),
        ("research_queue_status", {}),
        ("research_scheduler_status", {}),
        ("research_key_status", {}),
        ("research_deploy_status", {}),
        ("research_log_stats", {}),
        ("research_tor_status", {}),
    ]

    # Run all tools in parallel
    results = []
    tasks = [run_tool(name, params) for name, params in tools_to_test]
    results = await asyncio.gather(*tasks)

    # Format report
    total = len(results)
    ok_count = sum(1 for r in results if r["status"] == "ok")
    error_count = sum(1 for r in results if r["status"] in ["error", "import_error", "param_error"])
    not_found = sum(1 for r in results if r["status"] == "not_found")

    # Build email body
    body_lines = [
        "Loom Tool Health Check Results",
        "=" * 60,
        f"Timestamp: {timestamp}",
        f"Total Tools: {total}",
        f"OK: {ok_count}",
        f"Errors: {error_count}",
        f"Not Found: {not_found}",
        "",
        "Detailed Results:",
        "-" * 60,
    ]

    for result in results:
        tool = result["tool"]
        status = result["status"]
        ms = result.get("ms", 0)

        if status == "ok":
            result_type = result.get("result_type", "unknown")
            body_lines.append(f"✓ {tool}: OK ({ms}ms, returned {result_type})")
        elif status == "not_found":
            error = result.get("error", "unknown")
            body_lines.append(f"✗ {tool}: NOT_FOUND ({error})")
        elif status in ["error", "import_error", "param_error"]:
            error = result.get("error", "unknown")
            body_lines.append(f"✗ {tool}: {status.upper()} ({error})")

    # Summary stats
    total_ms = sum(r.get("ms", 0) for r in results)
    avg_ms = total_ms // max(ok_count, 1) if ok_count > 0 else 0

    body_lines.extend([
        "",
        "Performance:",
        f"Total Time: {total_ms}ms",
        f"Average: {avg_ms}ms per successful tool",
        "",
        "Environment:",
        f"Python: {sys.version.split()[0]}",
        f"Platform: {sys.platform}",
        f"Loom Root: {loom_root}",
        "",
        "This report was automatically generated by scripts/email_tool_results.py",
    ])

    body = "\n".join(body_lines)

    # Print to console
    print("\n" + body)
    print("\nAttempting to send email...")

    # Send email
    try:
        from loom.tools.email_report import research_email_report

        recipient = "ahmedalderai22@gmail.com"
        subject = f"Loom Tool Results - {timestamp}"

        email_result = await research_email_report(
            to=recipient,
            subject=subject,
            body=body,
            html=False,
        )

        print(f"\nEmail result: {json.dumps(email_result, indent=2)}")

        if email_result.get("status") == "sent":
            print(f"✓ Email sent successfully to {recipient}")
            sys.exit(0)
        else:
            print(f"✗ Email failed: {email_result.get('error', 'unknown error')}")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Failed to send email: {e}")
        print("Results saved to console output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
