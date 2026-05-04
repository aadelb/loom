"""Load testing configuration for Loom MCP server.

Defines test data, expected thresholds, and performance targets.
"""

from __future__ import annotations

# Sample search queries for load testing
TEST_QUERIES: list[str] = [
    "machine learning best practices",
    "python async programming",
    "database optimization techniques",
    "API design patterns",
    "cloud architecture",
    "DevOps automation",
    "security vulnerability assessment",
    "performance profiling",
    "distributed systems",
    "containerization with Docker",
    "Kubernetes orchestration",
    "microservices architecture",
    "GraphQL vs REST",
    "CI/CD pipelines",
    "monitoring and observability",
    "testing strategies",
    "code review best practices",
    "refactoring techniques",
    "design patterns",
    "SOLID principles",
]

# Test URLs for fetch operations
TEST_URLS: list[str] = [
    "https://example.com",
    "https://www.wikipedia.org/wiki/Computer_Science",
    "https://github.com/explore",
    "https://stackoverflow.com/questions",
    "https://dev.to",
    "https://medium.com",
    "https://docs.python.org",
    "https://www.python.org/about",
    "https://news.ycombinator.com",
    "https://www.reddit.com/r/programming",
]

# Expected response time thresholds (milliseconds)
RESPONSE_TIME_THRESHOLDS: dict[str, float] = {
    "health": 100.0,          # Health checks must be < 100ms
    "search": 5000.0,         # Search < 5 seconds
    "fetch": 10000.0,         # Fetch < 10 seconds
    "deep_research": 30000.0, # Deep research < 30 seconds
    "analytics": 2000.0,      # Analytics < 2 seconds
}

# Performance targets for load test
PERFORMANCE_TARGETS: dict[str, dict[str, float]] = {
    "health": {
        "p50": 50.0,           # 50th percentile < 50ms
        "p95": 100.0,          # 95th percentile < 100ms
        "p99": 150.0,          # 99th percentile < 150ms
    },
    "search": {
        "p50": 2000.0,         # 50th percentile < 2 seconds
        "p95": 4000.0,         # 95th percentile < 4 seconds
        "p99": 5000.0,         # 99th percentile < 5 seconds
    },
    "fetch": {
        "p50": 5000.0,         # 50th percentile < 5 seconds
        "p95": 8000.0,         # 95th percentile < 8 seconds
        "p99": 10000.0,        # 99th percentile < 10 seconds
    },
    "deep_research": {
        "p50": 15000.0,        # 50th percentile < 15 seconds
        "p95": 25000.0,        # 95th percentile < 25 seconds
        "p99": 30000.0,        # 99th percentile < 30 seconds
    },
    "analytics": {
        "p50": 800.0,          # 50th percentile < 800ms
        "p95": 1500.0,         # 95th percentile < 1500ms
        "p99": 2000.0,         # 99th percentile < 2 seconds
    },
}

# Load test parameters
LOAD_TEST_PARAMS: dict[str, int | str] = {
    "users": 50,                      # Number of concurrent users
    "spawn_rate": 10,                 # Users to spawn per second
    "run_time": 60,                   # Duration in seconds
    "host": "http://localhost:8787",  # Server URL
}

# HTTP status codes considered successful
SUCCESS_STATUS_CODES: list[int] = [200, 201, 202, 204, 206]

# HTTP status codes that indicate errors
ERROR_STATUS_CODES: list[int] = [400, 401, 403, 404, 500, 502, 503, 504]

# Rate limiting expectations
RATE_LIMIT_EXPECTATIONS: dict[str, dict[str, int]] = {
    "per_second": {
        "health": 1000,        # 1000 req/sec per user (no rate limit)
        "search": 10,          # 10 req/sec per user
        "fetch": 5,            # 5 req/sec per user
        "deep_research": 2,    # 2 req/sec per user
    },
}
