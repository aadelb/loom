"""Tag/Label system for organizing and filtering tools."""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.tool_tags")

_TAGS_FILE = Path.home() / ".loom" / "tool_tags.json"

DEFAULT_TAGS = {
    "research_swarm_attack": ["offensive", "attack"],
    "research_crescendo_loop": ["offensive", "attack"],
    "research_reid_pipeline": ["offensive", "attack"],
    "research_safety_filter_map": ["defensive", "safety"],
    "research_bias_probe": ["defensive", "safety"],
    "research_github": ["osint", "reconnaissance"],
    "research_social_graph": ["osint", "social"],
    "research_identity_resolve": ["osint", "social"],
    "research_infra_correlator": ["osint", "infrastructure"],
    "research_passive_recon": ["osint", "dns"],
    "research_config_watch": ["infrastructure", "monitoring"],
    "research_backup_create": ["infrastructure", "backup"],
    "research_cache_stats": ["infrastructure", "cache"],
    "research_model_profile": ["analysis", "profiling"],
    "research_unified_score": ["analysis", "scoring"],
    "research_sentiment_deep": ["analysis", "sentiment"],
    "research_fetch": ["research", "scraping"],
    "research_spider": ["research", "scraping"],
    "research_markdown": ["research", "extraction"],
    "research_search": ["research", "search"],
    "research_deep": ["research", "search"],
}

@handle_tool_errors("research_tag_tool")

async def research_tag_tool(tool_name: str, tags: list[str]) -> dict:
    """Add tags to a tool for organization.

    Args:
        tool_name: Name of the tool to tag
        tags: List of tags to add (deduplicated)

    Returns:
        {tool, tags_added, total_tags}
    """
    try:
        _TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tags_dict = json.loads(_TAGS_FILE.read_text()) if _TAGS_FILE.exists() else {}
        unique_tags = sorted(set(t.lower().strip() for t in tags if t.strip()))
        existing = set(tags_dict.get(tool_name, []))
        all_tags = sorted(existing | set(unique_tags))
        tags_dict[tool_name] = all_tags

        tmp_path = _TAGS_FILE.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(tags_dict, indent=2))
        tmp_path.replace(_TAGS_FILE)

        logger.info("tool_tagged", extra={"tool": tool_name, "tags_added": len(unique_tags), "total": len(all_tags)})
        return {"tool": tool_name, "tags_added": len(unique_tags), "total_tags": len(all_tags)}
    except Exception as e:
        logger.error("tag_tool_error", extra={"tool": tool_name, "error": str(e)})
        return {"error": str(e), "tool": tool_name}

@handle_tool_errors("research_tag_search")

async def research_tag_search(tags: list[str], match: str = "any") -> dict:
    """Find tools by tag(s).

    Args:
        tags: List of tags to search for
        match: "any" (OR logic) or "all" (AND logic)

    Returns:
        {tags_searched, match_mode, tools, total_matches}
    """
    try:
        search_tags = set(t.lower().strip() for t in tags if t.strip())
        tags_dict = json.loads(_TAGS_FILE.read_text()) if _TAGS_FILE.exists() else {}
        all_tags = {**DEFAULT_TAGS, **tags_dict}

        matches = []
        for tool, tool_tags in all_tags.items():
            tool_tag_set = set(t.lower().strip() for t in tool_tags)
            if (search_tags.issubset(tool_tag_set) if match == "all" else search_tags & tool_tag_set):
                matches.append({"name": tool, "tags": tool_tags})

        matches.sort(key=lambda x: x["name"])
        logger.info("tag_search", extra={"tags": list(search_tags), "match_mode": match, "matches": len(matches)})
        return {
            "tags_searched": list(search_tags),
            "match_mode": match,
            "tools": matches,
            "total_matches": len(matches),
        }
    except Exception as e:
        logger.error("tag_search_error", extra={"tags": tags, "error": str(e)})
        return {"error": str(e), "tags_searched": tags, "tools": []}

@handle_tool_errors("research_tag_cloud")

async def research_tag_cloud() -> dict:
    """Generate tag frequency cloud.

    Returns:
        {tags, total_unique_tags, most_common_tag}
    """
    try:
        tags_dict = json.loads(_TAGS_FILE.read_text()) if _TAGS_FILE.exists() else {}
        all_tags = {**DEFAULT_TAGS, **tags_dict}

        tag_counter, tag_tools = Counter(), {}
        for tool, tool_tags in all_tags.items():
            for tag in tool_tags:
                norm = tag.lower().strip()
                tag_counter[norm] += 1
                if norm not in tag_tools:
                    tag_tools[norm] = []
                tag_tools[norm].append(tool)

        cloud = [
            {"tag": tag, "count": count, "tools": sorted(tag_tools.get(tag, []))}
            for tag, count in tag_counter.most_common()
        ]

        most_common = cloud[0]["tag"] if cloud else None
        logger.info("tag_cloud_generated", extra={"unique_tags": len(cloud), "most_common": most_common})
        return {"tags": cloud, "total_unique_tags": len(cloud), "most_common_tag": most_common}
    except Exception as e:
        logger.error("tag_cloud_error", extra={"error": str(e)})
        return {"error": str(e), "tags": []}
