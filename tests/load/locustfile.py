"""Locust load testing configuration for Loom MCP server.

Simulates realistic user workloads with weighted task distributions.
"""

from __future__ import annotations

import random
from typing import Any

from locust import HttpUser, between, task

from config import TEST_QUERIES, TEST_URLS, RESPONSE_TIME_THRESHOLDS


class LoomUser(HttpUser):
    """Simulates a user interacting with Loom MCP server."""

    wait_time = between(1, 3)
    host = "http://localhost:8787"

    def on_start(self) -> None:
        """Initialize user session with API key header."""
        self.client.headers.update({
            "X-API-Key": "test-api-key",
            "Content-Type": "application/json",
        })

    @task(10)
    def health_check(self) -> None:
        """Lightweight health check endpoint (frequent, low latency expected)."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="GET /health",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

            # Assert response time < 100ms
            if response.elapsed.total_seconds() * 1000 > RESPONSE_TIME_THRESHOLDS["health"]:
                response.failure(
                    f"Health check exceeded {RESPONSE_TIME_THRESHOLDS['health']}ms "
                    f"(actual: {response.elapsed.total_seconds() * 1000:.2f}ms)"
                )

    @task(5)
    def search(self) -> None:
        """Search tool endpoint with random queries."""
        query = random.choice(TEST_QUERIES)
        payload = {
            "query": query,
            "limit": random.randint(5, 20),
            "providers": ["exa", "tavily"],
        }

        with self.client.post(
            "/tool",
            json={"tool": "research_search", "params": payload},
            catch_response=True,
            name="POST /tool (research_search)",
        ) as response:
            if response.status_code in (200, 202):
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")

            # Assert response time < 5000ms
            elapsed_ms = response.elapsed.total_seconds() * 1000
            if elapsed_ms > RESPONSE_TIME_THRESHOLDS["search"]:
                response.failure(
                    f"Search exceeded {RESPONSE_TIME_THRESHOLDS['search']}ms "
                    f"(actual: {elapsed_ms:.2f}ms)"
                )

    @task(3)
    def fetch(self) -> None:
        """Fetch tool endpoint with test URLs."""
        url = random.choice(TEST_URLS)
        payload = {
            "url": url,
            "escalate_on_cloudflare": True,
            "timeout": 30,
        }

        with self.client.post(
            "/tool",
            json={"tool": "research_fetch", "params": payload},
            catch_response=True,
            name="POST /tool (research_fetch)",
        ) as response:
            if response.status_code in (200, 202):
                response.success()
            else:
                response.failure(f"Fetch failed: {response.status_code}")

            # Assert response time < 10000ms (fetch is slower than search)
            elapsed_ms = response.elapsed.total_seconds() * 1000
            if elapsed_ms > RESPONSE_TIME_THRESHOLDS["fetch"]:
                response.failure(
                    f"Fetch exceeded {RESPONSE_TIME_THRESHOLDS['fetch']}ms "
                    f"(actual: {elapsed_ms:.2f}ms)"
                )

    @task(2)
    def deep_research(self) -> None:
        """Deep research tool endpoint (heaviest, slowest expected)."""
        query = random.choice(TEST_QUERIES)
        payload = {
            "query": query,
            "max_depth": 3,
            "include_sentiment": True,
        }

        with self.client.post(
            "/tool",
            json={"tool": "research_deep", "params": payload},
            catch_response=True,
            name="POST /tool (research_deep)",
        ) as response:
            if response.status_code in (200, 202):
                response.success()
            else:
                response.failure(f"Deep research failed: {response.status_code}")

            # Assert response time < 30000ms (heavy operation)
            elapsed_ms = response.elapsed.total_seconds() * 1000
            if elapsed_ms > RESPONSE_TIME_THRESHOLDS["deep_research"]:
                response.failure(
                    f"Deep research exceeded {RESPONSE_TIME_THRESHOLDS['deep_research']}ms "
                    f"(actual: {elapsed_ms:.2f}ms)"
                )

    @task(1)
    def analytics(self) -> None:
        """Analytics dashboard endpoint (lightweight but less frequent)."""
        with self.client.get(
            "/analytics",
            catch_response=True,
            name="GET /analytics",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Analytics failed: {response.status_code}")

            # Assert response time < 2000ms
            elapsed_ms = response.elapsed.total_seconds() * 1000
            if elapsed_ms > RESPONSE_TIME_THRESHOLDS["analytics"]:
                response.failure(
                    f"Analytics exceeded {RESPONSE_TIME_THRESHOLDS['analytics']}ms "
                    f"(actual: {elapsed_ms:.2f}ms)"
                )
