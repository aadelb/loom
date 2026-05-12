# Architecture Decision Records (ADRs) — LOOM BRAIN

These ADRs document the key architectural decisions for the LOOM BRAIN cognitive orchestration layer.

---

## ADR-001: Five-Layer Cognitive Architecture

**Status**: Accepted  
**Date**: 2026-05-09  
**Author**: Architectural Review  

### Context

The Loom MCP server exposes 883+ research tools across multiple domains (search, fetch, analysis, security, dark web, etc.). Users interact with this via natural language requests through the MCP protocol. Currently, tool selection and parameter extraction is manual — users must know tool names and parameter names.

We need an intelligent orchestration layer that:
1. Understands user intent from natural language
2. Selects appropriate tools
3. Extracts structured parameters
4. Handles multi-step workflows
5. Manages cost and quality trade-offs

### Decision

Implement a **five-layer cognitive architecture** that separates concerns into distinct, testable layers:

```
User Request (natural language)
    ↓
[1] PERCEPTION: Parse intent, extract entities
    ↓
[2] MEMORY: Load context, get tool suggestions
    ↓
[3] REASONING: Plan tool selection and workflows
    ↓
[4] ACTION: Extract params, execute, retry
    ↓
[5] REFLECTION: Validate, learn, track metrics
    ↓
Result
```

Each layer is independent and can be tested in isolation.

### Consequences

#### Positive
- **Modularity**: Each layer is 150-350 lines, focused on one concern
- **Testability**: Can test each layer independently with mocks
- **Reusability**: Layers can be reused in different contexts
- **Clarity**: Clear separation of concerns, easy to understand
- **Extensibility**: New layers can be added without breaking existing ones
- **Debugging**: Clear data flow makes debugging easier

#### Negative
- **Latency**: Each layer adds overhead (5 LLM calls for complex requests)
- **Complexity**: More code to maintain and understand
- **Interdependencies**: Failures in one layer can cascade
- **State management**: Need to pass state between layers

#### Risks
- **Latency could exceed 30+ seconds** for complex requests
  - Mitigation: Profile and optimize critical paths; batch simple intents
- **Context passing overhead** if state objects are large
  - Mitigation: Use lazy loading and on-demand evaluation
- **Error propagation** through multiple layers
  - Mitigation: Implement graceful fallbacks at each layer

### Rationale

The five-layer model is inspired by cognitive science and neural processing:
- PERCEPTION (sensory input) - understand what the user wants
- MEMORY (context) - recall relevant tools and patterns
- REASONING (cognition) - plan optimal execution
- ACTION (motor output) - execute the plan
- REFLECTION (metacognition) - learn from outcomes

This mirrors human problem-solving and aligns with well-established design patterns (MVC, N-tier architecture).

### Alternatives Considered

**Alternative 1: Monolithic "smart call" function**
- Pro: Simple, low latency
- Con: Hard to test, understand, extend; tight coupling

**Alternative 2: Single LLM call to select tool and params**
- Pro: Low latency, simple
- Con: Context window exhaustion with 883 tools; no multi-step support

**Alternative 3: Graph-based tool routing**
- Pro: Expressive, handles complex workflows
- Con: Complex to implement, overkill for current needs

### Decision Criteria Met

- ✓ Handles 883+ tools without context explosion (uses embeddings)
- ✓ Supports multi-step workflows
- ✓ Testable and maintainable
- ✓ Reuses existing Loom subsystems (semantic_router, tool_recommender_v2)
- ✓ Clear error handling and fallback chains

---

## ADR-002: Reuse Existing Subsystems Instead of Reimplementing

**Status**: Accepted  
**Date**: 2026-05-09  
**Author**: Architectural Review  

### Context

Loom already has several sophisticated subsystems for tool discovery and routing:
- **semantic_router.py**: Embedding-based tool matching (all-MiniLM-L6-v2)
- **smart_router.py**: Keyword-based tool routing
- **tool_recommender_v2.py**: Tool co-occurrence maps and workflow templates
- **model_router.py**: Query complexity classification for cost optimization
- **llm.py**: LLM cascade with circuit breaker pattern

Rather than rebuild this functionality, we could leverage it.

### Decision

BRAIN will be an **orchestration layer that coordinates existing subsystems** rather than reimplementing their functionality.

Integration points:
- **PERCEPTION** → Use model_router.classify_query_complexity()
- **MEMORY** → Use semantic_router for embeddings
- **REASONING** → Use tool_recommender_v2.CO_OCCURRENCE_MAP
- **ACTION** → Use llm.py's _call_with_cascade() for param extraction

