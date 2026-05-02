"""Data export tools for research results — JSON, CSV, and file listing."""

from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.data_export")

# Export directory
_EXPORT_DIR = Path.home() / ".loom" / "exports"


def _ensure_export_dir() -> Path:
    """Ensure export directory exists."""
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return _EXPORT_DIR


async def research_export_json(
    data: dict,
    filename: str = "export",
    pretty: bool = True,
) -> dict[str, Any]:
    """Export research data as JSON file.

    Args:
        data: Dictionary to export
        filename: Base filename (without extension)
        pretty: Pretty-print JSON (default: True)

    Returns:
        Dict with keys: exported, path, size_bytes, records_count
    """
    try:
        export_dir = _ensure_export_dir()
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filepath = export_dir / f"{filename}_{timestamp}.json"

        content = json.dumps(
            data,
            indent=2 if pretty else None,
            default=str,
        )

        filepath.write_text(content, encoding="utf-8")
        size_bytes = filepath.stat().st_size
        records_count = len(data) if isinstance(data, dict) else 1

        logger.info(
            "json_export_success",
            filename=filepath.name,
            size_bytes=size_bytes,
            records_count=records_count,
        )

        return {
            "exported": True,
            "path": str(filepath),
            "size_bytes": size_bytes,
            "records_count": records_count,
        }
    except Exception as e:
        logger.error("json_export_error", error=str(e))
        return {
            "exported": False,
            "error": str(e),
        }


async def research_export_csv(
    data: list[dict],
    filename: str = "export",
) -> dict[str, Any]:
    """Export list of dicts as CSV.

    Auto-detects columns from first dict.

    Args:
        data: List of dictionaries
        filename: Base filename (without extension)

    Returns:
        Dict with keys: exported, path, rows, columns
    """
    try:
        if not data:
            return {
                "exported": False,
                "error": "data list is empty",
            }

        export_dir = _ensure_export_dir()
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filepath = export_dir / f"{filename}_{timestamp}.csv"

        columns = list(data[0].keys()) if data else []

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)

        size_bytes = filepath.stat().st_size
        rows = len(data)

        logger.info(
            "csv_export_success",
            filename=filepath.name,
            rows=rows,
            columns=len(columns),
        )

        return {
            "exported": True,
            "path": str(filepath),
            "rows": rows,
            "columns": columns,
        }
    except Exception as e:
        logger.error("csv_export_error", error=str(e))
        return {
            "exported": False,
            "error": str(e),
        }


async def research_export_list(limit: int = 50) -> dict[str, Any]:
    """List all exported files.

    Args:
        limit: Maximum number of files to return

    Returns:
        Dict with keys: exports, total, total_size_mb
    """
    try:
        export_dir = _ensure_export_dir()

        if not export_dir.exists():
            return {
                "exports": [],
                "total": 0,
                "total_size_mb": 0,
            }

        files = []
        total_bytes = 0

        for filepath in sorted(export_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            if filepath.is_file():
                stat = filepath.stat()
                total_bytes += stat.st_size
                created = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()
                fmt = filepath.suffix.lstrip(".")

                # Count records for files we can read
                records = 0
                try:
                    if fmt == "json":
                        content = json.loads(filepath.read_text(encoding="utf-8"))
                        records = len(content) if isinstance(content, dict) else 1
                    elif fmt == "csv":
                        with open(filepath, encoding="utf-8") as f:
                            records = sum(1 for _ in f) - 1  # Exclude header
                except Exception:
                    pass

                files.append({
                    "filename": filepath.name,
                    "format": fmt,
                    "size_bytes": stat.st_size,
                    "created": created,
                    "records": records,
                })

        total_size_mb = round(total_bytes / (1024 * 1024), 2)

        logger.info(
            "export_list_success",
            count=len(files),
            total_size_mb=total_size_mb,
        )

        return {
            "exports": files,
            "total": len(files),
            "total_size_mb": total_size_mb,
        }
    except Exception as e:
        logger.error("export_list_error", error=str(e))
        return {
            "exports": [],
            "total": 0,
            "total_size_mb": 0,
            "error": str(e),
        }
