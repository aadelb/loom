#!/usr/bin/env bash
# Reproducible setup: expose Loom's MCP to the dockerised Hermes Agent and
# register it, so Hermes can call all Loom tools (research_last30days, paper
# research, quality_max, reframing, etc.) through a trusted MCP path.
#
# Why a bridge: the Hermes container sits on docker net `hermes-webui_hermes-net`
# (gateway 172.21.0.1) and cannot reach Loom on the host's 127.0.0.1:8788. Loom's
# MCP also rejects non-loopback Host headers (DNS-rebinding protection → 421).
# A Caddy L7 reverse-proxy on the gateway IP rewrites Host → 127.0.0.1:8788, so
# Loom stays bound to loopback (unchanged) and only the docker network can reach it.
#
# Run on the Hetzner host (the one running both loom-v3 and the Hermes containers).
# Author: Ahmed Adel Bakr Alderai
set -euo pipefail

GW="172.21.0.1"          # hermes-webui_hermes-net gateway (docker network inspect)
LOOM_PORT=8788

# 1. Caddy reverse-proxy on the docker gateway, Host-rewritten to loopback.
sudo mkdir -p /etc/caddy
sudo tee /etc/caddy/loom-bridge.Caddyfile >/dev/null <<EOF
{
	admin off
	auto_https off
}
http://${GW}:${LOOM_PORT} {
	bind ${GW}
	reverse_proxy 127.0.0.1:${LOOM_PORT} {
		header_up Host 127.0.0.1:${LOOM_PORT}
		flush_interval -1
	}
}
EOF

# 2. Persist as a systemd service.
sudo tee /etc/systemd/system/loom-hermes-bridge.service >/dev/null <<EOF
[Unit]
Description=Loom -> Hermes L7 bridge (Caddy, Host-rewrite ${GW}:${LOOM_PORT} -> 127.0.0.1:${LOOM_PORT})
After=network.target loom-v3.service

[Service]
ExecStart=/usr/bin/caddy run --config /etc/caddy/loom-bridge.Caddyfile --adapter caddyfile
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now loom-hermes-bridge.service

# 3. Register Loom as an MCP server in Hermes (no auth, enable all tools).
printf 'n\ny\n' | sudo docker exec -i hermes-agent \
	hermes mcp add loom --url "http://${GW}:${LOOM_PORT}/mcp"

# 4. Verify.
sudo docker exec hermes-agent hermes mcp list
echo "Done. Loom MCP available to Hermes; start a new Hermes session to use the tools."
