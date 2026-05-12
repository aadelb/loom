"""YARA backend — malware detection and pattern matching.

YARA is a pattern matching engine for identifying and classifying malware.
This module provides a wrapper around the yara-python library for compiling
YARA rules and scanning files/directories with detailed match reporting.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.yara_backend")

try:
    import yara
    YARA_AVAILABLE = True
except ImportError:
    YARA_AVAILABLE = False


def _validate_rules_path(rules_path: str) -> str:
    """Validate YARA rules file path.

    Args:
        rules_path: path to YARA rules file

    Returns:
        The validated path

    Raises:
        ValueError: if path is invalid
    """
    rules_path = rules_path.strip() if isinstance(rules_path, str) else ""

    if not rules_path or len(rules_path) > 1024:
        raise ValueError("rules_path must be 1-1024 characters")

    # Check for path traversal
    if ".." in rules_path:
        raise ValueError("rules_path contains parent directory references")

    # Must be a file path
    if not rules_path.endswith((".yar", ".yara", ".txt")):
        raise ValueError("rules_path must end with .yar, .yara, or .txt")

    # Validate it exists and is readable
    try:
        path = Path(rules_path).resolve()
        if not path.exists():
            raise ValueError(f"rules file does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"rules path is not a file: {path}")
        if not os.access(path, os.R_OK):
            raise ValueError(f"rules file is not readable: {path}")
    except Exception as exc:
        raise ValueError(f"invalid rules_path: {str(exc)}")

    return str(path)


def _validate_target_path(target_path: str) -> str:
    """Validate target file or directory path.

    Args:
        target_path: path to file or directory to scan

    Returns:
        The validated path

    Raises:
        ValueError: if path is invalid
    """
    target_path = target_path.strip() if isinstance(target_path, str) else ""

    if not target_path or len(target_path) > 1024:
        raise ValueError("target_path must be 1-1024 characters")

    # Check for path traversal
    if ".." in target_path:
        raise ValueError("target_path contains parent directory references")

    # Validate it exists and is readable
    try:
        path = Path(target_path).resolve()
        if not path.exists():
            raise ValueError(f"target path does not exist: {path}")
        if not os.access(path, os.R_OK):
            raise ValueError(f"target path is not readable: {path}")
    except Exception as exc:
        raise ValueError(f"invalid target_path: {str(exc)}")

    return str(path)


def _validate_timeout(timeout: int) -> int:
    """Validate timeout value.

    Args:
        timeout: timeout in seconds

    Returns:
        The validated timeout

    Raises:
        ValueError: if timeout is invalid
    """
    if not isinstance(timeout, int):
        raise ValueError("timeout must be an integer")

    if timeout < 1 or timeout > 3600:
        raise ValueError("timeout must be between 1 and 3600 seconds")

    return timeout


def _check_yara_available() -> tuple[bool, str]:
    """Check if YARA library is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    if not YARA_AVAILABLE:
        return False, (
            "YARA library not found. Install with: pip install yara-python"
        )

    try:
        # Try to get YARA version
        version = yara.__version__ if hasattr(yara, "__version__") else "unknown"
        return True, f"YARA library available (version: {version})"
    except Exception as exc:
        return False, f"YARA availability check error: {str(exc)}"


def _scan_file(
    rules: Any, file_path: str, timeout: int = 60
) -> dict[str, Any]:
    """Scan a single file with compiled YARA rules.

    Args:
        rules: compiled YARA rules object
        file_path: path to file to scan
        timeout: timeout in seconds

    Returns:
        Dict with scan results
    """
    matches = []
    try:
        file_matches = rules.match(file_path, timeout=timeout)

        for match in file_matches:
            match_data = {
                "rule": match.rule,
                "namespace": match.namespace,
                "tags": match.tags,
                "strings": [],
            }

            # Extract string matches
            for string_match in match.strings:
                match_data["strings"].append(
                    {
                        "offset": string_match.instances[0].offset
                        if string_match.instances
                        else 0,
                        "matched_string": (
                            str(string_match.instances[0].matched_string)[:100]
                            if string_match.instances
                            else ""
                        ),
                    }
                )

            matches.append(match_data)

    except yara.TimeoutError:
        logger.warning(f"YARA scan timeout on {file_path}")
    except Exception as exc:
        logger.warning(f"YARA scan error on {file_path}: {exc}")

    return {"file": file_path, "matches": matches, "match_count": len(matches)}


