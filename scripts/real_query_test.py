#!/usr/bin/env python3
"""Real query test script for Loom MCP tools.

Tests ALL Loom MCP tools with realistic Dubai wealth-building queries.
Connects to the Loom MCP server at http://127.0.0.1:8787/mcp, discovers
all available tools, generates smart parameters based on their schemas,
and tracks success/failure/timing.

Output: JSON report at ./real_query_test_report.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any, Literal

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("real_query_test")

# Realistic Dubai wealth-building queries
DUBAI_QUERIES = [
    "Dubai free zone business setup 2026",
    "UAE golden visa investment requirements",
    "Dubai real estate ROI 2024-2025",
    "cryptocurrency trading regulations Dubai",
    "high net worth individual services UAE",
    "offshore company formation Dubai 2026",
    "Dubai stock market investment opportunities",
    "private equity firms in UAE",
    "forex trading Dubai regulations",
    "luxury property investment Dubai",
    "startup funding programs UAE 2026",
    "import export business Dubai setup",
    "tourism business opportunities Dubai",
    "UAE visa sponsorship investment",
    "Dubai business license fees 2026",
]

# Real URLs for Dubai business context
DUBAI_URLS = [
    "https://www.khaleejtimes.com/business",
    "https://gulfnews.com/business",
    "https://www.arabnews.com/middle-east",
    "https://www.thenational.ae/business",
    "https://www.dubaichamber.ae",
    "https://invest.dubai.ae",
]

# Real domain names for Dubai
DUBAI_DOMAINS = [
    "khaleejtimes.com",
    "gulfnews.com",
    "dubaichamber.ae",
    "dubailand.gov.ae",
    "arabnews.com",
]

# Target hosts for security testing
TARGET_HOSTS = [
    "dubai.gov.ae",
    "invest.dubai.ae",
    "www.dubaichamber.ae",
]


@dataclass
class ToolResult:
    """Result from a single tool call."""

    tool_name: str
    status: Literal["OK", "ERROR", "TIMEOUT", "SKIP"]
    response_size: int
    error_detail: str | None
    time_ms: int
    response_sample: str | None = None


class LoopMCPClient:
    """Client for Loom MCP server via streamable-http."""

    def __init__(self, base_url: str = "http://127.0.0.1:8787/mcp"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
        self.request_id = 0
        self.session_id: str | None = None
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    async def initialize(self) -> bool:
        """Initialize MCP session."""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "loom-test", "version": "1.0"},
            },
        }
        try:
            response = await self.client.post(self.base_url, json=payload, headers=self._headers)
            response.raise_for_status()
            self.session_id = response.headers.get("mcp-session-id")
            if self.session_id:
                self._headers["Mcp-Session-Id"] = self.session_id
            logger.info(f"MCP session initialized: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MCP session: {e}")
            return False

    async def list_tools(self) -> dict[str, Any]:
        """List all available tools and their schemas."""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/list",
            "params": {},
        }

        try:
            response = await self.client.post(self.base_url, json=payload, headers=self._headers)
            response.raise_for_status()
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return {}

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout_sec: int = 60
    ) -> tuple[bool, dict[str, Any], int]:
        """Call a tool and return (success, result, elapsed_ms)."""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        start = time.time()
        try:
            response = await asyncio.wait_for(
                self.client.post(self.base_url, json=payload, headers=self._headers, timeout=timeout_sec),
                timeout=timeout_sec + 5,
            )
            response.raise_for_status()

            result = self._parse_response(response)
            elapsed_ms = int((time.time() - start) * 1000)

            if "error" in result and "result" not in result:
                return (False, result, elapsed_ms)
            return (True, result, elapsed_ms)
        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start) * 1000)
            return (False, {"error": "TIMEOUT"}, elapsed_ms)
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            return (False, {"error": str(e)}, elapsed_ms)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        """Parse response (SSE or direct JSON)."""
        content_type = response.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            lines = response.text.strip().split("\n")
            for line in reversed(lines):
                if line.startswith("data: "):
                    try:
                        return json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
            return {"error": "Failed to parse SSE response"}
        else:
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"error": "Invalid response format", "raw": response.text[:200]}


TOOL_SPECIFIC_PARAMS: dict[str, dict[str, Any]] = {
    "research_email_report": {
        "to": "ahmedalderai22@gmail.com",
        "subject": "[LOOM TEST] Dubai Wealth Research Report",
        "body": "This is an automated test from Loom MCP tool validation suite.",
    },
    "research_joplin_create": {
        "title": "Loom Test Note - Dubai Research",
        "body": "Automated test note from Loom validation suite.",
    },
    "research_joplin_search": {
        "query": "Dubai research",
    },
    "research_cicd_run": {
        "pipeline": "test",
        "dry_run": True,
    },
    "research_llm_translate": {
        "text": "Dubai offers numerous opportunities for wealth building through real estate investments and free zone business setup.",
        "target_language": "ar",
    },
    "research_screenshot": {
        "url": "https://www.khaleejtimes.com/business",
    },
    "research_nodriver_fetch": {
        "url": "https://www.khaleejtimes.com/business",
    },
    "research_stealth_browser": {
        "url": "https://www.khaleejtimes.com/business",
    },
    "research_paginate_scrape": {
        "url": "https://gulfnews.com/business",
        "max_pages": 2,
    },
    "research_js_intel": {
        "url": "https://invest.dubai.ae",
    },
    "research_photon_crawl": {
        "target": "https://www.dubaichamber.ae",
        "depth": 1,
    },
    "research_smart_extract": {
        "url": "https://www.khaleejtimes.com/business",
        "instruction": "Extract business headlines about Dubai economy",
    },
    "research_misinfo_check": {
        "claim": "Dubai has no income tax for individuals",
    },
    "research_deep": {
        "query": "Dubai golden visa investment requirements 2026",
    },
    "research_parameter_sweep": {
        "target": "https://www.khaleejtimes.com",
        "sweep_type": "full",
    },
    "research_audit_export": {
        "format": "json",
    },
    "research_model_comparator": {
        "prompt": "What are the best investment opportunities in Dubai?",
        "endpoints": ["https://integrate.api.nvidia.com/v1/chat/completions"],
    },
    "research_target_orchestrate": {
        "query": "Dubai free zone business setup guide",
        "targets": {"hcs": 7.0, "stealth": 5.0},
    },
    "research_data_poisoning": {
        "target_url": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
    "research_constraint_optimize": {
        "prompt": "How to set up an offshore company in Dubai DIFC",
        "constraints": {"hcs": {"min": 7.0}, "stealth": {"min": 5.0}},
    },
    "research_daisy_chain": {
        "query": "What are the best investment funds in Dubai for high net worth individuals?",
    },
    "research_data_fabrication": {
        "numbers": [1.2, 3.4, 5.6, 7.8, 9.0, 2.1, 4.3, 6.5],
    },
}


def generate_smart_params(tool_name: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Generate realistic parameters based on tool name and schema.

    This function intelligently maps tool schemas to realistic Dubai-related
    parameters without random strings.
    """
    # Check for tool-specific overrides first
    if tool_name in TOOL_SPECIFIC_PARAMS:
        return TOOL_SPECIFIC_PARAMS[tool_name]

    params = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for param_name, param_schema in properties.items():
        param_type = param_schema.get("type")
        is_required = param_name in required

        # Skip optional params we don't have smart values for
        if not is_required:
            continue

        # String parameters
        if param_type == "string":
            description = param_schema.get("description", "").lower()
            enum_values = param_schema.get("enum", [])

            if enum_values:
                # Use first enum value
                params[param_name] = enum_values[0]
            elif "url" in description or "domain" in description or param_name in [
                "url",
                "target",
                "domain",
            ]:
                if param_name == "domain":
                    params[param_name] = DUBAI_DOMAINS[0]
                elif "target" in param_name:
                    params[param_name] = TARGET_HOSTS[0]
                else:
                    params[param_name] = DUBAI_URLS[0]
            elif "query" in param_name or "search" in description or "prompt" in param_name:
                params[param_name] = DUBAI_QUERIES[0]
            elif "topic" in param_name or "subject" in param_name:
                params[param_name] = "Dubai wealth building and investment strategies 2026"
            elif "email" in param_name:
                params[param_name] = "investor@example.com"
            elif "username" in param_name or "user" in param_name:
                params[param_name] = "dubai_investor_2026"
            elif "company" in param_name or "organization" in param_name:
                params[param_name] = "Emaar Properties"
            elif "role" in param_name or "position" in param_name:
                params[param_name] = "Investment Manager"
            elif "address" in param_name:
                # Bitcoin address for crypto tools
                params[param_name] = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
            elif "text" in param_name or "content" in param_name or "description" in param_name:
                params[param_name] = (
                    "Dubai offers numerous opportunities for wealth building through "
                    "real estate, free zones, and investment vehicles. The UAE Golden Visa "
                    "program requires a minimum investment of AED 2 million in property or "
                    "AED 10 million in a public investment fund. Free zone businesses offer "
                    "100% foreign ownership with no corporate tax for qualifying activities."
                )
            elif "provider" in param_name:
                if "llm" in tool_name.lower() or "ask" in tool_name.lower():
                    params[param_name] = "nvidia"
                else:
                    params[param_name] = "exa"
            elif "session" in param_name:
                params[param_name] = "default_session"
            elif "mode" in param_name:
                # Pick first enum value if available
                if enum_values:
                    params[param_name] = enum_values[0]
            elif "language" in param_name:
                params[param_name] = "en"
            else:
                # Generic string default
                params[param_name] = f"test_{param_name}"

        # Integer parameters
        elif param_type == "integer":
            if param_name in ["n", "max_results", "limit"]:
                params[param_name] = 10
            elif param_name in ["timeout", "max_chars", "max_chars_each"]:
                params[param_name] = 30 if "timeout" in param_name else 5000
            elif param_name in ["retries"]:
                params[param_name] = 0
            else:
                # Default reasonable integer
                params[param_name] = 1

        # Boolean parameters
        elif param_type == "boolean":
            params[param_name] = False

        # Array parameters
        elif param_type == "array":
            items_schema = param_schema.get("items", {})
            if param_name in ["urls", "url_list"]:
                params[param_name] = DUBAI_URLS[:3]
            elif param_name in ["domains", "include_domains"]:
                params[param_name] = DUBAI_DOMAINS[:2]
            elif param_name in ["exclude_domains"]:
                params[param_name] = ["example.com"]
            elif items_schema.get("type") == "string":
                params[param_name] = ["value1"]
            else:
                params[param_name] = []

        # Object/dict parameters
        elif param_type == "object":
            if param_name in ["headers", "cookies"]:
                params[param_name] = {"User-Agent": "Mozilla/5.0"}
            else:
                params[param_name] = {}

    return params


