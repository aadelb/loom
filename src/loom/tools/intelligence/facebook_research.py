"""Facebook research tools via SharedModels social API.

Provides OSINT and research capabilities for Facebook pages, profiles,
groups, and marketplace through the SharedModels service on port 8000.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.facebook_research")

SHARED_MODELS_BASE = os.environ.get("SHARED_MODELS_URL", "http://127.0.0.1:8000")
_TIMEOUT = 30.0


def _get_api_key() -> str:
    key = os.environ.get("SHARED_MODELS_API_KEY", "")
    if not key:
        raise RuntimeError(
            "SHARED_MODELS_API_KEY not set. Register at "
            f"POST {SHARED_MODELS_BASE}/admin/projects/register"
        )
    return key


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": _get_api_key(),
        "Content-Type": "application/json",
    }


@handle_tool_errors("research_facebook_search")
async def research_facebook_search(
    query: str,
    search_type: str = "page",
    limit: int = 10,
) -> dict[str, Any]:
    """Search Facebook for pages, people, groups, or posts.

    Args:
        query: Search term (person name, company, topic)
        search_type: Type of search — page, post, group
        limit: Max results (1-50, default 10)

    Returns:
        Dict with results list, each containing id, name, url, type, snippet
    """
    limit = max(1, min(limit, 50))

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{SHARED_MODELS_BASE}/facebook/search",
            headers=_headers(),
            json={"query": query, "type": search_type, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "query": query,
        "search_type": search_type,
        "results": data.get("results", data),
        "count": len(data.get("results", data)) if isinstance(data, (list, dict)) else 0,
    }


@handle_tool_errors("research_facebook_page")
async def research_facebook_page(
    page_id: str,
    include_posts: bool = True,
    post_limit: int = 10,
) -> dict[str, Any]:
    """Get Facebook page info and recent posts.

    Args:
        page_id: Facebook page ID or username (e.g. "meta", "20531316728")
        include_posts: Whether to fetch recent posts (default True)
        post_limit: Number of posts to fetch (1-100, default 10)

    Returns:
        Dict with page info (name, category, followers, about) and posts list
    """
    post_limit = max(1, min(post_limit, 100))

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        page_info: dict[str, Any] = {"page_id": page_id}
        try:
            info_resp = await client.get(
                f"{SHARED_MODELS_BASE}/v1/social/facebook/page/{page_id}/info",
                headers=_headers(),
            )
            if info_resp.status_code == 200:
                page_info = info_resp.json()
        except Exception:
            pass

        if "name" not in page_info:
            try:
                search_resp = await client.post(
                    f"{SHARED_MODELS_BASE}/facebook/search",
                    headers=_headers(),
                    json={"query": page_id, "type": "page", "limit": 1},
                )
                if search_resp.status_code == 200:
                    results = search_resp.json().get("results", [])
                    if results:
                        page_info = results[0] if isinstance(results[0], dict) else {"name": str(results[0])}
                        page_info["page_id"] = page_id
            except Exception:
                pass

        posts: list[Any] = []
        if include_posts:
            try:
                posts_resp = await client.get(
                    f"{SHARED_MODELS_BASE}/facebook/page/{page_id}/posts",
                    headers=_headers(),
                    params={"limit": post_limit},
                )
                if posts_resp.status_code == 200:
                    posts_data = posts_resp.json()
                    posts = posts_data.get("posts", posts_data) if isinstance(posts_data, dict) else posts_data
            except Exception:
                pass

    return {
        "page_id": page_id,
        "info": page_info,
        "posts": posts if isinstance(posts, list) else [],
        "post_count": len(posts) if isinstance(posts, list) else 0,
    }


@handle_tool_errors("research_facebook_profile")
async def research_facebook_profile(
    username: str,
) -> dict[str, Any]:
    """Research a Facebook user profile (authenticated session required).

    Args:
        username: Facebook username or profile URL slug

    Returns:
        Dict with profile data: name, bio, location, work, education, friends_count
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{SHARED_MODELS_BASE}/v1/social/facebook/profile-auth/{username}",
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


@handle_tool_errors("research_facebook_group")
async def research_facebook_group(
    group_id: str = "",
    group_url: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Get posts from a Facebook group.

    Args:
        group_id: Facebook group ID
        group_url: Alternatively, full group URL
        limit: Number of posts to fetch (1-100, default 20)

    Returns:
        Dict with group info and recent posts
    """
    limit = max(1, min(limit, 100))

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{SHARED_MODELS_BASE}/v1/social/facebook/group-posts",
            headers=_headers(),
            json={"group_id": group_id, "group_url": group_url, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


@handle_tool_errors("research_facebook_marketplace")
async def research_facebook_marketplace(
    query: str = "",
    location: str = "",
    category: str = "",
    min_price: float = 0,
    max_price: float = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Search Facebook Marketplace listings.

    Args:
        query: Search term (e.g. "iPhone 15", "apartment rent")
        location: City or area (e.g. "Dubai", "Abu Dhabi")
        category: Category filter (vehicles, property, electronics, etc.)
        min_price: Minimum price filter (0 = no min)
        max_price: Maximum price filter (0 = no max)
        limit: Max results (1-50, default 20)

    Returns:
        Dict with listings: title, price, location, seller, image_url, listing_url
    """
    limit = max(1, min(limit, 50))
    body: dict[str, Any] = {"query": query, "limit": limit}
    if location:
        body["location"] = location
    if category:
        body["category"] = category
    if min_price > 0:
        body["min_price"] = min_price
    if max_price > 0:
        body["max_price"] = max_price

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{SHARED_MODELS_BASE}/v1/social/facebook/marketplace",
            headers=_headers(),
            json=body,
        )
        resp.raise_for_status()
        return resp.json()


@handle_tool_errors("research_facebook_page_insights")
async def research_facebook_page_insights(
    page_id: str,
) -> dict[str, Any]:
    """Get analytics/insights for a Facebook page.

    Falls back to page posts analysis if Graph API token not configured.

    Args:
        page_id: Facebook page ID

    Returns:
        Dict with engagement metrics, reach, impressions, follower growth
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{SHARED_MODELS_BASE}/v1/social/facebook/page/{page_id}/insights",
                headers=_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

        posts_resp = await client.get(
            f"{SHARED_MODELS_BASE}/facebook/page/{page_id}/posts",
            headers=_headers(),
            params={"limit": 20},
        )
        posts_data = posts_resp.json() if posts_resp.status_code == 200 else {}
        posts = posts_data.get("posts", []) if isinstance(posts_data, dict) else []

        total_likes = sum(p.get("likes", 0) for p in posts if isinstance(p, dict))
        total_comments = sum(p.get("comments", 0) for p in posts if isinstance(p, dict))
        total_shares = sum(p.get("shares", 0) for p in posts if isinstance(p, dict))

        return {
            "page_id": page_id,
            "source": "post_analysis",
            "posts_analyzed": len(posts),
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_engagement": (total_likes + total_comments + total_shares) / max(len(posts), 1),
            "note": "Derived from recent posts (Graph API token not configured)",
        }
