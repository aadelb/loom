"""Social media and article extraction tools using instaloader and newspaper3k."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, TypedDict

from loom.validators import validate_url, UrlSafetyError

try:
    import instaloader
    from instaloader import Profile, Instaloader

    _HAS_INSTALOADER = True
except ImportError:  # pragma: no cover
    _HAS_INSTALOADER = False
    Profile = None  # type: ignore
    Instaloader = None  # type: ignore

try:
    from newspaper import Article

    _HAS_NEWSPAPER = True
except ImportError:  # pragma: no cover
    _HAS_NEWSPAPER = False
    Article = None  # type: ignore

logger = logging.getLogger("loom.tools.social_scraper")


class InstagramPost(TypedDict):
    """Instagram post data."""

    url: str
    caption: str | None
    likes: int
    comments: int
    date: str


class InstagramProfile(TypedDict):
    """Instagram profile data."""

    username: str
    full_name: str | None
    bio: str | None
    followers: int
    following: int
    post_count: int
    recent_posts: list[InstagramPost]


class ArticleData(TypedDict):
    """Extracted article data."""

    url: str
    title: str | None
    authors: list[str]
    publish_date: str | None
    text: str
    summary: str | None
    keywords: list[str]
    top_image: str | None
    movies: list[str]


class ArticleBatchResult(TypedDict):
    """Batch article extraction result."""

    urls_processed: int
    articles: list[ArticleData]
    failed: list[dict[str, str]]


async def research_instagram(username: str, max_posts: int = 10) -> dict[str, Any]:
    """Download Instagram profile info and recent posts.

    Args:
        username: Instagram username (without @ symbol)
        max_posts: Maximum number of recent posts to fetch (default: 10, max: 100)

    Returns:
        dict with keys: username, full_name, bio, followers, following,
        post_count, recent_posts (list of {url, caption, likes, comments, date})

    Raises:
        ValueError: If instaloader is not installed or username is invalid
    """
    try:
        if not username or not isinstance(username, str):
            return {"error": "invalid username", "username": username}

        if not _HAS_INSTALOADER:
            return {"error": "instaloader not installed", "username": username}

        # Clamp max_posts
        max_posts = min(max(max_posts, 1), 100)

        # Run synchronous operation in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _fetch_instagram_profile, username, max_posts)
        return result
    except Exception as e:
        logger.error("instagram_fetch_error username=%s error=%s", username, str(e))
        return {"error": str(e), "tool": "research_instagram"}


def _fetch_instagram_profile(username: str, max_posts: int) -> dict[str, Any]:
    """Synchronous helper to fetch Instagram profile data."""
    try:
        # Create instaloader context (no login required for public profiles)
        loader = Instaloader()

        # Fetch profile
        profile = Profile.from_username(loader.context, username)

        # Extract profile metadata
        result: InstagramProfile = {
            "username": profile.username,
            "full_name": profile.full_name or None,
            "bio": profile.biography or None,
            "followers": profile.followers,
            "following": profile.followees,
            "post_count": profile.mediacount,
            "recent_posts": [],
        }

        # Fetch recent posts
        posts: list[InstagramPost] = []
        post_iterator = profile.get_posts()

        for post in post_iterator:
            if len(posts) >= max_posts:
                break

            post_url = f"https://instagram.com/p/{post.shortcode}/"
            post_data: InstagramPost = {
                "url": post_url,
                "caption": post.caption or None,
                "likes": post.likes,
                "comments": post.comments,
                "date": post.date.isoformat(),
            }
            posts.append(post_data)

        result["recent_posts"] = posts

        logger.info("instagram_profile_fetched username=%s post_count=%d", username, len(posts))

        return result

    except Exception as e:
        if _HAS_INSTALOADER and isinstance(e, instaloader.exceptions.UserNotFound):
            logger.warning("instagram_user_not_found username=%s", username)
            return {"error": f"User {username} not found", "username": username}
        logger.error("instagram_fetch_error username=%s error=%s", username, str(e))
        return {"error": str(e), "username": username}


async def research_article_extract(url: str) -> dict[str, Any]:
    """Extract article content, metadata, and NLP features from URL.

    Uses newspaper3k to download, parse, and extract NLP features
    (summary, keywords) from the article.

    Args:
        url: Full article URL

    Returns:
        dict with keys: url, title, authors, publish_date, text, summary,
        keywords, top_image, movies

    Raises:
        ValueError: If newspaper3k is not installed
    """
    try:
        validate_url(url)
        if not url or not isinstance(url, str):
            return {"error": "invalid url", "url": url}

        if not _HAS_NEWSPAPER:
            return {"error": "newspaper3k not installed", "url": url}

        # Run synchronous extraction in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _extract_article_sync, url)
        return result
    except Exception as e:
        logger.error("article_extract_error url=%s error=%s", url, str(e))
        return {"error": str(e), "tool": "research_article_extract"}


def _extract_article_sync(url: str) -> dict[str, Any]:
    """Synchronous helper to extract article data."""
    try:
        article = Article(url)

        # Download the article
        article.download()

        # Parse the article
        article.parse()

        # Extract NLP features (summary, keywords)
        article.nlp()

        # Build result
        result: ArticleData = {
            "url": url,
            "title": article.title or None,
            "authors": article.authors or [],
            "publish_date": article.publish_date.isoformat()
            if article.publish_date
            else None,
            "text": article.text,
            "summary": article.summary or None,
            "keywords": article.keywords or [],
            "top_image": article.top_image or None,
            "movies": article.movies or [],
        }

        logger.info("article_extracted url=%s title=%s", url, result.get("title", ""))

        return result

    except Exception as e:
        logger.error("article_extract_error url=%s error=%s", url, str(e))
        return {"error": str(e), "url": url}


async def research_article_batch(
    urls: list[str], max_concurrent: int = 5
) -> dict[str, Any]:
    """Batch extract articles from multiple URLs with concurrency control.

    Args:
        urls: List of article URLs
        max_concurrent: Maximum concurrent requests (default: 5, max: 20)

    Returns:
        dict with keys: urls_processed, articles (list), failed (list with
        {url, error} dicts)
    """
    try:
        if not urls or not isinstance(urls, list):
            return {
                "error": "invalid urls",
                "urls_processed": 0,
                "articles": [],
                "failed": [],
            }

        if not _HAS_NEWSPAPER:
            return {
                "error": "newspaper3k not installed",
                "urls_processed": 0,
                "articles": [],
                "failed": [{"url": url, "error": "newspaper3k not installed"} for url in urls],
            }

        # Clamp max_concurrent
        max_concurrent = min(max(max_concurrent, 1), 20)

        # Limit total URLs
        urls = urls[:200]

        articles: list[ArticleData] = []
        failed: list[dict[str, str]] = []

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_with_semaphore(url: str) -> None:
            """Extract article with semaphore to control concurrency."""
            async with semaphore:
                result = await research_article_extract(url)

                # Check if result is an error dict
                if "error" in result and result.get("error"):
                    failed.append({"url": url, "error": result["error"]})
                else:
                    articles.append(result)  # type: ignore

        # Create tasks for all URLs
        tasks = [extract_with_semaphore(url) for url in urls]

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

        logger.info(
            "article_batch_complete urls_requested=%d articles_extracted=%d failed_count=%d",
            len(urls),
            len(articles),
            len(failed),
        )

        return {
            "urls_processed": len(urls),
            "articles": articles,
            "failed": failed,
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "tool": "research_article_batch",
            "urls_processed": 0,
            "articles": [],
            "failed": [],
        }
