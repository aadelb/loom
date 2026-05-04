# Tool Composition DSL — Composer Guide

The Composer tool provides a simple declarative syntax for chaining research tools together. Instead of writing complex orchestration code, you can describe pipelines using an intuitive DSL (Domain-Specific Language).

## Quick Start

### Simple Sequential Pipeline

Chain tools together with `|` (pipe):

```
search(python security) | fetch($.urls[0]) | markdown($) | llm_summarize($)
```

This:
1. Searches for "python security"
2. Fetches the first URL from results
3. Converts HTML to markdown
4. Summarizes the markdown with an LLM

### Parallel Execution

Execute tools in parallel with `&`:

```
search(ai safety) & github(ai-safety) & social_graph(ai-safety) | merge($)
```

This:
1. Runs `search`, `github`, and `social_graph` in parallel
2. Merges results into a single structure

### Use Built-in Aliases

Replace common pipelines with aliases:

```
deep_research        # Search + fetch + markdown + summarize
osint_sweep          # Search + GitHub + social graph + merge
code_search          # GitHub + fetch + markdown + extract
breach_scan          # Search + leak scan + threat profile
```

## DSL Syntax

### Basic Tool Call

```
tool_name(arg1, arg2, ...)
```

Examples:
- `search(python)` — Simple string argument
- `fetch(url, mode)` — Multiple arguments
- `spider($.urls)` — Field reference argument

### Operators

| Operator | Meaning | Behavior |
|----------|---------|----------|
| `\|` | Sequential (pipe) | Execute left side, pass result to right side |
| `&` | Parallel | Execute both sides simultaneously, merge results |

### Field References

Access parts of the result from previous step using `$`:

| Reference | Meaning |
|-----------|---------|
| `$` | Entire result from previous step |
| `$.field` | Access dict key or object attribute |
| `$.field.subfield` | Nested field access |
| `$.urls[0]` | Array indexing (0-based) |
| `$.urls[:3]` | Array slicing (start:end) |
| `$.results[1].title` | Complex path access |

Examples:
```
search(query) | fetch($.urls[0])           # Fetch first search result
search(q) | fetch($.urls[:3])              # Fetch first 3 results
spider($.domains) | markdown($)            # Pass all domains to spider
```

## Examples

### Search and Analyze

```
search(vulnerabilities in nodejs) | fetch($.urls[0]) | markdown($)
```

Search for Node.js vulnerabilities, fetch the top result, and convert to clean text.

### Parallel OSINT

```
search(target-company.com) & whois(target-company.com) | merge($)
```

Search and look up WHOIS info in parallel, then merge results.

### Multi-Step Chain

```
github(pytorch) | fetch($.repos[0].url) | markdown($) | llm_extract($.code_features)
```

Find PyTorch on GitHub, fetch the main repo, convert to markdown, extract code features.

### Deep Research Pipeline

```
deep_research                                       # Shorthand
search($) | fetch($.urls[:3]) | markdown($) | llm_summarize($)   # Expanded
```

Execute the full deep research pipeline automatically.

### Scan for Breaches

```
breach_scan                                         # Shorthand
search($) | leak_scan($) | threat_profile($)       # Expanded
```

Search, scan for leaks, build threat profile.

## API Reference

### `research_compose()`

Execute a pipeline DSL string.

**Parameters:**
- `pipeline` (str): Pipeline DSL string (required)
- `initial_input` (str): Initial value for first step (default: "")
- `continue_on_error` (bool): Continue if step fails (default: False)
- `timeout_ms` (int): Execution timeout in milliseconds (optional)

**Returns:**
```python
{
    "success": bool,           # Overall success
    "output": Any,             # Final result
    "steps": [                 # Step metadata
        {
            "tool": str,       # Tool name
            "args": [str],     # Arguments used
            "status": str,     # "success" or "error"
            "error": str       # Error message if failed
        }
    ],
    "errors": [str],          # List of all errors
    "execution_time_ms": float,  # Total time
    "step_results": [Any]     # Results from each step
}
```

**Example:**
```python
result = await research_compose(
    "search(python) | fetch($.urls[0]) | markdown($)",
    initial_input="",
    timeout_ms=30000
)

if result["success"]:
    print(f"Pipeline succeeded in {result['execution_time_ms']}ms")
    print(f"Final result: {result['output']}")
else:
    print(f"Errors: {result['errors']}")
```

### `research_compose_validate()`

Validate pipeline syntax without executing.

**Parameters:**
- `pipeline` (str): Pipeline DSL string to validate