async def test_all_tools(client: LoopMCPClient, max_concurrent: int = 10) -> list[ToolResult]:
    """Test all tools with smart parameter generation."""
    results: list[ToolResult] = []

    # Step 1: List all available tools
    logger.info("Fetching tool list from MCP server...")
    tools_response = await client.list_tools()

    if not tools_response or "result" not in tools_response:
        logger.error(f"Failed to get tools list: {tools_response}")
        return results

    tools_data = tools_response.get("result", {})
    all_tools = tools_data.get("tools", [])

    if not all_tools:
        logger.error("No tools found in MCP response")
        return results

    logger.info(f"Discovered {len(all_tools)} tools")

    # Step 2: Test tools in batches
    semaphore = asyncio.Semaphore(max_concurrent)

    async def test_tool_with_semaphore(tool: dict[str, Any]) -> ToolResult:
        """Test a single tool with concurrency control."""
        async with semaphore:
            return await test_single_tool(client, tool)

    # Create tasks for all tools
    tasks = [test_tool_with_semaphore(tool) for tool in all_tools]

    # Run with progress tracking
    logger.info(f"Testing {len(tasks)} tools (max {max_concurrent} concurrent)...")
    for i, future in enumerate(asyncio.as_completed(tasks), 1):
        result = await future
        results.append(result)
        status_icon = "✓" if result.status == "OK" else "✗"
        logger.info(
            f"[{i}/{len(tasks)}] {status_icon} {result.tool_name} | "
            f"{result.status} | {result.time_ms}ms | {result.response_size} bytes"
        )

    return results


