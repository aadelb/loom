"""Startup validation system for Loom MCP server."""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.startup_validator")

TOOL_MODULES = [
    "academic_integrity", "access_tools", "adversarial_debate_tool",
    "ai_safety", "ai_safety_extended", "arxiv_pipeline", "breach_check",
    "cache_mgmt", "cert_analyzer", "change_monitor", "company_intel",
    "crypto_trace", "dark_forum", "dark_recon", "dead_content",
    "deception_detect", "deep", "domain_intel", "fact_checker", "fetch",
    "gap_tools_academic", "gap_tools_advanced", "github", "infra_analysis",
    "ip_intel", "knowledge_graph", "llm", "markdown", "multi_llm",
    "multi_search", "pdf_extract", "prompt_reframe", "search", "social_intel",
    "spider", "threat_profile", "transcribe",
]


async def research_validate_startup() -> dict[str, Any]:
    """Comprehensive health check on all registered tools.

    Validates: tool modules, providers, config, required directories, databases.

    Returns:
        {
            total_modules: int,
            loaded_ok: int,
            import_errors: [{"module": str, "error": str}],
            missing_dirs: [str],
            db_status: {"accessible": bool, "writable": bool, "databases": [str]},
            overall_health: "healthy" | "degraded" | "critical"
        }
    """
    results = {
        "total_modules": len(TOOL_MODULES),
        "loaded_ok": 0,
        "import_errors": [],
        "missing_dirs": [],
        "db_status": {"accessible": False, "writable": False, "databases": []},
        "overall_health": "healthy",
    }

    # Validate tool modules
    for module_name in TOOL_MODULES:
        try:
            importlib.import_module(f"loom.tools.{module_name}")
            results["loaded_ok"] += 1
        except Exception as e:
            results["import_errors"].append({
                "module": module_name,
                "error": str(e)[:150]
            })
            results["overall_health"] = "degraded"

    # Validate config
    try:
        from loom.config import load_config, CONFIG
        load_config()
        if not CONFIG:
            results["overall_health"] = "degraded"
    except Exception as e:
        results["import_errors"].append({"module": "config", "error": str(e)[:150]})
        results["overall_health"] = "critical"

    # Check required directories
    for dir_path in [Path.home() / ".loom", Path.home() / ".cache" / "loom"]:
        if not dir_path.exists():
            results["missing_dirs"].append(str(dir_path))
            results["overall_health"] = "degraded"

    # Check SQLite databases
    db_dir = Path.home() / ".loom"
    if db_dir.exists():
        db_files = list(db_dir.glob("*.db"))
        results["db_status"]["databases"] = [f.name for f in db_files]
        try:
            for db_file in db_files[:3]:  # Check first 3
                conn = sqlite3.connect(str(db_file), timeout=2.0)
                conn.execute("PRAGMA integrity_check")
                conn.close()
            results["db_status"]["accessible"] = True
            test_file = db_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            results["db_status"]["writable"] = True
        except Exception as e:
            logger.warning(f"Database check failed: {e}")
            results["db_status"]["writable"] = False
            results["overall_health"] = "degraded"

    if results["import_errors"] and len(results["import_errors"]) > 5:
        results["overall_health"] = "critical"

    logger.info("startup_validation health=%s loaded=%d total=%d", results["overall_health"], results["loaded_ok"], results["total_modules"])
    return results
