"""Social Analyzer integration for cross-platform username reconnaissance.

Searches for a username across 300+ social media platforms and returns
presence, URLs, and metadata for each discovered profile.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.social_analyzer_backend")


@handle_tool_errors("research_social_analyze")
async def research_social_analyze(
    username: str,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Search for a username across social media platforms.

    Uses the social-analyzer CLI tool to perform cross-platform username
    reconnaissance. Searches across 300+ platforms including social media,
    forums, code repositories, job sites, and more.

    Args:
        username: Username to search for
        platforms: Optional list of platform names to search (e.g., ['twitter', 'github'])
                   If empty/None, searches all platforms

    Returns:
        Dict with keys:
        - username: The searched username
        - profiles_found: List of discovered profiles [{platform, url, exists, ...}]
        - total_found: Count of profiles found
        - error: Error message if any (instead of profiles on failure)
    """

    result: dict[str, Any] = {
        "username": username,
        "total_found": 0,
        "profiles_found": [],
    }

    # Try library import first
    try:
        import importlib.util

        spec = importlib.util.find_spec("social_analyzer")
        if spec is not None:
            return await _search_with_library(username, platforms, result)
    except (ImportError, ValueError):
        logger.debug("social_analyzer library not installed, falling back to CLI")

    # Fall back to CLI
    return await _search_with_cli(username, platforms, result)


async def _search_with_library(
    username: str,
    platforms: list[str] | None,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Search using social-analyzer Python library if available."""
    try:
        from social_analyzer import analyze

        # Prepare arguments
        kwargs = {
            "username": username,
            "output": "json",
            "timeout": 10,
        }

        if platforms:
            kwargs["platforms"] = platforms

        # Run analysis
        response = await analyze(**kwargs)

        # Parse response
        if isinstance(response, dict):
            found = response.get("found", [])
            if isinstance(found, list):
                result["profiles_found"] = found
                result["total_found"] = len(found)
                logger.info("social_analyze_success: found %d profiles for %s", len(found), username)
            else:
                logger.debug("unexpected social_analyzer response format for found: %s", type(found))
        else:
            logger.debug("unexpected social_analyzer response type: %s", type(response))

    except Exception as e:
        logger.error("social_analyzer_library_error: %s", e)
        result["error"] = f"social_analyzer library failed: {e!s}"

    return result


async def _search_with_cli(
    username: str,
    platforms: list[str] | None,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Search using social-analyzer CLI tool."""
    try:
        # Build CLI command
        cmd = [
            "social-analyzer",
            "--username",
            username,
            "--output",
            "json",
        ]

        # Add platforms if specified
        if platforms:
            cmd.extend(["--platforms", ",".join(platforms)])

        # Run with timeout
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            logger.error("social_analyzer_cli_timeout: exceeded 60 seconds")
            result["error"] = "social-analyzer CLI timeout after 60 seconds"
            return result

        # Check return code
        if process.returncode != 0:
            logger.error("social_analyzer_cli_error: exit code %d", process.returncode)
            if stderr:
                logger.error("social_analyzer_stderr: %s", stderr.decode("utf-8", errors="ignore"))
            result["error"] = f"social-analyzer CLI failed with exit code {process.returncode}"
            return result

        # Parse JSON output
        try:
            output_str = stdout.decode("utf-8")
            response = json.loads(output_str)

            # Extract profiles
            profiles = []
            if isinstance(response, dict):
                # Handle various response formats
                if "results" in response:
                    results = response["results"]
                    if isinstance(results, dict):
                        for platform, data in results.items():
                            if isinstance(data, dict) and data.get("found"):
                                profiles.append(
                                    {
                                        "platform": platform,
                                        "url": data.get("url"),
                                        "exists": data.get("found", False),
                                        "is_similar": data.get("is_similar", False),
                                        "accuracy": data.get("accuracy"),
                                    }
                                )
                elif "found_profiles" in response:
                    profiles = response["found_profiles"]

            result["profiles_found"] = profiles
            result["total_found"] = len(profiles)
            logger.info("social_analyze_success: found %d profiles for %s via CLI", len(profiles), username)

        except json.JSONDecodeError as e:
            logger.error("social_analyzer_json_parse_error: %s", e)
            result["error"] = f"Failed to parse social-analyzer JSON output: {e!s}"

    except FileNotFoundError:
        logger.error("social_analyzer_cli_not_found")
        result["error"] = "social-analyzer CLI tool not found in PATH"
    except Exception as e:
        logger.error("social_analyzer_cli_error: %s", e)
        result["error"] = f"social-analyzer CLI failed: {e!s}"

    return result
