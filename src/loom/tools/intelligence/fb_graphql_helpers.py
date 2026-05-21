"""Facebook GraphQL data extraction helpers.

Adapted from FaustRen/facebook-graphql-scraper (75 stars).
These recursive JSON walkers extract structured data from Facebook's
internal GraphQL responses embedded in rendered HTML.
"""
import json
import re
from typing import Any


def find_feedback(data: Any) -> dict | None:
    """Recursively find feedback dict with subscription_target_id (= post ID)."""
    if isinstance(data, dict):
        if "feedback" in data and isinstance(data["feedback"], dict):
            fb = data["feedback"]
            if "subscription_target_id" in fb:
                return fb
        for value in data.values():
            result = find_feedback(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_feedback(item)
            if result:
                return result
    return None


def find_message_text(data: Any) -> str:
    """Recursively find story.message.text in GraphQL response."""
    if isinstance(data, dict):
        if "story" in data and isinstance(data["story"], dict):
            msg = data["story"].get("message")
            if isinstance(msg, dict) and "text" in msg:
                return msg["text"]
        for value in data.values():
            result = find_message_text(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_message_text(item)
            if result:
                return result
    return ""


def find_creation_time(data: Any) -> int:
    """Recursively find story.creation_time (Unix timestamp)."""
    if isinstance(data, dict):
        if "story" in data and isinstance(data["story"], dict):
            ct = data["story"].get("creation_time")
            if ct:
                return int(ct)
        for value in data.values():
            result = find_creation_time(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_creation_time(item)
            if result:
                return result
    return 0


def find_actors(data: Any) -> dict:
    """Recursively find story.actors (post author info)."""
    if isinstance(data, dict):
        if "story" in data and isinstance(data["story"], dict):
            actors = data["story"].get("actors")
            if actors:
                return actors if isinstance(actors, dict) else actors[0] if isinstance(actors, list) else {}
        for value in data.values():
            result = find_actors(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_actors(item)
            if result:
                return result
    return {}


def extract_graphql_posts(html: str) -> list[dict[str, Any]]:
    """Extract structured posts from Facebook HTML containing GraphQL JSON blobs.

    Parses the inline JSON data that Facebook embeds in rendered HTML,
    extracting post data using the same recursive walkers that
    facebook-graphql-scraper uses.
    """
    posts = []

    # Find all JSON blobs that look like GraphQL responses
    # Facebook embeds them as: require("RelayPrefetchedStreamCache")...init({"data":...})
    json_blobs = re.findall(
        r'\{"data":\{"node":\{[^}]{50,}', html
    )

    for blob in json_blobs:
        # Try to find a complete JSON object
        depth = 0
        end = 0
        for i, ch in enumerate(blob):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == 0:
            continue

        try:
            data = json.loads(blob[:end])
        except (json.JSONDecodeError, ValueError):
            continue

        feedback = find_feedback(data)
        if not feedback:
            continue

        text = find_message_text(data)
        creation = find_creation_time(data)
        actors = find_actors(data)

        post = {
            "post_id": feedback.get("subscription_target_id", ""),
            "text": text[:500] if text else "",
            "creation_time": creation,
            "reactions": feedback.get("reaction_count", {}).get("count", 0),
            "comments": feedback.get("comment_rendering_instance", {}).get("comments", {}).get("total_count", 0),
            "shares": feedback.get("share_count", {}).get("count", 0),
            "video_views": feedback.get("video_view_count", 0),
            "author": actors.get("name", "") if isinstance(actors, dict) else "",
        }

        # Extract reaction breakdown
        top_reactions = feedback.get("top_reactions", {}).get("edges", [])
        reaction_breakdown = {}
        for edge in top_reactions:
            node = edge.get("node", {})
            rtype = node.get("reaction_type", "UNKNOWN")
            count = edge.get("reaction_count", 0)
            reaction_breakdown[rtype.lower()] = count
        post["reaction_breakdown"] = reaction_breakdown

        posts.append(post)

    return posts


def build_osint_search_url(
    target_id: str = "",
    keyword: str = "*",
    search_type: str = "posts",
    group_id: str = "",
) -> str:
    """Build a Facebook search URL with encoded OSINT filters.

    Adapted from tomoneill19/FacebookOSINT (145 stars).
    Uses base64-encoded filter parameters for targeted queries.
    """
    import base64

    filters = []
    if target_id:
        filters.append(f'"rp_author":{{"name":"author","args":"{target_id}"}}')
    if group_id:
        filters.append(f'"rp_group":{{"name":"group_posts","args":"{group_id}"}}')

    joined = "{" + ",".join(filters) + "}"
    encoded = base64.b64encode(joined.encode()).decode().rstrip("=")

    url = f"https://www.facebook.com/search/{search_type}/?q={keyword}"
    if filters:
        url += f"&epa=FILTERS&filters={encoded}"
    return url
