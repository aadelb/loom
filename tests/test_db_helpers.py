"""Tests for shared db_helpers module.

Tests database initialization, connection management, and schema handling.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from loom.db_helpers import db_connection, get_db_path, init_db


class TestGetDbPath:
    """Tests for get_db_path()."""

    def test_get_db_path_creates_directory(self, tmp_path: Path) -> None:
        """get_db_path() creates directory if it doesn't exist."""
        base_dir = tmp_path / "db" / "nested" / "dir"
        assert not base_dir.exists()

        db_path = get_db_path("test", base_dir)

        assert base_dir.exists()
        assert db_path == base_dir / "test.db"

    def test_get_db_path_returns_correct_filename(self, tmp_path: Path) -> None:
        """get_db_path() appends .db extension."""
        db_path = get_db_path("batch_queue", tmp_path)

        assert db_path.name == "batch_queue.db"
        assert str(db_path).endswith(".db")

    def test_get_db_path_uses_default_directory(self) -> None:
        """get_db_path() uses ~/.loom/db when base_dir is None."""
        # Just test that it returns a path under .loom/db
        # Don't actually create it to avoid polluting home directory
        db_path = get_db_path("test", None)

        assert ".loom" in str(db_path)
        assert "db" in str(db_path)
        assert db_path.name == "test.db"

    def test_get_db_path_multiple_names(self, tmp_path: Path) -> None:
        """get_db_path() works with different database names."""
        names = ["batch_queue", "deadletter", "workflow_engine", "exploit_db"]

        for name in names:
            db_path = get_db_path(name, tmp_path)
            assert db_path.name == f"{name}.db"
            assert db_path.parent == tmp_path

    def test_get_db_path_idempotent(self, tmp_path: Path) -> None:
        """get_db_path() can be called multiple times safely."""
        db_path1 = get_db_path("test", tmp_path)
        db_path2 = get_db_path("test", tmp_path)

        assert db_path1 == db_path2
        assert (tmp_path / "test.db").exists() is False  # path, not created yet


class TestInitDb:
    """Tests for init_db()."""

    def test_init_db_creates_database(self, tmp_path: Path) -> None:
        """init_db() creates database file."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);"

        init_db(db_path, schema)

        assert db_path.exists()
        assert db_path.stat().st_size > 0

    def test_init_db_executes_schema(self, tmp_path: Path) -> None:
        """init_db() executes provided schema."""
        db_path = tmp_path / "test.db"
        schema = """
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT);
        """

        init_db(db_path, schema)

        # Verify tables exist
        with db_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert cursor.fetchone() is not None

            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            assert cursor.fetchone() is not None

    def test_init_db_enables_wal_mode(self, tmp_path: Path) -> None:
        """init_db() enables WAL mode for concurrent access."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER);"

        init_db(db_path, schema)

        with db_connection(db_path) as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0].lower()
            assert mode == "wal"

    def test_init_db_supports_foreign_keys(self, tmp_path: Path) -> None:
        """init_db() creates schema with foreign key support."""
        db_path = tmp_path / "test.db"
        schema = """
            CREATE TABLE users (id INTEGER PRIMARY KEY);
            CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER,
                              FOREIGN KEY(user_id) REFERENCES users(id));
        """

        init_db(db_path, schema)

        # Verify schema was created successfully with FK support
        with db_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            assert cursor.fetchone() is not None

    def test_init_db_idempotent(self, tmp_path: Path) -> None:
        """init_db() is idempotent - can be called multiple times."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT);"

        # Call init_db twice
        init_db(db_path, schema)
        init_db(db_path, schema)

        # Database should still be valid and tables should exist
        with db_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test'"
            )
            assert cursor.fetchone() is not None

    def test_init_db_creates_parent_directory(self, tmp_path: Path) -> None:
        """init_db() creates parent directories if they don't exist."""
        db_path = tmp_path / "deep" / "nested" / "path" / "test.db"
        schema = "CREATE TABLE test (id INTEGER);"

        assert not db_path.parent.exists()

        init_db(db_path, schema)

        assert db_path.exists()
        assert db_path.parent.exists()

    def test_init_db_with_complex_schema(self, tmp_path: Path) -> None:
        """init_db() handles complex schemas with indexes and constraints."""
        db_path = tmp_path / "test.db"
        schema = """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX idx_email ON users(email);
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """

        init_db(db_path, schema)

        with db_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_email'"
            )
            assert cursor.fetchone() is not None

    def test_init_db_invalid_schema_raises_error(self, tmp_path: Path) -> None:
        """init_db() raises DatabaseError on invalid SQL."""
        db_path = tmp_path / "test.db"
        schema = "INVALID SQL HERE"

        with pytest.raises(sqlite3.DatabaseError):
            init_db(db_path, schema)


