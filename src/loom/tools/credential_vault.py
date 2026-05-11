"""Secure credential vault for managing API keys and secrets.

Provides encrypted storage of credentials using XOR cipher with
machine-specific derived key. Supports store, retrieve, and list operations.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.credential_vault")


def _derive_key(length: int = 32) -> bytes:
    """Derive encryption key from hostname + username."""
    hostname = socket.gethostname()
    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get("USER", "unknown")
    seed = f"{hostname}:{username}".encode()
    return hashlib.sha256(seed).digest()[:length]


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    """Apply XOR cipher with repeating key."""
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))


def _get_vault_path() -> Path:
    """Get vault file path with proper directory."""
    vault_dir = Path.home() / ".loom"
    vault_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    vault_path = vault_dir / "vault.json"
    return vault_path


def _load_vault() -> dict[str, Any]:
    """Load vault from disk, creating empty if missing."""
    vault_path = _get_vault_path()
    if not vault_path.exists():
        return {}
    try:
        with open(vault_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("vault_load_error: %s", e)
        return {}


def _save_vault(vault: dict[str, Any]) -> None:
    """Save vault to disk with restricted permissions."""
    vault_path = _get_vault_path()
    with open(vault_path, "w") as f:
        json.dump(vault, f, indent=2)
    vault_path.chmod(0o600)


async def research_vault_store(
    name: str,
    value: str,
    category: str = "api_key",
) -> dict[str, Any]:
    """Store a credential securely in the vault.

    Args:
        name: Credential name (alphanumeric + underscore)
        value: Secret value to encrypt and store
        category: Classification (api_key, token, password, etc)

    Returns:
        Dict with keys: stored (bool), name, category, value_prefix (first 4 chars)
    """
    try:
        if not name or not value:
            return {"stored": False, "error": "name and value required"}

        vault = _load_vault()
        key = _derive_key()

        # Encrypt the value
        encrypted = _xor_cipher(value.encode(), key)
        encoded = base64.b64encode(encrypted).decode("ascii")

        # Store entry with metadata
        vault[name] = {
            "encrypted": encoded,
            "category": category,
            "stored_at": datetime.now(UTC).isoformat(),
            "accessed_at": datetime.now(UTC).isoformat(),
        }

        _save_vault(vault)
        logger.info("credential_stored name=%s category=%s", name, category)

        return {
            "stored": True,
            "name": name,
            "category": category,
            "value_prefix": value[:4] if len(value) >= 4 else "****",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_vault_store"}


async def research_vault_retrieve(name: str) -> dict[str, Any]:
    """Retrieve and decrypt a credential from the vault.

    Args:
        name: Credential name to retrieve

    Returns:
        Dict with keys: name, value, category, last_accessed
    """
    try:
        vault = _load_vault()

        if name not in vault:
            return {"error": f"credential not found: {name}"}

        entry = vault[name]
        key = _derive_key()

        # Decrypt the value
        encrypted = base64.b64decode(entry["encrypted"])
        decrypted = _xor_cipher(encrypted, key).decode("utf-8", errors="replace")

        # Update access time
        entry["accessed_at"] = datetime.now(UTC).isoformat()
        _save_vault(vault)

        logger.info("credential_retrieved name=%s", name)

        return {
            "name": name,
            "value": decrypted,
            "category": entry.get("category", "unknown"),
            "last_accessed": entry.get("accessed_at"),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_vault_retrieve"}


async def research_vault_list() -> dict[str, Any]:
    """List all stored credentials (names only, never values).

    Returns:
        Dict with keys: credentials (list of dicts), total
    """
    try:
        vault = _load_vault()
        credentials = []

        for name, entry in vault.items():
            credentials.append({
                "name": name,
                "category": entry.get("category", "unknown"),
                "stored_at": entry.get("stored_at"),
                "value_prefix": "****",  # Never expose prefix on list
            })

        logger.info("vault_listed count=%d", len(credentials))

        return {
            "credentials": credentials,
            "total": len(credentials),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_vault_list"}
