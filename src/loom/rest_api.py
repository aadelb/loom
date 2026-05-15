"""REST API wrapper for Loom tools.

Exposes all registered MCP tools as POST /api/v1/tools/{tool_name}
with JSON body for params. This allows testing with curl, Postman,
or any HTTP client without MCP framing.

Usage:
    Mount alongside the MCP app in run_loom_workers.py:
        from loom.rest_api import create_rest_app
        rest = create_rest_app(mcp_instance)
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger("loom.rest_api")


def create_rest_app(mcp: Any = None) -> Starlette:
    """Create a Starlette REST API wrapping all registered MCP tools."""

    _tool_registry: dict[str, Any] = {}

    def _discover_tools() -> None:
        """Build registry by importing all loom.tools modules."""
        if _tool_registry:
            return
        import importlib
        import pathlib

        tools_dir = pathlib.Path(__file__).parent / "tools"
        for f in sorted(tools_dir.iterdir()):
            if f.suffix == ".py" and not f.name.startswith("_"):
                mod_name = f.stem
                try:
                    m = importlib.import_module(f"loom.tools.{mod_name}")
                    for attr_name in dir(m):
                        if attr_name.startswith("research_"):
                            obj = getattr(m, attr_name)
                            if callable(obj) and not isinstance(obj, type):
                                _tool_registry[attr_name] = obj
                except Exception:
                    pass

        # Also add core tools from loom namespace
        core_modules = [
            "loom.sessions", "loom.config", "loom.orchestrator",
            "loom.scoring", "loom.unified_scorer",
        ]
        for mod_path in core_modules:
            try:
                m = importlib.import_module(mod_path)
                for attr_name in dir(m):
                    if attr_name.startswith("research_"):
                        obj = getattr(m, attr_name)
                        if callable(obj) and not isinstance(obj, type):
                            _tool_registry[attr_name] = obj
            except Exception:
                pass

        logger.info("REST API discovered %d tools", len(_tool_registry))

    async def list_tools(request: Request) -> JSONResponse:
        _discover_tools()
        tools = []
        for name, func in sorted(_tool_registry.items()):
            sig = inspect.signature(func)
            params = {}
            for pname, param in sig.parameters.items():
                ptype = str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                ptype = ptype.replace("typing.", "").replace("collections.abc.", "")
                default = None if param.default is inspect.Parameter.empty else repr(param.default)
                params[pname] = {"type": ptype, "default": default, "required": param.default is inspect.Parameter.empty}
            tools.append({
                "name": name,
                "async": inspect.iscoroutinefunction(func),
                "params": params,
            })
        return JSONResponse({"tools": tools, "count": len(tools)})

    async def call_tool(request: Request) -> JSONResponse:
        _discover_tools()
        tool_name = request.path_params["tool_name"]

        if tool_name not in _tool_registry:
            from difflib import get_close_matches
            suggestions = get_close_matches(tool_name, list(_tool_registry.keys()), n=3, cutoff=0.5)
            return JSONResponse(
                {"error": f"Tool '{tool_name}' not found", "suggestions": suggestions},
                status_code=404,
            )

        try:
            body = await request.json()
        except Exception:
            body = {}

        func = _tool_registry[tool_name]
        t0 = time.monotonic()

        try:
            if inspect.iscoroutinefunction(func):
                result = await func(**body)
            else:
                result = await asyncio.get_event_loop().run_in_executor(None, lambda: func(**body))
        except TypeError as e:
            sig = inspect.signature(func)
            params = {
                pname: {
                    "type": str(p.annotation) if p.annotation != inspect.Parameter.empty else "Any",
                    "required": p.default is inspect.Parameter.empty,
                }
                for pname, p in sig.parameters.items()
            }
            return JSONResponse(
                {"error": str(e), "expected_params": params},
                status_code=400,
            )
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return JSONResponse(
                {"error": str(e), "tool": tool_name},
                status_code=500,
            )

        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

        if isinstance(result, (dict, list, str, int, float, bool, type(None))):
            serializable = result
        else:
            serializable = str(result)

        return JSONResponse({
            "tool": tool_name,
            "result": serializable,
            "elapsed_ms": elapsed_ms,
        })

    async def tool_info(request: Request) -> JSONResponse:
        _discover_tools()
        tool_name = request.path_params["tool_name"]

        if tool_name not in _tool_registry:
            return JSONResponse({"error": f"Tool '{tool_name}' not found"}, status_code=404)

        func = _tool_registry[tool_name]
        sig = inspect.signature(func)
        params = {}
        for pname, param in sig.parameters.items():
            ptype = str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
            default = None if param.default is inspect.Parameter.empty else repr(param.default)
            params[pname] = {
                "type": ptype,
                "default": default,
                "required": param.default is inspect.Parameter.empty,
            }

        return JSONResponse({
            "name": tool_name,
            "async": inspect.iscoroutinefunction(func),
            "params": params,
            "docstring": (func.__doc__ or "").strip()[:500],
        })

    async def health(request: Request) -> JSONResponse:
        _discover_tools()
        return JSONResponse({
            "status": "ok",
            "tools_registered": len(_tool_registry),
            "api_version": "v1",
        })

    routes = [
        Route("/api/v1/health", health, methods=["GET"]),
        Route("/api/v1/tools", list_tools, methods=["GET"]),
        Route("/api/v1/tools/{tool_name}", call_tool, methods=["POST"]),
        Route("/api/v1/tools/{tool_name}/info", tool_info, methods=["GET"]),
    ]

    return Starlette(routes=routes)
