# Loom Webhook Notification System

The webhook notification system allows you to receive real-time HTTP POST notifications when Loom tool events occur. This is useful for:

- Monitoring tool execution in production environments
- Triggering downstream workflows when tools complete
- Building alerts and dashboards around Loom activity
- Integrating Loom with external systems

## Quick Start

### 1. Register a Webhook

```bash
curl -X POST http://localhost:8787/mcp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/webhook",
    "events": ["tool.completed", "tool.failed"],
    "secret": "my-webhook-secret"
  }'
```

Response:
```json
{
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/webhook",
  "events": ["tool.completed", "tool.failed"],
  "secret": "my-webhook-secret",
  "created_at": "2026-05-04T12:00:00Z",
  "active": true
}
```

### 2. Handle Webhook Notifications

Your webhook endpoint will receive POST requests with this format:

```json
{
  "event": "tool.completed",
  "timestamp": "2026-05-04T12:00:05Z",
  "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "tool_name": "research_fetch",
    "duration": 2.5,
    "success": true
  }
}
```

### 3. Verify Webhook Signature

Every webhook includes an HMAC-SHA256 signature in the `X-Loom-Signature` header. Use your secret key to verify it:

```python
import hmac
import hashlib

def verify_webhook(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

# In your Flask/FastAPI handler
@app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Loom-Signature", "")
    
    if not verify_webhook(body, signature, "my-webhook-secret"):
        return {"error": "invalid signature"}, 401
    
    # Process webhook
    payload = await request.json()
    print(f"Event: {payload['event']}")
    return {"ok": True}
```

## Supported Events

### `tool.completed`

Fired when a tool finishes successfully.

**Payload:**
```json
{
  "tool_name": "research_fetch",
  "duration": 2.5,
  "success": true
}
```

### `tool.failed`

Fired when a tool execution fails.

**Payload:**
```json
{
  "tool_name": "research_fetch",
  "error_type": "ValidationError",
  "message": "Invalid URL provided",
  "duration": 0.1
}
```

### `job.queued`

Fired when a job is queued for execution.

**Payload:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "research_deep",
  "queued_at": "2026-05-04T12:00:00Z"
}
```

### `job.finished`

Fired when a job finishes (success or failure).

**Payload:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "research_deep",
  "status": "completed",
  "duration": 5.2
}
```

### `alert.error`

Fired when a system error is detected.

**Payload:**
```json
{
  "error_type": "HttpError",
  "message": "Connection timeout to example.com",
  "service": "research_fetch",
  "severity": "warning"
}
```

## API Reference

### Register Webhook

**Tool:** `research_webhook_register`

Register a new webhook to receive notifications for specified events.

**Parameters:**
- `url` (string, required): Webhook URL (must start with `http://` or `https://`)
- `events` (array, required): List of events to subscribe to
- `secret` (string, optional): HMAC secret for signature verification (auto-generated if not provided)

**Returns:**
```json
{
  "webhook_id": "string (UUID)",
  "url": "string",
  "events": ["string"],
  "secret": "string (only on registration)",
  "created_at": "string (ISO-8601)",
  "active": true,
  "success_count": 0,
  "failure_count": 0
}
```

### List Webhooks

**Tool:** `research_webhook_list`

List all registered webhooks (secrets are masked).

**Parameters:** None

**Returns:**
```json
{
  "webhooks": [
    {
      "webhook_id": "string",
      "url": "string",
      "events": ["string"],
      "secret": "***...",
      "created_at": "string",
      "last_triggered": "string | null",
      "success_count": 0,
      "failure_count": 0,
      "active": true
    }
  ],
  "total": 5,
  "supported_events": [
    "tool.completed",
    "tool.failed",
    "job.queued",
    "job.finished",
    "alert.error"
  ]
}
```

### Unregister Webhook

**Tool:** `research_webhook_unregister`

Unregister a webhook to stop receiving notifications.

**Parameters:**
- `webhook_id` (string, required): ID of webhook to unregister

**Returns:**
```json
{
  "success": true,
  "webhook_id": "string",
  "message": "Webhook ... unregistered successfully"
}
```

### Test Webhook

**Tool:** `research_webhook_test`

Send a test notification to verify your webhook endpoint is working.

**Parameters:**
- `webhook_id` (string, required): ID of webhook to test

**Returns:**
```json
{
  "webhook_id": "string",
  "url": "string",
  "status": "success",
  "retries": 0,
  "error": null,
  "message": "Test notification sent to ... Status: success"
}
```

## Retry Logic

Webhook delivery includes automatic retry logic:

1. **Initial attempt** — Send notification immediately
2. **1st retry** — Wait 1 second, try again
3. **2nd retry** — Wait 4 seconds, try again
4. **3rd retry** — Wait 16 seconds, try again

