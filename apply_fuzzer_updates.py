#!/usr/bin/env python3
"""Apply api_fuzzer updates to server.py"""
import sys

# Read entire file
with open('src/loom/server.py', 'r') as f:
    content = f.read()

# Update 1: Add api_fuzzer import
# Find: ai_safety_extended, followed by newline and spaces + antiforensics,
old_import = '    ai_safety_extended,\n    antiforensics,'
new_import = '    ai_safety_extended,\n    api_fuzzer,\n    antiforensics,'

if old_import in content:
    content = content.replace(old_import, new_import)
    print("✓ Added api_fuzzer to imports")
else:
    print("✗ Could not find import location")
    sys.exit(1)

# Update 2: Add api_fuzzer tool registration
# Find the security_headers registration line and insert after it
old_registration = '''    # Sherlock username OSINT tools
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_lookup, "search"))
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_batch, "search"))'''

new_registration = '''    # API fuzzing tools (2 tools for endpoint vulnerability discovery)
    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_api, "fetch"))
    mcp.tool()(_wrap_tool(api_fuzzer.research_fuzz_report))

    # Sherlock username OSINT tools
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_lookup, "search"))
    mcp.tool()(_wrap_tool(sherlock_backend.research_sherlock_batch, "search"))'''

if old_registration in content:
    content = content.replace(old_registration, new_registration)
    print("✓ Added api_fuzzer tool registration")
else:
    print("✗ Could not find registration location")
    sys.exit(1)

# Write back
with open('src/loom/server.py', 'w') as f:
    f.write(content)

print("\nSuccessfully updated src/loom/server.py")
