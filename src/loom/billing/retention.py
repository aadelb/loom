"""Audit log retention policy — 5-year archival."""
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import TypedDict


class ArchiveResult(TypedDict):
    """Result of archiving operation."""

    archived: int
    archive_dir: str


class VerificationResult(TypedDict):
    """Result of archive verification."""

    readable: int
    corrupt: int
    total: int


def archive_old_logs(
    audit_dir: Path,
    archive_dir: Path | None = None,
    days_old: int = 90,
) -> ArchiveResult:
    """Compress and archive audit logs older than days_old.

    Args:
        audit_dir: Directory containing audit log files
        archive_dir: Directory to store compressed logs (default: audit_dir/archive)
        days_old: Archive logs older than this many days (default: 90)

    Returns:
        Dictionary with count of archived files and archive directory path
    """
    if archive_dir is None:
        archive_dir = Path(audit_dir) / "archive"

    archive_dir = Path(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
    archived = 0

    audit_dir = Path(audit_dir)

    for log_file in audit_dir.glob("*.jsonl"):
        try:
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            if file_date < cutoff:
                gz_path = archive_dir / f"{log_file.name}.gz"
                with open(log_file, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                log_file.unlink()
                archived += 1
        except ValueError:
            # Skip files that don't match date format
            continue

    return {
        "archived": archived,
        "archive_dir": str(archive_dir),
    }


def verify_archived_readable(archive_dir: Path) -> VerificationResult:
    """Verify archived logs are still readable.

    Args:
        archive_dir: Directory containing archived (gzip) log files

    Returns:
        Dictionary with counts of readable, corrupt, and total files
    """
    archive_dir = Path(archive_dir)
    readable = 0
    corrupt = 0

    for gz_file in archive_dir.glob("*.gz"):
        try:
            with gzip.open(gz_file, "rt") as f:
                f.read(100)
            readable += 1
        except Exception:
            corrupt += 1

    return {
        "readable": readable,
        "corrupt": corrupt,
        "total": readable + corrupt,
    }


RETENTION_YEARS: int = 5
"""Audit logs are retained for 5 years as per compliance requirements."""
