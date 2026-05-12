"""Fix 17 PARTIAL tools: remove error field when fallback provided real results."""
import os

tools_dir = "/data/opt/research-toolbox/loom-legal/src/loom_legal/tools"
fixed = 0

partial_tools = [
    "legislation.py", "dubai_law.py", "elaws.py", "federal_law.py",
    "difc.py", "adgm.py", "criminal.py", "labor.py", "commercial.py",
    "personal_status.py", "court_decisions.py", "legal_compare.py",
    "aml_compliance.py", "trademark.py", "dubai_decree.py",
    "municipality.py", "labor_dispute.py"
]

for fname in partial_tools:
    fpath = os.path.join(tools_dir, fname)
    if not os.path.exists(fpath):
        print(f"  SKIP {fname} (not found)")
        continue

    content = open(fpath).read()

    if "error_cleanup" in content:
        print(f"  SKIP {fname} (already fixed)")
        continue

    # Find the main async function
    lines = content.split("\n")

    # Find last return { or return result
    last_return_idx = None
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith("return {") or stripped.startswith("return _result") or stripped.startswith("return result"):
            last_return_idx = i
            break

    if last_return_idx is None:
        print(f"  SKIP {fname} (no return found)")
        continue

    indent = len(lines[last_return_idx]) - len(lines[last_return_idx].lstrip())
    sp = " " * indent

    return_line = lines[last_return_idx].strip()

    if return_line.startswith("return {"):
        # Wrap in variable
        lines[last_return_idx] = lines[last_return_idx].replace("return {", "_final_result = {", 1)

        # Find closing brace
        brace_count = lines[last_return_idx].count("{") - lines[last_return_idx].count("}")
        close_idx = last_return_idx
        while brace_count > 0 and close_idx < len(lines) - 1:
            close_idx += 1
            brace_count += lines[close_idx].count("{") - lines[close_idx].count("}")

        # Insert cleanup after closing brace
        insert = [
            "",
            sp + "# error_cleanup: if fallback gave results, remove error",
            sp + "if isinstance(_final_result, dict) and _final_result.get('results') and len(_final_result.get('results', [])) > 0:",
            sp + "    _final_result.pop('error', None)",
            sp + "return _final_result",
        ]
        for j, line in enumerate(insert):
            lines.insert(close_idx + 1 + j, line)

        open(fpath, "w").write("\n".join(lines))
        fixed += 1
        print(f"  FIXED {fname} (return dict)")

    elif "return result" in return_line or "return _result" in return_line:
        var_name = "result" if "return result" in return_line else "_result"
        insert = [
            sp + f"# error_cleanup: if fallback gave results, remove error",
            sp + f"if isinstance({var_name}, dict) and {var_name}.get('results') and len({var_name}.get('results', [])) > 0:",
            sp + f"    {var_name}.pop('error', None)",
        ]
        for j, line in enumerate(insert):
            lines.insert(last_return_idx + j, line)

        open(fpath, "w").write("\n".join(lines))
        fixed += 1
        print(f"  FIXED {fname} (return var)")

print(f"\nTotal: {fixed}/17 fixed")
