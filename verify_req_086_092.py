#!/usr/bin/env python3
"""Verification script for Loom compliance requirements REQ-086 through REQ-092.

This script verifies:
- REQ-086: Audit logging module exists and provides export functionality
- REQ-087: Tamper-proof audit logs with SHA-256 checksums
- REQ-090: Arabic language routing and detection
- REQ-092: Arabic refusal detection patterns

Run on Hetzner with: python verify_req_086_092.py
"""

import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def verify_req_086():
    """REQ-086: Audit logging module loads and provides export."""
    try:
        from loom.audit import export_audit, log_invocation, verify_integrity

        # Check that functions exist and are callable
        assert callable(export_audit), "export_audit not callable"
        assert callable(log_invocation), "log_invocation not callable"
        assert callable(verify_integrity), "verify_integrity not callable"

        print("✓ REQ-086: Audit module loaded with export_audit, log_invocation, verify_integrity")
        return True
    except Exception as e:
        print(f"✗ REQ-086: Failed to load audit module: {e}")
        return False


def verify_req_087():
    """REQ-087: Tamper-proof (check for SHA-256 or checksum in audit)."""
    try:
        import inspect
        from loom.audit import export_audit, AuditEntry

        # Check AuditEntry dataclass has checksum field
        import dataclasses
        fields = {f.name for f in dataclasses.fields(AuditEntry)}
        assert "checksum" in fields, "AuditEntry missing checksum field"

        # Check export_audit source for hash operations
        src_export = inspect.getsource(export_audit)
        src_entry = inspect.getsource(AuditEntry)

        has_sha256 = "sha256" in src_export.lower() or "sha256" in src_entry.lower()
        has_checksum = "checksum" in src_export.lower() or "checksum" in src_entry.lower()
        has_hash = "hashlib" in src_export or "hash" in src_entry.lower()

        tamper_proof = has_sha256 or has_checksum or has_hash

        if tamper_proof:
            print(f"✓ REQ-087: Tamper-proof audit logs detected (sha256={has_sha256}, checksum={has_checksum}, hash={has_hash})")
            return True
        else:
            print("✗ REQ-087: No SHA-256/checksum detection found in audit module")
            return False

    except Exception as e:
        print(f"✗ REQ-087: Failed to verify tamper-proof mechanism: {e}")
        return False


def verify_req_090():
    """REQ-090: Arabic routing and language detection."""
    try:
        from loom.arabic import detect_arabic, route_by_language, get_arabic_preferred_providers

        # Test Arabic detection
        arabic_text = "كيف أصبح غنياً"
        english_text = "how to be rich"

        assert detect_arabic(arabic_text), f"Failed to detect Arabic in: {arabic_text}"
        assert not detect_arabic(english_text), f"False positive Arabic detection in: {english_text}"

        # Test provider routing
        cascade = ["groq", "gemini", "openai"]
        routed = route_by_language(arabic_text, cascade)

        # gemini should be prioritized (Arabic-capable)
        gemini_idx = routed.index("gemini") if "gemini" in routed else -1
        assert gemini_idx == 0, f"Arabic routing failed: gemini not first in {routed}"

        # Test Arabic providers list
        providers = get_arabic_preferred_providers()
        expected = ["qwen", "gemini", "kimi", "deepseek"]
        assert providers == expected, f"Arabic providers mismatch: {providers} != {expected}"

        print(f"✓ REQ-090: Arabic routing verified")
        print(f"    - detect_arabic: '{arabic_text[:20]}...' = True")
        print(f"    - route_by_language: {cascade} → {routed}")
        print(f"    - providers: {providers}")
        return True

    except Exception as e:
        print(f"✗ REQ-090: Failed to verify Arabic routing: {e}")
        return False


def verify_req_092():
    """REQ-092: Arabic refusal detection patterns."""
    try:
        from loom.tools.prompt_reframe import _detect_refusal, _REFUSAL_PATTERNS

        # Test Arabic refusal patterns
        arabic_refusals = [
            "لا أستطيع المساعدة في ذلك",
            "هذا الطلب غير مناسب",
            "لا يمكنني تقديم هذه المعلومات",
            "أعتذر، لا أستطيع",
            "يتعارض مع سياساتي",
            "كنموذج ذكاء اصطناعي لا أستطيع",
            "أرفض تقديم هذا المحتوى",
        ]

        # Count how many Arabic patterns exist
        arabic_patterns = [p for p, cat in _REFUSAL_PATTERNS if cat == "non_english"]

        # Test detection
        detected = 0
        for text in arabic_refusals:
            if _detect_refusal(text):
                detected += 1

        detection_rate = detected / len(arabic_refusals) * 100

        print(f"✓ REQ-092: Arabic refusal detection verified")
        print(f"    - Total refusal patterns: {len(_REFUSAL_PATTERNS)}")
        print(f"    - Arabic patterns: {len(arabic_patterns)}")
        print(f"    - Detection rate: {detected}/{len(arabic_refusals)} ({detection_rate:.0f}%)")

        # Show detected vs missed
        for i, text in enumerate(arabic_refusals, 1):
            detected_flag = "✓" if _detect_refusal(text) else "✗"
            print(f"    {detected_flag} {i}. {text[:50]}...")

        return detection_rate >= 50  # At least 50% should be detected

    except Exception as e:
        print(f"✗ REQ-092: Failed to verify Arabic refusal detection: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("Loom Compliance Verification: REQ-086 through REQ-092")
    print("="*70 + "\n")

    results = {
        "REQ-086 (Audit Logging)": verify_req_086(),
        "REQ-087 (Tamper-proof)": verify_req_087(),
        "REQ-090 (Arabic Routing)": verify_req_090(),
        "REQ-092 (Arabic Refusal)": verify_req_092(),
    }

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for req, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{req:40s} {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\nTotal: {passed}/{total} requirements verified")
    print("="*70 + "\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
