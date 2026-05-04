# Loom VS Code Extension

VS Code integration for the Loom MCP Research Server (738+ tools).

## Features

- **Loom: Search** — Run research queries from the command palette
- **Loom: Deep Research** — Deep research with results in a webview panel
- **Loom: Reframe Text** — Select text and reframe it using 957 strategies
- **Loom: Check Server Health** — Status bar indicator for server connectivity

## Setup

1. Configure server URL in settings: `loom.serverUrl` (default: `http://localhost:8787`)
2. Optionally set API key: `loom.apiKey`

## Development

```bash
cd vscode-extension
npm install
npm run compile
# Press F5 in VS Code to launch Extension Development Host
```

## Commands

| Command | Description |
|---------|-------------|
| `Loom: Search` | Search across 21 providers |
| `Loom: Deep Research` | 12-stage deep research pipeline |
| `Loom: Reframe Text` | Reframe selected text with AI safety strategies |
| `Loom: Check Server Health` | Verify server connection |
