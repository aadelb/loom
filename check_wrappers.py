import ast
import glob

files = glob.glob("src/loom/**/*.py", recursive=True)
funcs = set()
for f in files:
    content = open(f).read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            funcs.add(node.name)

tools = {f for f in funcs if f.startswith("tool_")}
research = {f for f in funcs if f.startswith("research_")}

print("Tools with wrapper but no research_:")
for t in tools:
    r_name = t.replace("tool_", "research_")
    if r_name not in research:
        print(t)

print("Wrappers missing for research functions? Usually research_ functions are wrapped in server.py, but some are wrapped explicitly.")
for t in tools:
    print(f"Wrapper: {t}")
