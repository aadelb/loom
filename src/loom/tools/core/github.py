"""research_github — GitHub API client for searching repos, code, issues."""

from __future__ import annotations

import json
import logging
import os
import subprocess  # noqa: F401  # module-level patch target for tests/test_tools/test_github.py
from typing import Any

import httpx
from mcp.types import TextContent
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.github")


@handle_tool_errors("research_github")
def research_github(
    kind: str,
    query: str,
    sort: str = "stars",
    order: str = "desc",
    limit: int = 20,
    language: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
) -> dict[str, Any]:
    """Search GitHub via public REST API.

    Args:
        kind: 'repo' | 'code' | 'issues'
        query: search query (GitHub syntax)
        sort: sort field (stars, forks, updated)
        order: 'asc' | 'desc'
        limit: max results (1-100)
        language: programming language filter
        owner: repository owner (user/org)
        repo: repository name

    Returns:
        Dict with results list and metadata.
    """
    # Validate
    if kind not in ("repo", "repos", "repositories", "code", "issues"):
        return {"error": f"Invalid kind: {kind}. Valid: repo, code, issues"}
    if kind in ("repos", "repositories"):
        kind = "repo"

    from loom.validators import GH_QUERY_RE

    # Check for flag injection (--flag) and shell operators (|, &, <, >)
    # These are dangerous if query is ever passed to CLI in future refactors
    if not GH_QUERY_RE.match(query) or "--" in query or any(op in query for op in ("|", "&", "<", ">")):
        return {"error": "Query contains disallowed characters (allow-list violated)"}

    limit = max(1, min(limit, 100))

    # Build GitHub search query
    q_parts = [query]
    if language:
        q_parts.append(f"language:{language}")
    if owner:
        q_parts.append(f"user:{owner}")
    if repo:
        q_parts.append(f"repo:{repo}")

    search_q = " ".join(q_parts)

    # Endpoint mapping
    endpoints = {
        "repo": "/search/repositories",
        "code": "/search/code",
        "issues": "/search/issues",
    }
    endpoint = endpoints[kind]

    # GitHub API headers
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "LoomMCP/1.0",
    }
    if token:
        # GitHub API expects "token <PAT>" format for Personal Access Tokens
        headers["Authorization"] = f"token {token}"

    # Make request
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"https://api.github.com{endpoint}",
                params={
                    "q": search_q,
                    "sort": sort,
                    "order": order,
                    "per_page": limit,
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        # Format results
        items = data.get("items", [])
        results = []

        if kind == "repo":
            for item in items:
                results.append(
                    {
                        "name": item.get("full_name"),
                        "url": item.get("html_url"),
                        "description": item.get("description"),
                        "stars": item.get("stargazers_count"),
                        "forks": item.get("forks_count"),
                        "language": item.get("language"),
                        "updated_at": item.get("updated_at"),
                    }
                )
        elif kind == "code":
            for item in items:
                results.append(
                    {
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "url": item.get("html_url"),
                        "repository": item.get("repository", {}).get("full_name"),
                        "score": item.get("score"),
                    }
                )
        elif kind == "issues":
            for item in items:
                # Safe repository name extraction from URL
                repo_url = item.get("repository_url", "")
                repo_name = repo_url.split("/")[-1] if repo_url else "unknown"
                results.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("html_url"),
                        "state": item.get("state"),
                        "created_at": item.get("created_at"),
                        "updated_at": item.get("updated_at"),
                        "repository": repo_name,
                        "user": item.get("user", {}).get("login"),
                    }
                )

        return {
            "kind": kind,
            "query": query,
            "total_count": data.get("total_count", 0),
            "results": results,
        }

    except Exception as exc:
        logger.exception("github_search_failed kind=%s", kind)
        return {
            "kind": kind,
            "query": query,
            "results": [],
            "error": str(exc),
        }


