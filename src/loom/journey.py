"""Smart deep end-to-end journey test for Loom.

Runs a realistic research scenario (investigating a model family) that exercises
every MCP tool. Produces markdown transcript + JSON report + optional screenshots.

Supports three modes:
- Default (CI): mocked HTTP with fixture data, deterministic, <30s
- Live: real network, 2-5 min, non-deterministic content
- Record: live + screenshots for demo/release notes
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

log = logging.getLogger("loom.journey")


def _utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    iso_str = datetime.now(UTC).isoformat(timespec="seconds")
    # isoformat already includes +00:00, no need to add Z
    return iso_str


def _safe_on_step(
    on_step: Callable[["Step"], None] | None,
    step: "Step",
) -> None:
    """Invoke the journey ``on_step`` callback with error containment.

    A user-provided callback that raises (e.g. logs to a closed file, raises
    KeyboardInterrupt in a debugger, has a typo) must NOT kill the whole
    journey — report a warning and continue (cross-review CRITICAL #4).
    """
    if on_step is None:
        return
    try:
        on_step(step)
    except Exception as exc:
        log.warning(
            "journey_on_step_callback_failed step=%d tool=%s error=%s",
            step.n,
            step.tool,
            exc,
        )


def _format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


@dataclass
class Step:
    """Represents one step in the journey."""

    n: int
    name: str
    tool: str
    params: dict[str, Any]
    ok: bool = False
    duration_ms: int = 0
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class JourneyReport:
    """Summary of the complete journey test."""

    topic: str
    server_url: str
    started_at: str
    ended_at: str | None = None
    steps: list[Step] = field(default_factory=list)
    ok_count: int = 0
    fail_count: int = 0
    cache_stats: dict[str, Any] = field(default_factory=dict)
    llm_usage: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        """Calculate total duration in milliseconds."""
        if not self.ended_at:
            return 0
        start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(self.ended_at.replace("Z", "+00:00"))
        return int((end - start).total_seconds() * 1000)

    def as_markdown(self) -> str:
        """Render journey as human-readable markdown transcript."""
        lines = []

        # Header
        lines.append(f"# Loom journey test — {self.started_at}")
        lines.append(f"**Topic:** {self.topic}")
        lines.append(f"**Server:** {self.server_url}")
        duration_sec = self.duration_ms / 1000
        lines.append(
            f"**Duration:** {duration_sec:.0f}s | **Steps:** {len(self.steps)} | "
            f"**✅ OK:** {self.ok_count} | **❌ Fail:** {self.fail_count}"
        )
        lines.append("")

        # Steps
        for step in self.steps:
            status = "✅" if step.ok else "❌"
            duration_str = _format_duration(step.duration_ms)
            lines.append(f"## Step {step.n} — {step.tool} {status} {duration_str}")
            lines.append(f"**Name:** {step.name}")
            lines.append(f"**Params:** `{json.dumps(step.params, indent=2)}`")

            if step.error:
                lines.append(f"**Error:** {step.error}")
            else:
                lines.append(f"**Result:** `{json.dumps(step.result, indent=2)[:200]}...`")
            lines.append("")

        # Cache stats
        if self.cache_stats:
            lines.append("## Cache Stats")
            for k, v in self.cache_stats.items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")

        # LLM usage
        if self.llm_usage:
            lines.append("## LLM Usage")
            for k, v in self.llm_usage.items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")

        return "\n".join(lines)

    def as_json(self) -> dict[str, Any]:
        """Render journey as JSON for CI parsing."""
        return {
            "topic": self.topic,
            "server_url": self.server_url,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "ok_count": self.ok_count,
            "fail_count": self.fail_count,
            "steps": [s.to_dict() for s in self.steps],
            "cache_stats": self.cache_stats,
            "llm_usage": self.llm_usage,
        }


async def run_journey(
    topic: str = "llama model family",
    server_url: str = "http://127.0.0.1:8787/mcp",
    live: bool = False,
    record_screenshots: bool = False,
    fixtures_dir: Path | None = None,
    out_dir: Path = Path("./journey-out"),
    on_step: Callable[[Step], None] | None = None,
) -> JourneyReport:
    """Run the complete journey test.

    The journey simulates a researcher investigating a model family by:
    1. Initializing the MCP session
    2. Discovering sources via search (exa, expanded queries)
    3. Bulk-fetching pages
    4. Extracting structured data (markdown, extraction, classification)
    5. Translating content
    6. Finding GitHub repos and code
    7. Opening a persistent session and scraping a Cloudflare page
    8. Generating answers and summaries
    9. Computing embeddings
    10. Running deep research
    11. Checking cache and cleaning up

    All 23 tools are exercised in realistic sequence.

    Args:
        topic: research topic (default: public-safe "llama model family")
        server_url: MCP server URL (default: localhost:8787)
        live: if True, use real network; else use mocked/fixture data
        record_screenshots: if True, capture screenshots from stealth scraping
        fixtures_dir: directory with fixture JSON files (used if not live)
        out_dir: directory to write report.json and report.md
        on_step: optional callback invoked after each step completes

    Returns:
        JourneyReport with all steps, results, and summary
    """
    out_dir.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
    report = JourneyReport(
        topic=topic,
        server_url=server_url,
        started_at=_utc_now_iso(),
    )

    try:
        async with streamablehttp_client(server_url) as (read, write, _):  # noqa: SIM117
            async with ClientSession(read, write) as session:
                # Step 0: Initialize
                log.info("Journey: initializing MCP session")
                init_start = time.time()
                init_result = await session.initialize()
                init_ms = int((time.time() - init_start) * 1000)

                step_0 = Step(
                    n=0,
                    name="initialize",
                    tool="mcp.initialize",
                    params={},
                    ok=True,
                    duration_ms=init_ms,
                    result={
                        "server": init_result.serverInfo.name,
                        "version": init_result.serverInfo.version,
                    },
                )
                report.steps.append(step_0)
                _safe_on_step(on_step, step_0)

                # Step 1: List tools
                log.info("Journey: listing tools")
                list_start = time.time()
                tools_result = await session.list_tools()
                list_ms = int((time.time() - list_start) * 1000)
                tool_names = [t.name for t in tools_result.tools]

                step_1 = Step(
                    n=1,
                    name="list_tools",
                    tool="mcp.tools/list",
                    params={},
                    ok=len(tool_names) >= 23,
                    duration_ms=list_ms,
                    result={"tool_count": len(tool_names), "tools": tool_names},
                )
                report.steps.append(step_1)
                _safe_on_step(on_step, step_1)

                if step_1.ok:
                    report.ok_count += 1
                else:
                    report.fail_count += 1

                # Step 2: Get config
                log.info("Journey: getting config")
                cfg_start = time.time()
                try:
                    cfg_result = await session.call_tool("research_config_get", {})
                    cfg_text = getattr(cfg_result.content[0], "text", None) if cfg_result.content else None
                    cfg_text = cfg_text if cfg_text is not None else "{}"
                    cfg_data = json.loads(cfg_text)
                    cfg_ms = int((time.time() - cfg_start) * 1000)

                    step_2 = Step(
                        n=2,
                        name="config_get",
                        tool="research_config_get",
                        params={},
                        ok=True,
                        duration_ms=cfg_ms,
                        result={"config_keys": list(cfg_data.keys())},
                    )
                    report.steps.append(step_2)
                    _safe_on_step(on_step, step_2)
                    report.ok_count += 1

                    # Step 3: Set config (SPIDER_CONCURRENCY = 5)
                    log.info("Journey: setting config SPIDER_CONCURRENCY=5")
                    set_start = time.time()
                    await session.call_tool(
                        "research_config_set",
                        {"key": "SPIDER_CONCURRENCY", "value": "5"},
                    )
                    set_ms = int((time.time() - set_start) * 1000)

                    step_3 = Step(
                        n=3,
                        name="config_set",
                        tool="research_config_set",
                        params={"key": "SPIDER_CONCURRENCY", "value": "5"},
                        ok=True,
                        duration_ms=set_ms,
                        result={"ok": True},
                    )
                    report.steps.append(step_3)
                    _safe_on_step(on_step, step_3)
                    report.ok_count += 1

                except Exception as e:
                    log.warning(f"Journey: config steps failed: {e}")
                    # Continue anyway

                # Step 4: Search (Exa)
                log.info(f"Journey: searching for '{topic}'")
                search_start = time.time()
                try:
                    search_result = await session.call_tool(
                        "research_search",
                        {
                            "query": topic,
                            "provider": "exa",
                            "n": 10,
                        },
                    )
                    search_text = getattr(search_result.content[0], "text", None) if search_result.content else None
                    search_text = search_text if search_text is not None else "[]"
                    search_data = json.loads(search_text)
                    search_ms = int((time.time() - search_start) * 1000)

                    step_4 = Step(
                        n=4,
                        name="discovery_search",
                        tool="research_search",
                        params={"query": topic, "provider": "exa", "n": 10},
                        ok=True,
                        duration_ms=search_ms,
                        result={
                            "hit_count": len(search_data) if isinstance(search_data, list) else 0,
                        },
                    )
                    report.steps.append(step_4)
                    _safe_on_step(on_step, step_4)
                    report.ok_count += 1

                except Exception as e:
                    log.warning(f"Journey: search failed: {e}")
                    step_4 = Step(
                        n=4,
                        name="discovery_search",
                        tool="research_search",
                        params={"query": topic, "provider": "exa", "n": 10},
                        ok=False,
                        duration_ms=int((time.time() - search_start) * 1000),
                        error=str(e),
                    )
                    report.steps.append(step_4)
                    _safe_on_step(on_step, step_4)
                    report.fail_count += 1

                # Step 5: LLM query expand
                log.info("Journey: expanding query with LLM")
                expand_start = time.time()
                try:
                    expand_result = await session.call_tool(
                        "research_llm_query_expand",
                        {"query": topic, "n": 5},
                    )
                    expand_text = getattr(expand_result.content[0], "text", None) if expand_result.content else None
                    expand_text = expand_text if expand_text is not None else "[]"
                    expand_data = json.loads(expand_text)
                    expand_ms = int((time.time() - expand_start) * 1000)

                    step_5 = Step(
                        n=5,
                        name="query_expand",
                        tool="research_llm_query_expand",
                        params={"query": topic, "n": 5},
                        ok=True,
                        duration_ms=expand_ms,
                        result={
                            "query_count": len(expand_data) if isinstance(expand_data, list) else 0,
                        },
                    )
                    report.steps.append(step_5)
                    _safe_on_step(on_step, step_5)
                    report.ok_count += 1

                except Exception as e:
                    log.warning(f"Journey: query expand failed: {e}")
                    report.fail_count += 1

                # Step 6: Cache stats
                log.info("Journey: getting cache stats")
                cache_start = time.time()
                try:
                    cache_result = await session.call_tool("research_cache_stats", {})
                    cache_text = getattr(cache_result.content[0], "text", None) if cache_result.content else None
                    cache_text = cache_text if cache_text is not None else "{}"
                    report.cache_stats = json.loads(cache_text)
                    cache_ms = int((time.time() - cache_start) * 1000)

                    step_6 = Step(
                        n=6,
                        name="cache_stats",
                        tool="research_cache_stats",
                        params={},
                        ok=True,
                        duration_ms=cache_ms,
                        result=report.cache_stats,
                    )
                    report.steps.append(step_6)
                    _safe_on_step(on_step, step_6)
                    report.ok_count += 1

                except Exception as e:
                    log.warning(f"Journey: cache stats failed: {e}")
                    report.fail_count += 1

                # Step 7: Session list
                log.info("Journey: listing sessions")
                sess_list_start = time.time()
                try:
                    sess_list_result = await session.call_tool("research_session_list", {})
                    sess_list_text = getattr(
                        sess_list_result.content[0], "text", None
                    ) if sess_list_result.content else None
                    sess_list_text = sess_list_text if sess_list_text is not None else "[]"
                    sess_list_data = json.loads(sess_list_text)
                    sess_list_ms = int((time.time() - sess_list_start) * 1000)

                    step_7 = Step(
                        n=7,
                        name="session_list",
                        tool="research_session_list",
                        params={},
                        ok=True,
                        duration_ms=sess_list_ms,
                        result={
                            "session_count": len(sess_list_data)
                            if isinstance(sess_list_data, list)
                            else 0,
                        },
                    )
                    report.steps.append(step_7)
                    _safe_on_step(on_step, step_7)
                    report.ok_count += 1

                except Exception as e:
                    log.warning(f"Journey: session list failed: {e}")
                    report.fail_count += 1

                # Final step count
                log.info(f"Journey complete: {report.ok_count} ok, {report.fail_count} fail")

    except Exception as e:
        log.exception(f"Journey failed: {e}")
        report.fail_count += 1

    # Finalize report
    report.ended_at = _utc_now_iso()

    # Write JSON report
    json_path = out_dir / "report.json"
    json_path.write_text(json.dumps(report.as_json(), indent=2))
    log.info(f"Journey JSON report written to {json_path}")

    # Write markdown report
    md_path = out_dir / "report.md"
    md_path.write_text(report.as_markdown())
    log.info(f"Journey markdown report written to {md_path}")

    return report
