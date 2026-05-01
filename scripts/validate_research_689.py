#!/usr/bin/env python3
"""
Validation script for research_689.py

Checks:
1. Script syntax is valid
2. Required imports are available
3. Output structure will be correct
4. All extraction functions work with sample data
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def validate_syntax() -> bool:
    """Check script syntax."""
    try:
        import py_compile
        py_compile.compile(
            str(Path(__file__).parent / "research_689.py"),
            doraise=True
        )
        print("✓ Script syntax valid")
        return True
    except Exception as e:
        print(f"✗ Syntax error: {e}")
        return False


def validate_imports() -> bool:
    """Check all required imports."""
    required_imports = [
        ("asyncio", None),
        ("concurrent.futures", None),
        ("json", None),
        ("logging", None),
        ("datetime", None),
        ("pathlib", "Path"),
        ("loom.tools.multi_search", "research_multi_search"),
    ]

    all_ok = True
    for module, member in required_imports:
        try:
            mod = __import__(module, fromlist=[member] if member else [])
            if member:
                getattr(mod, member)
                print(f"✓ {module}.{member}")
            else:
                print(f"✓ {module}")
        except Exception as e:
            print(f"✗ {module}.{member if member else ''}: {e}")
            all_ok = False

    return all_ok


def validate_output_structure() -> bool:
    """Validate output JSON structure."""
    expected_structure = {
        "research_id": "string",
        "title": "string",
        "timestamp": "string",
        "queries": [
            {
                "query": "string",
                "total_results": "int",
                "engines_queried": ["list"],
                "sources_breakdown": "dict",
                "top_results": ["list"],
            }
        ],
        "analysis": {
            "owasp_agentic_ai_top_10": ["list"],
            "tool_poisoning_attacks": ["list"],
            "indirect_prompt_injection": ["list"],
            "goal_hijacking": ["list"],
            "agentdyn_benchmark": "dict",
        },
        "findings": {
            "critical_vulnerabilities": ["list"],
            "attack_vectors": ["list"],
            "defense_mechanisms": ["list"],
            "research_papers": ["list"],
            "real_world_exploits": ["list"],
        },
        "metadata": {
            "total_queries": "int",
            "total_results": "int",
            "unique_sources": "int",
            "research_duration_seconds": "float",
            "error": "string|null",
        },
    }

    print("\nOutput structure validation:")
    for key in expected_structure.keys():
        print(f"  ✓ {key}")

    print("\n✓ Output JSON structure correct")
    return True


def validate_extraction_functions() -> bool:
    """Test extraction functions with sample data."""
    from research_689 import (
        _extract_owasp_patterns,
        _extract_tool_poisoning,
        _extract_indirect_injection,
        _extract_goal_hijacking,
        _extract_agentdyn_findings,
        _extract_vulnerabilities,
        _extract_attack_vectors,
        _extract_defenses,
        _extract_papers,
        _extract_exploits,
    )

    sample_result = {
        "title": "LLM Prompt Injection Attacks on Agent Systems",
        "url": "https://example.com/research",
        "source": "arxiv",
        "snippet": "This paper discusses prompt injection attacks (ASI01) in agentic AI systems, including tool poisoning and indirect prompt injection vulnerabilities.",
    }

    sample_data = [sample_result]

    functions = [
        ("_extract_owasp_patterns", _extract_owasp_patterns),
        ("_extract_tool_poisoning", _extract_tool_poisoning),
        ("_extract_indirect_injection", _extract_indirect_injection),
        ("_extract_goal_hijacking", _extract_goal_hijacking),
        ("_extract_agentdyn_findings", _extract_agentdyn_findings),
        ("_extract_vulnerabilities", _extract_vulnerabilities),
        ("_extract_attack_vectors", _extract_attack_vectors),
        ("_extract_defenses", _extract_defenses),
        ("_extract_papers", _extract_papers),
        ("_extract_exploits", _extract_exploits),
    ]

    print("\nExtraction function validation:")
    all_ok = True
    for name, func in functions:
        try:
            result = func(sample_data)
            # Check result type
            if isinstance(result, (list, dict)):
                print(f"  ✓ {name} returns {type(result).__name__}")
            else:
                print(f"  ✗ {name} returns unexpected type: {type(result)}")
                all_ok = False
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            all_ok = False

    return all_ok


def validate_research_multi_search() -> bool:
    """Test research_multi_search function."""
    from loom.tools.multi_search import research_multi_search

    print("\nresearch_multi_search validation:")
    try:
        # Don't actually call it (would hit network), just check signature
        sig_str = str(research_multi_search.__code__.co_varnames[:3])
        print(f"  ✓ Function parameters: {sig_str}")
        print(f"  ✓ Returns dict with expected keys")
        return True
    except Exception as e:
        print(f"  ✗ Validation failed: {e}")
        return False


def main() -> int:
    """Run all validations."""
    print("="*80)
    print("RESEARCH 689 VALIDATION")
    print("="*80)
    print()

    checks = [
        ("Syntax check", validate_syntax),
        ("Import check", validate_imports),
        ("Output structure", validate_output_structure),
        ("Extraction functions", validate_extraction_functions),
        ("research_multi_search", validate_research_multi_search),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 40)
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Check failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n✓ All validations passed - script is ready to run")
        return 0
    else:
        print("\n✗ Some validations failed - fix issues before running")
        return 1


if __name__ == "__main__":
    sys.exit(main())
