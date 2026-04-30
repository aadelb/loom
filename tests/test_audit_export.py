"""Unit tests for audit export API (REQ-089).

Tests cover:
- export_audit() with JSON format → valid JSON array
- export_audit() with CSV format → valid CSV string with headers
- Date filtering works (only entries in specified range)
- Export empty → count=0
- Export all (no dates) → all entries
- Register as MCP tool (research_audit_export)
- Format validation
- Empty file handling
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from loom.audit import export_audit, log_invocation


class TestExportAuditJSON:
    """export_audit() JSON format tests."""

    def test_export_json_empty_directory(self, tmp_path: Path) -> None:
        """Export JSON from empty directory → count=0."""
        audit_dir = tmp_path / "nonexistent"

        result = export_audit(format="json", audit_dir=audit_dir)

        assert result["format"] == "json"
        assert result["data"] == []
        assert result["count"] == 0

    def test_export_json_single_entry(self, tmp_path: Path) -> None:
        """Export JSON with single entry → valid JSON array."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-1",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result = export_audit(format="json", audit_dir=audit_dir)

        assert result["format"] == "json"
        assert result["count"] == 1
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1

        entry = result["data"][0]
        assert entry["client_id"] == "client-1"
        assert entry["tool_name"] == "research_fetch"
        assert entry["_verified"] is True

    def test_export_json_multiple_entries(self, tmp_path: Path) -> None:
        """Export JSON with multiple entries → valid JSON array."""
        audit_dir = tmp_path / "audit"

        for i in range(5):
            log_invocation(
                client_id=f"client-{i}",
                tool_name="research_fetch",
                params={"url": f"https://example{i}.com"},
                result_summary="200 OK",
                duration_ms=500 + i * 100,
                status="success",
                audit_dir=audit_dir,
            )

        result = export_audit(format="json", audit_dir=audit_dir)

        assert result["format"] == "json"
        assert result["count"] == 5
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 5

        for i, entry in enumerate(result["data"]):
            assert entry["client_id"] == f"client-{i}"

    def test_export_json_has_verification_status(self, tmp_path: Path) -> None:
        """Export JSON includes _verified field for each entry."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-1",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result = export_audit(format="json", audit_dir=audit_dir)

        assert result["count"] == 1
        entry = result["data"][0]
        assert "_verified" in entry
        assert isinstance(entry["_verified"], bool)
        assert entry["_verified"] is True


class TestExportAuditCSV:
    """export_audit() CSV format tests."""

    def test_export_csv_empty_directory(self, tmp_path: Path) -> None:
        """Export CSV from empty directory → count=0."""
        audit_dir = tmp_path / "nonexistent"

        result = export_audit(format="csv", audit_dir=audit_dir)

        assert result["format"] == "csv"
        assert result["data"] == ""
        assert result["count"] == 0

    def test_export_csv_single_entry(self, tmp_path: Path) -> None:
        """Export CSV with single entry → valid CSV with headers."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-1",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result = export_audit(format="csv", audit_dir=audit_dir)

        assert result["format"] == "csv"
        assert result["count"] == 1
        assert isinstance(result["data"], str)

        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(result["data"]))
        rows = list(csv_reader)

        assert len(rows) == 1
        row = rows[0]
        assert row["client_id"] == "client-1"
        assert row["tool_name"] == "research_fetch"
        assert row["status"] == "success"

    def test_export_csv_has_headers(self, tmp_path: Path) -> None:
        """Export CSV includes all field headers."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-1",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result = export_audit(format="csv", audit_dir=audit_dir)

        csv_reader = csv.DictReader(io.StringIO(result["data"]))
        fieldnames = csv_reader.fieldnames

        # Should have all expected fields
        assert fieldnames is not None
        assert "client_id" in fieldnames
        assert "tool_name" in fieldnames
        assert "status" in fieldnames
        assert "timestamp" in fieldnames
        assert "duration_ms" in fieldnames
        assert "checksum" in fieldnames
        assert "_verified" in fieldnames

    def test_export_csv_multiple_entries(self, tmp_path: Path) -> None:
        """Export CSV with multiple entries → valid CSV rows."""
        audit_dir = tmp_path / "audit"

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

        result = export_audit(format="csv", audit_dir=audit_dir)

        assert result["count"] == 3
        csv_reader = csv.DictReader(io.StringIO(result["data"]))
        rows = list(csv_reader)

        assert len(rows) == 3
        for i, row in enumerate(rows):
            assert row["client_id"] == f"client-{i}"

    def test_export_csv_json_fields_serialized(self, tmp_path: Path) -> None:
        """Export CSV serializes nested JSON objects as strings."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-1",
            tool_name="research_fetch",
            params={
                "url": "https://example.com",
                "headers": {"User-Agent": "test"},
            },
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result = export_audit(format="csv", audit_dir=audit_dir)

        csv_reader = csv.DictReader(io.StringIO(result["data"]))
        row = list(csv_reader)[0]

        # params_summary should be JSON string in CSV
        assert "params_summary" in row
        params = json.loads(row["params_summary"])
        assert params["url"] == "https://example.com"


