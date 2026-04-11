# OpenAI — Secondary LLM Provider

Use OpenAI's GPT models as a primary or fallback provider for Loom's LLM tools.

## Get an API Key

1. Visit https://platform.openai.com/account/api-keys
2. Click "Create new secret key"
3. Copy and save the key securely

## Set Environment Variable

Add to `.env` or shell:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Usually not needed
```

In a `.env` file:

```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

Verify setup:

```bash
python3 -c "import os; print('OpenAI key:', os.getenv('OPENAI_API_KEY'))"
```

## Available Models

| Model | Use Case | Input Cost | Output Cost |
|-------|----------|-----------|------------|
| gpt-5-mini | Fast, cheap | $0.30 / 1M | $1.20 / 1M |
| gpt-5 | Balanced | $1.50 / 1M | $6.00 / 1M |
| gpt-5-preview | Latest | $3.00 / 1M | $12.00 / 1M |
| gpt-4-turbo | High quality | $10 / 1M | $30 / 1M |

See https://openai.com/pricing/gpt-4-5 for current pricing.

## Usage Examples

### Default (Uses NIM First, Falls Back to OpenAI)

```python
result = research_llm_summarize(text="...")
# Tries NVIDIA NIM first; if fails, uses OpenAI
```

### Force OpenAI

```python
result = research_llm_summarize(
    text="...",
    provider_override="openai"
)
```

### Specify OpenAI Model

```python
result = research_llm_summarize(
    text="...",
    model="openai/gpt-5-mini"
)
```

### Use GPT-5 for High-Quality Output

```python
result = research_llm_extract(
    text="Technical paper...",
    schema={
        "title": "str",
        "authors": "list[str]",
        "methodology": "str",
    },
    model="openai/gpt-5"
)
```

## Cost Control

### Set Per-Call Budget

```python
# Will error if this call costs more than $0.10
result = research_llm_summarize(
    text="...",
    max_cost_usd=0.10,
    model="openai/gpt-5"
)
```

### Set Daily Budget

```python
# Stop all LLM calls once daily spend exceeds $5
loom config set LLM_DAILY_COST_CAP_USD 5.0

# Now all LLM calls check this budget
result = research_llm_summarize(text="...")
```

### Monitor Costs

Check your OpenAI usage:

1. Visit https://platform.openai.com/account/billing/overview
2. View costs by model and date
3. Set spending limits in "Billing" → "Usage limits"

## Configuration

Set OpenAI as default for certain tasks:

```bash
# Use GPT-5-mini for most tasks (cheap)
loom config set LLM_DEFAULT_CHAT_MODEL "openai/gpt-5-mini"

# Use GPT-5 for high-quality extraction
# (Note: would need custom per-task config; not yet supported)
```

Or in environment:

```bash
export LOOM_LLM_DEFAULT_CHAT_MODEL="openai/gpt-5-mini"
```

## Provider Cascade Configuration

Control the fallback order:

```bash
# Use OpenAI first, then fall back to NIM
loom config set LLM_CASCADE_ORDER '["openai", "nvidia", "anthropic", "vllm"]'
```

## Structured Output (JSON Schema)

OpenAI supports strict JSON response formatting:

```python
result = research_llm_chat(
    messages=[
        {
            "role": "user",
            "content": "Extract JSON from this document: ..."
        }
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "extraction_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "integer"},
                },
                "required": ["field1", "field2"],
            },
        },
    },
    model="openai/gpt-5"
)
```

## Troubleshooting

### "Invalid API key"

```bash
# Check key is set and correct format
echo $OPENAI_API_KEY

# Keys start with "sk-"
export OPENAI_API_KEY="sk-..."
```

### "Rate limit exceeded"

```python
# OpenAI has rate limits; wait and retry
import time
time.sleep(60)

# Or use NVIDIA NIM instead
result = research_llm_summarize(
    text="...",
    provider_override="nvidia"
)
```

### "Insufficient quota"

You've exceeded your monthly spending limit. Set a usage limit on OpenAI:

1. Visit https://platform.openai.com/account/billing/limits
2. Set "Hard limit" to a reasonable amount (e.g., $50/month)

### "Exceeds token limit"

```python
# Reduce max_tokens or split into smaller chunks
result = research_llm_summarize(
    text=text[:10000],  # Truncate
    max_tokens=200
)
```

## Cost Examples

Typical costs for Loom operations using GPT-5-mini:

| Operation | Input Tokens | Output Tokens | Cost |
|-----------|------------|--------------|------|
| Summarize 5KB page | 2,000 | 200 | ~$0.0015 |
| Extract structured data | 3,000 | 300 | ~$0.0018 |
| Translate Arabic ↔ English | 1,500 | 1,500 | ~$0.0018 |
| Deep research (3 sources) | 10,000 | 800 | ~$0.0063 |

Using GPT-5 (better quality):

| Operation | Input Tokens | Output Tokens | Cost |
|-----------|------------|--------------|------|
| Summarize 5KB page | 2,000 | 200 | ~$0.0045 |
| Extract structured data | 3,000 | 300 | ~$0.0051 |

## Advanced: Custom Base URL

If you're using an OpenAI-compatible service (e.g., Azure OpenAI):

```bash
export OPENAI_BASE_URL="https://your-endpoint.openai.azure.com/v1"
export OPENAI_API_KEY="your_key"
```

Or in code:

```python
# Set via environment before importing loom
import os
os.environ["OPENAI_BASE_URL"] = "https://..."
os.environ["OPENAI_API_KEY"] = "..."

result = research_llm_summarize(text="...")
```

## Related Documentation

- [docs/providers/nvidia-nim.md](nvidia-nim.md) — NVIDIA NIM setup
- [docs/providers/anthropic.md](anthropic.md) — Anthropic setup
- [docs/tools/research_llm.md](../tools/research_llm.md) — LLM tools reference
