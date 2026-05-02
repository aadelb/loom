"""HTML health dashboard for Loom server status visualization.

Generates a self-contained, interactive HTML page showing:
- Server status indicator (green/yellow/red)
- Key metrics (tools, uptime, memory, errors)
- LLM & search provider availability
- Recent error history
"""

from __future__ import annotations

import asyncio
import logging
import psutil
import time
from datetime import UTC, datetime
from typing import Any

from loom.server import research_health_check

logger = logging.getLogger("loom.tools.health_dashboard")

# Color scheme
COLOR_GREEN = "#4CAF50"
COLOR_YELLOW = "#FF9800"
COLOR_RED = "#F44336"
COLOR_BG = "#1a1a2e"
COLOR_TEXT = "#eee"
COLOR_CARD = "#16213e"


async def research_dashboard_html() -> dict[str, Any]:
    """Generate self-contained HTML health dashboard for Loom server.

    Returns:
        Dict with:
        - html: Complete HTML page as string
        - generated_at: ISO 8601 timestamp
        - metrics_summary: Dict of key metrics
    """
    try:
        # Get health check data
        health = await research_health_check()

        # Get system metrics
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = round(memory_info.rss / (1024 * 1024), 1)
        cpu_percent = round(process.cpu_percent(interval=0.1), 1)

        # Count provider statuses
        llm_up = sum(
            1 for p in health.get("llm_providers", {}).values() if p.get("status") == "up"
        )
        search_up = sum(
            1 for p in health.get("search_providers", {}).values() if p.get("status") == "up"
        )

        status = health.get("status", "unknown")
        status_color = (
            COLOR_GREEN if status == "healthy"
            else COLOR_YELLOW if status == "degraded"
            else COLOR_RED
        )

        # Build metrics summary
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

        # Format uptime for display
        uptime_sec = health.get("uptime_seconds", 0)
        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        minutes = (uptime_sec % 3600) // 60
        uptime_str = f"{days}d {hours}h {minutes}m"

        # Build provider status rows
        llm_html = _build_provider_rows(health.get("llm_providers", {}), "LLM")
        search_html = _build_provider_rows(health.get("search_providers", {}), "Search")

        # Build recent errors (if any)
        errors_html = "<p style='color: #999; font-size: 12px;'>No recent errors</p>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loom Server Health</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            background: {COLOR_BG};
            color: {COLOR_TEXT};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 28px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .status-indicator {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: {status_color};
            box-shadow: 0 0 8px {status_color};
        }}
        .subtitle {{
            color: #999;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: {COLOR_CARD};
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid {COLOR_GREEN};
        }}
        .metric-label {{
            font-size: 12px;
            color: #aaa;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: {COLOR_TEXT};
        }}
        .metric-unit {{
            font-size: 12px;
            color: #666;
            margin-left: 5px;
        }}
        .section {{
            background: {COLOR_CARD};
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 15px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}
        .provider-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
        }}
        .provider-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 4px;
            font-size: 12px;
        }}
        .provider-status-up {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: {COLOR_GREEN};
        }}
        .provider-status-down {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: {COLOR_RED};
        }}
        .error-log {{
            background: rgba(244, 67, 54, 0.1);
            padding: 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: 'Monaco', monospace;
            max-height: 150px;
            overflow-y: auto;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <div class="status-indicator"></div>
            Loom Server Health
        </h1>
        <div class="subtitle">
            Status: <strong>{status.upper()}</strong> • Last updated: {datetime.now(UTC).strftime('%H:%M:%S UTC')}
        </div>

        <div class="grid">
            <div class="metric-card">
                <div class="metric-label">Uptime</div>
                <div class="metric-value">{uptime_str}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Memory</div>
                <div class="metric-value">{memory_mb}<span class="metric-unit">MB</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">CPU</div>
                <div class="metric-value">{cpu_percent}<span class="metric-unit">%</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Tools Loaded</div>
                <div class="metric-value">{health.get("tool_count", 0)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Cache Size</div>
                <div class="metric-value">{health.get("cache", {}).get("size_mb", 0)}<span class="metric-unit">MB</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Sessions</div>
                <div class="metric-value">{health.get("sessions", {}).get("active", 0)}</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">LLM Providers ({llm_up}/8 Available)</div>
            <div class="provider-grid">
                {llm_html}
            </div>
        </div>

        <div class="section">
            <div class="section-title">Search Providers ({search_up}/21 Available)</div>
            <div class="provider-grid">
                {search_html}
            </div>
        </div>

        <div class="section">
            <div class="section-title">Recent Errors</div>
            <div class="error-log">
                {errors_html}
            </div>
        </div>

        <div class="footer">
            Loom v{health.get("version", "unknown")} • Generated at {datetime.now(UTC).isoformat()}
        </div>
    </div>
</body>
</html>"""

        generated_at = datetime.now(UTC).isoformat()

        return {
            "html": html,
            "generated_at": generated_at,
            "metrics_summary": metrics_summary,
        }

    except Exception as e:
        logger.exception("Error generating health dashboard")
        # Return basic error HTML
        error_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Loom Health - Error</title>
    <style>
        body {{ background: {COLOR_BG}; color: {COLOR_TEXT}; padding: 20px; font-family: sans-serif; }}
        .error {{ color: {COLOR_RED}; }}
    </style>
</head>
<body>
    <h1>Health Dashboard Error</h1>
    <p class="error">Failed to generate dashboard: {str(e)}</p>
</body>
</html>"""
        return {
            "html": error_html,
            "generated_at": datetime.now(UTC).isoformat(),
            "metrics_summary": {"error": str(e)},
        }


def _build_provider_rows(providers: dict[str, Any], provider_type: str) -> str:
    """Build HTML rows for provider status display.

    Args:
        providers: Dict of provider name -> {status: 'up'|'down'}
        provider_type: Type label for logging

    Returns:
        HTML string with provider status items
    """
    html_rows = []
    for name, info in providers.items():
        status = info.get("status", "down")
        status_class = "provider-status-up" if status == "up" else "provider-status-down"
        html_rows.append(
            f'<div class="provider-item"><div class="{status_class}"></div>{name}</div>'
        )
    return "\n".join(html_rows)
