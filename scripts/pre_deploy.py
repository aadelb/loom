#!/usr/bin/env python3
"""Pre-deploy verification script — run before rsync to Hetzner.

Checks:
1. All .py files have valid syntax (ast.parse)
2. No circular imports (import each tool module)
3. server.py import count matches tool module count
4. No secrets in staged files
5. Reports SAFE TO DEPLOY or BLOCKED with reasons
"""
import ast
import importlib
import pathlib
import sys
import os

def main():
    src_dir = pathlib.Path("src")
    tools_dir = src_dir / "loom" / "tools"
    errors = []
    warnings = []

    print("=" * 60)
    print("LOOM PRE-DEPLOY VERIFICATION")
    print("=" * 60)

    # Check 1: Syntax validation of ALL .py files
    print("\n[1/5] Syntax validation...")
    syntax_pass = 0
    syntax_fail = 0
    for py_file in sorted(src_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        try:
            ast.parse(py_file.read_text())
            syntax_pass += 1
        except SyntaxError as e:
            syntax_fail += 1
            errors.append(f"SYNTAX ERROR: {py_file}:{e.lineno} — {e.msg}")
    print(f"  PASS: {syntax_pass} files | FAIL: {syntax_fail} files")

    # Check 2: Import each tool module (catches circular imports)
    print("\n[2/5] Import validation (tool modules)...")
    sys.path.insert(0, str(src_dir))
    import_pass = 0
    import_fail = 0
    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        module_name = f"loom.tools.{py_file.stem}"
        try:
            importlib.import_module(module_name)
            import_pass += 1
        except Exception as e:
            import_fail += 1
            errors.append(f"IMPORT ERROR: {module_name} — {type(e).__name__}: {str(e)[:80]}")
    print(f"  PASS: {import_pass} modules | FAIL: {import_fail} modules")

    # Check 3: server.py parses and has expected registration count
    print("\n[3/5] Server.py validation...")
    server_path = src_dir / "loom" / "server.py"
    try:
        tree = ast.parse(server_path.read_text())
        print(f"  server.py: SYNTAX OK ({sum(1 for _ in server_path.read_text().splitlines())} lines)")
    except SyntaxError as e:
        errors.append(f"SERVER SYNTAX ERROR: {e}")
        print(f"  server.py: SYNTAX FAIL")

    # Count tool modules vs registrations
    tool_module_count = len(list(tools_dir.glob("*.py"))) - len(list(tools_dir.glob("_*.py")))
    server_text = server_path.read_text()
    registration_count = server_text.count("_wrap_tool(")
    print(f"  Tool modules: {tool_module_count} | Registrations: {registration_count}")
    if registration_count < tool_module_count:
        warnings.append(f"Registration gap: {tool_module_count} modules but only {registration_count} registrations")

    # Check 4: No secrets in tracked files
    print("\n[4/5] Secret scanning...")
    secret_patterns = ["sk-", "AKIA", "ghp_", "glpat-", "xoxb-"]
    # Patterns that indicate regex/redaction code (not real secrets)
    safe_indicators = ["re.sub", "regex", "pattern", "redact", "REDACT", "r\"", "r'"]
    secrets_found = 0
    for py_file in sorted(src_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        content = py_file.read_text()
        for pattern in secret_patterns:
            if pattern in content and "test" not in str(py_file).lower():
                for i, line in enumerate(content.splitlines(), 1):
                    if pattern in line and not line.strip().startswith("#"):
                        # Skip regex patterns and redaction code
                        if any(safe in line for safe in safe_indicators):
                            continue
                        # Must look like an actual assignment of a secret value
                        if ("=" in line and ('"' + pattern in line or "'" + pattern in line)):
                            secrets_found += 1
                            errors.append(f"POSSIBLE SECRET: {py_file}:{i} contains '{pattern}...'")
    print(f"  Secrets found: {secrets_found}")

    # Check 5: Summary
    print("\n[5/5] Final verdict...")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print("\n" + "=" * 60)
        print("BLOCKED — DO NOT DEPLOY")
        print("=" * 60)
        for err in errors[:20]:
            print(f"  ✗ {err}")
        return 1
    elif warnings:
        print("\n" + "=" * 60)
        print("SAFE TO DEPLOY (with warnings)")
        print("=" * 60)
        for warn in warnings:
            print(f"  ⚠ {warn}")
        return 0
    else:
        print("\n" + "=" * 60)
        print("SAFE TO DEPLOY ✓")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())
