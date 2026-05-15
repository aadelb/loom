"""HTTP route registration for Loom MCP server.

Extracted from server.py create_app(). All routes are registered via
mcp.custom_route() decorator inside register_http_routes().
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from loom.server_state import (
    get_health_status,
    get_start_time,
    get_validation_error_count,
    get_startup_validation_result,
    is_prometheus_enabled,
)
from loom.tool_functions import _get_strategy_count

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.routes")


def register_http_routes(mcp: "FastMCP") -> None:
    """Register all HTTP routes on the FastMCP instance.

    Args:
        mcp: The FastMCP server instance to register routes on.
    """
    _prometheus_enabled = is_prometheus_enabled()

    @mcp.custom_route("/", methods=["GET"])
    async def root_endpoint(request: Request) -> JSONResponse:
        return JSONResponse({
            "service": "loom",
            "version": "3.0.0",
            "description": "Loom MCP Research Server — 885 tools, 957 strategies",
            "mcp_endpoint": "/mcp",
            "health_endpoint": "/health",
            "health_endpoint_v1": "/v1/health",
            "metrics_endpoint": "/metrics" if _prometheus_enabled else None,
            "metrics_endpoint_v1": "/v1/metrics" if _prometheus_enabled else None,
            "versions_endpoint": "/versions",
            "api_versions": ["v1"],
            "status": "running",
        })

    @mcp.custom_route("/health", methods=["GET"])
    async def health_endpoint(request: Request) -> JSONResponse:
        from loom.registrations import get_registration_stats

        uptime = int(time.time() - get_start_time())
        tool_count = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 885

        reg_stats = get_registration_stats()

        memory_mb = None
        try:
            import psutil
            memory_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
        except (ImportError, Exception):
            pass

        health_response = {
            "status": "healthy",
            "startup_validation_status": get_health_status(),
            "startup_validation_result": get_startup_validation_result(),
            "uptime_seconds": uptime,
            "tool_count": tool_count,
            "strategy_count": _get_strategy_count(),
            "registration_stats": reg_stats.get("registration_stats", {}),
            "optional_modules_loaded": reg_stats.get("optional_modules_loaded", 0),
            "import_failures": reg_stats.get("import_failures", []),
            "total_tools_loaded": reg_stats.get("total_loaded", 0),
            "total_tools_failed": reg_stats.get("total_failed", 0),
            "validation_errors_found": get_validation_error_count(),
            "prometheus_enabled": _prometheus_enabled,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if memory_mb is not None:
            health_response["memory_mb"] = memory_mb
        return JSONResponse(health_response)

    if _prometheus_enabled:
        @mcp.custom_route("/metrics", methods=["GET"])
        async def metrics_endpoint(request: Request) -> Response:
            from prometheus_client import generate_latest
            from loom.server import _PROMETHEUS_REGISTRY
            metrics_output = generate_latest(_PROMETHEUS_REGISTRY)
            return Response(
                content=metrics_output,
                media_type="text/plain; charset=utf-8; version=0.0.4",
            )
        log.info("prometheus_metrics_endpoint_registered")

    @mcp.custom_route("/versions", methods=["GET"])
    async def versions_endpoint(request: Request) -> JSONResponse:
        try:
            from loom.api_versioning import get_version_info
            return JSONResponse(get_version_info())
        except ImportError:
            return JSONResponse({
                "api_version": "v1",
                "server_version": "3.0.0",
                "mcp_version": "2024-11-05",
                "python_version": __import__("sys").version,
            })

    @mcp.custom_route("/v1/", methods=["GET"])
    async def v1_root_endpoint(request: Request) -> JSONResponse:
        return JSONResponse({
            "api_version": "v1",
            "service": "loom",
            "version": "3.0.0",
            "description": "Loom MCP Research Server — 885 tools, 957 strategies",
            "endpoints": {
                "health": "/v1/health",
                "metrics": "/v1/metrics" if _prometheus_enabled else None,
            },
            "status": "running",
        })

    @mcp.custom_route("/v1/health", methods=["GET"])
    async def v1_health_endpoint(request: Request) -> JSONResponse:
        from loom.registrations import get_registration_stats, get_registration_errors

        uptime = int(time.time() - get_start_time())
        tool_count = len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 885

        reg_stats = get_registration_stats()
        reg_errors = get_registration_errors()

        reg_health = reg_stats.get("health_status", "healthy")
        overall_status = "degraded" if reg_health == "degraded" else "healthy"

        memory_mb = None
        try:
            import psutil
            memory_mb = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
        except (ImportError, Exception):
            pass

        health_response = {
            "api_version": "v1",
            "status": overall_status,
            "registration_health": reg_health,
            "startup_validation_status": get_health_status(),
            "startup_validation_result": get_startup_validation_result(),
            "uptime_seconds": uptime,
            "tool_count": tool_count,
            "strategy_count": _get_strategy_count(),
            "registration_stats": reg_stats.get("registration_stats", {}),
            "optional_modules_loaded": reg_stats.get("optional_modules_loaded", 0),
            "import_failures": reg_stats.get("import_failures", []),
            "total_tools_loaded": reg_stats.get("total_loaded", 0),
            "total_tools_failed": reg_stats.get("total_failed", 0),
            "failure_rate_percent": reg_stats.get("failure_rate_percent", 0.0),
            "registration_errors": reg_errors,
            "validation_errors_found": get_validation_error_count(),
            "prometheus_enabled": _prometheus_enabled,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if memory_mb is not None:
            health_response["memory_mb"] = memory_mb
        return JSONResponse(health_response)

    @mcp.custom_route("/v1/health/deep", methods=["GET"])
    async def v1_health_deep_endpoint(request: Request) -> JSONResponse:
        try:
            from loom.tools.monitoring.health_deep import research_health_deep
            result = await research_health_deep()
            return JSONResponse(result)
        except Exception as e:
            log.error("health_deep_check_failed error=%s", str(e))
            return JSONResponse(
                {"status": "unhealthy", "error": "Deep health check failed", "details": type(e).__name__, "timestamp": datetime.now(UTC).isoformat()},
                status_code=500,
            )

    @mcp.custom_route("/health/deep", methods=["GET"])
    async def health_deep_endpoint(request: Request) -> JSONResponse:
        try:
            from loom.tools.monitoring.health_deep import research_health_deep
            result = await research_health_deep()
            return JSONResponse(result)
        except Exception as e:
            log.error("health_deep_check_failed error=%s", str(e))
            return JSONResponse(
                {"status": "unhealthy", "error": "Deep health check failed", "details": type(e).__name__, "timestamp": datetime.now(UTC).isoformat()},
                status_code=500,
            )

    if _prometheus_enabled:
        @mcp.custom_route("/v1/metrics", methods=["GET"])
        async def v1_metrics_endpoint(request: Request) -> Response:
            from prometheus_client import generate_latest
            from loom.server import _PROMETHEUS_REGISTRY
            metrics_output = generate_latest(_PROMETHEUS_REGISTRY)
            return Response(
                content=metrics_output,
                media_type="text/plain; charset=utf-8; version=0.0.4",
            )
        log.info("prometheus_metrics_v1_endpoint_registered")

    @mcp.custom_route("/openapi.json", methods=["GET"])
    async def openapi_endpoint(request: Request) -> JSONResponse:
        from loom.openapi_gen import get_openapi_spec
        try:
            spec = get_openapi_spec(mcp, bypass_cache=False)
            return JSONResponse(spec)
        except Exception as e:
            log.error("openapi_spec_generation_failed error=%s", e)
            return JSONResponse(
                {"error": "Failed to generate OpenAPI spec", "details": str(e)},
                status_code=500,
            )

    @mcp.custom_route("/docs", methods=["GET"])
    async def swagger_ui_endpoint(request: Request) -> Response:
        html = """<!DOCTYPE html>
