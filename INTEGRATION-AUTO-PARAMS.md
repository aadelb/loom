# Auto-Parameter Generator Integration

## Overview

The Auto-Parameter Generator (`auto_params.py`) automatically infers tool parameters from natural language queries. This eliminates the need to manually construct complex parameter dictionaries when invoking MCP tools.

## Features

### 1. Intelligent Parameter Inference

The generator analyzes natural language input and automatically extracts:
- **URLs**: Detects HTTP/HTTPS URLs via regex
- **Domains**: Extracts domain names (e.g., `github.com`, `api.example.org`)
- **Query/Prompt text**: Uses the query itself for text-based parameters
- **Model names**: Detects model identifiers (claude, gpt, deepseek, gemini, llama, etc.)
- **Language codes**: Auto-detects language hints (english→en, arabic→ar, etc.)
- **Numeric parameters**: Extracts numbers for limits, counts, iterations
- **Boolean parameters**: Defaults to True
- **List parameters**: Wraps single values into lists
- **Strategy names**: Detects quoted strings or strategy identifiers

### 2. Tool Inspection

The `research_inspect_tool` function returns complete signature metadata for any tool:
- Parameter names, types, and defaults
- Required vs optional parameters
- Function docstring
- Source file location

## Tools

### 1. `research_auto_params`

Automatically infers tool parameters from a natural language query.

**Parameters:**
- `tool_name` (str): Name of the target tool (e.g., `research_fetch`, `research_search`)
- `query` (str): Natural language description or query

**Returns:**
```json
{
  "tool_name": "research_fetch",
  "generated_params": {
    "url": "https://example.com",
    "mode": "stealthy",
    "max_chars": 20000
  },
  "params_inferred": 3,
  "params_defaulted": 2,
  "confidence": 85,
  "error": null
}
```

**Response Fields:**
- `tool_name`: Input tool name
- `generated_params`: Dictionary of inferred parameters ready to use
- `params_inferred`: Count of parameters inferred from the query
- `params_defaulted`: Count of optional parameters using defaults
- `confidence`: Score 0-100 based on inference quality
- `error`: Error message if tool lookup failed

### 2. `research_inspect_tool`

Returns full signature and metadata for a tool.

**Parameters:**
- `tool_name` (str): Name of the tool to inspect

**Returns:**
```json
{
  "tool_name": "research_fetch",
  "module": "loom.tools.fetch",
  "parameters": [
    {
      "name": "url",
      "type": "str",
      "default": null,
      "required": true
    },
    {
      "name": "mode",
      "type": "Literal['http', 'stealthy', 'dynamic']",
      "default": "stealthy",
      "required": false
    }
  ],
  "docstring": "Unified URL fetcher with HTTP, stealth, and dynamic modes...",
  "source_file": "/path/to/loom/tools/fetch.py"
}
```

## Usage Examples

### Example 1: Auto-infer fetch parameters

```bash
# Input
tool_name: research_fetch
query: "Fetch https://example.com in stealthy mode and get 20000 characters"

# Output
{
  "generated_params": {
    "url": "https://example.com",
    "mode": "stealthy",
    "max_chars": 20000
  },
  "params_inferred": 3,
  "confidence": 90
}
```

### Example 2: Auto-infer search parameters

```bash
# Input
tool_name: research_search
query: "Search for python tutorials with gpt using 10 results in english"

# Output
{
  "generated_params": {
    "query": "Search for python tutorials with gpt using 10 results in english",
    "model": "gpt",
    "n": 10,
    "language": "en"
  },
  "params_inferred": 4,
  "confidence": 80
}
```

### Example 3: Inspect tool signature

```bash
# Input
tool_name: research_search

# Output
{
  "tool_name": "research_search",
  "module": "loom.tools.search",
  "parameters": [
    {
      "name": "query",
      "type": "str",
      "required": true
    },
    {
      "name": "provider",
      "type": "str | None",
      "default": null,
      "required": false
    },
    {
      "name": "n",
      "type": "int",
      "default": "10",
      "required": false
    }
  ],
  "docstring": "Search the web using the configured provider...",
  "source_file": "/path/to/loom/tools/search.py"
}
```

## Implementation Details

### Architecture

The implementation consists of:

1. **Helper Functions** (6 total):
   - `_extract_urls()`: Regex-based URL extraction
   - `_extract_numbers()`: Integer extraction
   - `_detect_language()`: Language code inference
   - `_detect_model()`: Model name detection
   - `_extract_domain()`: Domain name extraction
   - `_infer_param_value()`: Master parameter inference

2. **Core Tools** (2 total):
   - `research_auto_params()`: Parameter inference from natural language
   - `research_inspect_tool()`: Tool signature inspection

### Parameter Inference Strategy

The inference engine uses a hierarchical matching approach:

1. **Semantic matching**: Parameter name analysis (url, query, domain, model, etc.)
2. **Pattern matching**: Regex-based extraction (URLs, domains, numbers)
3. **Contextual detection**: Language codes, model names, strategy names
4. **Type-based defaults**: Boolean→True, List→[value], Missing→skip
5. **Confidence scoring**: (inferred_params / total_params) × 100

### Error Handling

- Import failures: Returns detailed error message
- Missing tools: Gracefully returns empty params with error flag
- Malformed input: Non-blocking; defaults to safe values
- Long queries: No length limits; handles edge cases

## Testing

Comprehensive test suite in `tests/test_tools/test_auto_params.py`:

- **Unit tests**: Individual helper functions
- **Integration tests**: Full parameter inference workflow
- **Edge cases**: Empty queries, special characters, very long input
- **Confidence scoring**: Validation of quality metrics
- **Tool inspection**: Signature metadata retrieval

Run tests:
```bash
pytest tests/test_tools/test_auto_params.py -v
```

## Performance

- **Extraction**: O(1) regex operations per parameter
- **Inference**: O(p) where p = number of parameters
- **Inspection**: O(p) for signature traversal
- **Memory**: Constant overhead; no state maintained

## Integration Points

### Server Registration

Tools are registered in `src/loom/server.py`:

```python
from loom.tools import auto_params

# In _register_tools():
mcp.tool()(_wrap_tool(auto_params.research_auto_params))
mcp.tool()(_wrap_tool(auto_params.research_inspect_tool))
```

### Workflow

1. **User provides natural language query**
2. `research_auto_params` analyzes query
3. Extracts URLs, numbers, language, model, domain
4. Returns inferred parameters + confidence score
5. User can use params directly or adjust via `research_inspect_tool`
6. Call target tool with generated parameters

## Security Considerations

- **URL validation**: Only HTTP/HTTPS URLs accepted
- **Input sanitization**: Regex patterns prevent injection
- **Model detection**: Whitelist of known model names
- **Language codes**: Limited to ISO 639-1 two-letter codes
- **Domain validation**: Strict regex pattern (DNS-compliant)

## Future Enhancements

1. **ML-based inference**: Train on historical tool calls
2. **Contextual awareness**: Track previous parameters in session
3. **Provider optimization**: Recommend providers based on query type
4. **Cost estimation**: Predict parameter impact on billing
5. **Strategy recommendation**: Suggest effective reframing strategies
6. **Parameter validation**: Pre-flight checks before tool invocation

## Metrics

- **Coverage**: 6 helper functions + 2 core tools
- **Code size**: ~320 lines (including comprehensive documentation)
- **Test coverage**: 20+ test cases covering all inference paths
- **Supported tools**: Any tool with standard Python signature
- **Language support**: 8 language codes (en, ar, fr, es, de, zh, ja, ko)
- **Model detection**: 12 model names (claude, gpt, deepseek, gemini, llama, etc.)
