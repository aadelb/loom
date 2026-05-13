"""Schema migration tools for Loom SQLite databases."""

from __future__ import annotations

import aiosqlite, logging, shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.schema_migrate")

_MIGRATIONS = {
    "auth": [
        {"v": 1, "type": "create_table", "table": "tokens", "desc": "Create tokens table", "sql": ["CREATE TABLE IF NOT EXISTS tokens (id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, name TEXT NOT NULL, created TEXT NOT NULL, expires TEXT NOT NULL, active BOOLEAN NOT NULL DEFAULT 1)"]},
        {"v": 2, "type": "add_column", "table": "tokens", "desc": "Add last_used column", "sql": ["ALTER TABLE tokens ADD COLUMN last_used TEXT DEFAULT NULL"]},
    ],
    "gamification": [
        {"v": 1, "type": "create_table", "table": "scores", "desc": "Create scores/challenges", "sql": ["CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY, strategy TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL, timestamp TEXT NOT NULL, model TEXT, run_id TEXT)", "CREATE TABLE IF NOT EXISTS challenges (id INTEGER PRIMARY KEY, challenge_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, target_model TEXT NOT NULL, success_criteria TEXT NOT NULL, reward_credits INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, attempts INTEGER DEFAULT 0, completions INTEGER DEFAULT 0)"]},
        {"v": 2, "type": "create_index", "table": "scores", "desc": "Create performance indexes", "sql": ["CREATE INDEX IF NOT EXISTS idx_scores_metric ON scores(metric, timestamp)", "CREATE INDEX IF NOT EXISTS idx_challenges_status ON challenges(status)"]},
    ],
    "change_monitor": [
        {"v": 1, "type": "create_table", "table": "changes", "desc": "Create changes table", "sql": ["CREATE TABLE IF NOT EXISTS changes (id INTEGER PRIMARY KEY, url TEXT NOT NULL, hash TEXT NOT NULL, detected_at TEXT NOT NULL, previous_hash TEXT, change_type TEXT)"]},
        {"v": 2, "type": "create_index", "table": "changes", "desc": "Create URL index", "sql": ["CREATE INDEX IF NOT EXISTS idx_changes_url ON changes(url, detected_at)"]},
    ],
}
_TARGET_VERSIONS = {"auth": 2, "gamification": 2, "change_monitor": 2, "dlq": 1, "checkpoints": 1, "hitl_eval": 1}


@handle_tool_errors("research_migrate_status")
async def research_migrate_status() -> dict[str, Any]:
    """Check migration status of all SQLite databases in ~/.loom."""
    loom_dir = Path.home() / ".loom"
    if not loom_dir.exists():
        return {"databases": [], "total": 0}

    databases, db_path = [], None
    try:
        for db_path in sorted(loom_dir.glob("*.db")):
            try:
                async with aiosqlite.connect(str(db_path)) as db:
                    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                    tables = [row[0] for row in await cursor.fetchall()]
                    try:
                        cursor = await db.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
                        current_v = (await cursor.fetchone() or (0,))[0]
                    except Exception:
                        current_v = 0
                    target_v = _TARGET_VERSIONS.get(db_path.stem, 1)
                    databases.append({"name": db_path.stem, "path": str(db_path), "tables": tables, "current_version": current_v, "target_version": target_v, "needs_migration": current_v < target_v})
            except Exception as e:
                logger.error("migrate_status_error db=%s error=%s", db_path.stem, e)
                databases.append({"name": db_path.stem, "path": str(db_path), "tables": [], "current_version": 0, "target_version": _TARGET_VERSIONS.get(db_path.stem, 1), "needs_migration": True, "error": str(e)})
    except Exception:
        pass
    return {"databases": databases, "total": len(databases)}


@handle_tool_errors("research_migrate_run")
async def research_migrate_run(database: str = "all", dry_run: bool = True) -> dict[str, Any]:
    """Run pending migrations on SQLite databases."""
    loom_dir = Path.home() / ".loom"
    if not loom_dir.exists():
        return {"database": database, "migrations_applied": [], "dry_run": dry_run, "changed": 0}

    if database == "all":
        results = [await research_migrate_run(database=db_file.stem, dry_run=dry_run) for db_file in sorted(loom_dir.glob("*.db"))]
        return {"database": "all", "migrations": results, "total_changed": sum(r.get("changed", 0) for r in results), "dry_run": dry_run}

    db_path = loom_dir / f"{database}.db"
    if not db_path.exists():
        return {"database": database, "migrations_applied": [], "dry_run": dry_run, "error": f"Not found: {db_path}", "changed": 0}

    migrations_applied = []
    try:
        async with aiosqlite.connect(str(db_path)) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER NOT NULL, description TEXT, applied_at TEXT NOT NULL)")
            await db.commit()
            cursor = await db.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
            current_v = (await cursor.fetchone() or (0,))[0]
            for m in _MIGRATIONS.get(database, []):
                if m["v"] > current_v:
                    if not dry_run:
                        for sql in m["sql"]:
                            await db.execute(sql)
                        await db.execute("INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)", (m["v"], m["desc"], datetime.now().isoformat()))
                        await db.commit()
                    migrations_applied.append({"type": m["type"], "table": m.get("table", ""), "description": m["desc"], "version": m["v"]})
    except Exception as e:
        logger.error("migrate_run_error db=%s error=%s", database, e)
        return {"database": database, "migrations_applied": [], "dry_run": dry_run, "error": str(e), "changed": 0}

    return {"database": database, "migrations_applied": migrations_applied, "dry_run": dry_run, "changed": len(migrations_applied)}


@handle_tool_errors("research_migrate_backup")
async def research_migrate_backup(database: str) -> dict[str, Any]:
    """Create backup of database before migration."""
    loom_dir = Path.home() / ".loom"
    db_path = loom_dir / f"{database}.db"
    if not db_path.exists():
        return {"database": database, "backup_path": "", "size_bytes": 0, "error": f"Not found: {db_path}"}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = loom_dir / f"{database}.db.bak.{timestamp}"
    try:
        shutil.copy2(str(db_path), str(backup_path))
        size = backup_path.stat().st_size
        logger.info("migrate_backup_created db=%s path=%s size=%d", database, backup_path, size)
        return {"database": database, "backup_path": str(backup_path), "size_bytes": size, "timestamp": timestamp}
    except Exception as e:
        logger.error("migrate_backup_error db=%s error=%s", database, e)
        return {"database": database, "backup_path": "", "size_bytes": 0, "error": str(e)}
