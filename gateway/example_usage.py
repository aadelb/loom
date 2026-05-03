"""Example usage and integration tests for Loom MCP Gateway.

This module demonstrates how to use the gateway in various scenarios.
Run with: python3 -m gateway.example_usage
"""

from __future__ import annotations

import asyncio
import httpx
from gateway.config import get_backend_config, BackendService
from gateway.router import ToolRouter
from gateway.health import HealthAggregator
from gateway.auth import GatewayAuthProvider


async def example_basic_config() -> None:
    """Example: Load and inspect backend configuration."""
    print("\n=== Example 1: Backend Configuration ===")
    config = get_backend_config()
    print(f"Default backend: {config.default_service}")
    print(f"Configured services: {list(config.services.keys())}")

    for name, service in config.services.items():
        print(f"  {name}: {service.url} (enabled={service.enabled})")

    # Resolve a tool to its backend
    backend = config.get_service("research_fetch")
    if backend:
        print(f"\nTool 'research_fetch' routes to: {backend.name} ({backend.url})")


async def example_router_resolution() -> None:
    """Example: Tool name resolution and routing."""
    print("\n=== Example 2: Tool Routing ===")
    config = get_backend_config()
    router = ToolRouter(config)

    tools_to_test = [
        "research_fetch",
        "research_spider",
        "gateway_status",
        "unknown_tool_xyz",
    ]

    for tool_name in tools_to_test:
        backend = await router.resolve_backend(tool_name)
        if backend:
            print(f"  {tool_name} → {backend.name} ({backend.url})")
        else:
            print(f"  {tool_name} → NO BACKEND FOUND")


async def example_health_check() -> None:
    """Example: Check health of backend services."""
    print("\n=== Example 3: Health Monitoring ===")
    config = get_backend_config()
    aggregator = HealthAggregator(config)

    # Check all services
    results = await aggregator.check_all_services()
    for name, health in results.items():
        status = "HEALTHY" if health.healthy else "UNHEALTHY"
        print(f"  {name}: {status} ({health.response_time_ms:.1f}ms)")
        if health.error:
            print(f"    Error: {health.error}")

    # Get aggregate health
    aggregate = aggregator.get_aggregate_health()
    print(f"\nAggregate status: {aggregate['status']}")
    print(f"  Healthy: {aggregate['healthy_count']}")
    print(f"  Unhealthy: {aggregate['unhealthy_count']}")


async def example_auth() -> None:
    """Example: Authentication token extraction and verification."""
    print("\n=== Example 4: Authentication ===")
    auth = GatewayAuthProvider()

    # Test Authorization header parsing
    headers_to_test = [
        "Bearer valid-token-123",
        "bearer lowercase-token",
        "Invalid-Format",
        "Bearer",
        "",
    ]

    for header in headers_to_test:
        token = auth.extract_bearer_token(header)
        print(f"  '{header}' → {token or 'INVALID'}")

    # Note: Actual token verification requires LOOM_API_KEY env var
    print("\n  (Token verification requires LOOM_API_KEY environment variable)")


async def example_mock_tool_call() -> None:
    """Example: Mock tool call flow (backend not required)."""
    print("\n=== Example 5: Tool Call Flow (Mock) ===")
    config = get_backend_config()
    router = ToolRouter(config)

    tool_name = "research_fetch"
    params = {"url": "https://example.com"}

    print(f"  Tool: {tool_name}")
    print(f"  Params: {params}")

    backend = await router.resolve_backend(tool_name)
    if backend:
        print(f"  → Resolved to backend: {backend.name}")
        print(f"  → Would POST to: {backend.url}/mcp")
        print(f"  → Request timeout: {backend.timeout_seconds}s")
        print("\n  (Actual call requires running backend)")
    else:
        print("  → No backend found!")

    await router.close()


async def example_config_env_override() -> None:
    """Example: Configuration from environment variables."""
    print("\n=== Example 6: Environment Configuration ===")
    import os

    print("  Current environment settings:")
    print(f"    LOOM_GATEWAY_BACKEND_URL: {os.environ.get('LOOM_GATEWAY_BACKEND_URL', 'http://127.0.0.1:8787')}")
    print(f"    LOOM_GATEWAY_HOST: {os.environ.get('LOOM_GATEWAY_HOST', '127.0.0.1')}")
    print(f"    LOOM_GATEWAY_PORT: {os.environ.get('LOOM_GATEWAY_PORT', '8800')}")
    print(f"    LOOM_GATEWAY_TIMEOUT: {os.environ.get('LOOM_GATEWAY_TIMEOUT', '30')}")
    print(f"    LOOM_API_KEY: {'SET' if os.environ.get('LOOM_API_KEY') else 'NOT SET'}")
    print(f"    LOG_LEVEL: {os.environ.get('LOG_LEVEL', 'INFO')}")


async def example_backend_service_structure() -> None:
    """Example: BackendService dataclass structure."""
    print("\n=== Example 7: Backend Service Structure ===")
    service = BackendService(
        name="core",
        url="http://127.0.0.1:8787",
        enabled=True,
        timeout_seconds=30,
        tool_prefixes=None,
    )
    print(f"  Service: {service.name}")
    print(f"  URL: {service.url}")
    print(f"  Enabled: {service.enabled}")
    print(f"  Timeout: {service.timeout_seconds}s")
    print(f"  Tool prefixes: {service.tool_prefixes}")
    print(f"  (Frozen dataclass - immutable)")


async def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("LOOM MCP GATEWAY - USAGE EXAMPLES")
    print("=" * 60)

    try:
        await example_basic_config()
        await example_router_resolution()
        await example_health_check()
        await example_auth()
        await example_mock_tool_call()
        await example_config_env_override()
        await example_backend_service_structure()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError in examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
