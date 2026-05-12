# LOOM BRAIN Architecture — Cognitive Orchestration Layer for 883 Tools

**Status**: Architecture Design (Ready for Implementation)  
**Author**: Architectural Review  
**Date**: 2026-05-09  
**Context**: 4,951 lines of research from 7 AIs + 6 codebase exploration reports  
**Scope**: Cognitive orchestration layer for Loom research MCP server (883 tools, 8 LLM providers, 21 search engines)

---

## 1. Executive Summary

The **LOOM BRAIN** is a five-layer cognitive orchestration system that transforms unstructured user requests into optimized tool execution plans. It sits between the user/API and the Loom tool ecosystem, providing intelligent:

- **Intent detection** from natural language
- **Tool selection** via semantic + keyword routing
- **Parameter extraction** from user intent using LLM
- **Multi-step planning** for complex workflows
- **Quality-aware execution** with cost optimization
- **Outcome reflection** for continuous learning

The BRAIN reuses existing Loom subsystems (semantic_router, smart_router, tool_recommender_v2, model_router, cascade LLM) and adds a thin orchestration layer that routes requests to optimal tools without exceeding context windows.

---

## 2. Architecture Overview

### 2.1 Five-Layer Cognitive Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  USER REQUEST (natural language)                            │
│  "Find GitHub repos for Python web scraping then analyze"   │
└────────────────┬────────────────────────────────────────────┘
                 │
         ┌───────▼─────────┐
         │ PERCEPTION      │  Parse intent, extract entities
         │ (llm.py based)  │  Keywords: search, analyze
         └────────┬────────┘  Complexity: medium
                  │           Entities: {domain: web scraping}
         ┌────────▼──────────┐
         │ MEMORY            │  Load tool embeddings
         │ (caching layer)   │  Recommend tools (co-occurrence)
         └────────┬──────────┘  Session context lookup
                  │
         ┌────────▼──────────────┐
         │ REASONING             │  Tool selection logic
         │ (semantic + keyword)  │  Multi-step planning
         └────────┬──────────────┘  Fetch → Summarize workflow
                  │
         ┌────────▼──────────────────┐
         │ ACTION                     │  Extract params from intent
         │ (cascade + quality modes)  │  Validate via Pydantic
         └────────┬──────────────────┘  Execute with retry logic
                  │
         ┌────────▼──────────────┐
         │ REFLECTION            │  Validate results
         │ (learning + feedback) │  Update usage stats
         └────────┬──────────────┘  Learn from outcomes
                  │
         ┌────────▼──────────────┐
         │ RESULT ENVELOPE       │  {success, data, cost, time}
         └───────────────────────┘
```

### 2.2 Data Flow: Request to Result

```
User Request
  │
  ├─ Intent Detection (NLP)
  │  └─ Extract: primary_intent, entities, complexity, keywords
  │
  ├─ Tool Selection
  │  ├─ Semantic Router: cosine similarity on embeddings
  │  ├─ Smart Router: keyword matching fallback
  │  ├─ Tool Recommender: co-occurrence suggestions
  │  └─ Select: {primary_tool, alternatives, confidence}
  │
  ├─ Multi-Step Planning (if workflow detected)
  │  ├─ Check CO_OCCURRENCE_MAP for sequential tools
  │  ├─ Build execution DAG
  │  └─ Output: {primary_tool, workflow_steps, quality_mode}
  │
  ├─ Parameter Extraction (LLM-based)
  │  ├─ Load tool's Pydantic schema from tool_params.json
  │  ├─ Call LLM with param extraction prompt
  │  ├─ Parse JSON response
  │  └─ Apply _fuzzy_correct_params() for typo correction
  │
  ├─ Execution (with quality mode)
  │  ├─ If quality_mode="max": force Anthropic/OpenAI
  │  ├─ If quality_mode="economy": force Groq/NVIDIA
  │  ├─ If quality_mode="auto": use classify_query_complexity()
  │  ├─ Call tool via MCP framework
  │  ├─ Retry on transient errors (3x exponential backoff)
  │  └─ Capture: {result, duration, cost, error}
  │
  ├─ Reflection & Learning
  │  ├─ Validate output schema
  │  ├─ Update tool usage stats
  │  ├─ Detect drift/anomalies
  │  └─ Return: {success, data, cost_usd, duration_ms}
```

---

## 3. File Structure

### 3.1 New BRAIN Package

```
src/loom/brain/
├── __init__.py                  # Package exports
├── core.py                      # Brain class (250-300 lines)
├── perception.py                # Intent detection (150-200 lines)
├── memory.py                    # Embeddings cache, session context (150-200 lines)
├── reasoning.py                 # Tool selection, planning (200-250 lines)
├── action.py                    # Param extraction, execution (200-250 lines)
├── reflection.py                # Result validation, learning (100-150 lines)
├── params_extractor.py          # LLM-based param extraction (150-200 lines)
├── types.py                     # DataClasses: Intent, Plan, Result (100-150 lines)
└── prompts.py                   # Prompt templates (80-120 lines)

Total: ~1200-1600 lines of well-structured, testable code
```

### 3.2 Integration Points (Existing Files)

```
src/loom/
├── server.py
│  └─ Add: async def research_smart_call(...) → BrainResult
│     (calls Brain.process() internally)
│
├── tools/
│  ├── llm.py
│  │  └─ Reuse: _call_with_cascade(), circuit breaker pattern
│  │
│  ├── semantic_router.py
│  │  └─ Reuse: research_semantic_route() for tool matching
│  │
│  ├── smart_router.py
│  │  └─ Reuse: research_route_query() for keyword fallback
│  │
│  ├── tool_recommender_v2.py
│  │  └─ Reuse: CO_OCCURRENCE_MAP, WORKFLOW_TEMPLATES
│  │
│  └── model_router.py
│     └─ Reuse: classify_query_complexity() for cost optimization
│
├── config.py
│  └─ Add: BRAIN_ENABLED, BRAIN_QUALITY_MODE configs
│
└── params.json (existing)
   └─ Reuse: 806 tool parameter definitions
```

---

## 4. Core Brain Class Definition

### 4.1 Brain Class Structure (pseudo-code)

```python
# src/loom/brain/core.py

