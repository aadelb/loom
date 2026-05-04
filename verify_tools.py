import ast
import os

def analyze():
    research_funcs = {}
    stubs = []
    errors = 0
    search_dir = os.path.join(os.getcwd(), 'src', 'loom')
    
    for root, dirs, files in os.walk(search_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    try:
                        tree = ast.parse(content)
                    except SyntaxError:
                        continue
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('research_'):
                            if node.name not in research_funcs:
                                research_funcs[node.name] = []
                            research_funcs[node.name].append(filepath)
                            
                            is_stub = False
                            body = node.body
                            if len(body) == 1:
                                stmt = body[0]
                                if isinstance(stmt, ast.Pass) or isinstance(stmt, ast.Raise):
                                    is_stub = True
                                elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                                    is_stub = True # docstring only
                                elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                                    if "stub" in str(stmt.value.value).lower() or "not implemented" in str(stmt.value.value).lower():
                                        is_stub = True
                            elif len(body) == 2 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                                stmt = body[1]
                                if isinstance(stmt, ast.Pass) or isinstance(stmt, ast.Raise):
                                    is_stub = True
                                elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                                    if "stub" in str(stmt.value.value).lower() or "not implemented" in str(stmt.value.value).lower():
                                        is_stub = True
                            
                            if is_stub:
                                stubs.append((node.name, filepath))
                except Exception as e:
                    errors += 1

    print(f"Total files with errors: {errors}")
    unique_funcs = len(research_funcs)
    total_funcs = sum(len(v) for v in research_funcs.values())
    print(f"Total research_* functions found: {total_funcs}")
    print(f"Unique research_* functions: {unique_funcs}")
    print(f"Total stubs/broken functions: {len(stubs)}")
    for stub, file in stubs:
        print(f"Stub: {stub} in {file}")

if __name__ == '__main__':
    analyze()
