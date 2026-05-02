#!/usr/bin/env python3
"""Add api_fuzzer import to server.py"""
import re

with open('src/loom/server.py', 'r') as f:
    content = f.read()

# Add api_fuzzer after ai_safety_extended, before antiforensics
pattern = r'(    ai_safety_extended,)\n(    antiforensics,)'
replacement = r'\1\n    api_fuzzer,\n\2'

new_content = re.sub(pattern, replacement, content)

if new_content != content:
    with open('src/loom/server.py', 'w') as f:
        f.write(new_content)
    print("Successfully updated server.py with api_fuzzer import")
else:
    print("ERROR: Could not find pattern to update")
