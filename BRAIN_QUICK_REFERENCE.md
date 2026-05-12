# LOOM BRAIN — Quick Reference Guide

## What is BRAIN?

A **five-layer cognitive orchestration system** that transforms natural language requests into optimized tool execution plans for the Loom MCP server.

```
User Request → PERCEPTION → MEMORY → REASONING → ACTION → REFLECTION → Result
```

---

## Five Layers at a Glance

| Layer | Input | Process | Output |
|-------|-------|---------|--------|
| **PERCEPTION** | Natural language | Intent detection, entity extraction, complexity classification | Intent (action, entities, keywords, complexity) |
| **MEMORY** | Intent | Embed intent, lookup similar tools, load session context | MemoryContext (tool suggestions, embeddings) |
| **REASONING** | Intent + Context | Tool selection, workflow planning, cost estimation | Plan (primary tool, workflow steps, quality mode) |
| **ACTION** | Plan | Extract params (LLM), validate (Pydantic), execute tool, retry on error | ExecutionResult (success, result, cost, duration) |
| **REFLECTION** | Result | Validate output, update stats, detect drift, learn | LearningSignal (usage stats, metrics) |

---

## Core Data Types

```python
# Intent: What the user wants
Intent(
    user_request="Search for Python web scraping",
    primary_intent="search",
    entities={"language": "Python", "topic": "web scraping"},
    complexity="simple",
    keywords=["search", "python", "web", "scraping"]
)

# Plan: How to do it
Plan(
    primary_tool="research_search",
    params_template={"query": "Python web scraping"},
    workflow_steps=[],
    quality_mode="economy"  # Use free providers
)

# Result: Did it work?
BrainResult(
    success=True,
    data={"tools": ["beautifulsoup", "scrapy", "selenium"]},
    tool_used="research_search",
    cost_usd=0.0,
    duration_ms=2350.5
)
```

---

## Main API Entry Point

```python
result = await research_smart_call(
    request="Search for Python web scraping libraries",
    tool="auto",           # auto-detect or specify tool name
    quality_mode="auto",   # "auto", "max" (premium), "economy" (free)
    session_id=None        # optional session context
)

print(result["success"])      # bool
print(result["data"])         # result from tool
print(result["tool_used"])    # "research_search"
print(result["cost_usd"])     # 0.0 (free tier)
print(result["duration_ms"])  # 2350.5
```

---

## Quality Modes

### `quality_mode="max"` (Premium)
- Uses: Anthropic Claude, OpenAI GPT-4
- Cost: ~$1-5 per call
- Best for: Complex reasoning, ambiguous intents, creative synthesis
- Speed: 3-5 seconds for LLM operations

### `quality_mode="economy"` (Free)
- Uses: Groq, NVIDIA NIM
- Cost: ~$0 (free tier)
- Best for: Simple factual queries, classifications, lookups
- Speed: 100-500ms for LLM operations

### `quality_mode="auto"` (Default)
- Auto-selects based on query complexity
- Simple queries → economy (free)
- Medium queries → gemini/deepseek (cheap)
- Complex queries → anthropic/openai (premium)

---

## File Structure

```
src/loom/brain/
├── __init__.py              # Exports
├── core.py                  # Brain class (main orchestrator)
├── types.py                 # Intent, Plan, Result dataclasses
├── prompts.py               # LLM prompts
├── perception.py            # Intent detection
├── memory.py                # Embeddings + session context
├── reasoning.py             # Tool selection + planning
├── action.py                # Param extraction + execution
├── reflection.py            # Learning + validation
└── params_extractor.py      # LLM-based param extraction
```

---

## Integration Points

| Component | Reuses From | Purpose |
|-----------|------------|---------|
| Tool selection | `semantic_router.py` | Embedding-based tool matching |
| Fallback routing | `smart_router.py` | Keyword-based tool lookup |
| Workflows | `tool_recommender_v2.py` | CO_OCCURRENCE_MAP, WORKFLOW_TEMPLATES |
| Complexity classification | `model_router.py` | Determine cost tier |
| LLM cascade | `llm.py` | Provider fallback (Groq → NVIDIA → DeepSeek → ...) |
| Param validation | `params.py` | Pydantic v2 schemas |
| Tool execution | `server.py` | MCP tool registration + execution |

