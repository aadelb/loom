# Health Dashboard

The Loom health dashboard provides a self-contained HTML view of server status at a glance.

## Usage

Call the `research_dashboard_html` tool to generate an HTML page:

```bash
# Via Loom CLI
loom research_dashboard_html

# Via MCP
mcp call loom research_dashboard_html
```

## Output

Returns a dictionary with:

- **html**: Complete HTML page (self-contained, no external dependencies)
- **generated_at**: ISO 8601 timestamp of generation
- **metrics_summary**: Dictionary of key metrics

## Dashboard Features

The HTML dashboard shows:

1. **Status Indicator** - Color-coded (green/yellow/red) showing overall health
2. **Key Metrics** - Uptime, memory, CPU, tools loaded, cache size, active sessions
3. **Provider Status** - Individual status of 8 LLM providers and 21 search providers
4. **Error Log** - Recent errors (placeholder for future enhancement)

## Viewing the Dashboard

Save the HTML to a file and open in a browser:

```bash
# Using the Loom CLI and jq to extract HTML
loom research_dashboard_html | jq -r '.html' > /tmp/loom_health.html
open /tmp/loom_health.html
```

## Visual Design

- **Dark theme**: #1a1a2e background with light text (#eee)
- **Status colors**: Green (#4CAF50), Yellow (#FF9800), Red (#F44336)
- **Responsive layout**: Grid-based design that adapts to screen size
- **No external dependencies**: Fully self-contained CSS, no JavaScript

## Metrics Summary

The returned metrics_summary includes:

- `status`: "healthy", "degraded", or "unhealthy"
- `uptime_seconds`: Server uptime in seconds
- `tool_count`: Number of registered tools
- `memory_mb`: Process memory usage in MB
- `cpu_percent`: CPU usage percentage
- `llm_providers_up`: Number of available LLM providers
- `search_providers_up`: Number of available search providers
- `cache_entries`: Number of cache entries
- `cache_size_mb`: Cache size in MB
- `active_sessions`: Number of active sessions
