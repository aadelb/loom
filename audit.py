import ast
import os
import sys
import glob
from collections import defaultdict
import re

def main():
    src_files = glob.glob("src/loom/**/*.py", recursive=True)
    tests_files = glob.glob("tests/**/*.py", recursive=True)
    
    # 1. Collect all functions
    all_functions = {} # file -> list of func names
    research_funcs = {} # func_name -> file
    search_funcs = {}
    find_funcs = {}
    
    for f in src_files:
        with open(f, "r", encoding="utf-8") as file:
            try:
                tree = ast.parse(file.read(), filename=f)
                all_functions[f] = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        all_functions[f].append((node.name, node.lineno))
                        if node.name.startswith("research_"):
                            research_funcs[node.name] = (f, node.lineno)
                        elif node.name.startswith("search_"):
                            search_funcs[node.name] = (f, node.lineno)
                        elif node.name.startswith("find_"):
                            find_funcs[node.name] = (f, node.lineno)
            except Exception as e:
                print(f"Failed to parse {f}: {e}")

    # Check 1: Unregistered functions
    print("\n=== 1. UNREGISTERED FUNCTIONS ===")
    with open("src/loom/server.py", "r", encoding="utf-8") as file:
        server_content = file.read()
    
    # We will also parse server.py to see tools
    registered_tools = set()
    server_tree = ast.parse(server_content)
    for node in ast.walk(server_tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "tool":
                # It might be mcp.tool()(func)
                pass # This is tricky, let's just use regex for @mcp.tool() or mcp.tool()(func)
                
    mcp_tool_regex = re.compile(r'mcp\.tool\(\)\s*\(\s*(?:[\w_]+\.)?([\w_]+)\s*\)')
    registered_tools.update(mcp_tool_regex.findall(server_content))
    
    # Look for @mcp.tool() decorators in server.py
    for node in ast.walk(server_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "tool":
                        registered_tools.add(node.name)
    
    # creative tools dynamically registered?
    if "_creative_tools" in server_content or "creative_mod" in server_content:
        # let's add all from creative.py
        for fn in all_functions.get("src/loom/tools/creative.py", []):
            if fn[0].startswith("research_"):
                registered_tools.add(fn[0])
                
    all_target_funcs = {**research_funcs, **search_funcs, **find_funcs}
    for func, (f, line) in all_target_funcs.items():
        if func not in registered_tools and func != "research_session_open": # just an example
            # check if it's registered in other ways or used internally
            # It asks if they are registered as MCP tool in server.py
            if func not in registered_tools:
                print(f"- {f}:{line} : {func} is NOT explicitly registered as MCP tool in server.py.")

    # Check 2: Search routing completeness
    print("\n=== 2. SEARCH ROUTING COMPLETENESS ===")
    provider_files = [os.path.basename(p).replace(".py", "") for p in glob.glob("src/loom/providers/*.py") if not p.endswith("__init__.py") and not p.endswith("base.py") and not p.endswith("anthropic_provider.py") and not p.endswith("openai_provider.py") and not p.endswith("nvidia_nim.py") and not p.endswith("vllm_local.py")]
    
    with open("src/loom/tools/search.py", "r", encoding="utf-8") as file:
        search_py = file.read()
        
    routed_providers = set(re.findall(r'elif provider == "([^"]+)"|if provider == "([^"]+)"', search_py))
    routed_providers = {p for tup in routed_providers for p in tup if p}
    
    for pf in provider_files:
        # map filename to provider name roughly
        pname = pf.replace("_search", "").replace("_extract", "")
        if pname not in routed_providers and pf not in routed_providers:
            print(f"- src/loom/tools/search.py : Provider '{pf}' (or '{pname}') is NOT routed in search.py.")

    # Check 3: Literal Type Consistency
    print("\n=== 3. LITERAL TYPE CONSISTENCY ===")
    literal_regex = re.compile(r'Literal\[(.*?)\]')
    required_providers = {"exa", "tavily", "firecrawl", "brave", "ddgs", "arxiv", "wikipedia"}
    
    for f in src_files:
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
            for i, line in enumerate(content.split('\n'), 1):
                matches = literal_regex.findall(line)
                for m in matches:
                    if 'exa' in m or 'provider' in line.lower():
                        # Parse the literal elements
                        elements = {e.strip(' \'"') for e in m.split(',')}
                        if not required_providers.issubset(elements):
                            missing = required_providers - elements
                            print(f"- {f}:{i} : Literal is missing providers: {missing}. Found: {elements}")

    # Check 4: Dynamic Import Completeness
    print("\n=== 4. DYNAMIC IMPORT COMPLETENESS ===")
    with open("src/loom/providers/__init__.py", "r", encoding="utf-8") as file:
        init_content = file.read()
    
    for pf in provider_files:
        if pf not in init_content:
            print(f"- src/loom/providers/__init__.py : Missing dynamic import mapping for '{pf}.py'")

    # Check 5: Test coverage gaps
    print("\n=== 5. TEST COVERAGE GAPS ===")
    test_basenames = [os.path.basename(t) for t in tests_files]
    for f in glob.glob("src/loom/providers/*.py") + glob.glob("src/loom/tools/*.py"):
        if f.endswith("__init__.py") or f.endswith("base.py"): continue
        base = os.path.basename(f).replace(".py", "")
        expected_test = f"test_{base}.py"
        # fuzzy match
        found = False
        for tb in test_basenames:
            if base in tb or base.split("_")[0] in tb:
                found = True
                break
        if not found:
            print(f"- {f} : Missing corresponding test file (expected something like {expected_test})")

    # Check 6: Deep Pipeline Completeness
    print("\n=== 6. DEEP PIPELINE COMPLETENESS ===")
    with open("src/loom/tools/deep.py", "r", encoding="utf-8") as file:
        deep_content = file.read()
    
    tools_used_in_deep = set(re.findall(r'research_[a-zA-Z_]+', deep_content))
    all_tools = set(research_funcs.keys())
    print(f"Tools used in deep.py: {tools_used_in_deep}")
    print(f"Tools NOT used in deep.py: {all_tools - tools_used_in_deep}")

    # Check 7: Import Path Validation
    print("\n=== 7. IMPORT PATH VALIDATION ===")
    # Extract defined classes/funcs per file
    exports = defaultdict(set)
    for f in src_files:
        module_path = f.replace("src/", "").replace(".py", "").replace("/", ".")
        if module_path.endswith(".__init__"):
            module_path = module_path[:-9]
        with open(f, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    exports[module_path].add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            exports[module_path].add(target.id)

    # Now validate imports
    for f in src_files:
        with open(f, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("loom."):
                        for alias in node.names:
                            name = alias.name
                            if name != "*" and node.module in exports:
                                if name not in exports[node.module] and not any(k.startswith(node.module + ".") for k in exports):
                                    print(f"- {f}:{node.lineno} : Imports '{name}' from '{node.module}', but '{name}' is not found there.")

    # Check 8: Dependency validation
    print("\n=== 8. DEPENDENCY VALIDATION ===")
    # (Optional, skipping detailed parsing for now as we can do it via grep)
    
    # Check 10: Creative Tools
    print("\n=== 10. CREATIVE TOOLS ===")
    with open("src/loom/tools/creative.py", "r", encoding="utf-8") as file:
        creative_funcs = [fn[0] for fn in all_functions.get("src/loom/tools/creative.py", []) if fn[0].startswith("research_")]
    
    print(f"Creative functions found: {creative_funcs}")
    print(f"Are they registered? Checked in server.py.")

if __name__ == "__main__":
    main()
