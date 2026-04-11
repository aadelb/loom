# Persistent Browser Sessions — Deep Dive

This guide covers the advanced features and architecture of Loom's persistent browser session system for handling login-walled content, stateful workflows, and session reuse.

## When to Use Sessions

Sessions maintain browser state (cookies, localStorage, DOM) across multiple `research_fetch` calls:

- **Gated academic content** — HuggingFace model cards (requires login), OpenReview PDFs, vendor documentation behind SSO
- **Login workflows** — Auto-login to sites, then reuse the session for multiple fetches
- **Stateful crawling** — Maintain context across a multi-step browsing flow
- **Cookie persistence** — Avoid re-logging in for every fetch
- **Performance** — Reusing an open browser context is faster than opening a new one per request

Session URLs are never exposed to Claude Code; only a handle (string name) is returned.

## Architecture

### Session Storage

Sessions are stored in `LOOM_SESSIONS_DIR` (default `/var/lib/loom/sessions` on systemd, `/app/sessions` in Docker, or `/tmp/.loom-sessions` when running locally).

Directory structure:

```
sessions/
├── session_name_1/
│   ├── profile.db          # Playwright browser profile (cookies, etc.)
│   ├── metadata.json       # Session metadata (created_at, ttl_seconds, etc.)
│   └── browser.lock        # Lock file while session is in use
├── session_name_2/
│   └── ...
└── sessions.db             # SQLite index of all sessions
```

Each session is isolated in its own directory with a session-specific browser context and profile.

### Session Lifecycle

1. **Open** — `research_session_open()` creates a new BrowserContext, optionally logs in, returns session handle
2. **Reuse** — `research_fetch(..., session="handle")` reuses the context across multiple calls
3. **Eviction** — LRU: if 8+ active sessions exist, the least-recently-used is closed
4. **Close** — `research_session_close("handle")` explicitly closes the session
5. **Expiry** — Sessions with TTL past 0 are eligible for cleanup on next operation

### LRU Eviction

If you open more than 8 simultaneous sessions, Loom automatically closes the least-recently-used one (lowest `last_accessed` timestamp in metadata.json). This prevents unbounded browser process growth.

In-flight calls are protected: if a session is being used in a concurrent fetch, it is not evicted.

### Persistence Across Restart

Session metadata is persisted in `/data/sessions/sessions.db` (SQLite). When Loom restarts:

1. Metadata is loaded from SQLite
2. BrowserContext is lazy-instantiated on first use
3. Cookies and profile state are restored from the profile directory

This allows session reuse across Loom server restarts.

## Session Security

### Name Validation

Session names must match the regex `^[a-z0-9_-]{1,32}$`:

- Lowercase alphanumeric, underscore, dash
- 1–32 characters max

This bounds all filesystem operations and prevents path traversal attacks.

### Profile Isolation

Each session has its own Chromium/Firefox user profile, preventing cookie/data leakage between sessions.

### URL Security

Session handles are opaque strings (e.g., `"hf-login"` or `"openreview"`). They are never exposed to external parties; they are local identifiers only.

## Using Sessions

### Basic Session (No Login)

```python
# Open a session
result = research_session_open(
    name="basic-session",
    browser="playwright",
    ttl_seconds=3600  # 1 hour
)
# result = {"name": "basic-session", "session_id": "...", "status": "open", ...}

# Use it to fetch from a site
content1 = research_fetch(
    url="https://example.com/page1",
    session="basic-session"
)

# Cookies are persisted; fetch another page
content2 = research_fetch(
    url="https://example.com/page2",
    session="basic-session"
)

# Close when done
research_session_close("basic-session")
```

### Logged-In Session

```python
# Open a session and auto-login with a script
result = research_session_open(
    name="huggingface",
    browser="camoufox",  # Stealth mode for better compatibility
    login_url="https://huggingface.co/login",
    login_script="""
        // JavaScript to auto-login
        document.querySelector('input[name="username"]').value = 'user@example.com';
        document.querySelector('input[name="password"]').value = 'password';
        document.querySelector('button[type="submit"]').click();
        await new Promise(resolve => setTimeout(resolve, 5000));  // Wait 5s for login
    """,
    ttl_seconds=86400  # 24 hours
)
# result = {"status": "logged_in", ...}

# Now fetch gated content
model_card = research_fetch(
    url="https://huggingface.co/meta-llama/Llama-2-7b-hf",
    session="huggingface"
)

# Reuse many times; login script was run once
for i in range(10):
    content = research_fetch(
        url=f"https://huggingface.co/models?page={i}",
        session="huggingface"
    )
```

### Manual Login

For interactive login, set `headless=False`:

