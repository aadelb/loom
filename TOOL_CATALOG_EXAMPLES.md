# Tool Catalog Usage Examples

Quick reference for using the 4 tool catalog functions.

## Example 1: Discover All Scraping Tools

**Goal**: Find all web scraping and content extraction tools

**Function**: `research_tool_catalog(category="scraping")`

**Result**:
```python
{
  "tools": [
    {
      "name": "research_fetch",
      "description": "HTTP fetch with Scrapling 3-tier escalation",
      "capabilities": ["accepts_url", "returns_text", "stealth"]
    },
    {
      "name": "research_spider", 
      "description": "Concurrent multi-URL fetch with escalation",
      "capabilities": ["accepts_url", "returns_list", "stealth"]
    },
    {
      "name": "research_markdown",
      "description": "HTML to markdown conversion (Crawl4AI + Trafilatura fallback)",
      "capabilities": ["accepts_text", "returns_text"]
    },
    # ... 5 more scraping tools
  ],
  "total_count": 8
}
```

**Use Case**: You need a web scraper. This tells you Loom has 8 options from basic HTTP to browser automation.

---

## Example 2: Find All LLM-Powered Tools

**Goal**: Discover tools that use LLM providers

**Function**: `research_tool_catalog(capability="calls_llm")`

**Result**:
```python
{
  "tools": [
    {
      "name": "research_llm_summarize",
      "description": "Text summarization with multi-provider cascade",
      "capabilities": ["accepts_text", "returns_text", "calls_llm"]
    },
    {
      "name": "research_llm_extract",
      "description": "Structured extraction from content",
      "capabilities": ["accepts_text", "returns_structured", "calls_llm"]
    },
    {
      "name": "research_knowledge_graph",
      "description": "Knowledge graph construction from content",
      "capabilities": ["accepts_text", "returns_structured", "calls_llm"]
    },
    {
      "name": "research_consensus",
      "description": "Consensus builder from multiple sources",
      "capabilities": ["accepts_text", "returns_structured", "calls_llm"]
    },
    # ... 7 more LLM tools
  ],
  "total_count": 11
}
```

**Use Case**: You want to use AI for analysis. This shows all 11 LLM-powered tools available.

---

## Example 3: Visualize the Tool Dependency Graph

**Goal**: Understand how tools connect and can feed into each other

**Function**: `research_tool_graph()`

**Result** (partial):
```python
{
  "nodes": [
    {
      "id": "research_fetch",
      "label": "Fetch",
      "category": "scraping",
      "output_types": ["html_content"]
    },
    # ... 50 more nodes
  ],
  "edges": [
    {
      "source": "research_fetch",
      "target": "research_markdown",
      "reason": "['html_content'] → ['markdown']"
    },
    {
      "source": "research_markdown",
      "target": "research_llm_extract",
      "reason": "['markdown'] → ['text']"
    },
    {
      "source": "research_llm_extract",
      "target": "research_knowledge_graph",
      "reason": "['text'] → ['structured_data']"
    },
    # ... 42 more edges
  ],
  "clusters": {
    "scraping": ["research_fetch", "research_spider", ...],
    "llm": ["research_llm_summarize", "research_llm_extract", ...],
    # ... all 14 categories
  },
  "node_count": 51,
  "edge_count": 45,
  "cluster_count": 14
}
```

**Use Case**: You want to see the "research ecosystem" - what tools work well together.

---

## Example 4: Build a Pipeline for OSINT Research

**Goal**: Automatically suggest tools for domain investigation

**Function**: `research_tool_pipeline("investigate domain infrastructure")`

**Result**:
```python
{
  "goal": "investigate domain infrastructure",
  "target_category": "osint",
  "pipeline": [
    {
      "step": 1,
      "tool": "research_whois",
      "description": "WHOIS domain information lookup",
      "input_types": ["domain"],
      "output_types": ["whois_data"]
    },
    {
      "step": 2,
      "tool": "research_dns_lookup",
      "description": "DNS record resolution and analysis",
      "input_types": ["domain"],
      "output_types": ["dns_records"]
    },
    {
      "step": 3,
      "tool": "research_ip_geolocation",
      "description": "IP geolocation and reputation",
      "input_types": ["ip"],
      "output_types": ["ip_data"]
    },
    {
      "step": 4,
      "tool": "research_infra_correlator",
      "description": "Link domains/IPs via shared infrastructure",
      "input_types": ["domain_or_ip"],
      "output_types": ["correlated_assets"]
    }
  ],
  "pipeline_length": 4,
  "estimated_time_ms": 4000,
  "success": true
}
```

**Use Case**: You say "find domain OSINT" and get a suggested 4-step pipeline.

---

## Example 5: Get Complete Tool Documentation

**Goal**: Learn everything about the deep research tool

