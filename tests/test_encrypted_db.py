"""Tests for encrypted_db module (encryption at rest for SQLite databases)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from loom.encrypted_db import (
    EncryptedDB,
    get_encryption_key,
    research_db_encryption_status,
)

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


@pytest.fixture
def temp_db_dir() -> Path:
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def encryption_key() -> bytes:
    """Generate a test encryption key."""
    if not HAS_CRYPTOGRAPHY:
        pytest.skip("cryptography not installed")
    return Fernet.generate_key()


@pytest.fixture
def plain_db(temp_db_dir: Path) -> Path:
    """Create a simple test database with sample data."""
    db_path = temp_db_dir / "test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
    cursor.execute("INSERT INTO users VALUES (2, 'Bob')")
    conn.commit()
    conn.close()
    return db_path


class TestGetEncryptionKey:
    """Test encryption key generation and retrieval."""

    def test_explicit_key_from_env(self, encryption_key: bytes) -> None:
        """Test retrieving explicitly set encryption key from env."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        with mock.patch.dict(
            os.environ,
            {"LOOM_DB_ENCRYPTION_KEY": encryption_key.decode()},
            clear=False,
        ):
            key = get_encryption_key()
            assert key == encryption_key

    def test_invalid_key_raises_error(self) -> None:
        """Test that invalid key format raises ValueError."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        with mock.patch.dict(
            os.environ,
            {"LOOM_DB_ENCRYPTION_KEY": "invalid_base64_key"},
            clear=False,
        ):
            with pytest.raises(ValueError, match="Invalid LOOM_DB_ENCRYPTION_KEY"):
                get_encryption_key()

    def test_password_derived_key(self) -> None:
        """Test key derivation from password."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        password = "test_password_123"
        with mock.patch.dict(
            os.environ,
            {
                "LOOM_DB_ENCRYPTION_PASSWORD": password,
                "LOOM_DB_ENCRYPTION_KEY": "",  # Clear explicit key
            },
            clear=False,
        ):
            # Clear explicit key from environment
            os.environ.pop("LOOM_DB_ENCRYPTION_KEY", None)

            key1 = get_encryption_key()
            key2 = get_encryption_key()
            # Same password should derive same key
            assert key1 == key2
            assert len(key1) > 0

    def test_key_from_disk(self, temp_db_dir: Path) -> None:
        """Test loading encryption key from disk."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        key_file = temp_db_dir / ".loom" / "encryption_key"
        key_file.parent.mkdir(parents=True, exist_ok=True)

        test_key = Fernet.generate_key()
        key_file.write_bytes(test_key)

        with mock.patch("pathlib.Path.home", return_value=temp_db_dir):
            key = get_encryption_key()
            assert key == test_key


class TestEncryptedDB:
    """Test EncryptedDB context manager and encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(
        self, temp_db_dir: Path, encryption_key: bytes, plain_db: Path
    ) -> None:
        """Test encrypting and decrypting a database file."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        # Copy test db to temp dir
        test_db = temp_db_dir / "test.db"
        test_db.write_bytes(plain_db.read_bytes())

        # Encrypt
        edb = EncryptedDB(test_db, key=encryption_key, use_sqlcipher=False)
        enc_path = edb.encrypt_file(test_db)

        assert enc_path.exists()
        assert not test_db.exists()  # Original removed after encryption

        # Verify encrypted file is different
        enc_data = enc_path.read_bytes()
        assert enc_data != plain_db.read_bytes()

        # Decrypt
        dec_path = edb.decrypt_file(enc_path)
        assert dec_path.exists()
        assert dec_path.read_bytes() == plain_db.read_bytes()

    def test_context_manager_encryption(
        self, temp_db_dir: Path, encryption_key: bytes, plain_db: Path
    ) -> None:
        """Test context manager automatically encrypts on exit."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        test_db = temp_db_dir / "test.db"
        test_db.write_bytes(plain_db.read_bytes())
        original_data = plain_db.read_bytes()

        edb = EncryptedDB(test_db, key=encryption_key, use_sqlcipher=False)

        # Access database in context
        with edb:
            assert test_db.exists()
            # Database should be readable
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()
            conn.close()
            assert len(rows) == 2

        # After context, should be encrypted
        enc_path = test_db.with_suffix(test_db.suffix + ".enc")
        assert enc_path.exists()
        assert not test_db.exists()

        # Encrypted file should be different from original
        assert enc_path.read_bytes() != original_data

    def test_context_manager_decryption(
        self, temp_db_dir: Path, encryption_key: bytes, plain_db: Path
    ) -> None:
        """Test context manager automatically decrypts on entry."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        # Create encrypted database
        test_db = temp_db_dir / "test.db"
        test_db.write_bytes(plain_db.read_bytes())

        edb = EncryptedDB(test_db, key=encryption_key, use_sqlcipher=False)
        enc_path = edb.encrypt_file(test_db)

        # Context manager should decrypt
        with edb:
            assert test_db.exists()
            # Should be readable
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            conn.close()
            assert count == 2

    def test_is_encrypted(
        self, temp_db_dir: Path, encryption_key: bytes, plain_db: Path
    ) -> None:
        """Test is_encrypted() method."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        test_db = temp_db_dir / "test.db"
        test_db.write_bytes(plain_db.read_bytes())

        edb = EncryptedDB(test_db, key=encryption_key, use_sqlcipher=False)

        # Initially not encrypted
        assert not edb.is_encrypted()

        # Encrypt
        edb.encrypt_file(test_db)
        assert edb.is_encrypted()

    def test_wrong_key_fails(
        self, temp_db_dir: Path, encryption_key: bytes, plain_db: Path
    ) -> None:
        """Test that wrong decryption key raises error."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        test_db = temp_db_dir / "test.db"
        test_db.write_bytes(plain_db.read_bytes())

        edb = EncryptedDB(test_db, key=encryption_key, use_sqlcipher=False)
        enc_path = edb.encrypt_file(test_db)

        # Try decrypting with wrong key
        wrong_key = Fernet.generate_key()
        edb_wrong = EncryptedDB(test_db, key=wrong_key, use_sqlcipher=False)

        with pytest.raises(ValueError, match="Failed to decrypt"):
            edb_wrong.decrypt_file(enc_path)

    def test_missing_file_raises_error(
        self, temp_db_dir: Path, encryption_key: bytes
    ) -> None:
        """Test that encrypting non-existent file raises error."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        missing_db = temp_db_dir / "missing.db"
        edb = EncryptedDB(missing_db, key=encryption_key, use_sqlcipher=False)

        with pytest.raises(FileNotFoundError):
            edb.encrypt_file(missing_db)

    def test_connection_context_manager(
        self, temp_db_dir: Path, encryption_key: bytes, plain_db: Path
    ) -> None:
        """Test connection() context manager for database access."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        test_db = temp_db_dir / "test.db"
        test_db.write_bytes(plain_db.read_bytes())

        edb = EncryptedDB(test_db, key=encryption_key, use_sqlcipher=False)

        with edb:
            with edb.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM users WHERE id = 1")
                name = cursor.fetchone()[0]
                assert name == "Alice"

    def test_get_encrypted_path(
        self, temp_db_dir: Path, encryption_key: bytes
    ) -> None:
        """Test _get_encrypted_path() method."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        db_path = temp_db_dir / "test.db"
        edb = EncryptedDB(db_path, key=encryption_key, use_sqlcipher=False)

        enc_path = edb._get_encrypted_path()
        assert enc_path == temp_db_dir / "test.db.enc"

        # If db_path already has .enc suffix
        enc_db = temp_db_dir / "test.db.enc"
        edb2 = EncryptedDB(enc_db, key=encryption_key, use_sqlcipher=False)
        enc_path2 = edb2._get_encrypted_path()
        assert enc_path2 == enc_db


