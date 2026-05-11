"""Brain Memory Layer — Session context, usage patterns, and tool history."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("loom.brain.memory")

_MAX_HISTORY = 100
_MAX_SESSION_CONTEXT = 20


@dataclass
class ToolUsageRecord:
    """Record of a single tool invocation."""

    tool_name: str
    query: str
    params: dict[str, Any]
    success: bool
    elapsed_ms: int = 0
    timestamp: float = field(default_factory=time.time)
    error: str | None = None


class BrainMemory:
    """In-memory session and usage pattern store.

    Tracks:
    - Recent tool calls for context chaining
    - Tool success/failure rates for adaptive selection
    - Frequently used tool combinations
    """

    def __init__(self) -> None:
        self._history: list[ToolUsageRecord] = []
        self._tool_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"calls": 0, "successes": 0, "failures": 0, "total_ms": 0}
        )
        self._tool_pairs: dict[tuple[str, str], int] = defaultdict(int)

    def record_call(
        self,
        tool_name: str,
        query: str,
        params: dict[str, Any],
        success: bool,
        elapsed_ms: int = 0,
        error: str | None = None,
    ) -> None:
        """Record a tool call for learning and context."""
        record = ToolUsageRecord(
            tool_name=tool_name,
            query=query,
            params=params,
            success=success,
            elapsed_ms=elapsed_ms,
            error=error,
        )
        self._history.append(record)
        if len(self._history) > _MAX_HISTORY:
            self._history = self._history[-_MAX_HISTORY:]

        stats = self._tool_stats[tool_name]
        stats["calls"] += 1
        stats["total_ms"] += elapsed_ms
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1

        if len(self._history) >= 2:
            prev = self._history[-2].tool_name
            self._tool_pairs[(prev, tool_name)] += 1

    def get_recent_context(self, n: int = 5) -> list[dict[str, Any]]:
        """Get recent tool call context for chain reasoning."""
        recent = self._history[-min(n, _MAX_SESSION_CONTEXT):]
        return [
            {
                "tool": r.tool_name,
                "query": r.query[:100],
                "success": r.success,
                "elapsed_ms": r.elapsed_ms,
            }
            for r in recent
        ]

    def get_tool_reliability(self, tool_name: str) -> float:
        """Get success rate for a tool (0.0–1.0). Returns 0.5 for unknown tools."""
        stats = self._tool_stats.get(tool_name)
        if not stats or stats["calls"] == 0:
            return 0.5
        return stats["successes"] / stats["calls"]

    def get_suggested_next_tools(self, current_tool: str, top_k: int = 3) -> list[str]:
        """Suggest next tools based on historical co-occurrence."""
        candidates: list[tuple[str, int]] = []
        for (prev, nxt), count in self._tool_pairs.items():
            if prev == current_tool:
                candidates.append((nxt, count))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in candidates[:top_k]]

    def get_average_latency(self, tool_name: str) -> float:
        """Get average latency in ms for a tool."""
        stats = self._tool_stats.get(tool_name)
        if not stats or stats["calls"] == 0:
            return 0.0
        return stats["total_ms"] / stats["calls"]

    def clear(self) -> None:
        """Clear all memory (for testing)."""
        self._history.clear()
        self._tool_stats.clear()
        self._tool_pairs.clear()


_global_memory = BrainMemory()


def get_memory() -> BrainMemory:
    """Get the global brain memory instance."""
    return _global_memory
