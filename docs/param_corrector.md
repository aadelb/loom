# Parameter Auto-Correction Module

## Overview

The `param_corrector` module provides intelligent, automatic correction of common parameter name mistakes in Loom tool calls. It helps users avoid frustrating validation errors by suggesting or automatically fixing misspelled, aliased, or incorrectly-cased parameter names.

## Features

- **Fuzzy Matching**: Uses Python's `difflib` to find similar parameter names with confidence scoring
- **Common Aliases**: Built-in dictionary of 20+ frequently-used parameter aliases
- **Case-Insensitive Matching**: Automatically corrects capitalization issues
- **Dynamic Introspection**: Can automatically discover valid parameter names for any tool
- **User-Friendly Messages**: Formats corrections into clear, helpful messages
- **Zero Dependencies**: Uses only Python standard library (difflib, inspect, importlib)

## API Reference

### `suggest_param(user_param, valid_params, confidence_threshold=0.6)`

Suggests the closest valid parameter name for a user-provided parameter.

**Parameters:**
- `user_param` (str): The parameter name provided by the user
- `valid_params` (list[str]): List of valid parameter names for a tool
- `confidence_threshold` (float): Minimum similarity score (0.0-1.0) to suggest. Default: 0.6

**Returns:**
- Tuple of (suggested_param, confidence_score)
- Returns (None, 0.0) if no match meets the threshold

**Example:**
```python
from loom.param_corrector import suggest_param

valid = ["limit", "offset", "query"]
suggestion, confidence = suggest_param("limi", valid)
# Returns: ("limit", 0.89)

suggestion, confidence = suggest_param("xyz", valid)
# Returns: (None, 0.0)
```

### `auto_correct_params(tool_name, user_params, valid_params=None)`

Auto-corrects parameter names in a tool call using aliases and fuzzy matching.

**Parameters:**
- `tool_name` (str): Name of the tool being called (e.g., "fetch", "search")
- `user_params` (dict): User-provided parameters
- `valid_params` (list[str], optional): Valid params for the tool. If None, introspects dynamically

**Returns:**
- Tuple of (corrected_dict, list_of_correction_messages)

**Example:**
```python
from loom.param_corrector import auto_correct_params

user_params = {
    "max_results": 50,
    "search_query": "python",
    "time_out": 30
}
valid_params = ["limit", "query", "timeout"]

corrected, corrections = auto_correct_params(
    "search", user_params, valid_params
)

print(corrected)
# Output: {'limit': 50, 'query': 'python', 'timeout': 30}

print(corrections)
# Output: [
#     "'max_results' → 'limit' (common alias)",
#     "'search_query' → 'query' (common alias)",
#     "'time_out' → 'timeout' (similarity: 86%)"
# ]
```

### `get_tool_params(tool_name)`

Dynamically introspects a tool function to extract valid parameter names.

**Parameters:**
- `tool_name` (str): Name of the tool (e.g., "fetch", "search")

**Returns:**
- List of valid parameter names, or empty list if tool not found

**Example:**
```python
from loom.param_corrector import get_tool_params

params = get_tool_params("fetch")
# Returns: ["query", "max_chars", "wait_time", "javascript_enabled", ...]
```

### `format_correction_message(corrections)`

Formats a list of corrections into a user-friendly message.

**Parameters:**
- `corrections` (list[str]): List of correction messages

**Returns:**
- Formatted string suitable for user display

**Example:**
```python
from loom.param_corrector import format_correction_message

corrections = [
    "'max_results' → 'limit' (common alias)",
    "'search_query' → 'query' (common alias)"
]

message = format_correction_message(corrections)
print(message)
# Output:
# Auto-corrected parameters:
#   1. 'max_results' → 'limit' (common alias)
#   2. 'search_query' → 'query' (common alias)
```

## Common Aliases

The module includes 20+ common aliases that users frequently use. These are automatically detected and corrected:

| User Input | Correct Parameter |
|------------|------------------|
| `max_results` | `limit` |
| `num_results` | `n` |
| `search_query` | `query` |
| `query_text` | `query` |
| `keywords` | `query` |
| `url_list` | `urls` |
| `target_language` | `target_lang` |
| `target_model` | `model_name` |
| `max_tokens_output` | `max_tokens` |
| `timeout_sec` | `timeout` |
| `wait_sec` | `wait_time` |
| `javascript` | `javascript_enabled` |
| `js_enabled` | `javascript_enabled` |
| `output_format` | `format` |
| `return_type` | `format` |
| `include_metadata` | `metadata` |
| `show_metadata` | `metadata` |
| `num_workers` | `workers` |
| `thread_count` | `workers` |
| `batch_size` | `batch` |

