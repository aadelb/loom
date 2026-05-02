# Natural Language Tool Executor - Technical Specification

## Overview

The Natural Language Tool Executor is a unified, minimal interface that transforms plain English instructions into structured tool calls. It provides a single entry point (`research_do`) that automatically:

1. Parses the instruction to extract intent
2. Routes to the appropriate tool category
3. Selects the best matching tool
4. Generates required parameters
5. Executes the tool
6. Returns structured results

## Architecture

```
Instruction Input
    ↓
[_extract_action] → Category (security, search, analysis, etc.)
    ↓
[_extract_url] → URL/Domain parameters
    ↓
[_extract_query] → Query text
    ↓
[_extract_number] → Numeric limits
    ↓
[_extract_model_name] → Model selection
    ↓
[_select_tool] → Best matching tool from category
    ↓
[_get_tool_function] → Dynamic import and resolution
    ↓
[research_do] → Execute with built parameters
    ↓
Structured Response {instruction, tool_selected, params_used, success, result, execution_ms, alternatives}
```

## Component Details

### 1. TOOL_CATEGORIES (Mapping)

Maps action categories to available tools:

```python
{
    "security": [research_security_headers, research_cert_analyzer, ...],
    "search": [research_search, research_deep, research_github, ...],
    "analysis": [research_hcs_scorer, research_stealth_score, ...],
    "monitoring": [research_change_monitor, research_drift_monitor, ...],
    "reframing": [research_prompt_reframe, research_auto_reframe],
    "export": [research_export_json, research_export_csv],
}
```

**Design rationale**: 
- Clear categorization by use case
- Easy to extend with new tools
- Multiple tools per category for fine-tuned selection

### 2. ACTION_TO_CATEGORY (Pattern List)

Maps action verbs to categories using regex patterns:

```python
[
    (r"\b(evaluate|score|assess|measure)\b", "analysis"),
    (r"\b(scan|audit|check|verify)\b", "security"),
    (r"\b(search|find|discover|lookup|query)\b", "search"),
    (r"\b(analyze)\b", "analysis"),
    (r"\b(monitor|track|watch|observe)\b", "monitoring"),
    (r"\b(reframe|bypass|rephrase|transform)\b", "reframing"),
    (r"\b(export|save|download|report)\b", "export"),
]
```

**Design notes**:
- List (not dict) to maintain order and precedence
- More specific patterns first (evaluate/score/assess before generic analyze)
- Word boundaries (`\b`) prevent substring matches
- Case-insensitive matching

### 3. _extract_action() Function

**Purpose**: Identify action category from instruction

**Algorithm**:
1. Convert instruction to lowercase
2. Iterate through ACTION_TO_CATEGORY patterns in order
3. Return first matching category
4. Return None if no match

**Example**:
```python
_extract_action("analyze the security of this domain")
# → "analysis" (matches \b(analyze)\b pattern)
```

**Time complexity**: O(n) where n = number of patterns (7)

### 4. _extract_url() Function

**Purpose**: Extract URLs and domains from instructions

**Algorithm**:
1. Try full URL pattern: `https?://[^\s]+`
2. If no match, try domain pattern: `(?:www\.)?([a-z0-9-]+\.)+[a-z]{2,}`
3. Return first match or None

**Examples**:
- "scan https://example.com" → "https://example.com"
- "check example.com for headers" → "example.com"
- "search for patterns" → None

**Security**: Only extracts valid URLs/domains, prevents injection attacks

### 5. _extract_query() Function

**Purpose**: Extract query text by removing action verb

**Algorithm**:
1. Match all known action verbs: `\b(scan|audit|check|...)\b\s+`
2. Remove first occurrence using `re.sub()`
3. Strip whitespace and return

**Example**:
```python
_extract_query("search for python async patterns", "search")
# → "for python async patterns"
```

**Design**: Removes action verb to keep only substantive query text

### 6. _extract_number() Function

**Purpose**: Extract numeric limits from instructions

**Algorithm**:
1. Search for first number: `\b(\d+)\b`
2. Return as int, or default (10)

**Examples**:
- "search and return 25 results" → 25
- "monitor changes" → 10 (default)

**Bounds**: Some tools enforce max (e.g., n ≤ 50 for search)

### 7. _extract_model_name() Function

**Purpose**: Detect model names for model-selection tools

**Algorithm**:
1. Define known models: gpt-3.5, gpt-4, claude, llama, etc.
2. Case-insensitive substring search
3. Return first match or None

**Example**:
```python
_extract_model_name("reframe using gpt-4")
# → "gpt-4"
```

### 8. _select_tool() Function

**Purpose**: Choose best tool from category based on instruction keywords

**Algorithm**:
1. Get category tools from TOOL_CATEGORIES
2. For each tool, split name into keywords (e.g., "research_security_headers" → ["security", "headers"])
3. Score each tool: count keyword matches in instruction (lowercased)
4. Return tool with highest score
5. Fallback to first tool if no scores > 0

**Example**:
```python
_select_tool("security", "check example.com for security headers", "example.com")
# Tool scores:
#   research_security_headers: 2 (matches "security", "headers")
#   research_cert_analyzer: 0
#   research_breach_check: 0
# → "research_security_headers"
```

**Design**: Keyword matching provides basic semantic ranking without ML

### 9. _get_tool_function() Function

