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

    logger.info("startup_validation", health=results["overall_health"],
                loaded=results["loaded_ok"], total=results["total_modules"])
    return results


async def research_health_deep() -> dict[str, Any]:
    """Deep health check with resource usage metrics.

    Checks: memory, disk space, file descriptors, cache size, WAL files.

    Returns:
        {
            memory_mb: float,
            disk_free_gb: float,
            open_fds: int | None,
            cache_size_mb: float,
            sqlite_wal_sizes: {str: float},
            recommendations: [str]
        }
    """
    results = {
        "memory_mb": 0.0,
        "disk_free_gb": 0.0,
        "open_fds": None,
        "cache_size_mb": 0.0,
        "sqlite_wal_sizes": {},
        "recommendations": [],
    }

    # Memory usage (psutil optional)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        results["memory_mb"] = process.memory_info().rss / (1024 * 1024)
        try:
            results["open_fds"] = process.num_fds()
        except AttributeError:
            pass
        if results["memory_mb"] > 500:
            results["recommendations"].append("Memory usage high (>500MB)")
    except ImportError:
        pass

    # Disk space
    try:
        import shutil
        stat = shutil.disk_usage(str(Path.home()))
        results["disk_free_gb"] = stat.free / (1024 ** 3)
        if results["disk_free_gb"] < 1.0:
            results["recommendations"].append("Disk space low (<1GB)")
    except Exception as e:
        logger.warning(f"Disk check failed: {e}")

    # Cache size
    cache_dir = Path.home() / ".cache" / "loom"
    if cache_dir.exists():
        try:
            total = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
            results["cache_size_mb"] = total / (1024 * 1024)
            if results["cache_size_mb"] > 1000:
                results["recommendations"].append("Cache >1GB; cleanup recommended")
        except Exception as e:
            logger.warning(f"Cache size check failed: {e}")

    # WAL files
    db_dir = Path.home() / ".loom"
    if db_dir.exists():
        for wal_file in db_dir.glob("*.db-wal"):
            try:
                size_mb = wal_file.stat().st_size / (1024 * 1024)
                results["sqlite_wal_sizes"][wal_file.name] = round(size_mb, 2)
                if size_mb > 50:
                    results["recommendations"].append(f"WAL {wal_file.name} large ({size_mb}MB)")
            except Exception as e:
                logger.warning(f"WAL check failed: {e}")

    logger.info("health_deep", memory_mb=results["memory_mb"],
                cache_mb=results["cache_size_mb"])
    return results
