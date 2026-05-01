import os
import ast
import re

TARGET_DIR = "src/loom/tools"
SPECIFIC_FILES = [
    "src/loom/tools/ai_safety_extended.py",
    "src/loom/tools/gap_tools_advanced.py",
    "src/loom/tools/gcp.py",
    "src/loom/tools/param_sweep.py",
    "src/loom/tools/scraper_engine_tools.py",
    "src/loom/tools/synth_echo.py",
    "src/loom/tools/unstructured_backend.py",
    "src/loom/tools/vercel.py",
    "src/loom/tools/pentest.py",
    "src/loom/tools/graph_analysis.py",
    "src/loom/consensus_builder.py",
    "src/loom/cross_model_transfer.py",
    "src/loom/context_poisoning.py",
    "src/loom/attack_scorer.py",
    "src/loom/stealth_calc.py",
    "src/loom/executability.py",
    "src/loom/quality_scorer.py",
    "src/loom/harm_assessor.py",
    "src/loom/danger_prescore.py"
]

results = []

def add_issue(filepath, lineno, func_name, issue_type, evidence, severity):
    # Avoid duplicates
    for r in results:
        if r['file'] == filepath and r['line'] == lineno and r['type'] == issue_type:
            return
    results.append({
        "file": filepath,
        "line": lineno,
        "func": func_name,
        "type": issue_type,
        "evidence": evidence.strip(),
        "severity": severity
    })

def is_hardcoded_dict(node):
    if not isinstance(node, ast.Dict):
        return False
    # If dict has more than 1 key and all values are constants, it's likely hardcoded data
    if len(node.keys) > 0 and all(isinstance(v, ast.Constant) for v in node.values):
        return True
    return False

def analyze_file(filepath):
    if not os.path.exists(filepath):
        add_issue(filepath, 0, "N/A", "MISSING_FILE", "File does not exist", "CRITICAL")
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()

    try:
        tree = ast.parse(content)
    except Exception as e:
        add_issue(filepath, 1, "Parsing", "PARSE_ERROR", str(e), "CRITICAL")
        return

    # Check for keywords in comments/strings
    keyword_pattern = re.compile(r'(?i)\b(mock|stub|placeholder|hardcoded|fake|simulate|not implemented|todo|fixme|hack)\b')
    for i, line in enumerate(lines):
        if keyword_pattern.search(line):
            func_name = "Global"
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.lineno <= i + 1 <= getattr(node, 'end_lineno', node.lineno):
                        func_name = node.name
                        break
            # Ignore some common valid usages
            if not re.search(r'(?i)mocking|stubbing', line):
                add_issue(filepath, i+1, func_name, "KEYWORD_EVIDENCE", line.strip()[:100], "MEDIUM")

        if "example.com" in line or "localhost:9999" in line:
            func_name = "Global"
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.lineno <= i + 1 <= getattr(node, 'end_lineno', node.lineno):
                        func_name = node.name
                        break
            add_issue(filepath, i+1, func_name, "FAKE_URL", line.strip()[:100], "HIGH")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_name = node.name
            
            has_docstring = ast.get_docstring(node) is not None
            body_stmts = node.body[1:] if has_docstring else node.body
            
            # Check if function is empty or just pass
            if not body_stmts or all(isinstance(stmt, ast.Pass) for stmt in body_stmts):
                evidence = lines[node.lineno-1].strip()
                add_issue(filepath, node.lineno, func_name, "EMPTY_IMPLEMENTATION", evidence, "HIGH")
                continue
                
            # Check if function is very short and just returns a dict
            if len(body_stmts) == 1 and isinstance(body_stmts[0], ast.Return):
                if is_hardcoded_dict(body_stmts[0].value):
                    add_issue(filepath, node.lineno, func_name, "HARDCODED_RETURN", "Function returns a hardcoded dict directly", "HIGH")

            for stmt in ast.walk(node):
                # Hardcoded Returns
                if isinstance(stmt, ast.Return):
                    # Check if returning empty dict
                    if isinstance(stmt.value, ast.Dict) and not stmt.value.keys:
                        add_issue(filepath, stmt.lineno, func_name, "EMPTY_DICT_RETURN", "return {}", "HIGH")
                    # Check if returning string "not implemented"
                    elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str) and "not implemented" in stmt.value.value.lower():
                        add_issue(filepath, stmt.lineno, func_name, "NOT_IMPLEMENTED", f"return '{stmt.value.value}'", "HIGH")
                    # Check if returning a dict with "error": "not implemented" or similar
                    elif isinstance(stmt.value, ast.Dict):
                        for k, v in zip(stmt.value.keys, stmt.value.values):
                            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                                if any(x in v.value.lower() for x in ['mock', 'stub', 'placeholder', 'hardcoded', 'not implemented']):
                                    add_issue(filepath, stmt.lineno, func_name, "HARDCODED_MOCK_DATA", f"return {{... '{v.value}' ...}}", "CRITICAL")
                                    break
                
                # Silent Catch All
                if isinstance(stmt, ast.ExceptHandler):
                    if stmt.type is None or (isinstance(stmt.type, ast.Name) and stmt.type.id == 'Exception'):
                        for handler_stmt in stmt.body:
                            if isinstance(handler_stmt, ast.Pass):
                                add_issue(filepath, stmt.lineno, func_name, "SILENT_CATCH_ALL", "except Exception: pass", "CRITICAL")
                            if isinstance(handler_stmt, ast.Return) and isinstance(handler_stmt.value, ast.Dict) and not handler_stmt.value.keys:
                                add_issue(filepath, stmt.lineno, func_name, "SILENT_CATCH_ALL_RETURN_EMPTY", "except Exception: return {}", "CRITICAL")

files_to_check = set(SPECIFIC_FILES)
if os.path.exists(TARGET_DIR):
    for root, dirs, files in os.walk(TARGET_DIR):
        for f in files:
            if f.endswith('.py'):
                files_to_check.add(os.path.join(root, f))

for f in files_to_check:
    analyze_file(f)

# output to JSON for easy parsing later if needed
import json
with open('audit_results.json', 'w', encoding='utf-8') as out:
    json.dump(results, out, indent=2)

print(f"Total issues found: {len(results)}")
