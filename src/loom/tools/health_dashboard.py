"""HTML health dashboard for Loom server status visualization."""

from __future__ import annotations

import html
import logging

try:
    import psutil
except ImportError:
    psutil = None

from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.tools.health_dashboard")

# Magic number constants
DEFAULT_LLM_PROVIDER_COUNT = 8
DEFAULT_SEARCH_PROVIDER_COUNT = 21


async def research_dashboard_html() -> dict[str, Any]:
    """Generate self-contained HTML health dashboard for Loom server.

    Returns:
        Dict with html (complete page), generated_at (ISO timestamp),
        metrics_summary (key metrics dict). On error, returns dict with
        error message, status code, and tool name.
    """
    try:
        if psutil is None:
            return {
                "error": "psutil not installed; cannot gather system metrics",
                "status": "unavailable",
                "tool": "research_dashboard_html",
            }

        from loom.tool_functions import research_health_check

        health = await research_health_check()
        if not isinstance(health, dict):
            return {
                "error": f"Invalid health response type: {type(health).__name__}",
                "status": "error",
                "tool": "research_dashboard_html",
            }

        process = psutil.Process()
        memory_mb = round(process.memory_info().rss / (1024 * 1024), 1)
        # Non-blocking CPU check; interval=None avoids synchronous delay
        cpu_percent = round(process.cpu_percent(interval=None), 1)

        # Safely count providers with type validation
        llm_providers = health.get("llm_providers", {})
        if not isinstance(llm_providers, dict):
            llm_providers = {}
        llm_up = sum(1 for p in llm_providers.values() if isinstance(p, dict) and p.get("status") == "up")

        search_providers = health.get("search_providers", {})
        if not isinstance(search_providers, dict):
            search_providers = {}
        search_up = sum(1 for p in search_providers.values() if isinstance(p, dict) and p.get("status") == "up")

        status = health.get("status", "unknown")
        # Explicit status color mapping with documented defaults
        status_colors = {
            "healthy": "#4CAF50",
            "degraded": "#FF9800",
            "unknown": "#F44336",
            "error": "#F44336",
        }
        status_color = status_colors.get(status, "#F44336")

        uptime_sec = health.get("uptime_seconds", 0)
        uptime_str = f"{uptime_sec // 86400}d {(uptime_sec % 86400) // 3600}h {(uptime_sec % 3600) // 60}m"

        # Build provider status HTML with proper escaping and type checking
        def build_provider_html(providers: dict[str, Any]) -> str:
            """Build provider status grid HTML."""
            if not isinstance(providers, dict):
                return ""
            items = []
            for name, prov_data in providers.items():
                if not isinstance(prov_data, dict):
                    continue
                status_val = "up" if prov_data.get("status") == "up" else "dn"
                # Escape provider name to prevent HTML injection
                escaped_name = html.escape(str(name))
                items.append(f'<div class="pi"><div class="ps-{status_val}"></div>{escaped_name}</div>')
            return "".join(items)

        llm_html = build_provider_html(llm_providers)
        search_html = build_provider_html(search_providers)

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
<div class="s"><div class="st2">LLM ({llm_up}/{DEFAULT_LLM_PROVIDER_COUNT})</div><div class="pg">{llm_html}</div></div>
<div class="s"><div class="st2">Search ({search_up}/{DEFAULT_SEARCH_PROVIDER_COUNT})</div><div class="pg">{search_html}</div></div>
<div class="ft">Loom v{health.get("version", "?")} • {datetime.now(UTC).isoformat()}</div>
</div></body></html>"""

        return {
            "html": html,
            "generated_at": datetime.now(UTC).isoformat(),
            "metrics_summary": metrics_summary,
        }
    except Exception as exc:
        logger.exception("Dashboard generation failed")
        return {
            "error": str(exc),
            "status": "error",
            "tool": "research_dashboard_html",
        }
