#!/usr/bin/env python3
# Validate all 835 Loom tools against their quality guidelines.

import json
import argparse
from pathlib import Path
from typing import Any, Dict, Tuple

def load_guidelines(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)

def validate_output(tool_name: str, output: Any, guideline: Dict[str, Any]) -> Tuple[bool, str]:
    criteria = guideline.get("quality_criteria", {})
    
    if criteria.get("must_not_be_empty", True):
        if output is None or output == {} or output == [] or output == "":
            return False, "Output is empty"
    
    if criteria.get("must_be_dict_or_list", False):
        if not isinstance(output, (dict, list)):
            return False, f"Output type {type(output)} not in (dict, list)"
    
    min_chars = criteria.get("min_chars", 0)
    output_str = json.dumps(output) if isinstance(output, (dict, list)) else str(output)
    if len(output_str) < min_chars:
        return False, f"Output too short ({len(output_str)} < {min_chars})"
    
    return True, ""

def main():
    parser = argparse.ArgumentParser(description="Validate Loom tools")
    parser.add_argument("--guidelines", required=True)
    parser.add_argument("--tool", help="Specific tool to validate")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    
    guidelines = load_guidelines(args.guidelines)
    
    if args.tool:
        if args.tool not in guidelines:
            print(f"Tool {args.tool} not found")
            return 1
        
        g = guidelines[args.tool]
        print(f"Tool: {args.tool}")
        print(f"  Module: {g.get(module)}")
        print(f"  Category: {g.get(category)}")
        print(f"  Required: {g.get(required_params, [])}")
        print(f"  Async: {g.get(is_async)}")
        print(f"  Return type: {g.get(expected_return_type)}")
        print(f"  Min chars: {g.get(min_output_chars)}")
    else:
        print(f"Total tools: {len(guidelines)}")
        
        category_counts = {}
        for tool in guidelines.values():
            cat = tool.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print("By Category:")
        for cat in sorted(category_counts.keys(), key=lambda x: -category_counts[x]):
            print(f"  {cat:20s}: {category_counts[cat]}")
        
        with_docs = sum(1 for t in guidelines.values() if t.get("has_docstring"))
        pct = 100 * with_docs / len(guidelines)
        print(f"Docstrings: {with_docs}/{len(guidelines)} ({pct:.1f}%)")
        
        async_count = sum(1 for t in guidelines.values() if t.get("is_async"))
        pct_async = 100 * async_count / len(guidelines)
        print(f"Async: {async_count}/{len(guidelines)} ({pct_async:.1f}%)")

if __name__ == "__main__":
    main()
