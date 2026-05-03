"""Tests for audit log retention policy."""
import gzip
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from loom.billing.retention import (
    archive_old_logs,
    verify_archived_readable,
    RETENTION_YEARS,
)


@pytest.fixture
def audit_dir(tmp_path: Path) -> Path:
    """Create a temporary audit directory."""
    return tmp_path / "audit"


@pytest.fixture
def archive_dir(tmp_path: Path) -> Path:
    """Create a temporary archive directory."""
    return tmp_path / "archive"


@pytest.fixture
def sample_logs(audit_dir: Path) -> dict:
    """Create sample log files with various dates.

    Returns a dict with paths and metadata for created files.
    """
    audit_dir.mkdir(parents=True, exist_ok=True)

    # Create logs with specific dates
    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).date()
    recent_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()

    old_log_file = audit_dir / f"{old_date.isoformat()}.jsonl"
    recent_log_file = audit_dir / f"{recent_date.isoformat()}.jsonl"

    # Write sample log entries
    with open(old_log_file, "w") as f:
        f.write(json.dumps({"timestamp": str(old_date), "action": "test1"}))
        f.write("\n")
        f.write(json.dumps({"timestamp": str(old_date), "action": "test2"}))
        f.write("\n")

    with open(recent_log_file, "w") as f:
        f.write(json.dumps({"timestamp": str(recent_date), "action": "test3"}))
        f.write("\n")

    return {
        "old_log_file": old_log_file,
        "recent_log_file": recent_log_file,
        "old_date": old_date,
        "recent_date": recent_date,
    }



