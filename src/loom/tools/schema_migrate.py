"""Schema migration tools for Loom SQLite databases.

Provides utilities to:
  - Check migration status across all .loom databases
  - Run pending schema migrations with dry-run support
  - Backup databases before migration
"""

from __future__ import annotations

import aiosqlite
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.schema_migrate")


async def research_migrate_status() -> dict[str, Any]:
    """Check migration status of all SQLite databases.

    Scans ~/.loom/*.db and inspects schema versions and tables.

    Returns:
        Dict with keys:
          - databases: List of dicts with {name, path, tables, current_version, needs_migration}
          - total: Total database count
    """
    loom_dir = Path.home() / ".loom"
    if not loom_dir.exists():
        return {"databases": [], "total": 0}

    databases = []
    db_files = sorted(loom_dir.glob("*.db"))

    for db_path in db_files:
        try:
            async with aiosqlite.connect(str(db_path)) as db:
                # Get all tables
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = [row[0] for row in await cursor.fetchall()]

                # Check for schema_version table
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
                )
                has_version_table = await cursor.fetchone() is not None

                current_version = 0
                if has_version_table:
                    cursor = await db.execute(
                        "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
                    )
                    row = await cursor.fetchone()
                    current_version = row[0] if row else 0

                # Determine if migration needed
                needs_migration = not has_version_table or current_version < _get_target_version(db_path.stem)

                databases.append({
                    "name": db_path.stem,
                    "path": str(db_path),
                    "tables": tables,
                    "current_version": current_version,
                    "target_version": _get_target_version(db_path.stem),
                    "needs_migration": needs_migration,
                })
        except Exception as e:
            logger.error("migrate_status_error db=%s error=%s", db_path.stem, e)
            databases.append({
                "name": db_path.stem,
                "path": str(db_path),
                "tables": [],
                "current_version": 0,
                "target_version": 1,
                "needs_migration": True,
                "error": str(e),
            })

    return {
        "databases": databases,
        "total": len(databases),
    }