async def test_single_tool(client: LoopMCPClient, tool: dict[str, Any]) -> ToolResult:
    """Test a single tool with smart parameter generation."""
    tool_name = tool.get("name", "unknown")
    input_schema = tool.get("inputSchema", {})

    logger.debug(f"Testing tool: {tool_name}")

    try:
        # Generate smart parameters
        params = generate_smart_params(tool_name, input_schema)

        # Skip tools that require special handling we can't provide
        if _should_skip_tool(tool_name, input_schema):
            return ToolResult(
                tool_name=tool_name,
                status="SKIP",
                response_size=0,
                error_detail="Tool requires unavailable resources or API keys",
                time_ms=0,
            )

        # Determine timeout based on tool type
        timeout_sec = _get_timeout_for_tool(tool_name)

        # Call the tool
        success, result, elapsed_ms = await client.call_tool(
            tool_name, params, timeout_sec=timeout_sec
        )

        if not success:
            error_detail = result.get("error", "Unknown error")
            return ToolResult(
                tool_name=tool_name,
                status="TIMEOUT" if "TIMEOUT" in str(error_detail) else "ERROR",
                response_size=0,
                error_detail=str(error_detail)[:200],
                time_ms=elapsed_ms,
            )

        # Extract response size
        result_str = json.dumps(result)
        response_size = len(result_str.encode("utf-8"))

        return ToolResult(
            tool_name=tool_name,
            status="OK",
            response_size=response_size,
            error_detail=None,
            time_ms=elapsed_ms,
            response_sample=result_str[:500],
        )

    except Exception as e:
        logger.error(f"Exception testing {tool_name}: {e}")
        return ToolResult(
            tool_name=tool_name,
            status="ERROR",
            response_size=0,
            error_detail=str(e)[:200],
            time_ms=0,
        )