def _scan_directory(
    rules: Any, dir_path: str, timeout: int = 60
) -> dict[str, Any]:
    """Recursively scan all files in a directory.

    Args:
        rules: compiled YARA rules object
        dir_path: path to directory to scan
        timeout: timeout in seconds per file

    Returns:
        Dict with aggregated scan results
    """
    all_matches = []
    files_scanned = 0
    total_matches = 0

    try:
        # Recursively scan all files
        for root, _, files in os.walk(dir_path):
            for filename in files:
                file_path = os.path.join(root, filename)

                # Skip very large files (>100MB)
                try:
                    if os.path.getsize(file_path) > 100 * 1024 * 1024:
                        logger.debug(f"Skipping large file: {file_path}")
                        continue
                except OSError:
                    continue

                # Scan file
                result = _scan_file(rules, file_path, timeout)
                files_scanned += 1

                if result["match_count"] > 0:
                    all_matches.append(result)
                    total_matches += result["match_count"]

    except Exception as exc:
        logger.exception(f"Error scanning directory {dir_path}: {exc}")

    return {
        "directory": dir_path,
        "files_scanned": files_scanned,
        "matches": all_matches,
        "total_matches": total_matches,
    }

@handle_tool_errors("research_yara_scan")

async def research_yara_scan(
    rules_path: str, target_path: str, timeout: int = 60
) -> dict[str, Any]:
    """Scan files for malware patterns using compiled YARA rules.

    Compiles YARA rules from a file and scans a target file or directory
    for matches. Returns detailed information about what was matched.

    Args:
        rules_path: path to YARA rules file (.yar, .yara, or .txt)
        target_path: path to file or directory to scan
        timeout: timeout in seconds per file (default 60)

    Returns:
        Dict with:
        - rules_file: path to the rules file used
        - target: path to scanned target
        - matches: list of files with matches and their details
        - total_matches: total count of YARA rule matches
        - files_scanned: count of files scanned (if directory)
        - target_type: "file" or "directory"
        - yara_available: bool indicating if YARA library is available
        - error: error message if scan failed (optional)
    """
    try:
        rules_path = _validate_rules_path(rules_path)
        target_path = _validate_target_path(target_path)
        timeout = _validate_timeout(timeout)
    except ValueError as exc:
        return {
            "rules_file": rules_path,
            "target": target_path,
            "error": str(exc),
            "yara_available": False,
        }

    # Check if YARA is available
    available, msg = _check_yara_available()
    if not available:
        return {
            "rules_file": rules_path,
            "target": target_path,
            "error": msg,
            "yara_available": False,
        }

    try:
        # Compile YARA rules asynchronously
        rules = await asyncio.to_thread(yara.compile, filepath=rules_path)

        # Determine if target is file or directory
        target_is_dir = os.path.isdir(target_path)
        target_type = "directory" if target_is_dir else "file"

        # Run scan asynchronously
        if target_is_dir:
            scan_result = await asyncio.to_thread(
                _scan_directory, rules, target_path, timeout
            )
            output: dict[str, Any] = {
                "rules_file": rules_path,
                "target": target_path,
                "target_type": target_type,
                "matches": scan_result["matches"],
                "total_matches": scan_result["total_matches"],
                "files_scanned": scan_result["files_scanned"],
                "yara_available": True,
            }
        else:
            scan_result = await asyncio.to_thread(
                _scan_file, rules, target_path, timeout
            )
            output = {
                "rules_file": rules_path,
                "target": target_path,
                "target_type": target_type,
                "matches": scan_result["matches"],
                "total_matches": scan_result["match_count"],
                "yara_available": True,
            }

        return output

    except yara.Error as exc:
        logger.exception("YARA compilation or scan error")
        return {
            "rules_file": rules_path,
            "target": target_path,
            "error": f"YARA error: {str(exc)}",
            "yara_available": True,
        }
    except Exception as exc:
        logger.exception("YARA scan failed")
        return {
            "rules_file": rules_path,
            "target": target_path,
            "error": f"YARA scan error: {str(exc)}",
            "yara_available": True,
        }
