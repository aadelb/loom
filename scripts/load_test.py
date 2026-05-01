#!/usr/bin/env python3
"""Comprehensive load test suite for Loom MCP server.

Stress-tests the MCP server to identify performance limits across:
1. Concurrent sessions (10, 20, 50, 100 simultaneous MCP sessions)
2. Throughput (100 rapid requests on single session)
3. Heavy tools (concurrent fetch, embed, reframe operations)
4. Sustained load (10 req/sec for 60 seconds)
5. Large payloads (100KB upload, 800KB response)

Generates JSON report: /opt/research-toolbox/tmp/load_test_results.json

Usage:
    PYTHONPATH=src python3 scripts/load_test.py               # full suite
    PYTHONPATH=src python3 scripts/load_test.py --quick       # fast subset
    PYTHONPATH=src python3 scripts/load_test.py --remote      # on Hetzner

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any
from statistics import median, stdev
from concurrent.futures import ThreadPoolExecutor

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("load_test")

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    status: int
    latency_ms: float
    timestamp: float
    success: bool
    error: str | None = None


@dataclass
class TestResult:
    """Results for a single test category."""
    name: str
    description: str
    status: str = "PASS"  # PASS, WARN, FAIL
    requests: list[RequestMetrics] = field(default_factory=list)
    duration_sec: float = 0.0
    error_message: str | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if not self.requests:
            return 0.0
        successes = sum(1 for r in self.requests if r.success)
        return (successes / len(self.requests)) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if not self.requests:
            return 0.0
        return sum(r.latency_ms for r in self.requests) / len(self.requests)

    @property
    def p50_latency_ms(self) -> float:
        """Calculate P50 latency."""
        if not self.requests:
            return 0.0
        latencies = sorted([r.latency_ms for r in self.requests])
        return latencies[len(latencies) // 2]

    @property
    def p95_latency_ms(self) -> float:
        """Calculate P95 latency."""
        if not self.requests:
            return 0.0
        latencies = sorted([r.latency_ms for r in self.requests])
        idx = int(len(latencies) * 0.95)
        return latencies[min(idx, len(latencies) - 1)]

    @property
    def p99_latency_ms(self) -> float:
        """Calculate P99 latency."""
        if not self.requests:
            return 0.0
        latencies = sorted([r.latency_ms for r in self.requests])
        idx = int(len(latencies) * 0.99)
        return latencies[min(idx, len(latencies) - 1)]

    @property
    def throughput_rps(self) -> float:
        """Calculate requests per second."""
        if self.duration_sec == 0:
            return 0.0
        return len(self.requests) / self.duration_sec

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "duration_sec": self.duration_sec,
            "request_count": len(self.requests),
            "success_rate": f"{self.success_rate:.1f}%",
            "throughput_rps": f"{self.throughput_rps:.2f}",
            "latency_ms": {
                "avg": f"{self.avg_latency_ms:.2f}",
                "p50": f"{self.p50_latency_ms:.2f}",
                "p95": f"{self.p95_latency_ms:.2f}",
                "p99": f"{self.p99_latency_ms:.2f}",
            },
            "error": self.error_message,
        }


class MCPClient:
    """Async MCP client for streamable-http transport."""

    def __init__(self, base_url: str = "http://127.0.0.1:8787"):
        self.base_url = base_url
        self.session_id: str | None = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def health_check(self) -> dict[str, Any]:
        """Call research_health_check tool."""
        return await self._call_tool("research_health_check", {})

    async def cache_stats(self) -> dict[str, Any]:
        """Call research_cache_stats tool."""
        return await self._call_tool("research_cache_stats", {})

    async def config_get(self, key: str = "LOG_LEVEL") -> dict[str, Any]:
        """Call research_config_get tool."""
        return await self._call_tool("research_config_get", {"key": key})

    async def fetch(self, url: str) -> dict[str, Any]:
        """Call research_fetch tool with URL."""
        return await self._call_tool("research_fetch", {
            "url": url,
            "use_scrapling": True,
        })

    async def text_analyze(self, text: str) -> dict[str, Any]:
        """Call research_text_analyze tool."""
        return await self._call_tool("research_text_analyze", {
            "text": text[:100000],  # Cap at 100KB
        })

    async def search(self, query: str) -> dict[str, Any]:
        """Call research_search tool."""
        return await self._call_tool("research_search", {
            "query": query,
            "provider": "brave",
            "limit": 5,
        })

    async def _call_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool via streamable-http."""
        try:
            response = await self.client.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": params,
                    },
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


