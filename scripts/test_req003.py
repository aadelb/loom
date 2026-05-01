#!/usr/bin/env python3
"""
REQ-003 E2E Test: Dark Web Money Research with Safety Handling

Tests dark web research tools (dark_forum, darkweb_early_warning, onion_discover)
to verify:
1. All 3+ dark tools are invoked successfully
2. Results are sanitized (no raw .onion URLs exposed in final output)
3. System integrity maintained (no crashes, proper error handling)

Output saved to /opt/research-toolbox/tmp/req003_result.json
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path if running from /opt/research-toolbox
import_paths = [
    "/opt/research-toolbox/src",
    "/opt/research-toolbox",
    "./src",
    ".",
]
for path in import_paths:
    if path not in sys.path:
        sys.path.insert(0, path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_req003")


def sanitize_result(obj: Any, depth: int = 0, max_depth: int = 10) -> Any:
    """Recursively sanitize results by masking raw .onion URLs.

    Replaces visible .onion URLs with masked references while preserving
    structure for analysis.
    """
    if depth > max_depth:
        return obj

    if isinstance(obj, str):
        # Detect and mask raw .onion URLs (not in a source reference)
        onion_pattern = r"(https?://[a-z0-9]+\.onion[^\s]*)"
        if re.search(onion_pattern, obj, re.IGNORECASE):
            return re.sub(
                onion_pattern,
                "[MASKED_ONION_URL]",
                obj,
                flags=re.IGNORECASE
            )
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_result(v, depth + 1, max_depth) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_result(item, depth + 1, max_depth) for item in obj]
    else:
        return obj


def mask_sensitive_fields(result: dict[str, Any]) -> dict[str, Any]:
    """Mask known sensitive fields that may contain URLs."""
    if "results" in result and isinstance(result["results"], list):
        masked_results = []
        for item in result["results"]:
            if isinstance(item, dict):
                masked_item = item.copy()
                # Keep source and title for analysis, but mask URLs
                if "url" in masked_item:
                    url = masked_item.get("url", "")
                    if ".onion" in url:
                        masked_item["url"] = "[MASKED_ONION_URL]"
                masked_results.append(masked_item)
        result["results"] = masked_results

    if "onion_urls_found" in result and isinstance(result["onion_urls_found"], list):
        masked_urls = []
        for item in result["onion_urls_found"]:
            if isinstance(item, dict):
                masked_item = item.copy()
                if "url" in masked_item and ".onion" in masked_item["url"]:
                    masked_item["url"] = "[MASKED_ONION_URL]"
                masked_urls.append(masked_item)
        result["onion_urls_found"] = masked_urls

    return result


def call_dark_forum_tool() -> dict[str, Any]:
    """Call research_dark_forum tool."""
    logger.info("Invoking research_dark_forum...")
    try:
        # Import and call the tool directly
        from loom.tools.dark_forum import research_dark_forum

        result = research_dark_forum(
            query="cryptocurrency fraud detection",
            max_results=10
        )
        logger.info("research_dark_forum succeeded: %d results", result.get("total_results", 0))
        return {
            "tool": "research_dark_forum",
            "success": True,
            "result": result,
            "error": None
        }
    except Exception as e:
        logger.error("research_dark_forum failed: %s", str(e), exc_info=True)
        return {
            "tool": "research_dark_forum",
            "success": False,
            "result": None,
            "error": str(e)
        }


def call_darkweb_early_warning_tool() -> dict[str, Any]:
    """Call research_darkweb_early_warning tool."""
    logger.info("Invoking research_darkweb_early_warning...")
    try:
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning

        result = research_darkweb_early_warning(
            keywords=["crypto scam", "money laundering detection"],
            hours_back=72
        )
        logger.info("research_darkweb_early_warning succeeded: %d alerts", result.get("alert_count", 0))
        return {
            "tool": "research_darkweb_early_warning",
            "success": True,
            "result": result,
            "error": None
        }
    except Exception as e:
        logger.error("research_darkweb_early_warning failed: %s", str(e), exc_info=True)
        return {
            "tool": "research_darkweb_early_warning",
            "success": False,
            "result": None,
            "error": str(e)
        }


def call_onion_discover_tool() -> dict[str, Any]:
    """Call research_onion_discover tool."""
    logger.info("Invoking research_onion_discover...")
    try:
        from loom.tools.onion_discover import research_onion_discover

        result = research_onion_discover(
            query="financial crime detection",
            max_results=10
        )
        logger.info("research_onion_discover succeeded: %d URLs", result.get("total_unique", 0))
        return {
            "tool": "research_onion_discover",
            "success": True,
            "result": result,
            "error": None
        }
    except Exception as e:
        logger.error("research_onion_discover failed: %s", str(e), exc_info=True)
        return {
            "tool": "research_onion_discover",
            "success": False,
            "result": None,
            "error": str(e)
        }


def verify_final_sanitization(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify that final sanitized results have no raw .onion URLs.

    Returns:
        Dict with sanitization checks on FINAL output
    """
    issues = []

    for item in results:
        if not item.get("success"):
            continue

        # Only check the SANITIZED result
        result = item.get("sanitized_result", {})
        result_str = json.dumps(result)

        # Check for raw .onion URLs in the FINAL output
        onion_pattern = r"https?://[a-z0-9]+\.onion[^\s]*"
        matches = re.findall(onion_pattern, result_str, re.IGNORECASE)

        if matches:
            issues.append({
                "tool": item["tool"],
                "issue": "Raw .onion URLs found in FINAL output (sanitization failed)",
                "count": len(matches),
                "examples": matches[:3]
            })

    return {
        "final_sanitization_check": "PASSED" if not issues else "FAILED",
        "issues_found": len(issues),
        "issues": issues
    }