class TestDbConnection:
    """Tests for db_connection() context manager."""

    def test_db_connection_provides_connection(self, tmp_path: Path) -> None:
        """db_connection() yields an sqlite3.Connection object."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER);"
        init_db(db_path, schema)

        with db_connection(db_path) as conn:
            assert isinstance(conn, sqlite3.Connection)

    def test_db_connection_closes_on_exit(self, tmp_path: Path) -> None:
        """db_connection() closes connection when exiting context."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER);"
        init_db(db_path, schema)

        conn = None
        with db_connection(db_path) as conn_ctx:
            conn = conn_ctx

        # Attempt to use connection after exit should fail
        assert conn is not None
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_db_connection_tuple_rows(self, tmp_path: Path) -> None:
        """db_connection() returns tuple rows by default."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);"
        init_db(db_path, schema)

        with db_connection(db_path) as conn:
            conn.execute("INSERT INTO test (name) VALUES ('Alice')")
            conn.commit()

            cursor = conn.execute("SELECT * FROM test")
            row = cursor.fetchone()

            assert isinstance(row, tuple)
            assert row == (1, "Alice")

    def test_db_connection_dict_rows(self, tmp_path: Path) -> None:
        """db_connection(row_factory=True) returns dict-like rows."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);"
        init_db(db_path, schema)

        with db_connection(db_path, row_factory=True) as conn:
            conn.execute("INSERT INTO test (name) VALUES ('Bob')")
            conn.commit()

            cursor = conn.execute("SELECT * FROM test")
            row = cursor.fetchone()

            # Row should support dict-like access
            assert row["id"] == 1
            assert row["name"] == "Bob"

    def test_db_connection_multiple_operations(self, tmp_path: Path) -> None:
        """db_connection() allows multiple database operations."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);"
        init_db(db_path, schema)

        with db_connection(db_path) as conn:
            # Insert
            conn.execute("INSERT INTO users (name) VALUES ('Alice')")
            conn.execute("INSERT INTO users (name) VALUES ('Bob')")
            conn.commit()

            # Query
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            assert count == 2

    def test_db_connection_rollback_on_error(self, tmp_path: Path) -> None:
        """db_connection() handles transaction rollback."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, value INTEGER UNIQUE);"
        init_db(db_path, schema)

        # First insert
        with db_connection(db_path) as conn:
            conn.execute("INSERT INTO test (value) VALUES (1)")
            conn.commit()

        # Try duplicate (should fail)
        with db_connection(db_path) as conn:
            try:
                conn.execute("INSERT INTO test (value) VALUES (1)")
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()

        # Verify only one row
        with db_connection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            assert cursor.fetchone()[0] == 1

    def test_db_connection_with_exception_still_closes(self, tmp_path: Path) -> None:
        """db_connection() closes even if exception occurs in context."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER);"
        init_db(db_path, schema)

        conn = None
        try:
            with db_connection(db_path) as conn_ctx:
                conn = conn_ctx
                raise ValueError("test error")
        except ValueError:
            pass

        # Connection should still be closed
        assert conn is not None
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_db_connection_concurrent_access(self, tmp_path: Path) -> None:
        """db_connection() supports concurrent read access via WAL mode."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT);"
        init_db(db_path, schema)

        # Insert data
        with db_connection(db_path) as conn:
            conn.execute("INSERT INTO test (value) VALUES ('data1')")
            conn.execute("INSERT INTO test (value) VALUES ('data2')")
            conn.commit()

        # Concurrent read access
        with db_connection(db_path) as conn1:
            with db_connection(db_path) as conn2:
                cursor1 = conn1.execute("SELECT COUNT(*) FROM test")
                cursor2 = conn2.execute("SELECT COUNT(*) FROM test")

                count1 = cursor1.fetchone()[0]
                count2 = cursor2.fetchone()[0]

                assert count1 == 2
                assert count2 == 2

    def test_db_connection_context_manager_protocol(self, tmp_path: Path) -> None:
        """db_connection() is a proper context manager."""
        db_path = tmp_path / "test.db"
        schema = "CREATE TABLE test (id INTEGER);"
        init_db(db_path, schema)

        cm = db_connection(db_path)
        assert hasattr(cm, "__enter__")
        assert hasattr(cm, "__exit__")

        conn = cm.__enter__()
        assert isinstance(conn, sqlite3.Connection)
        cm.__exit__(None, None, None)
