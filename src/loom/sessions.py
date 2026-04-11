"""Session management for persistent browser contexts.

Supports Camoufox, Chromium, and Firefox with configurable TTL.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from mcp.types import TextContent
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
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
    """Load session metadata from disk."""
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
        from camoufox import Camoufox

        camou = Camoufox()
        return await camou.launch()
    else:
        playwright = await async_playwright().start()
        if browser_type == "chromium":
            return await playwright.chromium.launch()
        else:  # firefox
            return await playwright.firefox.launch()


async def open_session(
    name: str,
    browser: Literal["camoufox", "chromium", "firefox"] = "camoufox",
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
        browser=browser,  # type: ignore[arg-type]
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
            # Launch browser
            browser_instance = await _get_browser(params.browser)

            # Create context with persistent storage
            user_data_dir = _get_session_dir() / name
            user_data_dir.mkdir(exist_ok=True)

            context = await browser_instance.new_context(
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
            if name in _metadata:
                del _metadata[name]
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
        try:
            await _sessions[name].close()
            del _sessions[name]
            if name in _metadata:
                del _metadata[name]
            _delete_metadata(name)
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
            except Exception:
                pass

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
    for name, ctx in _sessions.items():
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

    # Persisted sessions on disk
    session_dir = _get_session_dir()
    for meta_path in session_dir.glob("*.json"):
        name = meta_path.stem
        if name in _sessions:
            continue  # Already listed as active

        try:
            meta = json.loads(meta_path.read_text())
            # Check if expired
            created = datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
            age = time.time() - created.timestamp()
            ttl = meta.get("ttl_seconds", SESSION_TTL_SECONDS)
            status = "expired" if age > ttl else "persisted"

            results.append(
                {
                    "name": name,
                    "status": status,
                    "browser": meta.get("browser", "unknown"),
                    "created_at": meta["created_at"],
                    "last_used": meta.get("last_used"),
                    "ttl_seconds": ttl,
                }
            )
        except Exception as e:
            logger.warning("session_meta_load_failed path=%s error=%s", meta_path, e)

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
    valid_items = [(name, meta) for name, meta in _metadata.items() if get_created_at((name, meta)) is not None]
    
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


def research_session_list() -> list[dict[str, Any]]:
    """List active persistent browser sessions."""
    return list_sessions()
