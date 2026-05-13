"""Save research results to Joplin notes.

Tools:
- research_save_note: Create a note in Joplin
- research_list_notebooks: List all Joplin notebooks
"""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.joplin")

# Default Joplin URL (Hetzner instance)
DEFAULT_JOPLIN_URL = "http://65.108.199.151:3100"

# Constraints
MAX_TITLE_CHARS = 500
MAX_BODY_CHARS = 100000
JOPLIN_REQUEST_TIMEOUT = 30

# Notebook ID validation regex (UUID-like)
_NOTEBOOK_ID_REGEX = re.compile(r"^[a-fA-F0-9]{32}$")


def _get_joplin_url() -> str:
    """Get Joplin URL from environment or use default."""
    return os.environ.get("JOPLIN_URL", DEFAULT_JOPLIN_URL)


def _get_joplin_token() -> str | None:
    """Get Joplin API token from environment."""
    return os.environ.get("JOPLIN_TOKEN")


@handle_tool_errors("research_save_note")
async def research_save_note(
    title: str,
    body: str,
    notebook: str | None = None,
) -> dict[str, Any]:
    """Create a note in Joplin via REST API.

    Args:
        title: note title (max 500 chars)
        body: note content/body (max 100000 chars)
        notebook: optional notebook ID to save note in

    Returns:
        Dict with ``status``, ``note_id``, and ``title`` on success,
        or ``error`` on failure.
    """
    # Validate inputs
    if not title or len(title) > MAX_TITLE_CHARS:
        return {
            "error": f"title required and must be <= {MAX_TITLE_CHARS} chars",
            "status": "failed",
        }

    if not body or len(body) > MAX_BODY_CHARS:
        return {
            "error": f"body required and must be <= {MAX_BODY_CHARS} chars",
            "status": "failed",
        }

    # Get credentials
    joplin_url = _get_joplin_url()
    joplin_token = _get_joplin_token()

    if not joplin_token:
        return {
            "error": "missing JOPLIN_TOKEN environment variable",
            "status": "failed",
        }

    # Validate notebook ID if provided
    if notebook is not None and not _NOTEBOOK_ID_REGEX.match(notebook):
        return {
            "error": "invalid notebook ID format (expected 32-char hex UUID)",
            "status": "failed",
        }

    # Build request
    api_url = f"{joplin_url}/api/notes"
    headers = {"X-API-Token": joplin_token}

    request_body = {
        "title": title,
        "body": body,
    }

    if notebook:
        request_body["parent_id"] = notebook

    try:
        async with httpx.AsyncClient(timeout=JOPLIN_REQUEST_TIMEOUT) as client:
            response = await client.post(api_url, json=request_body, headers=headers)
            response.raise_for_status()

            try:
                result = response.json()
            except ValueError:
                return {
                    "error": "Joplin API returned invalid JSON response",
                    "status": "failed",
                }
            note_id = result.get("id", "")

            if not note_id:
                return {
                    "error": "Joplin API returned no note ID",
                    "status": "failed",
                }

            logger.info("joplin_note_created note_id=%s title=%s", note_id, title[:50])

            return {
                "status": "saved",
                "note_id": note_id,
                "title": title,
            }

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            error_msg = "Joplin API authentication failed (invalid token)"
        elif exc.response.status_code == 404:
            error_msg = "Joplin notebook not found"
        else:
            error_msg = f"Joplin API error: {exc.response.status_code}"

        logger.warning("joplin_save_failed error=%s", error_msg)
        return {
            "error": error_msg,
            "status": "failed",
        }

    except httpx.ConnectError:
        error_msg = f"Could not connect to Joplin at {joplin_url}"
        logger.warning("joplin_connect_failed url=%s", joplin_url)
        return {
            "error": error_msg,
            "status": "failed",
        }

    except httpx.TimeoutException:
        error_msg = f"Joplin request timeout ({JOPLIN_REQUEST_TIMEOUT}s)"
        logger.warning("joplin_timeout")
        return {
            "error": error_msg,
            "status": "failed",
        }

    except Exception as exc:
        error_msg = f"unexpected error: {exc!s}"
        logger.error("joplin_unexpected_error: %s", exc)
        return {
            "error": error_msg,
            "status": "failed",
        }


@handle_tool_errors("research_list_notebooks")
async def research_list_notebooks() -> dict[str, Any]:
    """List all Joplin notebooks.

    Returns:
        Dict with ``notebooks`` list (each with ``id`` and ``title``),
        or ``error`` on failure.
    """
    # Get credentials
    joplin_url = _get_joplin_url()
    joplin_token = _get_joplin_token()

    if not joplin_token:
        return {
            "error": "missing JOPLIN_TOKEN environment variable",
            "notebooks": [],
        }

    # Build request
    api_url = f"{joplin_url}/api/folders"
    headers = {"X-API-Token": joplin_token}

    try:
        async with httpx.AsyncClient(timeout=JOPLIN_REQUEST_TIMEOUT) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()

            try:
                result = response.json()
            except ValueError:
                return {
                    "error": "Joplin API returned invalid JSON response",
                    "notebooks": [],
                }
            notebooks = []

            for folder in result.get("items", []):
                notebook = {
                    "id": folder.get("id", ""),
                    "title": folder.get("title", ""),
                }
                if notebook["id"]:  # Only include if ID is present
                    notebooks.append(notebook)

            logger.info("joplin_notebooks_listed count=%d", len(notebooks))

            return {
                "notebooks": notebooks,
                "total": len(notebooks),
            }

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            error_msg = "Joplin API authentication failed (invalid token)"
        else:
            error_msg = f"Joplin API error: {exc.response.status_code}"

        logger.warning("joplin_list_failed error=%s", error_msg)
        return {
            "error": error_msg,
            "notebooks": [],
        }

    except httpx.ConnectError:
        error_msg = f"Could not connect to Joplin at {joplin_url}"
        logger.warning("joplin_connect_failed url=%s", joplin_url)
        return {
            "error": error_msg,
            "notebooks": [],
        }

    except httpx.TimeoutException:
        error_msg = f"Joplin request timeout ({JOPLIN_REQUEST_TIMEOUT}s)"
        logger.warning("joplin_timeout")
        return {
            "error": error_msg,
            "notebooks": [],
        }

    except Exception as exc:
        error_msg = f"unexpected error: {exc!s}"
        logger.error("joplin_unexpected_error: %s", exc)
        return {
            "error": error_msg,
            "notebooks": [],
        }
