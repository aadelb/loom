"""FastMCP gateway server - lightweight proxy for distributed Loom backends.

The gateway:
1. Accepts MCP connections on port 8800
2. Validates JWT/API key tokens
3. Routes tool calls to appropriate backend services
4. Aggregates health status from all backends
5. Provides unified interface to clients

Run:
    python -m gateway.server
    OR: gateway-serve --host 0.0.0.0 --port 8800
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from mcp.server import FastMCP

from gateway.auth import GatewayAuthProvider
from gateway.config import get_backend_config
from gateway.health import HealthAggregator
from gateway.router import ToolRouter

logger = logging.getLogger("gateway.server")

_start_time = time.time()


def setup_logging(log_level: str = "INFO") -> None:
    """Set up structured logging for gateway.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def _validate_environment() -> None:
    """Validate required environment configuration."""
    backend_url = os.environ.get("LOOM_GATEWAY_BACKEND_URL", "http://127.0.0.1:8787")
    logger.info("environment_config LOOM_GATEWAY_BACKEND_URL=%s", backend_url)

    api_key = os.environ.get("LOOM_API_KEY", "")
    if api_key:
        logger.info("environment_config LOOM_API_KEY_LENGTH=%d", len(api_key))
    else:
        logger.warning(
            "environment_config LOOM_API_KEY not set, gateway will allow anonymous access"
        )


async def _health_check_loop(
    aggregator: HealthAggregator,
    interval_seconds: int = 30,
) -> None:
    """Background task to periodically check backend health.

    Args:
        aggregator: HealthAggregator instance
        interval_seconds: Interval between checks
    """
    logger.info("health_loop_started interval_seconds=%d", interval_seconds)
    try:
        while True:
            await asyncio.sleep(interval_seconds)
            await aggregator.check_all_services()
            health = aggregator.get_aggregate_health()
            logger.debug(
                "health_loop_check status=%s healthy=%d unhealthy=%d",
                health["status"],
                health["healthy_count"],
                health["unhealthy_count"],
            )
    except Exception as e:
        logger.error("health_loop_error error=%s", str(e))


def create_gateway_app() -> FastMCP:
    """Create and configure the gateway FastMCP server.

    Returns:
        Configured FastMCP instance ready to run.
    """
    # Set up environment
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    setup_logging(log_level)
    _validate_environment()

    # Load configuration
    config = get_backend_config()
    auth_provider = GatewayAuthProvider()
    router = ToolRouter(config)
    health_agg = HealthAggregator(config)

    # Create FastMCP gateway (no authentication yet, will add after creation)
    host = os.environ.get("LOOM_GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("LOOM_GATEWAY_PORT", "8800"))

    mcp = FastMCP(
        name="loom-gateway",
        host=host,
        port=port,
        stateless_http=True,
    )

    logger.info("gateway_server_created host=%s port=%d", host, port)

    # ── HTTP Endpoints ──

    @mcp.custom_route("/", methods=["GET"])
    async def root_endpoint(_: Any) -> dict[str, Any]:
        """Root endpoint with service info."""
        return {
            "service": "loom-gateway",
            "version": "1.0.0",
            "description": "Lightweight MCP gateway for distributed Loom backends",
            "mcp_endpoint": "/mcp",
            "health_endpoint": "/health",
            "status": "running",
            "uptime_seconds": int(time.time() - _start_time),
        }

    @mcp.custom_route("/health", methods=["GET"])
    async def health_endpoint(_: Any) -> dict[str, Any]:
        """Health check endpoint aggregating all backends."""
        # Do a quick synchronous health check
        health_status = health_agg.get_aggregate_health()
        return {
            "status": health_status["status"],
            "gateway": {
                "healthy": True,
                "uptime_seconds": int(time.time() - _start_time),
                "version": "1.0.0",
            },
            "backends": health_status["services"],
            "summary": {
                "total_backends": health_status["total_services"],
                "healthy_backends": health_status["healthy_count"],
                "unhealthy_backends": health_status["unhealthy_count"],
            },
        }

    @mcp.custom_route("/health/backends", methods=["POST"])
    async def health_check_backends(_: Any) -> dict[str, Any]:
        """Trigger immediate health check of all backends."""
        await health_agg.check_all_services()
        return health_agg.get_aggregate_health()

    # ── MCP Tools ──

    @mcp.tool()
    async def gateway_call(tool_name: str, **params: Any) -> dict[str, Any]:
        """Forward a tool call to the appropriate backend service.

        Args:
            tool_name: Name of the tool to call (e.g., 'research_fetch')
            **params: Tool parameters

        Returns:
            Response from the backend tool.
        """
        try:
            logger.info("gateway_call tool=%s param_count=%d", tool_name, len(params))
            result = await router.call_tool(tool_name, params)
            logger.info("gateway_call_success tool=%s", tool_name)
            return result
        except ValueError as e:
            logger.error("gateway_call_error tool=%s error=%s", tool_name, str(e))
            return {
                "error": str(e),
                "tool_name": tool_name,
            }
        except Exception as e:
            logger.error(
                "gateway_call_exception tool=%s error=%s",
                tool_name,
                str(e)[:100],
            )
            return {
                "error": f"Failed to call tool: {str(e)[:100]}",
                "tool_name": tool_name,
            }

    @mcp.tool()
    async def gateway_status() -> dict[str, Any]:
        """Get gateway and backend status.

        Returns:
            Status including uptime, backend health, and configuration.
        """
        health = health_agg.get_aggregate_health()
        return {
            "gateway": {
                "version": "1.0.0",
                "uptime_seconds": int(time.time() - _start_time),
                "configured_backends": len(config.services),
                "default_backend": config.default_service,
            },
            "backends": health["services"],
            "health_status": health["status"],
        }

    # ── Initialization ──

    logger.info("gateway_server_initialized with %d backends", len(config.services))

    return mcp


def main() -> None:
    """Main entry point for gateway server."""
    mcp = create_gateway_app()
    logger.info("gateway_server_starting")
    mcp.run()


if __name__ == "__main__":
    main()
