# Triple-Model Code Validation Pipeline

A developer workflow tool that sends code to 3 independent models for quality review and reports findings by confidence level.

## Overview

`triple_validate.py` implements a code review pipeline that leverages multiple models for higher-confidence issue detection:

1. **Gemini** (via `gemini` CLI): Code quality, bugs, and improvements
2. **Kimi** (via `kimi` CLI): Problem identification and issues
3. **Claude/Opus** (synthesis): Combines findings into unified analysis

Issues are aggregated based on how many models found them:
- **HIGH confidence**: Found by all 3 models
- **MEDIUM confidence**: Found by 2 models
- **LOW confidence**: Found by 1 model

## Installation

### Prerequisites

Ensure CLI tools are installed and available in PATH:

```bash
# Gemini CLI (via Google's gemini package)
pip install google-generativeai-cli
# or
gemini --version

# Kimi CLI (via kimi-cli package)
pip install kimi-cli
# or
kimi --version

# Claude (via Anthropic SDK)
pip install anthropic
```

## Usage

```bash
# Basic validation
python scripts/triple_validate.py src/loom/server.py

# With JSON output
python scripts/triple_validate.py src/loom/tools/fetch.py --json

# With custom timeout
python scripts/triple_validate.py src/loom/core.py --timeout 120
```

## Output Format

### Human-Readable Report

```
================================================================================
TRIPLE-MODEL CODE VALIDATION REPORT
================================================================================
File: src/loom/server.py

SUMMARY:
  Total aggregated issues: 15
  HIGH confidence (all 3 models): 2
  MEDIUM confidence (2 models): 5
  LOW confidence (1 model): 8

HIGH CONFIDENCE ISSUES (Found by all 3 models)
================================================================================

  [HIGH] Missing type hints on function parameters
    Found by: gemini, kimi, claude

  [HIGH] Potential SQL injection vulnerability in database query
    Found by: gemini, kimi, claude

MEDIUM CONFIDENCE ISSUES (Found by 2 models)
================================================================================

  [MEDIUM] Inefficient loop structure could use list comprehension
    Found by: gemini, kimi

  ...

RESULT: FAILED (HIGH confidence issues found)
Exit code: 1
```

### JSON Output

```bash
python scripts/triple_validate.py file.py --json
```

Returns structured JSON:

```json
{
  "file_path": "src/loom/server.py",
  "summary": {
    "total_aggregated": 15,
    "high_confidence": 2,
    "medium_confidence": 5,
    "low_confidence": 8
  },
  "issues": [
    {
      "text": "Missing type hints on function parameters",
      "confidence": "HIGH",
      "models_found_by": ["gemini", "kimi", "claude"]
    },
    ...
  ]
}
```

## Exit Codes

- **0**: No HIGH confidence issues found (validation passed)
- **1**: Any HIGH confidence issues found (validation failed) or error occurred

## Configuration

### Timeouts

Each model has a 60-second timeout by default (adjustable via `--timeout`):

```bash
# 120-second timeout for slower connections
python scripts/triple_validate.py file.py --timeout 120
```

## How It Works

1. **Read Code**: Load Python file into memory
2. **Validate**: Send to all 3 models in sequence
   - Gemini: "Review for bugs and issues"
   - Kimi: "Find any problems in this code"
   - Claude: "Synthesize both reviews"
3. **Aggregate**: Group similar issues across models
4. **Report**: Categorize by confidence level (HIGH/MEDIUM/LOW)
5. **Exit**: Return appropriate exit code

## Error Handling

- Missing CLI tools: Gracefully skip model, report warning
- Network timeouts: Retry with warning, continue with other models
- Invalid file paths: Fail fast with clear error message
- Partial failures: Report what was found, indicate partial pipeline completion

## Limitations

- Requires internet connection for all 3 models
- CLI tools must be installed and authenticated
- Code size limited by CLI input buffer (typically 1-2MB)
- Timeouts may occur on slow networks or with large files
- Semantic similarity matching is basic (not using embeddings)

## Use Cases

### Pre-Commit Validation

```bash
#!/bin/bash
# .git/hooks/pre-commit
python scripts/triple_validate.py src/loom/server.py
if [ $? -ne 0 ]; then
  echo "Code validation failed. Fix HIGH confidence issues before committing."
  exit 1
fi
```

### CI/CD Pipeline

```yaml
# .github/workflows/validate.yml
- name: Triple-Model Code Validation
  run: |
    python scripts/triple_validate.py src/loom/server.py --json > validation_report.json
    if [ $? -ne 0 ]; then
      cat validation_report.json
      exit 1
    fi
```

### Manual Code Review

```bash
# Review critical files before PR
python scripts/triple_validate.py src/loom/server.py
python scripts/triple_validate.py src/loom/tools/fetch.py
python scripts/triple_validate.py src/loom/providers/base.py
```

## Performance

Typical execution times:

- Single file validation: 2-5 minutes (sequential model calls)
- Small file (<1KB): 1-2 minutes
- Medium file (1-10KB): 2-3 minutes
- Large file (10-50KB): 3-5 minutes

Note: Models are called sequentially to reduce memory overhead on local systems.

## Contributing

To improve issue aggregation:

1. Enhance `_parse_model_response()` for better parsing
2. Add fuzzy matching in `aggregate_issues()` using difflib or embeddings
3. Implement concurrent model calls with `asyncio.gather()`
4. Add support for additional models (DeepSeek, Moonshot, etc.)

## Author

Ahmed Adel Bakr Alderai

## License

Same as parent Loom project
