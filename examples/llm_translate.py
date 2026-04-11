#!/usr/bin/env python3
"""Demonstrates LLM-powered text translation via research_llm_translate.

Translates text to a target language using NVIDIA NIM or fallback LLM providers.
Supports arbitrary languages via natural language specification.

Requires:
- Loom server running on http://127.0.0.1:8787/mcp
- Python 3.11+ with `mcp` package installed
- NVIDIA NIM API credentials (for research_llm_translate)

Usage:
    # Translate to French
    python examples/llm_translate.py --text "Hello, world!" --to fr

    # Translate to Spanish
    python examples/llm_translate.py \\
      --text "The quick brown fox jumps over the lazy dog" \\
      --to es

    # Multi-sentence example
    python examples/llm_translate.py \\
      --text "Machine learning is transforming AI. Large language models are leading this change." \\
      --to de

    # Specify source language (optional)
    python examples/llm_translate.py \\
      --text "Bonjour le monde" \\
      --from fr \\
      --to en
"""
import argparse
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# Language code mappings
LANGUAGE_CODES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
}


async def main() -> int:
    parser = argparse.ArgumentParser(description="Translate text using Loom LLM")
    parser.add_argument(
        "--text",
        type=str,
        required=True,
        help="Text to translate",
    )
    parser.add_argument(
        "--to",
        type=str,
        required=True,
        help="Target language (code: en, es, fr, de, etc. or full name: English, Spanish, ...)",
    )
    parser.add_argument(
        "--from",
        type=str,
        dest="source_lang",
        default=None,
        help="Source language (optional; auto-detect if omitted)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="auto",
        help="LLM model to use (default: auto for fallback chain)",
    )

    args = parser.parse_args()

    # Normalize language names
    target_lang = args.to.lower()
    if target_lang not in LANGUAGE_CODES:
        # Check if it's a full name
        for code, name in LANGUAGE_CODES.items():
            if name.lower() == target_lang:
                target_lang = code
                break
        else:
            print(f"ERROR: unknown target language '{args.to}'")
            print(f"Supported: {', '.join(LANGUAGE_CODES.keys())}")
            return 1

    source_lang = None
    if args.source_lang:
        source_lang = args.source_lang.lower()
        if source_lang not in LANGUAGE_CODES:
            for code, name in LANGUAGE_CODES.items():
                if name.lower() == source_lang:
                    source_lang = code
                    break
            else:
                print(f"ERROR: unknown source language '{args.source_lang}'")
                return 1

    url = "http://127.0.0.1:8787/mcp"

    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                print("Translation Request")
                print("=" * 50)
                print(f"Source: {source_lang if source_lang else '(auto-detect)'}")
                print(f"Target: {LANGUAGE_CODES.get(target_lang, target_lang)}")
                print(f"Text: {args.text[:80]}{'...' if len(args.text) > 80 else ''}")
                print()

                # Call research_llm_translate
                print("Translating via NVIDIA NIM...")
                result = await session.call_tool(
                    "research_llm_translate",
                    {
                        "text": args.text,
                        "target_lang": target_lang,
                        "source_lang": source_lang,
                        "model": args.model,
                    },
                )

                body = result.content[0].text if result.content else ""

                if not body:
                    print("ERROR: empty response from translator")
                    return 1

                # Try to parse as JSON, fallback to plain text
                try:
                    response = json.loads(body)
                    if isinstance(response, dict):
                        translated = response.get("translation", response.get("text", ""))
                        if not translated:
                            print(f"Unexpected response format: {response}")
                            return 1
                    else:
                        translated = str(response)
                except json.JSONDecodeError:
                    # Plain text response
                    translated = body

                print("\nResult")
                print("=" * 50)
                print(f"Original: {args.text}")
                print()
                print(f"Translated ({LANGUAGE_CODES.get(target_lang, target_lang)}):")
                print(translated)

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