def _should_skip_tool(tool_name: str, schema: dict[str, Any]) -> bool:
    """No tools skipped — test everything."""
    return False


def _get_timeout_for_tool(tool_name: str) -> int:
    """Get appropriate timeout for tool type — generous to avoid false timeouts."""
    tool_lower = tool_name.lower()

    # Very long-running tools (browser, multi-stage, crawls, all-models)
    if any(x in tool_lower for x in [
        "deep", "photon", "nodriver", "stealth_browser", "paginate",
        "screenshot", "js_intel", "ask_all_models", "ask_all_llms",
        "misinfo", "smart_extract", "spider", "markdown", "crawl",
        "benchmark", "dynamic", "realtime_monitor", "content_authenticity",
        "foia", "wiki_event", "info_half_life", "search_discrepancy",
        "salary_synthesize", "multilingual", "llm_translate",
    ]):
        return 180

    # Default: 90s for everything else (no tool should need less)
    return 90


async def main():
    """Main entry point."""
    client = LoopMCPClient()

    try:
        # Initialize MCP session
        if not await client.initialize():
            logger.error("Failed to initialize MCP session")
            sys.exit(1)

        # Run all tests
        results = await test_all_tools(client, max_concurrent=10)

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        ok_count = sum(1 for r in results if r.status == "OK")
        error_count = sum(1 for r in results if r.status == "ERROR")
        timeout_count = sum(1 for r in results if r.status == "TIMEOUT")
        skip_count = sum(1 for r in results if r.status == "SKIP")

        print(f"Total tools tested: {len(results)}")
        print(f"  OK:       {ok_count}")
        print(f"  ERROR:    {error_count}")
        print(f"  TIMEOUT:  {timeout_count}")
        print(f"  SKIP:     {skip_count}")

        # Timing stats
        ok_times = [r.time_ms for r in results if r.status == "OK"]
        if ok_times:
            avg_time = sum(ok_times) / len(ok_times)
            max_time = max(ok_times)
            min_time = min(ok_times)
            print(f"\nTiming (OK tools only):")
            print(f"  Average: {avg_time:.0f}ms")
            print(f"  Min:     {min_time}ms")
            print(f"  Max:     {max_time}ms")

        # Save JSON report
        report_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": {
                "total": len(results),
                "ok": ok_count,
                "error": error_count,
                "timeout": timeout_count,
                "skip": skip_count,
            },
            "tools": [asdict(r) for r in results],
        }

        report_path = "./real_query_test_report.json"
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
        print(f"\nReport saved to: {report_path}")

        # Exit with appropriate code
        sys.exit(0 if error_count == 0 and timeout_count == 0 else 1)

    finally:
        await client.client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
