# Error Alerting System

Loom includes a comprehensive error alerting system that notifies operators of critical server errors via Slack webhooks and email.

## Overview

The alerting system automatically detects critical errors in tool execution and sends notifications to:
1. **Webhooks** — Slack, Discord, or custom HTTP endpoints
2. **Email** — SMTP-based email notifications

## Configuration

### Enable Webhook Alerts

Register a webhook to receive error notifications:

```bash
# Register a Slack webhook
curl -X POST http://localhost:8787/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "research_webhook_register",
      "arguments": {
        "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        "events": ["alert.error"],
        "secret": "your-secret-key"
      }
    }
  }'
```

Webhooks receive notifications for:
- **error** level alerts (general errors)
- **critical** level alerts (circuit breaker, SSRF, auth failures)

### Enable Email Alerts

Set the `LOOM_ALERT_EMAIL` environment variable to receive email notifications:

```bash
export LOOM_ALERT_EMAIL="ops@example.com"
export SMTP_USER="your-email@gmail.com"
export SMTP_APP_PASSWORD="your-app-password"
```

Email notifications are sent for:
- **warning** level alerts
- **error** level alerts
- **critical** level alerts

## Alert Levels

The alerting system uses four severity levels:

### info
- **Logging**: Yes
- **Webhook**: No
- **Email**: No
- **Use case**: Informational messages, no action required

### warning
- **Logging**: Yes
- **Webhook**: No
- **Email**: Yes (if `LOOM_ALERT_EMAIL` configured)
- **Use case**: Non-critical issues like slow operations

### error
- **Logging**: Yes
- **Webhook**: Yes (if configured)
- **Email**: Yes (if `LOOM_ALERT_EMAIL` configured)
- **Use case**: Tool execution failures, API errors

### critical
- **Logging**: Yes (at critical level)
- **Webhook**: Yes (if configured)
- **Email**: Yes (if `LOOM_ALERT_EMAIL` configured)
- **Use case**: Security violations, circuit breaker activation, authentication failures

## Critical Error Classification

The system automatically classifies errors as critical if they contain keywords:

- `circuitbreaker` / `circuit_breaker` — Rate limiter circuit breaker opened
- `ssrf` — SSRF attack detection
- `authentication` / `authorization` — Auth failures
- `forbidden` — Access denied
- `security` — Security policy violations
- `secret_manager` — Secret management failures
- `key_rotation` — Key rotation issues

## Webhook Payload Format

Webhooks receive JSON payloads with this structure:

```json
{
  "event": "alert.error",
  "timestamp": "2026-05-04T12:34:56.123456+00:00",
  "webhook_id": "uuid-string",
  "payload": {
    "level": "critical",
    "message": "Critical error in tool research_fetch: CircuitBreakerOpen",
    "timestamp": "2026-05-04T12:34:56.123456+00:00",
    "tool": "research_fetch",
    "error_type": "CircuitBreakerOpen",
    "error_message": "Rate limit circuit breaker activated",
    "execution_time_ms": 45000.0
  }
}
```

All webhooks include HMAC-SHA256 signature verification via the `X-Loom-Signature` header.

## Email Notification Format

Email alerts include:
- Subject: `[Loom Alert - CRITICAL] Critical error in tool research_fetch...`
- Body:
  ```
  Alert Level: CRITICAL
  Timestamp: 2026-05-04T12:34:56.123456+00:00
  Message: Critical error in tool research_fetch: CircuitBreakerOpen

  Details:
    tool: research_fetch
    error_type: CircuitBreakerOpen
    error_message: Rate limit circuit breaker activated
    execution_time_ms: 45000.0
  ```

## Integration with Tool Execution

Error alerting is automatically integrated into the tool execution wrapper (`_wrap_tool` in `server.py`):

1. **Tool execution** — Tool runs with timeout and metrics collection
2. **Error detection** — On exception, error is classified by criticality
3. **Alert dispatch** — If critical, `handle_tool_error()` sends alerts via webhook/email
4. **Fallback logging** — If alerting fails, error is still logged
5. **Audit logging** — Error is recorded in audit trail
6. **Metrics recording** — Error is tracked in Prometheus metrics

## API Reference

### send_alert(level, message, details)

Send an alert via webhook and/or email based on severity level.

**Parameters:**
- `level: str` — Alert severity ("info", "warning", "error", "critical")
- `message: str` — Human-readable alert message
- `details: dict` — Optional context dict (tool, error_type, error_message, execution_time_ms, etc.)