from dataclasses import dataclass
from typing import Literal, Any
import numpy as np
import asyncio

from loom.brain.types import Intent, Plan, ExecutionResult, BrainResult
from loom.brain.perception import PerceptionEngine
from loom.brain.memory import MemorySystem
from loom.brain.reasoning import ReasoningEngine
from loom.brain.action import ActionExecutor
from loom.brain.reflection import ReflectionSystem

class Brain:
    """Cognitive orchestration layer for Loom MCP server.
    
    Five-layer architecture:
    1. PERCEPTION: Parse user intent and extract entities
    2. MEMORY: Load tool embeddings, session context, usage patterns
    3. REASONING: Select tools, plan multi-step workflows
    4. ACTION: Extract params, validate, execute with quality modes
    5. REFLECTION: Validate results, learn from outcomes
    """
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        tool_params_path: str = "docs/tool_params.json",
        enable_caching: bool = True,
        enable_learning: bool = True,
    ):
        """Initialize Brain subsystems.
        
        Args:
            embedding_model: sentence-transformers model for tool matching
            tool_params_path: path to tool_params.json (ground truth)
            enable_caching: cache tool embeddings and intent history
            enable_learning: track usage patterns for optimization
        """
        self.perception = PerceptionEngine()
        self.memory = MemorySystem(
            embedding_model=embedding_model,
            tool_params_path=tool_params_path,
            enable_caching=enable_caching,
        )
        self.reasoning = ReasoningEngine(
            memory_system=self.memory,
            tool_params_path=tool_params_path,
        )
        self.action = ActionExecutor(
            memory_system=self.memory,
            tool_params_path=tool_params_path,
        )
        self.reflection = ReflectionSystem(
            enable_learning=enable_learning,
        )
        self._session_context: dict[str, Any] = {}
    
    async def process(
        self,
        request: str,
        tool: str = "auto",
        quality_mode: str = "auto",
        session_id: str | None = None,
        max_retries: int = 3,
        timeout_sec: int = 60,
    ) -> BrainResult:
        """End-to-end request processing.
        
        Main entry point: natural language → tool execution → result.
        
        Args:
            request: User natural language request
            tool: "auto" = detect tool, or specify tool name
            quality_mode: "auto", "max" (premium), "economy" (free)
            session_id: Optional session context
            max_retries: Retry count on transient errors
            timeout_sec: Execution timeout
        
        Returns:
            BrainResult: {success, data, cost_usd, duration_ms, tool_used, ...}
        
        Example:
            >>> result = await brain.process(
            ...     request="Find Python web scraping repos",
            ...     quality_mode="economy"
            ... )
            >>> print(result.data["recommended_tools"])
        """
        start_time = time.time()
        
        try:
            # 1. PERCEPTION: Parse intent
            intent = await self.perceive(request)
            
            # 2. MEMORY: Load context
            context = await self.remember(intent, session_id)
            
            # 3. REASONING: Select tools and plan
            plan = await self.reason(intent, context, tool=tool)
            
            # 4. ACTION: Execute
            result = await self.act(plan, quality_mode, max_retries, timeout_sec)
            
            # 5. REFLECTION: Learn
            learning_signal = await self.reflect(intent, plan, result)
            
            # Return envelope
            duration_ms = (time.time() - start_time) * 1000
            return BrainResult(
                success=result.success,
                data=result.result,
                tool_used=result.tool_used,
                params_used=result.params_used,
                cost_usd=result.cost_usd,
                duration_ms=duration_ms,
                quality_mode_used=plan.quality_mode,
                error=result.error,
                retries=result.retries,
                learning_signal=learning_signal,
            )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return BrainResult(
                success=False,
                data=None,
                error=str(e),
                duration_ms=duration_ms,
            )
    
    async def perceive(self, request: str) -> Intent:
        """PERCEPTION: Parse user intent and extract entities.
        
        Uses keyword detection + optional LLM for complex intent.
        Returns Intent with primary_intent, entities, complexity, keywords.
        """
        return await self.perception.detect_intent(request)
    
    async def remember(
        self,
        intent: Intent,
        session_id: str | None = None,
    ) -> MemoryContext:
        """MEMORY: Load context from embeddings and session history.
        
        - Embed intent using sentence-transformers
        - Look up similar tools (semantic + keyword)
        - Load session context if provided
        - Return MemoryContext with suggestions
        """
        return await self.memory.load_context(intent, session_id)
    
    async def reason(
        self,
        intent: Intent,
        context: MemoryContext,
        tool: str = "auto",
    ) -> Plan:
        """REASONING: Select tools and plan execution.
        
        - If tool != "auto": use specified tool
        - Else: select from suggestions using semantic ranking
        - Check CO_OCCURRENCE_MAP for multi-step workflows
        - Determine quality_mode from complexity
        - Return Plan with primary_tool, alternatives, workflow_steps
        """
        return await self.reasoning.generate_plan(intent, context, tool=tool)
    
    async def act(
        self,
        plan: Plan,
        quality_mode_override: str = "auto",
        max_retries: int = 3,
        timeout_sec: int = 60,
    ) -> ExecutionResult:
        """ACTION: Extract params, validate, execute with retries.
        
        - Extract params using LLM (with param extraction prompt)
        - Validate via Pydantic (tool_params_path)
        - Correct typos via _fuzzy_correct_params()
        - Execute via MCP cascade (respecting quality_mode)
        - Retry on transient errors (exponential backoff)
        - Return ExecutionResult with result, cost, duration
        """
        quality_mode = quality_mode_override if quality_mode_override != "auto" else plan.quality_mode
        return await self.action.execute(plan, quality_mode, max_retries, timeout_sec)
    
    async def reflect(
        self,
        intent: Intent,
        plan: Plan,
        result: ExecutionResult,
    ) -> dict[str, Any]:
        """REFLECTION: Validate results and learn.
        
        - Validate output schema
        - Update tool usage statistics
        - Detect drift/anomalies
        - Return learning_signal for continuous improvement
        """
        return await self.reflection.learn(intent, plan, result)
    
    async def close(self):
        """Cleanup: close embeddings model, flush cache."""
        await self.memory.close()
