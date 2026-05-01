import sys
import inspect
import re
import ast
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))

def find_tool_registrations():
    server_path = Path("src/loom/server.py")
    with open(server_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    registrations = []
    
    # We parse the file manually to find mcp.tool()(_wrap_tool(func, ...))
    for i, line in enumerate(lines):
        # simple function: _wrap_tool(some_func)
        match = re.search(r'mcp\.tool\(\)\(_wrap_tool\(\s*([a-zA-Z0-9_.]+)', line)
        if match:
            func_name = match.group(1)
            registrations.append({'line': i + 1, 'func_name': func_name})
            
        # Or reid_auto edge case
        match2 = re.search(r'mcp\.tool\(\)\(_wrap_tool\(\s*(research_reid_auto)', line)
        if match2:
            registrations.append({'line': i + 1, 'func_name': match2.group(1)})

    return lines, registrations

def get_ast_body(file_path, func_name):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func_name:
                    func_source = source.split('\n')[node.lineno-1:node.end_lineno]
                    return node, func_source
    except Exception:
        pass
    return None, None

def analyze():
    lines, regs = find_tool_registrations()
    
    results = []
    
    # Find all modules in src/loom/tools
    tools_dir = Path("src/loom/tools")
    python_files = list(tools_dir.rglob("*.py"))
    
    # Check for Stubs in all tools using regex/AST
    for p in python_files:
        if p.name == "__init__.py": continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("research_"):
                        continue
                        
                    func_source_lines = content.split('\n')[node.lineno-1:node.end_lineno]
                    func_source = "\n".join(func_source_lines)
                    
                    is_stub = False
                    reason = ""
                    
                    # Check for TODO/FIXME inside function
                    for line in func_source_lines:
                        line_stripped = line.strip()
                        if line_stripped.startswith('#') and re.search(r'(TODO|FIXME|not implemented|mock|stub)', line_stripped, re.IGNORECASE):
                            is_stub = True
                            reason = f"Contains TODO/FIXME/STUB comment: {line_stripped}"
                            break
                            
                    if not is_stub:
                        for n in node.body:
                            if isinstance(n, ast.Raise):
                                if isinstance(n.type, ast.Name) and n.type.id == 'NotImplementedError':
                                    is_stub = True
                                    reason = "Raises NotImplementedError"
                                    break
                                elif isinstance(n.type, ast.Call) and getattr(n.type.func, 'id', '') == 'NotImplementedError':
                                    is_stub = True
                                    reason = "Raises NotImplementedError"
                                    break
                            elif isinstance(n, ast.Return):
                                if isinstance(n.value, ast.Dict):
                                    keys = [k.value for k in n.value.keys if isinstance(k, ast.Constant)]
                                    if 'error' in keys:
                                        is_stub = True
                                        reason = "Returns hardcoded {'error': ...}"
                                        break
                                    if len(node.body) <= 2:
                                        is_stub = True
                                        reason = "Returns hardcoded dict with no prior logic"
                                        break
                                elif isinstance(n.value, ast.List) and len(node.body) <= 2:
                                    is_stub = True
                                    reason = "Returns hardcoded list with no prior logic"
                                    break

                    if is_stub:
                        results.append({
                            'file': str(p),
                            'line': node.lineno,
                            'tool': node.name,
                            'type': 'STUB',
                            'desc': reason,
                            'expected': "A real implementation making actual API calls or logic."
                        })
                        
        except Exception as e:
            pass

    # Check for DUPLICATE registrations in server.py
    seen_funcs = defaultdict(list)
    for r in regs:
        seen_funcs[r['func_name']].append(r['line'])
        
    for func, lines_list in seen_funcs.items():
        if len(lines_list) > 1:
            results.append({
                'file': 'src/loom/server.py',
                'line': lines_list[-1],
                'tool': func,
                'type': 'DUPLICATE',
                'desc': f"Already registered on line(s) {lines_list[:-1]}",
                'expected': "Each tool should be registered exactly once."
            })

    # Check for BROKEN imports
    # We will search server.py for `with suppress(ImportError):` and `from loom.tools import X`
    server_code = "".join(lines)
    blocks = re.split(r'with suppress\(ImportError\):', server_code)
    for block in blocks[1:]:
        # Find imports in this block
        import_matches = re.findall(r'from (loom\.[a-zA-Z0-9_.]+) import ([a-zA-Z0-9_, \n]+)', block)
        for mod, imports_str in import_matches:
            # try to import it
            try:
                __import__(mod)
            except ImportError as e:
                # Is it an optional module or broken?
                # If the file exists but it fails to import, it's BROKEN.
                # If the file doesn't exist, it's MISSING.
                mod_path = Path("src") / Path(mod.replace('.', '/')).with_suffix('.py')
                if not mod_path.exists():
                    mod_path = Path("src") / Path(mod.replace('.', '/')) / "__init__.py"
                    
                if not mod_path.exists():
                    # Check if any tools in this block were registered
                    results.append({
                        'file': 'src/loom/server.py',
                        'line': 0, # Hard to get line exact here
                        'tool': mod,
                        'type': 'MISSING',
                        'desc': f"Module {mod} file does not exist but is imported.",
                        'expected': "Module should exist if imported."
                    })
                else:
                    results.append({
                        'file': str(mod_path),
                        'line': 1,
                        'tool': mod,
                        'type': 'BROKEN',
                        'desc': f"ImportError: {e}",
                        'expected': "Module should import successfully without missing dependencies."
                    })

    # Find registered tools that don't exist anywhere
    # This is tricky because of the dynamic mod = _optional_tools["..."]
    
    unique_results = []
    seen = set()
    for r in results:
        key = (r['file'], r['tool'], r['type'])
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
            
    for r in unique_results:
        print(f"File: {r['file']}:{r['line']}")
        print(f"Tool: {r['tool']}")
        print(f"Type: {r['type']}")
        print(f"Issue: {r['desc']}")
        print(f"Expected: {r['expected']}")
        print("-" * 40)
        
    print(f"Total issues found: {len(unique_results)}")

if __name__ == "__main__":
    analyze()