**Returns:**
```python
{
    "status": "sent" | "skipped" | "failed",
    "level": str,
    "message": str,
    "timestamp": str,
    "webhook_notified": bool,
    "email_notified": bool,
    "webhook_error": str | None,
    "email_error": str | None,
}
```

**Example:**
```python
from loom.alerting import send_alert

result = await send_alert(
    level="error",
    message="SSRF attack detected",
    details={
        "tool": "research_fetch",
        "error_type": "SSRFError",
        "error_message": "Blocked internal URL",
        "execution_time_ms": 150.5,
    }
)
```

### handle_tool_error(tool_name, error, execution_time_ms)

Handle a tool execution error by determining criticality and sending alerts.

**Parameters:**
- `tool_name: str` — Name of the tool that failed
- `error: Exception` — The exception that was raised
- `execution_time_ms: float | None` — Optional execution duration before failure

**Behavior:**
- Classifies error severity (critical vs. non-critical)
- Sends alert only for critical errors
- Non-critical errors are logged but not alerted
- Always includes error context (type, message, execution time)

**Example:**
```python
from loom.alerting import handle_tool_error

try:
    result = await research_fetch(url)
except Exception as e:
    await handle_tool_error("research_fetch", e, execution_time_ms=1500.0)
    raise
```

## Monitoring and Debugging

### Check Webhook Registration

```bash
# List registered webhooks
curl -X POST http://localhost:8787/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "research_webhook_list",
      "arguments": {}
    }
  }'
```

### Test Webhook

```bash
# Send test notification to a webhook
curl -X POST http://localhost:8787/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "research_webhook_test",
      "arguments": {
        "webhook_id": "uuid-from-list"
      }
    }
  }'
```

### Check Alert Logs

Alert events are logged to the structured logger at various levels:

```bash
# Watch for critical alerts
grep "alert_critical\|alert_error" /var/log/loom/server.log

# Check webhook delivery
grep "webhook_alert_sent\|webhook_alert_failed" /var/log/loom/server.log

# Check email delivery
grep "email_alert_sent\|email_alert_failed" /var/log/loom/server.log
```

## Best Practices

### 1. Register Multiple Webhooks

Register different webhooks for different channels:
```bash
# Slack #ops channel
curl ... -d '{"url": "https://hooks.slack.com/...#ops", "events": ["alert.error"]}'

# Slack #security channel
curl ... -d '{"url": "https://hooks.slack.com/...#security", "events": ["alert.error"]}'

# Discord webhook
curl ... -d '{"url": "https://discordapp.com/api/webhooks/...", "events": ["alert.error"]}'
```

### 2. Use Email for Critical Alerts

Set `LOOM_ALERT_EMAIL` to ensure critical errors always reach on-call staff via email.

### 3. Monitor Alert Delivery

Periodically test webhooks and email delivery:
```bash
# Test webhook delivery every hour
0 * * * * curl ... -X POST ... -d '{"webhook_id": "..."}'

# Check alert log volume
* * * * * grep alert_error /var/log/loom/server.log | wc -l
```

### 4. Set Up Runbooks

Create runbooks for each critical error type:
- **CircuitBreakerOpen** — Check rate limiter configuration, scale services
- **SSRF** — Review URL validation, check URL allowlist
- **AuthenticationError** — Check API key expiration, rotate credentials
- **SecurityError** — Review access logs, check for intrusion

## Troubleshooting

### Webhooks not firing

1. Verify webhook is registered: `research_webhook_list`
2. Test webhook delivery: `research_webhook_test`
3. Check webhook URL is accessible: `curl https://webhook-url`
4. Check webhook secret is correct: Compare in `research_webhook_list` output
5. Check logs: `grep webhook_alert /var/log/loom/server.log`

### Emails not arriving

1. Verify `LOOM_ALERT_EMAIL` environment variable is set
2. Verify SMTP credentials: `SMTP_USER` and `SMTP_APP_PASSWORD`
3. Check email is not in spam: Gmail, Outlook may filter automated emails
4. Test SMTP connection: `python3 -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).quit()"`
5. Check logs: `grep email_alert /var/log/loom/server.log`

### Too many alerts

If you're receiving too many non-critical alerts:
1. Adjust classification in `_is_critical_error()` function
2. Reduce noise by ignoring specific error types
3. Implement alert throttling (coming soon)
4. Set up alert deduplication in Slack/Discord

## Future Enhancements

- [ ] Alert throttling (debounce duplicate errors)
- [ ] Alert grouping (batch related errors)
- [ ] Alert routing rules (route by error type)
- [ ] Alert templating (custom message formats)
- [ ] Mobile push notifications (PagerDuty, Opsgenie)
- [ ] Alert dashboard (web UI for alert history)
