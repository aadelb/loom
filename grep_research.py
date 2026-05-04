import os

count = 0
files_with_research = []
for root, dirs, files in os.walk('.'):
    if any(ignore in root for ignore in ['.git', 'venv', '.venv', '__pycache__', 'node_modules']):
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.lstrip().startswith('def research_'):
                            count += 1
                            if filepath not in files_with_research:
                                files_with_research.append(filepath)
            except Exception:
                pass

print(f"Total def research_ lines: {count}")
print(f"Total files containing them: {len(files_with_research)}")