**When retries stop:**
- HTTP 2xx or 3xx response → success (no retry needed)
- HTTP 4xx response → failure (don't retry, client error)
- HTTP 5xx response → retry up to 3 times

**Error handling:**
- Connection timeout → retry
- Network error → retry
- DNS failure → retry
- After 3 retries → mark as failed

## Headers

Every webhook notification includes these HTTP headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Type` | `application/json` | Request body format |
| `X-Loom-Signature` | `sha256=<hash>` | HMAC-SHA256 signature for verification |
| `X-Loom-Event` | `tool.completed` | Event type |
| `X-Loom-Webhook-ID` | `<webhook-id>` | Webhook ID |
| `User-Agent` | `Loom/1.0` | Loom service identifier |

## Examples

### Python (Flask)

```python
from flask import Flask, request
import json
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "my-webhook-secret"

def verify_signature(body: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-Loom-Signature", "")
    
    # Verify signature
    if not verify_signature(request.data, signature):
        return {"error": "invalid signature"}, 401
    
    # Parse and handle event
    payload = request.json
    event = payload["event"]
    
    if event == "tool.completed":
        print(f"Tool {payload['payload']['tool_name']} completed in {payload['payload']['duration']}s")
    elif event == "tool.failed":
        print(f"Tool {payload['payload']['tool_name']} failed: {payload['payload']['message']}")
    
    return {"ok": True}, 200

if __name__ == "__main__":
    app.run(port=3000)
```

### Node.js (Express)

```javascript
const express = require("express");
const crypto = require("crypto");

const app = express();
const WEBHOOK_SECRET = "my-webhook-secret";

app.use(express.raw({ type: "application/json" }));

function verifySignature(body, signature) {
  const expected = "sha256=" + crypto
    .createHmac("sha256", WEBHOOK_SECRET)
    .update(body)
    .digest("hex");
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}

app.post("/webhook", (req, res) => {
  const signature = req.headers["x-loom-signature"] || "";
  
  try {
    if (!verifySignature(req.body, signature)) {
      return res.status(401).json({ error: "invalid signature" });
    }
    
    const payload = JSON.parse(req.body);
    const event = payload.event;
    
    if (event === "tool.completed") {
      console.log(`Tool ${payload.payload.tool_name} completed`);
    } else if (event === "tool.failed") {
      console.log(`Tool ${payload.payload.tool_name} failed`);
    }
    
    res.json({ ok: true });
  } catch (error) {
    console.error("Webhook error:", error);
    res.status(400).json({ error: error.message });
  }
});

app.listen(3000, () => console.log("Webhook server on :3000"));
```

### curl Testing

```bash
# Register webhook
WEBHOOK_ID=$(curl -s -X POST http://localhost:8787/mcp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/webhook",
    "events": ["tool.completed"]
  }' | jq -r '.webhook_id')

# List webhooks
curl http://localhost:8787/mcp/webhook?action=list

# Test webhook
curl -X POST http://localhost:8787/mcp/webhook/$WEBHOOK_ID \
  -H "Content-Type: application/json" \
  -d '{"action": "test"}'

# Unregister webhook
curl -X DELETE http://localhost:8787/mcp/webhook/$WEBHOOK_ID
```

## Best Practices

1. **Verify signatures** — Always verify the HMAC-SHA256 signature on incoming webhooks
2. **Use HTTPS** — Always register webhooks with `https://` URLs
3. **Keep secrets safe** — Never commit webhook secrets to git
4. **Handle duplicates** — Webhooks may be delivered multiple times; use idempotent operations
5. **Set timeouts** — Respond to webhooks within 10 seconds
6. **Log everything** — Log all webhook activity for debugging and auditing
7. **Rate limiting** — Be prepared to handle high-frequency events during bulk operations

## Monitoring & Troubleshooting

### Check Webhook Status

```python
from loom.webhooks import get_webhook_manager

manager = get_webhook_manager()
webhook = await manager.get_webhook("webhook_id_here")

print(f"Success count: {webhook.success_count}")
print(f"Failure count: {webhook.failure_count}")
print(f"Last triggered: {webhook.last_triggered}")
```

### Common Issues

**Webhook not receiving notifications:**
- Verify webhook is active: `research_webhook_list`
- Verify URL is accessible from Loom server
- Check for network/firewall issues
- Enable HTTPS for production URLs

**Signature verification fails:**
- Ensure you're using the correct secret
- Verify body is not modified (use raw request body)
- Check for encoding issues (UTF-8)

**Timeouts:**
- Ensure webhook endpoint responds within 10 seconds
- Move long processing to background jobs
- Use webhook queue if endpoint is slow

## Integration Examples

### Slack Notifications

```python
import json
import httpx

async def send_to_slack(event: dict, webhook_url: str):
    """Send webhook event to Slack."""
    payload_data = event["payload"]
    
    if event["event"] == "tool.completed":
        text = f"✅ {payload_data['tool_name']} completed in {payload_data['duration']}s"
    elif event["event"] == "tool.failed":
        text = f"❌ {payload_data['tool_name']} failed: {payload_data['message']}"
    else:
        text = f"📌 {event['event']}"
    
    async with httpx.AsyncClient() as client:
        await client.post(
            webhook_url,
            json={"text": text}
        )
```

### Database Logging

```python
async def log_to_database(event: dict, db_connection):
    """Log webhook event to database."""
    await db_connection.execute(
        """
        INSERT INTO webhook_events
        (event_type, tool_name, timestamp, payload)
        VALUES (?, ?, ?, ?)
        """,
        (
            event["event"],
            event["payload"].get("tool_name", "unknown"),
            event["timestamp"],
            json.dumps(event["payload"]),
        ),
    )
```

### External Service Integration

```python
async def trigger_workflow(event: dict, workflow_api: str):
    """Trigger external workflow on tool completion."""
    if event["event"] == "tool.completed":
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{workflow_api}/workflows/run",
                json={
                    "workflow": "process_tool_results",
                    "tool": event["payload"]["tool_name"],
                    "timestamp": event["timestamp"],
                },
            )
```

## Performance Considerations

- Webhook delivery is **non-blocking** — notifications are sent concurrently
- Up to 10 concurrent HTTP connections per manager instance
- 10-second timeout per webhook request
- Retries don't block tool execution (fire-and-forget)
- Memory usage: ~500 bytes per registered webhook

## Security

- All webhook secrets are hashed before storage
- Signatures prevent tampering with webhook body
- HTTPS required for production URLs
- IP allowlisting can be added via custom middleware
- Rate limiting on webhook registration prevents abuse
