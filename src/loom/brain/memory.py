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

# Category-based reliability priors for cold-start tool selection
# Tools with no historical data start with these priors instead of 0.5
_CATEGORY_PRIORS = {
    "search": 0.85,  # search tools are generally reliable
    "fetch": 0.80,  # fetch tools handle HTTP reasonably well
    "llm": 0.75,  # LLM tools have variable latency
    "github": 0.90,  # GitHub API is reliable
    "cache": 0.95,  # cache lookups are very reliable
    "spider": 0.78,  # bulk crawling has moderate reliability
    "markdown": 0.82,  # markdown extraction reasonably reliable
}


def _infer_tool_category(tool_name: str) -> str:
    """Infer tool category from its name to determine prior reliability."""
    name_lower = tool_name.lower()

    if "cache" in name_lower or "cache" in name_lower:
        return "cache"
    elif "search" in name_lower:
        return "search"
    elif "fetch" in name_lower or "html" in name_lower:
        return "fetch"
    elif "github" in name_lower or "git" in name_lower:
        return "github"
    elif "llm" in name_lower or "ask" in name_lower or "model" in name_lower:
        return "llm"
    elif "spider" in name_lower or "crawl" in name_lower:
        return "spider"
    elif "markdown" in name_lower or "extract" in name_lower:
        return "markdown"
    else:
        # Default: slightly conservative prior
        return "general"


def _get_category_prior(tool_name: str) -> float:
    """Get the reliability prior for a tool based on its category.

    Returns value between 0.0 and 1.0. Known categories return specific priors,
    unknown categories return 0.75 (slightly conservative).
    """
    category = _infer_tool_category(tool_name)
    return _CATEGORY_PRIORS.get(category, 0.75)


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

    Uses category-based priors for cold-start tool reliability estimation.
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
        """Get success rate for a tool (0.0–1.0).

        For tools with no history, returns category-based prior instead of 0.5.
        This improves cold-start reliability estimation for new tools.
        """
        stats = self._tool_stats.get(tool_name)
        if not stats or stats["calls"] == 0:
            # Use category-based prior for unknown tools
            prior = _get_category_prior(tool_name)
            logger.debug("cold-start prior for %s: %.2f (category: %s)",
                        tool_name, prior, _infer_tool_category(tool_name))
            return prior

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

    def get_affinity_boost(self, tool_name: str, recent_tool: str | None = None) -> float:
        """Get affinity boost for a tool based on what was recently used.

        If tool_name frequently follows recent_tool, returns a positive boost (0.0–0.3).
        """
        if not recent_tool:
            if self._history:
                recent_tool = self._history[-1].tool_name
            else:
                return 0.0

        pair_count = self._tool_pairs.get((recent_tool, tool_name), 0)
        if pair_count == 0:
            return 0.0

        total_from_recent = sum(
            count for (prev, _), count in self._tool_pairs.items() if prev == recent_tool
        )
        if total_from_recent == 0:
            return 0.0

        ratio = pair_count / total_from_recent
        return min(ratio * 0.3, 0.3)

    def clear(self) -> None:
        """Clear all memory (for testing)."""
        self._history.clear()
        self._tool_stats.clear()
        self._tool_pairs.clear()


_global_memory = BrainMemory()


def get_memory() -> BrainMemory:
    """Get the global brain memory instance."""
    return _global_memory
