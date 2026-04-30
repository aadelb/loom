"""Unit tests for audit logging module (REQ-086, REQ-087).

Tests cover:
- log_invocation() creates valid JSONL with checksums
- verify_integrity() detects tampering
- Parameter redaction for sensitive keys
- Daily rotation of log files
- Empty file handling
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from loom.audit import (
    AuditEntry,
    VerifyResult,
    export_audit,
    log_invocation,
    verify_integrity,
    _redact_params,
)


class TestAuditEntry:
    """AuditEntry dataclass tests."""

    def test_audit_entry_creation(self) -> None:
        """Create AuditEntry with all required fields."""
        entry = AuditEntry(
            client_id="client-123",
            tool_name="research_fetch",
            params_summary={"url": "https://example.com"},
            timestamp="2025-04-29T10:30:00+00:00",
            duration_ms=500,
            status="success",
        )

        assert entry.client_id == "client-123"
        assert entry.tool_name == "research_fetch"
        assert entry.duration_ms == 500
        assert entry.status == "success"

    def test_audit_entry_to_json(self) -> None:
        """Serialize AuditEntry to JSON string."""
        entry = AuditEntry(
            client_id="client-123",
            tool_name="research_fetch",
            params_summary={"url": "https://example.com"},
            timestamp="2025-04-29T10:30:00+00:00",
            duration_ms=500,
            status="success",
            checksum="abc123def456",
        )

        json_str = entry.to_json(include_checksum=True)
        data = json.loads(json_str)

        assert data["client_id"] == "client-123"
        assert data["checksum"] == "abc123def456"

    def test_audit_entry_to_json_without_checksum(self) -> None:
        """Serialize AuditEntry to JSON without checksum field."""
        entry = AuditEntry(
            client_id="client-123",
            tool_name="research_fetch",
            params_summary={"url": "https://example.com"},
            timestamp="2025-04-29T10:30:00+00:00",
            duration_ms=500,
            status="success",
            checksum="abc123def456",
        )

        json_str = entry.to_json(include_checksum=False)
        data = json.loads(json_str)

        assert "checksum" not in data
        assert data["client_id"] == "client-123"

    def test_audit_entry_compute_checksum(self) -> None:
        """Compute SHA-256 checksum of entry without checksum field."""
        entry = AuditEntry(
            client_id="client-123",
            tool_name="research_fetch",
            params_summary={"url": "https://example.com"},
            timestamp="2025-04-29T10:30:00+00:00",
            duration_ms=500,
            status="success",
        )

        checksum = entry.compute_checksum()

        # Checksum should be 16 hex characters
        assert len(checksum) == 16
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_audit_entry_checksum_deterministic(self) -> None:
        """Checksum computation is deterministic."""
        entry = AuditEntry(
            client_id="client-123",
            tool_name="research_fetch",
            params_summary={"url": "https://example.com"},
            timestamp="2025-04-29T10:30:00+00:00",
            duration_ms=500,
            status="success",
        )

        checksum1 = entry.compute_checksum()
        checksum2 = entry.compute_checksum()

        assert checksum1 == checksum2


class TestParamRedaction:
    """Parameter redaction tests."""

    def test_redact_api_key(self) -> None:
        """Redact 'api_key' parameter."""
        params = {"url": "https://example.com", "api_key": "secret123"}
        redacted = _redact_params(params)

        assert redacted["url"] == "https://example.com"
        assert redacted["api_key"] == "***REDACTED***"

    def test_redact_token(self) -> None:
        """Redact 'token' parameter."""
        params = {"session_token": "abc123def456"}
        redacted = _redact_params(params)

        assert redacted["session_token"] == "***REDACTED***"

    def test_redact_password(self) -> None:
        """Redact 'password' parameter."""
        params = {"username": "user", "password": "mypassword"}
        redacted = _redact_params(params)

        assert redacted["username"] == "user"
        assert redacted["password"] == "***REDACTED***"

    def test_redact_secret(self) -> None:
        """Redact 'secret' parameter."""
        params = {"api_secret": "mysecret"}
        redacted = _redact_params(params)

        assert redacted["api_secret"] == "***REDACTED***"

    def test_redact_case_insensitive(self) -> None:
        """Redaction is case-insensitive."""
        params = {"API_KEY": "secret", "Token": "token123"}
        redacted = _redact_params(params)

        assert redacted["API_KEY"] == "***REDACTED***"
        assert redacted["Token"] == "***REDACTED***"

    def test_redact_multiple_keys(self) -> None:
        """Redact multiple sensitive keys in single dict."""
        params = {
            "url": "https://example.com",
            "api_key": "key123",
            "session_token": "token456",
            "password": "pass789",
        }
        redacted = _redact_params(params)

        assert redacted["url"] == "https://example.com"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["session_token"] == "***REDACTED***"
        assert redacted["password"] == "***REDACTED***"


class TestLogInvocation:
    """log_invocation() function tests."""

    def test_log_creates_file(self, tmp_path: Path) -> None:
        """log_invocation() creates audit file."""
        audit_dir = tmp_path / "audit"

        checksum = log_invocation(
            client_id="client-123",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        # File should exist
        log_files = list(audit_dir.glob("*.jsonl"))
        assert len(log_files) == 1

        # Checksum should be returned
        assert len(checksum) == 16
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_log_entry_format(self, tmp_path: Path) -> None:
        """log_invocation() writes valid JSONL with all required fields."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-123",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        # Read and parse the file
        log_file = list(audit_dir.glob("*.jsonl"))[0]
        with open(log_file) as f:
            line = f.readline()

        entry = json.loads(line)

        # Verify all required fields
        assert entry["client_id"] == "client-123"
        assert entry["tool_name"] == "research_fetch"
        assert entry["params_summary"]["url"] == "https://example.com"
        assert entry["duration_ms"] == 500
        assert entry["status"] == "success"
        assert "timestamp" in entry
        assert "checksum" in entry

    def test_log_checksum_valid(self, tmp_path: Path) -> None:
        """log_invocation() checksum matches recomputation."""
        audit_dir = tmp_path / "audit"

        returned_checksum = log_invocation(
            client_id="client-123",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        # Read and verify checksum
        log_file = list(audit_dir.glob("*.jsonl"))[0]
        with open(log_file) as f:
            line = f.readline()

        entry = json.loads(line)
        stored_checksum = entry["checksum"]

        # Recompute checksum
        entry_copy = dict(entry)
        entry_copy.pop("checksum")
        json_str = json.dumps(entry_copy, separators=(",", ":"), sort_keys=True)
        computed_checksum = hashlib.sha256(json_str.encode()).hexdigest()[:16]

        assert stored_checksum == computed_checksum
        assert stored_checksum == returned_checksum

    def test_log_param_redaction_in_file(self, tmp_path: Path) -> None:
        """log_invocation() redacts sensitive params before logging."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-123",
            tool_name="research_fetch",
            params={
                "url": "https://example.com",
                "api_key": "secret123",
                "session_token": "token456",
            },
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        # Read and verify redaction
        log_file = list(audit_dir.glob("*.jsonl"))[0]
        with open(log_file) as f:
            line = f.readline()

        entry = json.loads(line)
        params = entry["params_summary"]

        assert params["url"] == "https://example.com"
        assert params["api_key"] == "***REDACTED***"
        assert params["session_token"] == "***REDACTED***"

    def test_log_daily_rotation(self, tmp_path: Path, monkeypatch) -> None:
        """log_invocation() creates separate files for different dates."""
        audit_dir = tmp_path / "audit"

        # Mock datetime to return different dates
        from datetime import UTC, datetime
        from unittest.mock import patch

        # Log entry for 2025-04-28
        with patch("loom.audit.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 4, 28, 10, 0, 0, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            log_invocation(
                client_id="client-123",
                tool_name="research_fetch",
                params={"url": "https://example.com"},
                result_summary="200 OK",
                duration_ms=500,
                status="success",
                audit_dir=audit_dir,
            )

        # Log entry for 2025-04-29
        with patch("loom.audit.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 4, 29, 10, 0, 0, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            log_invocation(
                client_id="client-123",
                tool_name="research_spider",
                params={"urls": ["https://example.com"]},
                result_summary="200 OK",
                duration_ms=1000,
                status="success",
                audit_dir=audit_dir,
            )

        # Should have 2 separate files
        log_files = sorted(audit_dir.glob("*.jsonl"))
        assert len(log_files) == 2

    def test_log_multiple_entries(self, tmp_path: Path) -> None:
        """log_invocation() appends multiple entries to same file."""
        audit_dir = tmp_path / "audit"

        checksums = []
        for i in range(5):
            checksum = log_invocation(
                client_id=f"client-{i}",
                tool_name="research_fetch",
                params={"url": f"https://example{i}.com"},
                result_summary="200 OK",
                duration_ms=500 + i * 100,
                status="success",
                audit_dir=audit_dir,
            )
            checksums.append(checksum)

        # Should have 1 file
        log_files = list(audit_dir.glob("*.jsonl"))
        assert len(log_files) == 1

        # Should have 5 lines
        log_file = log_files[0]
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 5

        # All checksums should be different
        assert len(set(checksums)) == 5


class TestVerifyIntegrity:
    """verify_integrity() function tests."""

    def test_verify_empty_file(self, tmp_path: Path) -> None:
        """verify_integrity() handles empty file."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        log_file = audit_dir / "2025-04-29.jsonl"
        log_file.touch()

        result = verify_integrity(log_file)

        assert result.entries == 0
        assert result.valid == 0
        assert result.invalid == 0
        assert result.tampered is False

    def test_verify_nonexistent_file(self, tmp_path: Path) -> None:
        """verify_integrity() handles nonexistent file."""
        log_file = tmp_path / "nonexistent.jsonl"

        result = verify_integrity(log_file)

        assert result.entries == 0
        assert result.valid == 0
        assert result.invalid == 0
        assert result.tampered is False

    def test_verify_valid_entries(self, tmp_path: Path) -> None:
        """verify_integrity() validates correct checksums."""
        audit_dir = tmp_path / "audit"

        # Log 3 entries
        for i in range(3):
            log_invocation(
                client_id=f"client-{i}",
                tool_name="research_fetch",
                params={"url": f"https://example{i}.com"},
                result_summary="200 OK",
                duration_ms=500,
                status="success",
                audit_dir=audit_dir,
            )

        # Verify
        log_file = list(audit_dir.glob("*.jsonl"))[0]
        result = verify_integrity(log_file)

        assert result.entries == 3
        assert result.valid == 3
        assert result.invalid == 0
        assert result.tampered is False

    def test_tamper_detection_checksum(self, tmp_path: Path) -> None:
        """verify_integrity() detects tampered checksum."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-123",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        # Tamper with checksum
        log_file = list(audit_dir.glob("*.jsonl"))[0]
        with open(log_file) as f:
            line = f.read()

        entry = json.loads(line)
        entry["checksum"] = "0000000000000000"  # Invalid checksum

        with open(log_file, "w") as f:
            f.write(json.dumps(entry) + "\n")

        # Verify
        result = verify_integrity(log_file)

        assert result.entries == 1
        assert result.valid == 0
        assert result.invalid == 1
        assert result.tampered is True

    def test_tamper_detection_field_change(self, tmp_path: Path) -> None:
        """verify_integrity() detects tampered field."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-123",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        # Tamper with a field
        log_file = list(audit_dir.glob("*.jsonl"))[0]
        with open(log_file) as f:
            line = f.read()

        entry = json.loads(line)
        entry["status"] = "error"  # Change status, keep checksum

        with open(log_file, "w") as f:
            f.write(json.dumps(entry) + "\n")

        # Verify
        result = verify_integrity(log_file)

        assert result.entries == 1
        assert result.valid == 0
        assert result.invalid == 1
        assert result.tampered is True

    def test_tamper_detection_missing_checksum(self, tmp_path: Path) -> None:
        """verify_integrity() detects missing checksum."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        log_file = audit_dir / "2025-04-29.jsonl"
        entry = {
            "client_id": "client-123",
            "tool_name": "research_fetch",
            "status": "success",
            "duration_ms": 500,
        }

        with open(log_file, "w") as f:
            f.write(json.dumps(entry) + "\n")

        # Verify
        result = verify_integrity(log_file)

        assert result.entries == 1
        assert result.valid == 0
        assert result.invalid == 1
        assert result.tampered is True

    def test_verify_mixed_valid_invalid(self, tmp_path: Path) -> None:
        """verify_integrity() handles mix of valid and invalid entries."""
        audit_dir = tmp_path / "audit"

        # Log 2 valid entries
        for i in range(2):
            log_invocation(
                client_id=f"client-{i}",
                tool_name="research_fetch",
                params={"url": f"https://example{i}.com"},
                result_summary="200 OK",
                duration_ms=500,
                status="success",
                audit_dir=audit_dir,
            )

        # Add 1 invalid entry
        log_file = list(audit_dir.glob("*.jsonl"))[0]
        with open(log_file, "a") as f:
            entry = {"client_id": "bad", "status": "success"}
            f.write(json.dumps(entry) + "\n")

        # Verify
        result = verify_integrity(log_file)

        assert result.entries == 3
        assert result.valid == 2
        assert result.invalid == 1
        assert result.tampered is True


class TestExportAudit:
    """export_audit() function tests."""

    def test_export_empty_directory(self, tmp_path: Path) -> None:
        """export_audit() returns empty list for nonexistent directory."""
        audit_dir = tmp_path / "nonexistent"

        result = export_audit(audit_dir=audit_dir)

        assert result["count"] == 0
        assert result["data"] == []

    def test_export_all_entries(self, tmp_path: Path) -> None:
        """export_audit() exports all entries."""
        audit_dir = tmp_path / "audit"

        # Log 3 entries
        for i in range(3):
            log_invocation(
                client_id=f"client-{i}",
                tool_name="research_fetch",
                params={"url": f"https://example{i}.com"},
                result_summary="200 OK",
                duration_ms=500,
                status="success",
                audit_dir=audit_dir,
            )

        # Export all
        result = export_audit(audit_dir=audit_dir)

        assert result["count"] == 3
        assert result["data"][0]["client_id"] == "client-0"
        assert result["data"][1]["client_id"] == "client-1"
        assert result["data"][2]["client_id"] == "client-2"

    def test_export_with_date_range(self, tmp_path: Path) -> None:
        """export_audit() filters by date range."""
        audit_dir = tmp_path / "audit"

        # Create files for different dates
        audit_dir.mkdir()
        for date in ["2025-04-27", "2025-04-28", "2025-04-29"]:
            log_file = audit_dir / f"{date}.jsonl"
            entry = {
                "client_id": "client-123",
                "tool_name": "research_fetch",
                "timestamp": f"{date}T10:00:00+00:00",
                "duration_ms": 500,
                "status": "success",
                "params_summary": {"url": "https://example.com"},
                "checksum": "abc123def456abc1",
            }
            with open(log_file, "w") as f:
                f.write(json.dumps(entry) + "\n")

        # Export 2025-04-28 only
        result = export_audit(start_date="2025-04-28", end_date="2025-04-28", audit_dir=audit_dir)

        assert result["count"] == 1
        assert "2025-04-28" in result["data"][0]["timestamp"]

    def test_export_includes_verification_status(self, tmp_path: Path) -> None:
        """export_audit() includes _verified field in entries."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-123",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result = export_audit(audit_dir=audit_dir)
        entries = result.get("data", result) if isinstance(result, dict) else result

        if isinstance(entries, list):
            assert len(entries) == 1
            assert "_verified" in entries[0]
            assert entries[0]["_verified"] is True
        else:
            assert entries["count"] == 1
