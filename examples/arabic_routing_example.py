"""Example: Using Arabic language support for LLM provider routing.

This example demonstrates how to use the Arabic language detection and routing
features to automatically select the best LLM providers for Arabic queries.
"""

from loom.arabic import detect_arabic, route_by_language


def main() -> None:
    """Example usage of Arabic language routing."""

    # Example 1: Detect Arabic text
    print("=" * 70)
    print("EXAMPLE 1: Detecting Arabic text")
    print("=" * 70)

    texts = [
        "كيف أصبح غنياً",  # "How did I become rich?" in Arabic
        "how to be rich",  # English
        "Hello مرحبا world",  # Mixed English-Arabic
    ]

    for text in texts:
        is_arabic = detect_arabic(text)
        print(f"Text: {text!r}")
        print(f"  Is Arabic: {is_arabic}\n")

    # Example 2: Route LLM cascade for Arabic queries
    print("=" * 70)
    print("EXAMPLE 2: Provider routing based on language")
    print("=" * 70)

    # Default LLM cascade from config
    default_cascade = [
        "groq",
        "nvidia",
        "deepseek",
        "gemini",
        "moonshot",
        "openai",
        "anthropic",
        "vllm",
    ]

    queries = [
        ("كيف يمكنني تحسين مهاراتي البرمجية؟", "Arabic query"),
        ("How can I improve my programming skills?", "English query"),
        ("Tell me about تقنيات البرمجة", "Mixed language query"),
    ]

    for query, label in queries:
        routed = route_by_language(query, default_cascade)
        print(f"{label}: {query!r}")
        print(f"  Original cascade: {default_cascade[:3]}...")
        print(f"  Routed cascade:   {routed[:3]}...")
        print()

    # Example 3: Arabic text in caching and JSON
    print("=" * 70)
    print("EXAMPLE 3: Arabic text round-trip through JSON")
    print("=" * 70)

    import json

    data = {
        "query": "ما هي أفضل ممارسات الأمان السيبراني",
        "language": "ar",
        "detected_arabic": detect_arabic("ما هي أفضل ممارسات الأمان السيبراني"),
    }

    # Serialize with ensure_ascii=False to preserve Arabic
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    print("Serialized JSON (ensure_ascii=False):")
    print(json_str)

    # Deserialize to verify round-trip
    loaded = json.loads(json_str)
    print("\nRound-trip check:")
    print(f"  Original query: {data['query']!r}")
    print(f"  Loaded query:   {loaded['query']!r}")
    print(f"  Match: {data['query'] == loaded['query']}")


if __name__ == "__main__":
    main()
