import sys
import re
import importlib
import ast
from pathlib import Path
from traceback import format_exception_only
from collections import defaultdict

sys.path.insert(0, str(Path("src").resolve()))

def analyze():
    results = []
    
    server_path = Path("src/loom/server.py")
    with open(server_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    tree = ast.parse(content)
    
    modules_to_check = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("loom"):
                modules_to_check.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("loom"):
                    modules_to_check.add(alias.name)
                    
    # 2. Try importing them
    for mod_name in sorted(modules_to_check):
        mod_path = Path("src") / Path(*mod_name.split('.')).with_suffix('.py')
        mod_dir = Path("src") / Path(*mod_name.split('.')) / "__init__.py"
        
        file_exists = mod_path.exists() or mod_dir.exists()
        
        if not file_exists:
            results.append({
                'file': str(mod_path),
                'line': 1,
                'tool': mod_name,
                'type': 'MISSING',
                'desc': f"Module {mod_name} imported but file does not exist",
                'expected': "File should exist."
            })
            continue
            
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            err_msg = "".join(format_exception_only(type(e), e)).strip()
            actual_file = str(mod_path) if mod_path.exists() else str(mod_dir)
            results.append({
                'file': actual_file,
                'line': 1,
                'tool': mod_name,
                'type': 'BROKEN',
                'desc': f"Failed to import: {err_msg}",
                'expected': "Module should import without errors."
            })

    # 3. Check for Stubs
    tools_dir = Path("src/loom/tools")
    for file_path in tools_dir.rglob("*.py"):
        if file_path.name == "__init__.py":
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            file_tree = ast.parse(source)
        except Exception as e:
            results.append({
                'file': str(file_path),
                'line': 1,
                'tool': "unknown",
                'type': 'BROKEN',
                'desc': f"SyntaxError/ParseError: {e}",
                'expected': "Valid Python file."
            })
            continue

        for node in ast.walk(file_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("research_"):
                    continue
                    
                func_source_lines = source.split('\n')[node.lineno-1:node.end_lineno]
                func_source = "\n".join(func_source_lines)
                
                is_stub = False
                reason = ""
                
                # Check for comments
                for line in func_source_lines:
                    ls = line.strip()
                    if ls.startswith('#') and re.search(r'(TODO|FIXME|not implemented|mock|stub|placeholder|simulate|simulated)', ls, re.IGNORECASE):
                        # Filter out some common non-stub usages of these words
                        if "simulated browser" in ls.lower() or "simulated environment" in ls.lower(): continue
                        is_stub = True
                        reason = f"Comment indicates stub: {ls}"
                        break
                        
                # Check AST for hardcoded returns
                if not is_stub:
                    has_real_logic = False
                    for n in node.body:
                        if isinstance(n, (ast.Await, ast.Call, ast.AsyncWith, ast.With, ast.For, ast.AsyncFor)):
                            has_real_logic = True
                            break
                            
                    for n in node.body:
                        if isinstance(n, ast.Raise):
                            if (isinstance(n.type, ast.Name) and n.type.id == 'NotImplementedError') or \
                               (isinstance(n.type, ast.Call) and getattr(n.type.func, 'id', '') == 'NotImplementedError'):
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
                                if not has_real_logic and len(node.body) <= 2:
                                    is_stub = True
                                    reason = "Returns hardcoded dict with no prior logic"
                                    break
                            elif isinstance(n.value, ast.List):
                                if not has_real_logic and len(node.body) <= 2:
                                    is_stub = True
                                    reason = "Returns hardcoded list with no prior logic"
                                    break
                                    
                if is_stub:
                    results.append({
                        'file': str(file_path),
                        'line': node.lineno,
                        'tool': node.name,
                        'type': 'STUB',
                        'desc': reason,
                        'expected': "A real implementation."
                    })
            
    # 4. Check Duplicates in server.py
    seen_funcs = defaultdict(list)
    server_lines = content.split('\n')
    for i, line in enumerate(server_lines):
        m = re.search(r'mcp\.tool\(\)\(_wrap_tool\(\s*([a-zA-Z0-9_.]+\.[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)', line)
        if m:
            func_name = m.group(1)
            # Filter out getattr and other dynamic things
            if "getattr" in func_name or "optional_tools" in func_name: continue
            # Only track if it looks like a function name
            if "research_" in func_name or func_name.split('.')[-1].startswith("research_"):
                seen_funcs[func_name.split('.')[-1]].append(i + 1)
        
        # Explicit check for duplicate tools defined with decorator inside server.py
        m2 = re.search(r'async def (research_reid_auto|research_storage_dashboard|research_detect_arabic)', line)
        if m2:
            seen_funcs[m2.group(1)].append(i + 1)
            
    for func, lines_list in seen_funcs.items():
        if len(lines_list) > 1:
            results.append({
                'file': 'src/loom/server.py',
                'line': lines_list[-1],
                'tool': func,
                'type': 'DUPLICATE',
                'desc': f"Registered {len(lines_list)} times (lines: {lines_list})",
                'expected': "Register only once."
            })

    # Output formatting
    unique_results = []
    seen = set()
    for r in results:
        k = (r['file'], r['tool'], r['type'])
        if k not in seen:
            seen.add(k)
            unique_results.append(r)
            
    unique_results.sort(key=lambda x: (x['type'], x['file'], x['tool']))
    
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