## Integration with Tool Validation

### Strategy 1: Pre-validation Correction

```python
from loom.param_corrector import auto_correct_params
from loom.params import FetchParams

def research_fetch(url: str, max_chars: int = 20000, ...):
    """Fetch tool with auto-correction."""
    pass

# In your tool handler:
user_input = {
    "query_text": "https://example.com",  # Wrong param name
    "max_chars": 20000
}

# Correct before validation
corrected, messages = auto_correct_params("fetch", user_input)

# Now validate with Pydantic
validated = FetchParams(**corrected)
```

### Strategy 2: Error Recovery

```python
from loom.param_corrector import auto_correct_params, format_correction_message
from pydantic import ValidationError

try:
    # First attempt with user's original params
    validated = FetchParams(**user_params)
except ValidationError as e:
    # If validation fails, try auto-correction
    corrected, corrections = auto_correct_params("fetch", user_params)
    
    if corrections:
        # Suggest corrections to user
        message = format_correction_message(corrections)
        print(f"Hint: {message}")
        
        # Try validation again
        validated = FetchParams(**corrected)
    else:
        # No corrections possible, re-raise original error
        raise
```

## Use Cases

### 1. CLI Tools
```bash
# User types wrong parameter name
$ loom fetch --max_chars 20000 --query_text https://example.com

# Module auto-corrects to: --max_chars, --query
```

### 2. API Endpoints
```python
@app.post("/tools/fetch")
async def fetch_endpoint(request: dict):
    corrected, _ = auto_correct_params("fetch", request)
    return await fetch_tool(**corrected)
```

### 3. Interactive Debugging
```python
# User provides dict with wrong param names
user_params = {"max_results": 50, "time_out": 30}

corrected, corrections = auto_correct_params("search", user_params, valid_params)

if corrections:
    print(format_correction_message(corrections))
    print(f"Using: {corrected}")
```

## Confidence Scoring

The module uses Python's `difflib.SequenceMatcher` to calculate similarity between parameter names. Suggestions are only made if confidence exceeds 0.6 (60% similarity).

**Examples:**
- `"limi"` vs `"limit"` = 89% confidence → ACCEPTED
- `"ofset"` vs `"offset"` = 91% confidence → ACCEPTED
- `"tim"` vs `"timeout"` = 60% confidence → ACCEPTED (borderline)
- `"xyz"` vs `"query"` = 0% confidence → REJECTED

## Performance Characteristics

- **Memory**: ~1 KB for the COMMON_ALIASES dict + module overhead
- **Speed**: <1ms per correction (difflib is highly optimized)
- **Scaling**: O(n) where n = number of valid params (typically 5-50)
- **No Network**: All operations local, no external dependencies

## Testing

The module includes 26 comprehensive test cases covering:
- Exact matching
- Fuzzy matching with confidence scoring
- Case-insensitive matching
- Common alias detection
- Dynamic tool introspection
- Message formatting
- Edge cases (empty lists, special characters, etc.)

Run tests:
```bash
pytest tests/test_param_corrector.py -v
```

## Type Safety

The module is fully typed and passes strict mypy type checking:
```bash
mypy src/loom/param_corrector.py --strict
```

All functions have complete type hints for parameters and return values.

## Troubleshooting

### "No correction found for param 'xyz'"
This is expected behavior. The module only corrects parameters with >60% similarity to valid params. Completely different names are passed through unchanged and will fail validation.

**Solution**: Check the valid parameter names for the tool and use the correct name.

### "Tool not found during introspection"
The module tries to dynamically import the tool, which may fail if the module structure is non-standard.

**Solution**: Provide the `valid_params` list explicitly to `auto_correct_params()`.

### "Correction changed my intended value"
The module preserves all parameter values during correction. Only the parameter names are modified.

**Solution**: If a correction is incorrect, you can disable it by adding to the COMMON_ALIASES exclusion list (future enhancement).

## Future Enhancements

- [ ] Learning from user corrections (adaptive aliases)
- [ ] Per-tool custom aliases
- [ ] Correction confidence thresholds per tool
- [ ] Logging of common mistakes for analytics
- [ ] Integration with OpenAPI schemas for discovery
- [ ] Support for nested parameter correction
- [ ] Suggestion ranking by usage frequency

## Related Modules

- `loom.params`: Pydantic models for all tool parameters
- `loom.validators`: URL validation, character capping, etc.
- `loom.server`: MCP server where tools are registered
- `loom.tools`: The 829+ tool implementations

## License

Part of the Loom project. See LICENSE for details.
