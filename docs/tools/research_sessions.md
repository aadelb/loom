# research_sessions

Persistent browser session management with SQLite metadata tracking and LRU eviction.

## Session management overview

Sessions are long-lived browser profiles that persist across multiple tool calls. Each session is:

- Named with a strict allow-list: `^[a-z0-9_-]{1,32}$` (lowercase, no spaces)
- Stored in `LOOM_SESSIONS_DIR/` (default `./sessions/`)
- Tracked in SQLite DB at `LOOM_SESSIONS_DIR/sessions.db`
- Subject to LRU eviction when 8+ sessions are active
- Automatically expired after TTL (default 1 hour)

## research_session_open

Open a new browser session or retrieve an existing one.

### Synopsis

```python
result = await session.call_tool("research_session_open", {
    "name": "my-session",
    "browser": "camoufox"
})
```

### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| name | string | required | Session name (must match `^[a-z0-9_-]{1,32}$`) |
| browser | string | camoufox | Browser engine: `camoufox` \| `playwright` \| `patchright` |
| headless | bool | true | Run in headless mode |
| accept_language | string | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header for session |
| login_url | string | null | URL to navigate for login (optional) |
| login_script | string | null | JS snippet to execute after login (e.g., complete login form) |
| initial_cookies | dict | null | Pre-populate session cookies |
| ttl_seconds | int | 3600 | Session time-to-live in seconds (60-86400; default 1 hour) |

### Returns

```json
{
  "name": "my-session",
  "browser": "camoufox",
  "status": "opened",
  "created_at": "2026-04-11T20:36:00.123456Z",
  "expires_at": "2026-04-11T21:36:00.123456Z",
  "ttl_seconds": 3600
}
```

On error:

```json
{
  "error": "session name must match ^[a-z0-9_-]{1,32}$"
}
```

## research_session_list

List all active sessions.

### Synopsis

```python
result = await session.call_tool("research_session_list", {})
```

### Returns

```json
[
  {
    "name": "my-session",
    "browser": "camoufox",
    "created_at": "2026-04-11T20:36:00.123456Z",
    "last_used_at": "2026-04-11T20:36:15.654321Z",
    "expires_at": "2026-04-11T21:36:00.123456Z",
    "ttl_seconds": 3600
  },
  {
    "name": "other-session",
    "browser": "playwright",
    "created_at": "2026-04-11T20:35:00.000000Z",
    "last_used_at": "2026-04-11T20:35:30.000000Z",
    "expires_at": "2026-04-11T21:35:00.000000Z",
    "ttl_seconds": 3600
  }
]
```

## research_session_close

Close and clean up a session.

### Synopsis

```python
result = await session.call_tool("research_session_close", {
    "name": "my-session"
})
```

### Parameters

| Name | Type | Default | Purpose |
|---|---|---|---|
| name | string | required | Session name to close |

### Returns

```json
{
  "name": "my-session",
  "status": "closed",
  "closed_at": "2026-04-11T20:37:00.123456Z"
}
```

On error:

```json
{
  "error": "session not found: my-session"
}
```

## Session lifecycle

### Login workflow

```python
async with ClientSession(read, write) as s:
    # Open session with login
    session_result = await s.call_tool("research_session_open", {
        "name": "github-session",
        "browser": "camoufox",
        "login_url": "https://github.com/login",
        "login_script": """
            document.querySelector('input[name="login"]').value = 'user';
            document.querySelector('input[name="password"]').value = 'pass';
            document.querySelector('button[type="submit"]').click();
        """,
        "ttl_seconds": 7200
    })
    
    # Reuse session in fetch calls (future feature)
    # fetch_result = await s.call_tool("research_fetch", {
    #     "url": "https://github.com/settings",
    #     "session": "github-session"
    # })
```

### Session reuse across multiple fetches

```python
async with ClientSession(read, write) as s:
    # Open session
    await s.call_tool("research_session_open", {
        "name": "api-session",
        "initial_cookies": {"api_token": "secret..."}
    })
    
    # Make authenticated fetches (when session wiring is complete)
    # results = await s.call_tool("research_spider", {
    #     "urls": ["https://api.example.com/data1", "https://api.example.com/data2"],
    #     "session": "api-session"
    # })
```

### Session cleanup

```python
async with ClientSession(read, write) as s:
    # List all active sessions
    sessions = await s.call_tool("research_session_list", {})
    
    # Close old sessions
    for sess in sessions:
        if sess["name"].startswith("temp-"):
            await s.call_tool("research_session_close", {"name": sess["name"]})
```

## Configuration

- **LOOM_SESSIONS_DIR**: Directory for session storage (default `./sessions/`)
- **Session auto-cleanup**: Sessions expired by TTL are removed on next server start
- **LRU eviction**: When 8+ sessions are active, least-recently-used sessions are evicted

## Errors

- `session name must match ^[a-z0-9_-]{1,32}$` — Invalid session name
- `session not found: <name>` — Session does not exist (research_session_close only)
- `session already exists: <name>` — Name collision (research_session_open only; reuse existing instead)
- `ttl_seconds must be 60-86400` — TTL outside valid range
- `login_url_rejected: <reason>` — login_url fails SSRF validation

## Related tools

- `research_fetch` — Use with session parameter (when wired)
- `research_spider` — Use with session parameter (when wired)
- `research_camoufox` — Use with session parameter (when wired)
- `research_botasaurus` — Use with session parameter (when wired)
