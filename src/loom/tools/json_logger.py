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
        self._lock: asyncio.Lock | None = None

    async def write(
        self,
        level: str,
        tool: str,
        message: str,
        duration_ms: float | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()
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
                # Run blocking file I/O in executor
                await asyncio.to_thread(
                    self._write_entry,
                    log_file,
                    entry,
                )
            except OSError as e:
                logger.error("write_failed: %s", e)
            await self._cleanup_old_logs()

    @staticmethod
    def _write_entry(log_file: Path, entry: dict[str, Any]) -> None:
        """Write entry to log file (blocking I/O)."""
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

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


def _query_logs(log_dir: Path, limit: int, since_minutes: int, level: str, tool: str) -> tuple[list[dict[str, Any]], int]:
    """Query logs from disk (blocking I/O).

    Args:
        log_dir: log directory path
        limit: max entries to return
        since_minutes: time window in minutes
        level: log level filter
        tool: tool name filter

    Returns:
        Tuple of (entries, count)
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=since_minutes)
    entries, count = [], 0
    try:
        for log_file in sorted(log_dir.glob("*.jsonl")):
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
    return entries, count


async def research_log_query(
    level: str = "all",
    tool: str = "",
    limit: int = 100,
    since_minutes: int = 60,
) -> dict[str, Any]:
    """Query structured logs with filtering."""
    try:
        logger_inst = get_structured_logger()
        # Run blocking file I/O in executor
        entries, count = await asyncio.to_thread(
            _query_logs,
            logger_inst.log_dir,
            limit,
            since_minutes,
            level,
            tool,
        )
        return {
            "entries": entries,
            "total_count": count,
            "filters_applied": {
                "level": level,
                "tool": tool,
                "since_minutes": since_minutes,
            },
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_log_query"}


def _get_log_stats(log_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
    """Get log statistics (blocking I/O).

    Args:
        log_dir: log directory path

    Returns:
        Tuple of (counts, errors, minutes, total)
    """
    counts, errors, minutes, total = {}, {}, {}, 0
    try:
        for log_file in log_dir.glob("*.jsonl"):
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
                            key = "T".join(ts)
                            minutes[key] = minutes.get(key, 0) + 1
                    except (json.JSONDecodeError, ValueError):
                        pass
    except OSError as e:
        logger.error("stats_failed: %s", e)
    return counts, errors, minutes, total


async def research_log_stats() -> dict[str, Any]:
    """Return log statistics: level counts, top erroring tools, requests/minute."""
    try:
        logger_inst = get_structured_logger()
        # Run blocking file I/O in executor
        counts, errors, minutes, total = await asyncio.to_thread(
            _get_log_stats,
            logger_inst.log_dir,
        )
        return {
            "counts_by_level": counts,
            "top_erroring_tools": dict(sorted(errors.items(), key=lambda x: x[1], reverse=True)[:5]),
            "requests_per_minute": dict(sorted(minutes.items())[-10:] if minutes else {}),
            "total_entries": total,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_log_stats"}
