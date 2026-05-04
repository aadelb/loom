"""API versioning support for backward compatibility.

Provides version management, middleware for adding version headers,
and configuration for available API versions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# API version registry with status information
API_VERSIONS = {
    "v1": {
        "status": "stable",
        "deprecated": False,
        "release_date": "2024-01-01",
        "description": "Initial stable API version",
    },
}

# Current default version when no version specified
DEFAULT_VERSION = "v1"


def get_version_info() -> dict[str, Any]:
    """Get information about available API versions.

    Returns:
        Dict with version registry and metadata
    """
    return {
        "default_version": DEFAULT_VERSION,
        "versions": API_VERSIONS,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def is_version_supported(version: str) -> bool:
    """Check if a given version is supported.

    Args:
        version: Version string (e.g., "v1")

    Returns:
        True if version is in registry, False otherwise
    """
    return version in API_VERSIONS


def get_version_status(version: str) -> dict[str, Any] | None:
    """Get status information for a specific version.

    Args:
        version: Version string (e.g., "v1")

    Returns:
        Version config dict or None if not found
    """
    return API_VERSIONS.get(version)


class VersionMiddleware:
    """ASGI middleware that adds API version headers to responses.

    Adds:
    - X-API-Version: The API version being used
    - Deprecation: true if the version is deprecated
    - Sunset: Date when deprecated version will be removed (if applicable)
    """

    def __init__(self, app: Any, version: str = DEFAULT_VERSION) -> None:
        """Initialize middleware.

        Args:
            app: The ASGI application to wrap
            version: Default version to use
        """
        self.app = app
        self.version = version if is_version_supported(version) else DEFAULT_VERSION

    async def __call__(self, scope: dict, receive: Any, send: Any) -> Any:
        """Process the request and add version headers to response.

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_version(message: dict) -> None:
            """Wrap send to inject version headers.

            Args:
                message: ASGI message dict
            """
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Add X-API-Version header
                headers.append(
                    (b"x-api-version", self.version.encode("utf-8"))
                )

                # Add deprecation header if version is deprecated
                version_info = get_version_status(self.version)
                if version_info and version_info.get("deprecated"):
                    headers.append((b"deprecation", b"true"))

                    # Add Sunset header if available
                    if "sunset_date" in version_info:
                        sunset = version_info["sunset_date"]
                        headers.append((b"sunset", sunset.encode("utf-8")))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_version)
