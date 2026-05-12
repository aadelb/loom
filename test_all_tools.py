#!/usr/bin/env python3
"""Comprehensive test script for ALL Loom tools (829+ tools).

This script dynamically discovers all registered tools and calls each one
with sensible default parameters, categorizing results by module and status.

Usage:
    python3 test_all_tools.py

Or with timeout:
    timeout 1800 python3 test_all_tools.py

Results saved to: /opt/research-toolbox/full_tool_test_report.json
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Load environment variables first
try:
    from dotenv import load_dotenv

    env_paths = [
        Path("/opt/research-toolbox/.env"),
        Path(".env"),
        Path(__file__).parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_all_tools")

# Test configuration
TOOL_TIMEOUT_SECS = 30
TOTAL_TIMEOUT_SECS = 1800  # 30 minutes
PROGRESS_INTERVAL = 10  # Print progress every N tools


class ToolTester:
    """Main test orchestrator for Loom tools."""

    def __init__(self):
        self.results = {
            "metadata": {
                "start_time": datetime.now(datetime.UTC).isoformat(),
                "total_tools_found": 0,
                "total_tested": 0,
                "total_skipped": 0,
                "total_ok": 0,
                "total_failed": 0,
                "total_timeout": 0,
            },
            "by_module": defaultdict(lambda: {
                "found": 0,
                "tested": 0,
                "skipped": 0,
                "ok": 0,
                "failed": 0,
                "timeout": 0,
                "tools": []
            }),
            "failures": [],
            "timeouts": [],
            "skipped": [],
        }
        self.start_time = time.time()
        self.tools_tested_count = 0

    def add_result(
        self,
        module: str,
        tool_name: str,
        status: str,
        error: str | None = None,
        duration_sec: float = 0.0
    ) -> None:
        """Record a tool test result."""
        module_stats = self.results["by_module"][module]
        module_stats["found"] += 1

        tool_record = {
            "name": tool_name,
            "status": status,
            "duration_sec": round(duration_sec, 2),
        }

        if status == "OK":
            self.results["metadata"]["total_ok"] += 1
            module_stats["ok"] += 1
            module_stats["tested"] += 1
            self.tools_tested_count += 1
        elif status == "SKIP":
            self.results["metadata"]["total_skipped"] += 1
            module_stats["skipped"] += 1
            self.results["skipped"].append({"module": module, "tool": tool_name})
        elif status == "TIMEOUT":
            self.results["metadata"]["total_timeout"] += 1
            module_stats["timeout"] += 1
            module_stats["tested"] += 1
            self.tools_tested_count += 1
            self.results["timeouts"].append({"module": module, "tool": tool_name})
            tool_record["error"] = error
        elif status == "FAIL":
            self.results["metadata"]["total_failed"] += 1
            module_stats["failed"] += 1
            module_stats["tested"] += 1
            self.tools_tested_count += 1
            self.results["failures"].append({
                "module": module,
                "tool": tool_name,
                "error": error
            })
            tool_record["error"] = error

        module_stats["tools"].append(tool_record)

        if self.tools_tested_count % PROGRESS_INTERVAL == 0:
            elapsed = time.time() - self.start_time
            logger.info(
                f"Progress: {self.tools_tested_count} tools tested, "
                f"{self.results['metadata']['total_ok']} OK, "
                f"{self.results['metadata']['total_failed']} FAIL, "
                f"{self.results['metadata']['total_timeout']} TIMEOUT "
                f"({elapsed:.1f}s elapsed)"
            )

    def discover_tools(self) -> dict[str, list[tuple[str, Callable]]]:
        """Dynamically discover all tool functions from loom.tools modules.

        Returns:
            dict mapping module_name -> list of (tool_name, tool_func) tuples
        """
        tools_by_module = defaultdict(list)
        tools_dir = Path(__file__).parent / "src" / "loom" / "tools"

        if not tools_dir.exists():
            logger.error(f"Tools directory not found: {tools_dir}")
            return tools_by_module

        logger.info(f"Scanning tools directory: {tools_dir}")

        # Discover all .py files in tools directory
        for py_file in sorted(tools_dir.glob("*.py")):
            module_name = py_file.stem

            # Skip private/special files
            if module_name.startswith("_") or module_name.startswith("."):
                continue

            try:
                mod = importlib.import_module(f"loom.tools.{module_name}")

                # Find all functions starting with research_ or tool_
                for name, obj in inspect.getmembers(mod, inspect.isfunction):
                    if name.startswith("research_") or name.startswith("tool_"):
                        tools_by_module[module_name].append((name, obj))
                        self.results["metadata"]["total_tools_found"] += 1

            except ImportError as e:
                logger.warning(f"Failed to import {module_name}: {e}")
            except Exception as e:
                logger.warning(f"Error scanning {module_name}: {e}")

        logger.info(
            f"Discovered {self.results['metadata']['total_tools_found']} tools "
            f"from {len(tools_by_module)} modules"
        )
        return tools_by_module

    def generate_params(self, func: Callable) -> tuple[dict[str, Any], bool]:
        """Generate sensible default parameters for a tool function.

        Returns:
            (params_dict, should_skip_bool)
        """
        sig = inspect.signature(func)
        params = {}
        skip = False

        for param_name, param in sig.parameters.items():
            # Skip 'self' and special params
            if param_name in ("self", "cls"):
                continue

            # If no default and no annotation, we may need to skip
            if param.default == inspect.Parameter.empty:
                # Try to infer from param name and annotation
                if param.annotation != inspect.Parameter.empty:
                    param_type = param.annotation
                else:
                    param_type = None

                # Check for required file/object parameters
                param_lower = param_name.lower()
                if any(x in param_lower for x in ["path", "file", "binary", "image", "audio", "bytes", "buffer", "stream"]):
                    skip = True
                    break

                # Skip unknown required types
                if param_type and param_type not in (str, int, bool, list, dict, float):
                    skip = True
                    break

                # Provide defaults based on parameter name
                if param_lower in ("query", "q", "text", "prompt", "search", "input", "keyword"):
                    params[param_name] = "how to build wealth in 2026"
                elif param_lower in ("url", "uri", "link", "endpoint"):
                    params[param_name] = "https://example.com"
                elif param_lower in ("domain", "hostname", "host"):
                    params[param_name] = "example.com"
                elif param_lower in ("email", "email_address"):
                    params[param_name] = "test@example.com"
                elif param_lower in ("provider", "search_provider", "llm_provider"):
                    params[param_name] = "exa"
                elif param_lower in ("model", "model_name", "llm_model"):
                    params[param_name] = "auto"
                elif param_lower in ("strategy", "strategies"):
                    if "strategy" in param_lower:
                        params[param_name] = "ethical_anchor"
                    else:
                        params[param_name] = ["ethical_anchor"]
                elif param_lower in ("target", "target_name", "target_url"):
                    params[param_name] = "example.com"
                elif param_lower in ("address", "wallet_address", "crypto_address"):
                    params[param_name] = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
                elif param_lower in ("mode", "method", "type"):
                    params[param_name] = "http"
                elif param_lower in ("depth", "level"):
                    params[param_name] = "standard"
                elif param_lower in ("sources", "include"):
                    params[param_name] = ["web"]
                elif param_lower in ("darkness_level",):
                    params[param_name] = 5
                elif param_lower in ("spectrum",):
                    params[param_name] = True
                elif param_lower in ("target_lang", "lang", "language"):
                    params[param_name] = "ar"
                elif param_lower in ("dry_run",):
                    params[param_name] = True
                elif param_type in (int, type(None)):
                    params[param_name] = 5
                elif param_type in (bool,):
                    params[param_name] = True
                elif param_type in (list,):
                    params[param_name] = []
                elif param_type in (dict,):
                    params[param_name] = {}
                else:
                    params[param_name] = "test input"

            else:
                # Has a default value - use it
                if param.default is not None and param.default != inspect.Parameter.empty:
                    params[param_name] = param.default

        return params, skip

    async def call_tool(
        self,
        module: str,
        tool_name: str,
        func: Callable,
        params: dict[str, Any]
    ) -> tuple[str, str | None, float]:
        """Call a single tool with timeout handling.

        Returns:
            (status_str, error_str_or_none, duration_secs)
        """
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(**params),
                    timeout=TOOL_TIMEOUT_SECS
                )
            else:
                result = func(**params)

            duration = time.time() - start
            return "OK", None, duration

        except asyncio.TimeoutError:
            duration = time.time() - start
            return "TIMEOUT", f"Timed out after {TOOL_TIMEOUT_SECS}s", duration

        except Exception as e:
            duration = time.time() - start
            error_str = f"{type(e).__name__}: {str(e)[:200]}"
            return "FAIL", error_str, duration

    async def test_all_tools(self) -> None:
        """Discover and test all tools."""
        tools_by_module = self.discover_tools()

        logger.info(f"Starting tool testing (timeout: {TOOL_TIMEOUT_SECS}s per tool)...")

        for module_name in sorted(tools_by_module.keys()):
            tools = tools_by_module[module_name]
            logger.info(f"Testing module '{module_name}' ({len(tools)} tools)...")

            for tool_name, func in tools:
                # Generate params for this tool
                params, should_skip = self.generate_params(func)

                if should_skip:
                    logger.debug(f"  SKIP {tool_name} (requires file/object params)")
                    self.add_result(module_name, tool_name, "SKIP")
                    continue

                # Test the tool
                try:
                    status, error, duration = await self.call_tool(
                        module_name, tool_name, func, params
                    )
                    self.add_result(module_name, tool_name, status, error, duration)

                    if status == "OK":
                        logger.debug(f"  OK {tool_name} ({duration:.2f}s)")
                    elif status == "TIMEOUT":
                        logger.warning(f"  TIMEOUT {tool_name}")
                    else:
                        logger.warning(f"  FAIL {tool_name}: {error}")

                except Exception as e:
                    logger.error(f"  EXCEPTION testing {tool_name}: {e}")
                    self.add_result(
                        module_name, tool_name, "FAIL",
                        f"Exception: {str(e)[:200]}"
                    )

    def finalize_results(self) -> None:
        """Finalize and compute metrics."""
        end_time = time.time()
        duration = end_time - self.start_time

        self.results["metadata"]["end_time"] = datetime.now(datetime.UTC).isoformat()
        self.results["metadata"]["duration_sec"] = round(duration, 2)

        total = self.results["metadata"]["total_tools_found"]
        ok = self.results["metadata"]["total_ok"]
        failed = self.results["metadata"]["total_failed"]
        timeout = self.results["metadata"]["total_timeout"]
        skipped = self.results["metadata"]["total_skipped"]

        if total > 0:
            pass_rate = (ok / total) * 100
            tested_rate = ((ok + failed + timeout) / total) * 100
        else:
            pass_rate = 0
            tested_rate = 0

        self.results["metadata"]["pass_rate_percent"] = round(pass_rate, 2)
        self.results["metadata"]["tested_rate_percent"] = round(tested_rate, 2)

        # Convert defaultdict to regular dict for JSON serialization
        self.results["by_module"] = dict(self.results["by_module"])

    def print_summary(self) -> None:
        """Print a human-readable summary."""
        meta = self.results["metadata"]

        print("\n" + "=" * 80)
        print("LOOM COMPREHENSIVE TOOL TEST REPORT")
        print("=" * 80)
        print(f"\nTest Duration: {meta['duration_sec']}s")
        print(f"Start Time: {meta['start_time']}")
        print(f"End Time: {meta['end_time']}")

        print(f"\n{'SUMMARY':^80}")
        print("-" * 80)
        print(f"Total Tools Found:     {meta['total_tools_found']}")
        print(f"Total Tested:          {meta['total_ok'] + meta['total_failed'] + meta['total_timeout']}")
        print(f"Total Skipped:         {meta['total_skipped']}")
        print(f"\nResults:")
        print(f"  OK:                  {meta['total_ok']} ({(meta['total_ok']/meta['total_tools_found']*100 if meta['total_tools_found'] else 0):.1f}%)")
        print(f"  FAILED:              {meta['total_failed']}")
        print(f"  TIMEOUT:             {meta['total_timeout']}")
        print(f"\nPass Rate:             {meta['pass_rate_percent']}% ({meta['total_ok']}/{meta['total_tools_found']})")
        print(f"Tested Rate:           {meta['tested_rate_percent']}%")

        print(f"\n{'BY MODULE':^80}")
        print("-" * 80)
        for module in sorted(self.results["by_module"].keys()):
            stats = self.results["by_module"][module]
            found = stats["found"]
            ok = stats["ok"]
            failed = stats["failed"]
            timeout = stats["timeout"]
            skipped = stats["skipped"]
            pct = (ok / found * 100) if found else 0
            print(
                f"{module:30s} | "
                f"Found: {found:3d} | "
                f"OK: {ok:3d} ({pct:5.1f}%) | "
                f"Failed: {failed:2d} | "
                f"Timeout: {timeout:2d} | "
                f"Skipped: {skipped:2d}"
            )

        if self.results["failures"]:
            print(f"\n{'FAILURES':^80}")
            print("-" * 80)
            for failure in self.results["failures"][:20]:  # Show first 20
                print(f"{failure['module']}/{failure['tool']}:")
                print(f"  {failure['error'][:100]}")
            if len(self.results["failures"]) > 20:
                print(f"  ... and {len(self.results['failures']) - 20} more failures")

        if self.results["timeouts"]:
            print(f"\n{'TIMEOUTS':^80}")
            print("-" * 80)
            for timeout in self.results["timeouts"][:20]:  # Show first 20
                print(f"{timeout['module']}/{timeout['tool']}")
            if len(self.results["timeouts"]) > 20:
                print(f"  ... and {len(self.results['timeouts']) - 20} more timeouts")

        print("\n" + "=" * 80)

    def save_report(self, output_path: str | Path) -> None:
        """Save results to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Report saved to: {output_path}")


async def main():
    """Main entry point."""
    try:
        tester = ToolTester()
        await tester.test_all_tools()
        tester.finalize_results()
        tester.print_summary()

        # Save report
        output_path = Path("/opt/research-toolbox/full_tool_test_report.json")
        tester.save_report(output_path)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
