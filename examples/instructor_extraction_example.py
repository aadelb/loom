"""Example usage of research_structured_extract with instructor integration.

This example demonstrates how to use the instructor-backed structured extraction
tool to extract validated, type-safe data from unstructured text.
"""

import asyncio
import json

from loom.tools.instructor_backend import research_structured_extract


async def example_basic_extraction() -> None:
    """Basic extraction: person name and age."""
    print("=== Example 1: Basic Person Extraction ===\n")

    text = """
    John Smith is a 35-year-old software engineer from California.
    He has been working in the tech industry for over 10 years.
    """

    schema = {
        "name": "str",
        "age": "int",
        "occupation": "str",
        "location": "str",
    }

    print(f"Input text:\n{text}\n")
    print(f"Schema: {schema}\n")

    result = await research_structured_extract(
        text=text,
        output_schema=schema,
        model="auto",
        max_retries=2,
    )

    print(f"Result:\n{json.dumps(result, indent=2, default=str)}\n")


async def example_complex_extraction() -> None:
    """Complex extraction: product with structured metadata."""
    print("=== Example 2: Product Extraction ===\n")

    text = """
    MacBook Pro 16-inch (2024)
    Price: $2,499.99
    Available in silver, space black, and gold
    Features: Apple M4 Pro chip, 512GB SSD, 16GB RAM
    In stock: 25 units
    Rating: 4.8 out of 5 stars
    """

    schema = {
        "product_name": "str",
        "price": "float",
        "storage_gb": "int",
        "ram_gb": "int",
        "colors": "list",
        "in_stock": "int",
        "rating": "float",
    }

    print(f"Input text:\n{text}\n")
    print(f"Schema: {schema}\n")

    result = await research_structured_extract(
        text=text,
        output_schema=schema,
        model="auto",
        max_retries=3,
    )

    print(f"Result:\n{json.dumps(result, indent=2, default=str)}\n")


async def example_with_fallback() -> None:
    """Extraction with fallback demonstration.

    Shows how the tool falls back to research_llm_extract if instructor is
    not installed.
    """
    print("=== Example 3: Extraction with Automatic Fallback ===\n")

    text = """
    Meeting on 2025-05-15 from 2:00 PM to 3:30 PM
    Location: Conference Room B
    Attendees: Alice (organizer), Bob, Carol, David
    Topic: Q2 Planning Review
    """

    schema = {
        "date": "str",
        "start_time": "str",
        "end_time": "str",
        "location": "str",
        "attendee_count": "int",
        "topic": "str",
    }

    print(f"Input text:\n{text}\n")
    print(f"Schema: {schema}\n")

    result = await research_structured_extract(
        text=text,
        output_schema=schema,
        max_retries=2,
    )

    instructor_used = result.get("instructor_used", False)
    method = "instructor" if instructor_used else "fallback (research_llm_extract)"
    print(f"Extraction method used: {method}\n")
    print(f"Result:\n{json.dumps(result, indent=2, default=str)}\n")


async def example_provider_override() -> None:
    """Extraction with specific provider override."""
    print("=== Example 4: Provider Override ===\n")

    text = """
    Jane Doe purchased an iPhone 15 Pro for $999.99 on May 1, 2025.
    Order #: INV-2025-001
    Delivery expected in 3-5 business days.
    """

    schema = {
        "buyer": "str",
        "product": "str",
        "price": "float",
        "order_id": "str",
        "delivery_days": "int",
    }

    print(f"Input text:\n{text}\n")
    print(f"Schema: {schema}\n")
    print("Provider override: openai\n")

    result = await research_structured_extract(
        text=text,
        output_schema=schema,
        model="auto",
        provider_override="openai",
        max_retries=2,
    )

    print(f"Result:\n{json.dumps(result, indent=2, default=str)}\n")


async def example_error_handling() -> None:
    """Error handling: demonstrate invalid input handling."""
    print("=== Example 5: Error Handling ===\n")

    text = "Some sample text"

    # Invalid schema: empty
    schema_invalid = {}

    print(f"Input text: {text}")
    print(f"Invalid schema (empty): {schema_invalid}\n")

    result = await research_structured_extract(
        text=text,
        output_schema=schema_invalid,
    )

    if "error" in result:
        print(f"✓ Error correctly caught: {result['error']}\n")
    else:
        print(f"Result: {json.dumps(result, indent=2, default=str)}\n")

    # Invalid schema: unknown type
    schema_badtype = {"name": "str", "unknown_field": "badtype"}

    print(f"Invalid schema (bad type): {schema_badtype}\n")

    result = await research_structured_extract(
        text=text,
        output_schema=schema_badtype,
    )

    if "error" in result:
        print(f"✓ Error correctly caught: {result['error']}\n")
    else:
        print(f"Result: {json.dumps(result, indent=2, default=str)}\n")


async def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 70)
    print("INSTRUCTOR INTEGRATION EXAMPLES")
    print("=" * 70 + "\n")

    try:
        await example_basic_extraction()
        await example_complex_extraction()
        await example_with_fallback()
        await example_provider_override()
        await example_error_handling()

        print("=" * 70)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