class TestExportAuditDateFiltering:
    """export_audit() date filtering tests."""

    def test_export_with_start_date(self, tmp_path: Path) -> None:
        """Export filters entries with start_date."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        # Create entries for different dates
        for date in ["2025-04-27", "2025-04-28", "2025-04-29"]:
            log_file = audit_dir / f"{date}.jsonl"
            entry = {
                "client_id": f"client-{date}",
                "tool_name": "research_fetch",
                "timestamp": f"{date}T10:00:00+00:00",
                "duration_ms": 500,
                "status": "success",
                "params_summary": {"url": "https://example.com"},
                "checksum": "abc123def456abc1",
            }
            with open(log_file, "w") as f:
                f.write(json.dumps(entry) + "\n")

        # Export from 2025-04-28 onwards
        result = export_audit(start_date="2025-04-28", format="json", audit_dir=audit_dir)

        assert result["count"] == 2
        assert result["data"][0]["client_id"] == "client-2025-04-28"
        assert result["data"][1]["client_id"] == "client-2025-04-29"

    def test_export_with_end_date(self, tmp_path: Path) -> None:
        """Export filters entries with end_date."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        # Create entries for different dates
        for date in ["2025-04-27", "2025-04-28", "2025-04-29"]:
            log_file = audit_dir / f"{date}.jsonl"
            entry = {
                "client_id": f"client-{date}",
                "tool_name": "research_fetch",
                "timestamp": f"{date}T10:00:00+00:00",
                "duration_ms": 500,
                "status": "success",
                "params_summary": {"url": "https://example.com"},
                "checksum": "abc123def456abc1",
            }
            with open(log_file, "w") as f:
                f.write(json.dumps(entry) + "\n")

        # Export up to 2025-04-28
        result = export_audit(end_date="2025-04-28", format="json", audit_dir=audit_dir)

        assert result["count"] == 2
        assert result["data"][0]["client_id"] == "client-2025-04-27"
        assert result["data"][1]["client_id"] == "client-2025-04-28"

    def test_export_with_date_range(self, tmp_path: Path) -> None:
        """Export filters entries with both start_date and end_date."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()

        # Create entries for different dates
        for date in ["2025-04-26", "2025-04-27", "2025-04-28", "2025-04-29"]:
            log_file = audit_dir / f"{date}.jsonl"
            entry = {
                "client_id": f"client-{date}",
                "tool_name": "research_fetch",
                "timestamp": f"{date}T10:00:00+00:00",
                "duration_ms": 500,
                "status": "success",
                "params_summary": {"url": "https://example.com"},
                "checksum": "abc123def456abc1",
            }
            with open(log_file, "w") as f:
                f.write(json.dumps(entry) + "\n")

        # Export 2025-04-27 to 2025-04-28
        result = export_audit(
            start_date="2025-04-27",
            end_date="2025-04-28",
            format="json",
            audit_dir=audit_dir,
        )

        assert result["count"] == 2
        assert result["data"][0]["client_id"] == "client-2025-04-27"
        assert result["data"][1]["client_id"] == "client-2025-04-28"

    def test_export_no_dates_returns_all(self, tmp_path: Path) -> None:
        """Export without dates returns all entries."""
        audit_dir = tmp_path / "audit"

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

        result = export_audit(format="json", audit_dir=audit_dir)

        assert result["count"] == 3


class TestExportAuditValidation:
    """export_audit() parameter validation tests."""

    def test_export_invalid_format_raises_error(self, tmp_path: Path) -> None:
        """Export with invalid format raises ValueError."""
        audit_dir = tmp_path / "audit"

        with pytest.raises(ValueError, match='format must be "json" or "csv"'):
            export_audit(format="xml", audit_dir=audit_dir)

    def test_export_json_default_format(self, tmp_path: Path) -> None:
        """Export uses JSON as default format."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-1",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result = export_audit(audit_dir=audit_dir)

        assert result["format"] == "json"
        assert isinstance(result["data"], list)


