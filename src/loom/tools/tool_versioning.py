"""Tool versioning system for tracking deployed tool versions.

Provides content-addressable versioning using SHA-256 hashes of tool files
for deployment tracking and change detection.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).parent
SNAPSHOTS_DIR = Path.home() / ".loom" / "version_snapshots"


from loom.error_responses import handle_tool_errors
def _hash_file(path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _count_lines(path: Path) -> int:
    """Count lines of code in a file."""
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (UnicodeDecodeError, OSError):
        return 0


def _tool_info(path: Path) -> dict[str, Any]:
    """Get version info for a single tool file."""
    stat = path.stat()
    return {
        "tool": path.stem,
        "version_hash": _hash_file(path),
        "file_size": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        "lines_of_code": _count_lines(path),
    }

@handle_tool_errors("research_tool_version")

async def research_tool_version(tool_name: str = "") -> dict[str, Any]:
    """Get version info for a tool or all tools.

    Args:
        tool_name: Tool name (without .py). Empty = all tools.

    Returns:
        Single tool: {tool, version_hash, file_size, last_modified, lines_of_code}
        All tools: {tools_count, total_size_bytes, tools: [...]}
    """
    if tool_name:
        tool_file = TOOLS_DIR / f"{tool_name}.py"
        if not tool_file.exists():
            return {"error": f"Tool '{tool_name}' not found"}
        try:
            return _tool_info(tool_file)
        except (OSError, ValueError) as e:
            return {"error": f"Failed to version '{tool_name}': {e}"}

    tools, total_size = [], 0
    for tool_file in sorted(TOOLS_DIR.glob("*.py")):
        if tool_file.name.startswith("_"):
            continue
        try:
            info = _tool_info(tool_file)
            tools.append(info)
            total_size += info["file_size"]
        except (OSError, ValueError):
            pass

    return {"tools_count": len(tools), "total_size_bytes": total_size, "tools": tools}

@handle_tool_errors("research_version_diff")

async def research_version_diff(tool_name: str, previous_hash: str = "") -> dict[str, Any]:
    """Compare current version with a previous hash.

    Args:
        tool_name: Tool name (without .py)
        previous_hash: Previous version hash to compare

    Returns:
        {tool, current_hash, previous_hash, changed, current_size, current_lines}
    """
    tool_file = TOOLS_DIR / f"{tool_name}.py"
    if not tool_file.exists():
        return {"error": f"Tool '{tool_name}' not found"}

    try:
        info = _tool_info(tool_file)
        return {
            "tool": tool_name,
            "current_hash": info["version_hash"],
            "previous_hash": previous_hash or "none",
            "changed": info["version_hash"] != (previous_hash or ""),
            "current_size": info["file_size"],
            "current_lines": info["lines_of_code"],
        }
    except (OSError, ValueError) as e:
        return {"error": f"Failed to diff '{tool_name}': {e}"}

@handle_tool_errors("research_version_snapshot")

async def research_version_snapshot() -> dict[str, Any]:
    """Take a snapshot of all tool versions for deployment tracking.

    Saves snapshot to ~/.loom/version_snapshots/{timestamp}.json

    Returns:
        {snapshot_id, tools_count, total_size_bytes, timestamp, file_path}
    """
    try:
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        snapshot_data = {"timestamp": datetime.now(tz=UTC).isoformat(), "tools": {}}
        total_size = 0

        for tool_file in sorted(TOOLS_DIR.glob("*.py")):
            if tool_file.name.startswith("_"):
                continue
            try:
                info = _tool_info(tool_file)
                snapshot_data["tools"][info["tool"]] = {
                    "version_hash": info["version_hash"],
                    "file_size": info["file_size"],
                    "lines_of_code": info["lines_of_code"],
                }
                total_size += info["file_size"]
            except (OSError, ValueError):
                pass

        timestamp_str = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snapshot_{timestamp_str}"
        snapshot_file = SNAPSHOTS_DIR / f"{snapshot_id}.json"
        snapshot_file.write_text(json.dumps(snapshot_data, indent=2))

        return {
            "snapshot_id": snapshot_id,
            "tools_count": len(snapshot_data["tools"]),
            "total_size_bytes": total_size,
            "timestamp": snapshot_data["timestamp"],
            "file_path": str(snapshot_file),
        }
    except (OSError, ValueError) as e:
        return {"error": f"Failed to create snapshot: {e}"}