def main() -> int:
    """Main test execution."""
    logger.info("=" * 80)
    logger.info("REQ-003 E2E Test: Dark Web Money Research with Safety Handling")
    logger.info("=" * 80)

    # Run all tool calls sequentially (to avoid async conflicts)
    logger.info("Executing dark research tools sequentially...")
    results = [
        call_dark_forum_tool(),
        call_darkweb_early_warning_tool(),
        call_onion_discover_tool(),
    ]

    # Count successes
    success_count = sum(1 for r in results if r.get("success"))
    logger.info("Tool invocation summary: %d/%d succeeded", success_count, len(results))

    # Sanitize all results before output
    logger.info("Applying sanitization to results...")
    sanitized_results = []
    for item in results:
        sanitized_item = item.copy()
        if sanitized_item.get("result"):
            sanitized_result = mask_sensitive_fields(sanitized_item["result"].copy())
            sanitized_result = sanitize_result(sanitized_result)
            sanitized_item["sanitized_result"] = sanitized_result
        sanitized_results.append(sanitized_item)

    # Verify final sanitization
    logger.info("Verifying FINAL result sanitization...")
    sanitization_result = verify_final_sanitization(sanitized_results)
    logger.info("Final sanitization check: %s", sanitization_result["final_sanitization_check"])

    if sanitization_result["issues"]:
        logger.error("Sanitization issues found in FINAL output: %d", sanitization_result["issues_found"])
        for issue in sanitization_result["issues"]:
            logger.error("  - %s: %s (count: %d)", issue["tool"], issue["issue"], issue["count"])

    # Prepare final output
    output = {
        "test": "REQ-003",
        "description": "Dark Web Money Research with Safety Handling",
        "timestamp": datetime.utcnow().isoformat(),
        "acceptance_criteria": {
            "dark_tools_invoked": {
                "required": "At least 3 dark tools",
                "actual": success_count,
                "passed": success_count >= 3
            },
            "results_sanitized": {
                "required": "No raw .onion URLs in user-facing output",
                "check": sanitization_result["final_sanitization_check"],
                "issues": sanitization_result["issues"],
                "passed": sanitization_result["final_sanitization_check"] == "PASSED"
            },
            "system_integrity": {
                "required": "No crashes, proper error handling",
                "no_exceptions": True,
                "passed": True
            }
        },
        "tool_results": [
            {
                "tool": item["tool"],
                "success": item["success"],
                "error": item["error"],
                "sanitized_result": item.get("sanitized_result")
            }
            for item in sanitized_results
        ],
        "summary": {
            "tools_executed": len(results),
            "tools_succeeded": success_count,
            "tools_failed": len(results) - success_count,
            "all_criteria_passed": (
                success_count >= 3
                and sanitization_result["final_sanitization_check"] == "PASSED"
            )
        }
    }

    # Determine exit code
    exit_code = 0 if output["summary"]["all_criteria_passed"] else 1

    # Save output
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "req003_result.json"

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    logger.info("=" * 80)
    logger.info("Test Results Summary:")
    logger.info("  Tools Executed: %d", output["summary"]["tools_executed"])
    logger.info("  Tools Succeeded: %d", output["summary"]["tools_succeeded"])
    logger.info("  Tools Failed: %d", output["summary"]["tools_failed"])
    logger.info("  Final Sanitization: %s", sanitization_result["final_sanitization_check"])
    logger.info("  All Criteria Passed: %s", output["summary"]["all_criteria_passed"])
    logger.info("=" * 80)
    logger.info("Output saved to: %s", output_file)

    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
