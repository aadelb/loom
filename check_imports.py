import sys
import os

sys.path.insert(0, os.path.abspath('src'))

broken = []
for root, dirs, files in os.walk('src/loom'):
    for file in files:
        if file.endswith('.py') and file != '__main__.py':
            mod_path = os.path.relpath(os.path.join(root, file), 'src').replace('/', '.')[:-3]
            try:
                __import__(mod_path)
            except Exception as e:
                broken.append((mod_path, str(e)))

for p, err in broken:
    print(f"BROKEN: {p} -> {err}")

