"""Test X/Twitter GraphQL API with session cookies."""
import json
import urllib.parse

import requests

with open("/opt/loom-v3/x_session.json") as f:
    data = json.load(f)

cookies = {c["name"]: c["value"] for c in data["cookies"]}
auth_token = cookies["auth_token"]
ct0 = cookies["ct0"]

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

headers = {
    "Authorization": f"Bearer {BEARER}",
    "X-Csrf-Token": ct0,
    "Cookie": f"auth_token={auth_token}; ct0={ct0}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# Test 1: Search tweets
print("=== Search: AI safety ===")
variables = json.dumps({
    "rawQuery": "AI safety",
    "count": 3,
    "querySource": "typed_query",
    "product": "Latest",
})
features = json.dumps({
    "profile_label_improvements_pcf_label_in_post_enabled": False,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "communities_web_enable_tweet_community_results_fetch": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
})

url = (
    f"https://x.com/i/api/graphql/MJpyQGqgklrVl_6rYKQRow/SearchTimeline"
    f"?variables={urllib.parse.quote(variables)}"
    f"&features={urllib.parse.quote(features)}"
)
resp = requests.get(url, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    d = resp.json()
    instructions = (
        d.get("data", {})
        .get("search_by_raw_query", {})
        .get("search_timeline", {})
        .get("timeline", {})
        .get("instructions", [])
    )
    count = 0
    for inst in instructions:
        for entry in inst.get("entries", []):
            result = (
                entry.get("content", {})
                .get("itemContent", {})
                .get("tweet_results", {})
                .get("result", {})
            )
            legacy = result.get("legacy", {})
            user_legacy = (
                result.get("core", {})
                .get("user_results", {})
                .get("result", {})
                .get("legacy", {})
            )
            text = legacy.get("full_text", "")
            if text:
                count += 1
                screen_name = user_legacy.get("screen_name", "?")
                likes = legacy.get("favorite_count", 0)
                rts = legacy.get("retweet_count", 0)
                print(f"  @{screen_name} ({likes} likes, {rts} RTs): {text[:100]}...")
    print(f"Total tweets: {count}")
else:
    print(f"Error: {resp.text[:300]}")

# Test 2: Get user profile
print("\n=== Profile: @elikibasakis ===")
variables2 = json.dumps({"screen_name": "elikibasakis", "withSafetyModeUserFields": True})
features2 = json.dumps({
    "hidden_profile_subscriptions_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
})

url2 = (
    f"https://x.com/i/api/graphql/xc8f1g7BYqr6VTzTbvNlGw/UserByScreenName"
    f"?variables={urllib.parse.quote(variables2)}"
    f"&features={urllib.parse.quote(features2)}"
)
resp2 = requests.get(url2, headers=headers, timeout=15)
if resp2.status_code == 200:
    d2 = resp2.json()
    user = d2.get("data", {}).get("user", {}).get("result", {}).get("legacy", {})
    print(f"  Name: {user.get('name', '?')}")
    print(f"  Bio: {user.get('description', '')[:120]}")
    print(f"  Followers: {user.get('followers_count', 0):,}")
    print(f"  Following: {user.get('friends_count', 0):,}")
    print(f"  Tweets: {user.get('statuses_count', 0):,}")
else:
    print(f"  Error: {resp2.status_code}")
