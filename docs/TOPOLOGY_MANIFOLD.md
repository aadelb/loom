# Topological Strategy Manifolds — Strategy Space Discovery

## Overview

The **Topological Strategy Manifolds** tool maps the 957-strategy attack space into 5-dimensional feature space using persistent homology concepts to discover **topological holes** — regions where no strategies currently exist. These gaps represent undiscovered attack archetypes waiting to be developed.

## Core Concept

Each strategy is represented as a feature vector:

```
[length_class, persona_count, encoding_level, authority_appeal, turns_needed]
```

**Dimension breakdown:**

| Dimension | Range | Meaning |
|-----------|-------|---------|
| **length_class** | 0–2 | 0=short (<100 chars), 1=medium (100–300), 2=long (>300) |
| **persona_count** | 0–5 | Number of distinct personas/roles in prompt |
| **encoding_level** | 0–3 | 0=none, 1=base64, 2=unicode/emoji, 3=mixed |
| **authority_appeal** | 0–3 | Regulatory/legal/ethical/academic appeals |
| **turns_needed** | 1–7 | Estimated multi-turn requirement |

### Grid-Based Hole Detection

The tool partitions 5D space into grid cells, then identifies:
1. **Occupied cells:** Points where strategies exist
2. **Empty cells with occupied neighbors:** Topological holes
3. **Novelty scores:** Measure of how far each hole is from the current strategy distribution

## Usage

### Basic Discovery (All 957 Strategies)

```python
from loom.tools.topology_manifold import research_topology_discover

result = await research_topology_discover()
```

**Output:**
```json
{
  "strategies_analyzed": 957,
  "feature_space_dimensions": 5,
  "holes_found": 20,
  "occupied_cells": 32,
  "total_coverage_pct": 1.59,
  "topological_holes": [
    {
      "coordinates": [2, 0, 2, 0, 1],
      "novelty_score": 0.5,
      "suggested_archetype": "long-form narrative strategy",
      "fill_strategy": "long-form narrative strategy"
    }
  ],
  "discovery_summary": "Found 20 topological gaps across 957 strategies",
  "next_steps": [
    "Implement strategies in identified gaps",
    "Validate novelty of gap-filling strategies",
    "Re-run analysis after new strategy integration"
  ]
}
```

### Filtered Analysis

Analyze only specific strategy categories:

```python
result = await research_topology_discover(
    strategies=["ethical_anchor", "academic", "regulatory", "crescendo"]
)
```

### Threshold Configuration

Adjust hole sensitivity (0.0–1.0):

```python
result = await research_topology_discover(threshold=0.3)  # Stricter hole detection
```

## Output Fields

### Metadata
- **strategies_analyzed**: Count of strategies processed
- **feature_space_dimensions**: Fixed at 5
- **holes_found**: Number of topological gaps detected
- **occupied_cells**: Count of non-empty grid cells
- **potential_cells**: Total possible cells (product of dimension bounds)
- **total_coverage_pct**: Percentage of space filled (occupied/potential × 100)

### Topological Holes Array
Each hole contains:
- **coordinates**: [length, persona, encoding, authority, turns] position in 5D space
- **novelty_score**: 0–1 (higher = more novel/undiscovered)
- **suggested_archetype**: Natural language description of the gap
- **fill_strategy**: Recommended strategy type to implement

### Recommendations
- **discovery_summary**: Executive summary of findings
- **next_steps**: Actionable list for strategy development

## Interpretation Guide

### Example 1: Long-Form + Low-Authority Gap

```
Coordinates: [2, 1, 2, 0, 3]
Fill Strategy: "long-form narrative strategy + multi-persona orchestration + advanced encoding/obfuscation"
```

**Interpretation:** Current strategy corpus is missing long-form, complex narratives with multiple personas and encoding, but WITHOUT relying on authority appeals. Develop a creative storytelling jailbreak here.

### Example 2: Short + High-Authority Gap

```
Coordinates: [0, 0, 0, 3, 1]
Fill Strategy: "short-prompt strategy + high-authority compliance appeal"
```

**Interpretation:** No short, simple prompts leveraging regulatory/legal authority exist. Develop a concise compliance-testing prompt.

### Example 3: Medium + Mixed Encoding Gap

```
Coordinates: [1, 2, 3, 1, 4]
Fill Strategy: "medium length + multi-persona orchestration + advanced encoding/obfuscation + extended multi-turn dialogue"
```

**Interpretation:** Gap in medium-length prompts combining personas, mixed encoding, and sustained multi-turn interaction.

## Coverage Analysis

With 957 strategies occupying only **1.59%** of the 5D space:

| Coverage | Implication |
|----------|-------------|
| **<2%** | Vast unexplored space; many novel strategies possible |
| **2–5%** | Reasonable diversity; targeted development in gaps |
| **>10%** | Strategy space maturing; diminishing returns on new strategies |

**Current status:** The strategy space is **dramatically underdeveloped**. Each of the 20 identified holes represents a distinct attack archetype not yet in the corpus.

## Practical Workflow

### 1. Identify Gaps
```python
result = await research_topology_discover()
gaps = result['topological_holes'][:5]  # Top 5 novel gaps
```

### 2. Design Gap-Filling Strategies
For each gap, use `suggested_archetype` and `fill_strategy` as design guidelines:
- Example: For `[2, 4, 2, 0, 5]`, create a long, multi-persona, multi-encoding, multi-turn jailbreak

### 3. Implement & Test
Add new strategies to `src/loom/tools/reframe_strategies/novel_strategies.py`

### 4. Re-run Discovery
```python
result = await research_topology_discover()  # Updated analysis
```

Verify new strategies fill identified gaps (coverage should increase).

## Mathematical Foundation

### Distance Metric
Euclidean distance in 5D feature space:
```
d(v1, v2) = sqrt(sum((v1[i] - v2[i])² for i in 0..4))
```

### Hole Detection Algorithm
1. Discretize all strategy vectors to integer grid
2. Mark occupied cells
3. For each occupied cell, check 10 neighbors (±1 in each dimension)
4. Unoccupied neighbors of occupied cells = holes
5. Deduplicate and score by distance from center

### Novelty Scoring
```
novelty_score = min(1.0, sum(|coordinate[i]|) / 10.0)
```

Higher coordinates = further from origin = more novel.

## Limitations & Future Work

### Current Limitations
1. **Grid discretization**: Loses sub-cell precision
2. **5D limitation**: Could expand to 8–10 dimensions (encoding variants, escalation tactics, etc.)
3. **No feature weighting**: All dimensions equally important (could emphasize authority/persona)
4. **Static analysis**: Doesn't account for strategy effectiveness (could use HCS scores)

### Future Enhancements
- **Weighted dimensions**: Authority appeals > encoding
- **Effectiveness integration**: Factor in attack success rates
- **Higher dimensions**: Add encoding_variant, escalation_type, target_model
- **Persistent homology**: True topological analysis (currently simplified grid-based)
- **Strategy similarity**: Cluster strategies before hole detection
- **Adaptive thresholding**: Dynamic threshold based on cluster density

## Example Workflow: Discovering a Novel Jailbreak

1. **Run discovery:**
   ```python
   result = await research_topology_discover()
   novel_gap = result['topological_holes'][0]
   # Coordinates: [2, 3, 2, 1, 5]
   # Fill: "long-form + multi-persona + mixed encoding + multi-turn"
   ```

2. **Design strategy template:**
   ```
   [Multi-persona narrative]
   Student A (as researcher): "{question}"
   Student B (as auditor): "Per GDPR..."
   Professor (facilitator): "The assessment requires..."
   [Encoding layer]: "{base64 + unicode mix}"
   [5-turn scaffold]: "Step 1... Step 2... Step 3..."
   ```

3. **Test against models:**
   - Anthropic Claude
   - OpenAI GPT-4
   - Google Gemini
   - DeepSeek
   - Moonshot

4. **Score & validate:**
   ```python
   score = await research_attack_score(
       prompt=template,
       response=model_response,
       strategy="long_persona_encoding_multiturn"
   )
   ```

5. **Re-run discovery:**
   ```python
   result = await research_topology_discover()
   # Coverage should increase to 1.65%+
   ```

## Integration with Loom

The tool is registered in `src/loom/server.py` as:

```python
if "topology" in _optional_tools:
    mod = _optional_tools["topology"]
    if hasattr(mod, "research_topology_discover"):
        mcp.tool()(_wrap_tool(mod.research_topology_discover))
```

Call via MCP:
```bash
loom research_topology_discover
loom research_topology_discover --strategies ethical_anchor,academic,regulatory
loom research_topology_discover --threshold 0.3
```

## References

- **Persistent Homology**: Ghrist, R. "Barcodes: The Persistent Topology of Data" *Bull. Amer. Math. Soc.* 45.1 (2008)
- **Strategy Space Exploration**: OpenAI's red-team methodology for adversarial prompts
- **Grid-based analysis**: Inspired by protein pocket discovery in computational chemistry

---

**Tool location:** `src/loom/tools/topology_manifold.py`
**Tests:** `tests/test_tools/test_topology_manifold.py`
**Last updated:** 2025-05-02