@handle_tool_errors("research_github_readme")
def research_github_readme(owner: str, repo: str) -> dict[str, Any]:
    """Fetch a repository's README content.

    Args:
        owner: GitHub user or organization (alphanumeric, dash, underscore only)
        repo: repository name (alphanumeric, dash, underscore only)

    Returns:
        Dict with ``content`` (decoded text), ``name``, ``url``.
    """
    # Validate owner and repo to prevent path traversal
    import re as _re
    if not _re.match(r"^[\w\-]{1,39}$", owner) or not _re.match(r"^[\w\.\-]{1,255}$", repo):
        return {"error": "Invalid owner or repo name format"}

    token = os.environ.get("GITHUB_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        # GitHub API expects "token <PAT>" format for Personal Access Tokens
        headers["Authorization"] = f"token {token}"

    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/readme")
            resp.raise_for_status()
            data = resp.json()

            import base64

            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
            return {
                "name": data.get("name", "README.md"),
                "url": data.get("html_url", ""),
                "content": content[:20000],
            }

    except httpx.TimeoutException as exc:
        logger.warning("github_readme_timeout %s/%s after 15s", owner, repo)
        return {"error": f"Request timeout fetching README for {owner}/{repo}"}
    except httpx.HTTPStatusError as exc:
        logger.warning("github_readme_http_error %s/%s: status=%s", owner, repo, exc.response.status_code)
        return {"error": f"HTTP {exc.response.status_code} fetching README for {owner}/{repo}"}
    except Exception as exc:
        logger.warning("github_readme_failed %s/%s: %s", owner, repo, exc)
        return {"error": str(exc)}


@handle_tool_errors("research_github_releases")
def research_github_releases(owner: str, repo: str, limit: int = 5) -> dict[str, Any]:
    """Fetch recent releases for a repository.

    Args:
        owner: GitHub user or organization (alphanumeric, dash, underscore only)
        repo: repository name (alphanumeric, dash, underscore, dot only)
        limit: max releases to return (clamped to 1-100)

    Returns:
        Dict with ``releases`` list (each has ``tag``, ``name``, ``body``, ``published_at``).
    """
    # Validate owner and repo to prevent path traversal
    import re as _re
    if not _re.match(r"^[\w\-]{1,39}$", owner) or not _re.match(r"^[\w\.\-]{1,255}$", repo):
        return {"error": "Invalid owner or repo name format"}

    limit = max(1, min(limit, 100))

    token = os.environ.get("GITHUB_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        # GitHub API expects "token <PAT>" format for Personal Access Tokens
        headers["Authorization"] = f"token {token}"

    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/releases",
                params={"per_page": limit},
            )
            resp.raise_for_status()
            data = resp.json()

        releases = [
            {
                "tag": r.get("tag_name", ""),
                "name": r.get("name", ""),
                "body": (r.get("body", "") or "")[:1000],
                "published_at": r.get("published_at"),
                "prerelease": r.get("prerelease", False),
            }
            for r in data[:limit]
        ]
        return {"owner": owner, "repo": repo, "releases": releases}

    except httpx.TimeoutException as exc:
        logger.warning("github_releases_timeout %s/%s after 15s", owner, repo)
        return {"error": f"Request timeout fetching releases for {owner}/{repo}"}
    except httpx.HTTPStatusError as exc:
        logger.warning("github_releases_http_error %s/%s: status=%s", owner, repo, exc.response.status_code)
        return {"error": f"HTTP {exc.response.status_code} fetching releases for {owner}/{repo}"}
    except Exception as exc:
        logger.warning("github_releases_failed %s/%s: %s", owner, repo, exc)
        return {"error": str(exc)}


def tool_github(
    kind: str,
    query: str,
    sort: str = "stars",
    order: str = "desc",
    limit: int = 20,
    language: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
) -> list[TextContent]:
    """MCP wrapper for research_github."""
    result = research_github(
        kind=kind,
        query=query,
        sort=sort,
        order=order,
        limit=limit,
        language=language,
        owner=owner,
        repo=repo,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
