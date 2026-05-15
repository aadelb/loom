"""research_reconng_scan — Recon-ng modular OSINT framework integration."""

from __future__ import annotations

import asyncio
import logging
import os
from loom.cli_checker import is_available
from loom.error_responses import handle_tool_errors
from loom.subprocess_helpers import run_command
import tempfile
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("loom.tools.reconng_backend")


class ReconnGScanParams(BaseModel):
    """Parameters for research_reconng_scan tool."""

    target: str = Field(..., description="Target domain, IP, or email for reconnaissance")
    modules: list[str] | None = Field(
        default=None,
        description="List of recon-ng module names to run (e.g., ['whois', 'dns']). If None, runs discovery modules.",
    )
    timeout: int = Field(
        default=120,
        ge=10,
        le=600,
        description="Timeout in seconds for the entire scan operation",
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target", mode="before")
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Validate target format (domain, IP, or email)."""
        v = v.strip()
        if not v:
            raise ValueError("target cannot be empty")
        if len(v) > 255:
            raise ValueError("target exceeds max length (255 chars)")
        # Allow domains, IPs, and emails
        if not any(c in v for c in [".", "@"]):
            raise ValueError("target must be a domain, IP address, or email")
        # CRITICAL: Block shell metacharacters that could cause injection
        dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "<", ">", "\n", "\r"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"target contains invalid character: {char}")
        return v

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, v: list[str] | None) -> list[str] | None:
        """Validate module list format."""
        if v is None:
            return None
        if not v:
            raise ValueError("modules list cannot be empty (use None for auto-discovery)")
        if len(v) > 20:
            raise ValueError("modules list max 20 items")
        for mod in v:
            if not isinstance(mod, str):
                raise ValueError(f"module names must be strings, got {type(mod)}")
            if len(mod) > 64:
                raise ValueError(f"module name exceeds max length: {mod}")
        return v


class ReconnGResult(BaseModel):
    """Result from a recon-ng scan operation."""

    target: str
    findings: dict[str, Any] = Field(default_factory=dict)
    modules_run: list[str] = Field(default_factory=list)
    modules_failed: list[str] = Field(default_factory=list)
    total_findings: int = 0
    error: str | None = None
    elapsed_ms: int = 0


@handle_tool_errors("research_reconng_scan")
async def research_reconng_scan(
    target: str,
    modules: list[str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Execute recon-ng reconnaissance modules against a target.

    Recon-ng is a modular OSINT framework with 100+ reconnaissance modules
    for gathering information about domains, IP addresses, and email addresses.

    Args:
        target: Domain, IP address, or email to target
        modules: List of module names to run. If None, runs domain discovery modules.
        timeout: Timeout in seconds (10-600)

    Returns:
        Dict with findings, modules_run, modules_failed, total_findings, and error status.

    Example:
        >>> result = await research_reconng_scan("example.com", ["whois", "dns"])
        >>> print(result["total_findings"])
    """
    # Validate input
    params = ReconnGScanParams(target=target, modules=modules, timeout=timeout)

    # Check if recon-ng is available
    if not is_available("recon-ng"):
        return {
            "error": "recon-ng not found in PATH. Install with: pip install recon-ng",
            "target": params.target,
            "findings": {},
            "modules_run": [],
            "modules_failed": [],
            "total_findings": 0,
        }

    result = ReconnGResult(target=params.target)

    try:
        # Create temporary workspace directory
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_name = "loom_workspace"
            workspace_path = os.path.join(tmpdir, workspace_name)

            # Initialize workspace
            try:
                init_result = await asyncio.to_thread(
                    subprocess.run,
                    ["recon-ng", "-w", workspace_name, "--path", tmpdir, "-m", "create"],
                    timeout=10,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if init_result["returncode"] != 0:
                    result.error = f"Workspace initialization failed: {init_result["stderr"][:200]}"
                    logger.warning(f"recon-ng workspace init failed: {init_result["stderr"]}")
                    return result.model_dump()
            except subprocess.TimeoutExpired:
                result.error = "Workspace initialization timed out"
                return result.model_dump()

            # Determine modules to run
            modules_to_run = params.modules or _get_default_modules(params.target)

            # Run each module
            for module_name in modules_to_run:
                try:
                    cmd = [
                        "recon-ng",
                        "-w",
                        workspace_name,
                        "--path",
                        tmpdir,
                        "-m",
                        module_name,
                        "-o",
                        f"SOURCE={params.target}",
                        "--no-check",
                    ]

                    proc_result = await asyncio.to_thread(
                        subprocess.run,
                        cmd,
                        timeout=params.timeout,
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if proc_result["returncode"] == 0:
                        result.modules_run.append(module_name)
                        # Parse output for findings (simplified extraction)
                        _parse_module_output(
                            proc_result["stdout"], module_name, result.findings
                        )
                    else:
                        result.modules_failed.append(module_name)
                        logger.warning(
                            f"recon-ng module {module_name} failed: {proc_result["stderr"][:200]}"
                        )

                except subprocess.TimeoutExpired:
                    result.modules_failed.append(module_name)
                    logger.warning(f"recon-ng module {module_name} timed out")
                except Exception as e:
                    result.modules_failed.append(module_name)
                    logger.error(f"Error running recon-ng module {module_name}: {e}")

            # Calculate total findings
            result.total_findings = sum(
                len(v) if isinstance(v, list) else 1 for v in result.findings.values()
            )

    except Exception as e:
        result.error = f"Recon-ng scan failed: {str(e)[:200]}"
        logger.error(f"research_reconng_scan error: {e}")

    return result.model_dump()


def _get_default_modules(target: str) -> list[str]:
    """Return default recon-ng modules based on target type."""
    # Detect target type
    is_email = "@" in target
    # IPv6 check: presence of ':' AND hex/colon chars only
    # IPv4 check: all parts are numeric after removing dots
    is_ipv4 = all(
        part.isdigit() for part in target.split(".") if part
    ) and target.count(".") > 0
    is_ipv6 = ":" in target and all(
        c in "0123456789abcdefABCDEF:." for c in target
    )
    is_ip = is_ipv4 or is_ipv6

    if is_email:
        return ["whois_email", "email_extract"]
    elif is_ip:
        return ["whois_ip", "geoip"]
    else:
        # Assume domain
        return [
            "whois",
            "dns_reverse",
            "dns_txt",
            "dns_brute_snoop",
            "cert_transparency",
        ]


def _parse_module_output(
    output: str, module_name: str, findings: dict[str, Any]
) -> None:
    """Parse recon-ng module output and extract findings.

    Simplified parser that extracts key-value pairs and structured data
    from recon-ng module output.
    """
    if not output or not output.strip():
        return

    findings_list = []
    for line in output.split("\n"):
        line = line.strip()
        if not line or line.startswith("[*]"):
            continue
        if line.startswith("[!]"):
            # Error line, skip
            continue
        # Collect non-empty lines as findings
        if line and len(line) > 5:
            findings_list.append(line)

    if findings_list:
        findings[module_name] = findings_list
