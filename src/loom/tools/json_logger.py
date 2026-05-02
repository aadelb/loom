"""Structured JSON logging tools for Loom — query and analyze logs."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.json_logger")


class StructuredLogger:
    """Thread-safe JSON logger with daily rotation and 7-day retention."""

    def __init__(self, log_dir: str | None = None):
        self.log_dir = Path(log_dir or Path.home() / ".loom" / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def write(
        self,
        level: str,
        tool: str,
        message: str,
        duration_ms: float | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        async with self._lock:
            log_file = self.log_dir / datetime.now(UTC).strftime("%Y-%m-%d.jsonl")
            entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": level.lower(),
                "tool": tool,
                "message": message,
                "duration_ms": duration_ms,
                "error": error,
                "metadata": metadata or {},
            }
            try:
                with open(log_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except OSError as e:
                logger.error("write_failed: %s", e)
            await self._cleanup_old_logs()

    async def _cleanup_old_logs(self) -> None:
        cutoff = (datetime.now(UTC) - timedelta(days=7)).timestamp()
        try:
            for f in self.log_dir.glob("*.jsonl"):
                if f.stat().st_mtime < cutoff:
                    f.unlink()
        except OSError:
            pass


_instance: StructuredLogger | None = None


def get_structured_logger() -> StructuredLogger:
    global _instance
    _instance = _instance or StructuredLogger()
    return _instance


async def research_log_query(
    level: str = "all",
    tool: str = "",
    limit: int = 100,
    since_minutes: int = 60,
) -> dict[str, Any]:
    """Query structured logs with filtering."""
    logger_inst = get_structured_logger()
    cutoff = datetime.now(UTC) - timedelta(minutes=since_minutes)
    entries, count = [], 0
    try:
        for log_file in sorted(logger_inst.log_dir.glob("*.jsonl")):
            if count >= limit:
                break
            with open(log_file) as f:
                for line in f:
                    if count >= limit:
                        break
                    try:
                        entry = json.loads(line)
                        ts = datetime.fromisoformat(entry.get("timestamp", ""))
                        if ts < cutoff or (level != "all" and entry.get("level") != level.lower()):
                            continue
                        if tool and tool not in entry.get("tool", ""):
                            continue
                        entries.append(entry)
                        count += 1
                    except (json.JSONDecodeError, ValueError):
                        pass
    except OSError as e:
        logger.error("query_failed: %s", e)
    return {"entries": entries, "total_count": count, "filters_applied": {"level": level, "tool": tool, "since_minutes": since_minutes}}


async def research_log_stats() -> dict[str, Any]:
    """Return log statistics: level counts, top erroring tools, requests/minute."""
    logger_inst = get_structured_logger()
    counts, errors, minutes, total = {}, {}, {}, 0
    try:
        for log_file in logger_inst.log_dir.glob("*.jsonl"):
            with open(log_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        lv = entry.get("level", "unknown")
                        counts[lv] = counts.get(lv, 0) + 1
                        total += 1
                        if entry.get("error"):
                            t = entry.get("tool", "unknown")
                            errors[t] = errors.get(t, 0) + 1
                        ts = entry.get("timestamp", "").split("T")[:2]
                        if len(ts) == 2:
                            key = "".join(ts)
                            minutes[key] = minutes.get(key, 0) + 1
                    except (json.JSONDecodeError, ValueError):
                        pass
    except OSError as e:
        logger.error("stats_failed: %s", e)
    return {
        "counts_by_level": counts,
        "top_erroring_tools": dict(sorted(errors.items(), key=lambda x: x[1], reverse=True)[:5]),
        "requests_per_minute": dict(sorted(minutes.items())[-10:] if minutes else {}),
        "total_entries": total,
    }