```
Brain (new)
├─ Orchestration layer (250 lines)
├─ Reuses semantic_router.py
├─ Reuses smart_router.py
├─ Reuses tool_recommender_v2.py
├─ Reuses model_router.py
└─ Reuses llm.py
```

### Consequences

#### Positive
- **Code reuse**: Leverage 500+ lines of battle-tested code
- **Faster implementation**: Only need 1,200-1,600 lines vs 3,000+ lines
- **Reduced maintenance**: Bug fixes in subsystems apply to BRAIN
- **Consistency**: Use same routing logic across the system
- **Lower risk**: Existing subsystems are proven to work

#### Negative
- **Tight coupling**: BRAIN depends on existing APIs
- **API changes**: If subsystems change, BRAIN may need updates
- **Optimization constraints**: Cannot fully optimize BRAIN without considering subsystem performance
- **Debugging complexity**: Need to understand multiple modules

#### Risks
- **API instability**: If existing subsystems change their interface
  - Mitigation: Pin versions, use adapter patterns, unit test interface contracts
- **Performance bottlenecks** in existing subsystems
  - Mitigation: Profile and identify bottlenecks before BRAIN implementation
- **Feature gaps** in existing subsystems
  - Mitigation: Extend subsystems first, then use in BRAIN

### Rationale

