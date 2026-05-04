import os
import sys
import inspect
import ast

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from loom.server import create_app

app = create_app()

tools_dict = {}
if hasattr(app, '_tool_manager') and hasattr(app._tool_manager, '_tools'):
    tools_dict = app._tool_manager._tools
elif hasattr(app, 'tools'):
    tools_dict = app.tools

stubs = []
for tool_name, tool_obj in tools_dict.items():
    # In fastmcp, tool_obj might be a Tool instance, we need the original function
    func = getattr(tool_obj, 'fn', getattr(tool_obj, 'function', getattr(tool_obj, 'handler', None)))
    if func is None and callable(tool_obj):
        func = tool_obj
    
    # Try to unwrap if it's wrapped by _wrap_tool
    while hasattr(func, '__wrapped__'):
        func = func.__wrapped__
        
    try:
        source = inspect.getsource(func)
        tree = ast.parse(source)
        is_stub = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if len(body) == 1:
                    stmt = body[0]
                    if isinstance(stmt, ast.Pass) or isinstance(stmt, ast.Raise):
                        is_stub = True
                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        is_stub = True
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
                break # only check the top-level function in the source
        if is_stub:
            stubs.append(tool_name)
    except Exception as e:
        pass # couldn't get source or parse

print(f"Tool count: {len(tools_dict)}")
print(f"Broken/Stub tools: {len(stubs)}")
for stub in stubs:
    print(f"Stub: {stub}")