class LoadTester:
    """Load testing orchestrator."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8787",
        output_path: str = "/opt/research-toolbox/tmp/load_test_results.json",
    ):
        self.base_url = base_url
        self.output_path = Path(output_path)
        self.results: list[TestResult] = []

    async def run_all_tests(self, quick: bool = False) -> None:
        """Run complete test suite."""
        logger.info("Starting Loom MCP load tests...")
        logger.info(f"Target: {self.base_url}")

        start_time = time.time()

        try:
            # Test 1: Concurrent Sessions
            await self.test_concurrent_sessions(quick)

            # Test 2: Throughput (rapid requests)
            await self.test_throughput(quick)

            # Test 3: Heavy Tools
            await self.test_heavy_tools(quick)

            # Test 4: Sustained Load
            await self.test_sustained_load(quick)

            # Test 5: Large Payloads
            await self.test_large_payloads(quick)

        except Exception as e:
            logger.error(f"Test suite failed: {e}", exc_info=True)
            self.results.append(TestResult(
                name="Suite Execution",
                description="Overall test suite execution",
                status="FAIL",
                error_message=str(e),
            ))

        total_duration = time.time() - start_time
        self._save_results(total_duration)

    async def test_concurrent_sessions(self, quick: bool = False) -> None:
        """Test 1: Open multiple concurrent MCP sessions."""
        logger.info("\n[TEST 1] Concurrent Sessions...")

        session_counts = [10, 20] if quick else [10, 20, 50, 100]
        result = TestResult(
            name="Concurrent Sessions",
            description="Test opening multiple simultaneous MCP sessions",
        )

        start_time = time.time()

        for count in session_counts:
            logger.info(f"  Testing {count} concurrent sessions...")
            clients = [MCPClient(self.base_url) for _ in range(count)]
            metrics = []

            try:
                tasks = [self._timed_health_check(c) for c in clients]
                metrics = await asyncio.gather(*tasks, return_exceptions=False)
                metrics = [m for m in metrics if isinstance(m, RequestMetrics)]

                logger.info(f"    {count} sessions: {len(metrics)} successful")

            except Exception as e:
                logger.error(f"    Error with {count} sessions: {e}")
            finally:
                await asyncio.gather(
                    *[c.close() for c in clients],
                    return_exceptions=True,
                )

            result.requests.extend(metrics)

        result.duration_sec = time.time() - start_time

        # Assess status
        if result.success_rate >= 95:
            result.status = "PASS"
        elif result.success_rate >= 80:
            result.status = "WARN"
        else:
            result.status = "FAIL"

        self.results.append(result)
        logger.info(f"  Result: {result.status} ({result.success_rate:.1f}% success)")

    async def test_throughput(self, quick: bool = False) -> None:
        """Test 2: Rapid requests on single session."""
        logger.info("\n[TEST 2] Throughput (Rapid Requests)...")

        request_count = 50 if quick else 100
        result = TestResult(
            name="Throughput",
            description=f"Fire {request_count} rapid requests on single session",
        )

        client = MCPClient(self.base_url)
        start_time = time.time()
        metrics = []

        try:
            tasks = [
                self._timed_cache_stats(client)
                for _ in range(request_count)
            ]
            metrics = await asyncio.gather(*tasks, return_exceptions=False)
            metrics = [m for m in metrics if isinstance(m, RequestMetrics)]

        except Exception as e:
            logger.error(f"  Throughput test failed: {e}")
            result.error_message = str(e)
            result.status = "FAIL"
        finally:
            await client.close()

        result.requests = metrics
        result.duration_sec = time.time() - start_time

        if result.success_rate >= 95 and result.throughput_rps >= 10:
            result.status = "PASS"
        elif result.success_rate >= 80 and result.throughput_rps >= 5:
            result.status = "WARN"
        else:
            result.status = "FAIL"

        self.results.append(result)
        logger.info(
            f"  Result: {result.status} ({result.throughput_rps:.2f} req/s, "
            f"{result.success_rate:.1f}% success)"
        )

    async def test_heavy_tools(self, quick: bool = False) -> None:
        """Test 3: Concurrent resource-intensive operations."""
        logger.info("\n[TEST 3] Heavy Tools (Resource-Intensive)...")

        result = TestResult(
            name="Heavy Tools",
            description="Concurrent fetch, search, and analysis operations",
        )

        client = MCPClient(self.base_url)
        start_time = time.time()
        metrics = []

        try:
            # Mix of heavy operations
            test_url = "https://example.com"
            test_query = "python programming"
            test_text = "x" * 50000  # 50KB text

            tasks = []

            # 5x fetch (network IO)
            if not quick:
                tasks.extend([
                    self._timed_fetch(client, test_url)
                    for _ in range(5)
                ])

            # 5x search (API + network)
            tasks.extend([
                self._timed_search(client, test_query)
                for _ in range(3 if quick else 5)
            ])

            # 5x text_analyze (CPU + processing)
            tasks.extend([
                self._timed_text_analyze(client, test_text)
                for _ in range(3 if quick else 5)
            ])

            metrics = await asyncio.gather(*tasks, return_exceptions=False)
            metrics = [m for m in metrics if isinstance(m, RequestMetrics)]

        except Exception as e:
            logger.error(f"  Heavy tools test failed: {e}")
            result.error_message = str(e)
            result.status = "FAIL"
        finally:
            await client.close()

        result.requests = metrics
        result.duration_sec = time.time() - start_time

        if result.success_rate >= 90:
            result.status = "PASS"
        elif result.success_rate >= 70:
            result.status = "WARN"
        else:
            result.status = "FAIL"

        self.results.append(result)
        logger.info(
            f"  Result: {result.status} ({len(metrics)} ops, "
            f"{result.success_rate:.1f}% success, "
            f"avg {result.avg_latency_ms:.0f}ms)"
        )

    async def test_sustained_load(self, quick: bool = False) -> None:
        """Test 4: Sustained load (10 req/sec for duration)."""
        logger.info("\n[TEST 4] Sustained Load...")

        duration = 10 if quick else 60  # seconds
        target_rps = 10
        interval = 1.0 / target_rps  # Time between requests

        result = TestResult(
            name="Sustained Load",
            description=f"Maintain {target_rps} req/sec for {duration} seconds",
        )

        client = MCPClient(self.base_url)
        start_time = time.time()
        metrics = []

        try:
            # Mix of fast and medium tools
            tools = [
                ("cache_stats", lambda: self._timed_cache_stats(client)),
                ("config_get", lambda: self._timed_config_get(client)),
                ("search", lambda: self._timed_search(client, "test")),
            ]

            request_count = 0
            while time.time() - start_time < duration:
                tool_name, tool_fn = tools[request_count % len(tools)]
                task = tool_fn()
                metric = await asyncio.wait_for(task, timeout=30.0)
                if isinstance(metric, RequestMetrics):
                    metrics.append(metric)
                request_count += 1

                # Sleep to maintain target RPS
                elapsed = time.time() - start_time
                expected_time = request_count * interval
                if elapsed < expected_time:
                    await asyncio.sleep(expected_time - elapsed)

        except asyncio.TimeoutError:
            logger.warning("  Some requests timed out during sustained load")
        except Exception as e:
            logger.error(f"  Sustained load test failed: {e}")
            result.error_message = str(e)
        finally:
            await client.close()

        result.requests = metrics
        result.duration_sec = time.time() - start_time

        actual_rps = len(metrics) / result.duration_sec if result.duration_sec > 0 else 0

        if result.success_rate >= 95 and actual_rps >= target_rps * 0.9:
            result.status = "PASS"
        elif result.success_rate >= 80 and actual_rps >= target_rps * 0.7:
            result.status = "WARN"
        else:
            result.status = "FAIL"

        self.results.append(result)
        logger.info(
            f"  Result: {result.status} ({actual_rps:.2f} actual req/s, "
            f"{result.success_rate:.1f}% success, "
            f"avg latency {result.avg_latency_ms:.0f}ms)"
        )

    async def test_large_payloads(self, quick: bool = False) -> None:
        """Test 5: Large request/response payloads."""
        logger.info("\n[TEST 5] Large Payloads...")

        result = TestResult(
            name="Large Payloads",
            description="Send 100KB request + receive large responses",
        )

        client = MCPClient(self.base_url)
        start_time = time.time()
        metrics = []

        try:
            # Test 1: Large text upload (100KB)
            large_text = "x" * (100 * 1024)  # 100KB
            logger.info("  Sending 100KB text payload...")
            metric = await self._timed_text_analyze(client, large_text)
            if isinstance(metric, RequestMetrics):
                metrics.append(metric)

            # Test 2: Multiple concurrent text analysis
            if not quick:
                tasks = [
                    self._timed_text_analyze(client, "y" * (50 * 1024))
                    for _ in range(3)
                ]
                batch_metrics = await asyncio.gather(*tasks, return_exceptions=False)
                metrics.extend([m for m in batch_metrics if isinstance(m, RequestMetrics)])

        except Exception as e:
            logger.error(f"  Large payload test failed: {e}")
            result.error_message = str(e)
            result.status = "FAIL"
        finally:
            await client.close()

        result.requests = metrics
        result.duration_sec = time.time() - start_time

        if result.success_rate >= 90:
            result.status = "PASS"
        elif result.success_rate >= 70:
            result.status = "WARN"
        else:
            result.status = "FAIL"

        self.results.append(result)
        logger.info(
            f"  Result: {result.status} ({len(metrics)} payloads, "
            f"{result.success_rate:.1f}% success)"
        )

    # Helper methods for timed execution

    async def _timed_health_check(self, client: MCPClient) -> RequestMetrics:
        """Execute health check and measure time."""
        start = time.time()
        try:
            result = await client.health_check()
            latency = (time.time() - start) * 1000
            success = "error" not in result
            return RequestMetrics(
                status=200 if success else 500,
                latency_ms=latency,
                timestamp=start,
                success=success,
                error=result.get("error") if not success else None,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RequestMetrics(
                status=500,
                latency_ms=latency,
                timestamp=start,
                success=False,
                error=str(e),
            )

    async def _timed_cache_stats(self, client: MCPClient) -> RequestMetrics:
        """Execute cache_stats and measure time."""
        start = time.time()
        try:
            result = await client.cache_stats()
            latency = (time.time() - start) * 1000
            success = "error" not in result
            return RequestMetrics(
                status=200 if success else 500,
                latency_ms=latency,
                timestamp=start,
                success=success,
                error=result.get("error") if not success else None,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RequestMetrics(
                status=500,
                latency_ms=latency,
                timestamp=start,
                success=False,
                error=str(e),
            )

    async def _timed_config_get(self, client: MCPClient) -> RequestMetrics:
        """Execute config_get and measure time."""
        start = time.time()
        try:
            result = await client.config_get()
            latency = (time.time() - start) * 1000
            success = "error" not in result
            return RequestMetrics(
                status=200 if success else 500,
                latency_ms=latency,
                timestamp=start,
                success=success,
                error=result.get("error") if not success else None,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RequestMetrics(
                status=500,
                latency_ms=latency,
                timestamp=start,
                success=False,
                error=str(e),
            )

    async def _timed_fetch(self, client: MCPClient, url: str) -> RequestMetrics:
        """Execute fetch and measure time."""
        start = time.time()
        try:
            result = await client.fetch(url)
            latency = (time.time() - start) * 1000
            success = "error" not in result
            return RequestMetrics(
                status=200 if success else 500,
                latency_ms=latency,
                timestamp=start,
                success=success,
                error=result.get("error") if not success else None,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RequestMetrics(
                status=500,
                latency_ms=latency,
                timestamp=start,
                success=False,
                error=str(e),
            )

    async def _timed_search(self, client: MCPClient, query: str) -> RequestMetrics:
        """Execute search and measure time."""
        start = time.time()
        try:
            result = await client.search(query)
            latency = (time.time() - start) * 1000
            success = "error" not in result
            return RequestMetrics(
                status=200 if success else 500,
                latency_ms=latency,
                timestamp=start,
                success=success,
                error=result.get("error") if not success else None,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RequestMetrics(
                status=500,
                latency_ms=latency,
                timestamp=start,
                success=False,
                error=str(e),
            )

    async def _timed_text_analyze(self, client: MCPClient, text: str) -> RequestMetrics:
        """Execute text_analyze and measure time."""
        start = time.time()
        try:
            result = await client.text_analyze(text)
            latency = (time.time() - start) * 1000
            success = "error" not in result
            return RequestMetrics(
                status=200 if success else 500,
                latency_ms=latency,
                timestamp=start,
                success=success,
                error=result.get("error") if not success else None,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RequestMetrics(
                status=500,
                latency_ms=latency,
                timestamp=start,
                success=False,
                error=str(e),
            )

    def _save_results(self, total_duration: float) -> None:
        """Save test results to JSON file."""
        # Determine overall status
        statuses = [r.status for r in self.results]
        if "FAIL" in statuses:
            overall_status = "FAIL"
        elif "WARN" in statuses:
            overall_status = "WARN"
        else:
            overall_status = "PASS"

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "total_duration_sec": total_duration,
            "test_results": [r.to_dict() for r in self.results],
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.status == "PASS"),
                "warned": sum(1 for r in self.results if r.status == "WARN"),
                "failed": sum(1 for r in self.results if r.status == "FAIL"),
            },
        }

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON
        with open(self.output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"\nResults saved to: {self.output_path}")
        logger.info(f"Overall Status: {overall_status}")
        logger.info(f"Summary: {report['summary']}")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Loom MCP load tester")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick subset of tests (faster)",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Connect to remote Hetzner server",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8787",
        help="MCP server URL (default: http://127.0.0.1:8787)",
    )
    parser.add_argument(
        "--output",
        default="/opt/research-toolbox/tmp/load_test_results.json",
        help="Output JSON file path",
    )

    args = parser.parse_args()

    if args.remote:
        args.url = "http://localhost:8787"  # Will be tunneled via SSH

    tester = LoadTester(base_url=args.url, output_path=args.output)
    await tester.run_all_tests(quick=args.quick)


if __name__ == "__main__":
    asyncio.run(main())
