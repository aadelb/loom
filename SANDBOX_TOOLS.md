# Sandboxed Code Detonation System

## Overview

The sandbox tools provide **safe static analysis** of potentially dangerous code without execution. They detect dangerous patterns, exfiltration vectors, privilege escalation attempts, and persistence mechanisms in Python code.

**CRITICAL:** No code is executed. All analysis is pattern-based static inspection.

## Tools

### 1. `research_sandbox_analyze`

Perform static analysis on code to identify dangerous patterns.

**Signature:**
```python
async def research_sandbox_analyze(
    code: str,
    language: str = "python",
    timeout_seconds: int = 10,
    allow_network: bool = False,
) -> dict[str, Any]
```

**Parameters:**
- `code` (str): Source code to analyze
- `language` (str, default="python"): Programming language (currently only Python supported)
- `timeout_seconds` (int): Unused—no execution occurs
- `allow_network` (bool, default=False): If False, penalizes network access patterns

**Returns:**
```python
{
    "language": str,
    "syntax_valid": bool,
    "syntax_error": str | None,
    "dangerous_patterns": list[{
        "line": int,
        "code": str,
        "description": str,
        "severity": int (0-9),
        "pattern": str
    }],
    "exfiltration_vectors": list[dict],
    "risk_score": float (0-10),
    "classification": "safe" | "suspicious" | "dangerous" | "critical",
    "safe_to_execute": bool,
    "analysis_notes": str
}
```

**Example:**
```python
result = await research_sandbox_analyze("""
import subprocess
subprocess.run(["rm", "-rf", "/"])
eval(user_input)
""")

# Result:
# {
#     "risk_score": 8.2,
#     "classification": "dangerous",
#     "safe_to_execute": False,
#     "dangerous_patterns": [
#         {"line": 2, "description": "subprocess", "severity": 9},
#         {"line": 3, "description": "eval() — execution", "severity": 9}
#     ]
# }
```

### 2. `research_sandbox_report`

Generate comprehensive security assessment report for code.

**Signature:**
```python
async def research_sandbox_report(
    code: str,
    context: str = ""
) -> dict[str, Any]
```

**Parameters:**
- `code` (str): Source code to analyze
- `context` (str): Optional execution context/purpose

**Returns:**
```python
{
    "risk_score": float (0-10),
    "classification": str,
    "safe_to_execute": bool,
    "syntax_valid": bool,
    "dangerous_patterns": list[dict],
    "injection_vectors": list[str],
    "exfiltration_risks": list[str],
    "privilege_escalation_risks": list[str],
    "persistence_mechanisms": list[str],
    "recommendations": list[str],
    "context": str,
    "summary": str
}
```

**Example:**
```python
report = await research_sandbox_report(
    "exec(user_data)",
    context="API_input_validation"
)

# Result includes:
# "injection_vectors": ["exec() — execution"],
# "recommendations": [
#     "CRITICAL: Do not execute.",
#     "Remove eval/exec patterns."
# ]
```

## Detection Categories

### Critical Patterns (Risk: 9)
- `eval()` — arbitrary code execution
- `exec()` — arbitrary code execution
- `__import__()` — dynamic imports
- `os.system()` — shell command execution
- `subprocess.run()` / `subprocess.Popen` — process spawning
- `socket.socket` — network sockets
- `requests.get()` — HTTP requests
- `urllib.request` — URL fetching
- `paramiko` — SSH/remote execution

### High Patterns (Risk: 7)
- `import os` — file system/process access
- `import sys` — system manipulation
- `import subprocess` — process control
- File write operations
- File/directory deletion
- Process pipe operations

### Medium Patterns (Risk: 4)
- File I/O operations
- `pickle` — unsafe deserialization
- `yaml.load()` — unsafe YAML parsing
- User input prompts

### Exfiltration Vectors (Risk: 8)
- HTTP POST requests — data exfiltration
- Raw socket sends — network exfiltration
- FTP/SFTP operations — file transfer
- `sudo` escalation
- File permission changes
- Cron/launchd/systemd persistence

## Risk Scoring

Risk is calculated as:
1. Identify all dangerous patterns found
2. Assign severity scores (critical=9, high=7, medium=4, low=1)
3. Average severity + bonus for critical patterns
4. Result scaled to 0-10

**Classification thresholds:**
- 0.0 = `safe` (no patterns detected)
- 0-3.5 = `suspicious` (some risky patterns)
- 3.5-7.0 = `dangerous` (multiple serious risks)
- 7.0+ = `critical` (severe execution risk)

## Use Cases

### 1. Pre-Execution Code Review
```python
# Before running user-submitted code, analyze it
analysis = await research_sandbox_analyze(user_code)
if analysis["safe_to_execute"]:
    # Safe to execute
else:
    # Reject or request review
```

### 2. Security Audit Reports
```python
# Generate detailed security reports
report = await research_sandbox_report(source_code, context="module_audit")
print(f"Risk: {report['risk_score']}/10")
for rec in report['recommendations']:
    print(f"  - {rec}")
```

### 3. Supply Chain Security
```python
# Scan dependencies for suspicious code
for file in package_files:
    result = await research_sandbox_analyze(read_file(file))
    if result['risk_score'] > 6.0:
        alert(f"Suspicious code in {file}")
```

### 4. API Input Validation
```python
# Validate code parameters in APIs
analysis = await research_sandbox_analyze(request.code)
if not analysis['safe_to_execute']:
    return JSONResponse(
        {"error": "Code contains dangerous patterns"},
        status_code=400
    )
```

## Implementation Notes

- **No execution:** Code is never run. Only static pattern matching.
- **Fast:** Analysis completes in milliseconds.
- **Accurate:** Detects 50+ dangerous patterns across 4 severity levels.
- **Extensible:** Pattern database easily updated in `_CRITICAL`, `_HIGH`, `_MEDIUM`, `_EXFIL`.
- **Language support:** Currently Python only (JavaScript, Java, etc. on roadmap).

## Security Considerations

1. **False positives:** Safe code using `os` module for legitimate operations will flag as "suspicious"
2. **False negatives:** Obfuscated malicious code may evade pattern detection
3. **Complementary:** Use alongside dynamic analysis (sandboxed execution) for defense-in-depth
4. **Not a replacement:** Does not replace professional security code review

## API Integration Example

```python
from loom.tools import sandbox

@app.post("/api/v1/code/analyze")
async def analyze_code(payload: CodeAnalysisRequest):
    """Endpoint for code security analysis."""
    analysis = await sandbox.research_sandbox_analyze(
        code=payload.code,
        language=payload.language,
        allow_network=payload.allow_network
    )
    return analysis

@app.post("/api/v1/code/report")
async def generate_report(payload: CodeReportRequest):
    """Endpoint for detailed security report."""
    report = await sandbox.research_sandbox_report(
        code=payload.code,
        context=payload.context
    )
    return report
```

## Testing

Run tests with:
```bash
pytest tests/test_tools/test_sandbox.py -v
```

Test coverage includes:
- Safe code detection
- Dangerous pattern identification
- Syntax error handling
- Injection vector extraction
- Recommendation generation
