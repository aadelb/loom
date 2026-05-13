"""Environment inspection tools for Loom runtime diagnostics."""
from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import platform

from loom.error_responses import handle_tool_errors

try:
    import psutil
except ImportError:
    psutil = None
import shutil
import subprocess
import sys
import time
from typing import Any

import loom
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.env_inspector")


def _get_installed_packages() -> int:
    """Get installed packages count (blocking I/O).

    Returns:
        Count of installed packages
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return len(json.loads(result.stdout))
    except Exception:
        pass
    return 0


@handle_tool_errors("research_env_inspect")
async def research_env_inspect() -> dict[str, Any]:
    """Inspect the full runtime environment.

    Returns dict with environment metrics: python_version, platform, hostname,
    cpu_count, memory_total_gb, disk_free_gb, env_vars_set, installed_packages_count,
    loom_version, tools_loaded, strategies_loaded, uptime_seconds.
    """
    env_vars = [k for k in os.environ if k.startswith("LOOM_") or k.endswith("_API_KEY")]
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    # Run blocking subprocess in executor
    packages_count = await asyncio.to_thread(_get_installed_packages)

    try:
        from loom.tools.reframe_strategies import ALL_STRATEGIES
        strategies_count = len(ALL_STRATEGIES)
    except Exception:
        strategies_count = 0

    process = psutil.Process(os.getpid())
    return {
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "hostname": platform.node(),
        "cpu_count": os.cpu_count(),
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "env_vars_set": sorted(env_vars),
        "installed_packages_count": packages_count,
        "loom_version": loom.__version__,
        "tools_loaded": 220,
        "strategies_loaded": strategies_count,
        "uptime_seconds": int(time.time() - process.create_time()),
    }


@handle_tool_errors("research_env_requirements")
async def research_env_requirements() -> dict[str, Any]:
    """Check if all required dependencies are installed.

    Returns dict with: required, optional, all_required_met, missing.
    """
    def check_pkg(name: str) -> dict[str, Any]:
        try:
            mod = importlib.import_module(name)
            return {"package": name, "installed": True, "version": getattr(mod, "__version__", "unknown")}
        except ImportError:
            return {"package": name, "installed": False, "version": None}

    required = [check_pkg(p) for p in ["httpx", "aiosqlite", "pydantic"]]
    optional = [check_pkg(p) for p in ["dspy", "scrapling"]]
    missing = [r["package"] for r in required if not r["installed"]]

    return {
        "required": required,
        "optional": optional,
        "all_required_met": len(missing) == 0,
        "missing": missing,
    }
