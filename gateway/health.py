"""Health aggregation and monitoring for gateway."""

from __future__ import annotations

import httpx
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("gateway.health")


@dataclass(frozen=True)
class ServiceHealth:
    """Health status of a single backend service."""

    name: str
    """Service name."""

    url: str
    """Service URL."""

    healthy: bool
    """Whether service is responding."""

    response_time_ms: float
    """Response time in milliseconds."""

    error: str | None = None
    """Error message if unhealthy."""

    timestamp: float = 0
    """When health check was performed."""


class HealthAggregator:
    """Aggregates health status from all backend services."""

    def __init__(self, config: Any) -> None:
        """Initialize health aggregator.

        Args:
            config: BackendConfig instance with service definitions.
        """
        self.config = config
        self._last_check: dict[str, ServiceHealth] = {}

    async def check_service(self, name: str, url: str, timeout: int = 5) -> ServiceHealth:
        """Check health of a single backend service.

        Args:
            name: Service name
            url: Service URL
            timeout: Request timeout in seconds

        Returns:
            ServiceHealth with status and metrics.
        """
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{url}/health")
                response.raise_for_status()

            elapsed_ms = (time.time() - start) * 1000
            health = ServiceHealth(
                name=name,
                url=url,
                healthy=True,
                response_time_ms=elapsed_ms,
                timestamp=time.time(),
            )
            logger.debug(
                "health_check_ok service=%s response_time_ms=%.1f",
                name,
                elapsed_ms,
            )
            return health

        except httpx.TimeoutException:
            elapsed_ms = (time.time() - start) * 1000
            health = ServiceHealth(
                name=name,
                url=url,
                healthy=False,
                response_time_ms=elapsed_ms,
                error="timeout",
                timestamp=time.time(),
            )
            logger.warning("health_check_timeout service=%s", name)
            return health

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            health = ServiceHealth(
                name=name,
                url=url,
                healthy=False,
                response_time_ms=elapsed_ms,
                error=str(e)[:100],
                timestamp=time.time(),
            )
            logger.warning("health_check_error service=%s error=%s", name, str(e)[:50])
            return health

    async def check_all_services(self) -> dict[str, ServiceHealth]:
        """Check health of all configured backend services.

        Returns:
            Dict mapping service name to ServiceHealth.
        """
        results = {}
        for name, service in self.config.services.items():
            if service.enabled:
                health = await self.check_service(
                    name,
                    service.url,
                    timeout=service.timeout_seconds,
                )
                results[name] = health
                self._last_check[name] = health

        return results

    def get_aggregate_health(self) -> dict[str, Any]:
        """Get aggregate health status across all services.

        Returns:
            Dict with overall health and per-service details.
        """
        if not self._last_check:
            return {
                "status": "unknown",
                "healthy_count": 0,
                "unhealthy_count": 0,
                "services": {},
            }

        healthy_count = sum(1 for h in self._last_check.values() if h.healthy)
        unhealthy_count = len(self._last_check) - healthy_count

        return {
            "status": "healthy" if unhealthy_count == 0 else "degraded",
            "healthy_count": healthy_count,
            "unhealthy_count": unhealthy_count,
            "total_services": len(self._last_check),
            "services": {
                name: {
                    "healthy": h.healthy,
                    "response_time_ms": round(h.response_time_ms, 1),
                    "error": h.error,
                    "checked_at": h.timestamp,
                }
                for name, h in self._last_check.items()
            },
        }
