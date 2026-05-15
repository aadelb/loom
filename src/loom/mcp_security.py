"""MCP tool poisoning and injection vulnerability scanner.

This module tests Loom's own MCP tools for security issues including:
- Hidden Unicode characters (zero-width, RTL overrides) in descriptions
- Prompt injection keywords in tool descriptions and parameter defaults
- Tool description length anomalies (suspiciously long descriptions)
- Cross-tool data flow risks (tool A output → tool B input)
- Parameter injection via default values
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import UTC, datetime
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("loom.mcp_security")


@dataclass
class SecurityVulnerability:
    """Represents a single security vulnerability found."""

    tool_name: str
    vulnerability_type: str  # injection, unicode, anomaly, cross_tool, parameter
    severity: str  # critical, high, medium, low
    description: str
    affected_field: str | None = None
    evidence: str | None = None
    recommendation: str | None = None


@dataclass
class SecurityScanResult:
    """Complete security scan results."""

    total_tools_scanned: int
    vulnerabilities_found: list[SecurityVulnerability] = field(default_factory=list)
    severity_breakdown: dict[str, int] = field(default_factory=dict)
    per_tool_results: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_tools_scanned": self.total_tools_scanned,
            "vulnerabilities_found": len(self.vulnerabilities_found),
            "severity_breakdown": self.severity_breakdown,
            "per_tool_results": self.per_tool_results,
            "vulnerabilities": [
                {
                    "tool_name": v.tool_name,
                    "type": v.vulnerability_type,
                    "severity": v.severity,
                    "description": v.description,
                    "field": v.affected_field,
                    "evidence": v.evidence,
                    "recommendation": v.recommendation,
                }
                for v in self.vulnerabilities_found
            ],
        }


class MCPSecurityTester:
    """Test Loom's own MCP tools for tool poisoning and injection vulnerabilities."""

    # Patterns that indicate prompt injection attempts
    INJECTION_PATTERNS = [
        "ignore previous instructions",
        "system prompt override",
        "you are now",
        "disregard all",
        "forget about",
        "pretend that",
        "<|im_start|>system",
        "\\n\\nHuman:",
        "### Instruction:",
        "### System:",
        "### Assistant:",
        "[SYSTEM]",
        "[ADMIN]",
        "admin mode",
        "developer mode",
        "debug mode",
        "bypass",
        "override",
        "jailbreak",
        "exploit",
        "vulnerability",
        "execute code",
        "run command",
        "shell",
        "eval",
        "exec",
        "subprocess",
        "os.system",
        "import os",
        "from os",
        "__import__",
        ".__code__",
        "globals()",
        "__builtins__",
    ]

    # Unicode characters that are commonly used for obfuscation
    UNICODE_OBFUSCATION_PATTERNS = [
        "​",  # Zero-width space
        "‌",  # Zero-width non-joiner
        "‍",  # Zero-width joiner
        "﻿",  # Zero-width no-break space
        "‮",  # Right-to-left override
        "‭",  # Left-to-right override
        "؜",  # Arabic letter mark
        "⁦",  # Left-to-right isolate
        "⁧",  # Right-to-left isolate
        "⁨",  # First strong isolate
        "⁩",  # Pop directional isolate
    ]

    def __init__(self) -> None:
        """Initialize the security tester."""
        self.scan_result = SecurityScanResult(total_tools_scanned=0)

    def scan_tool_descriptions(self, tools: dict[str, Any]) -> dict[str, Any]:
        """Scan all tool descriptions for hidden injection payloads.

        Checks for:
        - Hidden Unicode characters (zero-width, RTL overrides)
        - Injection keywords
        - Suspiciously long descriptions (> 1000 chars)

        Args:
            tools: Dictionary of tools from MCP server

        Returns:
            Dictionary with scan results per tool
        """
        results = {}

        for tool_name, tool_info in tools.items():
            results[tool_name] = {"issues": []}

            description = tool_info.get("description", "")
            if not description:
                continue

            # Check for hidden Unicode
            unicode_issues = self._detect_hidden_unicode(description)
            if unicode_issues:
                for issue in unicode_issues:
                    vuln = SecurityVulnerability(
                        tool_name=tool_name,
                        vulnerability_type="unicode",
                        severity="high",
                        description="Hidden Unicode character detected in tool description",
                        affected_field="description",
                        evidence=issue["char"],
                        recommendation="Remove hidden Unicode characters from descriptions",
                    )
                    self.scan_result.vulnerabilities_found.append(vuln)
                    results[tool_name]["issues"].append(
                        {
                            "type": "unicode",
                            "severity": "high",
                            "details": issue,
                        }
                    )

            # Check for injection keywords
            injection_issues = self._detect_injection_keywords(description)
            if injection_issues:
                for keyword in injection_issues:
                    vuln = SecurityVulnerability(
                        tool_name=tool_name,
                        vulnerability_type="injection",
                        severity="critical",
                        description=f"Injection keyword '{keyword}' found in tool description",
                        affected_field="description",
                        evidence=keyword,
                        recommendation="Remove injection keywords from all tool descriptions",
                    )
                    self.scan_result.vulnerabilities_found.append(vuln)
                    results[tool_name]["issues"].append(
                        {
                            "type": "injection",
                            "severity": "critical",
                            "keyword": keyword,
                        }
                    )

            # Check for anomalies (suspiciously long descriptions)
            if len(description) > 1000:
                vuln = SecurityVulnerability(
                    tool_name=tool_name,
                    vulnerability_type="anomaly",
                    severity="medium",
                    description="Tool description is suspiciously long (>1000 chars)",
                    affected_field="description",
                    evidence=f"{len(description)} chars",
                    recommendation="Keep descriptions concise and clear; review for hidden content",
                )
                self.scan_result.vulnerabilities_found.append(vuln)
                results[tool_name]["issues"].append(
                    {
                        "type": "anomaly",
                        "severity": "medium",
                        "length_chars": len(description),
                    }
                )

        return results

    def scan_tool_parameters(self, tools: dict[str, Any]) -> dict[str, Any]:
        """Check parameter descriptions and defaults for injection vectors.

        Args:
            tools: Dictionary of tools from MCP server

        Returns:
            Dictionary with scan results per tool
        """
        results = {}

        for tool_name, tool_info in tools.items():
            results[tool_name] = {"parameter_issues": []}

            input_schema = tool_info.get("inputSchema", {})
            properties = input_schema.get("properties", {})

            for param_name, param_info in properties.items():
                param_desc = param_info.get("description", "")
                param_default = param_info.get("default")

                # Check parameter description for injection
                if param_desc:
                    injection_issues = self._detect_injection_keywords(param_desc)
                    if injection_issues:
                        for keyword in injection_issues:
                            vuln = SecurityVulnerability(
                                tool_name=tool_name,
                                vulnerability_type="injection",
                                severity="high",
                                description=f"Injection keyword '{keyword}' in parameter description",
                                affected_field=f"parameter.{param_name}.description",
                                evidence=keyword,
                                recommendation="Audit parameter descriptions for malicious content",
                            )
                            self.scan_result.vulnerabilities_found.append(vuln)
                            results[tool_name]["parameter_issues"].append(
                                {
                                    "parameter": param_name,
                                    "type": "injection_in_description",
                                    "keyword": keyword,
                                    "severity": "high",
                                }
                            )

                    # Check for hidden Unicode in parameter description
                    unicode_issues = self._detect_hidden_unicode(param_desc)
                    if unicode_issues:
                        for issue in unicode_issues:
                            vuln = SecurityVulnerability(
                                tool_name=tool_name,
                                vulnerability_type="unicode",
                                severity="high",
                                description=f"Hidden Unicode in parameter '{param_name}' description",
                                affected_field=f"parameter.{param_name}.description",
                                evidence=issue["char"],
                                recommendation="Sanitize parameter descriptions",
                            )
                            self.scan_result.vulnerabilities_found.append(vuln)
                            results[tool_name]["parameter_issues"].append(
                                {
                                    "parameter": param_name,
                                    "type": "unicode",
                                    "details": issue,
                                    "severity": "high",
                                }
                            )

                # Check parameter default value for injection
                if param_default is not None:
                    default_str = str(param_default)
                    if len(default_str) > 200:  # Suspiciously long default
                        vuln = SecurityVulnerability(
                            tool_name=tool_name,
                            vulnerability_type="anomaly",
                            severity="medium",
                            description=f"Parameter '{param_name}' has suspiciously long default",
                            affected_field=f"parameter.{param_name}.default",
                            evidence=f"{len(default_str)} chars",
                            recommendation="Review parameter defaults for hidden content",
                        )
                        self.scan_result.vulnerabilities_found.append(vuln)
                        results[tool_name]["parameter_issues"].append(
                            {
                                "parameter": param_name,
                                "type": "long_default",
                                "length": len(default_str),
                                "severity": "medium",
                            }
                        )

                    injection_issues = self._detect_injection_keywords(default_str)
                    if injection_issues:
                        for keyword in injection_issues:
                            vuln = SecurityVulnerability(
                                tool_name=tool_name,
                                vulnerability_type="injection",
                                severity="critical",
                                description=f"Injection keyword '{keyword}' in parameter default",
                                affected_field=f"parameter.{param_name}.default",
                                evidence=keyword,
                                recommendation="Sanitize all parameter default values",
                            )
                            self.scan_result.vulnerabilities_found.append(vuln)
                            results[tool_name]["parameter_issues"].append(
                                {
                                    "parameter": param_name,
                                    "type": "injection_in_default",
                                    "keyword": keyword,
                                    "severity": "critical",
                                }
                            )

        return results

    def test_cross_tool_hijacking(self, tools: dict[str, Any]) -> dict[str, Any]:
        """Check if one tool's output could hijack another tool's behavior.

        This checks for:
        - Unvalidated parameter passing between tools
        - Tools that accept arbitrary strings that could manipulate other tools
        - Parameter names that suggest unsafe chaining

        Args:
            tools: Dictionary of tools from MCP server

        Returns:
            Dictionary with cross-tool risk assessment
        """
        results: dict[str, Any] = {"cross_tool_risks": []}

        # Collect all parameter names and their types
        all_parameters: dict[str, set[str]] = {}
        for tool_name, tool_info in tools.items():
            input_schema = tool_info.get("inputSchema", {})
            properties = input_schema.get("properties", {})
            for param_name in properties:
                if param_name not in all_parameters:
                    all_parameters[param_name] = set()
                all_parameters[param_name].add(tool_name)

        # Check for suspicious patterns
        suspicious_param_names = [
            "command",
            "code",
            "script",
            "eval",
            "query",
            "prompt",
            "payload",
            "data",
            "input",
            "args",
            "kwargs",
        ]

        for tool_name, tool_info in tools.items():
            input_schema = tool_info.get("inputSchema", {})
            properties = input_schema.get("properties", {})

            for param_name, param_info in properties.items():
                # Check if parameter is shared across many tools (could be hijack vector)
                if param_name in all_parameters:
                    tool_count = len(all_parameters[param_name])
                    if tool_count >= 5:  # Used by 5+ tools
                        # Check if it accepts arbitrary strings
                        param_type = param_info.get("type")
                        if param_type in ("string", "object") and param_name in suspicious_param_names:
                            risk = {
                                "source_tool": tool_name,
                                "parameter": param_name,
                                "risk_level": "high",
                                "reason": f"Parameter used by {tool_count} tools with type '{param_type}'",
                                "tools_affected": list(all_parameters[param_name]),
                            }
                            results["cross_tool_risks"].append(risk)

                            vuln = SecurityVulnerability(
                                tool_name=tool_name,
                                vulnerability_type="cross_tool",
                                severity="medium",
                                description=f"Parameter '{param_name}' shared across {tool_count} tools",
                                affected_field=param_name,
                                evidence=f"Used by tools: {', '.join(sorted(all_parameters[param_name]))}",
                                recommendation="Validate cross-tool data flows; use strict parameter validation",
                            )
                            self.scan_result.vulnerabilities_found.append(vuln)

        return results

    def _detect_hidden_unicode(self, text: str) -> list[dict[str, Any]]:
        """Detect hidden Unicode characters in text.

        Args:
            text: Text to scan

        Returns:
            List of detected Unicode issues
        """
        issues = []

        for i, char in enumerate(text):
            # Check for zero-width and directional override characters
            if char in self.UNICODE_OBFUSCATION_PATTERNS:
                issues.append(
                    {
                        "position": i,
                        "char": repr(char),
                        "unicode_name": unicodedata.name(char, "UNKNOWN"),
                        "context": text[max(0, i - 10) : min(len(text), i + 10)],
                    }
                )

            # Check for suspicious Unicode categories
            category = unicodedata.category(char)
            if category.startswith("C"):  # Control characters
                if char not in "\n\r\t":  # Allow common whitespace
                    issues.append(
                        {
                            "position": i,
                            "char": repr(char),
                            "unicode_name": unicodedata.name(char, "UNKNOWN"),
                            "category": category,
                            "context": text[max(0, i - 10) : min(len(text), i + 10)],
                        }
                    )

        return issues

    def _detect_injection_keywords(self, text: str) -> list[str]:
        """Detect potential injection keywords in text.

        Args:
            text: Text to scan

        Returns:
            List of detected injection keywords
        """
        detected = []
        text_lower = text.lower()

        for pattern in self.INJECTION_PATTERNS:
            # Use word boundary detection for whole phrases
            if len(pattern) > 2:
                # Escape special regex characters
                escaped = re.escape(pattern)
                if re.search(rf"\b{escaped}\b", text_lower):
                    detected.append(pattern)
            else:
                # For short patterns, use simple substring match
                if pattern in text_lower:
                    detected.append(pattern)

        return detected

    def generate_security_report(self, scan_results: SecurityScanResult | None = None) -> str:
        """Generate markdown security report from scan results.

        Args:
            scan_results: SecurityScanResult object (uses self.scan_result if None)

        Returns:
            Markdown formatted security report
        """
        if scan_results is None:
            scan_results = self.scan_result

        # Calculate severity breakdown
        severity_count: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in scan_results.vulnerabilities_found:
            severity_count[vuln.severity] += 1

        report = [
            "# MCP Tool Security Scan Report\n",
            f"**Scan Date:** {datetime.now(UTC).isoformat()}\n",
            f"**Total Tools Scanned:** {scan_results.total_tools_scanned}\n",
            f"**Vulnerabilities Found:** {len(scan_results.vulnerabilities_found)}\n",
            "\n## Severity Breakdown\n",
            f"- **Critical:** {severity_count['critical']}\n",
            f"- **High:** {severity_count['high']}\n",
            f"- **Medium:** {severity_count['medium']}\n",
            f"- **Low:** {severity_count['low']}\n",
        ]

        if scan_results.vulnerabilities_found:
            report.append("\n## Vulnerabilities\n")
            for vuln in sorted(
                scan_results.vulnerabilities_found,
                key=lambda v: {"critical": 0, "high": 1, "medium": 2, "low": 3}[v.severity],
            ):
                report.append(
                    f"\n### [{vuln.severity.upper()}] {vuln.tool_name} - {vuln.vulnerability_type}\n"
                )
                report.append(f"**Description:** {vuln.description}\n")
                if vuln.affected_field:
                    report.append(f"**Field:** {vuln.affected_field}\n")
                if vuln.evidence:
                    report.append(f"**Evidence:** {vuln.evidence}\n")
                if vuln.recommendation:
                    report.append(f"**Recommendation:** {vuln.recommendation}\n")
        else:
            report.append("\n## Result\n")
            report.append("No vulnerabilities detected.\n")

        report.append("\n## Recommendations\n")
        report.append(
            "1. **Review all tool descriptions:** Ensure descriptions are concise and free of "
            "injection keywords\n"
        )
        report.append(
            "2. **Validate parameter inputs:** Use strict parameter validation for all tools\n"
        )
        report.append(
            "3. **Sanitize unicode:** Remove all hidden Unicode characters from metadata\n"
        )
        report.append("4. **Regular scanning:** Run this security test regularly (e.g., in CI/CD)\n")
        report.append("5. **Cross-tool validation:** Implement strict boundaries between tools\n")

        return "".join(report)


