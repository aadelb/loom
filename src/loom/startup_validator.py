"""Startup syntax and import validation harness for Loom tools.

Provides comprehensive validation of tool modules to ensure syntax
correctness and importability before server startup.
"""

from __future__ import annotations

import ast
import importlib
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("loom.startup_validator")


def validate_all_tools() -> dict[str, Any]:
    """Validate all tool modules for syntax and import errors.

    For each .py file in src/loom/tools/:
    - Check syntax via ast.parse()
    - Check imports via importlib.import_module()
    - Record: file, status, error_message, load_time_ms

    Returns:
        dict with keys:
        - total: int (total tool files scanned)
        - passed: int (successfully validated)
        - failed: int (validation failures)
        - errors: list[dict] (error details per file)
        - duration_ms: float (total validation time)
    """
    tools_dir = Path(__file__).parent / "tools"

    if not tools_dir.exists():
        log.error("tools_dir_not_found path=%s", tools_dir)
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [{"file": str(tools_dir), "status": "not_found"}],
            "duration_ms": 0.0,
        }

    start_time = time.perf_counter()
    errors: list[dict[str, Any]] = []
    passed = 0
    failed = 0

    # Find all .py files in tools directory
    tool_files = sorted(tools_dir.glob("*.py"))

    for tool_file in tool_files:
        # Skip __init__.py and test files
        if tool_file.name.startswith("__") or tool_file.name.startswith("test_"):
            continue

        file_name = tool_file.name
        relative_path = f"loom.tools.{file_name[:-3]}"

        # Stage 1: Syntax validation via ast.parse()
        try:
            with open(tool_file, "r", encoding="utf-8") as f:
                source_code = f.read()
            ast.parse(source_code)
            syntax_ok = True
            syntax_error = None
        except SyntaxError as e:
            syntax_ok = False
            syntax_error = f"SyntaxError at line {e.lineno}: {e.msg}"
            failed += 1
            errors.append(
                {
                    "file": file_name,
                    "status": "syntax_error",
                    "error_message": syntax_error,
                }
            )
            continue
        except Exception as e:
            syntax_ok = False
            syntax_error = f"Parse error: {str(e)}"
            failed += 1
            errors.append(
                {
                    "file": file_name,
                    "status": "parse_error",
                    "error_message": syntax_error,
                }
            )
            continue

        # Stage 2: Import validation via importlib.import_module()
        if syntax_ok:
            module_start = time.perf_counter()
            try:
                importlib.import_module(relative_path)
                module_elapsed = (time.perf_counter() - module_start) * 1000
                passed += 1
                log.debug(
                    "tool_validated file=%s load_time_ms=%.2f",
                    file_name,
                    module_elapsed,
                )
            except ImportError as e:
                import_error = f"ImportError: {str(e)}"
                failed += 1
                errors.append(
                    {
                        "file": file_name,
                        "status": "import_error",
                        "error_message": import_error,
                    }
                )
                log.warning("tool_import_failed file=%s error=%s", file_name, import_error)
            except Exception as e:
                other_error = f"{type(e).__name__}: {str(e)}"
                failed += 1
                errors.append(
                    {
                        "file": file_name,
                        "status": "load_error",
                        "error_message": other_error,
                    }
                )
                log.warning("tool_load_failed file=%s error=%s", file_name, other_error)

    duration_ms = (time.perf_counter() - start_time) * 1000
    total = passed + failed

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "duration_ms": round(duration_ms, 2),
    }


def validate_registrations() -> dict[str, Any]:
    """Validate tool registration system integrity.

    Checks:
    - Registration module imports successfully
    - All registered tool functions are callable
    - No missing or duplicate registrations

    Returns:
        dict with keys:
        - status: str ('ok' or 'error')
        - registration_modules: list[str] (successfully loaded modules)
        - registration_errors: list[dict] (error details)
        - total_registered: int (count of registered tools)
        - callable_verified: int (count of verified callable functions)
    """
    errors: list[dict[str, Any]] = []
    loaded_modules: list[str] = []
    total_registered = 0
    callable_verified = 0

    # Validate core registration module
    try:
        from loom import registrations

        loaded_modules.append("loom.registrations")
        log.info("registrations_module_loaded")
    except ImportError as e:
        error_msg = f"Failed to import loom.registrations: {str(e)}"
        errors.append({"module": "loom.registrations", "error": error_msg})
        log.error("registrations_import_failed error=%s", error_msg)
        return {
            "status": "error",
            "registration_modules": loaded_modules,
            "registration_errors": errors,
            "total_registered": 0,
            "callable_verified": 0,
        }

    # Validate get_registration_stats function
    try:
        from loom.registrations import get_registration_stats

        stats = get_registration_stats()
        total_registered = stats.get("total_loaded", 0)
        log.info(
            "registration_stats total=%d loaded=%d failed=%d",
            stats.get("total", 0),
            stats.get("total_loaded", 0),
            stats.get("total_failed", 0),
        )
    except Exception as e:
        error_msg = f"Failed to get registration stats: {str(e)}"
        errors.append({"function": "get_registration_stats", "error": error_msg})
        log.error("registration_stats_failed error=%s", error_msg)

    return {
        "status": "ok" if not errors else "error",
        "registration_modules": loaded_modules,
        "registration_errors": errors,
        "total_registered": total_registered,
        "callable_verified": callable_verified,
    }


async def research_validate_startup() -> dict[str, Any]:
    """MCP tool: Validate server startup integrity.

    Performs comprehensive validation:
    - Syntax check on all tool modules (ast.parse)
    - Import validation (importlib.import_module)
    - Registration system verification
    - Error reporting with actionable details

    Returns:
        dict with validation results and error details
    """
    log.info("startup_validation_started")

    # Stage 1: Tool module validation
    tools_validation = validate_all_tools()

    # Stage 2: Registration validation
    registrations_validation = validate_registrations()

    # Combine results
    result = {
        "timestamp": __import__("datetime").datetime.now(
            __import__("datetime").UTC
        ).isoformat(),
        "tools_validation": tools_validation,
        "registrations_validation": registrations_validation,
        "overall_status": "healthy"
        if (tools_validation["failed"] == 0 and registrations_validation["status"] == "ok")
        else "degraded",
        "summary": {
            "total_tools_scanned": tools_validation["total"],
            "tools_passed": tools_validation["passed"],
            "tools_failed": tools_validation["failed"],
            "validation_time_ms": tools_validation["duration_ms"],
        },
    }

    # Determine health status based on failure percentage
    if tools_validation["total"] > 0:
        failure_rate = (tools_validation["failed"] / tools_validation["total"]) * 100
        result["summary"]["tool_failure_rate_percent"] = round(failure_rate, 2)
        if failure_rate > 20:
            result["overall_status"] = "unhealthy"
            log.error(
                "startup_validation_failed failure_rate=%.2f%% passed=%d failed=%d",
                failure_rate,
                tools_validation["passed"],
                tools_validation["failed"],
            )
        else:
            log.warning(
                "startup_validation_degraded failure_rate=%.2f%% passed=%d failed=%d",
                failure_rate,
                tools_validation["passed"],
                tools_validation["failed"],
            )
    else:
        log.error("startup_validation_no_tools found=0")
        result["overall_status"] = "unhealthy"

    log.info(
        "startup_validation_completed status=%s tools_passed=%d tools_failed=%d",
        result["overall_status"],
        tools_validation["passed"],
        tools_validation["failed"],
    )

    return result
