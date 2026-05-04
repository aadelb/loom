# Loom API Reference v2

**Generated:** 2026-05-04  
**Version:** 4.0.0  
**Base URL:** `http://127.0.0.1:8787` (default, configurable via `LOOM_HOST` and `LOOM_PORT`)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health & Monitoring Endpoints](#health--monitoring-endpoints)
3. [API Discovery](#api-discovery)
4. [Infrastructure Tools](#infrastructure-tools)
5. [Research Tools](#research-tools)
6. [OSINT Tools](#osint-tools)
7. [Privacy Tools](#privacy-tools)
8. [EU AI Act Compliance Tools](#eu-ai-act-compliance-tools)
9. [Response Format & Error Handling](#response-format--error-handling)

---

## Authentication

### X-API-Key Header

All MCP tool calls through the HTTP interface require authentication via the `X-API-Key` header.

```
GET /tools
X-API-Key: your-api-key-here
```

**Configuration:**
- Set `LOOM_AUTH_REQUIRED=true` to enforce authentication globally
- Set `LOOM_API_KEY_HEADER=X-API-Key` to customize header name
- Store keys in environment variable `LOOM_VALID_KEYS` (comma-separated)

### Example Authentication Check

```python
# Client-side (Python)
import requests

headers = {
    "X-API-Key": "your-api-key-here",
    "Content-Type": "application/json"
}
response = requests.post(
    "http://127.0.0.1:8787/invoke/research_health_check",
    json={},
    headers=headers
)
```

---

## Health & Monitoring Endpoints

### GET /health

**Description:** Lightweight health check (does not make external API calls).

**Response Schema:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "uptime_seconds": 3600,
  "tool_count": 346,
  "strategy_count": 957,
  "llm_providers": {
    "groq": { "status": "up|down" },
    "nvidia_nim": { "status": "up|down" },
    "deepseek": { "status": "up|down" },
    "gemini": { "status": "up|down" },
    "moonshot": { "status": "up|down" },
    "openai": { "status": "up|down" },
    "anthropic": { "status": "up|down" },
    "vllm": { "status": "up|down" }
  },
  "search_providers": {
    "exa": { "status": "up|down" },
    "tavily": { "status": "up|down" },
    "firecrawl": { "status": "up|down" },
    "brave": { "status": "up|down" },
    "ddgs": { "status": "up|down" },
    "arxiv": { "status": "up|down" },
    "wikipedia": { "status": "up|down" },
    "hackernews": { "status": "up|down" },
    "reddit": { "status": "up|down" },
    "newsapi": { "status": "up|down" },
    "coindesk": { "status": "up|down" },
    "coinmarketcap": { "status": "up|down" },
    "binance": { "status": "up|down" },
    "ahmia": { "status": "up|down" },
    "darksearch": { "status": "up|down" },
    "ummro_rag": { "status": "up|down" },
    "onionsearch": { "status": "up|down" },
    "torcrawl": { "status": "up|down" },
    "darkweb_cti": { "status": "up|down" },
    "robin_osint": { "status": "up|down" },
    "investing": { "status": "up|down" }
  },
  "cache": {
    "entries": 1500,
    "size_mb": 245.6,
    "hit_rate": 0.87
  },
  "sessions": {
    "active": 3,
    "max": 10
  },
  "version": "4.0.0",
  "timestamp": "2026-05-04T12:34:56Z"
}
```

**Example Call:**
```bash
curl -X POST http://127.0.0.1:8787/invoke/research_health_check \
  -H "X-API-Key: test" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### POST /invoke/research_health_check

**Tool Name:** `research_health_check`

**Parameters:** None

**Returns:** Dict with comprehensive health status (same as /health endpoint)

**Example Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 7200,
  "tool_count": 346,
  "strategy_count": 957,
  "version": "4.0.0",
  "timestamp": "2026-05-04T12:35:00Z"
}
```

---

### POST /invoke/research_validate_startup

**Tool Name:** `research_validate_startup`

**Parameters:**
- `check_tools` (bool, optional): Validate all tool registrations (default: true)
- `check_providers` (bool, optional): Validate LLM/search provider availability (default: true)
- `verbose` (bool, optional): Include detailed error messages (default: false)

**Returns:**
```json
{
  "status": "valid|invalid|degraded",
  "validation_timestamp": "2026-05-04T12:35:00Z",
  "tools_validated": 346,
  "tools_ok": 340,
  "tools_failed": 6,
  "providers_validated": 29,
  "providers_ok": 22,
  "providers_failed": 7,
  "error_details": [
    {
      "type": "tool",
      "name": "research_example_tool",
      "error": "ImportError: module not found"
    }
  ]
}
```

---

## API Discovery

### GET /openapi.json

**Description:** OpenAPI 3.0.3 specification for all registered tools.

**Response:** Valid OpenAPI 3.0.3 JSON schema with all 346 tools, parameters, and response schemas.

**Usage:**
```bash
curl -X GET http://127.0.0.1:8787/openapi.json \
  -H "X-API-Key: test"
```

---

### GET /docs

**Description:** Swagger UI for interactive API exploration.

**Access:** Open browser to `http://127.0.0.1:8787/docs`

---

### GET /redoc

**Description:** ReDoc documentation viewer (alternative to Swagger).

**Access:** Open browser to `http://127.0.0.1:8787/redoc`

---

### POST /invoke/research_versions_get

**Tool Name:** `research_versions_get`

**Parameters:** None

**Returns:**
```json
{
  "current_version": "4.0.0",
  "supported_versions": ["3.9.0", "4.0.0"],
  "deprecated_versions": ["3.5.0", "3.6.0"],
  "breaking_changes": [
    {
      "version": "4.0.0",
      "change": "Removed legacy_mode parameter from tools",
      "migration": "Use modern async tools instead"
    }
  ],
  "release_date": "2026-05-01",
  "next_release": "2026-06-01"
}
```

---

## Monitoring Endpoints

### POST /invoke/research_metrics

**Tool Name:** `research_metrics` (requires prometheus_client)

**Parameters:**
- `format` (str): "prometheus" or "json" (default: "prometheus")
- `include_histogram` (bool): Include histogram buckets (default: true)

**Returns:** Prometheus metrics in text format or JSON

**Prometheus Metrics Available:**
- `loom_tool_calls_total` — Counter by tool_name, status
- `loom_tool_duration_seconds` — Histogram by tool_name
- `loom_tool_errors_total` — Counter by tool_name, error_type

**Example Response (JSON format):**
```json
{
  "format": "json",
  "timestamp": "2026-05-04T12:35:00Z",
  "metrics": {
    "loom_tool_calls_total": [
      { "labels": {"tool_name": "research_fetch", "status": "success"}, "value": 1234 },
      { "labels": {"tool_name": "research_fetch", "status": "error"}, "value": 12 }
    ],
    "loom_tool_duration_seconds": [
      { "labels": {"tool_name": "research_fetch"}, "p50": 0.52, "p95": 2.1, "p99": 5.3 }
    ]
  }
}
```

---

### POST /invoke/research_audit_export

**Tool Name:** `research_audit_export`

**Parameters:**
- `start_date` (str, optional): Start date "YYYY-MM-DD"
- `end_date` (str, optional): End date "YYYY-MM-DD"
- `format` (str): "json" or "csv" (default: "json")

**Returns:**
```json
{
  "format": "json",
  "data": [
    {
      "timestamp": "2026-05-04T12:00:00Z",
      "client_id": "user123",
      "tool_name": "research_fetch",
      "params": {"url": "https://example.com"},
      "result_summary": "success: 5234 bytes",
      "duration_ms": 1245,
      "status": "success",
      "_verified": true
    }
  ],
  "count": 1500
}
```

---

### POST /invoke/research_audit_query

**Tool Name:** `research_audit_query`

**Parameters:**
- `tool_name` (str, optional): Filter by tool name (default: "")
- `hours` (int): Look back N hours, 1-720 (default: 24)
- `limit` (int): Max entries to return, 1-1000 (default: 100)

**Returns:**
```json
{
  "entries": [
    {
      "timestamp": "2026-05-04T11:30:00Z",
      "client_id": "user123",
      "tool_name": "research_fetch",
      "duration_ms": 1245,
      "status": "success"
    }
  ],
  "count": 45,
  "total_count": 2340,
  "timestamp": "2026-05-04T12:35:00Z",
  "query_duration_ms": 125
}
```

---

### POST /invoke/research_audit_stats

**Tool Name:** `research_audit_stats`

**Parameters:**
- `hours` (int): Look back N hours, 1-720 (default: 24)

**Returns:**
```json
{
  "total_calls": 5420,
  "successful_calls": 5315,
  "failed_calls": 89,
  "timeout_calls": 12,
  "other_error_calls": 4,
  "top_tools": {
    "research_fetch": 1234,
    "research_search": 890,
    "research_llm_summarize": 567
  },
  "top_errors": {
    "ValidationError": 34,
    "TimeoutError": 12,
    "RateLimitError": 8
  },
  "avg_duration_ms": 1245,
  "min_duration_ms": 50,
  "max_duration_ms": 45000,
  "total_duration_ms": 6750000,
  "total_cost_credits": 1356,
  "timestamp": "2026-05-04T12:35:00Z"
}
```

---

### POST /invoke/research_analytics_dashboard

**Tool Name:** `research_analytics_dashboard`

**Parameters:**
- `action` (str): "get_summary", "get_tool_stats", "get_user_stats", "export"
- `tool_name` (str, optional): Filter by tool (for "get_tool_stats")
- `user_id` (str, optional): Filter by user (for "get_user_stats")
- `start_date` (str, optional): Start date "YYYY-MM-DD"
- `end_date` (str, optional): End date "YYYY-MM-DD"
- `format` (str): "json", "csv", or "html" (default: "json")

**Returns (Summary):**
```json
{
  "period": "24h",
  "total_calls": 5420,
  "unique_users": 145,
  "unique_tools": 78,
  "success_rate": 0.98,
  "avg_latency_ms": 1245,
  "p95_latency_ms": 3500,
  "total_credits_used": 1356
}
```

---

### POST /invoke/research_progress_stream

**Tool Name:** `research_progress_stream` (Server-Sent Events)

**Parameters:**
- `job_id` (str): Job ID to track
- `timeout_seconds` (int): Max wait time (default: 300)

**Returns:** SSE stream of progress updates

**Example:**
```
event: progress
data: {"status": "running", "step": 1, "total_steps": 5, "message": "Fetching URLs..."}

event: progress
data: {"status": "running", "step": 2, "total_steps": 5, "message": "Processing markdown..."}

event: complete
data: {"status": "complete", "result": {...}}
```

---

## Infrastructure Tools

### POST /invoke/research_circuit_status

**Tool Name:** `research_circuit_status`

**Parameters:** None

**Returns:**
```json
{
  "timestamp": "2026-05-04T12:35:00Z",
  "circuits": {
    "llm_groq": {
      "status": "closed|open|half_open",
      "failure_count": 2,
      "success_count": 1234,
      "last_failure": "2026-05-04T12:00:00Z",
      "retry_after": 30
    },
    "search_exa": {
      "status": "closed",
      "failure_count": 0,
      "success_count": 5680,
      "last_failure": null,
      "retry_after": 0
    }
  },
  "overall_status": "healthy"
}
```

---

### POST /invoke/research_retry_stats

**Tool Name:** `research_retry_stats`

**Parameters:**
- `hours` (int): Look back N hours (default: 24)
- `provider` (str, optional): Filter by provider

**Returns:**
```json
{
  "period_hours": 24,
  "total_retries": 456,
  "successful_retries": 421,
  "failed_retries": 35,
  "avg_retry_count": 1.3,
  "max_retry_count": 5,
  "by_provider": {
    "groq": { "retries": 123, "success": 115, "failure": 8 },
    "search_exa": { "retries": 89, "success": 85, "failure": 4 }
  }
}
```

---

### POST /invoke/research_quota_status

**Tool Name:** `research_quota_status`

**Parameters:**
- `provider` (str, optional): Filter to specific provider

**Returns:**
```json
{
  "timestamp": "2026-05-04T12:35:00Z",
  "quotas": {
    "groq": {
      "daily_limit": 10000,
      "used_today": 4567,
      "remaining": 5433,
      "reset_at": "2026-05-05T00:00:00Z",
      "percent_used": 45.67
    },
    "search_exa": {
      "daily_limit": 1000,
      "used_today": 850,
      "remaining": 150,
      "reset_at": "2026-05-05T00:00:00Z",
      "percent_used": 85.0
    }
  }
}
```

---

### POST /invoke/research_secret_health

**Tool Name:** `research_secret_health`

**Parameters:**
- `check_all` (bool): Check all configured secrets (default: true)

**Returns:**
```json
{
  "timestamp": "2026-05-04T12:35:00Z",
  "overall_status": "healthy|degraded|unhealthy",
  "secrets_configured": 18,
  "secrets_valid": 16,
  "secrets_invalid": 2,
  "details": {
    "GROQ_API_KEY": { "configured": true, "valid": true, "last_checked": "2026-05-04T12:00:00Z" },
    "OPENAI_API_KEY": { "configured": true, "valid": false, "last_checked": "2026-05-04T11:30:00Z", "error": "Invalid format" }
  }
}
```

---

### POST /invoke/research_cpu_pool_status

**Tool Name:** `research_cpu_pool_status`

**Parameters:** None

**Returns:**
```json
{
  "pool_initialized": true,
  "max_workers": 4,
  "active_tasks": 2,
  "pending_tasks": 5,
  "status": "busy|healthy|saturated|idle",
  "configuration": {
    "LOOM_CPU_WORKERS": "4",
    "LOOM_CPU_QUEUE_SIZE": "100"
  }
}
```

---

### POST /invoke/research_latency_report

**Tool Name:** `research_latency_report`

**Parameters:**
- `tool_name` (str, optional): Filter to specific tool
- `percentiles` (list[int], optional): Custom percentiles, e.g., [50, 90, 99, 99.9]

**Returns:**
```json
{
  "timestamp": "2026-05-04T12:35:00Z",
  "period": "24h",
  "tools": {
    "research_fetch": {
      "call_count": 1234,
      "p50": 450,
      "p90": 1200,
      "p95": 2100,
      "p99": 5300,
      "p99_9": 8500,
      "min": 50,
      "max": 45000,
      "mean": 1245
    }
  }
}
```

---

### POST /invoke/research_dlq_stats

**Tool Name:** `research_dlq_stats` (Dead Letter Queue)

**Parameters:**
- `hours` (int): Look back N hours (default: 24)

**Returns:**
```json
{
  "total_dlq_messages": 34,
  "oldest_message_age_hours": 18,
  "messages_by_tool": {
    "research_fetch": 12,
    "research_search": 8,
    "research_spider": 14
  },
  "messages_by_error_type": {
    "ValidationError": 15,
    "NetworkError": 12,
    "TimeoutError": 7
  },
  "sample_messages": [
    {
      "id": "dlq-2026-05-04-12-00-001",
      "tool": "research_fetch",
      "error": "Connection timeout",
      "created_at": "2026-05-04T12:00:00Z",
      "retry_count": 3
    }
  ]
}
```

---

### POST /invoke/research_rate_limits

**Tool Name:** `research_rate_limits`

**Parameters:**
- `user_id` (str, optional): Filter by user
- `category` (str, optional): Filter by category

**Returns:**
```json
{
  "timestamp": "2026-05-04T12:35:00Z",
  "user_limits": {
    "user123": {
      "requests_total": 5420,
      "requests_used": 4567,
      "requests_remaining": 853,
      "reset_at": "2026-05-05T00:00:00Z"
    }
  },
  "tool_limits": {
    "research_fetch": {
      "requests_per_minute": 60,
      "used_this_minute": 8,
      "remaining": 52
    }
  }
}
```

---

### POST /invoke/research_loader_stats

**Tool Name:** `research_loader_stats` (Plugin/Module Loader)

**Parameters:**
- `include_optional` (bool): Include optional modules (default: true)

**Returns:**
```json
{
  "timestamp": "2026-05-04T12:35:00Z",
  "total_modules": 61,
  "core_modules": 35,
  "optional_modules": 26,
  "loaded_modules": 59,
  "failed_modules": 2,
  "load_errors": {
    "loom.tools.example_optional": "ImportError: Optional dependency not installed"
  }
}
```

---

## Batch & Webhook Tools

### POST /invoke/research_batch_submit

**Tool Name:** `research_batch_submit`

**Parameters:**
- `tool_name` (str): Name of tool to batch invoke
- `batch_items` (list[dict]): List of parameter dicts for each invocation
- `timeout_seconds` (int): Batch timeout (default: 300)
- `parallel` (bool): Run in parallel (default: true)

**Returns:**
```json
{
  "batch_id": "batch-2026-05-04-001",
  "tool_name": "research_fetch",
  "item_count": 10,
  "status": "submitted|running|complete|failed",
  "created_at": "2026-05-04T12:35:00Z",
  "estimated_completion": "2026-05-04T12:50:00Z"
}
```

---

### POST /invoke/research_batch_status

**Tool Name:** `research_batch_status`

**Parameters:**
- `batch_id` (str): ID of batch to check

**Returns:**
```json
{
  "batch_id": "batch-2026-05-04-001",
  "status": "running",
  "progress": {
    "total": 10,
    "completed": 7,
    "failed": 1,
    "pending": 2
  },
  "results": [
    { "item_index": 0, "status": "success", "result": {...} },
    { "item_index": 1, "status": "success", "result": {...} }
  ],
  "errors": [
    { "item_index": 5, "status": "error", "error": "ValidationError: Invalid URL" }
  ]
}
```

---

### POST /invoke/research_batch_list

**Tool Name:** `research_batch_list`

**Parameters:**
- `status` (str, optional): Filter by status (submitted, running, complete, failed)
- `limit` (int): Max batches to return (default: 100)

**Returns:**
```json
{
  "batches": [
    {
      "batch_id": "batch-2026-05-04-001",
      "tool_name": "research_fetch",
      "status": "running",
      "item_count": 10,
      "created_at": "2026-05-04T12:35:00Z",
      "progress": { "completed": 7, "total": 10 }
    }
  ],
  "count": 15
}
```

---

### POST /invoke/research_webhook_register

**Tool Name:** `research_webhook_register`

**Parameters:**
- `url` (str): Webhook URL to register
- `event_types` (list[str]): Events to subscribe to (e.g., ["batch.complete", "batch.error"])
- `secret` (str, optional): HMAC signing secret
- `active` (bool): Whether webhook is active (default: true)

**Returns:**
```json
{
  "webhook_id": "wh-2026-05-04-001",
  "url": "https://example.com/webhook",
  "event_types": ["batch.complete", "batch.error"],
  "created_at": "2026-05-04T12:35:00Z",
  "status": "active|inactive"
}
```

---

### POST /invoke/research_webhook_list

**Tool Name:** `research_webhook_list`

**Parameters:** None

**Returns:**
```json
{
  "webhooks": [
    {
      "webhook_id": "wh-2026-05-04-001",
      "url": "https://example.com/webhook",
      "event_types": ["batch.complete"],
      "status": "active",
      "created_at": "2026-05-04T12:35:00Z",
      "last_delivery": "2026-05-04T12:30:00Z"
    }
  ],
  "count": 3
}
```

---

### POST /invoke/research_webhook_unregister

**Tool Name:** `research_webhook_unregister`

**Parameters:**
- `webhook_id` (str): Webhook ID to unregister

**Returns:**
```json
{
  "webhook_id": "wh-2026-05-04-001",
  "status": "deleted",
  "deleted_at": "2026-05-04T12:35:00Z"
}
```

---

### POST /invoke/research_webhook_test

**Tool Name:** `research_webhook_test`

**Parameters:**
- `webhook_id` (str): Webhook ID to test

**Returns:**
```json
{
  "webhook_id": "wh-2026-05-04-001",
  "test_sent": true,
  "http_status": 200,
  "response_time_ms": 245,
  "status": "ok|error"
}
```

---

## Research Tools

### POST /invoke/research_compose

**Tool Name:** `research_compose`

**Parameters:**
- `components` (list[dict]): List of tool calls with parameters
- `parallel` (bool): Execute in parallel (default: false)
- `aggregate` (bool): Aggregate results (default: true)

**Example Request:**
```json
{
  "components": [
    {
      "tool": "research_fetch",
      "params": { "url": "https://example.com/page1" }
    },
    {
      "tool": "research_search",
      "params": { "query": "python async programming", "max_results": 5 }
    }
  ],
  "parallel": true,
  "aggregate": true
}
```

**Returns:**
```json
{
  "composition_id": "comp-2026-05-04-001",
  "components": [
    {
      "tool": "research_fetch",
      "status": "success",
      "result": {...}
    },
    {
      "tool": "research_search",
      "status": "success",
      "result": {...}
    }
  ],
  "aggregated_summary": "Fetched page1 and found 5 search results related to async Python"
}
```

---

### POST /invoke/research_compose_validate

**Tool Name:** `research_compose_validate`

**Parameters:**
- `components` (list[dict]): List of tool calls to validate

**Returns:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["research_fetch should have timeout_seconds < 60"],
  "components_valid": 2,
  "components_invalid": 0
}
```

---

### POST /invoke/research_semantic_route

**Tool Name:** `research_semantic_route`

**Parameters:**
- `query` (str): Query to route
- `available_tools` (list[str], optional): Candidate tools

**Returns:**
```json
{
  "query": "Find the capital of France",
  "recommended_tool": "research_search",
  "confidence": 0.95,
  "reasoning": "Query requires factual lookup",
  "alternative_tools": ["research_llm_answer", "research_wikipedia"],
  "suggested_params": {
    "query": "capital of France",
    "max_results": 5
  }
}
```

---

### POST /invoke/research_batch_verify

**Tool Name:** `research_batch_verify`

**Parameters:**
- `batch_id` (str): Batch ID to verify
- `sample_size` (int): Number of results to sample (default: 10)

**Returns:**
```json
{
  "batch_id": "batch-2026-05-04-001",
  "verified": true,
  "total_items": 100,
  "sampled_items": 10,
  "passed": 9,
  "failed": 1,
  "issues": [
    {
      "item_index": 47,
      "issue": "Result schema mismatch: missing 'title' field"
    }
  ]
}
```

---

### POST /invoke/research_fact_verify

**Tool Name:** `research_fact_verify`

**Parameters:**
- `claim` (str): Claim to verify
- `sources` (list[str], optional): Reference sources
- `confidence_threshold` (float): Min confidence (0-1, default: 0.7)

**Returns:**
```json
{
  "claim": "Paris is the capital of France",
  "verified": true,
  "confidence": 0.98,
  "supporting_sources": [
    {
      "url": "https://en.wikipedia.org/wiki/Paris",
      "snippet": "Paris is the capital of France...",
      "relevance": 0.99
    }
  ]
}
```

---

### POST /invoke/research_trend_forecast

**Tool Name:** `research_trend_forecast`

**Parameters:**
- `query` (str): Topic to forecast
- `lookback_days` (int): Historical data window (default: 90)
- `forecast_days` (int): Days to forecast ahead (default: 30)

**Returns:**
```json
{
  "query": "artificial intelligence",
  "lookback_days": 90,
  "forecast_days": 30,
  "current_trend": "rising",
  "forecast_trend": "accelerating",
  "confidence": 0.82,
  "key_drivers": ["AI safety", "model scaling", "regulation"],
  "predicted_momentum": 0.85
}
```

---

### POST /invoke/research_generate_report

**Tool Name:** `research_generate_report`

**Parameters:**
- `title` (str): Report title
- `sections` (list[dict]): Report sections with content
- `format` (str): "markdown", "html", "pdf" (default: "markdown")
- `include_toc` (bool): Include table of contents (default: true)

**Returns:**
```json
{
  "report_id": "rep-2026-05-04-001",
  "title": "AI Safety Research Summary",
  "format": "markdown",
  "content": "# AI Safety Research Summary\n\n## Overview\n...",
  "size_bytes": 45678,
  "generated_at": "2026-05-04T12:35:00Z"
}
```

---

### POST /invoke/research_compress_prompt

**Tool Name:** `research_compress_prompt`

**Parameters:**
- `prompt` (str): Prompt to compress
- `compression_ratio` (float): Target ratio (0-1, default: 0.5)
- `preserve_meaning` (bool): Preserve semantic meaning (default: true)

**Returns:**
```json
{
  "original_length": 1200,
  "compressed_length": 600,
  "compression_ratio": 0.5,
  "original": "Full original prompt...",
  "compressed": "Compressed prompt...",
  "quality_score": 0.92
}
```

---

## OSINT Tools

### POST /invoke/research_maigret

**Tool Name:** `research_maigret`

**Parameters:**
- `username` (str): Username to search
- `timeout` (int): Search timeout in seconds (default: 60)
- `sites` (list[str], optional): Specific sites to search

**Returns:**
```json
{
  "username": "example_user",
  "found_on": [
    {
      "site": "GitHub",
      "url": "https://github.com/example_user",
      "confirmed": true
    },
    {
      "site": "Twitter",
      "url": "https://twitter.com/example_user",
      "confirmed": true
    }
  ],
  "total_found": 12,
  "search_duration_ms": 45000
}
```

---

### POST /invoke/research_harvest

**Tool Name:** `research_harvest` (Email harvesting)

**Parameters:**
- `domain` (str): Domain to harvest emails from
- `max_results` (int): Maximum emails to find (default: 100)

**Returns:**
```json
{
  "domain": "example.com",
  "emails_found": 47,
  "emails": [
    "admin@example.com",
    "info@example.com",
    "support@example.com"
  ],
  "sources": [
    "LinkedIn",
    "GitHub",
    "Public records"
  ]
}
```

---

### POST /invoke/research_spiderfoot_scan

**Tool Name:** `research_spiderfoot_scan`

**Parameters:**
- `target` (str): Target to scan (domain, email, IP, etc.)
- `modules` (list[str], optional): Specific modules to use
- `max_depth` (int): Recursion depth (default: 3)

**Returns:**
```json
{
  "scan_id": "sf-2026-05-04-001",
  "target": "example.com",
  "status": "complete",
  "findings": [
    {
      "type": "DOMAIN_REGISTERED",
      "value": "example.com",
      "source": "WHOIS"
    },
    {
      "type": "SUBDOMAIN",
      "value": "api.example.com",
      "source": "DNS"
    }
  ],
  "total_findings": 47
}
```

---

### POST /invoke/research_archive_page

**Tool Name:** `research_archive_page`

**Parameters:**
- `url` (str): URL to archive
- `capture` (bool): Capture new snapshot (default: false)

**Returns:**
```json
{
  "url": "https://example.com",
  "archived_url": "https://web.archive.org/web/20260504120000/https://example.com",
  "snapshots": [
    { "date": "2026-05-04", "status": 200 },
    { "date": "2026-05-03", "status": 200 },
    { "date": "2026-05-02", "status": 200 }
  ],
  "total_snapshots": 156
}
```

---

### POST /invoke/research_yara_scan

**Tool Name:** `research_yara_scan`

**Parameters:**
- `target` (str): File path or URL to scan
- `rule_set` (str): YARA ruleset name (default: "malware_detection")
- `recursive` (bool): Recursive directory scan (default: false)

**Returns:**
```json
{
  "target": "/path/to/file.exe",
  "status": "clean|suspicious|malicious",
  "matches": [
    {
      "rule": "Win32.Malware.Generic",
      "strings": ["MZ", "CreateProcessA"],
      "severity": "high"
    }
  ],
  "scan_time_ms": 245
}
```

---

### POST /invoke/research_misp_lookup

**Tool Name:** `research_misp_lookup`

**Parameters:**
- `indicator` (str): IOC to lookup (IP, domain, file hash, etc.)
- `event_limit` (int): Max events to return (default: 10)

**Returns:**
```json
{
  "indicator": "192.0.2.1",
  "type": "ip",
  "found": true,
  "events": [
    {
      "event_id": 12345,
      "threat_level": "high",
      "info": "Malware C2 server",
      "timestamp": "2026-04-15T10:00:00Z"
    }
  ],
  "total_events": 3
}
```

---

### POST /invoke/research_social_analyze

**Tool Name:** `research_social_analyze`

**Parameters:**
- `profile_url` (str): Social media profile URL
- `include_sentiment` (bool): Analyze sentiment (default: true)
- `include_network` (bool): Analyze social network (default: false)

**Returns:**
```json
{
  "profile_url": "https://twitter.com/example",
  "username": "example",
  "platform": "twitter",
  "followers": 5000,
  "sentiment": {
    "overall": "positive",
    "recent_tweets_analyzed": 50,
    "positive_percent": 72,
    "negative_percent": 15,
    "neutral_percent": 13
  },
  "activity": {
    "posts_per_week": 8.5,
    "engagement_rate": 0.045
  }
}
```

---

## Privacy Tools

### POST /invoke/research_fingerprint_audit

**Tool Name:** `research_fingerprint_audit`

**Parameters:**
- `target_url` (str): Website URL to audit
- `include_canvas` (bool): Test canvas fingerprinting (default: true)
- `include_webgl` (bool): Test WebGL fingerprinting (default: true)
- `include_audio` (bool): Test audio fingerprinting (default: true)
- `include_fonts` (bool): Test font enumeration (default: true)

**Returns:**
```json
{
  "target_url": "https://example.com",
  "audit_timestamp": "2026-05-04T12:35:00Z",
  "fingerprint_attributes": {
    "user_agent": "Mozilla/5.0...",
    "languages": ["en-US"],
    "screen_resolution": "1920x1080",
    "timezone": "UTC",
    "canvas_entropy": 8.5,
    "webgl_entropy": 7.2,
    "audio_entropy": 6.8,
    "font_count": 247
  },
  "total_unique_attributes": 70,
  "uniqueness_percentage": 0.78,
  "privacy_risk": "high"
}
```

---

### POST /invoke/research_privacy_exposure

**Tool Name:** `research_privacy_exposure`

**Parameters:**
- `target_url` (str): Website to scan
- `include_interactive` (bool): Run interactive tests (default: false)

**Returns:**
```json
{
  "target_url": "https://example.com",
  "privacy_baseline_score": 42,
  "exposures": [
    {
      "type": "Third-party tracker",
      "domain": "analytics.google.com",
      "category": "analytics",
      "severity": "medium"
    },
    {
      "type": "Cookie exposed",
      "name": "session_id",
      "domain": ".example.com",
      "severity": "high"
    }
  ],
  "total_exposures": 18,
  "recommendations": ["Block analytics", "Use privacy-focused DNS"]
}
```

---

### POST /invoke/research_artifact_cleanup

**Tool Name:** `research_artifact_cleanup`

**Parameters:**
- `target_paths` (list[str]): Paths to clean (logs, cache, temp, etc.)
- `os_type` (str): "linux", "windows", or "macos" (required)
- `dry_run` (bool): Simulate without deleting (default: true)

**Returns:**
```json
{
  "dry_run": true,
  "os_type": "linux",
  "artifacts_found": 247,
  "artifacts_would_delete": 189,
  "size_would_recover_mb": 456.7,
  "items": [
    { "path": "/home/user/.bash_history", "size_kb": 12.5, "status": "would_delete" },
    { "path": "/tmp/cache/*", "size_mb": 234.5, "status": "would_delete" }
  ]
}
```

---

### POST /invoke/research_stego_encode

**Tool Name:** `research_stego_encode`

**Parameters:**
- `input_media` (str): Path to media file (PNG, BMP, WAV)
- `secret_data` (str): Data to hide
- `output_path` (str): Path to save encoded media
- `output_format` (str): "png" or "bmp" (default: "png")

**Returns:**
```json
{
  "status": "success",
  "input_file": "image.png",
  "output_file": "image_encoded.png",
  "capacity_bytes": 50000,
  "data_hidden_bytes": 245,
  "capacity_used_percent": 0.49,
  "detection_resistance": "high",
  "compression": "none"
}
```

---

### POST /invoke/research_stego_decode

**Tool Name:** `research_stego_decode`

**Parameters:**
- `encoded_media` (str): Path to encoded media file

**Returns:**
```json
{
  "status": "success",
  "input_file": "image_encoded.png",
  "data_recovered": "Secret message hidden in image",
  "data_length_bytes": 245,
  "confidence": 0.99
}
```

---

### POST /invoke/research_usb_monitor

**Tool Name:** `research_usb_monitor` (requires usbkill)

**Parameters:**
- `trigger_action` (str): "alert", "lock", or "wipe" (default: "alert")
- `target_path` (str, optional): Path to wipe/lock
- `dry_run` (bool): Simulate without executing (default: true)

**Returns:**
```json
{
  "monitor_status": "enabled|disabled",
  "trigger_action": "alert",
  "dry_run": true,
  "usb_devices_detected": 3,
  "monitored_devices": ["Mass Storage", "Input Device"],
  "last_usb_activity": "2026-05-04T12:00:00Z",
  "emergency_actions_tested": true
}
```

---

### POST /invoke/research_network_anomaly

**Tool Name:** `research_network_anomaly`

**Parameters:**
- `monitor_duration` (int): Duration to monitor in seconds (default: 60)
- `baseline` (dict, optional): Baseline stats for comparison

**Returns:**
```json
{
  "monitor_duration_seconds": 60,
  "packets_captured": 1247,
  "anomalies_detected": 3,
  "anomalies": [
    {
      "type": "unusual_port",
      "description": "Connection to non-standard SSH port 12345",
      "severity": "medium",
      "ip": "192.0.2.1",
      "port": 12345
    }
  ],
  "baseline_deviation": 0.08
}
```

---

### POST /invoke/research_browser_privacy_score

**Tool Name:** `research_browser_privacy_score`

**Parameters:**
- `browser_type` (str): "chrome", "firefox", "safari", "edge"

**Returns:**
```json
{
  "browser": "firefox",
  "privacy_score": 78,
  "categories": {
    "tracking_protection": 95,
    "encryption": 85,
    "data_collection": 65,
    "ad_blocking": 72,
    "fingerprint_resistance": 68
  },
  "recommendations": [
    "Enable DNS-over-HTTPS",
    "Install privacy extension",
    "Configure Firefox Enhanced Tracking Protection"
  ]
}
```

---

### POST /invoke/research_metadata_strip

**Tool Name:** `research_metadata_strip`

**Parameters:**
- `file_path` (str): Path to file
- `output_path` (str, optional): Path to save cleaned file
- `metadata_types` (list[str], optional): Specific metadata to remove

**Returns:**
```json
{
  "input_file": "document.pdf",
  "output_file": "document_clean.pdf",
  "status": "success",
  "metadata_removed": [
    { "type": "author", "value": "John Doe" },
    { "type": "creation_date", "value": "2025-01-01" },
    { "type": "gps", "value": "40.7128,-74.0060" }
  ],
  "total_metadata_fields_removed": 12
}
```

---

## EU AI Act Compliance Tools

### POST /invoke/research_ai_transparency_check

**Tool Name:** `research_ai_transparency_check`

**Parameters:**
- `model_name` (str): Model identifier
- `check_categories` (list[str], optional): Specific checks to run

**Returns:**
```json
{
  "model": "gpt-4",
  "transparency_score": 72,
  "checks": {
    "capability_disclosure": {
      "status": "pass",
      "details": "Model capabilities documented"
    },
    "limitation_disclosure": {
      "status": "fail",
      "details": "Limitations not clearly documented"
    },
    "intended_use": {
      "status": "pass",
      "details": "Intended use documented"
    },
    "training_data_info": {
      "status": "partial",
      "details": "Limited information about training data"
    }
  },
  "compliance_status": "partial"
}
```

---

### POST /invoke/research_ai_bias_audit

**Tool Name:** `research_ai_bias_audit`

**Parameters:**
- `model_name` (str): Model to audit
- `test_domains` (list[str], optional): Domains to test (gender, race, age, etc.)
- `sample_size` (int): Test samples (default: 100)

**Returns:**
```json
{
  "model": "gpt-4",
  "audit_timestamp": "2026-05-04T12:35:00Z",
  "bias_score": 0.24,
  "domains_tested": ["gender", "race", "age", "disability"],
  "findings": {
    "gender": {
      "bias_detected": true,
      "bias_percentage": 0.35,
      "examples": [
        "Model associates doctor with male 35% more than female"
      ]
    },
    "race": {
      "bias_detected": false,
      "bias_percentage": 0.08
    }
  },
  "recommendations": ["Fine-tune on diverse datasets", "Use bias mitigation techniques"]
}
```

---

### POST /invoke/research_ai_robustness_test

**Tool Name:** `research_ai_robustness_test`

**Parameters:**
- `model_name` (str): Model to test
- `test_types` (list[str], optional): Test categories (adversarial, out_of_domain, etc.)
- `perturbation_intensity` (float): 0-1 scale (default: 0.5)

**Returns:**
```json
{
  "model": "gpt-4",
  "robustness_score": 0.81,
  "test_results": {
    "adversarial_examples": {
      "test_count": 50,
      "successful_attacks": 8,
      "attack_success_rate": 0.16
    },
    "out_of_domain": {
      "test_count": 50,
      "failures": 12,
      "failure_rate": 0.24
    },
    "perturbations": {
      "test_count": 100,
      "robustness_percentage": 87
    }
  },
  "vulnerabilities": [
    "Adversarial prompt injection attack",
    "Out-of-domain performance degradation"
  ]
}
```

---

### POST /invoke/research_ai_data_governance

**Tool Name:** `research_ai_data_governance`

**Parameters:**
- `model_name` (str): Model to assess
- `check_categories` (list[str], optional): Categories to verify

**Returns:**
```json
{
  "model": "gpt-4",
  "governance_score": 68,
  "checks": {
    "data_provenance": {
      "status": "documented",
      "details": "Training data sources identified"
    },
    "data_quality": {
      "status": "partial",
      "details": "Quality filters applied but details limited"
    },
    "data_retention": {
      "status": "pass",
      "details": "Retention policy clear"
    },
    "data_deletion_capability": {
      "status": "fail",
      "details": "Unable to delete specific training samples post-hoc"
    },
    "consent_management": {
      "status": "partial",
      "details": "Opt-out available but limited"
    }
  },
  "recommendations": [
    "Implement machine unlearning for data deletion",
    "Improve training data documentation"
  ]
}
```

---

### POST /invoke/research_ai_risk_classify

**Tool Name:** `research_ai_risk_classify`

**Parameters:**
- `model_name` (str): Model to classify
- `use_case` (str): Intended use case
- `risk_categories` (list[str], optional): Categories to evaluate

**Returns:**
```json
{
  "model": "gpt-4",
  "use_case": "medical diagnosis support",
  "eu_ai_act_risk_category": "high_risk",
  "risk_score": 0.78,
  "risk_categories": {
    "safety_critical": {
      "score": 0.85,
      "notes": "Medical decisions can affect patient health"
    },
    "privacy_intensive": {
      "score": 0.72,
      "notes": "Processes sensitive health data"
    },
    "biometric_sensitive": {
      "score": 0.5,
      "notes": "May involve biometric data interpretation"
    },
    "rights_impact": {
      "score": 0.88,
      "notes": "Decisions significantly impact individual rights"
    }
  },
  "required_compliance": [
    "Human oversight mandatory",
    "Transparency documentation",
    "Risk mitigation measures",
    "Audit trail maintenance"
  ]
}
```

---

## Response Format & Error Handling

### Standard Response Envelope

All MCP tool responses follow a consistent envelope format:

```json
{
  "tool": "research_tool_name",
  "status": "success|error|timeout",
  "timestamp": "2026-05-04T12:35:00Z",
  "result": {
    "data": {}
  },
  "metadata": {
    "execution_time_ms": 245,
    "request_id": "req-2026-05-04-001"
  }
}
```

### Error Response

```json
{
  "error": "InvalidParameter",
  "message": "Parameter 'url' is required",
  "tool": "research_fetch",
  "timestamp": "2026-05-04T12:35:00Z",
  "request_id": "req-2026-05-04-001"
}
```

### Pagination

For tools returning large result sets:

```json
{
  "result": {
    "items": [...],
    "pagination": {
      "total": 5000,
      "page": 1,
      "page_size": 100,
      "has_next": true,
      "next_page": 2
    }
  }
}
```

### Rate Limit Response

```json
{
  "error": "RateLimitExceeded",
  "message": "You have exceeded 60 requests per minute",
  "retry_after_seconds": 30,
  "limit_info": {
    "limit_per_minute": 60,
    "remaining": 0,
    "reset_at": "2026-05-04T12:36:00Z"
  }
}
```

### Token Economy Metadata

When `LOOM_TOKEN_ECONOMY=true`:

```json
{
  "result": {...},
  "_token_economy": {
    "cost": 50,
    "balance_before": 1000,
    "balance_after": 950
  }
}
```

### Billing Metadata

When `LOOM_BILLING_ENABLED=true`:

```json
{
  "result": {...},
  "_billing": {
    "customer_id": "cust-123",
    "tool_name": "research_fetch",
    "duration_ms": 1245,
    "credits_used": 1,
    "estimated_cost_usd": 0.01
  }
}
```

### Latency Tracking

For slow operations (>1000ms):

```json
{
  "result": {...},
  "_latency_p95_ms": 2100,
  "_latency_stats": {
    "p50": 450,
    "p95": 2100,
    "p99": 5300
  }
}
```

---

## Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| InvalidParameter | Missing or invalid parameter | 400 |
| ValidationError | Parameter validation failed | 400 |
| AuthenticationRequired | API key missing/invalid | 401 |
| AuthorizationFailed | User lacks permissions | 403 |
| RateLimitExceeded | Too many requests | 429 |
| ToolNotFound | Tool doesn't exist | 404 |
| ToolTimeout | Execution exceeded timeout | 504 |
| InsufficientCredits | Token economy balance too low | 402 |
| ProviderUnavailable | LLM/search provider down | 503 |
| InternalError | Server error | 500 |

---

## Best Practices

### 1. Batch Large Operations
```python
# Instead of many individual calls:
# Use research_batch_submit for 10+ invocations

response = requests.post(
    "http://127.0.0.1:8787/invoke/research_batch_submit",
    json={
        "tool_name": "research_fetch",
        "batch_items": [
            {"url": "https://example1.com"},
            {"url": "https://example2.com"},
            # ... up to 1000 items
        ],
        "parallel": True
    }
)
```

### 2. Compose Complex Workflows
```python
# Chain tools with research_compose:
response = requests.post(
    "http://127.0.0.1:8787/invoke/research_compose",
    json={
        "components": [
            {"tool": "research_search", "params": {"query": "topic"}},
            {"tool": "research_fetch", "params": {"url": ""}},  # Fill from search results
            {"tool": "research_llm_summarize", "params": {}}
        ],
        "parallel": False,  # Sequential dependency
        "aggregate": True
    }
)
```

### 3. Monitor Tool Performance
```python
# Check latency stats before using slow tools:
response = requests.post(
    "http://127.0.0.1:8787/invoke/research_latency_report",
    json={"tool_name": "research_fetch"}
)

if response["tools"]["research_fetch"]["p95"] > 5000:
    # Use alternative tool or increase timeout
```

### 4. Handle Rate Limits Gracefully
```python
import time
import requests

for attempt in range(3):
    response = requests.post(...)
    
    if response.status_code == 429:
        retry_after = response.json()["retry_after_seconds"]
        time.sleep(retry_after)
        continue
    
    break
```

### 5. Use Webhooks for Long-Running Batches
```python
# Register webhook for batch completion:
requests.post(
    "http://127.0.0.1:8787/invoke/research_webhook_register",
    json={
        "url": "https://myserver.com/webhook",
        "event_types": ["batch.complete", "batch.error"]
    }
)

# Then submit batch and let webhook notify completion:
batch = requests.post(
    "http://127.0.0.1:8787/invoke/research_batch_submit",
    json={
        "tool_name": "research_fetch",
        "batch_items": [...]
    }
)
```

---

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOOM_HOST` | `127.0.0.1` | Server bind address |
| `LOOM_PORT` | `8787` | Server port |
| `LOOM_AUTH_REQUIRED` | `false` | Enforce API key auth |
| `LOOM_VALID_KEYS` | - | Comma-separated valid API keys |
| `LOOM_BILLING_ENABLED` | `false` | Enable billing system |
| `LOOM_TOKEN_ECONOMY` | `false` | Enable token economy |
| `LOOM_USER_ID` | `anonymous` | Current user identifier |
| `LOOM_CUSTOMER_ID` | `default` | Current customer identifier |
| `LOOM_USER_BALANCE` | `0` | User credit balance (for token economy) |
| `LOOM_PROMETHEUS_ENABLED` | `true` | Enable Prometheus metrics |
| `LOOM_CONFIG_PATH` | `./config.json` | Configuration file path |
| `LOOM_CACHE_DIR` | `~/.cache/loom` | Cache directory |
| `LOOM_SESSIONS_DIR` | `~/.loom/sessions` | Session storage directory |

---

## Support & Debugging

### Enable Debug Logging
```bash
export LOOM_LOG_LEVEL=DEBUG
loom serve
```

### Check Tool Availability
```bash
curl -X POST http://127.0.0.1:8787/invoke/research_health_check \
  -H "X-API-Key: test" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Validate Configuration
```bash
curl -X POST http://127.0.0.1:8787/invoke/research_validate_startup \
  -H "X-API-Key: test" \
  -H "Content-Type: application/json" \
  -d '{"verbose": true}'
```

### Export Audit Logs
```bash
curl -X POST http://127.0.0.1:8787/invoke/research_audit_export \
  -H "X-API-Key: test" \
  -H "Content-Type: application/json" \
  -d '{"format": "json"}'
```

---

**Last Updated:** 2026-05-04  
**Document Version:** 2.0.0  
**API Version:** 4.0.0
