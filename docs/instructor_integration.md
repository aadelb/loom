# Instructor Integration: Guaranteed Structured Extraction

## Overview

`research_structured_extract` is a Loom tool that provides **guaranteed structured outputs** from LLMs using the [instructor](https://github.com/jxnl/instructor) library. It automatically validates extracted data against a Pydantic schema and retries on validation failure.

If the instructor library is not installed, the tool gracefully falls back to `research_llm_extract`.

## Features

- **Guaranteed Schema Compliance**: Pydantic-validated outputs with automatic retry
- **Multi-Type Support**: str, int, float, bool, list, dict
- **Automatic Retry**: Configurable retries on validation failure (1-10)
- **Provider Selection**: Cascade through 8 LLM providers or override a specific one
- **Fallback Mode**: Seamless fallback to research_llm_extract if instructor unavailable
- **Comprehensive Error Handling**: Clear error messages with sanitized secrets
- **Type Safety**: Strict mode validation on all parameters

## Installation

Install instructor with the instructor extras:

```bash
pip install instructor>=0.30.0
```

The tool works without instructor installed (falls back to research_llm_extract), but for guaranteed validation you must install instructor.

## API

### Tool Name
`research_structured_extract`

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | required | Input text to extract from (1-100,000 chars) |
| `output_schema` | dict[str, str] | required | Field definitions: {"field": "type"} |
| `model` | str | "auto" | LLM model ("auto" for cascade) |
| `max_retries` | int | 3 | Max validation retries (1-10) |
| `provider_override` | str | None | Force a provider: nvidia, openai, anthropic, groq, deepseek, gemini, moonshot, vllm |

### Response

```python
{
    "extracted_data": {...},           # Validated dict with extracted fields
    "model": "gpt-4-turbo",            # Model identifier used
    "provider": "openai",               # Provider name (openai, nvidia, etc.)
    "cost_usd": 0.00523,               # Estimated USD cost
    "retries_needed": 1,               # Number of validation retries performed
    "validation_passed": True,         # Always True on success
    "instructor_used": True,           # True if instructor was used, False if fallback
    "error": None,                     # None on success, error message on failure
}
```

### Supported Types

| Type String | Python Type | Example |
|-------------|------------|---------|
| "str", "string" | str | "Alice", "hello" |
| "int", "integer" | int | 42, -5 |
| "float" | float | 3.14, 2.5 |
| "bool", "boolean" | bool | True, False |
| "list" | list | ["a", "b", "c"] |
| "dict", "object" | dict | {"key": "value"} |

## Examples

### Basic Extraction

Extract person data from text:

```python
import asyncio
from loom.tools.instructor_backend import research_structured_extract

async def extract_person():
    text = "Alice Smith is 30 years old and works in New York."
    
    result = await research_structured_extract(
        text=text,
        output_schema={
            "name": "str",
            "age": "int",
            "city": "str",
        }
    )
    
    print(result["extracted_data"])
    # Output: {"name": "Alice Smith", "age": 30, "city": "New York"}

asyncio.run(extract_person())
```

### Complex Extraction with Multiple Types

Extract product information with various data types:

```python
result = await research_structured_extract(
    text="""
        iPhone 15 Pro - $999.99
        Storage: 256GB
        Available in silver, black, gold (3 colors)
        In stock: 50 units
        Rating: 4.8 stars
    """,
    output_schema={
        "product": "str",
        "price": "float",
        "storage_gb": "int",
        "colors": "list",
        "in_stock": "int",
        "rating": "float",
    }
)

data = result["extracted_data"]
assert data["product"] == "iPhone 15 Pro"
assert data["price"] == 999.99
assert data["in_stock"] == 50
```

### Provider Override

Force extraction with a specific provider:

```python
result = await research_structured_extract(
    text="Jane is 25 years old.",
    output_schema={"name": "str", "age": "int"},
    provider_override="anthropic",  # Use Claude instead of default cascade
    model="claude-opus-4-6",
)
```

### Retry Configuration

Control validation retry behavior:

```python
result = await research_structured_extract(
    text=text,
    output_schema=schema,
    max_retries=5,  # Retry up to 5 times on validation failure
)

print(f"Retries needed: {result['retries_needed']}")
```

### Error Handling

Handle validation failures gracefully:

```python
result = await research_structured_extract(
    text="Some text",
    output_schema={},  # Invalid: empty schema
)

if "error" in result:
    print(f"Extraction failed: {result['error']}")
else:
    print(f"Extracted: {result['extracted_data']}")
```

## How It Works

### With Instructor Installed

1. **Schema Validation**: Output schema is validated early (field names, type names)
2. **LLM Call**: Text is sent to LLM with cascade fallback (or specific provider)
3. **Pydantic Model Creation**: Dynamic Pydantic model generated from schema
4. **Client Patching**: LLM client is patched with instructor
5. **Structured Call**: LLM is called with response_model constraint
6. **Validation**: Response is validated against Pydantic schema
7. **Retry**: On validation failure, instructor retries with feedback (up to max_retries)
8. **Return**: Validated dict returned on success

### Without Instructor Installed

If instructor is not available:

1. Tool logs a debug message about fallback
2. `research_llm_extract` is called instead
3. Result is normalized to match instructor response format
4. `instructor_used` is set to False
5. Response returned with `validation_passed=True` (best-effort)

### Cascade Providers

Default cascade order (configurable via `LLM_CASCADE_ORDER` in config):

1. **NVIDIA NIM** (free tier, fastest)
2. **OpenAI** (most reliable)
3. **Anthropic** (Claude models)
4. **Groq** (low-cost)
5. **DeepSeek** (capable reasoning)
6. **Google Gemini** (multimodal)
7. **Moonshot (Kimi)** (Chinese-optimized)
8. **vLLM Local** (self-hosted)

## Configuration

### Environment Variables

```bash
# LLM Providers
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GROQ_API_KEY="gsk_..."
export DEEPSEEK_API_KEY="sk-..."
export GOOGLE_AI_KEY="AIzaSy..."
export MOONSHOT_API_KEY="sk-..."
export NVIDIA_NIM_API_KEY="nvapi-..."

# Cost Limits
export LLM_DAILY_COST_CAP_USD="10.0"
export LLM_MAX_PARALLEL="12"

# Provider Cascade Order
export LLM_CASCADE_ORDER='["nvidia","openai","anthropic","vllm"]'
```

### Config File (~/.loom/config.json)

```json
{
    "LLM_CASCADE_ORDER": ["nvidia", "openai", "anthropic"],
    "LLM_DEFAULT_CHAT_MODEL": "gpt-4o",
    "LLM_DAILY_COST_CAP_USD": 10.0,
    "LLM_MAX_PARALLEL": 12
}
```

## Cost Estimation

Costs vary by provider and model:

| Provider | Model | Cost |
|----------|-------|------|
| NVIDIA NIM | Free tier | $0.00 |
| OpenAI | gpt-4o mini | ~$0.003-0.006 per call |
| Anthropic | Claude 3.5 Sonnet | ~$0.003-0.015 per call |
| Groq | mixtral-8x7b | Very low (~$0.0001) |
| Local vLLM | Self-hosted | $0.00 |

The `cost_usd` field in the response shows the actual cost for that call.

## Error Handling

### Common Errors

**ValueError: output_schema cannot be empty**
- Ensure schema dict has at least one field
- Example: `{"name": "str"}` not `{}`

**ValueError: invalid type 'badtype'**
- Check field type names are valid
- Valid: str, int, float, bool, list, dict
- Invalid: badtype, string (use str), number (use int/float)

**RuntimeError: all providers failed**
- Check API keys are set and valid
- Check network connectivity
- Verify LLM_CASCADE_ORDER is correct

**RuntimeError: structured extraction failed after N retries**
- LLM couldn't generate valid structured output
- Try increasing max_retries
- Try simpler schema with fewer fields
- Check text is clear and unambiguous

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("loom.instructor")
logger.setLevel(logging.DEBUG)
```

This will show:
- Which providers are being tried
- Validation failures and retry attempts
- Fallback to research_llm_extract (if instructor unavailable)

## Performance Tips

1. **Limit Fields**: Keep schema to 10-20 fields max (better validation)
2. **Be Specific**: Use clear, unambiguous field names
3. **Clear Text**: Provide clean, well-formatted input text
4. **Provider Selection**: NVIDIA NIM is free and fastest for extraction
5. **Batch Processing**: For multiple extractions, reuse provider instances

## Advanced Usage

### Custom Type Mapping

The tool supports a fixed set of types for schema validation. If you need custom types:

1. Use "dict" or "object" for complex nested structures
2. Call `model_dump()` on the result to serialize

```python
result = await research_structured_extract(
    text="...",
    output_schema={
        "simple_field": "str",
        "complex_data": "dict",  # Nested structure
    }
)
# complex_data will be a dict that can be parsed further
```

### Combining with Other Tools

Extract text from a webpage, then structure it:

```python
# First: fetch and extract text
from loom.tools.fetch import research_fetch

page = await research_fetch("https://example.com/article")

# Then: structure the extracted content
result = await research_structured_extract(
    text=page,
    output_schema={"title": "str", "author": "str", "date": "str"}
)
```

### Integration with LLM Tools

Use alongside other LLM tools:

```python
from loom.tools.llm import research_llm_summarize

# Summarize first
summary = await research_llm_summarize(text, max_words=200)

# Then structure the summary
result = await research_structured_extract(
    text=summary["summary"],
    output_schema={...}
)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tool always falls back to research_llm_extract | Install instructor: `pip install instructor` |
| "all providers failed" error | Check API keys in environment; test network connectivity |
| Validation keeps failing | Simplify schema; provide clearer input text |
| High costs | Use NVIDIA NIM (free) or Groq; reduce max_retries |
| Slow extraction | Use NVIDIA NIM provider instead of OpenAI cascade |

## References

- **Instructor GitHub**: https://github.com/jxnl/instructor
- **Instructor Docs**: https://python.useinstructor.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Loom Architecture**: See `docs/architecture.md`
- **LLM Providers**: See `docs/api-keys.md`

## License

Instructor integration is part of Loom, which is licensed under the same license as the Loom project.
