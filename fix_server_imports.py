#!/usr/bin/env python3
"""Fix server.py imports to include api_fuzzer."""

# Read entire file
with open('src/loom/server.py', 'r') as f:
    lines = f.readlines()

# Find the line with ai_safety_extended and insert api_fuzzer after antiforensics
output_lines = []
for i, line in enumerate(lines):
    output_lines.append(line)
    if 'ai_safety_extended,' in line:
        # Insert api_fuzzer on next line with proper indentation
        output_lines.append('    api_fuzzer,\n')

# Write back
with open('src/loom/server.py', 'w') as f:
    f.writelines(output_lines)

print("Updated server.py")
