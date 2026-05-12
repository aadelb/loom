"""Network social graph analysis for forum and community detection.

Tools:
- research_network_persona: author interaction graph analysis with role detection
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from loom.error_responses import handle_tool_errors
from typing import Any

logger = logging.getLogger("loom.tools.network_persona")


def _normalize_author(author: str) -> str:
    """Normalize author name for matching (lowercase, strip whitespace)."""
    if not isinstance(author, str):
        return ""
    return author.strip().lower()


def _compute_in_degree(edges: list[tuple[str, str]]) -> dict[str, int]:
    """Compute in-degree (# of times author was replied to)."""
    in_degree: dict[str, int] = defaultdict(int)
    for from_author, to_author in edges:
        if from_author and to_author:
            in_degree[to_author] += 1
    return dict(in_degree)


def _compute_out_degree(edges: list[tuple[str, str]]) -> dict[str, int]:
    """Compute out-degree (# of times author replied to others)."""
    out_degree: dict[str, int] = defaultdict(int)
    for from_author, to_author in edges:
        if from_author:
            out_degree[from_author] += 1
    return dict(out_degree)


def _find_connected_components(
    nodes: set[str], edges: list[tuple[str, str]]
) -> list[set[str]]:
    """Find connected components in undirected graph."""
    adj: dict[str, set[str]] = defaultdict(set)
    for from_author, to_author in edges:
        if from_author and to_author:
            adj[from_author].add(to_author)
            adj[to_author].add(from_author)

    visited: set[str] = set()
    components: list[set[str]] = []

    for node in nodes:
        if node in visited:
            continue
        component: set[str] = set()
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in visited:
                    stack.append(neighbor)
        if component:
            components.append(component)

    return components


def _classify_role(
    author: str,
    post_count: int,
    replies_sent: int,
    replies_received: int,
    in_degree: dict[str, int],
    out_degree: dict[str, int],
) -> str:
    """Classify author role based on interaction metrics."""
    if post_count < 1:
        return "lurker"

    in_deg = in_degree.get(author, 0)
    out_deg = out_degree.get(author, 0)

    # hub: high out-degree (connects to many)
    if out_deg >= 5 and out_deg > in_deg * 1.5:
        return "hub"

    # authority: high in-degree (many reply to them)
    if in_deg >= 5 and in_deg > out_deg * 1.5:
        return "authority"

    # lurker: low interaction
    if replies_sent < 2 and replies_received < 2:
        return "lurker"

    # bridge: moderate in/out, connects groups
    if out_deg >= 3 and in_deg >= 3:
        return "bridge"

    # regular
    return "regular"


@handle_tool_errors("research_network_persona")
async def research_network_persona(
    posts: list[dict[str, Any]],
    min_interactions: int = 2,
) -> dict[str, Any]:
    """Analyze social network structure within forum data.

    Maps author interactions, identifies key roles (hub, authority, bridge,
    lurker), and computes network metrics.

    Args:
        posts: list of post dicts with keys:
            - "author" (str, required)
            - "text" (str, optional, for text length)
            - "reply_to" (str, optional, author being replied to)
            - "timestamp" (str/int, optional, for activity span)
        min_interactions: minimum in+out interactions to include author

    Returns:
        Dict with authors, network metrics, edges, and role assignments.
    """
    try:
        # Validate input
        if not posts or not isinstance(posts, list):
            logger.warning("research_network_persona: empty or invalid posts list")
            return {
                "authors": {},
                "network": {
                    "total_authors": 0,
                    "total_edges": 0,
                    "density": 0.0,
                    "communities": 0,
                    "top_authorities": [],
                    "top_hubs": [],
                },
                "edges": [],
            }

        # Filter valid posts
        valid_posts = [
            p for p in posts
            if isinstance(p, dict) and isinstance(p.get("author"), str) and p.get("author", "").strip()
        ]

        if len(valid_posts) < 3:
            logger.warning("research_network_persona: fewer than 3 valid posts")
            return {
                "authors": {},
                "network": {
                    "total_authors": 0,
                    "total_edges": 0,
                    "density": 0.0,
                    "communities": 0,
                    "top_authorities": [],
                    "top_hubs": [],
                },
                "edges": [],
            }

        # Run analysis in executor
        loop = asyncio.get_running_loop()

        def _analyze() -> dict[str, Any]:
            # Build author metrics and edges
            authors: dict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "post_count": 0,
                    "replies_sent": 0,
                    "replies_received": 0,
                    "unique_contacts": set(),
                    "text_lengths": [],
                    "timestamps": [],
                }
            )

            edges: list[tuple[str, str]] = []
            all_authors: set[str] = set()

            for post in valid_posts:
                author = _normalize_author(post.get("author", ""))
                if not author:
                    continue

                all_authors.add(author)
                authors[author]["post_count"] += 1

                # Track text length
                text = post.get("text", "")
                if isinstance(text, str):
                    authors[author]["text_lengths"].append(len(text))

                # Track timestamp
                ts = post.get("timestamp")
                if ts is not None:
                    authors[author]["timestamps"].append(ts)

                # Track reply relationship
                reply_to = post.get("reply_to")
                if reply_to:
                    reply_to = _normalize_author(reply_to)
                    if reply_to and reply_to != author:
                        edges.append((author, reply_to))
                        authors[author]["replies_sent"] += 1
                        authors[reply_to]["replies_received"] += 1
                        authors[author]["unique_contacts"].add(reply_to)

            # Require at least some reply_to fields
            if not edges:
                logger.warning("research_network_persona: no reply_to relationships found")
                return {
                    "authors": {},
                    "network": {
                        "total_authors": len(all_authors),
                        "total_edges": 0,
                        "density": 0.0,
                        "communities": 0,
                        "top_authorities": [],
                        "top_hubs": [],
                    },
                    "edges": [],
                }

            # Compute centrality
            in_degree = _compute_in_degree(edges)
            out_degree = _compute_out_degree(edges)

            # Filter authors by min_interactions
            filtered_authors: dict[str, dict[str, Any]] = {}
            for author in all_authors:
                total_interactions = (in_degree.get(author, 0) + out_degree.get(author, 0))
                if total_interactions >= min_interactions:
                    author_data = authors[author]
                    filtered_authors[author] = {
                        "post_count": author_data["post_count"],
                        "replies_sent": author_data["replies_sent"],
                        "replies_received": author_data["replies_received"],
                        "unique_contacts": len(author_data["unique_contacts"]),
                        "avg_text_length": (
                            sum(author_data["text_lengths"]) / len(author_data["text_lengths"])
                            if author_data["text_lengths"]
                            else 0.0
                        ),
                        "role": _classify_role(
                            author,
                            author_data["post_count"],
                            author_data["replies_sent"],
                            author_data["replies_received"],
                            in_degree,
                            out_degree,
                        ),
                        "influence_score": 0.0,  # Set below
                    }

            # Compute influence score (normalized in-degree)
            max_in_degree = max((in_degree.get(a, 0) for a in filtered_authors), default=1)
            for author in filtered_authors:
                filtered_authors[author]["influence_score"] = (
                    in_degree.get(author, 0) / max_in_degree if max_in_degree > 0 else 0.0
                )

            # Network density
            total_authors = len(filtered_authors)
            total_edges_count = len(edges)
            max_possible_edges = total_authors * (total_authors - 1) / 2 if total_authors > 1 else 1
            density = total_edges_count / max_possible_edges if max_possible_edges > 0 else 0.0

            # Communities (connected components in undirected graph)
            communities = _find_connected_components(set(filtered_authors.keys()), edges)

            # Top authorities and hubs
            sorted_by_in_degree = sorted(
                filtered_authors.items(),
                key=lambda x: in_degree.get(x[0], 0),
                reverse=True,
            )
            top_authorities = [author for author, _ in sorted_by_in_degree[:5]]

            sorted_by_out_degree = sorted(
                filtered_authors.items(),
                key=lambda x: out_degree.get(x[0], 0),
                reverse=True,
            )
            top_hubs = [author for author, _ in sorted_by_out_degree[:5]]

            # Deduplicate edges and compute weights
            edge_weights: dict[tuple[str, str], int] = defaultdict(int)
            for from_author, to_author in edges:
                if from_author in filtered_authors and to_author in filtered_authors:
                    edge_weights[(from_author, to_author)] += 1

            edges_output = [
                {
                    "from": from_author,
                    "to": to_author,
                    "weight": weight,
                }
                for (from_author, to_author), weight in edge_weights.items()
            ]

            return {
                "authors": filtered_authors,
                "network": {
                    "total_authors": total_authors,
                    "total_edges": len(edge_weights),
                    "density": round(density, 3),
                    "communities": len(communities),
                    "top_authorities": top_authorities,
                    "top_hubs": top_hubs,
                },
                "edges": edges_output,
            }

        result = await loop.run_in_executor(None, _analyze)
        logger.info(
            "network_persona_analyzed",
            total_authors=result["network"]["total_authors"],
            total_edges=result["network"]["total_edges"],
            density=result["network"]["density"],
        )
        return result
    except Exception as exc:
        logger.error("research_network_persona failed: %s", exc)
        return {
            "error": str(exc),
            "tool": "research_network_persona",
        }