**Purpose**: Dynamically import and load tool functions

**Algorithm**:
1. Parse tool name: "research_security_headers" → ["research", "security", "headers"]
2. Build module path: "loom.tools.security_headers" (second element + rest)
3. Use `importlib.import_module()`
4. Use `getattr()` to get the function
5. Catch ImportError/AttributeError and log

**Error handling**:
- Returns None if module doesn't exist
- Returns None if function not found in module
- Logs detailed errors for debugging

**Async-safe**: Returns callable (sync or async) without running it

### 10. research_do() Function

**Purpose**: Main orchestrator function

**Algorithm**:
1. Start timer
2. Extract action, URL, query, number, model
3. Select tool
4. Get alternatives for response
5. Load tool function
6. Build params dict:
   - url, query, n (limit), model (if present in function signature)
7. Execute tool (async or sync)
8. Return structured response
9. Catch all exceptions and return error response

**Response structure**:
```python
{
    "instruction": str,          # Original input
    "tool_selected": str,        # Tool name used
    "params_used": dict,         # Params passed to tool
    "success": bool,             # Execution success
    "result": Any,               # Tool output or error
    "execution_ms": int,         # Duration in milliseconds
    "alternatives": list[str],   # Other tools in category
}
```

**Error handling**:
- Catches all exceptions at top level
- Returns meaningful error in result field
- Execution time still calculated
- Logging at INFO and ERROR levels

**Performance**:
- Typical execution: <100ms (parsing + selection)
- Actual tool execution varies
- Minimal overhead (<10% relative to tool time)

## Design Principles

### 1. Simplicity
- Single entry point (`research_do`)
- Clear parameter extraction flow
- Minimal dependencies

### 2. Robustness
- Comprehensive error handling
- Graceful degradation (use defaults when needed)
- Logging at all key points

### 3. Extensibility
- New categories added by extending TOOL_CATEGORIES
- New action patterns added to ACTION_TO_CATEGORY
- New tools discovered via dynamic import

### 4. Type Safety
- Type hints on all functions
- Pydantic validation (when parameters reach tools)
- Return type documentation

### 5. Observability
- Structured logging via structlog
- Execution timing
- Alternative suggestions in response

## Usage Patterns

### Simple Search
```python
await research_do("search for machine learning papers")
# → Routes to research_search or research_deep
```

### Security Audit
```python
await research_do("scan example.com for security headers")
# → Routes to research_security_headers
# → Extracts URL automatically
```

### Analysis Task
```python
await research_do("analyze this prompt for injection attacks")
# → Routes to research_toxicity_checker or similar
# → Extracts query text
```

### Parameterized Search
```python
await research_do("search for python docs using 20 results")
# → Routes to research_search
# → Extracts n=20
```

### Model-specific Operation
```python
await research_do("reframe this prompt using gpt-4")
# → Routes to research_prompt_reframe
# → Extracts model="gpt-4"
```

## Testing Strategy

### Unit Tests (Extraction Functions)
- Test each extraction function independently
- Cover edge cases and boundary conditions
- Verify regex patterns match correctly

### Integration Tests
- Test full research_do flow
- Verify tool selection correctness
- Test error handling paths
- Validate response structure

### Coverage Target
- 80%+ code coverage
- All happy paths covered
- All error paths covered
- All extraction functions tested

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Parse instruction | <1ms | Regex matching |
| Extract parameters | <2ms | Multiple regex passes |
| Select tool | <1ms | Simple keyword scoring |
| Load tool function | <5ms | Dynamic import + getattr |
| **Total parsing overhead** | **<10ms** | Before tool execution |

## Security Considerations

### Input Validation
- URLs validated via `validators.validate_url()`
- SSRF protection at validator level
- Character limits enforced by tools

### Error Messages
- Don't leak sensitive information
- Generic error messages to users
- Detailed logs for debugging (internal only)

### Tool Safety
- All tools registered and vetted
- Parameters validated by Pydantic
- Execution happens in tool's own sandbox

## Future Enhancements

### Planned
1. **ML-based action classification** - Neural classifier for better intent detection
2. **Multi-step composition** - "First search, then analyze"
3. **Result formatting** - Custom output formats per category
4. **Instruction templates** - Pre-built pattern library
5. **Context awareness** - Remember previous instructions
6. **Confidence scoring** - Return confidence in action selection

### Possible
1. **Natural language parameters** - Extract complex param objects
2. **Chain of thought** - Explain reasoning for tool selection
3. **Feedback loop** - Learn from user corrections
4. **Caching** - Cache similar instructions
5. **Batch processing** - Process multiple instructions
6. **Streaming results** - Return results as they arrive

## Files

- **Implementation**: `/Users/aadel/projects/loom/src/loom/tools/nl_executor.py` (252 lines)
- **Tests**: `/Users/aadel/projects/loom/tests/test_tools/test_nl_executor.py` (132 lines)
- **Documentation**: `/Users/aadel/projects/loom/NATURAL_LANGUAGE_EXECUTOR.md`
- **This file**: `/Users/aadel/projects/loom/NL_EXECUTOR_TECHNICAL.md`

## References

- MCP Tool Protocol: https://modelcontextprotocol.io/
- Python AsyncIO: https://docs.python.org/3/library/asyncio.html
- Structlog Logging: https://www.structlog.org/
