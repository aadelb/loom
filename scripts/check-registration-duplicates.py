#!/usr/bin/env python3
"""Check for duplicate tool registrations across registration modules."""
import subprocess
import sys
from pathlib import Path

def main():
    # Find all registration files
    reg_dir = Path(__file__).parent.parent / "src/loom/registrations"
    if not reg_dir.exists():
        print(f"Error: Registration directory not found: {reg_dir}")
        sys.exit(1)
    
    # Extract all tool names
    all_tools = []
    for py_file in sorted(reg_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        
        try:
            result = subprocess.run(
                ["grep", "-hoE", r"from loom\.tools\.[a-z_0-9]+ import [a-z_0-9]+", str(py_file)],
                capture_output=True,
                text=True,
            )
            
            if result.stdout:
                tools = [line.split()[-1] for line in result.stdout.strip().split('\n') if line]
                all_tools.extend(tools)
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
            sys.exit(1)
    
    # Check for duplicates
    seen = {}
    duplicates = {}
    
    for tool in all_tools:
        if tool in seen:
            if tool not in duplicates:
                duplicates[tool] = 1
            duplicates[tool] += 1
        else:
            seen[tool] = 1
    
    # Report results
    total_registrations = len(all_tools)
    unique_tools = len(seen)
    
    print(f"Total registrations: {total_registrations}")
    print(f"Unique tools: {unique_tools}")
    
    if duplicates:
        print(f"\n✗ DUPLICATES FOUND ({len(duplicates)}):")
        for tool, count in sorted(duplicates.items()):
            print(f"  - {tool}: registered {count} times")
        return 1
    else:
        print("\n✓ NO DUPLICATES - Clean registration system")
        return 0

if __name__ == "__main__":
    sys.exit(main())
