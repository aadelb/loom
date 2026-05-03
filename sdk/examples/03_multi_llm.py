"""Example 3: Query all LLM providers in parallel.

Sends a prompt to all configured LLM providers:
- Groq
- NVIDIA NIM
- DeepSeek
- Gemini
- Moonshot (Kimi)
- OpenAI
- Anthropic

Run the Loom server first:
    loom serve

Then run this example:
    python examples/03_multi_llm.py
"""

import asyncio
from loom_sdk import LoomClient


async def main():
    """Ask all LLMs a question."""
    async with LoomClient("http://127.0.0.1:8787") as client:
        prompt = "What are the biggest challenges in AI safety?"

        print(f"Sending prompt to all LLM providers...\n")
        print(f"Prompt: {prompt}\n")

        response = await client.ask_all_llms(
            prompt=prompt,
            max_tokens=200,
        )

        print(f"Providers queried: {response.providers_queried}")
        print(f"Providers responded: {response.providers_responded}")
        print(f"Providers refused: {response.providers_refused}")
        print(f"Fastest: {response.fastest_provider} ({response.fastest_latency_ms:.0f}ms)\n")

        for llm_response in response.responses:
            print(f"{'='*60}")
            print(f"Provider: {llm_response.provider}")
            print(f"Latency: {llm_response.latency_ms:.0f}ms")

            if llm_response.response:
                text = llm_response.response[:200]
                if len(llm_response.response) > 200:
                    text += "..."
                print(f"Response: {text}")
            elif llm_response.error:
                print(f"Error: {llm_response.error}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
