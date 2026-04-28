"""Test that documentation matches actual tool registration.

Runs the verify_completeness.py script as part of pytest to ensure
all registered tools are properly documented in:
- docs/tools-reference.md
- docs/help.md
- CLAUDE.md
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_doc_completeness() -> None:
    """Verify that docs match the list of registered tools.

    This test runs the scripts/verify_completeness.py script which compares:
    - The actual list of registered tools from create_app()
    - The claimed count in docs/tools-reference.md
    - The claimed count in docs/help.md
    - The claimed count in CLAUDE.md
    """
    root_dir = Path(__file__).resolve().parent.parent
    script_path = root_dir / "scripts" / "verify_completeness.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(root_dir),
        timeout=30,
    )

    # Print output for visibility in test results
    print("\n" + result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    assert result.returncode == 0, (
        f"Doc completeness check failed with exit code {result.returncode}:\n"
        f"{result.stdout}\n{result.stderr}"
    )