class TestResearchDbEncryptionStatus:
    """Test research_db_encryption_status MCP tool."""

    def test_encryption_status_output_structure(self) -> None:
        """Test that status output has expected structure."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        status = research_db_encryption_status()

        assert isinstance(status, dict)
        # Check for expected database keys
        assert "batch_queue.db" in status
        assert "dlq.db" in status
        assert "jobs.db" in status

    def test_encryption_status_boolean_values(self) -> None:
        """Test that status values are boolean or string."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        status = research_db_encryption_status()

        for key, value in status.items():
            assert isinstance(value, (bool, str)), f"Unexpected type for {key}: {type(value)}"


class TestEncryptedDBWithSQLCipher:
    """Test EncryptedDB SQLCipher mode (if available)."""

    def test_sqlcipher_mode_preference(self, temp_db_dir: Path) -> None:
        """Test that SQLCipher mode is preferred if available."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        test_key = Fernet.generate_key()
        edb = EncryptedDB(temp_db_dir / "test.db", key=test_key)

        # use_sqlcipher should reflect whether sqlcipher3 is available
        try:
            import sqlcipher3  # noqa: F401
            assert edb.use_sqlcipher is True
        except ImportError:
            assert edb.use_sqlcipher is False

    def test_force_fernet_mode(self, temp_db_dir: Path) -> None:
        """Test forcing Fernet mode even if SQLCipher is available."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        test_key = Fernet.generate_key()
        edb = EncryptedDB(
            temp_db_dir / "test.db", key=test_key, use_sqlcipher=False
        )
        assert edb.use_sqlcipher is False

    def test_sqlcipher_not_available_error(self, temp_db_dir: Path) -> None:
        """Test error when requesting SQLCipher but not available."""
        if not HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography not installed")

        test_key = Fernet.generate_key()

        with mock.patch("loom.encrypted_db.HAS_SQLCIPHER", False):
            with pytest.raises(ValueError, match="SQLCipher requested but not installed"):
                EncryptedDB(
                    temp_db_dir / "test.db", key=test_key, use_sqlcipher=True
                )


class TestEncryptedDBNoEncryptionLibrary:
    """Test graceful handling when cryptography is not available."""

    def test_missing_cryptography_raises_import_error(self) -> None:
        """Test that missing cryptography library is caught."""
        if HAS_CRYPTOGRAPHY:
            pytest.skip("cryptography is installed")

        from pathlib import Path
        with pytest.raises(ImportError, match="cryptography library required"):
            EncryptedDB(Path("/tmp/test.db"))
