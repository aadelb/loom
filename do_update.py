#!/usr/bin/env python3
"""Update server.py to add api_fuzzer."""
import os
os.chdir('/Users/aadel/projects/loom')

with open('src/loom/server.py', 'r') as f:
    content = f.read()

# Replace 1: Add import
old_import = '''    ai_safety_extended,
    antiforensics,'''
new_import = '''    ai_safety_extended,
    api_fuzzer,
    antiforensics,'''
content = content.replace(old_import, new_import)

# Replace 2: Add tool registration after security_headers
old_reg = '''    mcp.tool()(_wrap_tool(security_headers.research_security_headers, "fetch"))

    # Sherlock username OSINT tools
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_lookup, "search"))'''
new_reg = '''    mcp.tool()(_wrap_tool(security_headers.research_security_headers, "fetch"))

    # API fuzzing tools (2 tools for endpoint vulnerability discovery)
    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_api, "fetch"))
    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_report))

    # Sherlock username OSINT tools
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_lookup, "search"))'''
content = content.replace(old_reg, new_reg)

with open('src/loom/server.py', 'w') as f:
    f.write(content)

print("Updated server.py successfully!")