class TestExportAuditReturnFormat:
    """export_audit() return value format tests."""

    def test_export_returns_dict_with_required_keys(self, tmp_path: Path) -> None:
        """Export returns dict with format, data, count."""
        audit_dir = tmp_path / "audit"

        result = export_audit(format="json", audit_dir=audit_dir)

        assert isinstance(result, dict)
        assert "format" in result
        assert "data" in result
        assert "count" in result

    def test_export_count_matches_data_length(self, tmp_path: Path) -> None:
        """Export count field matches data length."""
        audit_dir = tmp_path / "audit"

        for i in range(5):
            log_invocation(
                client_id=f"client-{i}",
                tool_name="research_fetch",
                params={"url": f"https://example{i}.com"},
                result_summary="200 OK",
                duration_ms=500,
                status="success",
                audit_dir=audit_dir,
            )

        result_json = export_audit(format="json", audit_dir=audit_dir)
        assert result_json["count"] == len(result_json["data"])

        result_csv = export_audit(format="csv", audit_dir=audit_dir)
        csv_reader = csv.DictReader(io.StringIO(result_csv["data"]))
        csv_rows = list(csv_reader)
        assert result_csv["count"] == len(csv_rows)


class TestExportAuditIntegration:
    """Integration tests for export_audit()."""

    def test_export_json_and_csv_same_entry_count(self, tmp_path: Path) -> None:
        """JSON and CSV exports have same entry count."""
        audit_dir = tmp_path / "audit"

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

        result_json = export_audit(format="json", audit_dir=audit_dir)
        result_csv = export_audit(format="csv", audit_dir=audit_dir)

        assert result_json["count"] == result_csv["count"]

    def test_export_json_matches_csv_entries(self, tmp_path: Path) -> None:
        """JSON and CSV exports contain same data."""
        audit_dir = tmp_path / "audit"

        log_invocation(
            client_id="client-1",
            tool_name="research_fetch",
            params={"url": "https://example.com"},
            result_summary="200 OK",
            duration_ms=500,
            status="success",
            audit_dir=audit_dir,
        )

        result_json = export_audit(format="json", audit_dir=audit_dir)
        result_csv = export_audit(format="csv", audit_dir=audit_dir)

        json_entry = result_json["data"][0]
        csv_reader = csv.DictReader(io.StringIO(result_csv["data"]))
        csv_entry = list(csv_reader)[0]

        # Check key fields match
        assert json_entry["client_id"] == csv_entry["client_id"]
        assert json_entry["tool_name"] == csv_entry["tool_name"]
        assert json_entry["status"] == csv_entry["status"]
