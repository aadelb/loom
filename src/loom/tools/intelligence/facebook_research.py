"""Facebook research tools — rich OSINT via Camoufox stealth browser.

Uses Camoufox (anti-detection Firefox) to load Facebook pages with
authenticated cookies and extract structured data from rendered HTML.
Falls back to SharedModels cookie-based scraper for simpler queries.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.facebook_research")

SHARED_MODELS_BASE = os.environ.get("SHARED_MODELS_URL", "http://127.0.0.1:8000")
_TIMEOUT = 30.0
_FB_COOKIES = "/data/gcp-migration/SharedModels/facebook_session.json"


def _safe(s: str) -> str:
    return s.encode("utf-8", errors="replace").decode("utf-8")


def _load_cookie_list() -> list[dict[str, str]]:
    try:
        with open(_FB_COOKIES) as f:
            return json.load(f).get("cookies", [])
    except Exception:
        return []


async def _camoufox_fetch(url: str, wait_secs: int = 6) -> str:
    from camoufox.async_api import AsyncCamoufox

    cookies = _load_cookie_list()
    async with AsyncCamoufox(headless=True) as browser:
        page = await browser.new_page()
        for c in cookies:
            await page.context.add_cookies([{
                "name": c["name"], "value": c["value"],
                "domain": c.get("domain", ".facebook.com"),
                "path": c.get("path", "/"),
            }])
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(wait_secs)
        content = await page.content()
    return content


def _extract_posts(html: str) -> list[dict[str, Any]]:
    texts = re.findall(r'"message":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
    reactions = re.findall(r'"reaction_count":\{"count":(\d+)', html)
    comments = re.findall(r'"comment_count":\{"total_count":(\d+)', html)
    shares = re.findall(r'"share_count":\{"count":(\d+)', html)
    urls = re.findall(r'"url":"(https://www\.facebook\.com/[^"]*?/posts/[^"]*?)"', html)
    images = re.findall(r'"image":\{"uri":"(https://[^"]+)"', html)

    posts = []
    for i in range(len(texts)):
        posts.append({
            "text": _safe(texts[i].encode().decode("unicode_escape", errors="replace"))[:500],
            "reactions": int(reactions[i]) if i < len(reactions) else 0,
            "comments": int(comments[i]) if i < len(comments) else 0,
            "shares": int(shares[i]) if i < len(shares) else 0,
            "url": urls[i] if i < len(urls) else "",
            "image": images[i] if i < len(images) else "",
        })
    return posts


def _extract_page_info(html: str) -> dict[str, Any]:
    title = ""
    m = re.search(r'<title[^>]*>([^<]+)', html)
    if m:
        title = _safe(re.sub(r'\s*[|\-]\s*Facebook.*$', '', m.group(1)).strip())

    followers = 0
    m = re.search(r'"follower_count":(\d+)', html)
    if m:
        followers = int(m.group(1))

    likes = 0
    m = re.search(r'"page_likers":\{"global_likers_count":(\d+)', html)
    if m:
        likes = int(m.group(1))

    category = ""
    m = re.search(r'"category_name":"([^"]+)"', html)
    if m:
        category = _safe(m.group(1))

    about = ""
    m = re.search(r'"page_about":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
    if m:
        about = _safe(m.group(1))[:300]

    return {"name": title, "followers": followers, "likes": likes, "category": category, "about": about}


def _get_api_key() -> str:
    key = os.environ.get("SHARED_MODELS_API_KEY", "")
    if not key:
        raise RuntimeError("SHARED_MODELS_API_KEY not set")
    return key


def _headers() -> dict[str, str]:
    return {"X-API-Key": _get_api_key(), "Content-Type": "application/json"}


@handle_tool_errors("research_facebook_search")
async def research_facebook_search(
    query: str,
    search_type: str = "page",
    limit: int = 10,
) -> dict[str, Any]:
    """Search Facebook for pages, posts, or groups.

    Args:
        query: Search term (person name, company, topic)
        search_type: page, post, or group
        limit: Max results (1-50, default 10)

    Returns:
        Dict with results list containing name, url, type, snippet
    """
    limit = max(1, min(limit, 50))

    try:
        html = await _camoufox_fetch(
            f"https://www.facebook.com/search/{search_type}s/?q={query.replace(' ', '%20')}",
            wait_secs=5,
        )

        results = []
        names = re.findall(r'"name":"((?:[^"\\]|\\.)*)","__typename":"(?:Page|Group|User)"', html)
        links = re.findall(r'"url":"(https://www\.facebook\.com/[^"?]+)"', html)

        for i, name in enumerate(names[:limit]):
            results.append({
                "type": search_type,
                "name": _safe(name),
                "url": links[i] if i < len(links) else "",
            })

        if results:
            return {"query": query, "search_type": search_type, "results": results, "count": len(results), "source": "camoufox"}
    except Exception as e:
        logger.warning("camoufox_search_failed: %s", e)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{SHARED_MODELS_BASE}/facebook/search",
            headers=_headers(),
            json={"query": query, "type": search_type, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
    return {"query": query, "search_type": search_type, "results": data.get("results", []), "count": len(data.get("results", [])), "source": "sharedmodels"}


@handle_tool_errors("research_facebook_page")
async def research_facebook_page(
    page_id: str,
    include_posts: bool = True,
    post_limit: int = 10,
) -> dict[str, Any]:
    """Get Facebook page info and recent posts with full engagement data.

    Uses Camoufox stealth browser to render Facebook and extract
    post text, reactions, comments, shares, images.

    Args:
        page_id: Facebook page username (e.g. "NASA", "meta")
        include_posts: Whether to fetch posts (default True)
        post_limit: Max posts (1-20, default 10)

    Returns:
        Dict with page info (name, followers, likes, category) and posts
        with full engagement metrics (reactions, comments, shares)
    """
    post_limit = max(1, min(post_limit, 20))

    try:
        html = await _camoufox_fetch(f"https://www.facebook.com/{page_id}", wait_secs=7)
        info = _extract_page_info(html)
        posts = _extract_posts(html)[:post_limit] if include_posts else []

        return {
            "page_id": page_id,
            "source": "camoufox",
            "info": info,
            "posts": posts,
            "post_count": len(posts),
            "content_size": len(html),
        }
    except Exception as e:
        logger.warning("camoufox_page_failed: %s", e)

    return {"page_id": page_id, "source": "error", "error": str(e), "info": {}, "posts": [], "post_count": 0}


@handle_tool_errors("research_facebook_profile")
async def research_facebook_profile(
    username: str,
) -> dict[str, Any]:
    """Get detailed Facebook user profile via stealth browser.

    Args:
        username: Facebook username, profile URL slug, or user ID

    Returns:
        Dict with name, followers, friends, about, work, education
    """
    try:
        html = await _camoufox_fetch(f"https://www.facebook.com/{username}", wait_secs=7)

        name = username
        m = re.search(r'<title[^>]*>([^<|]+)', html)
        if m:
            name = _safe(re.sub(r'\s*[|\-]\s*Facebook.*$', '', m.group(1)).strip())

        friends = 0
        m = re.search(r'"friend_count":(\d+)', html)
        if m:
            friends = int(m.group(1))

        followers = 0
        m = re.search(r'"follower_count":(\d+)', html)
        if m:
            followers = int(m.group(1))

        about = ""
        m = re.search(r'"about_me":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
        if m:
            about = _safe(m.group(1))[:300]

        return {
            "username": username,
            "source": "camoufox",
            "name": name,
            "friend_count": friends,
            "followers": followers,
            "about": about,
            "content_size": len(html),
        }
    except Exception as e:
        logger.warning("camoufox_profile_failed: %s", e)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{SHARED_MODELS_BASE}/v1/social/facebook/profile-auth/{username}",
            headers=_headers(),
        )
        if resp.status_code == 200:
            return resp.json()
    return {"username": username, "error": "profile not found"}


@handle_tool_errors("research_facebook_group")
async def research_facebook_group(
    group_id: str = "",
    group_url: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Get posts from a Facebook group with full content.

    Args:
        group_id: Facebook group ID or name
        group_url: Alternatively, full group URL
        limit: Number of posts (1-20, default 20)

    Returns:
        Dict with group posts including text, engagement metrics
    """
    limit = max(1, min(limit, 20))
    target = group_id or group_url

    if target:
        try:
            url = target if target.startswith("http") else f"https://www.facebook.com/groups/{target}"
            html = await _camoufox_fetch(url, wait_secs=7)
            posts = _extract_posts(html)[:limit]

            name = ""
            m = re.search(r'<title[^>]*>([^<|]+)', html)
            if m:
                name = _safe(re.sub(r'\s*[|\-]\s*Facebook.*$', '', m.group(1)).strip())

            return {
                "group_id": group_id,
                "source": "camoufox",
                "name": name,
                "posts": posts,
                "post_count": len(posts),
            }
        except Exception as e:
            logger.warning("camoufox_group_failed: %s", e)

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
        category: Category filter (vehicles, property, electronics)
        min_price: Minimum price filter
        max_price: Maximum price filter
        limit: Max results (1-50, default 20)

    Returns:
        Dict with listings: title, price, location, image
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
    """Get engagement analytics for a Facebook page.

    Loads the page via stealth browser and analyzes post engagement
    metrics (reactions, comments, shares) across recent posts.

    Args:
        page_id: Facebook page username (e.g. "NASA")

    Returns:
        Dict with total/avg engagement, top post, follower count
    """
    try:
        html = await _camoufox_fetch(f"https://www.facebook.com/{page_id}", wait_secs=7)
        info = _extract_page_info(html)
        posts = _extract_posts(html)

        n = max(len(posts), 1)
        total_reactions = sum(p["reactions"] for p in posts)
        total_comments = sum(p["comments"] for p in posts)
        total_shares = sum(p["shares"] for p in posts)

        top = max(posts, key=lambda p: p["reactions"]) if posts else None

        return {
            "page_id": page_id,
            "source": "camoufox",
            "page_name": info.get("name", ""),
            "followers": info.get("followers", 0),
            "page_likes": info.get("likes", 0),
            "posts_analyzed": len(posts),
            "total_reactions": total_reactions,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_reactions_per_post": round(total_reactions / n, 1),
            "avg_comments_per_post": round(total_comments / n, 1),
            "avg_shares_per_post": round(total_shares / n, 1),
            "engagement_rate": round((total_reactions + total_comments + total_shares) / n, 1),
            "top_post": top,
        }
    except Exception as e:
        logger.warning("camoufox_insights_failed: %s", e)
        return {"page_id": page_id, "error": str(e)}