<html>
  <head>
    <title>Loom API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
    <style>html{box-sizing:border-box;overflow:-moz-scrollbars-vertical;overflow-y:scroll}*,*:before,*:after{box-sizing:inherit}body{margin:0;padding:0}</style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
    <script>
      window.onload = function() {
        SwaggerUIBundle({
          url: "/openapi.json",
          dom_id: '#swagger-ui',
          presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
          layout: "BaseLayout",
          requestInterceptor: (request) => {
            const token = localStorage.getItem('api_token');
            if (token) request.headers['Authorization'] = `Bearer ${token}`;
            return request;
          }
        })
      }
    </script>
  </body>
</html>"""
        return Response(content=html, media_type="text/html")

    @mcp.custom_route("/redoc", methods=["GET"])
    async def redoc_endpoint(request: Request) -> Response:
        html = """<!DOCTYPE html>
<html>
  <head>
    <title>Loom API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>body{margin:0;padding:0}</style>
  </head>
  <body>
    <redoc spec-url="/openapi.json"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
  </body>
</html>"""
        return Response(content=html, media_type="text/html")

    @mcp.custom_route("/api/v1/tools", methods=["GET"])
    async def api_v1_tools(request: Request) -> JSONResponse:
        tools = {}
        if hasattr(mcp, "_tool_manager"):
            for name, tool in mcp._tool_manager._tools.items():
                tools[name] = {
                    "name": name,
                    "description": getattr(tool, "description", ""),
                }
        return JSONResponse({"tools": tools, "count": len(tools)})

    @mcp.custom_route("/api/v1/tools/{name}/info", methods=["GET"])
    async def api_v1_tool_info(request: Request) -> JSONResponse:
        import inspect
        name = request.path_params.get("name", "")
        if not hasattr(mcp, "_tool_manager") or name not in mcp._tool_manager._tools:
            return JSONResponse({"error": f"Tool '{name}' not found"}, status_code=404)
        tool = mcp._tool_manager._tools[name]
        func = getattr(tool, "fn", None)
        info: dict[str, Any] = {
            "name": name,
            "description": getattr(tool, "description", ""),
            "async": inspect.iscoroutinefunction(func) if func else False,
        }
        if func:
            sig = inspect.signature(func)
            info["parameters"] = {
                p.name: {
                    "type": p.annotation.__name__ if hasattr(p.annotation, "__name__") else str(p.annotation),
                    "default": str(p.default) if p.default is not inspect.Parameter.empty else None,
                    "required": p.default is inspect.Parameter.empty,
                }
                for p in sig.parameters.values()
            }
        return JSONResponse(info)

    @mcp.custom_route("/api/v1/tools/{name}", methods=["POST"])
    async def api_v1_tool_call(request: Request) -> JSONResponse:
        """Call any tool with JSON body: POST /api/v1/tools/{name} {"param1": "value"}"""
        import inspect
        name = request.path_params.get("name", "")
        if not hasattr(mcp, "_tool_manager") or name not in mcp._tool_manager._tools:
            return JSONResponse({"error": f"Tool '{name}' not found"}, status_code=404)
        tool = mcp._tool_manager._tools[name]
        func = getattr(tool, "fn", None)
        if func is None:
            return JSONResponse({"error": f"Tool '{name}' has no callable function"}, status_code=500)
        try:
            body = await request.json()
        except Exception:
            body = {}
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(**body)
            else:
                result = func(**body)
            if isinstance(result, dict):
                return JSONResponse(result)
            return JSONResponse({"result": str(result) if result is not None else None})
        except TypeError as e:
            return JSONResponse({"error": f"Invalid parameters: {e}"}, status_code=400)
        except Exception as e:
            return JSONResponse({"error": str(e)[:500]}, status_code=500)

    @mcp.custom_route("/api/v1/health", methods=["GET"])
    async def api_v1_health(request: Request) -> JSONResponse:
        return await health_endpoint(request)

    log.info("http_routes_registered count=16")
