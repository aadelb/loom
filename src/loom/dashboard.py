"""Real-time attack visualization dashboard for Loom.

Provides SSE (Server-Sent Events) compatible dashboard for monitoring:
- Live attack events (strategy_applied, model_response, score_update)
- Strategy success rates
- Model comparison metrics
- HCS score tracking
- Attack attempt counters

Generates standalone HTML with auto-refresh via text/event-stream protocol.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


class AttackDashboard:
    """Real-time streaming dashboard for attack visualization.

    Maintains an in-memory event log with summary statistics.
    Supports event filtering by index and HTML generation with embedded data.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8788) -> None:
        """Initialize the attack dashboard.

        Args:
            host: Server bind address (default: 127.0.0.1)
            port: Server port (default: 8788)
        """
        self.host = host
        self.port = port
        self.events: list[dict[str, Any]] = []

    def add_event(
        self,
        event_type: str,
        data: dict[str, Any],
        timestamp: str | None = None,
    ) -> None:
        """Record an event.

        Event types:
        - strategy_applied: strategy used on a model
        - model_response: model response received
        - score_update: HCS or other score calculated
        - attack_success: attack succeeded
        - attack_failure: attack failed

        Args:
            event_type: Type of event (must be one of known types)
            data: Event data (model, strategy, score, etc.)
            timestamp: ISO 8601 timestamp (auto-generated if None)
        """
        if timestamp is None:
            timestamp = datetime.now(UTC).isoformat()

        event = {
            "type": event_type,
            "timestamp": timestamp,
            "data": data,
            "index": len(self.events),
        }
        self.events.append(event)

    def get_events(self, since: int = 0) -> list[dict[str, Any]]:
        """Get events since index N.

        Args:
            since: Start index (inclusive). Default 0 returns all events.

        Returns:
            List of events from index `since` onwards.
        """
        if since < 0:
            since = 0
        if since >= len(self.events):
            return []
        return self.events[since:]

    def get_summary(self) -> dict[str, Any]:
        """Get dashboard summary statistics.

        Returns:
            Dictionary containing:
            - total_attacks: Total number of attacks attempted
            - successes: Number of successful attacks
            - failures: Number of failed attacks
            - success_rate: Percentage of successful attacks (0-100)
            - top_strategies: List of top 5 strategies by success rate
            - model_stats: Per-model attack statistics
            - avg_hcs_score: Average HCS score across successful attacks
            - active_models: Set of models that have been targeted
            - event_count: Total events recorded
        """
        total_attacks = 0
        successes = 0
        failures = 0
        hcs_scores: list[int] = []
        strategy_stats: dict[str, dict[str, int]] = {}
        model_stats: dict[str, dict[str, int]] = {}
        active_models: set[str] = set()

        for event in self.events:
            event_type = event["type"]
            data = event["data"]

            # Track model
            if "model" in data:
                active_models.add(data["model"])

            # Track attacks
            if event_type == "attack_success":
                total_attacks += 1
                successes += 1
                if "hcs_score" in data:
                    hcs_scores.append(data["hcs_score"])
                # Update model stats
                model = data.get("model", "unknown")
                if model not in model_stats:
                    model_stats[model] = {"total": 0, "successes": 0}
                model_stats[model]["total"] += 1
                model_stats[model]["successes"] += 1

            elif event_type == "attack_failure":
                total_attacks += 1
                failures += 1
                # Update model stats
                model = data.get("model", "unknown")
                if model not in model_stats:
                    model_stats[model] = {"total": 0, "successes": 0}
                model_stats[model]["total"] += 1

            # Track strategies
            if event_type == "strategy_applied" and "strategy" in data:
                strategy = data["strategy"]
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {"total": 0, "successes": 0}
                strategy_stats[strategy]["total"] += 1

            # Track strategy success
            if event_type == "attack_success" and "strategy" in data:
                strategy = data["strategy"]
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {"total": 0, "successes": 0}
                strategy_stats[strategy]["successes"] += 1

        # Calculate success rates
        success_rate = (
            (successes / max(total_attacks, 1)) * 100 if total_attacks > 0 else 0
        )

        # Top strategies (ranked by success rate)
        top_strategies = []
        for strategy, stats in sorted(
            strategy_stats.items(),
            key=lambda x: (
                x[1]["successes"] / max(x[1]["total"], 1),
                x[1]["successes"],
            ),
            reverse=True,
        )[:5]:
            top_strategies.append(
                {
                    "name": strategy,
                    "attempts": stats["total"],
                    "successes": stats["successes"],
                    "rate": round(
                        (stats["successes"] / max(stats["total"], 1)) * 100, 1
                    ),
                }
            )

        # Average HCS score
        avg_hcs = sum(hcs_scores) / len(hcs_scores) if hcs_scores else 0

        return {
            "total_attacks": total_attacks,
            "successes": successes,
            "failures": failures,
            "success_rate": round(success_rate, 1),
            "top_strategies": top_strategies,
            "model_stats": model_stats,
            "avg_hcs_score": round(avg_hcs, 1),
            "active_models": sorted(list(active_models)),
            "event_count": len(self.events),
        }

    def generate_html(self) -> str:
        """Generate standalone HTML dashboard page.

        Returns:
            HTML string with:
            - Live event feed (scrolling log)
            - Strategy success rate bar chart (text-based)
            - Model comparison table
            - Current HCS score indicator
            - Total attacks / successes / failures counters
        """
        summary = self.get_summary()
        events_json = json.dumps(self.events)

        # Generate strategy bars (text-based)
        strategy_bars = ""
        for strategy in summary["top_strategies"]:
            bar_width = int(strategy["rate"] / 5)  # 5% per character
            bar = "█" * bar_width
            strategy_bars += f"""
            <tr>
                <td>{strategy['name']}</td>
                <td>{strategy['attempts']}</td>
                <td>{strategy['successes']}</td>
                <td>{strategy['rate']:.1f}%</td>
                <td><code style="color: #4CAF50;">{bar}</code></td>
            </tr>"""

        # Generate model table rows
        model_rows = ""
        for model, stats in summary["model_stats"].items():
            rate = (stats["successes"] / max(stats["total"], 1)) * 100 if stats["total"] > 0 else 0
            model_rows += f"""
            <tr>
                <td>{model}</td>
                <td>{stats['total']}</td>
                <td>{stats['successes']}</td>
                <td>{rate:.1f}%</td>
            </tr>"""

        # HCS score color coding
        hcs_color = "#4CAF50"  # Green
        if summary["avg_hcs_score"] < 30:
            hcs_color = "#FF5722"  # Red
        elif summary["avg_hcs_score"] < 60:
            hcs_color = "#FFC107"  # Amber

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loom Attack Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Courier New', monospace;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}

        h1 {{
            color: #4CAF50;
            font-size: 28px;
            margin-bottom: 5px;
        }}

        .timestamp {{
            color: #888;
            font-size: 12px;
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric {{
            background: #111827;
            border: 1px solid #374151;
            border-radius: 4px;
            padding: 15px;
            text-align: center;
        }}

        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #4CAF50;
            margin: 10px 0;
        }}

        .metric-label {{
            font-size: 12px;
            text-transform: uppercase;
            color: #888;
            letter-spacing: 1px;
        }}

        .hcs-indicator {{
            width: 100%;
            height: 30px;
            background: #1f2937;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }}

        .hcs-fill {{
            height: 100%;
            background: {hcs_color};
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section-title {{
            font-size: 18px;
            color: #4CAF50;
            border-bottom: 1px solid #374151;
            padding-bottom: 10px;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: #111827;
            border: 1px solid #374151;
        }}

        th {{
            background: #1f2937;
            color: #4CAF50;
            padding: 12px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 2px solid #374151;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid #374151;
        }}

        tr:hover {{
            background: #1f2937;
        }}

        .event-feed {{
            background: #111827;
            border: 1px solid #374151;
            border-radius: 4px;
            max-height: 400px;
            overflow-y: auto;
            padding: 15px;
        }}

        .event {{
            padding: 10px;
            border-left: 3px solid #4CAF50;
            margin-bottom: 10px;
            background: #0a0e27;
            border-radius: 2px;
            font-size: 12px;
        }}

        .event-timestamp {{
            color: #888;
            font-size: 11px;
        }}

        .event-type {{
            color: #4CAF50;
            font-weight: bold;
        }}

        .event-data {{
            color: #bbb;
            margin-top: 5px;
        }}

        .status-success {{
            color: #4CAF50;
        }}

        .status-failure {{
            color: #FF5722;
        }}

        .status-pending {{
            color: #FFC107;
        }}

        code {{
            background: #1f2937;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
        }}

        .no-events {{
            color: #666;
            text-align: center;
            padding: 20px;
        }}

        @media (max-width: 768px) {{
            .metrics {{
                grid-template-columns: 1fr;
            }}

            table {{
                font-size: 12px;
            }}

            td, th {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚔️ LOOM Attack Dashboard</h1>
            <div class="timestamp">Last updated: <span id="timestamp">{datetime.now(UTC).isoformat()}</span></div>
        </header>

        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Total Attacks</div>
                <div class="metric-value">{summary['total_attacks']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Successes</div>
                <div class="metric-value status-success">{summary['successes']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Failures</div>
                <div class="metric-value status-failure">{summary['failures']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">{summary['success_rate']:.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg HCS Score</div>
                <div class="metric-value">{summary['avg_hcs_score']:.1f}</div>
                <div class="hcs-indicator">
                    <div class="hcs-fill" style="width: {min(summary['avg_hcs_score'], 100)}%;">
                        {int(summary['avg_hcs_score'])}
                    </div>
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">Active Models</div>
                <div class="metric-value">{len(summary['active_models'])}</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Strategy Success Rates</div>
            {"" if summary['top_strategies'] else '<div class="no-events">No strategy data yet</div>'}
            {f'''<table>
                <thead>
                    <tr>
                        <th>Strategy Name</th>
                        <th>Attempts</th>
                        <th>Successes</th>
                        <th>Success Rate</th>
                        <th>Visual</th>
                    </tr>
                </thead>
                <tbody>
                    {strategy_bars}
                </tbody>
            </table>''' if summary['top_strategies'] else ''}
        </div>

        <div class="section">
            <div class="section-title">Model Comparison</div>
            {"" if summary['model_stats'] else '<div class="no-events">No model data yet</div>'}
            {f'''<table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Total Attacks</th>
                        <th>Successes</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {model_rows}
                </tbody>
            </table>''' if summary['model_stats'] else ''}
        </div>

        <div class="section">
            <div class="section-title">Event Feed (Last {min(len(self.events), 20)} events)</div>
            <div class="event-feed" id="event-feed">
                {"" if self.events else '<div class="no-events">No events recorded yet</div>'}
                {self._generate_event_html()}
            </div>
        </div>
    </div>

    <script>
        const allEvents = {events_json};
        const maxDisplayed = 20;

        function updateEventFeed() {{
            const feed = document.getElementById('event-feed');
            const recentEvents = allEvents.slice(-maxDisplayed).reverse();

            if (recentEvents.length === 0) {{
                feed.innerHTML = '<div class="no-events">No events recorded yet</div>';
                return;
            }}

            feed.innerHTML = recentEvents.map(event => {{
                const date = new Date(event.timestamp);
                const time = date.toLocaleTimeString();
                const typeClass = event.type.includes('success') ? 'status-success' :
                                 event.type.includes('failure') ? 'status-failure' : 'status-pending';
                const dataStr = JSON.stringify(event.data, null, 2);

                return `
                    <div class="event">
                        <div class="event-timestamp">${{time}}</div>
                        <div class="event-type">${{event.type}}</div>
                        <div class="event-data"><code>${{JSON.stringify(event.data).substring(0, 80)}}</code></div>
                    </div>
                `;
            }}).join('');
        }}

        function updateTimestamp() {{
            const ts = document.getElementById('timestamp');
            ts.textContent = new Date().toISOString();
        }}

        // Initial render
        updateEventFeed();
        updateTimestamp();

        // Auto-refresh every 5 seconds
        setInterval(() => {{
            updateTimestamp();
        }}, 5000);
    </script>
</body>
</html>"""

        return html

    def _generate_event_html(self) -> str:
        """Generate HTML for recent events (last 20).

        Returns:
            HTML string containing event divs.
        """
        if not self.events:
            return ""

        recent_events = self.events[-20:]
        html = ""

        for event in recent_events:
            event_type = event["type"]
            timestamp = event["timestamp"]
            data = event["data"]

            # Color code by event type
            if "success" in event_type:
                type_class = "status-success"
            elif "failure" in event_type:
                type_class = "status-failure"
            else:
                type_class = "status-pending"

            data_str = json.dumps(data)
            # Truncate long data
            if len(data_str) > 80:
                data_str = data_str[:77] + "..."

            html += f"""
            <div class="event">
                <div class="event-timestamp">{timestamp[-8:-5]}Z</div>
                <div class="event-type {type_class}">{event_type}</div>
                <div class="event-data"><code>{data_str}</code></div>
            </div>"""

        return html
