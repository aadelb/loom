"""X/Twitter research tools — GraphQL internal API + Camoufox fallback.

Primary: Direct HTTP to X GraphQL API (profiles, user info, tweet details).
Fallback: Camoufox stealth browser for search and timeline (requires
x-client-transaction-id which is generated from JS).

Auth: auth_token + ct0 cookies from browser session.
Endpoint IDs auto-discovered from x.com JS bundle on first use.

Env vars:
  X_AUTH_TOKEN     — auth_token cookie value
  X_CT0            — ct0 CSRF cookie value
  X_SESSION_FILE   — path to session JSON (default: x_session.json)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.parse
from typing import Any

import requests

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.x_research")

_BEARER = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

_GRAPHQL_BASE = "https://x.com/i/api/graphql"

_DEFAULT_FEATURES = {
    "hidden_profile_subscriptions_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
}

_ENDPOINT_CACHE: dict[str, str] = {}


def _load_cookies() -> dict[str, str]:
    """Load X session cookies from env vars or session file."""
    auth_token = os.environ.get("X_AUTH_TOKEN", "")
    ct0 = os.environ.get("X_CT0", "")

    if auth_token and ct0:
        return {"auth_token": auth_token, "ct0": ct0}

    session_file = os.environ.get(
        "X_SESSION_FILE",
        os.path.expanduser("~/.loom/x_session.json"),
    )
    for path in [session_file, "x_session.json", "/tmp/x_session.json"]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                cookies = {c["name"]: c["value"] for c in data.get("cookies", [])}
                if cookies.get("auth_token") and cookies.get("ct0"):
                    return cookies
            except Exception:
                pass

    return {}


def _headers(cookies: dict[str, str]) -> dict[str, str]:
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    return {
        "Authorization": f"Bearer {_BEARER}",
        "X-Csrf-Token": cookies.get("ct0", ""),
        "Cookie": cookie_str,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "X-Twitter-Active-User": "yes",
        "X-Twitter-Auth-Type": "OAuth2Session",
        "X-Twitter-Client-Language": "en",
    }


def _discover_endpoints() -> dict[str, str]:
    """Fetch current GraphQL endpoint IDs from X.com JS bundle."""
    if _ENDPOINT_CACHE:
        return _ENDPOINT_CACHE

    try:
        resp = requests.get(
            "https://x.com",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        js_urls = re.findall(
            r'"(https://abs\.twimg\.com/responsive-web/client-web(?:-legacy)?/main\.[a-z0-9]+\.js)"',
            resp.text,
        )
        if not js_urls:
            return {}

        js_resp = requests.get(js_urls[0], timeout=30)
        js_text = js_resp.text

        operations = [
            "SearchTimeline",
            "UserByScreenName",
            "UserByRestId",
            "UserTweets",
            "TweetDetail",
            "Followers",
            "Following",
        ]
        for op in operations:
            match = re.search(
                rf'queryId:"([a-zA-Z0-9_-]+)",operationName:"{op}"', js_text
            )
            if match:
                _ENDPOINT_CACHE[op] = match.group(1)

    except Exception as e:
        logger.warning("Failed to discover X endpoints: %s", e)

    return _ENDPOINT_CACHE


def _graphql_get(
    operation: str,
    variables: dict,
    features: dict | None = None,
) -> dict | None:
    """Make a GraphQL GET request to X API."""
    cookies = _load_cookies()
    if not cookies:
        return None

    endpoints = _discover_endpoints()
    endpoint_id = endpoints.get(operation)
    if not endpoint_id:
        if operation == "UserByRestId":
            endpoint_id = "xf3jd90KKBCUxdlI_tNHZw"
        else:
            return None

    feat = features or _DEFAULT_FEATURES
    url = (
        f"{_GRAPHQL_BASE}/{endpoint_id}/{operation}"
        f"?variables={urllib.parse.quote(json.dumps(variables))}"
        f"&features={urllib.parse.quote(json.dumps(feat))}"
    )

    try:
        resp = requests.get(url, headers=_headers(cookies), timeout=20)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("X GraphQL %s returned %d", operation, resp.status_code)
    except Exception as e:
        logger.warning("X GraphQL request failed: %s", e)
    return None


def _extract_user(data: dict) -> dict[str, Any]:
    """Extract user profile from GraphQL response."""
    result = data.get("data", {}).get("user", {}).get("result", {})
    legacy = result.get("legacy", {})
    return {
        "id": result.get("rest_id", ""),
        "username": legacy.get("screen_name", ""),
        "name": legacy.get("name", ""),
        "bio": legacy.get("description", ""),
        "followers": legacy.get("followers_count", 0),
        "following": legacy.get("friends_count", 0),
        "tweets_count": legacy.get("statuses_count", 0),
        "likes_count": legacy.get("favourites_count", 0),
        "verified": result.get("is_blue_verified", False),
        "created_at": legacy.get("created_at", ""),
        "location": legacy.get("location", ""),
        "website": legacy.get("entities", {}).get("url", {}).get("urls", [{}])[0].get("expanded_url", "") if legacy.get("entities", {}).get("url") else "",
        "profile_image": legacy.get("profile_image_url_https", "").replace("_normal", "_400x400"),
        "profile_banner": legacy.get("profile_banner_url", ""),
        "profile_url": f"https://x.com/{legacy.get('screen_name', '')}",
    }


def _extract_tweet(result: dict) -> dict[str, Any]:
    """Extract tweet data from GraphQL result."""
    if result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet", result)
    legacy = result.get("legacy", {})
    user_legacy = (
        result.get("core", {})
        .get("user_results", {})
        .get("result", {})
        .get("legacy", {})
    )
    return {
        "id": result.get("rest_id", legacy.get("id_str", "")),
        "text": legacy.get("full_text", ""),
        "author": user_legacy.get("screen_name", ""),
        "author_name": user_legacy.get("name", ""),
        "likes": legacy.get("favorite_count", 0),
        "retweets": legacy.get("retweet_count", 0),
        "replies": legacy.get("reply_count", 0),
        "quotes": legacy.get("quote_count", 0),
        "views": result.get("views", {}).get("count", ""),
        "created_at": legacy.get("created_at", ""),
        "url": f"https://x.com/{user_legacy.get('screen_name', '')}/status/{result.get('rest_id', '')}",
        "is_retweet": legacy.get("retweeted_status_result") is not None,
        "media": [
            m.get("media_url_https", "")
            for m in legacy.get("entities", {}).get("media", [])
        ],
    }


async def _camoufox_search(query: str, limit: int = 10) -> list[dict]:
    """Search X via Camoufox stealth browser (fallback for GraphQL 404)."""
    try:
        from camoufox.async_api import AsyncCamoufox

        cookies_dict = _load_cookies()
        camoufox_cookies = [
            {"name": k, "value": v, "domain": ".x.com", "path": "/"}
            for k, v in cookies_dict.items()
        ]

        async with AsyncCamoufox(headless=True) as browser:
            context = await browser.new_context()
            await context.add_cookies(camoufox_cookies)
            page = await context.new_page()

            search_url = f"https://x.com/search?q={urllib.parse.quote(query)}&src=typed_query&f=live"
            await page.goto(search_url, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            html = await page.content()
            await context.close()

        tweets = []
        tweet_blocks = re.findall(
            r'<article[^>]*data-testid="tweet"[^>]*>(.*?)</article>',
            html,
            re.DOTALL,
        )
        for block in tweet_blocks[:limit]:
            text_match = re.search(
                r'data-testid="tweetText"[^>]*>(.*?)</div>', block, re.DOTALL
            )
            user_match = re.search(r'href="/([^/?"]+)"', block)
            text = re.sub(r"<[^>]+>", "", text_match.group(1)) if text_match else ""
            username = user_match.group(1) if user_match else ""
            if text and username:
                tweets.append({
                    "text": text[:500],
                    "author": username,
                    "url": f"https://x.com/{username}",
                })

        return tweets
    except Exception as e:
        logger.warning("Camoufox X search failed: %s", e)
        return []


@handle_tool_errors("research_x_profile")
async def research_x_profile(
    username: str,
) -> dict[str, Any]:
    """Get X/Twitter user profile with stats.

    Args:
        username: X handle without @ (e.g. "elonmusk", "AhmedAdel_Bakr")

    Returns:
        Dict with name, bio, followers, following, tweets_count, verified,
        location, website, profile_image, profile_url
    """
    if isinstance(username, list):
        username = str(username[0]) if username else ""
    if isinstance(username, dict):
        username = str(username)
    username = username.lstrip("@").strip()

    data = await asyncio.to_thread(
        _graphql_get,
        "UserByScreenName",
        {"screen_name": username, "withSafetyModeUserFields": True},
    )
    if data and data.get("data", {}).get("user"):
        profile = _extract_user(data)
        profile["source"] = "x_graphql"
        return profile

    data2 = await asyncio.to_thread(
        _graphql_get,
        "UserByRestId",
        {"userId": username, "withSafetyModeUserFields": True},
    )
    if data2 and data2.get("data", {}).get("user"):
        profile = _extract_user(data2)
        profile["source"] = "x_graphql_restid"
        return profile

    return {
        "username": username,
        "error": "X session expired or user not found. Refresh cookies.",
        "source": "none",
    }


@handle_tool_errors("research_x_search")
async def research_x_search(
    query: str,
    limit: int = 10,
    sort: str = "Latest",
) -> dict[str, Any]:
    """Search X/Twitter for tweets by keyword.

    Args:
        query: Search query (supports X search operators)
        limit: Max results (1-50, default 10)
        sort: "Latest" or "Top" (default "Latest")

    Returns:
        Dict with tweets: text, author, likes, retweets, url
    """
    if isinstance(query, list):
        query = " ".join(str(x) for x in query)
    if isinstance(query, dict):
        query = str(query)

    data = await asyncio.to_thread(
        _graphql_get,
        "SearchTimeline",
        {
            "rawQuery": query,
            "count": min(limit, 50),
            "querySource": "typed_query",
            "product": sort,
        },
    )

    if data and "data" in data:
        tweets = []
        instructions = (
            data.get("data", {})
            .get("search_by_raw_query", {})
            .get("search_timeline", {})
            .get("timeline", {})
            .get("instructions", [])
        )
        for inst in instructions:
            for entry in inst.get("entries", []):
                result = (
                    entry.get("content", {})
                    .get("itemContent", {})
                    .get("tweet_results", {})
                    .get("result", {})
                )
                if result:
                    tweet = _extract_tweet(result)
                    if tweet.get("text"):
                        tweets.append(tweet)
        return {
            "query": query,
            "sort": sort,
            "source": "x_graphql",
            "tweets": tweets[:limit],
            "count": len(tweets),
        }

    camoufox_tweets = await _camoufox_search(query, limit)
    if camoufox_tweets:
        return {
            "query": query,
            "sort": sort,
            "source": "camoufox",
            "tweets": camoufox_tweets,
            "count": len(camoufox_tweets),
        }

    return {
        "query": query,
        "sort": sort,
        "source": "none",
        "tweets": [],
        "count": 0,
        "error": "Search requires x-client-transaction-id. Refresh browser session or use Camoufox.",
    }


@handle_tool_errors("research_x_tweet")
async def research_x_tweet(
    tweet_id: str,
) -> dict[str, Any]:
    """Get a specific tweet with engagement stats and replies.

    Args:
        tweet_id: Tweet ID or full URL (e.g. "1234567890" or "https://x.com/user/status/1234567890")

    Returns:
        Dict with text, author, likes, retweets, replies, media, url
    """
    if isinstance(tweet_id, list):
        tweet_id = str(tweet_id[0]) if tweet_id else ""
    if isinstance(tweet_id, dict):
        tweet_id = str(tweet_id)

    match = re.search(r"/status/(\d+)", tweet_id)
    if match:
        tweet_id = match.group(1)
    tweet_id = tweet_id.strip()

    data = await asyncio.to_thread(
        _graphql_get,
        "TweetDetail",
        {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "rankingMode": "Relevance",
            "includePromotedContent": False,
            "withCommunity": True,
        },
    )

    if data and "data" in data:
        instructions = (
            data.get("data", {})
            .get("threaded_conversation_with_injections_v2", {})
            .get("instructions", [])
        )
        for inst in instructions:
            for entry in inst.get("entries", []):
                result = (
                    entry.get("content", {})
                    .get("itemContent", {})
                    .get("tweet_results", {})
                    .get("result", {})
                )
                if result and result.get("rest_id") == tweet_id:
                    tweet = _extract_tweet(result)
                    tweet["source"] = "x_graphql"
                    return tweet

    return {
        "tweet_id": tweet_id,
        "error": "Tweet not found or session expired",
        "source": "none",
    }


@handle_tool_errors("research_x_timeline")
async def research_x_timeline(
    username: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Get recent tweets from a user's timeline.

    Args:
        username: X handle without @ (e.g. "elonmusk")
        limit: Max tweets (1-50, default 10)

    Returns:
        Dict with user info and recent tweets
    """
    if isinstance(username, list):
        username = str(username[0]) if username else ""
    if isinstance(username, dict):
        username = str(username)
    username = username.lstrip("@").strip()

    profile_data = await asyncio.to_thread(
        _graphql_get,
        "UserByScreenName",
        {"screen_name": username, "withSafetyModeUserFields": True},
    )
    if not profile_data or not profile_data.get("data", {}).get("user"):
        return {"username": username, "error": "User not found", "source": "none"}

    user_id = (
        profile_data.get("data", {})
        .get("user", {})
        .get("result", {})
        .get("rest_id", "")
    )
    profile = _extract_user(profile_data)

    data = await asyncio.to_thread(
        _graphql_get,
        "UserTweets",
        {"userId": user_id, "count": min(limit, 50), "includePromotedContent": False},
    )

    tweets = []
    if data and "data" in data:
        instructions = (
            data.get("data", {})
            .get("user", {})
            .get("result", {})
            .get("timeline_v2", {})
            .get("timeline", {})
            .get("instructions", [])
        )
        for inst in instructions:
            for entry in inst.get("entries", []):
                result = (
                    entry.get("content", {})
                    .get("itemContent", {})
                    .get("tweet_results", {})
                    .get("result", {})
                )
                if result:
                    tweet = _extract_tweet(result)
                    if tweet.get("text"):
                        tweets.append(tweet)

    return {
        "username": username,
        "profile": profile,
        "source": "x_graphql",
        "tweets": tweets[:limit],
        "count": len(tweets),
    }