---

## Implementation Timeline (12 days)

**Phase 1 (Days 1-2)**: Core infrastructure
- Package structure, type definitions, prompts
- Tests: conftest, fixtures

**Phase 2 (Days 3-4)**: Perception + Memory
- Intent detection, embeddings-based tool lookup
- Tests: unit tests for P1+P2

**Phase 3 (Days 5-6)**: Reasoning + Planning
- Tool selection, workflow detection
- Tests: integration tests with real tool metadata

**Phase 4 (Days 7-8)**: Action + Execution
- Param extraction (LLM), execution, retries
- Tests: param extraction, action execution

**Phase 5 (Day 9)**: Reflection
- Learning, validation, outcome tracking

**Phase 6 (Day 10)**: Integration
- MCP server integration (research_smart_call)
- End-to-end tests

**Phase 7 (Days 11-12)**: Optimization + docs
- Performance tuning, error handling, documentation

---

## Multi-Step Workflows

Automatically detects and executes multi-step requests:

```python
# User request with implicit workflow
result = await research_smart_call(
    "Search for Python web scraping repos, then analyze code quality"
)

# Automatically becomes:
# Step 1: research_search("Python web scraping repos")
# Step 2: research_fetch(top_result_url)
# Step 3: research_analyze_code(fetched_content)
```

Workflow detection via:
1. Sequencing keywords ("then", "next", "also")
2. Intent stacking (multiple verbs)
3. CO_OCCURRENCE_MAP (tools commonly used together)

---

## Parameter Extraction

The ACTION layer uses LLM to extract parameters from natural language:

```
User Request: "Search GitHub for Django projects in Python"
           ↓
Param Extraction Prompt:
  Tool: research_github
  Schema: {query: str (required), kind: str (enum: repo/code/issues)}
           ↓
LLM Response: {"params": {"query": "Django projects Python", "kind": "repo"}}
           ↓
Validation: Validate types against Pydantic schema
           ↓
Fuzzy Correction: _fuzzy_correct_params() fixes typos
           ↓
Execute: Call tool with validated params
```

---

## Testing Strategy

**Test Coverage Target**: 80%+

```
tests/test_brain/
├── test_perception.py       # Intent detection
├── test_memory.py           # Embeddings + context
├── test_reasoning.py        # Tool selection + planning
├── test_action.py           # Param extraction + execution
├── test_reflection.py       # Learning
├── test_integration.py      # End-to-end flows
└── test_e2e_workflows.py    # Multi-step workflows
```

**Test Fixtures**:
- Mock embeddings (avoid large model downloads)
- Mock tool params (sample of tool_params.json)
- Sample Intent/Plan/Result objects
- Mock LLM responses

---

## Configuration

```python
# src/loom/config.py

BRAIN_ENABLED = True                          # Enable Brain orchestration
BRAIN_QUALITY_MODE = "auto"                   # Default quality mode
BRAIN_EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # Embedding model
BRAIN_CACHE_EMBEDDINGS = True                 # Cache tool embeddings
BRAIN_ENABLE_LEARNING = True                  # Track usage patterns
BRAIN_PARAM_EXTRACTION_TEMPERATURE = 0.3      # LLM temperature
BRAIN_MAX_RETRIES = 3                         # Retry policy
BRAIN_TIMEOUT_SEC = 60                        # Execution timeout
BRAIN_COST_CAP_USD = 5.0                      # Daily cost cap
```

---

## Error Handling

