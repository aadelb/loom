"""Backend service configuration for gateway routing."""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["BackendConfig", "get_backend_config"]


@dataclass(frozen=True)
class BackendService:
    """Configuration for a single backend service."""

    name: str
    """Service name (e.g., 'core', 'redteam', 'intel')."""

    url: str
    """Backend service URL (e.g., 'http://127.0.0.1:8787')."""

    enabled: bool = True
    """Whether this backend is active."""

    timeout_seconds: int = 30
    """Request timeout in seconds."""

    tool_prefixes: list[str] | None = None
    """Optional list of tool name prefixes routed to this backend.

    Examples: ['research_', 'gateway_']
    If None, no prefix filtering is applied.
    """


@dataclass(frozen=True)
class BackendConfig:
    """Configuration for all backend services."""

    services: dict[str, BackendService]
    """Mapping of service name to BackendService."""

    default_service: str = "core"
    """Default backend when tool prefix doesn't match any service."""

    def get_service(self, tool_name: str) -> BackendService | None:
        """Resolve backend service for a given tool name.

        Args:
            tool_name: Tool name to resolve (e.g., 'research_fetch')

        Returns:
            BackendService if found, None otherwise.
        """
        # First try prefix matching
        for service in self.services.values():
            if service.enabled and service.tool_prefixes:
                for prefix in service.tool_prefixes:
                    if tool_name.startswith(prefix):
                        return service

        # Fall back to default service
        default = self.services.get(self.default_service)
        return default if default and default.enabled else None


def get_backend_config() -> BackendConfig:
    """Load backend configuration from environment or defaults.

    Environment variables:
    - LOOM_GATEWAY_BACKEND_URL: Primary backend URL (default: http://127.0.0.1:8787)
    - LOOM_GATEWAY_TIMEOUT: Request timeout in seconds (default: 30)

    Returns:
        Configured BackendConfig instance.
    """
    backend_url = os.environ.get(
        "LOOM_GATEWAY_BACKEND_URL",
        "http://127.0.0.1:8787",
    )
    timeout_seconds = int(os.environ.get("LOOM_GATEWAY_TIMEOUT", "30"))

    # For now, all routes go to the same backend
    # Future: Add support for multiple backends via env config
    core_service = BackendService(
        name="core",
        url=backend_url,
        enabled=True,
        timeout_seconds=timeout_seconds,
        tool_prefixes=None,  # Accept all tools
    )

    return BackendConfig(
        services={
            "core": core_service,
            "redteam": core_service,  # Alias to core for now
            "intel": core_service,     # Alias to core for now
            "infra": core_service,     # Alias to core for now
        },
        default_service="core",
    )
