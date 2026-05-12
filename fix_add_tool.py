"""Fix _add_tool in loom-legal __init__.py to preserve function signatures."""
import sys

path = "/opt/research-toolbox/loom-legal/src/loom_legal/__init__.py"
with open(path) as f:
    content = f.read()

old_wrapper = '''    def decorator(func):
        @mcp.tool(name=name)
        @functools.wraps(func)
        async def wrapper(**kwargs):
            try:
                result = await func(**kwargs)
                text = json.dumps(result, indent=2, ensure_ascii=False)
                return [TextContent(type="text", text=text)]
            except Exception as exc:
                text = json.dumps(
                    {"error": str(exc), "tool": name},
                    indent=2,
                    ensure_ascii=False,
                )
                return [TextContent(type="text", text=text)]

        return wrapper

    return decorator'''

new_wrapper = '''    def decorator(func):
        mcp.tool(name=name)(func)
        return func
    return decorator'''

if old_wrapper in content:
    content = content.replace(old_wrapper, new_wrapper)
    with open(path, "w") as f:
        f.write(content)
    print("FIXED: _add_tool now registers tools directly without kwargs wrapper")
else:
    print("Exact pattern not found. Checking for wrapper...")
    if "async def wrapper(**kwargs):" in content:
        print("Found wrapper pattern but whitespace differs")
    else:
        print("No wrapper pattern found at all")