def research_mcp_security_scan(tool_specs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Scan Loom's MCP tools for poisoning and injection vulnerabilities.

    This is the main entry point for the research_mcp_security_scan MCP tool.

    Args:
        tool_specs: Optional dictionary of tool specifications to scan.
                   If None, will scan default Loom tools.

    Returns:
        Dictionary with scan results including vulnerabilities, severity breakdown,
        and per-tool findings.
    """
    tester = MCPSecurityTester()

    # If no tools provided, use a default set
    if tool_specs is None:
        tool_specs = _get_default_loom_tools()

    tester.scan_result.total_tools_scanned = len(tool_specs)

    # Run all scans
    description_results = tester.scan_tool_descriptions(tool_specs)
    parameter_results = tester.scan_tool_parameters(tool_specs)
    cross_tool_results = tester.test_cross_tool_hijacking(tool_specs)

    # Calculate severity breakdown
    severity_count: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for vuln in tester.scan_result.vulnerabilities_found:
        severity_count[vuln.severity] += 1

    tester.scan_result.severity_breakdown = severity_count

    # Aggregate per-tool results
    for tool_name in tool_specs:
        tester.scan_result.per_tool_results[tool_name] = {
            "description_issues": description_results.get(tool_name, {}).get("issues", []),
            "parameter_issues": parameter_results.get(tool_name, {}).get("parameter_issues", []),
        }

    return tester.scan_result.to_dict()


def _get_default_loom_tools() -> dict[str, Any]:
    """Get default Loom tool specifications for scanning.

    Returns:
        Dictionary mapping tool names to specifications.
    """
    # This is a minimal default set for testing
    # In production, this would be populated from the actual MCP server
    return {
        "research_fetch": {
            "description": "Fetch a single URL with optional Cloudflare bypass and JavaScript execution",
            "inputSchema": {
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "mode": {
                        "type": "string",
                        "description": "Fetch mode: http, stealthy, or dynamic",
                        "default": "stealthy",
                    },
                }
            },
        },
        "research_spider": {
            "description": "Fetch multiple URLs concurrently with deduplication and ordering",
            "inputSchema": {
                "properties": {
                    "urls": {"type": "array", "description": "URLs to fetch"},
                    "concurrency": {"type": "integer", "default": 5},
                }
            },
        },
        "research_search": {
            "description": "Search across multiple providers (exa, tavily, brave, etc)",
            "inputSchema": {
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                }
            },
        },
    }
