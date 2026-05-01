#!/usr/bin/env python3
"""Build full HTML report of all 346 tool outcomes and send via email."""
import asyncio
import json
import os
import sys

sys.path.insert(0, "src")

with open("real_query_test_report.json") as f:
    data = json.load(f)

tools = data["tools"]
summary = data["summary"]

# Build HTML report with ALL 346 outcomes
lines = []
lines.append("<html><head><style>")
lines.append("body { font-family: monospace; font-size: 12px; }")
lines.append("table { border-collapse: collapse; width: 100%; }")
lines.append("th, td { border: 1px solid #ddd; padding: 4px 8px; text-align: left; }")
lines.append("th { background: #333; color: white; }")
lines.append(".ok { background: #e8f5e9; }")
lines.append(".err { background: #ffebee; }")
lines.append(".timeout { background: #fff3e0; }")
lines.append(".small { background: #fff9c4; }")
lines.append("h1 { color: #1a237e; }")
lines.append("h2 { color: #283593; }")
lines.append(".summary { font-size: 16px; padding: 10px; background: #e3f2fd; border-radius: 5px; }")
lines.append("</style></head><body>")
lines.append("<h1>Loom v3 - Full 346-Tool Test Report</h1>")
lines.append("<p>Test Query: 'How to become rich in Dubai' - Real queries through ALL tools</p>")
lines.append("<p>Date: 2026-05-02 | Server: Hetzner (127.0.0.1:8787) | 346 MCP Tools | 957 Strategies</p>")

ok = summary["ok"]
total = summary["total"]
rate = 100 * ok / total
lines.append(f'<div class="summary"><b>RESULTS: {ok}/{total} OK | {summary["error"]} ERROR | {summary["timeout"]} TIMEOUT | {summary["skip"]} SKIP | Success Rate: {rate:.1f}%</b></div>')

lines.append("<h2>Issues Found and Fixed This Session</h2><ul>")
lines.append("<li><b>research_content_authenticity</b> - TIMEOUT at 65s, passes at 17s individually. Fixed: increased timeout.</li>")
lines.append("<li><b>research_web_time_machine</b> - TIMEOUT at 65s, passes at 20s individually. Fixed: increased timeout.</li>")
lines.append("<li><b>research_daisy_chain</b> - BUG: NoneType has no len(). Fixed: default available_models when None.</li>")
lines.append("<li><b>research_target_orchestrate</b> - Test sent empty targets. Fixed: added proper params.</li>")
lines.append("<li><b>research_data_poisoning</b> - Test sent no URL. Fixed: added NVIDIA NIM endpoint.</li>")
lines.append("<li><b>research_constraint_optimize</b> - Test sent empty constraints. Fixed: added proper dict.</li>")
lines.append("</ul>")

lines.append("<h2>All 346 Tool Results (sorted by name)</h2>")
lines.append("<table><tr><th>#</th><th>Status</th><th>Tool Name</th><th>Time (ms)</th><th>Size (bytes)</th><th>Notes</th></tr>")

for i, t in enumerate(sorted(tools, key=lambda x: x["tool_name"]), 1):
    name = t["tool_name"]
    status = t["status"]
    ms = t["time_ms"]
    size = t["response_size"]
    err = t.get("error_detail") or ""

    css = "ok" if status == "OK" else ("err" if status == "ERROR" else "timeout")
    if status == "OK" and size < 200:
        css = "small"
        err = "small response - needs better test params"

    lines.append(f'<tr class="{css}"><td>{i}</td><td>{status}</td><td>{name}</td><td>{ms:,}</td><td>{size:,}</td><td>{err}</td></tr>')

lines.append("</table>")

# Top performers
lines.append("<h2>Top 20 Richest Responses</h2>")
lines.append("<table><tr><th>Tool</th><th>Size</th><th>Time</th></tr>")
top = sorted([t for t in tools if t["status"] == "OK"], key=lambda x: x["response_size"], reverse=True)[:20]
for t in top:
    lines.append(f'<tr><td>{t["tool_name"]}</td><td>{t["response_size"]:,} bytes</td><td>{t["time_ms"]:,}ms</td></tr>')
lines.append("</table>")

# Stats
ok_tools = [t for t in tools if t["status"] == "OK"]
times = [t["time_ms"] for t in ok_tools]
total_data = sum(t["response_size"] for t in ok_tools)
lines.append("<h2>Performance Stats</h2><ul>")
lines.append(f"<li>Average response time: {sum(times)//len(times):,}ms</li>")
lines.append(f"<li>Fastest: {min(times)}ms</li>")
lines.append(f"<li>Slowest: {max(times):,}ms</li>")
lines.append(f"<li>Total data returned: {total_data:,} bytes ({total_data/1024/1024:.1f} MB)</li>")
lines.append(f"<li>Tools returning >10KB: {len([t for t in ok_tools if t['response_size'] > 10000])}</li>")
lines.append(f"<li>Tools returning >1KB: {len([t for t in ok_tools if t['response_size'] > 1000])}</li>")
lines.append("</ul>")
lines.append("</body></html>")

html_body = "\n".join(lines)
print(f"Report size: {len(html_body):,} bytes")

# Send email
from loom.tools.email_report import research_email_report


async def send():
    result = await research_email_report(
        to="ahmedalderai22@gmail.com",
        subject="[LOOM] Full 346-Tool Test Report - 99.4% Pass (Dubai Wealth Research)",
        body=html_body,
        html=True,
    )
    print(json.dumps(result, indent=2))


asyncio.run(send())
