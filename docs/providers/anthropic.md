# Anthropic (Optional) — Claude Models

Use Anthropic's Claude models as an optional LLM provider in Loom. Requires separate installation.

## Installation

Loom doesn't install Anthropic by default. To add support:

```bash
pip install loom-mcp[anthropic]
```

Or install separately:

```bash
pip install anthropic>=0.40
```

## Get an API Key

1. Visit https://console.anthropic.com/
2. Go to "API Keys"
3. Create a new key
4. Copy and save securely

## Set Environment Variable

Add to `.env` or shell:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

In a `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Verify setup:

```bash
python3 -c "import os; print('Anthropic key:', os.getenv('ANTHROPIC_API_KEY'))"
```

## Available Models

| Model | Capabilities | Max Tokens | Cost |
|-------|--------------|-----------|------|
| claude-opus-4-6 | Best reasoning, coding | 200K | High |
| claude-sonnet-4-6 | Balanced quality/speed | 200K | Medium |
| claude-haiku-4-5 | Fast, lightweight | 100K | Low |

## Usage Examples

### Force Anthropic Provider

```python
result = research_llm_summarize(
    text="...",
    provider_override="anthropic"
)
```

### Specify Anthropic Model

```python
result = research_llm_summarize(
    text="...",
    model="anthropic/claude-opus-4-6"
)
```

### Use Opus for Complex Reasoning

```python
result = research_llm_extract(
    text="Complex technical document...",
    schema={
        "abstract": "str",
        "methodology": "str",
        "findings": "list[str]",
        "implications": "str",
    },
    model="anthropic/claude-opus-4-6"
)
```

### Use Haiku for Speed and Cost

```python
result = research_llm_summarize(
    text="...",
    max_tokens=200,
    model="anthropic/claude-haiku-4-5"
)
```

## Provider Cascade with Anthropic

By default, the cascade is:

1. NVIDIA NIM (free)
2. OpenAI (paid)
3. Anthropic (optional, paid)
4. Local vLLM (optional)

Once you set `ANTHROPIC_API_KEY`, Anthropic becomes available as a fallback:

```python
# Will try NIM → OpenAI → Anthropic → vLLM
result = research_llm_summarize(text="...")
```

Force Anthropic before others:

```bash
loom config set LLM_CASCADE_ORDER '["anthropic", "openai", "nvidia", "vllm"]'
```

## Cost Management

### Per-Call Budget

```python
result = research_llm_summarize(
    text="...",
    max_cost_usd=0.05,  # Stop if exceeds $0.05
    model="anthropic/claude-sonnet-4-6"
)
```

### Daily Budget

```bash
loom config set LLM_DAILY_COST_CAP_USD 10.0
```

### Check Your Costs

1. Visit https://console.anthropic.com/
2. Go to "Billing" → "Usage"
3. View costs by model and date

## Context Window

Claude models have large context windows (good for long texts):

| Model | Context | Max Output |
|-------|---------|-----------|
| Opus | 200K tokens | 4096 |
| Sonnet | 200K tokens | 4096 |
| Haiku | 100K tokens | 4096 |

Use this for long document summarization:

```python
# Summarize a very long document
with open("long_document.txt") as f:
    text = f.read()

result = research_llm_summarize(
    text=text,  # Can be very long (up to 200K tokens)
    max_tokens=500,
    model="anthropic/claude-opus-4-6"
)
```

## Extended Thinking (Optional)

Claude Opus supports extended thinking for deep reasoning:

```python
# Use extended thinking for complex analysis
result = research_llm_chat(
    messages=[
        {
            "role": "user",
            "content": "Analyze the implications of prompt injection attacks on AI safety..."
        }
    ],
    model="anthropic/claude-opus-4-6",
    # Note: extended thinking requires special config (not yet exposed in Loom)
)
```

## Troubleshooting

### "Anthropic not installed"

```bash
pip install loom-mcp[anthropic]
```

### "Invalid API key"

```bash
# Check key format
echo $ANTHROPIC_API_KEY
# Should start with "sk-ant-"

# Set it
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Overloaded" error

Anthropic's API is temporarily overloaded. Wait and retry, or use a different provider:

```python
result = research_llm_summarize(
    text="...",
    provider_override="openai"  # Fall back to OpenAI
)
```

### Too many tokens

Reduce the input or output:

```python
# Truncate input
result = research_llm_summarize(
    text=text[:50000],  # First 50K chars
    max_tokens=200,
    model="anthropic/claude-sonnet-4-6"  # Smaller model
)
```

## Cost Examples

Using Claude models with Loom:

| Operation | Input Tokens | Output Tokens | Haiku Cost | Sonnet Cost | Opus Cost |
|-----------|------------|--------------|-----------|-----------|----------|
| Summarize 5KB | 2,000 | 200 | ~$0.0004 | ~$0.0009 | ~$0.0015 |
| Extract data | 3,000 | 300 | ~$0.0006 | ~$0.0014 | ~$0.0023 |
| Long document | 50,000 | 500 | ~$0.008 | ~$0.017 | ~$0.028 |

Haiku is cheapest; Opus is best quality.

## When to Use Anthropic

- **You already pay for Anthropic** — Use Claude for consistency
- **Long documents** — Large context window (200K)
- **Complex reasoning** — Opus is excellent for tough problems
- **Extended thinking** — Opus can reason through problems step-by-step
- **Fallback** — Good backup if NIM and OpenAI are overloaded

## Related Documentation

- [docs/providers/nvidia-nim.md](nvidia-nim.md) — NVIDIA NIM setup
- [docs/providers/openai.md](openai.md) — OpenAI setup
- [docs/providers/local-vllm.md](local-vllm.md) — Local vLLM setup
- [docs/tools/research_llm.md](../tools/research_llm.md) — LLM tools reference
