"""HTML health dashboard for Loom server status visualization."""

from __future__ import annotations

import logging
try:
    import psutil
except ImportError:
    psutil = None
from datetime import UTC, datetime
from typing import Any


logger = logging.getLogger("loom.tools.health_dashboard")


async def research_dashboard_html() -> dict[str, Any]:
    """Generate self-contained HTML health dashboard for Loom server.

    Returns:
        Dict with html (complete page), generated_at (ISO timestamp),
        metrics_summary (key metrics dict)
    """
    from loom.server import research_health_check
    health = await research_health_check()
    process = psutil.Process()
    memory_mb = round(process.memory_info().rss / (1024 * 1024), 1)
    cpu_percent = round(process.cpu_percent(interval=0.1), 1)

    llm_up = sum(1 for p in health.get("llm_providers", {}).values() if p.get("status") == "up")
    search_up = sum(1 for p in health.get("search_providers", {}).values() if p.get("status") == "up")

    status = health.get("status", "unknown")
    status_color = "#4CAF50" if status == "healthy" else "#FF9800" if status == "degraded" else "#F44336"

    uptime_sec = health.get("uptime_seconds", 0)
    uptime_str = f"{uptime_sec // 86400}d {(uptime_sec % 86400) // 3600}h {(uptime_sec % 3600) // 60}m"

    llm_html = "".join(
        f'<div class="pi"><div class="ps-{"up" if p.get("status") == "up" else "dn"}"></div>{k}</div>'
        for k, p in health.get("llm_providers", {}).items()
    )
    search_html = "".join(
        f'<div class="pi"><div class="ps-{"up" if p.get("status") == "up" else "dn"}"></div>{k}</div>'
        for k, p in health.get("search_providers", {}).items()
    )

    metrics_summary = {
        "status": status,
        "uptime_seconds": health.get("uptime_seconds", 0),
        "tool_count": health.get("tool_count", 0),
        "memory_mb": memory_mb,
        "cpu_percent": cpu_percent,
        "llm_providers_up": llm_up,
        "search_providers_up": search_up,
        "cache_entries": health.get("cache", {}).get("entries", 0),
        "cache_size_mb": health.get("cache", {}).get("size_mb", 0),
        "active_sessions": health.get("sessions", {}).get("active", 0),
    }

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Loom Health</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#1a1a2e;color:#eee;font-family:system-ui,sans-serif;padding:20px;line-height:1.6}}
.c{{max-width:1200px;margin:0 auto}}h1{{font-size:28px;margin:0 0 10px;display:flex;gap:10px}}
.si{{width:16px;height:16px;border-radius:50%;background:{status_color};box-shadow:0 0 8px {status_color}}}
.st{{color:#999;font-size:12px;margin-bottom:30px}}.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:30px}}
.mc{{background:#16213e;padding:15px;border-radius:8px;border-left:4px solid #4CAF50}}.ml{{font-size:11px;color:#aaa;text-transform:uppercase;margin-bottom:5px}}
.mv{{font-size:24px;font-weight:bold}}.mu{{font-size:11px;color:#666;margin-left:5px}}.s{{background:#16213e;padding:20px;border-radius:8px;margin-bottom:20px}}
.st2{{font-size:16px;font-weight:bold;margin-bottom:15px;border-bottom:1px solid #333;padding-bottom:10px}}.pg{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px}}
.pi{{display:flex;align-items:center;gap:8px;padding:8px;background:rgba(255,255,255,.03);border-radius:4px;font-size:12px}}.ps-up{{width:8px;height:8px;border-radius:50%;background:#4CAF50}}
.ps-dn{{width:8px;height:8px;border-radius:50%;background:#F44336}}.ft{{text-align:center;color:#666;font-size:11px;margin-top:30px;padding-top:20px;border-top:1px solid #333}}
</style></head><body><div class="c">
<h1><div class="si"></div>Loom Health</h1>
<div class="st">{status.upper()} • {datetime.now(UTC).strftime('%H:%M:%S UTC')}</div>
<div class="g">
<div class="mc"><div class="ml">Uptime</div><div class="mv">{uptime_str}</div></div>
<div class="mc"><div class="ml">Memory</div><div class="mv">{memory_mb}<span class="mu">MB</span></div></div>
<div class="mc"><div class="ml">CPU</div><div class="mv">{cpu_percent}<span class="mu">%</span></div></div>
<div class="mc"><div class="ml">Tools</div><div class="mv">{health.get("tool_count", 0)}</div></div>
<div class="mc"><div class="ml">Cache</div><div class="mv">{health.get("cache", {}).get("size_mb", 0)}<span class="mu">MB</span></div></div>
<div class="mc"><div class="ml">Sessions</div><div class="mv">{health.get("sessions", {}).get("active", 0)}</div></div>
</div>
<div class="s"><div class="st2">LLM ({llm_up}/8)</div><div class="pg">{llm_html}</div></div>
<div class="s"><div class="st2">Search ({search_up}/21)</div><div class="pg">{search_html}</div></div>
<div class="ft">Loom v{health.get("version", "?")} • {datetime.now(UTC).isoformat()}</div>
</div></body></html>"""

    return {
        "html": html,
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics_summary": metrics_summary,
    }
