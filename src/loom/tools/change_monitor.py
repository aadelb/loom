"""Web page change monitoring — track and detect meaningful content changes over time."""

from __future__ import annotations

import difflib
import hashlib
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.change_monitor")

_DB_PATH = Path.home() / ".loom" / "change_monitor.db"


def _init_db() -> None:
    """Initialize SQLite database schema if not exists."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS url_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            content_preview TEXT,
            timestamp TEXT NOT NULL,
            UNIQUE(url, content_hash, timestamp)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS url_metadata (
            url TEXT PRIMARY KEY,
            first_seen TEXT NOT NULL,
            last_changed TEXT,
            check_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_url_timestamp
        ON url_snapshots (url, timestamp)
        """
    )

    conn.commit()
    conn.close()


def _fetch_content(url: str) -> str:
    """Fetch current page content via httpx."""
    try:
        response = httpx.get(
            url,
            timeout=15.0,
            headers={"User-Agent": "Loom-Research/1.0"},
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.warning("change_monitor fetch failed url=%s: %s", url[:80], e)
        raise


def _compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def _get_previous_hash(url: str) -> tuple[str | None, str | None]:
    """Get the most recent hash and timestamp for a URL.

    Returns:
        Tuple of (hash, timestamp) or (None, None) if no prior record.
    """
    conn = sqlite3.connect(_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT content_hash, timestamp
        FROM url_snapshots
        WHERE url = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (url,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0], row[1]
    return None, None


def _store_snapshot(url: str, content_hash: str, content_preview: str) -> None:
    """Store a content snapshot in the database."""
    now = datetime.now(UTC).isoformat()

    conn = sqlite3.connect(_DB_PATH)
    cursor = conn.cursor()

    # Store the snapshot
    cursor.execute(
        """
        INSERT OR IGNORE INTO url_snapshots
        (url, content_hash, content_preview, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (url, content_hash, content_preview, now),
    )

    # Update or insert metadata
    cursor.execute(
        """
        SELECT check_count, first_seen, last_changed
        FROM url_metadata
        WHERE url = ?
        """,
        (url,),
    )

    row = cursor.fetchone()
    if row:
        check_count, first_seen, last_changed = row
        new_check_count = check_count + 1
        cursor.execute(
            """
            UPDATE url_metadata
            SET check_count = ?, last_changed = ?
            WHERE url = ?
            """,
            (new_check_count, now, url),
        )
    else:
        cursor.execute(
            """
            INSERT INTO url_metadata
            (url, first_seen, last_changed, check_count)
            VALUES (?, ?, ?, ?)
            """,
            (url, now, now, 1),
        )

    conn.commit()
    conn.close()


def _compute_diff(old_content: str, new_content: str) -> tuple[str, int]:
    """Compute unified diff and count changed lines.

    Returns:
        Tuple of (diff_text, changed_line_count)
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
    )

    # Count lines that are actual changes (start with + or -)
    changed_count = sum(1 for line in diff_lines if line.startswith(("+", "-")))

    diff_text = "\n".join(diff_lines)
    return diff_text, changed_count


def _classify_change(
    old_content: str, new_content: str, changed_count: int
) -> str:
    """Classify the type of change detected."""
    old_len = len(old_content)
    new_len = len(new_content)

    if old_len == new_len:
        return "content_modified"
    elif new_len > old_len:
        return "content_added"
    else:
        return "content_removed"


def _get_metadata(url: str) -> tuple[int, str | None, str | None]:
    """Get check count and timestamps from metadata.

    Returns:
        Tuple of (check_count, first_seen, last_changed)
    """
    conn = sqlite3.connect(_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT check_count, first_seen, last_changed
        FROM url_metadata
        WHERE url = ?
        """,
        (url,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0], row[1], row[2]
    return 0, None, None


def research_change_monitor(url: str, store_result: bool = True) -> dict[str, Any]:
    """Monitor a web page for meaningful content changes.

    Fetches the current content, computes a SHA-256 hash, and compares
    against the most recent stored hash. On change, computes a unified diff
    and classifies the change type.

    Args:
        url: the URL to monitor
        store_result: if True, store the snapshot in the database

    Returns:
        Dict with:
            - url: the monitored URL
            - current_hash: SHA-256 of current content
            - previous_hash: SHA-256 of previous content (or None)
            - changed: boolean indicating if content changed
            - change_type: one of "no_change", "content_added", "content_removed",
                          "content_modified"
            - diff_summary: first 500 chars of unified diff (or empty string)
            - changes_detected: count of changed lines in diff
            - check_count: total number of times this URL has been checked
            - first_seen: ISO timestamp of first check
            - last_changed: ISO timestamp of last change detected
    """
    validate_url(url)
    _init_db()

    # Fetch current content
    try:
        current_content = _fetch_content(url)
    except Exception as e:
        logger.error("change_monitor failed url=%s: %s", url[:80], e)
        return {
            "url": url,
            "error": f"Failed to fetch content: {e!s}",
            "current_hash": None,
            "previous_hash": None,
            "changed": False,
            "change_type": "error",
            "diff_summary": "",
            "changes_detected": 0,
            "check_count": 0,
            "first_seen": None,
            "last_changed": None,
        }

    # Compute hash
    current_hash = _compute_hash(current_content)

    # Get previous hash
    previous_hash, previous_timestamp = _get_previous_hash(url)

    # Determine if changed
    changed = previous_hash is not None and current_hash != previous_hash

    # Classify change and compute diff
    change_type = "no_change"
    diff_summary = ""
    changes_detected = 0

    if changed and previous_hash:
        # Need to get the previous content to compute diff
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content_preview
            FROM url_snapshots
            WHERE url = ? AND content_hash = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (url, previous_hash),
        )

        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            previous_preview = row[0]
            diff_text, changes_detected = _compute_diff(previous_preview, current_content)
            change_type = _classify_change(previous_preview, current_content, changes_detected)
            diff_summary = diff_text[:500]

    # Store the new snapshot if requested
    if store_result:
        content_preview = current_content[: max(1000, len(current_content) // 10)]
        _store_snapshot(url, current_hash, content_preview)

    # Get metadata
    check_count, first_seen, last_changed = _get_metadata(url)

    return {
        "url": url,
        "current_hash": current_hash,
        "previous_hash": previous_hash,
        "changed": changed,
        "change_type": change_type,
        "diff_summary": diff_summary,
        "changes_detected": changes_detected,
        "check_count": check_count,
        "first_seen": first_seen,
        "last_changed": last_changed,
    }