@handle_tool_errors("research_facebook_group_posts")
async def research_facebook_group_posts(
    group_url: str = "",
    group_id: str = "",
    limit: int = 50,
    expand_posts: bool = True,
    include_images: bool = True,
) -> dict[str, Any]:
    """Deep scrape Facebook group posts with scroll loading and full text expansion.

    Uses Camoufox stealth browser with scroll-and-collect pattern (inspired by
    jugurtha-gaci/facebook-group-posts-scraper). Expands "See more" buttons,
    deduplicates posts, and extracts images.

    Args:
        group_url: Full group URL (e.g. "https://www.facebook.com/groups/12345")
        group_id: Group ID or name (alternative to URL)
        limit: Max posts to collect (1-100, default 50). More = more scrolling.
        expand_posts: Click "See more" to get full text (default True)
        include_images: Extract image URLs from posts (default True)

    Returns:
        Dict with posts: id, text (full), image_url, reactions, comments,
        shares, author, timestamp. Also group name and member count.
    """
    if isinstance(group_url, list):
        group_url = str(group_url[0]) if group_url else ""
    if isinstance(group_id, list):
        group_id = str(group_id[0]) if group_id else ""

    target = group_url or (f"https://www.facebook.com/groups/{group_id}" if group_id else "")
    if not target:
        return {"error": "Provide group_url or group_id"}

    limit = max(1, min(limit, 100))

    try:
        from camoufox.async_api import AsyncCamoufox

        cookies = _load_cookie_list()
        camoufox_cookies = [
            {"name": c["name"], "value": c["value"], "domain": ".facebook.com", "path": "/"}
            for c in cookies
        ]

        async with AsyncCamoufox(headless=True) as browser:
            context = await browser.new_context()
            if camoufox_cookies:
                await context.add_cookies(camoufox_cookies)
            page = await context.new_page()

            await page.goto(target, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            group_name = ""
            try:
                title_el = await page.query_selector("h1")
                if title_el:
                    group_name = await title_el.inner_text()
            except Exception:
                pass

            collected_posts: list[dict[str, Any]] = []
            seen_ids: set[str] = set()
            scroll_attempts = 0
            max_scrolls = min(limit // 3 + 2, 30)

            while len(collected_posts) < limit and scroll_attempts < max_scrolls:
                if expand_posts:
                    see_more_buttons = await page.query_selector_all(
                        'div[role="button"]:has-text("See more"), '
                        'div[role="button"]:has-text("See More"), '
                        'div[role="button"]:has-text("Voir plus")'
                    )
                    for btn in see_more_buttons[:5]:
                        try:
                            await btn.click()
                            await asyncio.sleep(0.3)
                        except Exception:
                            pass

                feed_items = await page.query_selector_all('div[role="feed"] > div')
                for item in feed_items:
                    try:
                        post_data: dict[str, Any] = {}

                        msg_div = await item.query_selector('div[data-ad-preview="message"]')
                        if msg_div:
                            post_text = await msg_div.inner_text()
                            post_id = await msg_div.get_attribute("id") or ""
                        else:
                            text_divs = await item.query_selector_all('div[dir="auto"]')
                            texts = []
                            for td in text_divs[:3]:
                                t = await td.inner_text()
                                if t and len(t) > 20:
                                    texts.append(t)
                            post_text = "\n".join(texts)
                            post_id = str(hash(post_text[:100]))

                        if not post_text or post_id in seen_ids:
                            continue

                        seen_ids.add(post_id)
                        post_data["id"] = post_id
                        post_data["text"] = _safe(post_text[:2000])

                        if include_images:
                            img_els = await item.query_selector_all('img[src*="scontent"]')
                            images = []
                            for img in img_els[:3]:
                                src = await img.get_attribute("src")
                                if src and "emoji" not in src:
                                    images.append(src)
                            if images:
                                post_data["images"] = images

                        author_el = await item.query_selector('a[role="link"] strong, h3 a')
                        if author_el:
                            post_data["author"] = await author_el.inner_text()

                        reaction_spans = await item.query_selector_all('span[aria-label*="reaction"], span[aria-label*="like"]')
                        for rs in reaction_spans[:1]:
                            label = await rs.get_attribute("aria-label") or ""
                            nums = re.findall(r"(\d+)", label)
                            if nums:
                                post_data["reactions"] = int(nums[0])

                        collected_posts.append(post_data)
                    except Exception:
                        continue

                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(2)
                scroll_attempts += 1

            await context.close()

        return {
            "group_url": target,
            "group_name": group_name,
            "source": "camoufox_deep_scrape",
            "posts": collected_posts[:limit],
            "post_count": len(collected_posts),
            "scrolls_performed": scroll_attempts,
        }

    except ImportError:
        return {"error": "camoufox not installed", "source": "none"}
    except Exception as e:
        logger.warning("group_posts_deep_scrape_failed: %s", e)
        return {"group_url": target, "error": str(e), "source": "camoufox"}
