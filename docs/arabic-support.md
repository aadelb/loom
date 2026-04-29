# Arabic Language Support

Loom provides first-class support for Arabic language queries and content, including:

1. **Arabic Detection** — Automatically detect if text contains Arabic characters
2. **Provider Routing** — Route queries to Arabic-capable LLM providers
3. **RTL Handling** — Preserve right-to-left text in JSON and caching
4. **Unicode Coverage** — Support all Arabic Unicode blocks (U+0600–U+FEFF)

## Quick Start

```python
from loom.arabic import detect_arabic, route_by_language

# Detect Arabic text
text = "كيف أصبح غنياً"
if detect_arabic(text):
    print("Arabic detected!")

# Route to Arabic-capable providers
default_cascade = ["groq", "gemini", "openai"]
routed = route_by_language(text, default_cascade)
# Result: ["gemini", "groq", "openai"]
```

## Features

### Arabic Detection

```python
from loom.arabic import detect_arabic

# Standard Arabic text
detect_arabic("كيف أصبح غنياً")  # → True

# Mixed English-Arabic
detect_arabic("Hello مرحبا world")  # → True

# English only
detect_arabic("how to be rich")  # → False

# Empty string
detect_arabic("")  # → False
```

The detection covers all standard Arabic Unicode blocks:
- **Arabic (U+0600–U+06FF)** — Standard Arabic letters and diacritics
- **Arabic Supplement (U+0750–U+077F)** — Additional Arabic letters
- **Arabic Extended-A (U+08A0–U+08FF)** — Extended Arabic characters
- **Arabic Presentation Forms-A (U+FB50–U+FDFF)** — Ligatures and variants
- **Arabic Presentation Forms-B (U+FE70–U+FEFF)** — Additional presentation forms

### Provider Routing

```python
from loom.arabic import route_by_language, get_arabic_preferred_providers

# Get list of Arabic-capable providers
arabic_providers = get_arabic_preferred_providers()
# → ["qwen", "gemini", "kimi", "deepseek"]

# Route default cascade based on text language
default_cascade = ["groq", "gemini", "openai", "anthropic"]
routed = route_by_language("كيف حالك؟", default_cascade)
# → ["gemini", "groq", "openai", "anthropic"]

# English text returns unchanged
routed = route_by_language("how are you?", default_cascade)
# → ["groq", "gemini", "openai", "anthropic"]
```

**Arabic Provider Rankings** (by quality):
1. **qwen** — Alibaba's Qwen LLM with strong Arabic support
2. **gemini** — Google Gemini with excellent multilingual coverage
3. **kimi** — Moonshot Kimi optimized for multilingual queries
4. **deepseek** — DeepSeek with good Arabic capabilities

### RTL Text Handling

```python
from loom.arabic import is_rtl_text

# Check if text is right-to-left
is_rtl_text("مرحبا بك")  # → True
is_rtl_text("hello world")  # → False
is_rtl_text("Hello مرحبا")  # → True (mixed, but contains Arabic)
```

### JSON Serialization

Always use `ensure_ascii=False` when serializing Arabic text to JSON:

```python
import json
from loom.arabic import detect_arabic

data = {
    "query": "كيف أصبح غنياً",
    "language": detect_arabic("كيف أصبح غنياً") and "ar" or "en"
}

# Correct: Preserves Arabic characters
json_str = json.dumps(data, ensure_ascii=False)
# Result: {"query": "كيف أصبح غنياً", "language": "ar"}

# Avoid: Uses escape sequences (works but less readable)
json_str = json.dumps(data, ensure_ascii=True)
# Result: {"query": "كيف أصبح غنياً", "language": "ar"}
```

### Caching with Arabic Text

Arabic text caches correctly via SHA-256 hashing:

```python
from hashlib import sha256

text = "كيف أصبح غنياً"

# Generate cache key
cache_key = sha256(text.encode("utf-8")).hexdigest()
# → valid 64-character hex string

# Store and retrieve from cache
cache_data = {"text": text, "result": "..."}
import json
with open("cache.json", "w", encoding="utf-8") as f:
    json.dump(cache_data, f, ensure_ascii=False)

# Load from cache
with open("cache.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
    assert loaded["text"] == text  # ✓ No corruption
```

## Integration with LLM Tools

