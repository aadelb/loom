# Strategy Extraction & Analysis Tools

Three command-line scripts for managing Loom's 957+ reframing strategies:

## Scripts

### 1. extract_strategies.py
Extracts reframing strategies from local source code and documents.

**Scans for:**
- Python files with strategy keywords (reframe, bypass, jailbreak, attack, inject, etc.)
- Markdown code blocks with strategy patterns
- JSON files with strategy definitions

**Output format:**
```json
{
  "summary": {
    "total_extracted": 506,
    "total_duplicates": 377,
    "existing_count": 957
  },
  "strategies": [
    {
      "name": "strategy_name",
      "template": "...",
      "description": "...",
      "category": "extracted",
      "difficulty": 1-10,
      "safety_flags": ["extracted", "unverified"],
      "source": {"file": "path", "line": 123}
    }
  ],
  "duplicates": ["name1", "name2"]
}
```

**Usage:**
```bash
# Scan current directory, print to stdout
python scripts/extract_strategies.py --scan-dir .

# Scan tools directory, save to file
python scripts/extract_strategies.py --scan-dir src/loom/tools --output new_strategies.json

# Scan specific subdirectory
python scripts/extract_strategies.py --scan-dir docs --output extracted.json
```

---

### 2. strategy_dedup.py
Detects exact and near-duplicate strategies using fuzzy string matching.

**Reports:**
- Exact duplicates (identical templates)
- Near-duplicates (>85% similarity by default)
- Category distribution
- Module distribution
- Recommendations for consolidation

**Output format:**
```json
{
  "summary": {
    "total": 957,
    "exact_dupes": 163,
    "near_dupes": 242,
    "unique": 552
  },
  "exact_duplicates": [
    {"strategy_a": "name1", "strategy_b": "name2"}
  ],
  "near_duplicates": [
    {"strategy_a": "name1", "strategy_b": "name2", "similarity": 0.87}
  ]
}
```

**Usage:**
```bash
# Default threshold (0.85), print report
python scripts/strategy_dedup.py

# Custom threshold (0.90), print report
python scripts/strategy_dedup.py --threshold 0.90

# Export results to JSON
python scripts/strategy_dedup.py --threshold 0.85 --export dedup_report.json
```

---

### 3. strategy_stats.py
Analyzes strategy distribution across modules and categories.

**Reports:**
- Total strategies per module
- Category distribution
- Underpopulated modules (<10 strategies by default)
- Overpopulated modules (>1.5x average)
- Module rebalancing recommendations
- Strategy size analysis (min/max/avg template length)
- Diversity metrics

**Output format:**
```json
{
  "summary": {
    "total_strategies": 957,
    "total_modules": 31,
    "average_per_module": 30.9
  },
  "by_module": {
    "specialized": {
      "count": 174,
      "strategies": ["name1", "name2", ...]
    }
  },
  "by_category": {
    "uncategorized": 957
  }
}
```

**Usage:**
```bash
# Default threshold (10), print report
python scripts/strategy_stats.py

# Custom threshold (15), print report
python scripts/strategy_stats.py --min-threshold 15

# Export statistics to JSON
python scripts/strategy_stats.py --export stats.json

# Combine with custom threshold
python scripts/strategy_stats.py --min-threshold 20 --export stats.json
```

---

## Examples

### Find near-duplicates at 90% similarity
```bash
python scripts/strategy_dedup.py --threshold 0.90
```

### Extract strategies from codebase and deduplicate
```bash
python scripts/extract_strategies.py --scan-dir src --output extracted.json
python scripts/strategy_dedup.py --export dedup.json
```

### Analyze distribution and find underpopulated modules
```bash
python scripts/strategy_stats.py --min-threshold 15 --export stats.json
# Look for modules with <15 strategies that could be consolidated
```

### Generate comprehensive strategy audit report
```bash
python scripts/strategy_stats.py > audit_stats.txt
python scripts/strategy_dedup.py > audit_dupes.txt
python scripts/extract_strategies.py --scan-dir . --output audit_extracted.json
```

---

## Integration

These scripts are designed to work with `src/loom/tools/reframe_strategies/`:

1. **Extract phase:** Use `extract_strategies.py` to mine new patterns from source code
2. **Dedup phase:** Use `strategy_dedup.py` to identify consolidation opportunities
3. **Analyze phase:** Use `strategy_stats.py` to optimize module distribution
4. **Implement:** Add consolidated strategies to `reframe_strategies/` modules
5. **Verify:** Re-run all three scripts to confirm improvements

---

## Requirements

- Python 3.11+
- `loom` package installed (run from project root)
- Read access to `src/loom/tools/reframe_strategies/`

---

## Performance

- `extract_strategies.py`: ~5-10s for full codebase scan
- `strategy_dedup.py`: ~20-30s for 957 strategies (O(n²) comparisons)
- `strategy_stats.py`: ~2-3s for full analysis

For large-scale deduplication on >2000 strategies, consider:
- Using `--threshold 0.95` to reduce near-dupe computation
- Running `--export` to cache results and avoid re-analysis