async def research_migrate_run(database: str = "all", dry_run: bool = True) -> dict[str, Any]:
    """Run pending migrations on SQLite databases.

    Args:
        database: Database name (stem), or "all" for all .loom databases
        dry_run: If True, show what would change without applying

    Returns:
        Dict with keys:
          - database: Database name
          - migrations_applied: List of dicts with {type, table, description}
          - dry_run: Whether this was a dry run
          - changed: Number of changes applied/would apply
    """
    loom_dir = Path.home() / ".loom"
    if not loom_dir.exists():
        return {"database": database, "migrations_applied": [], "dry_run": dry_run, "changed": 0}

    if database == "all":
        results = []
        for db_file in sorted(loom_dir.glob("*.db")):
            result = await research_migrate_run(database=db_file.stem, dry_run=dry_run)
            results.append(result)
        return {
            "database": "all",
            "migrations": results,
            "total_changed": sum(r.get("changed", 0) for r in results),
            "dry_run": dry_run,
        }

    db_path = loom_dir / f"{database}.db"
    if not db_path.exists():
        return {
            "database": database,
            "migrations_applied": [],
            "dry_run": dry_run,
            "error": f"Database not found: {db_path}",
            "changed": 0,
        }

    migrations_applied: list[dict[str, str]] = []

    try:
        async with aiosqlite.connect(str(db_path)) as db:
            # Ensure schema_version table exists
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY,
                    version INTEGER NOT NULL,
                    description TEXT,
                    applied_at TEXT NOT NULL
                )
            """)
            await db.commit()

            current_version = 0
            cursor = await db.execute(
                "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                current_version = row[0]

            target_version = _get_target_version(database)

            # Run migrations for versions > current_version
            for migration in _get_migrations(database):
                if migration["version"] > current_version:
                    if not dry_run:
                        for sql in migration["sqls"]:
                            await db.execute(sql)
                        await db.execute(
                            "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
                            (migration["version"], migration["description"], datetime.now().isoformat()),
                        )
                        await db.commit()

                    migrations_applied.append({
                        "type": migration["type"],
                        "table": migration.get("table", ""),
                        "description": migration["description"],
                        "version": migration["version"],
                    })

    except Exception as e:
        logger.error("migrate_run_error db=%s error=%s", database, e)
        return {
            "database": database,
            "migrations_applied": [],
            "dry_run": dry_run,
            "error": str(e),
            "changed": 0,
        }

    return {
        "database": database,
        "migrations_applied": migrations_applied,
        "dry_run": dry_run,
        "changed": len(migrations_applied),
    }


async def research_migrate_backup(database: str) -> dict[str, Any]:
    """Create backup of database before migration.

    Args:
        database: Database name (stem)

    Returns:
        Dict with keys:
          - database: Database name
          - backup_path: Path to backup file
          - size_bytes: Size of backup in bytes
    """
    loom_dir = Path.home() / ".loom"
    db_path = loom_dir / f"{database}.db"

    if not db_path.exists():
        return {
            "database": database,
            "backup_path": "",
            "size_bytes": 0,
            "error": f"Database not found: {db_path}",
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = loom_dir / f"{database}.db.bak.{timestamp}"

    try:
        shutil.copy2(str(db_path), str(backup_path))
        size = backup_path.stat().st_size
        logger.info("migrate_backup_created db=%s path=%s size=%d", database, backup_path, size)

        return {
            "database": database,
            "backup_path": str(backup_path),
            "size_bytes": size,
            "timestamp": timestamp,
        }
    except Exception as e:
        logger.error("migrate_backup_error db=%s error=%s", database, e)
        return {
            "database": database,
            "backup_path": "",
            "size_bytes": 0,
            "error": str(e),
        }


def _get_target_version(database: str) -> int:
    """Get target schema version for database."""
    schema_versions = {
        "auth": 2,
        "gamification": 2,
        "dlq": 1,
        "change_monitor": 2,
        "checkpoints": 1,
        "hitl_eval": 1,
    }
    return schema_versions.get(database, 1)


def _get_migrations(database: str) -> list[dict[str, Any]]:
    """Get list of migrations for a database."""
    migrations: dict[str, list[dict[str, Any]]] = {
        "auth": [
            {
                "version": 1,
                "type": "create_table",
                "table": "tokens",
                "description": "Create tokens table",
                "sqls": ["""
                    CREATE TABLE IF NOT EXISTS tokens (
                        id INTEGER PRIMARY KEY,
                        token_hash TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        created TEXT NOT NULL,
                        expires TEXT NOT NULL,
                        active BOOLEAN NOT NULL DEFAULT 1
                    )
                """],
            },
            {
                "version": 2,
                "type": "add_column",
                "table": "tokens",
                "description": "Add last_used column to tokens",
                "sqls": [
                    "PRAGMA table_info(tokens)",
                    "ALTER TABLE tokens ADD COLUMN last_used TEXT DEFAULT NULL",
                ],
            },
        ],
        "gamification": [
            {
                "version": 1,
                "type": "create_table",
                "table": "scores",
                "description": "Create scores and challenges tables",
                "sqls": ["""
                    CREATE TABLE IF NOT EXISTS scores (
                        id INTEGER PRIMARY KEY,
                        strategy TEXT NOT NULL,
                        metric TEXT NOT NULL,
                        value REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        model TEXT,
                        run_id TEXT
                    )
                """, """
                    CREATE TABLE IF NOT EXISTS challenges (
                        id INTEGER PRIMARY KEY,
                        challenge_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        target_model TEXT NOT NULL,
                        success_criteria TEXT NOT NULL,
                        reward_credits INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        attempts INTEGER DEFAULT 0,
                        completions INTEGER DEFAULT 0
                    )
                """],
            },
            {
                "version": 2,
                "type": "create_index",
                "table": "scores",
                "description": "Create indexes for performance",
                "sqls": [
                    "CREATE INDEX IF NOT EXISTS idx_scores_metric ON scores(metric, timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_challenges_status ON challenges(status)",
                ],
            },
        ],
        "change_monitor": [
            {
                "version": 1,
                "type": "create_table",
                "table": "changes",
                "description": "Create changes tracking table",
                "sqls": ["""
                    CREATE TABLE IF NOT EXISTS changes (
                        id INTEGER PRIMARY KEY,
                        url TEXT NOT NULL,
                        hash TEXT NOT NULL,
                        detected_at TEXT NOT NULL,
                        previous_hash TEXT,
                        change_type TEXT
                    )
                """],
            },
            {
                "version": 2,
                "type": "create_index",
                "table": "changes",
                "description": "Create index for URL lookups",
                "sqls": [
                    "CREATE INDEX IF NOT EXISTS idx_changes_url ON changes(url, detected_at)",
                ],
            },
        ],
    }

    return migrations.get(database, [])
