"""research_social_analyze — Username analysis across social media platforms.

Provides cross-platform username enumeration and profile detection using
the social-analyzer library.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

try:
    from social_analyzer import SocialAnalyzer

    _HAS_SOCIAL_ANALYZER = True
except ImportError:
    _HAS_SOCIAL_ANALYZER = False

logger = logging.getLogger("loom.tools.social_analyzer_backend")

# Constraints
MIN_USERNAME_LEN = 1
MAX_USERNAME_LEN = 128
MAX_PLATFORMS = 50


async def research_social_analyze(
    username: str,
    platforms: list[str] | None = None,
    timeout: int = 30,
    extract_emails: bool = True,
) -> dict[str, Any]:
    """Analyze username across social media platforms.

    Uses the social-analyzer library to search for a username across
    multiple social networks and return findings.

    Args:
        username: Username or account name to search for
        platforms: List of platform names to search (e.g., ['twitter', 'github', 'linkedin']).
                  If None, searches all supported platforms.
        timeout: Request timeout in seconds (1-120)
        extract_emails: Extract email addresses from profiles (default: True)

    Returns:
        Dict with keys:
        - username: Input username
        - profiles_found: Number of profiles found
        - platforms_checked: List of platforms searched
        - results: List of dicts with {platform, url, found, username_match, profile_url}
        - total_platforms: Total number of platforms checked
        - error: Error message if operation failed (optional)
    """
    # Input validation
    if not username or not isinstance(username, str):
        return {
            "username": username,
            "error": "username must be a non-empty string",
            "profiles_found": 0,
            "platforms_checked": [],
            "results": [],
            "total_platforms": 0,
        }

    username = username.strip()
    if len(username) < MIN_USERNAME_LEN or len(username) > MAX_USERNAME_LEN:
        return {
            "username": username,
            "error": f"username length must be {MIN_USERNAME_LEN}-{MAX_USERNAME_LEN} chars",
            "profiles_found": 0,
            "platforms_checked": [],
            "results": [],
            "total_platforms": 0,
        }

    # Validate timeout
    if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
        timeout = 30

    # Validate platforms list
    if platforms is not None:
        if not isinstance(platforms, list):
            return {
                "username": username,
                "error": "platforms must be a list of strings",
                "profiles_found": 0,
                "platforms_checked": [],
                "results": [],
                "total_platforms": 0,
            }
        if len(platforms) > MAX_PLATFORMS:
            return {
                "username": username,
                "error": f"platforms list max {MAX_PLATFORMS} items",
                "profiles_found": 0,
                "platforms_checked": [],
                "results": [],
                "total_platforms": 0,
            }
        # Sanitize platform names
        platforms = [str(p).strip().lower() for p in platforms if p]

    # Check if library is installed
    if not _HAS_SOCIAL_ANALYZER:
        return {
            "username": username,
            "error": "social-analyzer library not installed. Install with: pip install social-analyzer",
            "profiles_found": 0,
            "platforms_checked": [],
            "results": [],
            "total_platforms": 0,
            "library_installed": False,
        }

    try:
        # Run in executor to avoid blocking event loop
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            _run_social_analyzer,
            username,
            platforms,
            timeout,
            extract_emails,
        )
        return result

    except Exception as e:
        logger.error("social_analyze_failed username=%s: %s", username, e)
        return {
            "username": username,
            "error": f"social-analyzer execution error: {str(e)}",
            "profiles_found": 0,
            "platforms_checked": platforms or [],
            "results": [],
            "total_platforms": 0,
        }


def _run_social_analyzer(
    username: str,
    platforms: list[str] | None,
    timeout: int,
    extract_emails: bool,
) -> dict[str, Any]:
    """Run social analyzer in executor thread.

    Args:
        username: Username to analyze
        platforms: List of platform names to check
        timeout: Request timeout
        extract_emails: Extract email addresses

    Returns:
        Analysis result dict
    """
    try:
        # Initialize analyzer
        analyzer = SocialAnalyzer()

        # Build options dict
        options = {
            "username": username,
            "timeout": timeout,
            "extract_emails": extract_emails,
        }

        if platforms:
            options["platforms"] = platforms

        # Run analysis
        logger.info("social_analyze_start username=%s platforms=%s", username, len(platforms or []))

        # Call analyze method - behavior depends on library version
        # Most versions support a dict-based approach or direct method calls
        try:
            # Try newer API
            result = analyzer.analyze(options)
        except (AttributeError, TypeError):
            # Fallback to older API
            try:
                result = analyzer.run({
                    "username": username,
                    "sites": platforms or [],
                    "fast": False,
                    "output": None,
                })
            except Exception as e:
                logger.warning("social_analyzer_fallback_failed: %s", e)
                return {
                    "username": username,
                    "error": f"social-analyzer error: {str(e)}",
                    "profiles_found": 0,
                    "platforms_checked": [],
                    "results": [],
                    "total_platforms": 0,
                }

        # Parse results
        profiles_found = 0
        results = []

        # Handle different result formats
        if isinstance(result, dict):
            # Extract found profiles
            if "profiles" in result:
                profiles = result["profiles"]
                if isinstance(profiles, dict):
                    for platform, data in profiles.items():
                        if isinstance(data, dict) and data.get("found"):
                            profiles_found += 1
                            results.append({
                                "platform": platform,
                                "found": True,
                                "url": data.get("url", ""),
                                "username_match": data.get("username_match", True),
                                "profile_url": data.get("profile_url", ""),
                            })
                elif isinstance(profiles, list):
                    for profile in profiles:
                        if isinstance(profile, dict) and profile.get("found"):
                            profiles_found += 1
                            results.append({
                                "platform": profile.get("platform", "unknown"),
                                "found": True,
                                "url": profile.get("url", ""),
                                "username_match": profile.get("username_match", True),
                                "profile_url": profile.get("profile_url", ""),
                            })

        platforms_checked = platforms or []

        logger.info(
            "social_analyze_complete username=%s profiles_found=%d",
            username,
            profiles_found,
        )

        return {
            "username": username,
            "profiles_found": profiles_found,
            "platforms_checked": platforms_checked,
            "results": results,
            "total_platforms": len(platforms_checked) if platforms_checked else 150,
            "library_installed": True,
        }

    except Exception as e:
        logger.error("social_analyzer_internal_error username=%s: %s", username, e)
        return {
            "username": username,
            "error": f"social-analyzer execution error: {str(e)}",
            "profiles_found": 0,
            "platforms_checked": platforms or [],
            "results": [],
            "total_platforms": 0,
        }
