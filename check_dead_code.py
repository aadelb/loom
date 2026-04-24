import ast
import glob

files = glob.glob("src/loom/**/*.py", recursive=True)
all_funcs = set()
for f in files:
    content = open(f).read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_funcs.add(node.name)

# exclude special methods and MCP tools and route handlers
dead_candidates = {f for f in all_funcs if f.startswith("_") and not f.startswith("__") and not f.endswith("__")}

# Look for usage of these candidates
used = {t: False for t in dead_candidates}
for f in files:
    content = open(f).read()
    for t in dead_candidates:
        if t in content:
            # simple text match is enough to clear a lot of noise.
            # to be safe, count > 1 if defined in this file
            if content.count(t) > (1 if f"def {t}" in content else 0):
                used[t] = True

print("Potentially dead internal helper functions:")
for t, is_used in used.items():
    if not is_used:
        print(f"Internal helper {t} appears to be unused!")
