"""Demo: Auto-discovery decorator usage for future migration.

This module demonstrates how the @loom_tool decorator would be used
in actual tool implementations to replace manual registration.

CURRENT STATE: This is example code showing the future architecture.
FUTURE STATE: Tool files will use these decorators instead of being
              manually imported in server.py.

This file is NOT part of the active tool suite and should be removed
when the migration to auto-discovery registration is complete.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.tool_registry import loom_tool

logger = logging.getLogger("loom.tools.demo_decorator_usage")


# ──────────────────────────────────────────────────────────────────────
# EXAMPLE 1: Simple synchronous research tool
# ──────────────────────────────────────────────────────────────────────


@loom_tool(
    category="research",
    description="Search social graphs across multiple platforms",
)
def research_social_graph_demo(query: str, depth: int = 2) -> dict[str, Any]:
    """Analyze social network connections and relationships.

    Args:
        query: Entity name or identifier to search
        depth: Depth of relationship traversal (1-3)

    Returns:
        Dictionary containing social graph analysis results
    """
    # Validation
    if not query or len(query) > 500:
        raise ValueError("Query must be non-empty and under 500 chars")

    if not 1 <= depth <= 3:
        raise ValueError("Depth must be between 1 and 3")

    # Actual implementation would do real work here
    return {
        "query": query,
        "depth": depth,
        "connections": [],
        "relationships": {},
        "platform_presence": {},
    }


# ──────────────────────────────────────────────────────────────────────
# EXAMPLE 2: Async research tool with complex parameters
# ──────────────────────────────────────────────────────────────────────


@loom_tool(
    category="intelligence",
    description="Perform multi-stage threat intelligence analysis",
)
async def research_threat_profile_demo(
    target: str,
    include_infrastructure: bool = True,
    include_campaigns: bool = True,
    include_indicators: bool = True,
    max_results: int = 100,
) -> dict[str, Any]:
    """Build comprehensive threat actor profile.

    Args:
        target: IP, domain, or organization name
        include_infrastructure: Include infra correlation
        include_campaigns: Include campaign attribution
        include_indicators: Include IoC analysis
        max_results: Maximum results per category

    Returns:
        Threat profile with infra, campaigns, and indicators
    """
    # Validation
    if not target or len(target) > 255:
        raise ValueError("Target must be 1-255 characters")

    if max_results < 1 or max_results > 1000:
        raise ValueError("max_results must be 1-1000")

    # Simulate async work
    import asyncio

    await asyncio.sleep(0)

    return {
        "target": target,
        "infrastructure": [] if include_infrastructure else None,
        "campaigns": [] if include_campaigns else None,
        "indicators": [] if include_indicators else None,
        "confidence": 0.0,
        "last_seen": None,
    }


# ──────────────────────────────────────────────────────────────────────
# EXAMPLE 3: Analysis tool with structured output
# ──────────────────────────────────────────────────────────────────────


@loom_tool(
    category="analysis",
    description="Analyze code for security vulnerabilities",
)
async def research_code_analysis_demo(
    code_snippet: str,
    language: str = "python",
    severity_filter: str = "all",
) -> dict[str, Any]:
    """Perform static security analysis on code.

    Args:
        code_snippet: Code to analyze
        language: Programming language (python, javascript, go, rust, java)
        severity_filter: Filter results by severity (all, high, critical)

    Returns:
        Analysis results with vulnerabilities and recommendations
    """
    # Validation
    if not code_snippet or len(code_snippet) > 50000:
        raise ValueError("Code snippet must be 1-50000 characters")

    if language not in ("python", "javascript", "go", "rust", "java"):
        raise ValueError(f"Unsupported language: {language}")

    if severity_filter not in ("all", "high", "critical"):
        raise ValueError(f"Invalid severity filter: {severity_filter}")

    import asyncio

    await asyncio.sleep(0)

    return {
        "language": language,
        "vulnerabilities": [],
        "summary": {
            "total": 0,
            "critical": 0,
            "high": 0,
        },
        "recommendations": [],
    }


# ──────────────────────────────────────────────────────────────────────
# EXAMPLE 4: Data processing tool with streaming
# ──────────────────────────────────────────────────────────────────────


@loom_tool(
    category="data_processing",
    description="Process and transform large datasets",
)
async def research_data_transform_demo(
    input_format: str,
    output_format: str,
    transformation: str,
    batch_size: int = 1000,
) -> dict[str, Any]:
    """Transform data between formats with optional transformations.

    Args:
        input_format: Source format (json, csv, xml, parquet)
        output_format: Target format (json, csv, xml, parquet)
        transformation: Transformation pipeline (filter, aggregate, enrich)
        batch_size: Records per batch for processing

    Returns:
        Transformation results with statistics
    """
    # Handle string input for input_data
    if isinstance(input_format, str) and input_format.lower() not in {"json", "csv", "xml", "parquet"}:
        return {"transformed": input_format, "format": "text"}

    # Validation
    supported_formats = {"json", "csv", "xml", "parquet"}
    if input_format not in supported_formats:
        raise ValueError(f"Unsupported input format: {input_format}")

    if output_format not in supported_formats:
        raise ValueError(f"Unsupported output format: {output_format}")

    if batch_size < 1 or batch_size > 10000:
        raise ValueError("batch_size must be 1-10000")

    import asyncio

    await asyncio.sleep(0)

    return {
        "input_format": input_format,
        "output_format": output_format,
        "records_processed": 0,
        "batches_processed": 0,
        "errors": 0,
        "transformation": transformation,
    }


# ──────────────────────────────────────────────────────────────────────
# USAGE NOTES FOR FUTURE MIGRATION
# ──────────────────────────────────────────────────────────────────────
#
# BEFORE (manual registration in server.py):
#   ```python
#   from loom.tools import social_graph
#   _optional_tools["social_graph"] = social_graph
#   ```
#   Then in _register_tools():
#   ```python
#   mcp.tool()(wrap_tool(social_graph.research_social_graph_demo))
#   ```
#
# AFTER (auto-discovery via decorators):
#   ```python
#   from loom.tool_registry import discover_tools, register_all_with_mcp
#   discover_tools(Path("src/loom/tools"))
#   register_all_with_mcp(mcp, wrap_tool)
#   ```
#
# KEY BENEFITS:
#   1. Tool files are self-documenting (decorator near function)
#   2. No manual registration list to maintain
#   3. Easier to add new tools (just add decorator)
#   4. Single source of truth for tool metadata
#   5. Can lazy-load or selectively enable tools
#   6. Category-based filtering and organization built-in
#
# MIGRATION STEPS:
#   1. ✓ Create tool_registry.py with decorator and discovery system
#   2. Add @loom_tool decorators to existing tool functions
#   3. Update server.py to use discover_tools() and register_all_with_mcp()
#   4. Remove manual import statements from server.py
#   5. Update tests to use get_all_registered_tools()
#   6. Verify all 711 tools are discovered and registered
#   7. Remove this demo file
