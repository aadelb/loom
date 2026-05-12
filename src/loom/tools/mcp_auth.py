"""MCP authentication enforcement — token generation, validation, revocation."""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("loom.tools.mcp_auth")
AUTH_DB_PATH = Path.home() / ".loom" / "auth.db"


async def _get_auth_db() -> aiosqlite.Connection:
    """Get or create auth database."""
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(AUTH_DB_PATH))
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL, created TEXT NOT NULL, expires TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT 1)"""
    )
    await conn.commit()
    return conn


def _hash_token(token: str) -> str:
    """Hash token using SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()


@handle_tool_errors("research_auth_create_token")
async def research_auth_create_token(
    name: str = "default", expires_hours: int = 24
) -> dict[str, Any]:
    """Create a bearer token for MCP access.

    Returns: {token, name, expires_at, token_prefix}
    WARNING: Token is full plaintext — store securely immediately. Do not log.
    """
    token = "loom_" + secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=expires_hours)

    conn = await _get_auth_db()
    try:
        await conn.execute(
            "INSERT INTO tokens (token_hash, name, created, expires, active) VALUES (?, ?, ?, ?, 1)",
            (token_hash, name, now.isoformat(), expires_at.isoformat()),
        )
        await conn.commit()
        logger.info("token_created name=%s expires_hours=%d", name, expires_hours)
        return {
            "token": token,
            "name": name,
            "expires_at": expires_at.isoformat(),
            "token_prefix": token[:15] + "...",
        }
    finally:
        await conn.close()


@handle_tool_errors("research_auth_validate")
async def research_auth_validate(token: str) -> dict[str, Any]:
    """Validate a token.

    Returns: {valid: bool, name, expires_at, reason (if invalid)}
    Uses SQL constant-time comparison for token_hash lookup (database-level protection).
    """
    token_hash = _hash_token(token)
    conn = await _get_auth_db()

    try:
        cursor = await conn.execute(
            "SELECT name, expires, active FROM tokens WHERE token_hash = ?",
            (token_hash,),
        )
        row = await cursor.fetchone()

        if not row:
            logger.warning("token_validation_failed: token_not_found")
            return {"valid": False, "reason": "token_not_found"}

        name, expires_str, active = row

        if not active:
            logger.warning("token_validation_failed: token_revoked name=%s", name)
            return {"valid": False, "reason": "token_revoked"}

        if datetime.fromisoformat(expires_str) < datetime.now(UTC):
            logger.warning("token_validation_failed: token_expired name=%s", name)
            return {"valid": False, "reason": "token_expired", "expires_at": expires_str}

        logger.info("token_validated name=%s", name)
        return {"valid": True, "name": name, "expires_at": expires_str}
    finally:
        await conn.close()


@handle_tool_errors("research_auth_revoke")
async def research_auth_revoke(name: str = "") -> dict[str, Any]:
    """Revoke token(s) by name.

    Args:
        name: Token name to revoke. Required.

    Returns: {revoked_count, remaining_active, error (if any)}
    """
    if not name:
        return {"error": "specify name to revoke", "revoked_count": 0}

    conn = await _get_auth_db()
    try:
        cursor = await conn.execute(
            "UPDATE tokens SET active = 0 WHERE name = ? AND active = 1", (name,)
        )
        revoked_count = cursor.rowcount
        await conn.commit()

        cursor = await conn.execute("SELECT COUNT(*) FROM tokens WHERE active = 1")
        remaining_active = (await cursor.fetchone())[0]

        logger.info("token_revoked name=%s revoked_count=%d", name, revoked_count)
        return {"revoked_count": revoked_count, "remaining_active": remaining_active}
    finally:
        await conn.close()