pytestmark = pytest.mark.asyncio
class TestArchiveOldLogs:
    """Test suite for archive_old_logs function."""

    def test_archive_old_logs_compresses_older_files(
        self, audit_dir: Path, sample_logs: dict
    ) -> None:
        """Test that files older than 90 days are archived."""
        result = archive_old_logs(audit_dir, days_old=90)

        assert result["archived"] == 1
        assert "archive" in result["archive_dir"]

    def test_archive_old_logs_preserves_recent_files(
        self, audit_dir: Path, sample_logs: dict
    ) -> None:
        """Test that recent files are not archived."""
        result = archive_old_logs(audit_dir, days_old=90)

        # Recent file (30 days old) should not be archived
        recent_log = audit_dir / f"{sample_logs['recent_date'].isoformat()}.jsonl"
        assert recent_log.exists()

    def test_archived_files_are_gzipped(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test that archived files are stored as gzip."""
        archive_old_logs(audit_dir, archive_dir, days_old=90)

        # Check for gzip file
        gz_files = list(archive_dir.glob("*.gz"))
        assert len(gz_files) > 0

        # Verify it's a valid gzip file
        gz_file = gz_files[0]
        with gzip.open(gz_file, "rt") as f:
            content = f.read()
            assert len(content) > 0

    def test_archived_files_deleted_from_source(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test that original files are deleted after archival."""
        old_log = sample_logs["old_log_file"]
        assert old_log.exists()

        archive_old_logs(audit_dir, archive_dir, days_old=90)

        assert not old_log.exists()

    def test_archive_dir_created_automatically(
        self, audit_dir: Path, sample_logs: dict
    ) -> None:
        """Test that archive directory is created if it doesn't exist."""
        archive_path = audit_dir / "archive"
        assert not archive_path.exists()

        archive_old_logs(audit_dir, archive_path, days_old=90)

        assert archive_path.exists()

    def test_archive_returns_correct_count(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test that result contains accurate archive count."""
        result = archive_old_logs(audit_dir, archive_dir, days_old=90)

        assert isinstance(result, dict)
        assert "archived" in result
        assert "archive_dir" in result
        assert result["archived"] == 1

    def test_archive_handles_non_date_named_files(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test that files with non-standard names are skipped."""
        # Add a file with non-date name
        non_date_file = audit_dir / "invalid_name.jsonl"
        non_date_file.write_text("test content")

        result = archive_old_logs(audit_dir, archive_dir, days_old=90)

        # Should only archive the valid date-named file
        assert result["archived"] == 1
        # Non-date file should still exist
        assert non_date_file.exists()

    def test_archive_with_custom_days_threshold(
        self, audit_dir: Path, archive_dir: Path
    ) -> None:
        """Test archiving with custom days_old threshold."""
        # Create log exactly 30 days old
        audit_dir.mkdir(parents=True, exist_ok=True)
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date()
        log_file = audit_dir / f"{thirty_days_ago.isoformat()}.jsonl"
        log_file.write_text("test")

        # Archive with threshold of 20 days (should archive this file)
        result = archive_old_logs(audit_dir, archive_dir, days_old=20)
        assert result["archived"] == 1

        # Archive with threshold of 40 days (should not archive)
        log_file.write_text("test")  # Recreate it
        result = archive_old_logs(audit_dir, archive_dir, days_old=40)
        assert result["archived"] == 0


class TestVerifyArchivedReadable:
    """Test suite for verify_archived_readable function."""

    def test_verify_readable_archives(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test that archived files are verified as readable."""
        archive_old_logs(audit_dir, archive_dir, days_old=90)

        result = verify_archived_readable(archive_dir)

        assert result["readable"] == 1
        assert result["corrupt"] == 0
        assert result["total"] == 1

    async def test_verify_reports_corrupt_archives(self, archive_dir: Path) -> None:
        """Test that corrupt gzip files are detected."""
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Create a corrupted gzip file
        corrupt_gz = archive_dir / "corrupt.jsonl.gz"
        corrupt_gz.write_bytes(b"this is not gzip")

        result = verify_archived_readable(archive_dir)

        assert result["corrupt"] == 1
        assert result["readable"] == 0
        assert result["total"] == 1

    async def test_verify_empty_archive_dir(self, archive_dir: Path) -> None:
        """Test verification on empty archive directory."""
        archive_dir.mkdir(parents=True, exist_ok=True)

        result = verify_archived_readable(archive_dir)

        assert result["readable"] == 0
        assert result["corrupt"] == 0
        assert result["total"] == 0

    def test_verify_mixed_readable_and_corrupt(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test verification with both readable and corrupt files."""
        # Archive valid logs
        archive_old_logs(audit_dir, archive_dir, days_old=90)

        # Add a corrupt file
        corrupt_gz = archive_dir / "corrupt.jsonl.gz"
        corrupt_gz.write_bytes(b"corrupted")

        result = verify_archived_readable(archive_dir)

        assert result["readable"] == 1
        assert result["corrupt"] == 1
        assert result["total"] == 2

    def test_verify_reads_archive_content(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test that verification actually reads archive content."""
        archive_old_logs(audit_dir, archive_dir, days_old=90)

        result = verify_archived_readable(archive_dir)

        # Result indicates at least one readable file
        assert result["readable"] >= 1

        # Manually verify we can read the archived file
        gz_files = list(archive_dir.glob("*.gz"))
        assert len(gz_files) > 0

        with gzip.open(gz_files[0], "rt") as f:
            content = f.read()
            assert "test" in content or "action" in content


class TestRetentionConstants:
    """Test suite for retention policy constants."""

    async def test_retention_years_constant(self) -> None:
        """Test that retention years constant is set correctly."""
        assert RETENTION_YEARS == 5
        assert isinstance(RETENTION_YEARS, int)


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_full_archival_workflow(
        self, audit_dir: Path, archive_dir: Path
    ) -> None:
        """Test complete archival and verification workflow."""
        # Create multiple log files
        audit_dir.mkdir(parents=True, exist_ok=True)
        for days_back in [10, 50, 100, 200]:
            date = (datetime.now(timezone.utc) - timedelta(days=days_back)).date()
            log_file = audit_dir / f"{date.isoformat()}.jsonl"
            log_file.write_text(f"Log entry for {days_back} days ago\n")

        # Archive logs older than 90 days
        archive_result = archive_old_logs(audit_dir, archive_dir, days_old=90)
        assert archive_result["archived"] == 2  # 100 and 200 days old

        # Verify archives
        verify_result = verify_archived_readable(archive_dir)
        assert verify_result["readable"] == 2
        assert verify_result["corrupt"] == 0

        # Check that recent logs remain
        recent_files = list(audit_dir.glob("*.jsonl"))
        assert len(recent_files) == 2  # 10 and 50 days old

    def test_idempotent_archival(
        self, audit_dir: Path, archive_dir: Path, sample_logs: dict
    ) -> None:
        """Test that running archival multiple times is safe."""
        result1 = archive_old_logs(audit_dir, archive_dir, days_old=90)
        result2 = archive_old_logs(audit_dir, archive_dir, days_old=90)

        # Second run should archive 0 files (already done)
        assert result1["archived"] == 1
        assert result2["archived"] == 0

    def test_default_archive_dir_parameter(
        self, audit_dir: Path, sample_logs: dict
    ) -> None:
        """Test that default archive_dir is created in audit_dir."""
        result = archive_old_logs(audit_dir, days_old=90)

        default_archive = audit_dir / "archive"
        assert default_archive.exists()
        assert str(default_archive) in result["archive_dir"]
