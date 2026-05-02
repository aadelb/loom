"""Deployment automation tools for Loom."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.deployment")
_DEPLOY_FILE = Path.home() / ".loom" / "deploy_history.jsonl"


async def research_deploy_status() -> dict[str, Any]:
    """Check deployment status: service, port, uptime, memory, health."""
    result = {
        "service_status": "unknown",
        "port_listening": False,
        "uptime_seconds": 0,
        "memory_mb": 0,
        "last_deploy": None,
        "restarts_today": 0,
        "health": "unknown",
    }

    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "status", "research-toolbox",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        text = (await asyncio.wait_for(proc.communicate(), timeout=5))[0].decode()
        result["service_status"] = "running" if "active (running)" in text else "inactive"
        if m := re.search(r"Memory:\s+([\d.]+)([KMG]?)", text):
            val, unit = float(m.group(1)), m.group(2)
            result["memory_mb"] = round(
                val * 1024 if unit == "G" else (val / 1024 if unit == "K" else val), 2
            )
    except (asyncio.TimeoutError, OSError):
        pass

    try:
        proc = await asyncio.create_subprocess_exec(
            "lsof", "-i", ":8787",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        result["port_listening"] = len((await asyncio.wait_for(proc.communicate(), timeout=5))[0]) > 0
    except (asyncio.TimeoutError, OSError):
        pass

    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "show", "-p", "ActiveEnterTimestamp", "research-toolbox",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        ts_line = (await asyncio.wait_for(proc.communicate(), timeout=5))[0].decode().strip()
        if "=" in ts_line:
            dt = datetime.strptime(ts_line.split("=", 1)[1], "%a %Y-%m-%d %H:%M:%S %Z")
            result["uptime_seconds"] = max(0, int((datetime.now(UTC).replace(tzinfo=None) - dt).total_seconds()))
    except (asyncio.TimeoutError, OSError, ValueError):
        pass

    if _DEPLOY_FILE.exists():
        try:
            lines = _DEPLOY_FILE.read_text().splitlines()
            if lines:
                result["last_deploy"] = json.loads(lines[-1]).get("timestamp")
                today = datetime.now(UTC).date()
                result["restarts_today"] = sum(
                    1 for line in lines
                    if datetime.fromisoformat(json.loads(line).get("timestamp", "")).date() == today
                )
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    result["health"] = (
        "healthy" if result["service_status"] == "running" and result["port_listening"]
        else ("degraded" if result["service_status"] == "running" else "unhealthy")
    )
    return result


async def research_deploy_history(limit: int = 20) -> dict[str, Any]:
    """Show deployment history from ~/.loom/deploy_history.jsonl."""
    if not _DEPLOY_FILE.exists():
        return {"deploys": [], "total_deploys": 0}
    try:
        lines = _DEPLOY_FILE.read_text().splitlines()
        deploys = [json.loads(line) for line in lines[-limit:] if line]
        return {"deploys": list(reversed(deploys)), "total_deploys": len(lines)}
    except (OSError, json.JSONDecodeError):
        return {"deploys": [], "total_deploys": 0}


async def research_deploy_record(
    commit_hash: str = "",
    tool_count: int = 0,
    duration_seconds: float = 0,
    status: str = "success",
) -> dict[str, Any]:
    """Record deployment event to ~/.loom/deploy_history.jsonl."""
    _DEPLOY_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "commit_hash": commit_hash or "",
        "tool_count": tool_count,
        "duration_seconds": duration_seconds,
        "status": status,
    }
    try:
        _DEPLOY_FILE.write_text(_DEPLOY_FILE.read_text() + json.dumps(record) + "\n")
        return {"recorded": True, "deploy_id": record["timestamp"].replace(":", "").replace("-", "")[:14]}
    except OSError as e:
        logger.error("deploy_record_write_failed: %s", e)
        return {"recorded": False, "deploy_id": "", "error": str(e)}
