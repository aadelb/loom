# Loom SDK Quick Start

Get up and running with Loom SDK in 2 minutes.

## 1. Install

```bash
cd sdk
pip install -e .
```

## 2. Start Server

In another terminal:

```bash
loom serve
```

## 3. Use It

```python
import asyncio
from loom_sdk import LoomClient

async def main():
    async with LoomClient() as client:
        # Search
        results = await client.search("AI safety", n=5)
        print(f"Found {len(results.results)} results")
        
        # Deep research
        report = await client.deep("how transformers work")
        print(f"Summary: {report.summary}")
        
        # Multi-LLM
        responses = await client.ask_all_llms("What is AGI?")
        print(f"Fastest: {responses.fastest_provider}")

asyncio.run(main())
```

## API Cheat Sheet

| Method | Purpose | Example |
|--------|---------|---------|
| `search()` | Web search | `await client.search("topic", provider="exa", n=10)` |
| `fetch()` | Single URL | `await client.fetch("https://example.com")` |
| `spider()` | Bulk fetch | `await client.spider(["url1", "url2"])` |
| `deep()` | Full research | `await client.deep("research question")` |
| `ask_all_llms()` | Multi-LLM | `await client.ask_all_llms("question")` |
| `reframe()` | Prompt reframe | `await client.reframe("prompt", strategy="ethical")` |
| `list_tools()` | Tool discovery | `await client.list_tools()` |
| `health_check()` | Server status | `await client.health_check()` |

## Common Patterns

### Pattern 1: Search and Fetch
```python
results = await client.search("topic")
content = await client.fetch(results.results[0].url)
print(content.content)
```

### Pattern 2: Deep Research + LLM
```python
report = await client.deep("research query")
responses = await client.ask_all_llms(
    f"Based on this research: {report.summary}, what are implications?"
)
```

### Pattern 3: Bulk Content Extraction
```python
results = await client.spider(urls=["url1", "url2", "url3"])
for result in results.results:
    if result.content:
        process(result.content)
```

### Pattern 4: Prompt Reframing
```python
original = "dangerous prompt"
reframed = await client.reframe(original)
responses = await client.ask_all_llms(reframed.reframed_prompt)
```

## Troubleshooting

**Connection refused?**
```bash
loom serve  # Start server
```

**Import error?**
```bash
pip install -e .  # Reinstall
```

**Timeout?**
```python
client = LoomClient(timeout=600.0)  # Increase timeout
```

## Next Steps

1. Run examples: `python examples/01_basic_search.py`
2. Read [README.md](README.md)
3. Check [API Reference](README.md#api-reference)
4. Explore [Server Docs](../docs/)
