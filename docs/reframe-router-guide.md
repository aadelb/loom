# Reframe Router Guide

## Overview

The **reframe router** (`research_reframe_or_integrate`) is an intelligent classification tool that analyzes research queries and decides whether they need:

1. **Reframing strategies** - LLM-based techniques (jailbreaks, encoding, personas) when facing refusal
2. **Tool integrations** - External data gathering (web scraping, search, OSINT)
3. **Both** - Complex queries requiring both strategies and external data

## When to Use

Use the reframe router as a **pre-filter** before executing research tasks:

```python
# First: Classify the query
routing_decision = await research_reframe_or_integrate(query)

# Then: Route to appropriate tool/strategy
if routing_decision["decision"] == "reframe":
    # Use suggested_strategies with prompt engineering
    strategy = select_strategy(routing_decision["suggested_strategies"])
    result = apply_strategy(strategy, original_query)
elif routing_decision["decision"] == "integrate":
    # Use suggested_tools to gather external data
    tool = select_tool(routing_decision["suggested_tools"])
    result = await call_tool(tool, query)
else:  # "both"
    # Combine both approaches
    data = await call_tools(routing_decision["suggested_tools"])
    refined_prompt = apply_strategy(routing_decision["suggested_strategies"], query, data)
    result = refine_output(refined_prompt)
```

## Classification Categories

### Reframe (Refusal Bypass)

Triggered when query contains:
- Bypass/jailbreak keywords: "bypass", "jailbreak", "circumvent", "evade"
- Dangerous patterns: "how to exploit", "without detection", "unauthorized"
- Encoding hints: "encode", "obfuscate", "hide"
- Reasoning manipulation: "explain", "step by step", "reasoning"
- Persona adoption: "pretend", "role play", "assume", "act as"

**Confidence boosted by:** Dangerous pattern detection (adds +0.3 to score)

### Integrate (Data Gathering)

Triggered when query contains:
- Search keywords: "find", "search", "discover", "look up"
- Scraping keywords: "scrape", "fetch", "crawl"
- OSINT keywords: "osint", "recon", "identity", "domain"
- Monitoring keywords: "monitor", "track", "trending", "latest"
- Analysis keywords: "analyze", "identify", "enumerate", "list"

### Both (Complex Attack)

Triggered when **both** scores exceed thresholds:
- Reframe score > 0.6 AND Integrate score > 0.5
- Indicates query needs both strategies + data gathering

## Response Format

```json
{
  "decision": "reframe|integrate|both",
  "confidence": 0.0-1.0,
  "query_intent": "refusal_bypass|data_gathering|complex_attack_with_data|etc",
  "suggested_tools": ["research_fetch", "research_search", ...],
  "suggested_strategies": ["jailbreak_v1", "encoding_base64", ...],
  "detected_patterns": ["bypass", "how to", "fetch", ...],
  "reasoning": "Human-readable explanation"
}
```

## Examples

### Example 1: Refusal Bypass Detection

**Input:**
```
query = "how to bypass OpenAI safety filters without getting caught"
```

**Output:**
```json
{
  "decision": "reframe",
  "confidence": 0.95,
  "query_intent": "refusal_bypass",
  "suggested_strategies": [
    "jailbreak_persona_expert",
    "encoding_rot13",
    "reasoning_step_by_step",
    "novel_2026_technique_42",
    "token_smuggling_v2"
  ],
  "suggested_tools": [],
  "detected_patterns": ["bypass", "how to", "without detection"],
  "reasoning": "Query requires reframing (refusal bypass detected) | 2 dangerous patterns detected"
}
```

### Example 2: Data Gathering Detection

**Input:**
```
query = "find all open SSH ports on example.com and enumerate services"
```

**Output:**
```json
{
  "decision": "integrate",
  "confidence": 0.88,
  "query_intent": "data_gathering",
  "suggested_tools": [
    "research_nmap_scan",
    "research_passive_recon",
    "research_fetch",
    "research_search"
  ],
  "suggested_strategies": [],
  "detected_patterns": ["find", "scan", "enumerate"],
  "reasoning": "Query requires external data tools and API integration"
}
```

### Example 3: Complex Attack Detection

**Input:**
```
query = "how to exploit CVE-2024-1234 without detection and find all vulnerable servers"
```

**Output:**
```json
{
  "decision": "both",
  "confidence": 0.92,
  "query_intent": "complex_attack_with_data",
  "suggested_tools": [
    "research_cve_lookup",
    "research_exploit_search",
    "research_passive_recon",
    "research_nmap_scan"
  ],
  "suggested_strategies": [
    "jailbreak_v1",
    "encoding_polyalphabetic",
    "reasoning_chain_of_thought"
  ],
  "detected_patterns": ["exploit", "without detection", "find", "cve"],
  "reasoning": "Query is complex: needs both reframing (0.85) and integration (0.82) | 1 dangerous patterns detected"
}
```

