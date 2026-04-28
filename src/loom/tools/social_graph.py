"""Social relationship graph analysis — build relationship graphs from public data."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.social_graph")

_HTTP_TIMEOUT = 15.0
_GITHUB_RATE_LIMIT_DELAY = 1.0  # 1 req/sec for GitHub


async def _get_json(
    client: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None
) -> Any:
    """Fetch JSON from URL safely."""
    try:
        resp = await client.get(url, timeout=_HTTP_TIMEOUT, headers=headers or {})
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("json_fetch_failed url=%s error=%s", url, exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None
) -> str:
    """Fetch text from URL safely."""
    try:
        resp = await client.get(url, timeout=_HTTP_TIMEOUT, headers=headers or {})
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("text_fetch_failed url=%s error=%s", url, exc)
    return ""


async def _fetch_github_data(
    client: httpx.AsyncClient, username: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str, int]]]:
    """Fetch GitHub repos and co-contributor relationships.

    Returns:
        Tuple of (nodes, edges) where:
        - nodes: list of {id, platform, name}
        - edges: list of (source, target, relationship, weight)
    """
    nodes: list[dict[str, Any]] = []
    edges: list[tuple[str, str, str, int]] = []

    # Add main user node
    nodes.append({"id": f"github:{username}", "platform": "github", "name": username})

    try:
        # Fetch repos with rate limiting
        repos_url = f"https://api.github.com/users/{username}/repos"
        repos = await _get_json(client, repos_url, {"Accept": "application/vnd.github.v3+json"})

        if not repos or not isinstance(repos, list):
            return nodes, edges

        # Track contributors across repos
        contributors_by_repo: dict[str, list[str]] = {}

        for repo_idx, repo in enumerate(repos[:50]):  # Limit to 50 repos
            if repo_idx > 0:
                await asyncio.sleep(_GITHUB_RATE_LIMIT_DELAY)

            repo_name = repo.get("name")
            if not repo_name:
                continue

            # Fetch contributors for this repo
            contributors_url = (
                f"https://api.github.com/repos/{username}/{repo_name}/contributors"
            )
            contributors = await _get_json(
                client, contributors_url, {"Accept": "application/vnd.github.v3+json"}
            )

            if not contributors or not isinstance(contributors, list):
                continue

            repo_contributors = []
            for contributor in contributors[:30]:  # Limit to 30 per repo
                if isinstance(contributor, dict):
                    contrib_login = contributor.get("login")
                    if contrib_login and contrib_login != username:
                        repo_contributors.append(contrib_login)
                        # Add contributor node if not already present
                        node_id = f"github:{contrib_login}"
                        if not any(n["id"] == node_id for n in nodes):
                            nodes.append(
                                {
                                    "id": node_id,
                                    "platform": "github",
                                    "name": contrib_login,
                                }
                            )

            contributors_by_repo[repo_name] = repo_contributors

        # Build co-contributor edges
        for _repo_name, contributors in contributors_by_repo.items():
            # Connect main user to each contributor
            for contributor in contributors:
                edges.append(
                    (
                        f"github:{username}",
                        f"github:{contributor}",
                        "collaborated",
                        1,
                    )
                )

            # Connect contributors who worked on same repo
            for i, contrib1 in enumerate(contributors):
                for contrib2 in contributors[i + 1 :]:
                    edges.append(
                        (
                            f"github:{contrib1}",
                            f"github:{contrib2}",
                            "co-contributor",
                            1,
                        )
                    )

    except Exception as exc:
        logger.error("github_fetch_error username=%s error=%s", username, exc)

    return nodes, edges


async def _fetch_reddit_data(
    client: httpx.AsyncClient, username: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str, int]]]:
    """Fetch Reddit user data and community/reply relationships.

    Returns:
        Tuple of (nodes, edges) where:
        - nodes: list of {id, platform, name}
        - edges: list of (source, target, relationship, weight)
    """
    nodes: list[dict[str, Any]] = []
    edges: list[tuple[str, str, str, int]] = []

    # Add main user node
    nodes.append({"id": f"reddit:{username}", "platform": "reddit", "name": username})

    try:
        # Fetch user comments
        comments_url = f"https://www.reddit.com/user/{username}/comments.json"
        data = await _get_json(client, comments_url, {"User-Agent": "Loom-Research/1.0"})

        if not data or "data" not in data:
            return nodes, edges

        comments = data.get("data", {}).get("children", [])
        if not isinstance(comments, list):
            return nodes, edges

        # Track subreddit activity and reply mentions
        subreddit_activity: dict[str, int] = {}
        mentioned_users: set[str] = set()

        for comment in comments[:100]:  # Limit to 100 comments
            if not isinstance(comment, dict):
                continue

            comment_data = comment.get("data", {})
            subreddit = comment_data.get("subreddit")

            # Track subreddit activity
            if subreddit:
                subreddit_activity[subreddit] = subreddit_activity.get(subreddit, 0) + 1

            # Extract mentions (Reddit username format: u/username)
            body = comment_data.get("body", "")
            mentions = re.findall(r"u/([a-zA-Z0-9_-]+)", body)
            for mention in mentions:
                if mention.lower() != username.lower():
                    mentioned_users.add(mention)

        # Add subreddit nodes
        for subreddit, activity_count in subreddit_activity.items():
            node_id = f"reddit:r/{subreddit}"
            nodes.append({"id": node_id, "platform": "reddit", "name": f"r/{subreddit}"})
            edges.append(
                (
                    f"reddit:{username}",
                    node_id,
                    "posts_in",
                    activity_count,
                )
            )

        # Add mentioned user nodes
        for mentioned_user in mentioned_users:
            node_id = f"reddit:{mentioned_user}"
            if not any(n["id"] == node_id for n in nodes):
                nodes.append(
                    {"id": node_id, "platform": "reddit", "name": mentioned_user}
                )
            edges.append(
                (
                    f"reddit:{username}",
                    node_id,
                    "mentions",
                    1,
                )
            )

    except Exception as exc:
        logger.error("reddit_fetch_error username=%s error=%s", username, exc)

    return nodes, edges


async def _fetch_hackernews_data(
    client: httpx.AsyncClient, username: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str, int]]]:
    """Fetch HackerNews user data and topic/karma relationships.

    Returns:
        Tuple of (nodes, edges) where:
        - nodes: list of {id, platform, name}
        - edges: list of (source, target, relationship, weight)
    """
    nodes: list[dict[str, Any]] = []
    edges: list[tuple[str, str, str, int]] = []

    # Add main user node
    nodes.append({"id": f"hn:{username}", "platform": "hackernews", "name": username})

    try:
        # Fetch user profile
        user_url = f"https://hacker-news.firebaseio.com/v0/user/{username}.json"
        user_data = await _get_json(client, user_url)

        if not user_data:
            return nodes, edges

        # Get karma
        karma = user_data.get("karma", 0)

        # Fetch submissions
        submission_ids = user_data.get("submitted", [])
        if not isinstance(submission_ids, list):
            return nodes, edges

        # Track topics from submissions
        topic_count: dict[str, int] = {}

        for submission_id in submission_ids[:50]:  # Limit to 50 submissions
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{submission_id}.json"
            story_data = await _get_json(client, story_url)

            if not story_data:
                continue

            title = story_data.get("title", "").lower()
            url = story_data.get("url", "")

            # Extract potential topics from title (simple heuristic)
            topics = _extract_hn_topics(title, url)
            for topic in topics:
                topic_count[topic] = topic_count.get(topic, 0) + 1

        # Add topic nodes and edges
        for topic, count in topic_count.items():
            node_id = f"hn:topic:{topic}"
            nodes.append({"id": node_id, "platform": "hackernews", "name": topic})
            edges.append(
                (
                    f"hn:{username}",
                    node_id,
                    "interested_in",
                    count,
                )
            )

        # Add karma relationship to self (for reference)
        if karma > 0:
            edges.append(
                (
                    f"hn:{username}",
                    f"hn:{username}",
                    "karma",
                    karma,
                )
            )

    except Exception as exc:
        logger.error("hackernews_fetch_error username=%s error=%s", username, exc)

    return nodes, edges


async def _fetch_semanticscholar_data(
    author_name: str,
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str, int]]]:
    """Fetch Semantic Scholar author data and co-author relationships.

    Returns:
        Tuple of (nodes, edges) where:
        - nodes: list of {id, platform, name}
        - edges: list of (source, target, relationship, weight)
    """
    nodes: list[dict[str, Any]] = []
    edges: list[tuple[str, str, str, int]] = []

    try:
        async with httpx.AsyncClient() as client:
            # Search for author
            search_url = f"https://api.semanticscholar.org/graph/v1/author/search?query={author_name}&limit=1"
            search_data = await _get_json(client, search_url)

            if not search_data or "data" not in search_data:
                return nodes, edges

            authors = search_data.get("data", [])
            if not authors:
                return nodes, edges

            author = authors[0]
            author_id = author.get("authorId")

            if not author_id:
                return nodes, edges

            # Add main author node
            name = author.get("name", author_name)
            nodes.append(
                {"id": f"semanticscholar:{author_id}", "platform": "semanticscholar", "name": name}
            )

            # Fetch author papers
            papers_url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers?fields=authors"
            papers_data = await _get_json(client, papers_url)

            if not papers_data or "data" not in papers_data:
                return nodes, edges

            papers = papers_data.get("data", [])
            coauthor_count: dict[str, int] = {}

            for paper in papers[:30]:  # Limit to 30 papers
                if not isinstance(paper, dict):
                    continue

                paper_authors = paper.get("authors", [])
                if not isinstance(paper_authors, list):
                    continue

                for coauthor_info in paper_authors:
                    if not isinstance(coauthor_info, dict):
                        continue

                    coauthor_id = coauthor_info.get("authorId")
                    coauthor_name = coauthor_info.get("name", "Unknown")

                    if not coauthor_id or coauthor_id == author_id:
                        continue

                    coauthor_count[coauthor_id] = coauthor_count.get(coauthor_id, 0) + 1

                    # Add coauthor node if not already present
                    node_id = f"semanticscholar:{coauthor_id}"
                    if not any(n["id"] == node_id for n in nodes):
                        nodes.append(
                            {
                                "id": node_id,
                                "platform": "semanticscholar",
                                "name": coauthor_name,
                            }
                        )

            # Add co-authorship edges
            for coauthor_id, paper_count in coauthor_count.items():
                edges.append(
                    (
                        f"semanticscholar:{author_id}",
                        f"semanticscholar:{coauthor_id}",
                        "co-author",
                        paper_count,
                    )
                )

    except Exception as exc:
        logger.error("semanticscholar_fetch_error author=%s error=%s", author_name, exc)

    return nodes, edges


def _extract_hn_topics(title: str, url: str) -> list[str]:
    """Extract potential topics from HN title and URL.

    Args:
        title: Article title
        url: Article URL

    Returns:
        List of potential topic keywords
    """
    topics: set[str] = set()

    # Keywords from title (simple heuristic)
    keywords = [
        "ai",
        "machine learning",
        "python",
        "javascript",
        "rust",
        "go",
        "kubernetes",
        "docker",
        "devops",
        "security",
        "privacy",
        "startup",
        "business",
        "programming",
        "web",
        "mobile",
        "database",
        "cloud",
        "open source",
    ]

    title_lower = title.lower()
    for keyword in keywords:
        if keyword in title_lower:
            topics.add(keyword)

    # Domain heuristics from URL
    if "arxiv.org" in url.lower():
        topics.add("research")
    elif "github.com" in url.lower():
        topics.add("open source")
    elif any(domain in url.lower() for domain in ["medium.com", "dev.to", "blog"]):
        topics.add("blog")

    # If no topics extracted, use "general" as fallback
    return list(topics) if topics else ["general"]


def research_social_graph(
    username: str, platforms: list[str] | None = None
) -> dict[str, Any]:
    """Build a social relationship graph from public data across platforms.

    Analyzes relationships across GitHub (co-contributors), Reddit (mentions),
    HackerNews (topic interests), and Semantic Scholar (co-authorship).

    Args:
        username: Username/identifier to analyze (interpreted per platform)
        platforms: List of platforms to analyze. Defaults to
                   ["github", "reddit", "hackernews"].
                   Supports: "github", "reddit", "hackernews", "semanticscholar"

    Returns:
        Dict with:
        - username: Input username
        - nodes: List of {id, platform, name}
        - edges: List of {source, target, relationship, weight}
        - platforms_analyzed: List of platforms successfully analyzed
        - total_connections: Total number of edges (relationships)
    """
    if not username or not isinstance(username, str):
        logger.warning("invalid_username username=%s", username)
        return {
            "username": username,
            "nodes": [],
            "edges": [],
            "platforms_analyzed": [],
            "total_connections": 0,
            "error": "username must be a non-empty string",
        }

    if len(username) > 255:
        logger.warning("username_too_long username_len=%d", len(username))
        return {
            "username": username,
            "nodes": [],
            "edges": [],
            "platforms_analyzed": [],
            "total_connections": 0,
            "error": "username exceeds 255 characters",
        }

    # Validate platforms
    platforms_to_use = platforms or ["github", "reddit", "hackernews"]
    valid_platforms = {"github", "reddit", "hackernews", "semanticscholar"}
    platforms_to_use = [p for p in platforms_to_use if p in valid_platforms]

    if not platforms_to_use:
        logger.warning(
            "no_valid_platforms username=%s platforms=%s", username, platforms_to_use
        )
        return {
            "username": username,
            "nodes": [],
            "edges": [],
            "platforms_analyzed": [],
            "total_connections": 0,
            "error": "no valid platforms specified",
        }

    async def _run() -> dict[str, Any]:
        all_nodes: list[dict[str, Any]] = []
        all_edges: list[dict[str, Any]] = []
        platforms_analyzed: list[str] = []

        async with httpx.AsyncClient() as client:
            # GitHub fetch
            if "github" in platforms_to_use:
                try:
                    gh_nodes, gh_edges = await _fetch_github_data(client, username)
                    all_nodes.extend(gh_nodes)
                    all_edges.extend(
                        {
                            "source": source,
                            "target": target,
                            "relationship": rel,
                            "weight": weight,
                        }
                        for source, target, rel, weight in gh_edges
                    )
                    platforms_analyzed.append("github")
                except Exception as exc:
                    logger.error("github_graph_error username=%s error=%s", username, exc)

            # Reddit fetch
            if "reddit" in platforms_to_use:
                try:
                    reddit_nodes, reddit_edges = await _fetch_reddit_data(client, username)
                    all_nodes.extend(reddit_nodes)
                    all_edges.extend(
                        {
                            "source": source,
                            "target": target,
                            "relationship": rel,
                            "weight": weight,
                        }
                        for source, target, rel, weight in reddit_edges
                    )
                    platforms_analyzed.append("reddit")
                except Exception as exc:
                    logger.error("reddit_graph_error username=%s error=%s", username, exc)

            # HackerNews fetch
            if "hackernews" in platforms_to_use:
                try:
                    hn_nodes, hn_edges = await _fetch_hackernews_data(client, username)
                    all_nodes.extend(hn_nodes)
                    all_edges.extend(
                        {
                            "source": source,
                            "target": target,
                            "relationship": rel,
                            "weight": weight,
                        }
                        for source, target, rel, weight in hn_edges
                    )
                    platforms_analyzed.append("hackernews")
                except Exception as exc:
                    logger.error("hackernews_graph_error username=%s error=%s", username, exc)

        # Semantic Scholar uses author name (not platform-specific username)
        if "semanticscholar" in platforms_to_use:
            try:
                ss_nodes, ss_edges = await _fetch_semanticscholar_data(username)
                all_nodes.extend(ss_nodes)
                all_edges.extend(
                    {
                        "source": source,
                        "target": target,
                        "relationship": rel,
                        "weight": weight,
                    }
                    for source, target, rel, weight in ss_edges
                )
                if ss_nodes:  # Only mark as analyzed if we got data
                    platforms_analyzed.append("semanticscholar")
            except Exception as exc:
                logger.error("semanticscholar_graph_error author=%s error=%s", username, exc)

        # Deduplicate nodes by id
        seen_ids: set[str] = set()
        unique_nodes: list[dict[str, Any]] = []
        for node in all_nodes:
            if node["id"] not in seen_ids:
                seen_ids.add(node["id"])
                unique_nodes.append(node)

        # Deduplicate edges by (source, target, relationship)
        seen_edges: set[tuple[str, str, str]] = set()
        unique_edges: list[dict[str, Any]] = []
        for edge in all_edges:
            key = (edge["source"], edge["target"], edge["relationship"])
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(edge)

        logger.info(
            "social_graph_completed username=%s platforms=%s nodes=%d edges=%d",
            username,
            platforms_analyzed,
            len(unique_nodes),
            len(unique_edges),
        )

        return {
            "username": username,
            "nodes": unique_nodes,
            "edges": unique_edges,
            "platforms_analyzed": platforms_analyzed,
            "total_connections": len(unique_edges),
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
