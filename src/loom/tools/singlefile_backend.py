"""SingleFile backend — complete webpage archive and preservation.

SingleFile is a tool that saves complete web pages as single HTML files,
including all assets (CSS, JavaScript, images) embedded as base64. This module
provides a wrapper around the SingleFile CLI with subprocess execution and
file handling.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.singlefile_backend")


def _validate_url(url: str) -> str:
    """Validate URL for SingleFile archival.

    Args:
        url: URL to validate

    Returns:
        The validated URL string

    Raises:
        ValueError: if URL is invalid
    """
    url = url.strip() if isinstance(url, str) else ""

    if not url or len(url) > 2048:
        raise ValueError("URL must be 1-2048 characters")

    # Basic URL validation - must start with http/https
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValueError("URL must start with http:// or https://")

    # Check for common injection patterns
    if any(char in url for char in [";", "`", "$", "{", "}"]):
        raise ValueError("URL contains potentially dangerous characters")

    return url


def _validate_output_dir(output_dir: str | None) -> str:
    """Validate output directory path.

    Args:
        output_dir: directory path to validate

    Returns:
        The validated output directory path

    Raises:
        ValueError: if path is invalid
    """
    if output_dir is None:
        return tempfile.gettempdir()

    output_dir = output_dir.strip() if isinstance(output_dir, str) else ""

    if not output_dir:
        return tempfile.gettempdir()

    if len(output_dir) > 1024:
        raise ValueError("output_dir path is too long")

    # Normalize and validate path
    try:
        path = Path(output_dir).resolve()

        # Ensure parent exists
        if not path.parent.exists():
            raise ValueError(f"parent directory does not exist: {path.parent}")

        # Check for path traversal attempts
        if ".." in str(path):
            raise ValueError("path contains parent directory references")

        return str(path)
    except Exception as exc:
        raise ValueError(f"invalid output directory: {str(exc)}")


def _check_singlefile_available() -> tuple[bool, str]:
    """Check if SingleFile CLI is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["single-file", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "SingleFile CLI found"
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    try:
        # Try alternative binary name
        result = subprocess.run(
            ["sf", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "SingleFile CLI found"
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    return False, (
        "SingleFile CLI not found. Install with: npm install -g single-file-cli"
    )


async def research_archive_page(
    url: str, output_dir: str | None = None
) -> dict[str, Any]:
    """Archive a complete webpage as a single HTML file using SingleFile.

    Creates a complete, self-contained HTML file containing the webpage and
    all its assets (CSS, JavaScript, images) embedded as base64. Useful for
    preserving web content, OSINT evidence, or offline browsing.

    Args:
        url: URL of the webpage to archive
        output_dir: directory to save the archive file (default: temp directory)

    Returns:
        Dict with:
        - url: the archived URL
        - saved_path: full path to the saved HTML file
        - file_size_bytes: size of the saved file in bytes
        - file_size_mb: size of the saved file in megabytes
        - archived_at: timestamp when the archive was created
        - title: title of the archived page (if extractable)
        - singlefile_available: bool indicating if SingleFile CLI is available
        - error: error message if archival failed (optional)
    """
    try:
        url = _validate_url(url)
        output_dir = _validate_output_dir(output_dir)
    except ValueError as exc:
        return {
            "url": url,
            "error": str(exc),
            "singlefile_available": False,
        }

    # Check if singlefile is available
    available, msg = _check_singlefile_available()
    if not available:
        return {
            "url": url,
            "error": msg,
            "singlefile_available": False,
        }

    try:
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate output filename
        filename = f"archive_{uuid.uuid4().hex}.html"
        output_path = os.path.join(output_dir, filename)

        # Build single-file command
        cmd = [
            "single-file",
            url,
            "--output-directory",
            output_dir,
            "--filename",
            filename,
        ]

        # Run single-file asynchronously
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # Allow up to 2 minutes for page loading and processing
        )

        # Check if file was created
        if not os.path.exists(output_path):
            return {
                "url": url,
                "error": f"SingleFile did not create output file. stdout: {result.stdout}, stderr: {result.stderr}",
                "singlefile_available": True,
            }

        # Get file stats
        file_stats = os.stat(output_path)
        file_size_bytes = file_stats.st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Try to extract page title from the HTML
        title = "unknown"
        try:
            with open(output_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(5000)  # Read first 5KB to find title
                title_match = re.search(r"<title[^>]*>([^<]+)</title>", content)
                if title_match:
                    title = title_match.group(1).strip()[:200]  # Cap title length
        except Exception as exc:
            logger.debug(f"Could not extract title: {exc}")

        output: dict[str, Any] = {
            "url": url,
            "saved_path": output_path,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_mb, 2),
            "title": title,
            "singlefile_available": True,
            "archived_at": str(file_stats.st_mtime),
        }

        return output

    except subprocess.TimeoutExpired:
        return {
            "url": url,
            "error": "SingleFile archival timed out after 120 seconds",
            "singlefile_available": True,
        }
    except Exception as exc:
        logger.exception("SingleFile archival failed")
        return {
            "url": url,
            "error": f"SingleFile archival error: {str(exc)}",
            "singlefile_available": True,
        }