@handle_tool_errors("research_x_followers")
async def research_x_followers(
    username: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Get followers of an X/Twitter user.

    Args:
        username: X handle without @ (e.g. "elonmusk")
        limit: Max followers (1-100, default 20)

    Returns:
        Dict with follower profiles: name, username, bio, followers
    """
    if isinstance(username, list):
        username = str(username[0]) if username else ""
    if isinstance(username, dict):
        username = str(username)
    username = username.lstrip("@").strip()

    profile_data = await asyncio.to_thread(
        _graphql_get,
        "UserByScreenName",
        {"screen_name": username, "withSafetyModeUserFields": True},
    )
    if not profile_data or not profile_data.get("data", {}).get("user"):
        return {"username": username, "error": "User not found", "source": "none"}

    user_id = (
        profile_data.get("data", {})
        .get("user", {})
        .get("result", {})
        .get("rest_id", "")
    )

    data = await asyncio.to_thread(
        _graphql_get,
        "Followers",
        {"userId": user_id, "count": min(limit, 100), "includePromotedContent": False},
    )

    followers = []
    if data and "data" in data:
        instructions = (
            data.get("data", {})
            .get("user", {})
            .get("result", {})
            .get("timeline", {})
            .get("timeline", {})
            .get("instructions", [])
        )
        for inst in instructions:
            for entry in inst.get("entries", []):
                result = (
                    entry.get("content", {})
                    .get("itemContent", {})
                    .get("user_results", {})
                    .get("result", {})
                )
                if result:
                    legacy = result.get("legacy", {})
                    followers.append({
                        "username": legacy.get("screen_name", ""),
                        "name": legacy.get("name", ""),
                        "bio": legacy.get("description", "")[:200],
                        "followers": legacy.get("followers_count", 0),
                        "verified": result.get("is_blue_verified", False),
                    })

    return {
        "username": username,
        "source": "x_graphql",
        "followers": followers[:limit],
        "count": len(followers),
    }


@handle_tool_errors("research_x_trending")
async def research_x_trending(
    location: str = "worldwide",
) -> dict[str, Any]:
    """Get trending topics on X/Twitter.

    Args:
        location: Location filter (default "worldwide")

    Returns:
        Dict with trending topics and tweet volumes
    """
    if isinstance(location, list):
        location = str(location[0]) if location else "worldwide"

    cookies = _load_cookies()
    if not cookies:
        return {"error": "X session not configured", "source": "none"}

    try:
        url = "https://x.com/i/api/2/guide.json?include_page_configuration=false&initial_tab_id=trending"
        resp = await asyncio.to_thread(
            requests.get, url, headers=_headers(cookies), timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            trends = []
            for module in data.get("timeline", {}).get("instructions", []):
                for entry in module.get("addEntries", {}).get("entries", []):
                    trend = entry.get("content", {}).get("timelineModule", {})
                    for item in trend.get("items", []):
                        trend_data = (
                            item.get("item", {})
                            .get("content", {})
                            .get("trend", {})
                        )
                        name = trend_data.get("name", "")
                        if name:
                            trends.append({
                                "name": name,
                                "tweet_count": trend_data.get("trendMetadata", {}).get("metaDescription", ""),
                                "url": f"https://x.com/search?q={urllib.parse.quote(name)}",
                            })

            return {
                "location": location,
                "source": "x_api",
                "trends": trends[:30],
                "count": len(trends),
            }
    except Exception as e:
        logger.warning("Trending API failed: %s", e)

    return {
        "location": location,
        "source": "none",
        "trends": [],
        "error": "Could not fetch trends",
    }