**Returns:**
```python
{
    "valid": bool,           # Is syntax valid?
    "steps": [               # Parsed steps
        {
            "tool_name": str,
            "args": [str],
            "parallel_group": int
        }
    ],
    "errors": [str],         # Validation errors
    "expanded_pipeline": str  # After alias expansion
}
```

**Example:**
```python
validation = research_compose_validate("search($) | fetch($.urls[0])")
if validation["valid"]:
    print(f"Pipeline will execute {len(validation['steps'])} steps")
else:
    print(f"Errors: {validation['errors']}")
```

## Error Handling

### Continue on Error

By default, if a step fails, the pipeline stops:

```python
# Stops at first error
result = await research_compose("fetch(bad_url) | markdown($)")
```

To continue despite errors:

```python
# Continues even if fetch fails
result = await research_compose(
    "fetch(bad_url) | markdown($) | summarize($)",
    continue_on_error=True
)
```

### Validate Before Execution

Always validate first to catch syntax errors early:

```python
validation = research_compose_validate(user_pipeline)
if not validation["valid"]:
    print(f"Pipeline errors: {validation['errors']}")
else:
    result = await research_compose(user_pipeline)
```

## Parallel Execution Details

When multiple tools are in parallel (`&` operator):

1. **Simultaneous execution**: All tools start at the same time
2. **Independent inputs**: Each tool receives the same input value
3. **Merged results**: Results are combined into a dict by tool name

Example:
```
search(query) & github(query) & deep(query) | merge($)
```

Results in:
```python
{
    "merged": True,
    "sources": ["search", "github", "deep"],
    "data": {
        "search": [...],
        "github": [...],
        "deep": [...]
    }
}
```

## Performance Tips

1. **Use parallel execution** when tools are independent
2. **Limit field slicing** on large arrays (e.g., `[:10]` not `[:]`)
3. **Set appropriate timeouts** for long-running pipelines
4. **Validate pipelines** before executing in production
5. **Monitor step_results** to debug intermediate outputs

## Limitations

1. **Field references** only work with dict/list/object types
2. **Complex logic** should use orchestration APIs instead
3. **Timeout** applies to entire pipeline, not per-step
4. **Error messages** limited to 2000 character pipeline strings

## Integration with Other Tools

The Composer works with existing Loom tools:

```
# Use with pipeline_enhancer for auto-enrichment
research_enhance(
    tool_name="research_compose",
    params={"pipeline": "search($) | fetch($.urls[0])"},
    auto_hcs=True,
    auto_cost=True
)

# Chain multiple composers
result1 = await research_compose("search(x) | fetch($.urls[0])")
result2 = await research_compose(
    "markdown($)",
    initial_input=result1["output"]
)
```

## Troubleshooting

### "Tool not found"

The tool name doesn't exist in Loom. Check the spelling:
- Available tools: `search`, `fetch`, `spider`, `markdown`, `github`, `llm_summarize`, etc.
- Use `research_compose_validate()` to see which tools are available

### "Invalid field reference"

Field references must follow the syntax:
- ✓ `$.field` — simple field
- ✓ `$.field[0]` — array index
- ✓ `$.field[:3]` — array slice
- ✗ `$.field[abc]` — string indexes not supported
- ✗ `$.` — incomplete reference

### "Step timeout"

Pipeline exceeded the timeout. Increase `timeout_ms`:

```python
result = await research_compose(
    pipeline,
    timeout_ms=60000  # 60 second timeout
)
```

### "Missing field in result"

A field reference tried to access a key that doesn't exist. Use `research_compose_validate()` to test field access before running the full pipeline.

## Advanced Usage

### Custom Aliases

Define your own pipeline aliases by modifying `PIPELINE_ALIASES` in `composer.py`:

```python
PIPELINE_ALIASES = {
    "my_pipeline": "search($) | fetch($.urls[0]) | markdown($)",
    "my_osint": "search($) & github($) & social_graph($) | merge($)",
}
```

Then use them:
```python
await research_compose("my_pipeline", initial_input="target")
```

### Step-by-Step Execution

Get intermediate results:

```python
result = await research_compose("search($) | fetch($.urls[0]) | markdown($)")

for i, step_result in enumerate(result["step_results"]):
    print(f"Step {i} result: {step_result}")
```

### Error Recovery

Use `continue_on_error=True` and check which steps failed:

```python
result = await research_compose(
    "a(x) | b($) | c($)",
    continue_on_error=True
)

for step in result["steps"]:
    if step["status"] == "error":
        print(f"Failed: {step['tool']} - {step['error']}")
```
