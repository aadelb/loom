"""Module to update server.py with api_fuzzer changes."""

def update_server_py():
    """Apply api_fuzzer updates to server.py"""
    import os

    filepath = os.path.join(os.path.dirname(__file__), 'src/loom/server.py')

    with open(filepath, 'r') as f:
        content = f.read()

    # Update 1: Add api_fuzzer import
    old_import = 'ai_safety_extended,\n    antiforensics,'
    new_import = 'ai_safety_extended,\n    api_fuzzer,\n    antiforensics,'
    content = content.replace(old_import, new_import)

    # Update 2: Add tool registration
    old_reg = 'mcp.tool()(_wrap_tool(security_headers.research_security_headers, "fetch"))\n\n    # Sherlock username OSINT tools'
    new_reg = '''mcp.tool()(_wrap_tool(security_headers.research_security_headers, "fetch"))

    # API fuzzing tools (2 tools for endpoint vulnerability discovery)
    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_api, "fetch"))
    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_report))

    # Sherlock username OSINT tools'''
    content = content.replace(old_reg, new_reg)

    with open(filepath, 'w') as f:
        f.write(content)

    return True

if __name__ == '__main__':
    try:
        update_server_py()
        print("Successfully updated server.py")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