```python
# Graceful degradation on failures

try:
    # Attempt to extract params with LLM
    params = await extract_params_with_llm(plan, quality_mode="max")
except ParamExtractionError:
    # Fallback to heuristics
    logger.warning("LLM param extraction failed, using heuristics")
    params = extract_params_heuristic(plan)

try:
    # Execute tool
    result = await execute_tool(plan.primary_tool, params)
except ToolError as e:
    # Retry with alternative tool
    logger.warning(f"Tool failed: {e}, retrying with alternative")
    result = await execute_tool(plan.alternatives[0], params)
```

---

## Example Flows

### Simple Search
```
Request: "Search for Python web scraping"
↓
PERCEPTION: Intent(primary="search", complexity="simple")
↓
MEMORY: Suggestions=[research_search (0.99), research_deep (0.85)]
↓
REASONING: Plan(tool="research_search", quality="economy")
↓
ACTION: Extract params → Execute research_search
↓
Result: {success: true, data: [repos], cost: 0.0}
```

### Complex Analysis
```
Request: "Search GitHub for Django projects, fetch top 3 READMEs, summarize each"
↓
PERCEPTION: Intent(primary="search", complexity="complex")
↓
MEMORY: Suggestions=[research_github, research_fetch, research_llm_summarize]
↓
REASONING: Plan(
    tool="research_github",
    workflow=[
      {tool: "research_github", params: {query: "Django"}},
      {tool: "research_fetch", params: {urls: [top_3]}},
      {tool: "research_llm_summarize", params: {texts: [READMEs]}}
    ],
    quality="max"
)
↓
ACTION: Execute 3-step workflow
↓
Result: {success: true, data: [summaries], cost: 2.5}
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Five layers | Modular, testable, reuses existing code |
| LLM-based param extraction | Handles complex intents, adaptable to new tools |
| Quality modes | User control over cost/quality trade-off |
| Reuse existing subsystems | Leverage battle-tested code, avoid duplication |
| Async orchestration | Scalable, non-blocking |
| Sentence-transformers for embeddings | Lightweight, no external API required |

---

## Performance Targets

| Operation | Target Latency |
|-----------|-----------------|
| Intent detection | <50ms (simple), <500ms (complex) |
| Embeddings lookup | 50-100ms |
| Tool selection | <100ms |
| Plan generation | 100-500ms (simple), 500-2000ms (complex) |
| Param extraction (LLM) | 500-2000ms |
| Tool execution | 1-30s (depends on tool) |
| **Total request** | 1.5-35s (mostly tool execution) |

---

## Deployment Checklist

- [ ] Create `src/loom/brain/` package
- [ ] Implement all 5 layers
- [ ] Write 80%+ test coverage
- [ ] Integration tests with real tool metadata
- [ ] Performance benchmarks (latency < 35s)
- [ ] Error handling & recovery
- [ ] Documentation (API ref, examples, troubleshooting)
- [ ] Register `research_smart_call` in server.py
- [ ] Update CLAUDE.md
- [ ] Merge to main branch

---

## FAQ

**Q: Do I need to install additional dependencies?**  
A: sentence-transformers (for embeddings). All others are already in Loom.

**Q: Can I use my own LLM provider?**  
A: Yes, through the LLM_CASCADE_ORDER config. BRAIN respects quality modes.

**Q: What if param extraction fails?**  
A: Falls back to heuristics, then uses tool defaults. Retries with higher quality mode.

**Q: Does BRAIN require internet?**  
A: Only for the underlying tools (research_search, research_fetch, etc.). Intent detection is local.

**Q: How much does it cost?**  
A: Depends on quality_mode. Economy: ~$0 (free). Max: ~$1-5 per request.

**Q: Can I cache results?**  
A: Yes, BRAIN caches embeddings and tool suggestions. Semantic caching coming in v2.

---

## References

- Full architecture: `/Users/aadel/projects/loom/BRAIN_ARCHITECTURE_OPUS.md`
- Existing subsystems: `src/loom/tools/{semantic_router,smart_router,tool_recommender_v2,model_router}.py`
- Tool metadata: `docs/tool_params.json`
- MCP server: `src/loom/server.py`
