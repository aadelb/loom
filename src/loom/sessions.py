"""Session management for persistent browser contexts.

Supports Camoufox, Chromium, and Firefox with configurable TTL.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import sqlite3
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

from mcp.types import TextContent
from playwright.async_api import Browser, BrowserContext, async_playwright
from pydantic import BaseModel, Field

from loom.config import get_config
from loom.params import SessionOpenParams

# Default session TTL in seconds (1 hour). Individual sessions may override.
SESSION_TTL_SECONDS = 3600

logger = logging.getLogger("loom.sessions")

# Global session registry
_sessions: dict[str, BrowserContext] = {}
_metadata: dict[str, dict[str, Any]] = defaultdict(dict)
_lock = asyncio.Lock()


class SessionMetadata(BaseModel):
    """Metadata for a browser session."""

    name: str
    browser: Literal["camoufox", "chromium", "firefox"]
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_used: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    ttl_seconds: int = SESSION_TTL_SECONDS
    login_url: str | None = None
    user_data_dir: Path | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


def _get_session_dir() -> Path:
    """Get directory for session storage."""
    config = get_config()
    base = Path(config.get("SESSION_DIR", "~/.loom/sessions")).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    return base


def _load_metadata(name: str) -> SessionMetadata | None:
    """Load session metadata from disk.

    Note: Uses sync Path.read_text() which is blocking I/O. This is called
    from list_sessions() (sync context), so wrapping in executor would be
    complex. Acceptable here since JSON files are small (<10KB typically).
    """
    meta_path = _get_session_dir() / f"{name}.json"
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text())
        return SessionMetadata(**data)
    except Exception as e:
        logger.warning("session_meta_load_failed name=%s error=%s", name, e)
        return None


def _save_metadata(meta: SessionMetadata) -> None:
    """Save session metadata to disk."""
    meta_path = _get_session_dir() / f"{meta.name}.json"
    meta_path.write_text(meta.model_dump_json(indent=2))


def _delete_metadata(name: str) -> None:
    """Delete session metadata from disk."""
    meta_path = _get_session_dir() / f"{name}.json"
    if meta_path.exists():
        meta_path.unlink()


async def _cleanup_expired() -> None:
    """Remove expired sessions from registry."""
    now = time.time()
    expired = []

    for name, meta_raw in _metadata.items():
        if meta_raw:
            try:
                meta = SessionMetadata(**meta_raw)
                created = datetime.fromisoformat(meta.created_at.replace("Z", "+00:00"))
                age = now - created.timestamp()
                if age > meta.ttl_seconds:
                    expired.append(name)
            except Exception:
                expired.append(name)

    for name in expired:
        await close_session(name)


async def _get_browser(
    browser_type: Literal["camoufox", "chromium", "firefox"],
) -> Browser:
    """Launch or reuse a Playwright browser instance."""
    # Import here to avoid circular imports
    if browser_type == "camoufox":
        from camoufox.async_api import AsyncNewBrowser

        # camoufox is untyped third-party — narrow to Any at the boundary
        playwright = await async_playwright().start()
        launched: Browser = await AsyncNewBrowser(playwright)  # type: ignore[no-untyped-call]
        return launched
    else:
        playwright = await async_playwright().start()
        if browser_type == "chromium":
            return await playwright.chromium.launch()
        else:  # firefox
            return await playwright.firefox.launch()


async def open_session(
    name: str,
    browser: Literal["camoufox", "chromium", "firefox"] | str = "camoufox",
    ttl_seconds: int = SESSION_TTL_SECONDS,
    login_url: str | None = None,
    login_script: str | None = None,
) -> dict[str, Any]:
    """Create or reuse a persistent browser session.

    Args:
        name: unique session name
        browser: browser type
        ttl_seconds: time-to-live in seconds
        login_url: optional URL to navigate to after opening
        login_script: optional JavaScript to run after loading login_url

    Returns:
        Dict with session info and status.
    """
    params = SessionOpenParams(
        name=name,
        browser=browser,  # type: ignore[arg-type] # camoufox type mismatch
        ttl_seconds=ttl_seconds,
        login_url=login_url,
        login_script=login_script,
    )

    async with _lock:
        # Cleanup expired sessions first
        await _cleanup_expired()

        # Check if already exists
        if name in _sessions:
            logger.info("session_reuse name=%s", name)
            _metadata[name]["last_used"] = datetime.now(UTC).isoformat()
            return {
                "name": name,
                "status": "reused",
                "browser": browser,
                "created_at": _metadata[name].get("created_at"),
                "ttl_seconds": ttl_seconds,
            }

        # Create new session
        logger.info("session_create name=%s browser=%s", name, browser)
        try:
            # Map the stealth-library literal (camoufox|playwright|patchright)
            # onto the browser engine literal (camoufox|chromium|firefox) that
            # _get_browser accepts. Both patchright and playwright drive
            # Chromium under the hood, so they map to "chromium".
            _engine_map: dict[str, Literal["camoufox", "chromium", "firefox"]] = {
                "camoufox": "camoufox",
                "playwright": "chromium",
                "patchright": "chromium",
                "chromium": "chromium",
                "firefox": "firefox",
            }
            engine: Literal["camoufox", "chromium", "firefox"] = _engine_map.get(
                params.browser, "chromium"
            )
            browser_instance = await _get_browser(engine)

            # Create context with persistent storage
            user_data_dir = _get_session_dir() / name
            user_data_dir.mkdir(exist_ok=True)

            context = await browser_instance.new_context(  # type: ignore[call-arg]
                user_data_dir=str(user_data_dir),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="America/New_York",
            )

            # Store
            _sessions[name] = context
            meta = SessionMetadata(
                name=name,
                browser=browser,
                ttl_seconds=ttl_seconds,
                login_url=login_url,
                user_data_dir=user_data_dir,
            )
            _metadata[name] = meta.model_dump()
            _save_metadata(meta)

            # Optional login flow
            if login_url:
                page = await context.new_page()
                try:
                    await page.goto(login_url, wait_until="networkidle")
                    if login_script:
                        await page.evaluate(login_script)
                    logger.info("session_login_complete name=%s url=%s", name, login_url)
                except Exception as e:
                    logger.warning("session_login_failed name=%s error=%s", name, e)
                finally:
                    await page.close()

            return {
                "name": name,
                "status": "created",
                "browser": browser,
                "created_at": meta.created_at,
                "ttl_seconds": ttl_seconds,
                "user_data_dir": str(user_data_dir),
            }

        except Exception as e:
            logger.exception("session_create_failed name=%s", name)
            # Cleanup on failure
            if name in _sessions:
                await _sessions[name].close()
                del _sessions[name]
            _metadata.pop(name, None)
            _delete_metadata(name)
            return {"name": name, "error": str(e), "status": "failed"}


async def close_session(name: str) -> dict[str, Any]:
    """Close a browser session and clean up resources.

    Args:
        name: session name

    Returns:
        Dict with closure status.
    """
    async with _lock:
        if name not in _sessions:
            return {"name": name, "status": "not_found"}

        logger.info("session_close name=%s", name)
        session = _sessions.pop(name)
        _metadata.pop(name, None)
        _delete_metadata(name)

        try:
            await session.close()
            return {"name": name, "status": "closed"}
        except Exception as e:
            logger.warning("session_close_failed name=%s error=%s", name, e)
            return {"name": name, "status": "error", "error": str(e)}


async def get_session(name: str) -> BrowserContext | None:
    """Get a browser session by name, updating last_used timestamp.

    Args:
        name: session name

    Returns:
        BrowserContext if found and valid, else None.
    """
    async with _lock:
        # Cleanup expired sessions first (Issue #182)
        await _cleanup_expired()

        if name not in _sessions:
            return None

        # Check expiry
        if name in _metadata:
            meta_raw = _metadata[name]
            try:
                meta = SessionMetadata(**meta_raw)
                created = datetime.fromisoformat(meta.created_at.replace("Z", "+00:00"))
                age = time.time() - created.timestamp()
                if age > meta.ttl_seconds:
                    logger.info("session_expired name=%s age=%d", name, age)
                    await close_session(name)
                    return None
            except Exception as e:
                logger.debug("session_load_fallback name=%s error=%s", name, e)

        # Update last used
        _metadata[name]["last_used"] = datetime.now(UTC).isoformat()
        return _sessions[name]


def list_sessions() -> list[dict[str, Any]]:
    """List all active and persisted sessions.

    Returns:
        List of session info dicts.
    """
    results = []

    # Active sessions
    for name, _ctx in _sessions.items():
        meta = _metadata.get(name, {})
        results.append(
            {
                "name": name,
                "status": "active",
                "browser": meta.get("browser", "unknown"),
                "created_at": meta.get("created_at"),
                "last_used": meta.get("last_used"),
                "ttl_seconds": meta.get("ttl_seconds", SESSION_TTL_SECONDS),
            }
        )

    # Persisted sessions on disk (using _load_metadata for consistent parsing)
    session_dir = _get_session_dir()
    for meta_path in session_dir.glob("*.json"):
        name = meta_path.stem
        if name in _sessions:
            continue

        meta_obj = _load_metadata(name)
        if meta_obj is None:
            continue

        try:
            created = datetime.fromisoformat(meta_obj.created_at.replace("Z", "+00:00"))
            age = time.time() - created.timestamp()
            status = "expired" if age > meta_obj.ttl_seconds else "persisted"

            results.append(
                {
                    "name": name,
                    "status": status,
                    "browser": meta_obj.browser,
                    "created_at": meta_obj.created_at,
                    "last_used": meta_obj.last_used,
                    "ttl_seconds": meta_obj.ttl_seconds,
                }
            )
        except Exception as e:
            logger.warning("session_meta_parse_failed name=%s error=%s", name, e)

    # Sort by name
    results.sort(key=lambda x: x["name"])
    return results


async def _find_oldest_session() -> str | None:
    """Find the oldest active session by creation time."""
    if not _metadata:
        return None

    def get_created_at(item: tuple[str, dict[str, Any]]) -> Any | None:
        """Extract creation timestamp from metadata."""
        _, meta = item
        if "created_at" in meta:
            try:
                return datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
            except (ValueError, KeyError):
                return None
        return None

    # Filter out items without valid timestamps
    valid_items = [
        (name, meta) for name, meta in _metadata.items() if get_created_at((name, meta)) is not None
    ]

    if not valid_items:
        return None

    # Find the session with minimum creation time
    oldest = min(valid_items, key=lambda x: cast(datetime, get_created_at(x)))
    return oldest[0]


async def cleanup_sessions(max_sessions: int = 10) -> dict[str, Any]:
    """Enforce a maximum number of active sessions by closing oldest ones.

    Args:
        max_sessions: maximum number of sessions to keep

    Returns:
        Dict with cleanup results.
    """
    async with _lock:
        current = len(_sessions)
        if current <= max_sessions:
            return {
                "current_sessions": current,
                "max_sessions": max_sessions,
                "closed": [],
                "status": "no_cleanup_needed",
            }

        to_close = current - max_sessions
        closed = []

        for _ in range(to_close):
            oldest = await _find_oldest_session()
            if not oldest:
                break

            result = await close_session(oldest)
            if result.get("status") == "closed":
                closed.append(oldest)

        return {
            "current_sessions": len(_sessions),
            "max_sessions": max_sessions,
            "closed": closed,
            "closed_count": len(closed),
            "status": "cleanup_complete",
        }


async def cleanup_all_sessions() -> dict[str, Any]:
    """Close ALL active sessions. Called during server shutdown."""
    async with _lock:
        names = list(_sessions.keys())
    closed: list[str] = []
    errors: list[str] = []
    for name in names:
        try:
            result = await close_session(name)
            if result.get("status") == "closed":
                closed.append(name)
            elif result.get("error"):
                errors.append(f"{name}: {result['error']}")
        except Exception as e:
            logger.error("session_cleanup_failed name=%s error=%s", name, e)
            errors.append(f"{name}: {e}")
    logger.info("cleanup_all_sessions closed=%d errors=%d", len(closed), len(errors))
    return {"closed": closed, "errors": errors}


def tool_session_open(
    name: str,
    browser: str = "camoufox",
    ttl_seconds: int = SESSION_TTL_SECONDS,
    login_url: str | None = None,
    login_script: str | None = None,
) -> list[TextContent]:
    """MCP wrapper for open_session."""
    result = asyncio.run(
        open_session(
            name=name,
            browser=cast(Literal["camoufox", "chromium", "firefox"], browser),
            ttl_seconds=ttl_seconds,
            login_url=login_url,
            login_script=login_script,
        )
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_session_close(name: str) -> list[TextContent]:
    """MCP wrapper for close_session."""
    result = asyncio.run(close_session(name))
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def tool_session_list() -> list[TextContent]:
    """MCP wrapper for list_sessions."""
    result = list_sessions()
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ─── Public MCP tool entrypoints (registered by server.py) ───────────────────
async def research_session_open(
    name: str,
    browser: Literal["camoufox", "chromium", "firefox"] = "camoufox",
    ttl_seconds: int = SESSION_TTL_SECONDS,
    login_url: str | None = None,
    login_script: str | None = None,
) -> dict[str, Any]:
    """Open (or reuse) a persistent browser session."""
    return await open_session(
        name=name,
        browser=browser,
        ttl_seconds=ttl_seconds,
        login_url=login_url,
        login_script=login_script,
    )


async def research_session_close(name: str) -> dict[str, Any]:
    """Close a persistent browser session by name."""
    return await close_session(name)


def research_session_list() -> dict[str, Any]:
    """List active persistent browser sessions.

    Returns a dict wrapper (not a bare list) so FastMCP always serializes
    it as a non-empty TextContent even when there are zero sessions.
    """
    sessions = list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


# ─── SessionManager class for test compatibility ──────────────────────────────


def _validate_session_name(name: Any) -> None:
    """Validate session name against allow-list regex.

    Raises ValueError if:
    - Not a string
    - Contains uppercase letters
    - Contains spaces, dots, or special chars
    - Longer than 32 chars
    """
    if not isinstance(name, str):
        raise ValueError("Session name must be a string")

    pattern = r"^[a-z0-9_-]{1,32}$"
    if not re.match(pattern, name):
        raise ValueError(
            f"Session name must match {pattern} (lowercase alphanumeric, underscore, hyphen, max 32 chars)"
        )


class SessionManager:
    """Manages browser sessions with SQLite persistence and LRU eviction.

    Singleton pattern: use get_session_manager() to get the shared instance.
    For testing, set SessionManager._instance = None to reset.
    """

    _instance: ClassVar[SessionManager | None] = None
    _lock_map: ClassVar[dict[str, asyncio.Semaphore]] = {}

    def __init__(self) -> None:
        """Initialize SessionManager, creating DB if needed."""
        base_dir = os.environ.get("LOOM_SESSIONS_DIR", "~/.loom/sessions")
        base_path = Path(base_dir).expanduser()
        # Reject path traversal in LOOM_SESSIONS_DIR (cf. sessions audit HIGH #4)
        if ".." in base_path.parts:
            raise ValueError(f"LOOM_SESSIONS_DIR must not contain '..' (got {base_path!s})")
        self.base_dir = base_path.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Enforce 0700 on an existing dir (mkdir(mode=...) is a no-op when exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(self.base_dir, 0o700)

        self.db_path = self.base_dir / "sessions.db"
        self._init_db()

    def _init_db(self) -> None:
        """Create sessions table if not exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    name TEXT PRIMARY KEY,
                    browser TEXT NOT NULL,
                    profile_dir TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_session_lock(self, name: str) -> asyncio.Semaphore:
        """Get or create a semaphore for a session name (for serializing access)."""
        if name not in self._lock_map:
            self._lock_map[name] = asyncio.Semaphore(1)
        return self._lock_map[name]

    async def open(
        self,
        name: str,
        browser: str = "camoufox",
        ttl_seconds: int = SESSION_TTL_SECONDS,
    ) -> dict[str, Any]:
        """Open or reuse a session, updating TTL. Creates profile_dir and DB entry.

        Args:
            name: session name (validated)
            browser: browser type (default "camoufox")
            ttl_seconds: time-to-live in seconds (default SESSION_TTL_SECONDS)

        Returns:
            Dict with name, session_id, created_at, expires_at, browser, profile_dir
        """
        _validate_session_name(name)

        lock = self._get_session_lock(name)
        async with lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()

                now = datetime.now(UTC)
                expires_at = now + timedelta(seconds=ttl_seconds)
                now_iso = now.isoformat()
                expires_iso = expires_at.isoformat()

                # Check if session exists
                cursor.execute("SELECT * FROM sessions WHERE name = ?", (name,))
                existing = cursor.fetchone()

                if existing:
                    # Schema order (matches INSERT below):
                    #   [0]=name, [1]=browser, [2]=profile_dir, [3]=session_id,
                    #   [4]=created_at, [5]=last_used_at, [6]=expires_at
                    browser_existing = existing[1]
                    profile_dir = existing[2]
                    session_id = existing[3]
                    created_at = existing[4]
                    cursor.execute(
                        "UPDATE sessions SET last_used_at = ?, expires_at = ? WHERE name = ?",
                        (now_iso, expires_iso, name),
                    )
                    conn.commit()
                    return {
                        "name": name,
                        "session_id": session_id,
                        "created_at": created_at,
                        "expires_at": expires_iso,
                        "browser": browser_existing,
                        "profile_dir": profile_dir,
                    }

                # Create new session
                session_id = str(uuid.uuid4())
                profile_dir_path = self.base_dir / name
                profile_dir_path.mkdir(mode=0o700, exist_ok=True)
                profile_dir = str(profile_dir_path)

                cursor.execute(
                    """INSERT INTO sessions
                       (name, browser, profile_dir, session_id, created_at, last_used_at, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (name, browser, profile_dir, session_id, now_iso, now_iso, expires_iso),
                )
                conn.commit()

                # Check LRU eviction (max 8 sessions)
                sessions = self.list()
                if len(sessions) > 8:
                    # Evict oldest (first in list, sorted by last_used_at DESC)
                    oldest = sessions[-1]["name"]
                    await self.close(oldest)

                return {
                    "name": name,
                    "session_id": session_id,
                    "created_at": now_iso,
                    "expires_at": expires_iso,
                    "browser": browser,
                    "profile_dir": profile_dir,
                }
            finally:
                conn.close()

    async def close(self, name: str) -> dict[str, Any]:
        """Close a session, delete profile_dir and DB row.

        Args:
            name: session name

        Returns:
            Empty dict on success, or {error: "..."} on failure
        """
        lock = self._get_session_lock(name)
        async with lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT profile_dir FROM sessions WHERE name = ?", (name,))
                row = cursor.fetchone()
                if not row:
                    return {"error": "Session not found"}
                profile_dir = row[0]
                cursor.execute("DELETE FROM sessions WHERE name = ?", (name,))
                conn.commit()
            finally:
                conn.close()

            # Validate profile_dir is under base_dir before rmtree (guard against
            # DB tampering / symlink escape — sessions audit LOW #7).
            try:
                profile_path = Path(profile_dir).resolve()  # noqa: ASYNC240
                profile_path.relative_to(self.base_dir)
            except ValueError:
                logger.error(
                    "profile_dir_outside_base name=%s profile=%s base=%s",
                    name,
                    profile_dir,
                    self.base_dir,
                )
                return {}

            try:
                if profile_path.exists():
                    shutil.rmtree(profile_path)
            except Exception as e:
                logger.warning("failed_to_delete_profile_dir path=%s error=%s", profile_dir, e)

            return {}

    def list(self) -> list[dict[str, Any]]:
        """List all sessions, sorted by last_used_at DESC (newest first).

        Returns:
            List of session dicts with name, browser, profile_dir, session_id, etc.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, browser, profile_dir, session_id, created_at, last_used_at, expires_at "
                "FROM sessions ORDER BY last_used_at DESC"
            )
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append(
                    {
                        "name": row[0],
                        "browser": row[1],
                        "profile_dir": row[2],
                        "session_id": row[3],
                        "created_at": row[4],
                        "last_used_at": row[5],
                        "expires_at": row[6],
                    }
                )
            return result
        finally:
            conn.close()

    def get_context(self, name: str) -> dict[str, Any] | None:
        """Get session metadata by name, or None if not found.

        Args:
            name: session name

        Returns:
            Session dict or None
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, browser, profile_dir, session_id, created_at, last_used_at, expires_at "
                "FROM sessions WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "name": row[0],
                "browser": row[1],
                "profile_dir": row[2],
                "session_id": row[3],
                "created_at": row[4],
                "last_used_at": row[5],
                "expires_at": row[6],
            }
        finally:
            conn.close()


def get_session_manager() -> SessionManager:
    """Get or create the singleton SessionManager instance.

    Returns:
        The shared SessionManager instance
    """
    if SessionManager._instance is None:
        SessionManager._instance = SessionManager()
    return SessionManager._instance
