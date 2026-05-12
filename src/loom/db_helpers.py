"""Shared database helper functions for Loom tool modules.

Consolidates _init_db, _get_db_path, db_connection patterns
duplicated across workflow_engine, change_monitor, observability, exploit_db,
batch_queue, deadletter, and other modules. Provides a single source of truth
for SQLite connection and schema initialization.

Public API:
    get_db_path(name, base_dir)       Get path for a named SQLite database
    init_db(path, schema)             Initialize database with schema
    db_connection(path, row_factory)  Context manager for SQLite connections
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

log = logging.getLogger("loom.db_helpers")

_DEFAULT_DB_DIR = Path.home() / ".loom" / "db"


def get_db_path(name: str, base_dir: Path | None = None) -> Path:
    """Get path for a named SQLite database. Creates directory if needed.

    Args:
        name: Database name (e.g., "batch_queue", "deadletter").
              Used as filename with .db extension.
        base_dir: Base directory for database files. If None, uses
                 ~/.loom/db. Created if it doesn't exist.

    Returns:
        Path object pointing to the .db file
    """
    if base_dir is None:
        base_dir = _DEFAULT_DB_DIR

    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    db_path = base_dir / f"{name}.db"
    return db_path


def init_db(path: Path, schema: str) -> None:
    """Initialize SQLite database with schema if tables don't exist.

    Executes the provided SQL schema only if the database is new.
    Uses a lock table to detect first-time initialization in concurrent
    scenarios (safe for multi-process access).

    Args:
        path: Path to the SQLite database file
        schema: SQL schema definition (CREATE TABLE statements).
               Must include all tables needed by the application.

    Returns:
        None

    Raises:
        sqlite3.DatabaseError: If schema contains invalid SQL
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        # Enable WAL mode for concurrent access and foreign keys
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # Create a lock table to detect first-time init
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _loom_init_lock (
                initialized INTEGER PRIMARY KEY DEFAULT 1,
                initialized_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

        # Check if this is first-time initialization
        cursor = conn.execute("SELECT COUNT(*) FROM _loom_init_lock")
        is_first_init = cursor.fetchone()[0] == 0

        if is_first_init:
            # Execute the schema
            try:
                conn.executescript(schema)
                conn.commit()
                # Mark initialization complete AFTER successful schema execution
                conn.execute(
                    "INSERT INTO _loom_init_lock (initialized_at) VALUES (CURRENT_TIMESTAMP)"
                )
                conn.commit()
                log.info("Initialized database at %s", path)
            except sqlite3.DatabaseError as e:
                log.error("Failed to initialize schema at %s: %s", path, e)
                raise


@contextmanager
def db_connection(
    path: Path, *, row_factory: bool = False
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections. Always closes on exit.

    Provides a clean interface for database access with automatic
    connection cleanup. Handles both dict-like rows (row_factory=True)
    and tuple rows (default).

    Args:
        path: Path to the SQLite database file
        row_factory: If True, returns rows as dicts (via Row); else tuples.
                    Default False (tuples).

    Yields:
        sqlite3.Connection: An open database connection

    Example:
        >>> from pathlib import Path
        >>> db_path = Path.home() / ".loom" / "db" / "mydb.db"
        >>> with db_connection(db_path) as conn:
        ...     cursor = conn.execute("SELECT * FROM mytable")
        ...     rows = cursor.fetchall()
    """
    conn = sqlite3.connect(str(path))
    try:
        if row_factory:
            conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()
