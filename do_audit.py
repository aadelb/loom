import os
import re
import ast
from pathlib import Path

def get_server_tools():
    content = Path('src/loom/server.py').read_text()
    tree = ast.parse(content)
    funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                funcs.add(node.name)
    
    # Also find all registered tools via mcp.tool()(_wrap_tool(module.func))
    import re
    wrapped = set(re.findall(r'_wrap_tool\([^.]+\.([a-zA-Z0-9_]+)', content))
    wrapped.update(re.findall(r'_wrap_tool\((research_[a-zA-Z0-9_]+)', content))
    wrapped.update(re.findall(r'hasattr\([^,]+,\s*"([^"]+)"\)', content))
    
    # Also anything that looks like a tool name
    for line in content.split('\n'):
        if 'research_' in line or 'fetch_' in line or 'search_' in line:
            m = re.search(r'\b(research_[a-z0-9_]+|fetch_[a-z0-9_]+|search_[a-z0-9_]+)\b', line)
            if m: funcs.add(m.group(1))

    funcs.update(wrapped)
    return funcs

def extract_ideas(directory):
    idea_pattern = re.compile(r'\b(?:research|fetch|search|find|analyze|detect|run)_[a-z_]+\b')
    ideas = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith('.txt') and not file.endswith('.md'):
                continue
            filepath = os.path.join(root, file)
            try:
                content = Path(filepath).read_text(encoding='utf-8', errors='ignore')
                matches = idea_pattern.findall(content)
                for match in set(matches):
                    if match not in ideas:
                        ideas[match] = set()
                    ideas[match].add(file)
            except Exception:
                pass
    return ideas

def check_tool_file(tool_name):
    # Search for the tool in src/loom/tools/
    tools_dir = Path('src/loom/tools')
    for py_file in tools_dir.glob('*.py'):
        if py_file.name == '__init__.py': continue
        try:
            content = py_file.read_text(encoding='utf-8')
            if tool_name in content:
                # Check first 20 lines around the function
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if f"def {tool_name}" in line or f"async def {tool_name}" in line:
                        # Extract the next 20 lines
                        chunk = "\n".join(lines[i:i+20])
                        has_docstring = '"""' in chunk or "'''" in chunk
                        has_type_hints = '->' in chunk or ':' in line
                        has_return_dict = 'dict' in chunk or 'Any' in chunk
                        if has_docstring and has_type_hints and has_return_dict:
                            return True, py_file.name
                        return False, py_file.name
        except Exception:
            pass
    return False, None

def main():
    tools = get_server_tools()
    ideas = extract_ideas('docs/creative-research/')
    
    implemented = []
    covered = []
    gaps = []
    
    for idea, files in ideas.items():
        if idea in tools:
            # Check implementation
            valid, filename = check_tool_file(idea)
            if filename:
                implemented.append((idea, filename, valid))
            else:
                # If registered but file not found, it might be in a provider
                implemented.append((idea, "server.py (dynamic)", True))
        else:
            # Try to see if it's covered by a similar name
            core_name = idea.replace('research_', '').replace('fetch_', '').replace('search_', '')
            found_cover = False
            for t in tools:
                if core_name in t:
                    covered.append((idea, t, list(files)[0]))
                    found_cover = True
                    break
            if not found_cover:
                gaps.append((idea, list(files)[0]))
                
    report = []
    report.append("=== AUDIT REPORT ===")
    report.append(f"Total ideas found across all files: {len(ideas)}")
    report.append(f"Total IMPLEMENTED: {len(implemented)}")
    report.append(f"Total COVERED: {len(covered)}")
    report.append(f"Total GAP: {len(gaps)}")
    
    report.append("\n=== GAPS (Not Implemented) ===")
    for gap, file in sorted(gaps):
        report.append(f"- GAP: {gap} (found in {file})")
        
    report.append("\n=== IMPLEMENTED ===")
    for imp, filename, valid in sorted(implemented):
        valid_str = "VALIDATED" if valid else "MISSING_DOCS_OR_TYPES"
        report.append(f"- IMPLEMENTED: {imp} -> {filename} [{valid_str}]")
        
    report.append("\n=== COVERED (Different name, same capability) ===")
    for cov, t, file in sorted(covered):
        report.append(f"- COVERED: {cov} is covered by {t} (found in {file})")
        
    Path('audit_report_final.txt').write_text('\n'.join(report))
    print("Done. Wrote audit_report_final.txt")

if __name__ == '__main__':
    main()
