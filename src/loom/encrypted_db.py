"""Encryption at rest for SQLite databases using Fernet symmetric encryption.

Provides transparent encryption/decryption of SQLite database files.
Supports optional SQLCipher integration if available; falls back to Fernet
file-level encryption for portability.

Public API:
    EncryptedDB              Context manager for encrypted database access
    get_encryption_key()     Retrieve or generate encryption key
    research_db_encryption_status  MCP tool: show encryption status
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:
    from cryptography.fernet import Fernet

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

try:
    import sqlcipher3

    HAS_SQLCIPHER = True
except ImportError:
    HAS_SQLCIPHER = False

logger = logging.getLogger("loom.encrypted_db")


def get_encryption_key() -> bytes:
    """Retrieve or generate encryption key from environment.

    Key derivation:
        1. If LOOM_DB_ENCRYPTION_KEY is set, use as Fernet key (must be valid)
        2. If LOOM_DB_ENCRYPTION_PASSWORD is set, derive key via PBKDF2
        3. Otherwise, generate and save to ~/.loom/encryption_key (write-protected)

    Returns:
        32-byte Fernet-compatible key (base64-encoded)

    Raises:
        ValueError: If environment key is invalid Fernet format
    """
    # Priority 1: Explicit key from env
    if env_key := os.environ.get("LOOM_DB_ENCRYPTION_KEY"):
        try:
            # Validate it's valid Fernet format (base64, 32 bytes)
            Fernet(env_key)
            return env_key.encode() if isinstance(env_key, str) else env_key
        except Exception as exc:
            raise ValueError(
                f"Invalid LOOM_DB_ENCRYPTION_KEY format: {exc}. "
                "Must be base64-encoded Fernet key."
            ) from exc

    # Priority 2: Derive from password
    if password := os.environ.get("LOOM_DB_ENCRYPTION_PASSWORD"):
        salt = b"loom_db_encryption_v1"
        key_material = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            100000,  # iterations
            dklen=32,
        )
        return base64.b64encode(key_material)

    # Priority 3: Load or generate from disk
    key_file = Path.home() / ".loom" / "encryption_key"
    if key_file.exists():
        with open(key_file, "rb") as f:
            return f.read()

    # Generate new key
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    key_file.write_bytes(key)
    key_file.chmod(0o600)  # Read/write for owner only
    logger.info("Encryption key generated at %s", str(key_file))
    return key


class EncryptedDB:
    """Context manager for encrypted SQLite database access.

    Supports two modes:
    1. SQLCipher (if available): Native encrypted database
    2. Fernet (fallback): File-level encryption with transparent decrypt on entry

    Attributes:
        db_path: Path to .db or .db.enc file
        key: Encryption key (bytes)
        use_sqlcipher: Whether SQLCipher is available
        _temp_decrypted: Temporary decrypted database file path (Fernet mode only)
    """

    def __init__(
        self,
        db_path: str | Path,
        key: bytes | None = None,
        use_sqlcipher: bool | None = None,
    ) -> None:
        """Initialize encrypted database context.

        Args:
            db_path: Path to database file (.db or .db.enc)
            key: Encryption key (defaults to get_encryption_key())
            use_sqlcipher: Force SQLCipher (True) or Fernet (False) mode
                          (defaults to auto-detect)
        """
        if not HAS_CRYPTOGRAPHY:
            raise ImportError(
                "cryptography library required. Install: pip install cryptography"
            )

        self.db_path = Path(db_path)
        self.key = key or get_encryption_key()
        self._temp_decrypted: Path | None = None

        # Auto-detect mode
        if use_sqlcipher is None:
            self.use_sqlcipher = HAS_SQLCIPHER
        else:
            if use_sqlcipher and not HAS_SQLCIPHER:
                raise ValueError(
                    "SQLCipher requested but not installed. "
                    "Install: pip install sqlcipher3"
                )
            self.use_sqlcipher = use_sqlcipher

    def __enter__(self) -> Path:
        """Enter context: decrypt database if needed.

        Returns:
            Path to usable database file (temp file in Fernet mode)
        """
        if self.use_sqlcipher:
            return self.db_path

        # Fernet mode: decrypt to temp file
        enc_path = self._get_encrypted_path()
        if enc_path.exists():
            self._decrypt_file(enc_path)
        return self.db_path

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exit context: re-encrypt and cleanup."""
        if self.use_sqlcipher:
            return

        # Fernet mode: encrypt and cleanup temp
        if self.db_path.exists():
            self._encrypt_file()

        if self._temp_decrypted and self._temp_decrypted.exists():
            self._temp_decrypted.unlink()
            logger.debug("Temporary decrypted file cleaned up: %s", str(self._temp_decrypted))

    @contextmanager
    def connection(self, **kwargs: Any) -> Iterator[sqlite3.Connection]:
        """Context manager for database connection.

        Args:
            **kwargs: Additional sqlite3.connect() arguments

        Yields:
            sqlite3.Connection object

        Example:
            with EncryptedDB("db.enc") as db:
                with db.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM users")
        """
        if self.use_sqlcipher:
            # SQLCipher mode: use password directly
            if not HAS_SQLCIPHER:
                raise RuntimeError("SQLCipher mode requested but sqlcipher3 not available")
            # Guard ensures sqlcipher3 is available in this branch
            conn = sqlcipher3.connect(str(self.db_path), **kwargs)  # pylint: disable=undefined-variable
            conn.execute("PRAGMA key = ?", (self.key.decode(),))
        else:
            # Fernet mode: temp decrypted file
            conn = sqlite3.connect(str(self.db_path), **kwargs)

        try:
            yield conn
        finally:
            conn.close()

    def _get_encrypted_path(self) -> Path:
        """Get encrypted file path (.db.enc)."""
        if self.db_path.suffix == ".enc":
            return self.db_path
        return self.db_path.with_suffix(self.db_path.suffix + ".enc")

    def _decrypt_file(self, enc_path: Path) -> None:
        """Decrypt .enc file to .db (in-place or to temp).

        Args:
            enc_path: Path to encrypted .db.enc file
        """
        cipher = Fernet(self.key)
        enc_data = enc_path.read_bytes()

        try:
            dec_data = cipher.decrypt(enc_data)
        except Exception as exc:
            raise ValueError(
                f"Failed to decrypt {enc_path}: {exc}. "
                "Key may be incorrect."
            ) from exc

        self.db_path.write_bytes(dec_data)
        logger.debug("Database decrypted: %s -> %s", str(enc_path), str(self.db_path))

    def _encrypt_file(self) -> None:
        """Encrypt .db file to .db.enc (in-place).

        Overwrites .db.enc if it exists; original .db is removed.
        """
        if not self.db_path.exists():
            return

        cipher = Fernet(self.key)
        db_data = self.db_path.read_bytes()
        enc_data = cipher.encrypt(db_data)

        enc_path = self._get_encrypted_path()
        enc_path.write_bytes(enc_data)
        self.db_path.unlink()  # Remove plaintext

        logger.debug("Database encrypted: %s -> %s", str(self.db_path), str(enc_path))

    def encrypt_file(self, path: str | Path) -> Path:
        """Encrypt a database file manually.

        Args:
            path: Path to plaintext .db file

        Returns:
            Path to encrypted .db.enc file
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Database file not found: {path}")

        cipher = Fernet(self.key)
        db_data = path.read_bytes()
        enc_data = cipher.encrypt(db_data)

        enc_path = path.with_suffix(path.suffix + ".enc")
        enc_path.write_bytes(enc_data)
        logger.info("Manual database encryption: %s -> %s", str(path), str(enc_path))
        return enc_path

    def decrypt_file(self, enc_path: str | Path) -> Path:
        """Decrypt a database file manually.

        Args:
            enc_path: Path to encrypted .db.enc file

        Returns:
            Path to decrypted .db file
        """
        enc_path = Path(enc_path)
        if not enc_path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {enc_path}")

        cipher = Fernet(self.key)
        enc_data = enc_path.read_bytes()

        try:
            db_data = cipher.decrypt(enc_data)
        except Exception as exc:
            raise ValueError(f"Failed to decrypt {enc_path}: {exc}") from exc

        db_path = enc_path.with_suffix("")
        db_path.write_bytes(db_data)
        logger.info("Manual database decryption: %s -> %s", str(enc_path), str(db_path))
        return db_path

    def is_encrypted(self) -> bool:
        """Check if database file is currently encrypted.

        Returns:
            True if .db.enc exists, False if .db exists
        """
        enc_path = self._get_encrypted_path()
        db_exists = self.db_path.exists()
        enc_exists = enc_path.exists()

        return enc_exists and not db_exists


def research_db_encryption_status() -> dict[str, bool | str]:
    """MCP tool: Report encryption status of all Loom databases.

    Returns:
        Dictionary mapping database paths to encryption status.
        Example:
            {
                "batch_queue.db": false,
                "dlq.db": false,
                "jobs.db": false,
                "sessions.db": false,
                "audit_dir": "JSONL (not encrypted)"
            }
    """
    databases: dict[str, bool | str] = {}

    # Batch queue
    batch_db = Path.home() / ".cache" / "loom" / "batch_queue.db"
    batch_enc = batch_db.with_suffix(batch_db.suffix + ".enc")
    databases["batch_queue.db"] = batch_enc.exists()

    # Dead letter queue
    dlq_db = Path.home() / ".cache" / "loom" / "dlq.db"
    dlq_enc = dlq_db.with_suffix(dlq_db.suffix + ".enc")
    databases["dlq.db"] = dlq_enc.exists()

    # Job queue
    jobs_db = Path.home() / ".loom" / "jobs.db"
    jobs_enc = jobs_db.with_suffix(jobs_db.suffix + ".enc")
    databases["jobs.db"] = jobs_enc.exists()

    # Session database
    sessions_db = Path.home() / ".loom" / "sessions" / "sessions.db"
    if sessions_db.exists():
        sessions_enc = sessions_db.with_suffix(sessions_db.suffix + ".enc")
        databases["sessions.db"] = sessions_enc.exists()

    # Audit (JSONL, not encrypted)
    audit_dir = Path.home() / ".loom" / "audit"
    if audit_dir.exists():
        databases["audit_dir"] = "JSONL (see audit.py for HMAC signing)"

    return databases