```

### 4.2 Type Definitions

```python
# src/loom/brain/types.py

from dataclasses import dataclass
from typing import Literal, Any
import numpy as np

@dataclass
class Intent:
    """Detected user intent from natural language."""
    user_request: str
    primary_intent: str  # e.g., "search", "fetch", "analyze"
    entities: dict[str, Any]  # extracted entities (e.g., {domain: "python", topic: "web scraping"})
    confidence: float  # 0-1
    complexity: Literal["simple", "medium", "complex"]
    keywords: list[str]  # tokenized request keywords

@dataclass
class MemoryContext:
    """Context loaded from memory systems."""
    session_id: str | None
    recent_tools: list[str]  # tools used in this session
    tool_suggestions: list[tuple[str, float]]  # [(tool_name, similarity_score), ...]
    embedding: np.ndarray  # intent embedding
    metadata: dict[str, Any]  # session data, recent params, etc.

@dataclass
class Plan:
    """Execution plan generated by reasoning layer."""
    primary_tool: str
    alternatives: list[str]
    params_template: dict[str, Any]  # LLM-suggested params (unvalidated)
    workflow_steps: list[dict]  # multi-step workflows: [{tool, params_template}, ...]
    estimated_cost: float
    reasoning: str  # human-readable explanation
    quality_mode: Literal["max", "economy"]

@dataclass
class ExecutionResult:
    """Result of tool execution."""
    success: bool
    tool_used: str
    params_used: dict[str, Any]
    result: Any
    error: str | None
    duration_ms: float
    cost_usd: float
    retries: int

@dataclass
class BrainResult:
    """Final result envelope returned to caller."""
    success: bool
    data: Any
    tool_used: str | None = None
    params_used: dict[str, Any] | None = None
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    quality_mode_used: str | None = None
    error: str | None = None
    retries: int = 0
    learning_signal: dict[str, Any] | None = None
```

---

## 5. Parameter Extraction Strategy

### 5.1 Param Extraction Prompt Template

```python
# src/loom/brain/prompts.py

PARAM_EXTRACTION_PROMPT = """You are an expert at extracting structured parameters from natural language requests.

TOOL DEFINITION:
- Name: {tool_name}
- Description: {tool_description}
- Pydantic Schema:
{pydantic_schema_json}

USER REQUEST:
{user_request}

TASK:
Extract all parameters required to call this tool based on the user's request.

RULES:
1. Only include parameters defined in the Pydantic schema
2. For each parameter:
   - If required and not specified in the request, return an error
   - If optional and not specified, omit it from the response
   - Validate the type matches the schema
   - Use field defaults if available
3. For list/array parameters: infer the list from the request context
4. For URL parameters: validate SSRF-safe (must be http/https, not file://)
5. For enum parameters: use exact values from the schema

RESPONSE FORMAT:
Return a JSON object with the extracted parameters:
{{
  "params": {{
    "param1": value1,
    "param2": value2,
    ...
  }},
  "missing_required": [],  # List any required params that couldn't be inferred
  "confidence": 0.95,       # 0-1 confidence in the extraction
  "reasoning": "..."        # Brief explanation of extraction choices
}}

EXAMPLES:
Tool: research_search
Request: "Search for Python web scraping libraries"
Response:
{{
  "params": {{"query": "Python web scraping libraries", "depth": 1}},
  "missing_required": [],
  "confidence": 0.99,
  "reasoning": "Query directly from request. Depth defaults to 1."
}}

Tool: research_spider
Request: "Fetch and analyze content from these sites: site1.com site2.com"
Response:
{{
  "params": {{"urls": ["site1.com", "site2.com"]}},
  "missing_required": [],
  "confidence": 0.95,
  "reasoning": "URLs extracted from list in request."
}}

Now extract parameters from the user's request:
"""

PARAM_EXTRACTION_SYSTEM_PROMPT = """You are a parameter extraction specialist for a research MCP server.
Your goal is to convert natural language requests into valid structured parameters.
Be precise, validate types, and handle missing required parameters gracefully.
For ambiguous requests, prefer reasonable defaults and note low confidence."""
```

### 5.2 Parameter Extraction Execution

```python
# src/loom/brain/params_extractor.py