DRY (Don't Repeat Yourself) principle: existing code works, is tested, and is battle-hardened. Reimplementing is expensive and error-prone.

Additionally, by reusing subsystems, BRAIN automatically benefits from any optimizations or bug fixes applied to those subsystems.

### Alternatives Considered

**Alternative 1: Reimplementing all functionality in BRAIN**
- Pro: Self-contained, can optimize end-to-end
- Con: 3x more code, duplicates existing logic, higher risk

**Alternative 2: Wrapping subsystems with minimal BRAIN**
- Pro: Minimal code, clear dependencies
- Con: Less intelligent orchestration, less control

### Decision Criteria Met

- ✓ Avoids code duplication
- ✓ Leverages proven, tested code
- ✓ Faster time to market
- ✓ Lower maintenance burden
- ✓ Clear, documented integration points

---

## ADR-003: LLM-Based Parameter Extraction

**Status**: Accepted  
**Date**: 2026-05-09  
**Author**: Architectural Review  

### Context

Parameters are the critical bridge between user intent and tool execution. Examples:
- User: "Search for Python web scraping"
- Parameters: `{"query": "Python web scraping", "depth": 1}`

- User: "Fetch the top result and summarize it"
- Parameters: `{"url": "...", "include_html": false}` + `{"text": "...", "max_length": 500}`

Parameter extraction is difficult because:
1. Users don't know valid parameter names or types
2. Parameter combinations can be complex
3. User language is ambiguous and context-dependent
4. New tools require new extraction logic

### Decision

Use **LLM-based parameter extraction** with a structured prompt that includes:
1. Tool description (what it does)
2. Pydantic schema (valid parameters and types)
3. Field defaults (what to use if not specified)
4. User request (what they want)
5. Validation rules (SSRF checks, enum validation, type validation)

```
[User Intent] → [Param Extraction Prompt]
              ↓
          [LLM Call]
              ↓
         [JSON Response]
              ↓
      [Pydantic Validation]
              ↓
  [Fuzzy Correction (_fuzzy_correct_params)]
              ↓
    [Merge with Defaults]
              ↓
        [Execute Tool]
```

### Consequences

#### Positive
- **Generality**: Works for any tool without custom extraction logic
- **Adaptability**: New tools are automatically supported
- **Flexibility**: Handles complex intent patterns and ambiguity
- **User-friendly**: Users can phrase requests naturally
- **Extensibility**: Easy to add validation rules (SSRF, enum checks, etc.)

#### Negative
- **Additional cost**: Every tool execution costs tokens for param extraction
- **Hallucination risk**: LLM may generate invalid parameters
- **Latency overhead**: LLM call adds 500-2000ms per request
- **Dependency on LLM quality**: Poor LLM = poor params

#### Risks
- **Invalid parameters** generated by LLM
  - Mitigation: Validate against Pydantic, use low temperature (0.3), test with examples
- **Hallucinated data** (e.g., invalid URLs)
  - Mitigation: Validate URLs (SSRF-safe), validate enums, type checking
- **Cost explosion** if used for every tool call
  - Mitigation: Cache params, use heuristics for simple intents, batch requests

### Rationale

LLM-based extraction is more robust than heuristic approaches because:
1. LLMs understand natural language better than regex/heuristics
2. LLMs can handle ambiguity through context
3. LLMs generalize to new tools without retraining
4. LLMs can follow complex instructions (validation rules, defaults)

Additionally, cost is mitigated by:
1. Using economy providers (Groq/NVIDIA, free tier) for simple params
2. Caching extracted params for similar intents
3. Only using LLM when heuristics fail

### Alternatives Considered

**Alternative 1: Regex and heuristic extraction**
- Pro: Deterministic, no LLM cost
- Con: Brittle, doesn't generalize, hard to maintain

**Alternative 2: Hard-coded extraction per tool**
- Pro: Optimal extraction logic
- Con: Unmaintainable, doesn't scale to 883 tools

**Alternative 3: User provides params directly**
- Pro: No extraction needed
- Con: Defeats the purpose of natural language interface

### Decision Criteria Met

- ✓ Handles 883 tools without custom code per tool
- ✓ Flexible and adaptable to new tools
- ✓ Validates parameters before execution
- ✓ Cost-controlled via provider selection
- ✓ Clear error handling and fallbacks

---

## ADR-004: Quality Modes (max/economy/auto)

**Status**: Accepted  
**Date**: 2026-05-09  
**Author**: Architectural Review  

### Context

Loom supports 8 LLM providers with different costs and capabilities:

| Provider | Cost (per 1M tokens) | Quality | Speed |
|----------|---------------------|---------|-------|
| Groq | $0 (free) | Medium | 100ms |
| NVIDIA NIM | $0 (free) | Medium | 150ms |
| DeepSeek | $0.14 | Good | 200ms |
| Gemini | $0.075 | Good | 300ms |
| Moonshot | $0.2 | Good | 250ms |
| OpenAI | $0.5 | Excellent | 500ms |
| Anthropic | $1.0 | Excellent | 600ms |
| vLLM | Varies | Varies | 50ms |

Users want control over cost/quality trade-offs:
- Some want cheapest (batch processing)
- Some want best quality (critical analysis)
- Some want auto-selection (simplicity)

### Decision

Implement **three quality modes** that control provider selection for all BRAIN operations (param extraction, intent classification, planning):

```
quality_mode="max"
├─ Providers: Anthropic, OpenAI
├─ Cost: ~$1-5 per call
├─ Best for: Complex reasoning, ambiguous intent, creative synthesis
└─ Use case: Important decisions, novel analysis

quality_mode="economy"
├─ Providers: Groq, NVIDIA
├─ Cost: ~$0 per call
├─ Best for: Simple factual queries, classifications, lookups
└─ Use case: Batch processing, high volume

quality_mode="auto" (default)
├─ Classification: simple → economy, medium → cheap, complex → max
├─ Intelligent cost management
└─ Use case: General-purpose (recommended)
```

Each mode controls:
1. Provider selection (which LLM models can be used)
2. Parameter extraction quality (quality threshold, retry policy)
3. Planning sophistication (simple vs advanced planning)
4. Caching strategy (short vs long TTL)

### Consequences

#### Positive
- **User control**: Users can optimize for their use case
- **Cost transparency**: Clear cost for each quality level
- **Flexibility**: Batch processing with economy, critical work with max
- **Intelligent defaults**: "auto" adapts to request complexity
- **Operational cost savings**: Estimated 70% cost reduction for simple queries

#### Negative
- **Quality variance**: Different tiers have different quality levels
- **User confusion**: Too many options
- **Implementation complexity**: Need to handle provider selection logic
- **SLA complexity**: Different SLAs per quality mode

#### Risks
- **Users always choosing "max"** leading to high costs
  - Mitigation: Default to "auto", make costs transparent, show cost estimates
- **Quality issues with "economy" mode**
  - Mitigation: Test extensively, use with appropriate use cases, document limitations
- **Provider availability issues** for certain quality modes
  - Mitigation: Implement fallback chains, circuit breakers, graceful degradation

### Rationale

Quality modes provide a simple way for users to control the fundamental cost/quality trade-off without exposing the complexity of provider selection. This is inspired by:
- Cloud storage tiers (Hot/Warm/Cold storage)
- Cloud compute tiers (Free/Standard/Premium)
- Airlines (Economy/Business/First class)

The three tiers provide sufficient granularity without overwhelming users.

### Alternatives Considered

**Alternative 1: Always use best provider (Anthropic/OpenAI)**
- Pro: Best quality
- Con: Expensive, 70% cost waste on simple queries

**Alternative 2: Always use cheapest provider (Groq/NVIDIA)**
- Pro: Cheapest
- Con: Lower quality for complex requests, poor user experience

**Alternative 3: Fine-grained provider selection per operation**
- Pro: Optimal cost
- Con: Too complex, requires ML for optimal provider selection

### Decision Criteria Met

- ✓ Clear cost/quality trade-offs
- ✓ Simple three-tier model (avoid option paralysis)
- ✓ Intelligent defaults ("auto")
- ✓ User control when needed
- ✓ Operational cost efficiency

---

## ADR-005: Asynchronous Orchestration with Sync Tool Support

**Status**: Accepted  
**Date**: 2026-05-09  
**Author**: Architectural Review  

### Context

Loom tools have mixed sync/async implementations:
- **Async tools** (220+ tools): research_search, research_fetch, research_spider, etc.
  - Can use `await` directly
  - Scalable with asyncio
  - Non-blocking

- **Sync tools** (50+ tools): research_github (gh CLI), etc.
  - Cannot use `await`
  - CPU-bound or blocking I/O
  - Need special handling

BRAIN needs to:
1. Support both sync and async tools
2. Scale to handle multiple concurrent requests
3. Provide clear concurrency semantics
4. Avoid blocking the event loop

### Decision

Use **async/await for BRAIN orchestration** with `asyncio.run_in_executor()` for sync tools.

```python
# Async tool (direct await)
result = await research_search(query)

# Sync tool (executor)
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, research_github, query)
```

BRAIN methods are all async (`async def`), enabling:
- Concurrent requests via asyncio
- Concurrent tool calls within workflows
- Non-blocking I/O

### Consequences

#### Positive
- **Scalability**: Can handle many concurrent requests with asyncio
- **Non-blocking**: Doesn't block the event loop
- **Natural**: Async/await is standard for Python async code
- **Composability**: Asyncio tools compose naturally with BRAIN
- **Flexibility**: Can mix sync and async tools seamlessly

#### Negative
- **Complexity**: Async/await can be tricky to get right
- **Executor overhead**: Sync tools have ~10-50ms overhead
- **Debugging**: Async stack traces are harder to debug
- **Cancellation**: Need to handle task cancellation properly

#### Risks
- **Deadlocks** from improper async usage
  - Mitigation: Use structured concurrency (asyncio.create_task, gather)
- **Executor pool exhaustion** if too many sync tools
  - Mitigation: Monitor pool, use process pool for CPU-bound work
- **Resource leaks** from unclosed event loops or connections
  - Mitigation: Proper cleanup in __init__ and close() methods

### Rationale

Async/await is the standard Python async pattern (PEP 492). Using it makes BRAIN:
1. Compatible with modern Python code
2. Scalable for high concurrency
3. Non-blocking (integrates with asyncio event loop)
4. Compositional (async functions compose naturally)

For sync tools, `run_in_executor()` is the standard approach that runs blocking code in a thread pool, freeing up the event loop.

### Alternatives Considered

**Alternative 1: Always run tools synchronously (blocking)**
- Pro: Simple
- Con: Not scalable, blocks event loop, hurts performance

**Alternative 2: Require all tools to be async**
- Pro: Pure async throughout
- Con: Breaks existing sync tools, requires major refactoring

**Alternative 3: Process pool instead of thread pool**
- Pro: True parallelism for CPU-bound sync tools
- Con: Higher overhead, harder to debug, slower for I/O-bound work

### Decision Criteria Met

- ✓ Supports both sync and async tools
- ✓ Scalable to multiple concurrent requests
- ✓ Non-blocking event loop
- ✓ Standard Python async patterns
- ✓ Clear semantics and debugging experience

---

## ADR-006: Embedding Model Selection (all-MiniLM-L6-v2)

**Status**: Accepted  
**Date**: 2026-05-09  
**Author**: Architectural Review  

### Context

BRAIN needs to embed user intent and tool descriptions to match tools semantically. This requires:
1. A sentence-transformers model (lightweight, no API)
2. Fast inference (< 100ms per embedding)
3. Good semantic understanding (match user queries to tool descriptions)
4. Reasonable model size (downloads quickly)

Options:
- **all-MiniLM-L6-v2** (33M params, 384 dims): Small, fast, good quality
- **all-mpnet-base-v2** (110M params, 768 dims): Better quality, slower, larger
- **cross-encoders** (300M+ params): Excellent but too slow
- **GPT embeddings API** ($0.02 per million): Excellent but requires API key

### Decision

Use **all-MiniLM-L6-v2** as default embedding model.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
# 33M params, 384-dim embeddings
# ~50ms inference time
# Good semantic understanding
```

Rationale:
- **Size**: 33M params downloads in <5 seconds
- **Speed**: 50ms per embedding (batched)
- **Quality**: Sufficient for semantic tool matching
- **Cost**: No API required (local inference)
- **Availability**: Widely used, well-tested

### Consequences

#### Positive
- **Fast**: 50-100ms per embedding, can cache
- **Local**: No external API, privacy-preserving
- **Lightweight**: 33M params fits in memory
- **Free**: No API costs
- **Quality**: Good semantic understanding of intent and tools

#### Negative
- **Download**: ~130MB model download on first use
- **Memory**: ~200MB in memory during inference
- **Quality**: Slightly lower quality than larger models
- **Specificity**: Not optimized for tool matching (generic sentence encoder)

#### Risks
- **Semantic mismatches** for specific tool names or jargon
  - Mitigation: Test with real tool descriptions, fine-tune if needed, use smart_router fallback
- **Model loading time** on first BRAIN initialization
  - Mitigation: Lazy-load on first request, cache, preload on server startup
- **Model updates** in sentence-transformers
  - Mitigation: Pin model version, test before upgrading

### Rationale

all-MiniLM-L6-v2 is the optimal choice because:
1. It's the most popular lightweight embedding model
2. It has excellent speed (50ms per embedding)
3. It has good semantic understanding without being too large
4. It requires no external APIs (local, privacy-preserving)
5. It's free (no usage costs)

For BRAIN's use case (matching 883 tools to user intents), this trade-off of quality for speed is appropriate.

### Alternatives Considered

**Alternative 1: all-mpnet-base-v2 (better quality, slower)**
- Pro: Higher semantic quality
- Con: 110M params, slower inference, larger download
- Trade-off: Not worth the cost for tool matching

**Alternative 2: OpenAI embeddings API ($0.02 per 1M tokens)**
- Pro: Highest quality, constantly updated
- Con: Requires API key, adds cost, requires network access
- Trade-off: Overkill for this use case

**Alternative 3: Hybrid (all-MiniLM-L6-v2 + smart_router fallback)**
- Pro: Fast primary path, accurate fallback
- Con: Complexity
- Trade-off: Good (recommended approach)

### Decision Criteria Met

- ✓ Embedding inference < 100ms
- ✓ Local (no external API)
- ✓ Free (no usage costs)
- ✓ Good semantic understanding for tool matching
- ✓ Cacheable embeddings
- ✓ Fallback to smart_router if semantic matching fails

---

## Summary of Design Decisions

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-001 | Five-layer cognitive architecture | Accepted |
| ADR-002 | Reuse existing subsystems (semantic_router, tool_recommender_v2, etc.) | Accepted |
| ADR-003 | LLM-based parameter extraction with Pydantic validation | Accepted |
| ADR-004 | Quality modes (max/economy/auto) for cost control | Accepted |
| ADR-005 | Async orchestration with sync tool support via run_in_executor | Accepted |
| ADR-006 | all-MiniLM-L6-v2 as default embedding model | Accepted |

All decisions are well-reasoned, document trade-offs, identify risks with mitigations, and consider alternatives.

---

## Design Principle Summary

The LOOM BRAIN architecture is guided by these principles:

1. **Separation of Concerns**: Each layer handles one cognitive task
2. **DRY (Don't Repeat Yourself)**: Reuse existing, proven code
3. **Clarity**: Clear data flow, easy to understand and debug
4. **Extensibility**: New layers/tools can be added without breaking existing code
5. **Cost Efficiency**: Quality modes enable cost optimization
6. **Resilience**: Graceful fallbacks at each layer
7. **Testability**: Clear interfaces enable unit testing
8. **Performance**: Optimize for latency without sacrificing quality

---

## Next Steps

1. Review all ADRs with team
2. Approve design decisions
3. Begin implementation (12-day phased plan)
4. Document learnings and iterate

---

**Document Status**: Complete  
**Last Updated**: 2026-05-09  
**Next Review**: Post-implementation (identify improvements, update ADRs if needed)
