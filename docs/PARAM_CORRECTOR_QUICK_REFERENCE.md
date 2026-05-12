# Parameter Corrector - Quick Reference

## Import
```python
from loom.param_corrector import (
    auto_correct_params,
    format_correction_message,
    get_tool_params,
    suggest_param,
)
```

## Common Pattern

```python
# Step 1: Auto-correct user parameters
corrected, corrections = auto_correct_params(
    tool_name="search",
    user_params={"max_results": 50, "search_query": "python"},
    valid_params=["limit", "query"]
)

# Step 2: Format message for user (optional)
if corrections:
    print(format_correction_message(corrections))

# Step 3: Use corrected parameters
result = search_tool(**corrected)
```

## One-Liners

### Get a suggestion for a misspelled param
```python
suggestion, confidence = suggest_param("quey", ["query", "limit"])
# ('query', 0.89)
```

### Auto-correct with known valid params
```python
corrected, msgs = auto_correct_params("fetch", {"max_result": 100}, ["limit"])
# ({'limit': 100}, ["'max_result' → 'limit' (similarity: 91%)"])
```

### Format corrections for display
```python
msg = format_correction_message(["'max_results' → 'limit'"])
# "Auto-corrected parameter: 'max_results' → 'limit'"
```

### Get tool parameters dynamically
```python
params = get_tool_params("fetch")
# ["query", "max_chars", "wait_time", ...]
```

## Common Correction Examples

| User Input | Correct | Why |
|-----------|---------|-----|
| `max_results` | `limit` | Known alias |
| `search_query` | `query` | Known alias |
| `quey` | `query` | 89% fuzzy match |
| `QUERY` | `query` | Case normalization |
| `timeout_sec` | `timeout` | Known alias |
| `javascript` | `javascript_enabled` | Known alias |

## Error Handling Strategy

```python
from pydantic import ValidationError

try:
    # Try direct validation first
    params = FetchParams(**user_input)
except ValidationError as e:
    # If fails, try auto-correction
    corrected, corrections = auto_correct_params("fetch", user_input)
    
    if corrections:
        print(f"Note: {format_correction_message(corrections)}")
        params = FetchParams(**corrected)
    else:
        raise  # No fixes possible, re-raise original error
```

## Built-in Aliases (20+)

| Alias → Correct |
|-----------------|
| max_results → limit |
| num_results → n |
| search_query → query |
| query_text → query |
| keywords → query |
| url_list → urls |
| target_language → target_lang |
| target_model → model_name |
| max_tokens_output → max_tokens |
| timeout_sec → timeout |
| wait_sec → wait_time |
| javascript → javascript_enabled |
| output_format → format |
| include_metadata → metadata |
| num_workers → workers |

## Confidence Threshold

Default: 0.6 (60%)

```python
# More strict (90% match required)
suggestion, conf = suggest_param("quey", ["query"], confidence_threshold=0.9)
# (None, 0.0) - too lenient

# More lenient (40% match required)
suggestion, conf = suggest_param("xyz", ["query"], confidence_threshold=0.4)
# Might match unhelpful suggestions
```

## Testing

Run tests:
```bash
pytest tests/test_param_corrector.py -v
```

Run specific test:
```bash
pytest tests/test_param_corrector.py::TestAutoCorrectParams::test_single_alias_correction -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Correction not happening | Check if alias exists in COMMON_ALIASES, or if fuzzy match meets 0.6 threshold |
| Tool params not found | Provide valid_params explicitly instead of using auto-discovery |
| Value changed | Values are never changed, only keys. Check if you're looking at the right param |
| False correction | Confidence threshold can be adjusted per call |

## Performance

- Corrections: <1ms per call
- Memory: ~1 KB for module
- Scaling: O(n) where n = valid parameters (typically 5-50)

## Integration Example

```python
# In your tool wrapper
def call_research_tool(tool_name: str, **kwargs):
    from loom.param_corrector import auto_correct_params, format_correction_message
    
    # Auto-correct parameters
    corrected, corrections = auto_correct_params(tool_name, kwargs)
    
    # Log corrections if any
    if corrections:
        logger.info(f"Parameter corrections: {corrections}")
    
    # Call tool with corrected params
    return getattr(tools, f"research_{tool_name}")(**corrected)
```

## See Also

- Full documentation: `docs/param_corrector.md`
- Examples: `examples/param_corrector_usage.py`
- Tests: `tests/test_param_corrector.py`
- Source: `src/loom/param_corrector.py`