async def extract_params_from_intent(
    intent: Intent,
    tool_name: str,
    tool_description: str,
    pydantic_schema: dict[str, Any],
    quality_mode: str = "auto",
) -> tuple[dict[str, Any], float]:
    """Extract parameters from intent using LLM.
    
    Args:
        intent: Detected user intent
        tool_name: Name of tool to extract params for
        tool_description: Tool's docstring
        pydantic_schema: Pydantic field definitions from tool_params.json
        quality_mode: "max" (Anthropic/OpenAI), "economy" (Groq/NVIDIA), "auto"
    
    Returns:
        (extracted_params, confidence)
    
    Process:
        1. Format param extraction prompt
        2. Call LLM cascade (respecting quality_mode)
        3. Parse JSON response
        4. Validate types against schema
        5. Apply _fuzzy_correct_params() for typo correction
        6. Merge with defaults from schema
        7. Return (params, confidence)
    """
    prompt = PARAM_EXTRACTION_PROMPT.format(
        tool_name=tool_name,
        tool_description=tool_description,
        pydantic_schema_json=json.dumps(pydantic_schema, indent=2),
        user_request=intent.user_request,
    )
    
    # Determine provider based on quality_mode
    if quality_mode == "max":
        providers = ["anthropic", "openai"]  # Premium
    elif quality_mode == "economy":
        providers = ["groq", "nvidia"]  # Free
    else:  # auto
        if intent.complexity == "simple":
            providers = ["groq", "nvidia"]
        elif intent.complexity == "medium":
            providers = ["deepseek", "gemini"]
        else:  # complex
            providers = ["anthropic", "openai"]
    
    # Call LLM cascade
    response = await _call_with_cascade(
        messages=[
            {"role": "system", "content": PARAM_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        provider_order=providers,
        response_format={"type": "json_object"},
    )
    
    # Parse response
    parsed = json.loads(response.content)
    extracted_params = parsed.get("params", {})
    confidence = parsed.get("confidence", 0.8)
    
    # Apply fuzzy correction
    corrected_params, corrections = _fuzzy_correct_params(extracted_params, pydantic_schema)
    
    # Merge with defaults
    final_params = _merge_with_defaults(corrected_params, pydantic_schema)
    
    return final_params, confidence
```

---

## 6. Quality Mode Implementation

### 6.1 Quality Mode Strategy

```python
# src/loom/brain/action.py

QUALITY_MODE_CONFIG = {
    "max": {
        "providers": ["anthropic", "openai"],
        "max_tokens": 2000,
        "temperature": 0.7,
        "description": "Premium models for complex reasoning and param extraction",
        "use_cases": ["Complex multi-step planning", "Ambiguous intent", "Creative synthesis"],
    },
    "economy": {
        "providers": ["groq", "nvidia"],
        "max_tokens": 400,
        "temperature": 0.3,
        "description": "Free tier for fast, factual operations",
        "use_cases": ["Simple searches", "Classifications", "Direct lookups"],
    },
}

async def execute_with_quality_mode(
    plan: Plan,
    quality_mode: Literal["max", "economy"],
    param_extractor,
    tool_executor,
) -> ExecutionResult:
    """Execute tool with respect to quality mode.
    
    Quality mode controls:
    1. Which LLM providers are used (premium vs free)
    2. Parameter extraction strategy (LLM vs heuristic)
    3. Retry policy (aggressive vs conservative)
    4. Caching strategy (short vs long TTL)
    
    Process:
        1. Select providers based on quality_mode
        2. Extract params using selected providers
        3. Validate params
        4. Execute tool via MCP cascade
        5. Capture cost, duration, result
    """
    config = QUALITY_MODE_CONFIG[quality_mode]
    
    # Extract params using configured providers
    params, param_confidence = await param_extractor.extract(
        plan, 
        provider_order=config["providers"],
        max_tokens=config["max_tokens"],
    )
    
    # If param confidence low and quality_mode="economy", retry with "max"
    if param_confidence < 0.6 and quality_mode == "economy":
        logger.warning(f"Low param confidence ({param_confidence}), retrying with max quality")
        params, param_confidence = await param_extractor.extract(
            plan,
            provider_order=QUALITY_MODE_CONFIG["max"]["providers"],
        )
    
    # Execute tool
    result = await tool_executor.execute(
        tool_name=plan.primary_tool,
        params=params,
        timeout_sec=60,
        max_retries=3,
    )
    
    return result
```

### 6.2 Cost Tracking per Quality Mode

```python
# src/loom/brain/action.py

QUALITY_MODE_COST_ESTIMATES = {
    "max": {
        "anthropic": {"input": 3.0, "output": 15.0},  # per 1M tokens
        "openai": {"input": 5.0, "output": 15.0},
    },
    "economy": {
        "groq": {"input": 0.0, "output": 0.0},  # Free
        "nvidia": {"input": 0.0, "output": 0.0},  # Free
    },
}

def estimate_cost(
    quality_mode: str,
    primary_tool: str,
    params: dict[str, Any],
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate cost for tool execution.
    
    Combines:
    - LLM provider cost (param extraction)
    - Tool execution cost (if billable)
    - API call costs (search engines, etc.)
    """
    # Get provider for this quality mode
    providers = QUALITY_MODE_CONFIG[quality_mode]["providers"]
    primary_provider = providers[0]  # Use first provider
    
    costs = QUALITY_MODE_COST_ESTIMATES[quality_mode]
    if primary_provider not in costs:
        return 0.0
    
    provider_costs = costs[primary_provider]
    llm_cost = (
        (input_tokens / 1_000_000) * provider_costs["input"] +
        (output_tokens / 1_000_000) * provider_costs["output"]
    )
    
    # Add tool-specific costs (e.g., search engines)
    tool_cost = _estimate_tool_cost(primary_tool, params)
    
    return llm_cost + tool_cost
```

---

## 7. Multi-Step Planning

### 7.1 Workflow Detection

```python
# src/loom/brain/reasoning.py

async def detect_workflow(
    intent: Intent,
    context: MemoryContext,
) -> list[dict[str, Any]]:
    """Detect if request requires multi-step workflow.
    
    Detects patterns like:
    - "Search then summarize then extract"
    - "Fetch multiple sites and analyze them"
    - "Research topic then find related papers"
    
    Uses:
    1. Keyword detection (then, next, after, followed by)
    2. Intent stacking (multiple verbs)
    3. CO_OCCURRENCE_MAP from tool_recommender_v2
    
    Returns:
        List of {tool, params_template, depends_on} dicts
    """
    workflow = []
    
    # Check for sequencing keywords
    sequencing_keywords = ["then", "next", "after", "followed by", "also"]
    has_sequencing = any(kw in intent.user_request.lower() for kw in sequencing_keywords)
    
    if not has_sequencing:
        # Single-tool request
        return [{"tool": context.tool_suggestions[0][0], "depends_on": None}]
    
    # Multi-step workflow
    # Parse intent into sub-intents
    sub_intents = await _decompose_intent(intent)
    
    for i, sub_intent in enumerate(sub_intents):
        suggested_tool = context.tool_suggestions[0][0]  # Best match
        
        # Check co-occurrence for chaining
        if i > 0:
            prev_tool = workflow[-1]["tool"]
            next_tools = tool_recommender.CO_OCCURRENCE_MAP.get(prev_tool, [])
            if next_tools:
                suggested_tool = next_tools[0]  # Use co-occurrence
        
        workflow.append({
            "tool": suggested_tool,
            "params_template": sub_intent.entities,
            "depends_on": i - 1 if i > 0 else None,
        })
    
    return workflow

async def _decompose_intent(intent: Intent) -> list[Intent]:
    """Decompose complex intent into sub-intents.
    
    Uses LLM to break down multi-step requests.
    Example:
        "Search then summarize then extract" →
        [
            Intent("search for X"),
            Intent("summarize the results"),
            Intent("extract key insights"),
        ]
    """
    prompt = f"""Decompose this multi-step request into individual steps:
    
Request: {intent.user_request}

Return a JSON array of steps:
[
  {{"step": 1, "action": "...", "entities": {{...}}}},
  {{"step": 2, "action": "...", "entities": {{...}}}}
]
"""
    response = await llm.call_with_cascade(
        messages=[{"role": "user", "content": prompt}],
    )
    
    # Parse and convert to Intent objects
    steps = json.loads(response.content)
    sub_intents = []
    for step in steps:
        sub_intent = Intent(
            user_request=step["action"],
            primary_intent=step["action"].split()[0],  # First verb
            entities=step["entities"],
            complexity=intent.complexity,
            confidence=0.8,
            keywords=step["action"].split(),
        )
        sub_intents.append(sub_intent)
    
    return sub_intents
```

### 7.2 Workflow Execution DAG

```python
# src/loom/brain/action.py

async def execute_workflow(
    workflow: list[dict[str, Any]],
    quality_mode: str,
) -> list[ExecutionResult]:
    """Execute multi-step workflow with dependency handling.
    
    Builds a DAG of tool calls and executes with parallelization
    where possible.
    
    Args:
        workflow: List of {tool, params_template, depends_on}
        quality_mode: "max" or "economy"
    
    Returns:
        List of ExecutionResult (one per tool call)
    """
    results: dict[int, ExecutionResult] = {}
    tasks: dict[int, asyncio.Task] = {}
    
    for i, step in enumerate(workflow):
        # Wait for dependency
        if step["depends_on"] is not None:
            dep_result = results[step["depends_on"]]
            if not dep_result.success:
                return results.values()  # Stop on failure
            
            # Pass output to next step as input
            params = _merge_results(step["params_template"], dep_result)
        else:
            params = step["params_template"]
        
        # Execute in parallel if possible
        task = asyncio.create_task(
            execute_single_tool(
                tool_name=step["tool"],
                params=params,
                quality_mode=quality_mode,
            )
        )
        tasks[i] = task
    
    # Collect results
    for i, task in tasks.items():
        results[i] = await task
    
    return [results[i] for i in sorted(results.keys())]
```

---

## 8. Integration with Existing Code

### 8.1 MCP Server Integration (server.py)

```python
# src/loom/server.py (addition)

from loom.brain.core import Brain

# Global Brain instance
_BRAIN: Brain | None = None

def _get_brain() -> Brain:
    global _BRAIN
    if _BRAIN is None:
        _BRAIN = Brain(
            embedding_model="all-MiniLM-L6-v2",
            tool_params_path="docs/tool_params.json",
            enable_caching=True,
            enable_learning=True,
        )
    return _BRAIN

async def research_smart_call(
    request: str,
    tool: str = "auto",
    quality_mode: str = "auto",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Smart request routing via BRAIN.
    
    Automatically detect intent, select tools, extract parameters,
    and execute with quality-aware provider selection.
    
    Args:
        request: Natural language request
        tool: "auto" to detect, or specify tool name
        quality_mode: "max", "economy", "auto"
        session_id: Optional session context
    
    Returns:
        {"success": bool, "data": any, "tool_used": str, ...}
    
    Examples:
        >>> result = await research_smart_call("Search for Python web scraping")
        >>> result = await research_smart_call(
        ...     "Find GitHub repos and analyze them",
        ...     quality_mode="economy"
        ... )
    """
    brain = _get_brain()
    result = await brain.process(
        request=request,
        tool=tool,
        quality_mode=quality_mode,
        session_id=session_id,
    )
    
    return {
        "success": result.success,
        "data": result.data,
        "tool_used": result.tool_used,
        "params_used": result.params_used,
        "cost_usd": result.cost_usd,
        "duration_ms": result.duration_ms,
        "quality_mode": result.quality_mode_used,
        "error": result.error,
        "retries": result.retries,
    }
```

### 8.2 Tool Registration

```python
# src/loom/server.py (_register_tools section)

mcp.tool(
    description="Intelligent request routing with auto tool selection and param extraction"
)(research_smart_call)
```

### 8.3 Reusing Existing Subsystems

```python
# src/loom/brain/reasoning.py

from loom.tools.semantic_router import research_semantic_route
from loom.tools.smart_router import research_route_query
from loom.tools.tool_recommender_v2 import (
    CO_OCCURRENCE_MAP,
    WORKFLOW_TEMPLATES,
    TOOL_CATEGORIES,
)
from loom.tools.model_router import classify_query_complexity

class ReasoningEngine:
    def __init__(self, memory_system, tool_params_path):
        self.memory = memory_system
        self.tool_params_path = tool_params_path
    
    async def select_tool(self, intent: Intent, context: MemoryContext) -> str:
        """Select best tool using cascading methods:
        1. Semantic routing (embeddings)
        2. Smart routing (keywords)
        3. Tool recommendations (co-occurrence)
        """
        # 1. Semantic routing
        semantic_results = await research_semantic_route(intent.user_request)
        if semantic_results["recommended_tools"]:
            return semantic_results["recommended_tools"][0]
        
        # 2. Smart routing fallback
        smart_results = await research_route_query(intent.user_request)
        if smart_results["recommended_tools"]:
            return smart_results["recommended_tools"][0]
        
        # 3. Use context suggestions
        if context.tool_suggestions:
            return context.tool_suggestions[0][0]
        
        # Fallback: research_search (always available)
        return "research_search"
```

---

## 9. Testing Strategy

### 9.1 Test Structure

```
tests/test_brain/
├── __init__.py
├── conftest.py                  # Fixtures (mock embeddings, tools, LLM)
├── test_perception.py           # Intent detection
├── test_memory.py               # Context loading, embeddings
├── test_reasoning.py            # Tool selection, planning
├── test_action.py               # Param extraction, execution
├── test_reflection.py           # Learning, validation
├── test_params_extractor.py     # LLM param extraction
├── test_integration.py          # End-to-end flows
└── test_e2e_workflows.py        # Multi-step workflows
```

### 9.2 Sample Unit Tests

```python
# tests/test_brain/test_perception.py

import pytest
from loom.brain.perception import PerceptionEngine

@pytest.fixture
def perception():
    return PerceptionEngine()

@pytest.mark.asyncio
async def test_simple_intent_detection(perception):
    """Test detecting simple search intent."""
    request = "Search for Python web scraping libraries"
    intent = await perception.detect_intent(request)
    
    assert intent.primary_intent == "search"
    assert intent.complexity == "simple"
    assert "python" in intent.keywords
    assert intent.confidence > 0.8

@pytest.mark.asyncio
async def test_complex_intent_detection(perception):
    """Test detecting complex multi-step intent."""
    request = "Search for Python web scraping repos, then analyze their code quality"
    intent = await perception.detect_intent(request)
    
    assert intent.primary_intent in ["search", "analyze"]
    assert intent.complexity == "complex"
    assert "analyze" in intent.keywords

@pytest.mark.asyncio
async def test_entity_extraction(perception):
    """Test extracting entities from request."""
    request = "Search GitHub for Django REST framework projects in Python"
    intent = await perception.detect_intent(request)
    
    assert "Django REST framework" in str(intent.entities)
    assert "Python" in str(intent.entities)

# tests/test_brain/test_reasoning.py

@pytest.mark.asyncio
async def test_tool_selection_semantic(reasoning):
    """Test tool selection via semantic routing."""
    intent = Intent(
        user_request="Fetch and analyze a webpage",
        primary_intent="fetch",
        entities={},
        complexity="medium",
        confidence=0.9,
        keywords=["fetch", "analyze"]
    )
    context = MemoryContext(
        session_id=None,
        recent_tools=[],
        tool_suggestions=[("research_fetch", 0.95), ("research_spider", 0.85)],
        embedding=np.random.rand(384),
        metadata={},
    )
    
    plan = await reasoning.generate_plan(intent, context)
    
    assert plan.primary_tool == "research_fetch"
    assert len(plan.alternatives) > 0

@pytest.mark.asyncio
async def test_workflow_detection(reasoning):
    """Test detecting multi-step workflows."""
    intent = Intent(
        user_request="Search for Python repos, then fetch the README, then summarize",
        primary_intent="search",
        entities={},
        complexity="complex",
        confidence=0.85,
        keywords=["search", "fetch", "summarize"]
    )
    
    workflow = await reasoning.detect_workflow(intent, MemoryContext(...))
    
    assert len(workflow) >= 3
    assert workflow[0]["tool"] == "research_search"
    assert workflow[1]["tool"] == "research_fetch"
    assert workflow[2]["tool"] in ["research_llm_summarize", "research_summarize"]

# tests/test_brain/test_integration.py

@pytest.mark.asyncio
async def test_end_to_end_simple_request(brain):
    """Test full pipeline for simple request."""
    result = await brain.process(
        request="Search for Python web scraping",
        tool="auto",
        quality_mode="economy",
    )
    
    assert result.success
    assert result.tool_used == "research_search"
    assert result.data is not None
    assert result.cost_usd < 0.10  # Economy mode should be cheap

@pytest.mark.asyncio
async def test_end_to_end_complex_request(brain):
    """Test full pipeline for complex multi-step request."""
    result = await brain.process(
        request="Search for Python web scraping and analyze the top result",
        tool="auto",
        quality_mode="max",
    )
    
    assert result.success
    assert len(result.tool_used) > 0
    assert result.duration_ms > 1000  # More complex workflow

@pytest.mark.asyncio
async def test_quality_mode_max(brain):
    """Test quality_mode='max' forces premium providers."""
    result = await brain.process(
        request="Analyze sentiment of this text",
        quality_mode="max",
    )
    
    # Should use Anthropic or OpenAI
    assert result.quality_mode_used == "max"

@pytest.mark.asyncio
async def test_quality_mode_economy(brain):
    """Test quality_mode='economy' forces free providers."""
    result = await brain.process(
        request="Translate hello to French",
        quality_mode="economy",
    )
    
    assert result.quality_mode_used == "economy"
    assert result.cost_usd < 0.05
```

### 9.3 Mock Fixtures

```python
# tests/test_brain/conftest.py

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from loom.brain.core import Brain
from loom.brain.types import Intent, MemoryContext

@pytest.fixture
def mock_embeddings():
    """Mock sentence-transformers model."""
    model = MagicMock()
    model.encode.return_value = np.random.rand(384)
    return model

@pytest.fixture
def mock_tool_params():
    """Mock tool_params.json data."""
    return {
        "research_search": {
            "params": {
                "query": {"type": "str", "required": True},
                "depth": {"type": "int", "required": False, "default": 1},
            }
        },
        "research_fetch": {
            "params": {
                "url": {"type": "str", "required": True},
                "include_html": {"type": "bool", "required": False, "default": False},
            }
        },
    }

@pytest.fixture
def brain(mock_embeddings, mock_tool_params, monkeypatch):
    """Create Brain instance with mocked dependencies."""
    brain = Brain()
    brain.memory._embedding_model = mock_embeddings
    brain.memory._tool_params = mock_tool_params
    return brain

@pytest.fixture
def sample_intent():
    """Sample Intent object."""
    return Intent(
        user_request="Search for Python web scraping",
        primary_intent="search",
        entities={"language": "Python", "topic": "web scraping"},
        complexity="simple",
        confidence=0.95,
        keywords=["search", "python", "web", "scraping"],
    )

@pytest.fixture
def sample_memory_context():
    """Sample MemoryContext object."""
    return MemoryContext(
        session_id="test-session-123",
        recent_tools=["research_search"],
        tool_suggestions=[("research_search", 0.99), ("research_fetch", 0.85)],
        embedding=np.random.rand(384),
        metadata={"session_start": "2026-05-09T10:00:00Z"},
    )
```

---

## 10. Implementation Order for Kimi/DeepSeek

### Phase 1: Core Infrastructure (Days 1-2)

**Deliverable**: `src/loom/brain/` package with type definitions and basic structure

1. Create `src/loom/brain/__init__.py` (exports)
2. Create `src/loom/brain/types.py` (Intent, Plan, Result dataclasses)
3. Create `src/loom/brain/prompts.py` (param extraction template)
4. Create `src/loom/brain/core.py` (Brain class skeleton with lifecycle)
5. Write tests: `tests/test_brain/conftest.py`, `tests/test_brain/__init__.py`

**Tasks**:
- [ ] BRAIN-001: Create brain package structure
- [ ] BRAIN-002: Define type system (Intent, Plan, Result, etc.)
- [ ] BRAIN-003: Create prompt templates
- [ ] BRAIN-004: Write core Brain class skeleton

### Phase 2: Perception & Memory (Days 3-4)

**Deliverable**: Intent detection + embeddings-based tool lookup

1. Create `src/loom/brain/perception.py` (Intent detection)
   - Keyword-based intent classification
   - Entity extraction
   - Complexity classification (reuse model_router)
2. Create `src/loom/brain/memory.py` (MemorySystem)
   - Load embeddings (lazy-load sentence-transformers)
   - Cache embeddings and tool descriptions
   - Session context management
3. Write comprehensive tests

**Tasks**:
- [ ] BRAIN-005: Implement PerceptionEngine (intent detection)
- [ ] BRAIN-006: Implement MemorySystem (embeddings + caching)
- [ ] BRAIN-007: Write unit tests for perception
- [ ] BRAIN-008: Write unit tests for memory

### Phase 3: Reasoning & Planning (Days 5-6)

**Deliverable**: Tool selection + multi-step planning

1. Create `src/loom/brain/reasoning.py` (ReasoningEngine)
   - Reuse semantic_router, smart_router, tool_recommender_v2
   - Tool selection algorithm
   - Workflow detection
   - Plan generation
2. Write tests with real tool metadata

**Tasks**:
- [ ] BRAIN-009: Implement ReasoningEngine (tool selection)
- [ ] BRAIN-010: Implement workflow detection
- [ ] BRAIN-011: Integrate with semantic_router and tool_recommender_v2
- [ ] BRAIN-012: Write integration tests for reasoning

### Phase 4: Action & Execution (Days 7-8)

**Deliverable**: Parameter extraction + quality-aware execution

1. Create `src/loom/brain/params_extractor.py` (LLM-based param extraction)
   - Format param extraction prompts
   - Call LLM cascade (respecting quality modes)
   - Parse JSON responses
   - Validate against Pydantic schemas
2. Create `src/loom/brain/action.py` (ActionExecutor)
   - Execute single tools
   - Execute workflows (DAG-based)
   - Retry logic
   - Cost tracking
3. Write comprehensive tests

**Tasks**:
- [ ] BRAIN-013: Implement params_extractor
- [ ] BRAIN-014: Implement ActionExecutor (single tool)
- [ ] BRAIN-015: Implement workflow execution (DAG)
- [ ] BRAIN-016: Write tests for param extraction
- [ ] BRAIN-017: Write tests for action execution

### Phase 5: Reflection & Learning (Day 9)

**Deliverable**: Result validation + outcome learning

1. Create `src/loom/brain/reflection.py` (ReflectionSystem)
   - Validate output schemas
   - Track tool usage patterns
   - Detect drift/anomalies
   - Generate learning signals
2. Write tests

**Tasks**:
- [ ] BRAIN-018: Implement ReflectionSystem
- [ ] BRAIN-019: Write tests for reflection

### Phase 6: Integration & API (Day 10)

**Deliverable**: MCP server integration + user-facing API

1. Update `src/loom/server.py` to add `research_smart_call()`
2. Register tool in FastMCP
3. Write integration tests
4. Update documentation

**Tasks**:
- [ ] BRAIN-020: Integrate with server.py
- [ ] BRAIN-021: Register research_smart_call in MCP
- [ ] BRAIN-022: Write end-to-end tests
- [ ] BRAIN-023: Update docs (API reference, examples)

### Phase 7: Optimization & Polish (Day 11-12)

**Deliverable**: Performance optimization, error handling, documentation

1. Optimize embeddings loading (lazy + caching)
2. Add comprehensive error handling
3. Add logging and tracing
4. Update CLAUDE.md with brain architecture
5. Write comprehensive documentation

**Tasks**:
- [ ] BRAIN-024: Performance optimization (embeddings preloading)
- [ ] BRAIN-025: Error handling and validation
- [ ] BRAIN-026: Logging and observability
- [ ] BRAIN-027: Documentation update
- [ ] BRAIN-028: Final testing and validation

---

## 11. Key Design Decisions

### ADR-001: Five-Layer Architecture

**Status**: Accepted

**Context**: Need to process natural language requests into structured tool calls without exceeding context windows or requiring deep architectural changes.

**Decision**: Implement five-layer architecture (Perception → Memory → Reasoning → Action → Reflection) as a thin orchestration layer above existing subsystems.

**Consequences**:
- **Positive**: Modular, testable, reuses existing code, clear separation of concerns
- **Negative**: Additional latency (5 LLM calls for complex requests), requires coordination
- **Mitigation**: Batch simple intents, cache results, async execution

### ADR-002: Reuse Existing Subsystems

**Status**: Accepted

**Context**: Loom already has semantic_router, smart_router, tool_recommender_v2, model_router.

**Decision**: Integrate Brain as orchestration layer above existing subsystems rather than reimplementing.

**Consequences**:
- **Positive**: Leverage battle-tested code, reduce duplication, faster implementation
- **Negative**: Tight coupling to existing APIs
- **Mitigation**: Define clear interfaces, use adapters if APIs change

### ADR-003: LLM-Based Parameter Extraction

**Status**: Accepted

**Context**: Parameter extraction from natural language is complex and error-prone with heuristics.

**Decision**: Use LLM with param extraction prompt template to generate structured params from intent.

**Consequences**:
- **Positive**: Handles complex intents well, adaptable to new tools
- **Negative**: Additional LLM cost, potential hallucination
- **Mitigation**: Validate against Pydantic, use low temperature, fallback to defaults

### ADR-004: Quality Modes for Cost Control

**Status**: Accepted

**Context**: Need to balance quality vs cost, users want control over provider selection.

**Decision**: Implement quality_mode parameter (max/economy/auto) that controls provider selection for all LLM operations.

**Consequences**:
- **Positive**: User control, cost transparency, enables batch processing with economy mode
- **Negative**: Quality variance between tiers, increased complexity
- **Mitigation**: Document trade-offs, provide cost estimates, default to "auto"

### ADR-005: Synchronous Tool Execution with Async Orchestration

**Status**: Accepted

**Context**: Some tools (research_github) are sync, most are async, need to handle both.

**Decision**: Use async/await for orchestration layer, handle sync tools via run_in_executor().

**Consequences**:
- **Positive**: Scalable, non-blocking
- **Negative**: Executor overhead for sync tools
- **Mitigation**: Profile performance, consider process pool

---

## 12. Configuration & Environment Variables

```bash
# src/loom/config.py additions

BRAIN_ENABLED = True                                    # Enable Brain orchestration
BRAIN_QUALITY_MODE = "auto"                            # Default: auto, max, economy
BRAIN_EMBEDDING_MODEL = "all-MiniLM-L6-v2"            # sentence-transformers model
BRAIN_CACHE_EMBEDDINGS = True                         # Cache tool embeddings
BRAIN_ENABLE_LEARNING = True                          # Track usage patterns
BRAIN_PARAM_EXTRACTION_TEMPERATURE = 0.3              # Low = deterministic
BRAIN_MAX_RETRIES = 3                                 # Retry policy
BRAIN_TIMEOUT_SEC = 60                                # Execution timeout
BRAIN_COST_CAP_USD = 5.0                              # Daily cost cap
```

---

## 13. Error Handling Strategy

### Error Taxonomy

```python
# src/loom/brain/errors.py

class BrainException(Exception):
    """Base exception for Brain layer."""
    pass

class PerceptionError(BrainException):
    """Intent detection failed."""
    pass

class MemoryError(BrainException):
    """Context loading failed."""
    pass

class ReasoningError(BrainException):
    """Tool selection or planning failed."""
    pass

class ActionError(BrainException):
    """Tool execution failed."""
    pass

class ParamExtractionError(ActionError):
    """Parameter extraction failed."""
    pass

class ParamValidationError(ActionError):
    """Parameter validation failed."""
    pass

class ReflectionError(BrainException):
    """Outcome learning failed (non-fatal)."""
    pass
```

### Error Recovery

```python
# src/loom/brain/core.py (process method)

try:
    plan = await self.reason(intent, context, tool=tool)
except ReasoningError as e:
    logger.warning(f"Reasoning failed: {e}. Using fallback research_search.")
    plan = Plan(
        primary_tool="research_search",
        alternatives=[],
        params_template={"query": intent.user_request},
        workflow_steps=[],
        estimated_cost=0.0,
        reasoning="Fallback: reasoning failed",
        quality_mode="economy",
    )
```

---

## 14. Performance Considerations

### Latency Budget

```
Expected latencies per request phase:

PERCEPTION (intent detection)
  - Keyword analysis: 1 ms
  - Optional LLM call (complex intent): 500 ms
  Subtotal: 1-500 ms

MEMORY (embeddings lookup)
  - Load embeddings (cached): 50 ms
  - Cosine similarity: 10 ms
  Subtotal: 60 ms

REASONING (tool selection + planning)
  - Semantic routing: 50 ms
  - Plan generation (simple): 10 ms
  - Plan generation (workflow): 200-500 ms
  Subtotal: 60-550 ms

ACTION (param extraction + execution)
  - LLM param extraction: 500-2000 ms
  - Tool execution: 1000-30000 ms
  Subtotal: 1500-32000 ms

REFLECTION (learning)
  - Async, non-blocking
  Subtotal: <100 ms (async)

TOTAL: 1.6-33 seconds (mostly tool execution time)
```

### Optimization Strategies

1. **Eager embeddings loading**: Preload all tool embeddings on startup
2. **Caching**: Cache intent→tool mappings for frequent queries
3. **Async execution**: Use asyncio for parallel tool calls in workflows
4. **Batching**: Group similar requests to reduce LLM calls
5. **Lazy LLM**: Only call LLM for complex intents, use heuristics for simple

---

## 15. Documentation Artifacts

### User-Facing Documentation

```markdown
# BRAIN API Reference

## research_smart_call(request, tool="auto", quality_mode="auto", session_id=None)

Intelligent request routing with automatic tool selection and parameter extraction.

**Parameters**:
- request (str): Natural language request
- tool (str, optional): "auto" to auto-detect, or specific tool name
- quality_mode (str, optional): "auto", "max" (premium), "economy" (free)
- session_id (str, optional): Session for context preservation

**Returns**:
- success (bool): Whether execution succeeded
- data (any): Tool output
- tool_used (str): Tool that was executed
- cost_usd (float): Estimated cost
- duration_ms (float): Execution time

**Examples**:

```python
# Simple search
result = await research_smart_call("Find Python web scraping libraries")

# Multi-step with cost control
result = await research_smart_call(
    "Search for Django projects then analyze code quality",
    quality_mode="economy"
)

# Session-aware
result = await research_smart_call(
    "Summarize the findings",
    session_id="session-123"
)
```

## Quality Modes

- **max**: Use Anthropic/OpenAI, best quality, higher cost (~$1-5 per call)
- **economy**: Use Groq/NVIDIA, free tier, 10ms latency (~$0 per call)
- **auto**: Auto-select based on query complexity (recommended)
```

---

## 16. Future Enhancements (Out of Scope)

1. **Multi-agent coordination**: Parallel brain instances for complex queries
2. **Few-shot learning**: Learn from execution history to improve param extraction
3. **Adversarial robustness**: Detect and prevent prompt injection in intent
4. **Semantic caching**: Cache intents by semantic similarity
5. **Recursive planning**: Handle nested/recursive workflows
6. **Real-time feedback**: Interactive disambiguation for ambiguous intents

---

## Conclusion

The LOOM BRAIN architecture provides a principled, modular foundation for intelligent request orchestration across 883 tools. By layering perception, memory, reasoning, action, and reflection, it enables natural language interaction without exceeding existing architectural boundaries.

**Key Strengths**:
- Modular, testable design with clear separation of concerns
- Reuses existing battle-tested subsystems (semantic_router, tool_recommender_v2, etc.)
- Cost-transparent with quality mode control
- Handles both simple and complex multi-step workflows
- Extensible for future enhancements (few-shot learning, adversarial robustness, etc.)

**Ready for Implementation**: All design decisions documented, type system defined, integration points identified, test strategy outlined, and phased implementation plan provided.