**Function**: `research_tool_standalone("research_deep")`

**Result**:
```python
{
  "name": "research_deep",
  "description": "12-stage deep research pipeline with auto-escalation",
  "category": "search",
  "subcategory": "web_search",
  "capabilities": [
    "accepts_query",
    "returns_structured",
    "calls_external_api",
    "calls_llm"
  ],
  "input_types": ["query"],
  "output_types": ["research_results"],
  "related_tools": {
    "dependencies": [
      "research_search",
      "research_fetch",
      "research_markdown"
    ],
    "connects_to": [
      "research_knowledge_graph",
      "research_consensus"
    ],
    "same_category": [
      "research_search",
      "research_github",
      "research_dark_forum",
      "research_multi_search"
    ]
  },
  "typical_pipelines": [
    "research_search → research_deep",
    "research_deep → research_knowledge_graph",
    "research_deep → research_consensus"
  ]
}
```

**Use Case**: Before using a tool, get its full documentation automatically.

---

## Common Scenarios

### Scenario 1: "I need to research a person online"

```
Step 1: research_tool_catalog(category="osint")
  → Find OSINT tools: social_search, breach_check, domain_intel, etc.

Step 2: research_tool_pipeline("find person information")
  → Get suggested pipeline: search → fetch → extract → graph

Step 3: research_tool_standalone("research_social_search")
  → Learn how to use the social search tool
```

### Scenario 2: "I want to analyze a document"

```
Step 1: research_tool_catalog(category="document")
  → Find: pdf_extract, ocr, transcribe, table_extract, convert

Step 2: research_tool_pipeline("extract and analyze document")
  → Get pipeline: pdf_extract → llm_extract → llm_classify

Step 3: Use the suggested tools in sequence
```

### Scenario 3: "I need security analysis"

```
Step 1: research_tool_catalog(category="security")
  → Find: cert_analyze, security_headers, cve_lookup, threat_intel

Step 2: research_tool_pipeline("assess web vulnerability")
  → Get pipeline: cert_analyze → headers → cve → threat_intel

Step 3: Execute the pipeline step by step
```

### Scenario 4: "I want LLM-powered analysis"

```
Step 1: research_tool_catalog(capability="calls_llm")
  → Find all 11 LLM-powered tools

Step 2: research_tool_standalone("research_knowledge_graph")
  → Learn it extracts entities and relationships using LLM

Step 3: Use knowledge graph on your content
```

### Scenario 5: "Show me how tools connect"

```
Step 1: research_tool_graph()
  → Get nodes, edges, and clusters

Step 2: Visualize edges like:
  - search → fetch → markdown → extract → graph
  - fetch → markdown → llm_summarize → classify
  - whois → dns → ip_geo → correlate

Step 3: Build custom pipelines based on connections
```

---

## Integration in Your Workflow

### Step 1: Discovery
```
research_tool_catalog(category="category_name")
research_tool_catalog(capability="capability_name")
```

### Step 2: Plan
```
research_tool_pipeline("your goal here")
```

### Step 3: Learn
```
research_tool_standalone("tool_name_here")
```

### Step 4: Execute
Use the tools returned by pipeline builder

### Step 5: Feedback
Catalog gets better as more tools are added

---

## Tool Availability

**Currently Available: 51 tools documented**

By category:
- Scraping: 8 tools
- Search: 5 tools  
- LLM: 7 tools
- OSINT: 8 tools
- Security: 5 tools
- Document: 5 tools
- Graph: 3 tools
- Pipeline: 3 tools
- Monitoring: 2 tools
- System: 6 tools
- Crypto: 4 tools
- Career: 5 tools
- Academic: 4 tools
- Creative: 4 tools

**Total: 51 core tools** (with 325+ additional specialized tools available through extended integration)

---

## Tips

1. **Start with discovery**: Use `research_tool_catalog` to explore what's available
2. **Use the pipeline builder**: Let `research_tool_pipeline` suggest sequences
3. **Check connections**: Use `research_tool_graph` to understand data flow
4. **Read the docs**: Use `research_tool_standalone` before using a tool
5. **Combine tools**: Most powerful results come from chaining tools together

---

## Error Handling

If a tool doesn't exist:
```python
result = research_tool_standalone("nonexistent_tool")
# Returns: {"error": "Tool 'nonexistent_tool' not found", "available_tools": [...]}
```

If a category doesn't match:
```python
result = research_tool_catalog(category="invalid_category")
# Returns: {"tools": [], "total_count": 0, ...}
```

---

## See Also

- `TOOL_CATALOG_GUIDE.md` - Complete API documentation
- `TOOL_CATALOG_IMPLEMENTATION.md` - Technical implementation details
- Tool modules in `src/loom/tools/` - Actual tool implementations