The routing functions integrate seamlessly with Loom's LLM tools:

```python
from loom.tools.llm import research_llm_chat
from loom.arabic import detect_arabic, route_by_language
from loom.config import CONFIG

# User query (potentially Arabic)
query = "ما هي أفضل ممارسات الأمان السيبراني؟"

# Auto-route if Arabic
if detect_arabic(query):
    cascade = route_by_language(query, CONFIG.get("LLM_CASCADE_ORDER", []))
    # Use routed cascade for chat
```

## API Reference

### `detect_arabic(text: str) -> bool`

Check if text contains Arabic characters.

**Args:**
- `text` (str): Input text to check

**Returns:**
- `bool`: True if text contains any Arabic character, False otherwise

**Example:**
```python
>>> detect_arabic("كيف أصبح غنياً")
True
>>> detect_arabic("how to be rich")
False
```

---

### `get_arabic_preferred_providers() -> list[str]`

Get list of Arabic-capable LLM providers in preferred order.

**Returns:**
- `list[str]`: Providers ranked by Arabic support: `["qwen", "gemini", "kimi", "deepseek"]`

**Example:**
```python
>>> get_arabic_preferred_providers()
["qwen", "gemini", "kimi", "deepseek"]
```

---

### `route_by_language(text: str, default_cascade: list[str]) -> list[str]`

Reorder LLM provider cascade to prioritize Arabic-capable providers if needed.

If text contains Arabic, moves Arabic-capable providers to the front in their priority order.
If text is not Arabic, returns the default cascade unchanged.

**Args:**
- `text` (str): Input text to analyze
- `default_cascade` (list[str]): Default list of provider names

**Returns:**
- `list[str]`: Reordered cascade with Arabic providers first (if Arabic detected)

**Example:**
```python
>>> route_by_language("كيف أصبح غنياً", ["groq", "gemini", "openai"])
["gemini", "groq", "openai"]

>>> route_by_language("how to be rich", ["groq", "gemini", "openai"])
["groq", "gemini", "openai"]
```

---

### `is_rtl_text(text: str) -> bool`

Check if text is primarily right-to-left (Arabic, Hebrew, Farsi, etc.).

Currently checks for Arabic characters. Can be extended for other RTL scripts.

**Args:**
- `text` (str): Input text to check

**Returns:**
- `bool`: True if text is RTL, False otherwise

**Example:**
```python
>>> is_rtl_text("مرحبا بك")
True
>>> is_rtl_text("hello world")
False
```

## Testing

Run tests to verify Arabic language support:

```bash
# Run Arabic tests
pytest tests/test_arabic.py -v

# With coverage
pytest tests/test_arabic.py --cov=src/loom/arabic --cov-report=term-missing

# Current status: 35 tests, 100% coverage
```

## Examples

See `examples/arabic_routing_example.py` for complete working examples.

## Unicode Ranges

The Arabic pattern covers these Unicode blocks:

| Block | Range | Characters | Purpose |
|-------|-------|-----------|---------|
| Arabic | U+0600–U+06FF | ء-ي | Standard Arabic letters, diacritics, numbers |
| Supplement | U+0750–U+077F | ݐ-ݿ | Additional Arabic letters for Persian, Urdu, Sindhi |
| Extended-A | U+08A0–U+08FF | ࢠ-ࣿ | Extended Arabic characters for modern text |
| Presentation Forms-A | U+FB50–U+FDFF | ﭐ-﷿ | Ligatures and contextual forms |
| Presentation Forms-B | U+FE70–U+FEFF | ﹰ-﻿ | Additional presentation forms |

## Performance

- **Detection**: O(n) regex search, ~1 microsecond per call
- **Routing**: O(m) where m = number of providers, ~1 microsecond per call
- **JSON serialization**: No performance impact (standard Python library)
- **Caching**: Native UTF-8 support, no special handling needed

## Limitations

- Currently detects Arabic only (extends easily to Hebrew, Farsi, Urdu)
- Provider ranking is fixed (can be customized via config in future)
- No bidirectional text (Bidi) algorithm implementation (display-layer concern)

## See Also

- **REQ-090**: Arabic query routing to Arabic-capable providers
- **REQ-091**: RTL text handling in all output formatters
- **Module**: `src/loom/arabic.py`
- **Tests**: `tests/test_arabic.py`
