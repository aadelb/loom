# Natural Language Tool Executor

The Natural Language Tool Executor (`research_do`) is a unified interface that accepts plain English instructions and automatically routes them to the appropriate Loom tool.

## Overview

Instead of needing to know specific tool names and parameters, users can simply describe what they want to accomplish in natural language.

**Example:**
```
"scan example.com for security headers"
```

The executor will:
1. Parse the instruction to extract the action verb ("scan")
2. Map it to the security category
3. Select the best tool (research_security_headers)
4. Generate parameters (url="example.com")
5. Execute the tool and return results

## Usage

```python
import asyncio
from loom.tools.nl_executor import research_do

result = await research_do("search for python async patterns")
```

## Supported Actions

### Security
- Scan, audit, check, verify URLs/domains for vulnerabilities
- Examples: "scan example.com for headers", "check domain.com for breaches"
- Maps to: security_headers, cert_analyzer, breach_check, vuln_intel, cve_lookup

### Search
- Search, find, discover information across the web
- Examples: "search for python asyncio", "find github repositories for machine learning"
- Maps to: search, deep, github, multi_search

### Analysis
- Analyze, evaluate, score, assess content
- Examples: "analyze this prompt for injection", "score the stealth of this attack"
- Maps to: hcs_scorer, stealth_score, model_profiler, toxicity_checker, fact_checker

### Monitoring
- Monitor, track, watch for changes
- Examples: "monitor changes on github repo", "track website modifications"
- Maps to: change_monitor, drift_monitor, realtime_monitor

### Reframing
- Reframe, bypass, transform prompts
- Examples: "reframe this prompt to bypass filters", "transform the request"
- Maps to: prompt_reframe, auto_reframe

### Export
- Export, save, download, report results
- Examples: "export results to json", "save findings as CSV"
- Maps to: export_json, export_csv

## Response Structure

The executor returns a detailed response:

```python
{
    "instruction": "original instruction",
    "tool_selected": "research_search",
    "params_used": {"query": "python patterns", "n": 10},
    "success": True,
    "result": {...},  # Tool output
    "execution_ms": 1234,
    "alternatives": [...]  # Other tools in the same category
}
```

## URL and Parameter Extraction

The executor intelligently extracts parameters from instructions:

- **URLs**: Detects both full URLs (https://example.com) and domains (example.com)
- **Query text**: Extracts the main query after removing the action verb
- **Limit/count**: Recognizes numeric limits (e.g., "10 results")
- **Model names**: Detects model names (gpt-4, claude, deepseek, etc.)

## Implementation Details

Located at: `/Users/aadel/projects/loom/src/loom/tools/nl_executor.py`

### Components

1. **TOOL_CATEGORIES**: Maps categories to available tools
2. **ACTION_TO_CATEGORY**: Maps action patterns to categories (regex-based)
3. **_extract_action()**: Identifies the action verb from instruction
4. **_extract_url()**: Extracts URLs or domains
5. **_extract_query()**: Extracts the query text
6. **_extract_number()**: Extracts numeric limits
7. **_extract_model_name()**: Detects model names
8. **_select_tool()**: Chooses best tool based on instruction keywords
9. **_get_tool_function()**: Dynamically imports and returns the tool
10. **research_do()**: Main async function that orchestrates the flow

### Error Handling

All errors are caught and returned in the response structure:

```python
{
    "success": False,
    "result": "Execution failed: <error message>",
    "execution_ms": 100
}
```

## Testing

Run tests with:

```bash
pytest tests/test_tools/test_nl_executor.py -v
```

20 test cases covering:
- Action extraction for all categories
- URL/domain extraction
- Query extraction
- Number extraction
- Model name detection
- Tool selection
- Category structure
- Full tool execution flow

## Integration with MCP

The tool is registered in `server.py` as:

```python
mcp.tool()(_wrap_tool(nl_executor.research_do))
```

This makes it available as an MCP tool that can be called by Claude and other MCP clients.

## Future Enhancements

- Machine learning-based action classification for improved accuracy
- Multi-step instruction composition ("then also...")
- Instruction templates and saved workflows
- Context-aware parameter generation
- Result formatting options per category