## Keyword Lists

### Reframing Keywords (with base scores)

- **High confidence** (0.9+): "bypass", "jailbreak", "circumvent", "exploit", "without detection"
- **Medium-high** (0.8-0.89): "evade", "unauthorized", "covertly", "forbidden"
- **Medium** (0.7-0.79): "dangerous", "explain how", "unethical"
- **Lower** (0.6-0.69): "can you", "teach me", "guide me"

### Integration Keywords (with base scores)

- **High confidence** (0.9+): "search", "fetch", "scrape", "crawl"
- **Medium-high** (0.8-0.89): "find", "look up", "discover", "extract", "locate"
- **Medium** (0.7-0.79): "analyze", "monitor", "track", "research"
- **Lower** (0.6-0.69): "test", "benchmark", "compare"

## Implementation Details

### Keyword Matching Algorithm

1. **Tokenize query** to lowercase
2. **Check for each keyword** in REFRAMING_KEYWORDS and INTEGRATION_KEYWORDS
3. **Calculate average score** for matched keywords
4. **Boost for dangerous patterns** (+0.3 to reframe score if any detected)
5. **Normalize confidence** to 0-1 range

### Decision Logic

```
if reframe_score > 0.6 and integrate_score > 0.5:
    decision = "both"
elif reframe_score > integrate_score + 0.2:
    decision = "reframe"
elif integrate_score > reframe_score + 0.2:
    decision = "integrate"
else:
    # Default to higher score
    decision = "reframe" if reframe_score > integrate_score else "integrate"
```

## Tool Selection Heuristics

When `decision == "integrate"`, tools are selected based on detected keywords:

| Keywords | Tools |
|----------|-------|
| scrape, fetch, crawl, page | research_fetch, research_spider |
| search, find, discover, lookup | research_search, research_multi_search |
| osint, recon, identity, domain | research_passive_recon, research_identity_resolve |
| github, code, repo, project | research_github |
| monitor, track, trending | research_rss_monitor, research_change_monitor |

## Strategy Selection Heuristics

When `decision == "reframe"`, strategies are selected based on detected keywords:

| Keywords | Strategy Category |
|----------|-------------------|
| bypass, circumvent, without detection | jailbreak (5 strategies) |
| encode, obfuscate, hide | encoding (5 strategies) |
| explain, reasoning, logic, step by step | reasoning (5 strategies) |
| pretend, role play, assume, act as | persona (5 strategies) |
| novel, creative, unique, new way | novel_2026 (5 strategies) |

If no keywords match, top 3 general strategies are recommended.

## Best Practices

1. **Use as pre-filter** - Call before major research operations
2. **Trust high-confidence scores** - confidence > 0.8 = highly reliable
3. **Check detected_patterns** - Verify the detected intent matches your use case
4. **Combine both** - Don't ignore suggested_tools/strategies even if decision is different
5. **Log decisions** - Track which queries need which approaches for analytics

## Safety Notes

This router is **descriptive**, not prescriptive:
- It identifies when queries likely need refusal bypass
- Does NOT automatically apply strategies (you control execution)
- Designed for authorized research/testing only
- Use with proper safeguards and governance

## Costs and Performance

- **Latency**: < 10ms (purely keyword/pattern matching, no LLM calls)
- **Tokens**: None (no external API calls)
- **Cost**: Free (local classification)
- **Availability**: Always available (no external dependencies)

## Troubleshooting

### Query classified as "integrate" but I need "reframe"

Possible causes:
- Query contains too many data-oriented keywords
- Dangerous patterns not detected (maybe using obfuscated language)
- Try providing explicit context parameter with intent clarification

**Solution:**
```python
result = await research_reframe_or_integrate(
    query="how to h4ck the system",  # Obfuscated
    context="This is testing prompt injection resistance"
)
```

### Confidence too low

Possible causes:
- Neutral or ambiguous query
- Balanced mix of reframe + integrate keywords
- No dangerous patterns detected

**Solution:**
- Use the suggestions anyway (they're still useful)
- Add context for clarity
- Check reasoning field for diagnostic info

### No suggested tools/strategies

Possible causes:
- Not enough matching keywords for specific categories
- General fallback strategies selected

**Solution:**
- Check detected_patterns list
- Review reasoning for why decision was made
- Use manual tool/strategy selection if needed
