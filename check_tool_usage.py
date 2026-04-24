import ast
import glob

files = glob.glob("src/loom/**/*.py", recursive=True)
tool_funcs = set()
for f in files:
    content = open(f).read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("tool_"):
                tool_funcs.add(node.name)

# Search for usage of these tool_funcs
used = {t: False for t in tool_funcs}
for f in files:
    content = open(f).read()
    for t in tool_funcs:
        # crude search
        if content.count(t) > (1 if f.endswith(".py") and f"def {t}" in content else 0):
            used[t] = True

for t, is_used in used.items():
    if not is_used:
        print(f"Wrapper {t} is NEVER used!")
