#!/usr/bin/env python3
"""Example usage of the parameter auto-correction module.

Demonstrates how to use param_corrector to handle user input with
common parameter name mistakes and provide helpful correction messages.
"""

from __future__ import annotations

from loom.param_corrector import (
    auto_correct_params,
    format_correction_message,
    get_tool_params,
    suggest_param,
)


def example_1_simple_correction() -> None:
    """Example 1: Simple alias correction."""
    print("=" * 70)
    print("Example 1: Simple alias correction")
    print("=" * 70)

    user_params = {"max_results": 50}
    valid_params = ["limit", "offset", "query"]

    corrected, corrections = auto_correct_params(
        "search", user_params, valid_params
    )

    print(f"User provided: {user_params}")
    print(f"Corrected to:  {corrected}")
    print(f"Message: {format_correction_message(corrections)}")
    print()


def example_2_fuzzy_matching() -> None:
    """Example 2: Fuzzy matching for typos."""
    print("=" * 70)
    print("Example 2: Fuzzy matching for typos")
    print("=" * 70)

    # User made a typo: "query" became "quey"
    user_params = {"quey": "python", "limit": 25}
    valid_params = ["query", "limit", "offset"]

    corrected, corrections = auto_correct_params(
        "search", user_params, valid_params
    )

    print(f"User provided: {user_params}")
    print(f"Corrected to:  {corrected}")
    print(f"Message: {format_correction_message(corrections)}")
    print()


def example_3_multiple_corrections() -> None:
    """Example 3: Multiple parameter corrections."""
    print("=" * 70)
    print("Example 3: Multiple parameter corrections")
    print("=" * 70)

    user_params = {
        "max_results": 100,
        "target_language": "es",
        "search_query": "machine learning",
    }
    valid_params = ["limit", "target_lang", "query"]

    corrected, corrections = auto_correct_params(
        "search", user_params, valid_params
    )

    print(f"User provided: {user_params}")
    print(f"Corrected to:  {corrected}")
    print(f"Message:\n{format_correction_message(corrections)}")
    print()


def example_4_suggest_param() -> None:
    """Example 4: Getting suggestions for a single parameter."""
    print("=" * 70)
    print("Example 4: Getting suggestions for a single parameter")
    print("=" * 70)

    valid_params = ["limit", "offset", "query", "timeout"]

    # Check various inputs
    for user_input in ["limi", "ofset", "tim", "xyz"]:
        suggestion, confidence = suggest_param(user_input, valid_params)
        if suggestion:
            print(f"'{user_input}' → '{suggestion}' (confidence: {confidence:.0%})")
        else:
            print(f"'{user_input}' → no match (too dissimilar)")
    print()


def example_5_case_insensitive() -> None:
    """Example 5: Case-insensitive matching."""
    print("=" * 70)
    print("Example 5: Case-insensitive matching")
    print("=" * 70)

    user_params = {"QUERY": "python", "Limit": 50}
    valid_params = ["query", "limit", "offset"]

    corrected, corrections = auto_correct_params(
        "search", user_params, valid_params
    )

    print(f"User provided: {user_params}")
    print(f"Corrected to:  {corrected}")
    print(f"Message: {format_correction_message(corrections)}")
    print()


def example_6_preserves_values() -> None:
    """Example 6: Parameter values are preserved during correction."""
    print("=" * 70)
    print("Example 6: Parameter values are preserved during correction")
    print("=" * 70)

    complex_value = {
        "filters": ["python", "machine learning"],
        "boost": 1.5,
        "exclude": ["deprecated"],
    }
    user_params = {"max_results": complex_value}
    valid_params = ["limit"]

    corrected, corrections = auto_correct_params(
        "search", user_params, valid_params
    )

    print(f"Original value type: {type(user_params['max_results'])}")
    print(f"Corrected value type: {type(corrected['limit'])}")
    print(f"Values are identical: {corrected['limit'] == complex_value}")
    print()


def example_7_real_world_fetch_tool() -> None:
    """Example 7: Real-world scenario with fetch tool parameters."""
    print("=" * 70)
    print("Example 7: Real-world scenario with fetch tool parameters")
    print("=" * 70)

    # User trying to use fetch tool with common parameter mistakes
    user_params = {
        "query_text": "https://example.com",
        "max_chars": 20000,
        "wait_sec": 3,
        "javascript": True,
    }
    valid_params = ["query", "max_chars", "wait_time", "javascript_enabled"]

    corrected, corrections = auto_correct_params(
        "fetch", user_params, valid_params
    )

    print(f"User provided {len(user_params)} parameters:")
    for k, v in user_params.items():
        print(f"  - {k}: {v}")

    print(f"\nCorrected to {len(corrected)} parameters:")
    for k, v in corrected.items():
        print(f"  - {k}: {v}")

    if corrections:
        print(f"\nCorrections made:")
        for correction in corrections:
            print(f"  - {correction}")
    print()


def main() -> None:
    """Run all examples."""
    examples = [
        example_1_simple_correction,
        example_2_fuzzy_matching,
        example_3_multiple_corrections,
        example_4_suggest_param,
        example_5_case_insensitive,
        example_6_preserves_values,
        example_7_real_world_fetch_tool,
    ]

    for example in examples:
        example()

    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
