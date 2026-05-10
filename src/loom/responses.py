"""Unified response envelope for all Loom MCP tools.

Every tool's return value passes through _normalize_result() in middleware,
which ensures this shape is always present in the final response.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolResponse(BaseModel):
    """Standard response envelope for all MCP tools.

    Fields:
        results: The actual tool output (any type)
        total_count: Number of items in results (if list)
        source: Tool function name that produced this response
        category: Registration category of the tool
        elapsed_ms: Execution time in milliseconds
        cached: Whether this response came from cache
        error: Error message if tool failed (None on success)
        error_code: Machine-readable error classification
    """

    results: Any = None
    total_count: int = 0
    source: str = ""
    category: str = ""
    elapsed_ms: int = 0
    cached: bool = False
    error: str | None = None
    error_code: str | None = None

    model_config = {"extra": "allow"}
