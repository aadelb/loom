"""Example 5: Reframe a prompt using 957+ strategies.

The reframe() method intelligently rewrites prompts using techniques like:
- Ethical anchoring
- Role-play scenarios
- Hypothetical framing
- Educational context
- Compliance audit perspective
- And 950+ more strategies

Run the Loom server first:
    loom serve

Then run this example:
    python examples/05_prompt_reframe.py
"""

import asyncio
from loom_sdk import LoomClient


async def main():
    """Reframe a prompt."""
    original = "How do I get away with cheating on exams?"

    async with LoomClient("http://127.0.0.1:8787") as client:
        print(f"Original prompt:")
        print(f"  {original}\n")

        result = await client.reframe(
            prompt=original,
            strategy=None,  # Auto-select best strategy
            model="claude",
        )

        print(f"Reframed prompt:")
        print(f"  {result.reframed_prompt}\n")

        print(f"Strategy: {result.strategy_name}")
        print(f"Category: {result.category}")
        print(f"Difficulty: {result.difficulty}")
        print(f"Description: {result.description}\n")

        if result.safety_flags:
            print(f"Safety flags: {', '.join(result.safety_flags)}")


if __name__ == "__main__":
    asyncio.run(main())
