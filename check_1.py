import ast, glob, re
registered = set()
server = open("src/loom/server.py").read()
for match in re.findall(r'mcp\.tool\(\)\s*\(\s*(?:[\w_]+\.)?([\w_]+)\s*\)', server):
    registered.add(match)
for match in re.findall(r'def\s+(research_[a-zA-Z0-9_]+)', server):
    registered.add(match)

# Add creative tools dynamically registered:
creative = open("src/loom/tools/creative.py").read()
for match in re.findall(r'def\s+(research_[a-zA-Z0-9_]+)', creative):
    registered.add(match)

# Wait, let's just print all `research_`, `search_`, `find_` that aren't in registered
all_funcs = []
for f in glob.glob("src/loom/**/*.py", recursive=True):
    content = open(f).read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if name.startswith("research_") or name.startswith("search_") or name.startswith("find_"):
                if name not in registered:
                    print(f"{f}:{node.lineno} - {name}")
