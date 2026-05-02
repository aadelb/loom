#!/usr/bin/env python3
"""Add api_fuzzer to server.py imports and tool registration."""

with open('src/loom/server.py', 'r') as f:
    lines = f.readlines()

# Find the line with "ai_safety_extended," and insert "api_fuzzer," after it
output = []
found_import = False
found_registration = False

for i, line in enumerate(lines):
    output.append(line)

    # Handle import insertion
    if not found_import and 'ai_safety_extended,' in line:
        output.append('    api_fuzzer,\n')
        found_import = True

    # Handle tool registration insertion - look for security_headers registration
    if (not found_registration and
        'mcp.tool()(_wrap_tool(security_headers.research_security_headers, "fetch"))' in line):
        output.append('\n    # API fuzzing tools (2 tools for endpoint vulnerability discovery)\n')
        output.append('    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_api, "fetch"))\n')
        output.append('    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_report))\n')
        found_registration = True

with open('src/loom/server.py', 'w') as f:
    f.writelines(output)

print("Fixed server.py")
print(f"  - Added import: {found_import}")
print(f"  - Added registration: {found_registration}")