```python
# Open with visible window
result = research_session_open(
    name="manual-login",
    browser="camoufox",
    headless=False,  # Shows browser window
    login_url="https://example.com/login",
    ttl_seconds=3600
)

# Browser window opens; manually log in, then close the window
# The session is now logged in

# Use it
content = research_fetch(
    url="https://example.com/protected",
    session="manual-login"
)

research_session_close("manual-login")
```

### Session with Initial Cookies

Pre-set cookies before opening:

```python
# Get cookies from somewhere (e.g., export from browser)
cookies = {
    "sessionid": "abc123...",
    "csrf_token": "xyz789...",
}

result = research_session_open(
    name="pre-auth",
    browser="playwright",
    initial_cookies=cookies,
    ttl_seconds=3600
)

# Fetch; the cookies are already set
content = research_fetch(
    url="https://example.com/protected",
    session="pre-auth"
)
```

## Session Limits

| Constraint | Value | Reason |
|-----------|-------|--------|
| Max concurrent sessions | 8 | Limits browser process overhead; LRU evicts beyond this |
| Max session name length | 32 chars | Filesystem safety |
| TTL range | 60–86400 seconds | 1 minute to 24 hours |
| Session idle eviction | TTL expires if not used | Automatic cleanup of stale sessions |
| Max concurrent fetches per session | Unlimited | Single BrowserContext is thread-safe |

## Login Script Tips

### Avoid Hardcoding Credentials

Use environment variables or secret files:

```python
import os

login_script = f"""
    document.querySelector('input[name="username"]').value = '{os.environ["SITE_USER"]}';
    document.querySelector('input[name="password"]').value = '{os.environ["SITE_PASSWORD"]}';
    document.querySelector('button[type="submit"]').click();
    await new Promise(resolve => setTimeout(resolve, 5000));
"""

result = research_session_open(
    name="env-login",
    login_script=login_script,
)
```

### Handle Dynamic Elements

If the login form changes based on load timing, wait for it:

```python
login_script = """
    await page.waitForSelector('input[name="username"]', { timeout: 10000 });
    await page.fill('input[name="username"]', 'user@example.com');
    await page.fill('input[name="password"]', 'password');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle2' });  // Wait for page load
"""
```

### 2FA (Two-Factor Authentication)

If the site requires 2FA, manual login with `headless=False` is recommended:

```python
result = research_session_open(
    name="2fa-site",
    browser="camoufox",
    login_url="https://example.com/login",
    headless=False,  # You'll see the browser; manually complete 2FA
    ttl_seconds=3600
)
```

## Session Listing and Cleanup

### List Active Sessions

```python
result = research_session_list()
# result = [
#     {
#         "name": "huggingface",
#         "browser": "camoufox",
#         "created_at": "2025-04-11T10:00:00Z",
#         "expires_at": "2025-04-12T10:00:00Z",
#         "last_accessed": "2025-04-11T10:30:00Z",
#         "status": "open"
#     },
#     ...
# ]
```

### Close a Session

```python
result = research_session_close("huggingface")
# result = {"message": "Session 'huggingface' closed", "status": "closed"}
```

### Auto-Cleanup

Sessions with `expires_at` in the past are automatically cleaned up on the next Loom startup or on next session operation.

## Performance Considerations

### Startup Time

First use of a session incurs BrowserContext initialization (~2–5 seconds for Playwright, ~5–10 seconds for Camoufox due to stealth initialization). Reusing the same session for multiple fetches amortizes this cost.

### Memory

Each open BrowserContext uses ~100–300 MB of RAM (varies by browser and plugins). Limit concurrent sessions to stay within systemd/Docker memory limits.

### Cookie Persistence

Cookies and localStorage are automatically persisted to the profile directory. No manual save/load needed.

## Troubleshooting

### Login Script Fails

Check the script's syntax and wait times:

```python
result = research_session_open(
    name="debug-login",
    browser="camoufox",
    headless=False,  # Watch the browser window
    login_url="https://example.com/login",
    login_script="... (your script) ...",
)
```

Watch the browser window to see if elements are found and clicks work.

### Session Not Found

If you get "Session 'xyz' not found", either:

1. The session name is wrong (typo)
2. The session expired (TTL passed)
3. It was evicted due to LRU overflow

Use `research_session_list()` to see active sessions.

### Fetch Hangs on Logged-In Session

The site might have started a new login prompt (session expired on the server). Close and re-open:

```python
research_session_close("huggingface")
result = research_session_open(
    name="huggingface",
    login_script="...",
)
```

## Related Documentation

- [docs/tools/research_sessions.md](../tools/research_sessions.md) — Tool reference (research_session_open, research_session_list, research_session_close)
- [docs/tools/research_fetch.md](../tools/research_fetch.md) — research_fetch tool (use with `session` parameter)
- [docs/deployment/docker.md](../deployment/docker.md) — Docker volume setup for sessions persistence
