# NVIDIA NIM — Free LLM Provider Setup

Loom uses NVIDIA NIM as the default LLM provider (free tier with 12 parallel requests). This guide explains setup and model selection.

## What is NVIDIA NIM?

NVIDIA's Neural Inference Microservices (NIM) provide free access to several high-quality models:

- **Kimi K2 Instruct** — Strong multilingual performance (English, Arabic, Chinese, etc.)
- **Deepseek V3.2** — Reasoning and coding
- **Llama 4 Maverick** — General-purpose, good balance
- **Qwen 3.5 Coder** — Code generation and technical tasks
- **Mistral Large 3** — Fast, high quality

Free tier: 12 concurrent requests, shared with other users.

## Get an API Key

1. Visit https://api.nvidia.com/
2. Sign in with your NVIDIA or Google account
3. Generate an API key
4. Copy the key

## Set Environment Variable

Add to your `.env` file or shell environment:

```bash
export NVIDIA_NIM_API_KEY="your_api_key_here"
export NVIDIA_NIM_ENDPOINT="https://integrate.api.nvidia.com/v1"
```

Or in a `.env` file in your project directory:

```bash
NVIDIA_NIM_API_KEY=your_api_key_here
NVIDIA_NIM_ENDPOINT=https://integrate.api.nvidia.com/v1
```

Verify setup:

```bash
python3 -c "import os; print('NIM key:', os.getenv('NVIDIA_NIM_API_KEY'))"
```

## Available Models

| Model | ID | Best For | Speed | Quality |
|-------|----|-----------|----|---------|
| Kimi K2 Instruct | `nvidia/kimi-k2-instruct-v2` | Multilingual, General | Fast | High |
| Deepseek V3.2 | `nvidia/deepseek-v3.2` | Reasoning, Coding | Medium | Very High |
| Llama 4 Maverick | `nvidia/meta/llama-4-maverick-17b-128e-instruct` | General | Fast | Good |
| Qwen 3.5 Coder | `nvidia/qwen3.5-coder-480b` | Code | Fast | High |
| Mistral Large 3 | `nvidia/nvidia/mistral-large-3-instruct` | General | Very Fast | Good |

## Usage Examples

### Default Model (Auto-Selected)

```python
# Uses first available model in cascade (NIM first)
result = research_llm_summarize(text="...", max_tokens=200)
```

### Explicit Model Selection

```python
# Use Kimi K2 for multilingual support
result = research_llm_summarize(
    text="...",
    model="nvidia/kimi-k2-instruct-v2"
)

# Use Deepseek for reasoning
result = research_llm_summarize(
    text="...",
    model="nvidia/deepseek-v3.2"
)
```

### Force NIM Provider

```python
# Even if OpenAI key is set, use NIM
result = research_llm_summarize(
    text="...",
    provider_override="nvidia"
)
```

## Configuration

Set default NIM models in config:

```bash
# Use Kimi K2 as default for summarization
loom config set LLM_DEFAULT_CHAT_MODEL "nvidia/kimi-k2-instruct-v2"

# Use Kimi K2 for translation (strong multilingual support)
loom config set LLM_DEFAULT_TRANSLATE_MODEL "nvidia/kimi-k2-instruct-v2"
```

Or in environment:

```bash
export LOOM_LLM_DEFAULT_CHAT_MODEL="nvidia/kimi-k2-instruct-v2"
export LOOM_LLM_DEFAULT_TRANSLATE_MODEL="nvidia/kimi-k2-instruct-v2"
```

## Multilingual Support

Kimi K2 is excellent for Arabic and other languages:

```python
# Arabic summarization
result = research_llm_summarize(
    text="نص عربي طويل...",
    language="ar",
    model="nvidia/kimi-k2-instruct-v2"
)

# Arabic to English translation
result = research_llm_translate(
    text="مرحبا بك في عالم نماذج اللغات",
    target_lang="en",
    model="nvidia/kimi-k2-instruct-v2"
)
```

## Rate Limits and Best Practices

Free tier limits:
- **Concurrency**: 12 parallel requests
- **Rate**: ~1 request per second per API key
- **Quota**: Varies; check your NVIDIA dashboard

Best practices:

1. **Reuse sessions** — Don't open new sessions for every request
2. **Batch requests** — Use `research_spider` for concurrent fetches
3. **Monitor costs** — Set `max_cost_usd` on expensive calls
4. **Use fallback** — OpenAI configured as fallback for spikes

Example with monitoring:

```python
import time

start = time.time()
result = research_llm_summarize(
    text="...",
    max_cost_usd=0.01  # Stop if over $0.01
)
latency_ms = (time.time() - start) * 1000

print(f"Latency: {latency_ms:.0f}ms")
print(f"Cost: ${result['cost_usd']:.4f}")
print(f"Tokens: {result['tokens']['input']} input, {result['tokens']['output']} output")
```

## Fallback to OpenAI

If NIM is rate-limited or unavailable, Loom automatically tries OpenAI:

```bash
# Set OpenAI key as fallback
export OPENAI_API_KEY="sk-..."
```

The cascade is:

1. NVIDIA NIM (free)
2. OpenAI (paid)
3. Anthropic (if configured)
4. Local vLLM (if running)

## Cost Tracking

Track your NVIDIA NIM usage:

```python
# Get daily cost from Loom
result = research_config_get("LLM_DAILY_COST_CAP_USD")

# Or check the LLM cost tracking tool (if available)
# stats = research_llm_usage_today()
```

Or on NVIDIA's website:

1. Visit https://api.nvidia.com/
2. Click "Usage" or "Billing" (location varies)
3. View your API call statistics

## Troubleshooting

### "No API key found"

```bash
# Check env var
echo $NVIDIA_NIM_API_KEY

# Or set it
export NVIDIA_NIM_API_KEY="your_key"
loom serve
```

### "Rate limit exceeded"

```python
# Use OpenAI instead
result = research_llm_summarize(
    text="...",
    provider_override="openai"
)
```

Or wait a minute and retry.

### "Connection refused"

Check that NVIDIA NIM endpoint is accessible:

```bash
curl -H "Authorization: Bearer $NVIDIA_NIM_API_KEY" \
  https://integrate.api.nvidia.com/v1/models
```

## Advanced: Custom NIM Endpoint

If you're running a private NVIDIA NIM server:

```bash
export NVIDIA_NIM_ENDPOINT="http://your-nim-server.com:8000/v1"
export NVIDIA_NIM_API_KEY="your_key"
```

Or set in code:

```python
result = research_llm_summarize(
    text="...",
    # This uses environment variables by default
    model="nvidia/custom-model"
)
```

## Related Documentation

- [docs/providers/openai.md](openai.md) — OpenAI setup
- [docs/providers/anthropic.md](anthropic.md) — Anthropic setup
- [docs/tools/research_llm.md](../tools/research_llm.md) — LLM tools reference
