import sys
from pathlib import Path
import importlib
from traceback import format_exception_only
import re

sys.path.insert(0, str(Path("src").resolve()))

def find_broken_and_missing():
    server_path = Path("src/loom/server.py")
    with open(server_path, "r", encoding="utf-8") as f:
        content = f.read()

    modules_to_check = set()
    # Parse `from loom.tools.X import Y` -> loom.tools.X
    for m in re.findall(r'from\s+(loom\.[a-zA-Z0-9_.]+)\s+import', content):
        modules_to_check.add(m)
    # Parse `import loom.X.Y` -> loom.X.Y
    for m in re.findall(r'import\s+(loom\.[a-zA-Z0-9_.]+)', content):
        modules_to_check.add(m)

    results = []
    for mod_name in sorted(modules_to_check):
        if mod_name == "loom": continue
        
        mod_path = Path("src") / Path(*mod_name.split('.')).with_suffix('.py')
        mod_dir = Path("src") / Path(*mod_name.split('.')) / "__init__.py"
        file_exists = mod_path.exists() or mod_dir.exists()

        if not file_exists:
            results.append({
                'file': str(mod_path),
                'line': 1,
                'tool': mod_name,
                'type': 'MISSING',
                'desc': f"Module {mod_name} imported in server.py but file does not exist",
                'expected': "File should exist."
            })
            continue

        try:
            importlib.import_module(mod_name)
        except Exception as e:
            err_msg = "".join(format_exception_only(type(e), e)).strip()
            results.append({
                'file': str(mod_path) if mod_path.exists() else str(mod_dir),
                'line': 1,
                'tool': mod_name,
                'type': 'BROKEN',
                'desc': f"Failed to import: {err_msg}",
                'expected': "Module should import without errors."
            })

    for r in results:
        print(f"File: {r['file']}:{r['line']}")
        print(f"Tool: {r['tool']}")
        print(f"Type: {r['type']}")
        print(f"Issue: {r['desc']}")
        print(f"Expected: {r['expected']}")
        print("-" * 40)

if __name__ == "__main__":
    find_broken_and_missing()
