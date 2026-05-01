# Tool Catalog & Knowledge Graph Guide

The Loom Tool Catalog provides intelligent discovery, categorization, and orchestration of all 376+ research and attack tools.

## Overview

The tool catalog system enables:
1. **Discovery** - Find tools by category, capability, or function
2. **Connection Mapping** - See which tools feed into other tools
3. **Pipeline Building** - Automatically construct tool sequences for goals
4. **Standalone Info** - Complete usage documentation for any tool

## Architecture

The catalog lives in `src/loom/tools/tool_catalog.py` and exports 4 MCP tools:

### 1. `research_tool_catalog(category, capability)`

Return full tool inventory with optional filtering.

**Parameters:**
- `category` (str, optional): Filter by category (e.g., "scraping", "osint", "llm")
- `capability` (str, optional): Filter by capability tag (e.g., "accepts_url", "calls_llm")

**Returns:**
```python
{
    "tools": [
        {
            "name": "research_fetch",
            "category": "scraping",
            "subcategory": "http_fetch",
            "description": "HTTP fetch with Scrapling 3-tier escalation",
            "capabilities": ["accepts_url", "returns_text", "stealth"],
            "input_types": ["url"],
            "output_types": ["html_content"],
            "dependencies": [],
            "connects_to": ["research_markdown", "research_spider"]
        }
    ],
    "total_count": 51,
    "categories": {...},
    "capabilities": {...}
}
```

**Examples:**
```
# Get all scraping tools
research_tool_catalog(category="scraping")

# Get all tools that accept URLs
research_tool_catalog(capability="accepts_url")

# Get all tools that call external APIs
research_tool_catalog(capability="calls_external_api")
```

### 2. `research_tool_graph()`

Return the complete tool connection graph showing which tools connect to which others.

**Returns:**
```python
{
    "nodes": [
        {
            "id": "research_fetch",
            "label": "Fetch",
            "category": "scraping",
            "subcategory": "http_fetch",
            "capabilities": ["accepts_url", "returns_text"],
            "input_types": ["url"],
            "output_types": ["html_content"]
        }
    ],
    "edges": [
        {
            "source": "research_fetch",
            "target": "research_markdown",
            "type": "feeds_into",
            "reason": "['html_content'] → ['markdown']"
        }
    ],
    "clusters": {
        "scraping": ["research_fetch", "research_spider", ...],
        "search": ["research_search", "research_deep", ...]
    },
    "node_count": 51,
    "edge_count": 45,
    "cluster_count": 14
}
```

**Use Cases:**
- Visualize tool dependencies and data flow
- Find alternative tools by category
- Understand tool composition patterns

### 3. `research_tool_pipeline(goal, max_steps=5)`

Build an optimal pipeline of tools to achieve a research goal.

**Parameters:**
- `goal` (str): Research goal (e.g., "find domain OSINT", "analyze breach data")
- `max_steps` (int): Maximum pipeline length (default: 5)

**Returns:**
```python
{
    "goal": "find domain OSINT",
    "target_category": "osint",
    "pipeline": [
        {
            "step": 1,
            "tool": "research_whois",
            "category": "osint",
            "description": "WHOIS domain information lookup",
            "rationale": "Category match: osint",
            "input_from": "user",
            "output_to": "next_step"
        },
        {
            "step": 2,
            "tool": "research_dns_lookup",
            "category": "osint",
            "description": "DNS record resolution and analysis",
            "rationale": "Category match: osint",
            "input_from": "research_whois",
            "output_to": "next_step"
        }
    ],
    "pipeline_length": 2,
    "estimated_time_ms": 2000,
    "success": true
}
```

**Smart Goal Detection:**
- "domain" / "whois" → OSINT tools
- "vulnerability" / "security" → Security tools
- "search" / "find" → Search tools
- "extract" / "parse" → Document tools
- "summarize" / "analyze" → LLM tools

**Examples:**
```
# Build OSINT pipeline
research_tool_pipeline("find domain infrastructure")

# Build security analysis pipeline
research_tool_pipeline("analyze vulnerability data", max_steps=3)

# Build LLM analysis pipeline
research_tool_pipeline("summarize and extract key entities")
```

### 4. `research_tool_standalone(tool_name)`

Get complete standalone usage information for a single tool.

**Parameters:**
- `tool_name` (str): Tool name (e.g., "research_fetch")

**Returns:**
```python
{
    "name": "research_fetch",
    "description": "HTTP fetch with Scrapling 3-tier escalation",
    "category": "scraping",
    "subcategory": "http_fetch",
    "capabilities": ["accepts_url", "returns_text", "calls_external_api", "stealth"],
    "input_types": ["url"],
    "output_types": ["html_content"],
    "related_tools": {
        "dependencies": [],
        "connects_to": ["research_markdown", "research_spider", "research_deep"],
        "same_category": [
            "research_spider",
            "research_markdown",
            "research_lightpanda_fetch",
            "research_camoufox"
        ]
    },
    "typical_pipelines": [
        "research_fetch → research_markdown",
        "research_fetch → research_spider",
        "research_fetch → research_deep"
    ]
}
```

**Examples:**
```
# Get standalone info for fetch tool
research_tool_standalone("research_fetch")

# Get standalone info for search tool
research_tool_standalone("research_search")

# Get standalone info for analysis tool
research_tool_standalone("research_knowledge_graph")
```

## Tool Categories

The catalog organizes tools into 14 categories:

| Category | Subcategories | Tools |
|----------|---------------|-------|
| **scraping** | http_fetch, browser_automation, stealth_fetch, batch_fetch, content_extraction | 8 |
| **search** | web_search, academic_search, social_search, code_search, specialized_search | 5 |
| **llm** | summarize, extract, classify, translate, embed, chat, multi_model | 7 |
| **osint** | domain_intel, ip_intel, social_profiles, dark_web, breach_data, infrastructure | 8 |
| **crypto** | address_trace, risk_score, transaction_decode, defi_audit | 4 |
| **career** | job_search, salary, interview_prep, resume, company_intel | 5 |
| **academic** | citation, retraction, predatory_check, grant_forensics | 4 |
| **creative** | reframe, strategy, prompt_analysis, psycholinguistic | 4 |
| **document** | pdf_extract, ocr, transcribe, convert, table_extract | 5 |
| **monitoring** | rss, change_detect, realtime, early_warning | 2 |
| **security** | vuln_scan, cert_audit, header_check, pentest, threat_intel | 5 |
| **graph** | knowledge_graph, entity_extract, relationship_map, visualization | 3 |
| **pipeline** | workflow, orchestrate, consensus, debate, evidence | 3 |
| **system** | config, cache, session, health, metrics, traces | 6 |

## Tool Capabilities

Capabilities describe what a tool can do:

**Input Capabilities:**
- `accepts_url` - Takes a URL
- `accepts_query` - Takes a text query
- `accepts_text` - Takes arbitrary text
- `accepts_domain` - Takes a domain name
- `accepts_ip` - Takes an IP address

**Output Capabilities:**
- `returns_text` - Returns plain text
- `returns_structured` - Returns JSON/dict
- `returns_list` - Returns list of items
- `returns_score` - Returns numeric score

**Execution Capabilities:**
- `calls_external_api` - Calls external APIs
- `calls_llm` - Calls LLM providers
- `uses_browser` - Uses browser automation
- `uses_subprocess` - Spawns subprocesses

**Behavioral Capabilities:**
- `real_time` - Real-time or near real-time data
- `cached` - Results are cached
- `rate_limited` - Subject to rate limiting
- `stealth` - Anti-bot/anonymity features

## Common Pipelines

### OSINT Investigation
```
research_whois → research_dns_lookup → research_ip_geolocation → research_infra_correlator
```

### Content Analysis
```
research_fetch → research_markdown → research_llm_extract → research_knowledge_graph
```

### Deep Research
```
research_search → research_spider → research_markdown → research_consensus → research_deep
```

### Security Assessment
```
research_cert_analyze → research_security_headers → research_cve_lookup → research_threat_intel
```

### LLM-Powered Analysis
```
research_fetch → research_markdown → research_llm_summarize → research_llm_classify
```

## Connection Rules

Tools connect based on output→input type matching:

1. **Search → Scraping**: Search tools (URLs) feed into fetch/spider tools
2. **Scraping → Extraction**: Fetch tools (HTML) feed into markdown/extract tools
3. **Extraction → LLM**: Extracted content feeds into summarize/classify tools
4. **LLM → Scoring**: LLM output feeds into scoring/evaluation tools
5. **Any → Monitoring**: Any URL or content can feed into change monitors

## Usage Examples

### Example 1: Discover OSINT Tools
```python
# Get all OSINT tools
catalog = await research_tool_catalog(category="osint")

for tool in catalog["tools"]:
    print(f"{tool['name']}: {tool['description']}")
```

### Example 2: Find Tools for Your Goal
```python
# Get optimal pipeline for domain investigation
pipeline = await research_tool_pipeline("investigate domain infrastructure")

for step in pipeline["pipeline"]:
    print(f"Step {step['step']}: {step['tool']}")
    print(f"  Input: {tool['input_types']}")
    print(f"  Output: {tool['output_types']}")
```

### Example 3: Visualize Tool Graph
```python
# Get full connection graph
graph = await research_tool_graph()

print(f"Total tools: {graph['node_count']}")
print(f"Connections: {graph['edge_count']}")

# Show a category cluster
for cluster_name, tools in graph["clusters"].items():
    print(f"{cluster_name}: {len(tools)} tools")
```

### Example 4: Standalone Tool Info
```python
# Get complete info for one tool
info = await research_tool_standalone("research_deep")

print(f"Tool: {info['name']}")
print(f"Description: {info['description']}")
print(f"Category: {info['category']}")
print(f"Can input: {info['input_types']}")
print(f"Can output: {info['output_types']}")
print(f"Related tools: {info['related_tools']['connects_to']}")
```

## Implementation Details

### Registry Structure
Each tool in `TOOL_REGISTRY` has:
- `category`: Top-level grouping
- `subcategory`: Specific function
- `description`: What it does
- `capabilities`: Tags for behavior
- `input_types`: What it accepts
- `output_types`: What it produces
- `dependencies`: Tools it depends on
- `connects_to`: Tools that accept its output

### Scalability
- Registry is static (hardcoded) for performance
- No external dependencies or API calls
- Can handle 1000+ tools without slowdown
- Connection graph is bidirectional

### Future Extensions
1. Add more tools as they're implemented
2. Add user ratings and popularity metrics
3. Add execution time estimates
4. Add cost/API key requirements
5. Add success rate statistics
6. Add tool versioning and compatibility

## Integration with Loom

The tool catalog integrates seamlessly:

1. **Discovery**: Use `research_tool_catalog` to find tools
2. **Planning**: Use `research_tool_pipeline` to build tool sequences
3. **Execution**: Use identified tools in your research flow
4. **Feedback**: Results inform catalog improvements

## Performance Notes

- All functions are async and non-blocking
- Registry lookup is O(1) for individual tools
- Category filtering is O(n) but n ≤ 376
- Graph building is lazy (computed on-demand)
- No caching needed (operations are fast)

## File Locations

- **Catalog module**: `/src/loom/tools/tool_catalog.py`
- **Tests**: `/tests/test_tools/test_tool_catalog.py`
- **This guide**: `/TOOL_CATALOG_GUIDE.md`
