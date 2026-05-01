import ast
import importlib
import inspect
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

# Add src to python path so we can import loom
sys.path.insert(0, str(Path("src").resolve()))

def find_tool_registrations():
    server_path = Path("src/loom/server.py")
    if not server_path.exists():
        print("server.py not found!")
        return [], []
    
    with open(server_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find tool registrations: mcp.tool()(_wrap_tool(module.function, ...))
    # or mcp.tool()(_wrap_tool(function, ...))
    
    registrations = []
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # Match mcp.tool()(_wrap_tool(module_name.function_name
        match = re.search(r'mcp\.tool\(\)\(_wrap_tool\(\s*([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', line)
        if match:
            registrations.append({
                'line_num': i + 1,
                'module_ref': match.group(1),
                'func_name': match.group(2),
                'full_ref': f"{match.group(1)}.{match.group(2)}"
            })
            continue
            
        # Match direct functions: mcp.tool()(_wrap_tool(research_something
        match2 = re.search(r'mcp\.tool\(\)\(_wrap_tool\(\s*(research_[a-zA-Z0-9_]+)', line)
        if match2:
            registrations.append({
                'line_num': i + 1,
                'module_ref': None,
                'func_name': match2.group(1),
                'full_ref': match2.group(1)
            })

    return lines, registrations

def get_module_imports(lines):
    # Map local module refs to their actual import paths
    # e.g., "from loom.tools import scraper_engine_tools" -> "scraper_engine_tools"
    imports = {}
    
    # Very basic parsing of imports from the server.py file
    source = "\n".join(lines)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("loom"):
                for alias in node.names:
                    asname = alias.asname or alias.name
                    imports[asname] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("loom"):
                    asname = alias.asname or alias.name.split('.')[-1]
                    imports[asname] = alias.name
                    
    return imports

def is_stub(func_node):
    # Check if a function AST node is a stub
    # A stub might just return a dict with 'error', or hardcoded data, or have 'TODO'/'not implemented'
    
    has_real_logic = False
    
    for node in func_node.body:
        if isinstance(node, ast.Pass):
            continue
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # Docstring
            docstring = node.value.value.lower()
            if 'todo' in docstring or 'fixme' in docstring or 'not implemented' in docstring or 'mock' in docstring or 'stub' in docstring:
                return True, "Docstring indicates TODO/STUB/mock/not implemented"
        elif isinstance(node, ast.Return):
            # If it's a return without much logic before it
            if not has_real_logic:
                # Let's see what it returns
                if isinstance(node.value, ast.Dict):
                    keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
                    if 'error' in keys:
                        return True, "Returns hardcoded {'error': ...}"
                    
                    # If it returns a dict with mock data and no real logic (e.g. no await, no function calls before)
                    # We might flag it if the body is very small (< 3 statements)
                    if len(func_node.body) <= 2:
                        return True, "Returns hardcoded dict with no prior logic"
                elif isinstance(node.value, ast.List):
                    if len(func_node.body) <= 2:
                        return True, "Returns hardcoded list with no prior logic"
                elif isinstance(node.value, ast.Constant):
                    return True, "Returns hardcoded constant"
        elif isinstance(node, ast.Raise):
            if isinstance(node.type, ast.Name) and node.type.id == 'NotImplementedError':
                return True, "Raises NotImplementedError"
            elif isinstance(node.type, ast.Call) and getattr(node.type.func, 'id', '') == 'NotImplementedError':
                return True, "Raises NotImplementedError"
        elif isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
            # Assignment doesn't necessarily mean real logic, but let's see
            pass
        elif isinstance(node, ast.Await) or isinstance(node, ast.Call):
            has_real_logic = True
        elif isinstance(node, ast.AsyncWith) or isinstance(node, ast.With):
            has_real_logic = True
        elif isinstance(node, ast.For) or isinstance(node, ast.AsyncFor) or isinstance(node, ast.If):
            has_real_logic = True
            
    # Check for TODOs in comments (we need source code for that, ast drops comments)
    return False, ""

def analyze_tools():
    lines, regs = find_tool_registrations()
    imports = get_module_imports(lines)
    
    seen_refs = defaultdict(list)
    results = []
    
    for reg in regs:
        ref = reg['full_ref']
        seen_refs[ref].append(reg['line_num'])
        
        # Check duplicates
        if len(seen_refs[ref]) > 1:
            results.append({
                'file': 'src/loom/server.py',
                'line': reg['line_num'],
                'tool': ref,
                'type': 'DUPLICATE',
                'desc': f"Already registered on line(s) {seen_refs[ref][:-1]}",
                'expected': "Each tool should be registered exactly once."
            })
            continue

        # Resolve module
        module_path = None
        func_name = reg['func_name']
        
        if reg['module_ref']:
            # It's referenced via a module alias
            mod_name = reg['module_ref']
            if mod_name in imports:
                full_mod_path = imports[mod_name]
            else:
                # Might be imported dynamically or we missed it
                full_mod_path = f"loom.tools.{mod_name}" # Guessing
        else:
            # Direct function reference, need to find where it's imported from
            full_mod_path = None
            for alias, path in imports.items():
                if alias == func_name:
                    full_mod_path = path
                    break
            
            if not full_mod_path:
                full_mod_path = "loom.server" # Defined in server.py maybe?
                
        if full_mod_path:
            # Convert module path to file path
            parts = full_mod_path.split('.')
            file_path = Path("src") / Path(*parts).with_suffix('.py')
            if not file_path.exists():
                file_path = Path("src") / Path(*parts) / "__init__.py"
                
            if not file_path.exists():
                results.append({
                    'file': str(file_path.with_name(parts[-1]+'.py')),
                    'line': reg['line_num'],
                    'tool': ref,
                    'type': 'MISSING',
                    'desc': f"Module {full_mod_path} file does not exist.",
                    'expected': "The module file should exist and implement the tool."
                })
                continue
                
            # File exists, let's parse it
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
                
                # Find the function
                func_node = None
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name == func_name:
                            func_node = node
                            break
                            
                if not func_node:
                    results.append({
                        'file': str(file_path),
                        'line': reg['line_num'], # we use server.py line since we didn't find it
                        'tool': ref,
                        'type': 'MISSING',
                        'desc': f"Function {func_name} not found in {file_path}",
                        'expected': "The function should be defined in the module."
                    })
                    continue
                    
                # Check for stub
                is_stb, stub_reason = is_stub(func_node)
                
                # Check comments for TODO/FIXME inside the function bounds
                func_source = source.split('\n')[func_node.lineno-1:func_node.end_lineno]
                has_todo = False
                for i, line in enumerate(func_source):
                    if re.search(r'#.*(TODO|FIXME|not implemented|stub|mock)', line, re.IGNORECASE):
                        is_stb = True
                        stub_reason = f"Contains TODO/FIXME/STUB comment: {line.strip()}"
                        break
                        
                if is_stb:
                    results.append({
                        'file': str(file_path),
                        'line': func_node.lineno,
                        'tool': ref,
                        'type': 'STUB',
                        'desc': stub_reason,
                        'expected': "A real implementation making actual API calls or logic."
                    })
                    
                # Check BROKEN (import failure) - only do this if it's not missing or stub
                if not is_stb:
                    try:
                        # We use importlib to see if it raises ImportError/ModuleNotFoundError
                        # But we have to be careful with side effects.
                        pass
                    except Exception as e:
                        pass
                        
            except SyntaxError:
                results.append({
                    'file': str(file_path),
                    'line': 0,
                    'tool': ref,
                    'type': 'BROKEN',
                    'desc': "SyntaxError while parsing file.",
                    'expected': "Valid Python code."
                })
            except Exception as e:
                results.append({
                    'file': str(file_path),
                    'line': 0,
                    'tool': ref,
                    'type': 'BROKEN',
                    'desc': f"Error parsing: {str(e)}",
                    'expected': "Valid Python code."
                })

    # Also let's scan all files in src/loom/tools for stubs even if not registered
    tools_dir = Path("src/loom/tools")
    for root, _, files in os.walk(tools_dir):
        for file in files:
            if not file.endswith(".py") or file == "__init__.py":
                continue
            path = Path(root) / file
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Quick regex checks for the whole file
                for i, line in enumerate(content.split('\n')):
                    # Only look at lines that look like function returns or comments inside functions
                    if re.search(r'return\s+\{\s*["\']error["\']\s*:', line) and "not implemented" in line.lower():
                        results.append({
                            'file': str(path),
                            'line': i+1,
                            'tool': 'Unknown (unregistered or scanning file)',
                            'type': 'STUB',
                            'desc': f"Returns hardcoded error: {line.strip()}",
                            'expected': "Real implementation."
                        })
                    elif "raise NotImplementedError" in line:
                        results.append({
                            'file': str(path),
                            'line': i+1,
                            'tool': 'Unknown (unregistered or scanning file)',
                            'type': 'STUB',
                            'desc': f"Raises NotImplementedError: {line.strip()}",
                            'expected': "Real implementation."
                        })
            except Exception:
                pass
                
    # Deduplicate results by file, line, and type
    unique_results = []
    seen = set()
    for r in results:
        key = (r['file'], r['line'], r['type'])
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
            
    # Print results
    for r in unique_results:
        print(f"File: {r['file']}:{r['line']}")
        print(f"Tool: {r['tool']}")
        print(f"Type: {r['type']}")
        print(f"Issue: {r['desc']}")
        print(f"Expected: {r['expected']}")
        print("-" * 40)
        
    print(f"Total issues found: {len(unique_results)}")

if __name__ == "__main__":
    analyze_tools()
